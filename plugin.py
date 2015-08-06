import logging
import sys
from os.path import dirname, join

sys.path.append(join(dirname(__file__), "contrib"))
sys.path.append(join(dirname(__file__), "..", "jep-python"))

from .jep_sublime.infrastructure import BackendAdapter
from .jep_sublime.editing import Autocompleter, ErrorAnnotator
import sublime_plugin

_logger = logging.getLogger(__name__)


class JepSublimeEventListener(sublime_plugin.EventListener):
    """Entry point for Sublime events, composes object tree."""

    def __init__(self, backend_adapter=None):
        self.backend_adapter = backend_adapter or BackendAdapter()
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
        return self.backend_adapter.auto_completer.on_query_completions(view, prefix, locations)

    def on_modified(self, view):
        """View content was modified by user."""
        self.backend_adapter.mark_content_modified(view)

