"""Code completion."""
import datetime
import logging

from jep_py.schema import CompletionRequest
import sublime
from .constants import FRONTEND_POLL_DURATION_MS

_logger = logging.getLogger(__name__)


class Autocompleter:
    def __init__(self, backend_adapter):
        self.backend_adapter = backend_adapter

    def on_query_completions(self, view, prefix, locations):
        result = []

        con = self.backend_adapter.get_connection_for_view(view)
        if con:
            # Prefix passed in from Sublime not used here, as backend is expected to have full view of file content.
            response = con.request_message(CompletionRequest(file=view.file_name(), pos=locations[0]), datetime.timedelta(milliseconds=FRONTEND_POLL_DURATION_MS))
            if response:
                for option in response.options:
                    result.append(['%s\t%s' % (option.insert, option.desc), option.insert])
            else:
                _logger.warning('No completion response received.')
        else:
            _logger.warning('Completion request cannot be served, no connection for file %s.' % view.file_name())

        # INHIBIT_WORD_COMPLETIONS: prevent dummy code completion, i.e. do not simply offer any words found in document
        # INHIBIT_EXPLICIT_COMPLETIONS: prevent completions from completion files
        return result, sublime.INHIBIT_WORD_COMPLETIONS
