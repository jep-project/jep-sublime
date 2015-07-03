"""Infrastructure to connect Sublime and JEP."""
import datetime
import logging
from jep.frontend import BackendListener, Frontend, State
from jep.schema import ContentSync, CompletionRequest
import sublime

_logger = logging.getLogger(__name__)

FRONTEND_POLL_DURATION_MS = 100
FRONTEND_POLL_PERIOD_MS = 1000
STATUS_CATEGORY = 'JEP'
STATUS_FORMAT = 'JEP: %s'


class BackendAdapter(BackendListener):
    def __init__(self):
        self.frontend = Frontend([self])
        #: Map from connection to supported views.
        self.connection_views_map = {}
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
                views = self.connection_views_map.get(con)
                if not views:
                    views = []
                    self.connection_views_map[con] = views

                views.append(view)
            else:
                _logger.debug('Frontend did not identify backend for file.')

        return con

    def _release_connection_for_view(self, view):
        _logger.debug('Number of connections: %d' % len(self.connection_views_map))
        _logger.debug('Number of files:       %d' % len(self.file_connection_map))
        filename = view.file_name()
        con = self.file_connection_map.pop(filename, None)
        if con:
            views = self.connection_views_map[con]
            views.remove(view)
            if not views:
                _logger.debug('Shutting down connection as last view was closed.')
                con.disconnect()

    def run(self):
        for con in self.connection_views_map.keys():
            previous_state = con.state

            con.run(datetime.timedelta(milliseconds=FRONTEND_POLL_DURATION_MS))
            new_state = con.state

            if new_state is not previous_state:
                for view in self.connection_views_map[con]:
                    if new_state is State.Connected:
                        status = "Connected"
                    elif new_state is State.Connecting:
                        status = "Connecting..."
                    elif new_state is State.Disconnecting:
                        status = "Disconnecting..."
                    elif new_state is State.Disconnected:
                        status = "Disconnected"
                    else:
                        status = "Internal error, unexpected connection state %s." % new_state
                    view.set_status(STATUS_CATEGORY, STATUS_FORMAT % status)

    def run_periodically(self):
        self.run()
        sublime.set_timeout(self.run_periodically, FRONTEND_POLL_PERIOD_MS)
