"""Infrastructure to connect Sublime and JEP."""
import datetime
import logging

from jep.frontend import BackendListener, Frontend, State
from .editing import ContentTracker, Autocompleter, ErrorAnnotator
from .constants import FRONTEND_POLL_DURATION_MS, FRONTEND_POLL_PERIOD_MS, STATUS_CATEGORY, STATUS_FORMAT
import sublime

_logger = logging.getLogger(__name__)


# TODO for cleanup
# Move synchronous call logic to frontend connection class.

class BackendAdapter(BackendListener):
    """Adapter of JEP and Sublime events.

    This class coordinates the Sublime plugin and the JEP frontend class by implementing common tasks in a JEP/Sublime plugin that are independent of any specific editing
    features:

        * It maps views and files in Sublime to JEP connections.
        * It delegates Sublime events to interested editing capability implementations in the editing module.
    """

    def __init__(self, content_tracker=None, auto_completer=None, error_annotator=None):
        self._frontend = Frontend([self])
        #: Map from connection to supported views.
        self._connection_views_map = {}
        self._file_connection_map = {}

        self.content_tracker = content_tracker or ContentTracker()
        self.auto_completer = auto_completer or Autocompleter(self)
        self.error_annotator = error_annotator or ErrorAnnotator(self)

    def connect(self, view):
        self._get_or_create_connection_for_view(view)
        self.content_tracker.start_change_tracking(view)

    def disconnect(self, view):
        if 0 == self._release_connection_for_view(view):
            # this was the last view using this connection, no need to track any longer:
            self.content_tracker.stop_change_tracking(view)

    def mark_content_modified(self, view):
        self.content_tracker.mark_content_modified(view)

    def on_completion_response(self, response, context):
        # TODO Remove this after synchronous call logic has been moved to library:
        self.auto_completer._completion_response = response

    def _get_or_create_connection_for_view(self, view):
        # do we already have a connection for this view?
        con = self.get_connection_for_view(view)
        if not con:
            # try to create one:
            filename = view.file_name()
            _logger.debug('Creating new connection for file %s.' % filename)
            con = self._frontend.get_connection(filename)
            if con:
                self._file_connection_map[filename] = con

                # maybe the connection is already up as it was used by another file:
                views = self._connection_views_map.get(con)
                if not views:
                    views = []
                    self._connection_views_map[con] = views

                views.append(view)
            else:
                _logger.debug('Frontend did not identify backend for file.')

        if con:
            self._update_view_status_for_connection_state(view, con.state)

        return con

    def get_connection_for_view(self, view):
        """Public API to get an exiting connection for a view or None."""
        filename = view.file_name()
        con = self._file_connection_map.get(filename)
        return con

    def _release_connection_for_view(self, view):
        """Releases the connection for the given view and returns the number of views left using this connection."""
        num_views_left = 0

        _logger.debug('Number of connections: %d' % len(self._connection_views_map))
        _logger.debug('Number of files:       %d' % len(self._file_connection_map))
        filename = view.file_name()
        con = self._file_connection_map.pop(filename, None)
        if con:
            views = self._connection_views_map[con]
            views.remove(view)
            num_views_left = len(views)
            if not num_views_left:
                _logger.debug('Shutting down connection as last view was closed.')
                con.disconnect()

        return num_views_left

    def _update_view_status_for_connection_state(self, view, connection_state):
        if connection_state is State.Connected:
            status = "Connected"
        elif connection_state is State.Connecting:
            status = "Connecting..."
        elif connection_state is State.Disconnecting:
            status = "Disconnecting..."
        elif connection_state is State.Disconnected:
            status = "Disconnected"
        else:
            status = "Internal error, unexpected connection state %s." % connection_state
        view.set_status(STATUS_CATEGORY, STATUS_FORMAT % status)

    def run(self):
        for con in self._connection_views_map.keys():
            previous_state = con.state

            con.run(datetime.timedelta(milliseconds=FRONTEND_POLL_DURATION_MS))
            new_state = con.state

            for view in self._connection_views_map[con]:

                # show status changes:
                if new_state is not previous_state:
                    self._update_view_status_for_connection_state(view, new_state)

                # update view content if modified:
                if new_state is State.Connected:
                    self.content_tracker.synchronize_content(con, view)

    def run_periodically(self):
        self.run()
        sublime.set_timeout(self.run_periodically, FRONTEND_POLL_PERIOD_MS)
