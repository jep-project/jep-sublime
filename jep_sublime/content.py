"""File content management."""
from jep_py.schema import ContentSync
import sublime

# TODO: Change interface to filename, not view level. We are tracking the file content, not a particular view.

class Tracker:
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
        if self.file_modified_map.get(filename, False):
            self.file_modified_map[filename] = False
            connection.send_message(ContentSync(filename, view.substr(sublime.Region(0, view.size()))))