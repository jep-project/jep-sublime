import sys
from os.path import dirname, join

sys.path.append(join(dirname(__file__), "contrib"))
sys.path.append(join(dirname(__file__), "..", "jep-python"))

from .jep_sublime.infrastructure import BackendAdapter, TimeoutHandler
from .jep_sublime.editing import JEPAutocomplete, JEPErrorAnnotation
import sublime_plugin


# TODO for cleanup
# Move synchronous call logic to frontend connection class.


class JepSublimeEventListener(sublime_plugin.EventListener):
    """Entry point for Sublime events, composes object tree."""

    def __init__(self, backend_adapter=None, timeout=None, auto_completer=None, error_annotator=None):
        self.backend_adapter = backend_adapter or BackendAdapter()
        self.timeout = timeout or TimeoutHandler(self.backend_adapter)
        self.auto_completer = auto_completer or JEPAutocomplete(self.backend_adapter)
        self.error_annotator = error_annotator or JEPErrorAnnotation(self.backend_adapter)

        self.timeout.timeout()

    def on_query_completions(self, view, prefix, locations):
        return self.auto_completer.on_query_completions(view, prefix, locations)

    def on_modified(self, view):
        self.error_annotator.on_modified(view)

    def on_selection_modified(self, view):
        self.error_annotator.on_selection_modified(view)


