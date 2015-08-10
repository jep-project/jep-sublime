"""Code completion."""
import datetime
import logging

from jep.schema import CompletionRequest
from .constants import FRONTEND_POLL_DURATION_MS

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


