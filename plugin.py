import logging
import sys
from os.path import dirname, join

sys.path.append(join(dirname(__file__), "contrib"))
sys.path.append(join(dirname(__file__), "..", "jep-python"))

from .jep_sublime.infrastructure import BackendAdapter
from .jep_sublime.editing import JEPAutocomplete, JEPErrorAnnotation
import sublime_plugin


# TODO for cleanup
# Move synchronous call logic to frontend connection class.

_logger = logging.getLogger(__name__)


class JepSublimeEventListener(sublime_plugin.EventListener):
    """Entry point for Sublime events, composes object tree."""

    def __init__(self, backend_adapter=None, auto_completer=None, error_annotator=None):
        self.backend_adapter = backend_adapter or BackendAdapter()
        self.auto_completer = auto_completer or JEPAutocomplete(self.backend_adapter)
        self.error_annotator = error_annotator or JEPErrorAnnotation(self.backend_adapter)

        self.backend_adapter.run_periodically()

    def on_activated(self, view):
        """Activation of existing view, needed to capture files in editor from last Sublime session."""
        _logger.debug('Activated view %s.' % view.file_name())
        if view.file_name():
            self.backend_adapter.connect(view)

    def on_load(self, view):
        """File was opened from disk."""
        _logger.debug('Loaded view %s.' % view.file_name())
        self.backend_adapter.connect(view)

    def on_post_save(self, view):
        """File was saved to disk. For a new file we now have a name."""
        _logger.debug('Saved view %s.' % view.file_name())
        self.backend_adapter.connect(view)

    def on_close(self, view):
        """File was removed from editor."""
        _logger.debug('Closed view %s.' % view.file_name())
        self.backend_adapter.disconnect(view)

    def on_query_completions(self, view, prefix, locations):
        return self.auto_completer.on_query_completions(view, prefix, locations)

    def on_modified(self, view):
        self.error_annotator.on_modified(view)

    def on_selection_modified(self, view):
        self.error_annotator.on_selection_modified(view)
