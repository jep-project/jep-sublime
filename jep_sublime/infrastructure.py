"""Infrastructure to connect Sublime and JEP."""
import datetime
import logging
from jep.frontend import BackendListener, Frontend, State
from jep.schema import ContentSync, CompletionRequest
import sublime

_logger = logging.getLogger(__name__)

FRONTEND_POLL_DURATION_MS = 100
FRONTEND_POLL_PERIOD_MS = 1000

# TODO: clean up connections if front closes them (event needed?)
# issue: if connection is closed by sublime, run is no longer called --> connection is not properly closed --> connection is not
# properly reestablished --> state out of sync
#
# Try to keep running running frontend, at least until all connections are disconnected and dropped.

class BackendAdapter(BackendListener):
    def __init__(self):
        self.frontend = Frontend([self])
        #: Map from connection to supported views.
        self.connection_files_map = {}
        self.file_connection_map = {}
        self.next_token_id = 0
        self.completion_response = None

    def connect(self, view):
        self._get_connection_for_view(view)

    def disconnect(self, view):
        self._release_connection_for_view(view)

    def on_completion_response(self, response, context):
        self.completion_response = response

    def request_completion(self, view, file, data, pos):
        con = self._get_connection_for_view(view)
        if con and con.state is State.Connected:
                token = str(self.next_token_id)
                self.next_token_id += 1
                con.send_message(ContentSync(file=file, data=data))
                con.send_message(CompletionRequest(token=token, file=file, pos=pos))
                self.completion_response = None
                for i in range(0, 50):
                    con.run(datetime.timedelta(milliseconds=FRONTEND_POLL_DURATION_MS))
                    if self.completion_response:
                        break
                return self.completion_response
        else:
            _logger.warning("Completion request cannot be served, no connection.")
            return None

    def _get_connection_for_view(self, view):
        # do we already have a connection for this view?
        filename = view.file_name()
        con = self.file_connection_map.get(filename)

        # create one by filename if not:
        if not con:
            _logger.debug('Creating new connection for view %s.' % view.file_name())
            con = self.frontend.get_connection(filename)
            if con:
                self.file_connection_map[filename] = con

                # maybe the connection is already up as it was used by another file:
                files = self.connection_files_map.get(con)
                if not files:
                    files = set()
                    self.connection_files_map[con] = files

                files.add(filename)
            else:
                _logger.debug('Frontend did not identify backend for file.')

        return con

    def _release_connection_for_view(self, view):
        _logger.debug('Number of connections: %d' % len(self.connection_files_map))
        _logger.debug('Number of files:       %d' % len(self.file_connection_map))
        filename = view.file_name()
        con = self.file_connection_map.pop(filename, None)
        if con:
            files = self.connection_files_map[con]
            files.remove(filename)
            if not files:
                _logger.debug('Shutting down connection as last view was closed.')
                # con.disconnect()
                self.connection_files_map.pop(con)

    def run(self):
        for con in self.connection_files_map.keys():
            con.run(datetime.timedelta(milliseconds=FRONTEND_POLL_DURATION_MS))
        # view.set_status("jep-status", "JEP Backend Disconnected!")

    def run_periodically(self):
        self.run()
        sublime.set_timeout(self.run_periodically, FRONTEND_POLL_PERIOD_MS)
