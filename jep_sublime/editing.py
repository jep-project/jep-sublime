"""Editing features for Sublime using JEP."""
import datetime
import logging
from jep.schema import ContentSync, CompletionRequest
from .constants import FRONTEND_POLL_DURATION_MS
import sublime

_logger = logging.getLogger(__name__)


class Autocompleter:
    def __init__(self, backend_adapter):
        self.backend_adapter = backend_adapter

    def on_query_completions(self, view, prefix, locations):
        result = []

        con = self.backend_adapter.get_connection_for_view(view)
        if con:
            response = con.request_message(CompletionRequest(file=view.file_name(), pos=locations[0]), datetime.timedelta(milliseconds=FRONTEND_POLL_DURATION_MS))
            if response:
                for option in response.options:
                    result.append(['%s\t%s' % (option.insert, option.desc), option.insert])
            else:
                _logger.warning('No completion response received.')
        else:
            _logger.warning('Completion request cannot be served, no connection for file %s.' % view.file_name())

        return result


class ErrorAnnotator:
    def __init__(self, backend_adapter):
        self.backend_adapter = backend_adapter
        self.errors_by_file = {}

    def on_modified(self, view):
        text = view.substr(sublime.Region(0, view.size()))
        # call to JEP backend here
        errors = self.fake_errors(text)
        self.update_errors(view, errors)

    def on_selection_modified(self, view):
        self.update_status_bar(view)

    def update_errors(self, view, errors):
        self.errors_by_file[view.file_name()] = errors
        view.erase_regions("jep-marker")
        regions = []
        for e in errors:
            regions.append(view.line(view.text_point(e[0], 0)))
        if len(regions) > 0:
            # * we don't have our own scopes, so use an existing one ("invalid.illegal")
            #	 if we wanted our own scopes, all the user's color schemes would have to be extended as Sublimelinter does
            # * tinting of gutter icons doesn't seem to work (use icon="dot" for a test)
            view.add_regions("jep-marker", regions, "invalid.illegal", flags=sublime.DRAW_SQUIGGLY_UNDERLINE | sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)
        self.update_status_bar(view)

    def update_status_bar(self, view):
        errors = self.errors_by_file.get(view.file_name(), [])
        # sublime doesn't support tooltips, so error hovers aren't possible
        # show errors in the status bar instead
        cur_line = self.cursor_line(view)
        in_error_line = False
        for e in errors:
            if cur_line == e[0]:
                view.set_status("jep-status", "Error: " + e[1])
                in_error_line = True
        if not in_error_line:
            view.set_status("jep-status", "%d errors" % len(errors))

    @staticmethod
    def cursor_line(view):
        region = view.sel()[0]
        return view.rowcol(region.a)[0]

    @staticmethod
    def fake_errors(text):
        errors = []
        lines = text.split("\n")
        i = 0
        for line in lines:
            if line.find("error") >= 0:
                errors.append([i, "there's an error"])
            i += 1
        return errors


class ContentTracker:
    def __init__(self):
        #: Map from filename to flag if backend buffer needs update.
        self.file_modified_map = {}

    def start_change_tracking(self, view):
        filename = view.file_name()
        if filename not in self.file_modified_map:
            # trigger initial content synchronization:
            self.file_modified_map[filename] = True

    def stop_change_tracking(self, view):
        filename = view.file_name()
        if filename in self.file_modified_map:
            self.file_modified_map.pop(filename)

    def mark_content_modified(self, view):
        filename = view.file_name()
        # Sublime seems to debounce this events, so this is no performance nightmare:
        if filename in self.file_modified_map:
            self.file_modified_map[filename] = True

    def synchronize_content(self, connection, view):
        """Synchronizes content with backend if modified."""
        filename = view.file_name()
        if self.file_modified_map.get(view.file_name(), False):
            self.file_modified_map[filename] = False
            connection.send_message(ContentSync(filename, view.substr(sublime.Region(0, view.size()))))
