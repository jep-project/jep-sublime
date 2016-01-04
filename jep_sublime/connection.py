"""Infrastructure to connect Sublime and JEP."""
import datetime
import logging
import os
import sublime
from jep_py.frontend import BackendListener, Frontend, State
from jep_py.schema import StaticSyntaxRequest, SyntaxFormatType
from .annotation import ErrorAnnotator
from .completion import Autocompleter
from .constants import FRONTEND_POLL_DURATION_MS, FRONTEND_POLL_PERIOD_MS, STATUS_CATEGORY, STATUS_FORMAT
from .content import Tracker
from .syntax import SyntaxManager

_logger = logging.getLogger(__name__)


class ConnectionManager(BackendListener):
    """Manages connections between Sublime and JEP backends. Maps views and files in Sublime to JEP connections."""

    def __init__(self, content_tracker=None, syntax_manager=None, auto_completer=None, error_annotator=None):
        self._frontend = Frontend([self])
        #: Map from connection to supported views.
        self._connection_views_map = {}
        self._file_connection_map = {}

        self.content_tracker = content_tracker or Tracker()
        self.syntax_manager = syntax_manager or SyntaxManager(os.path.join(sublime.packages_path(), 'jep'))
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

    def run(self):
        for con in self._connection_views_map.keys():
            previous_state = con.state

            con.run(datetime.timedelta(milliseconds=FRONTEND_POLL_DURATION_MS))
            state = con.state

            # update views' contents if modified:
            for view in self._connection_views_map[con]:
                if state is State.Connected:
                    self.content_tracker.synchronize_content(con, view)

    def run_periodically(self):
        self.run()
        sublime.set_timeout(self.run_periodically, FRONTEND_POLL_PERIOD_MS)

    def on_connection_state_changed(self, old_state, new_state, connection):
        views = self._connection_views_map.get(connection)
        if views:
            for view in views:
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
                _logger.debug('Connection state changed to {}.'.format(status))

        if new_state is State.Connected:
            # this is a new connection and possibly a new backend, so ask for any syntax definitions that are available:
            _logger.debug('Querying backend for syntax definitions.')
            connection.send_message(StaticSyntaxRequest(SyntaxFormatType.textmate))

    def on_static_syntax_list(self, format_, syntaxes, connection):
        if format_ is not SyntaxFormatType.textmate:
            _logger.debug('Ignoring {} syntax definitions in format {}.'.format(len(syntaxes), format_.name))
            return

        install = self.syntax_manager.install_syntax
        for syntax in syntaxes:
            install(syntax.name, syntax.definition)
