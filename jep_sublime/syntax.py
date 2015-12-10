"""Syntax file management."""
import hashlib
import logging
import os
import re

_logger = logging.getLogger(__name__)


class SyntaxManager:
    """
    Controls installation and use of syntax highlighting definitions.

    After a syntax definition was uploaded from backend, this manager does the following:

    * Builds storage path = Packages/<syntax.name>.tmLanguage.
    * If already existing, compares hashes of syntax files and updates, if different.
    * Otherwise just saves to storage path.
    * Triggers syntax reloads for all affected view, depending on <syntax.extensions>, via sublime.View.set_syntax_file.

    This class:

    * Caches names to hash mapping, to prevent recomputing file hashes.
    * Remembers, which views need to apply a new syntax (does Sublime use a new file without restart for new views?).
    * Remembers, which syntax was downloaded from (which/any) backend in the current session to prevent reinstallation.
    """

    SYNTAX_FILE_PATTERN = re.compile(r'^(?P<name>[\w\.\-]+)\.tmLanguage$')
    SYNTAX_FILE_FORMAT = '{name}.tmLanguage'

    def __init__(self, dirpath):
        #: Path to directory holding JEP syntax files.
        self.dirpath = os.path.abspath(dirpath)
        #: Map from syntax name to content hash value.
        self.name_to_hash = {}
        self.compute_local_hashes()

    def install_syntax(self, name, extensions, definition):
        """Installs syntax definition if new."""
        _logger.debug('Received syntax {}.'.format(name))

        if not self.syntax_hash(definition) == self.syntax_file_hash(name):
            _logger.info('Installing new or updated syntax definition {}.'.format(name))

            with open(self.syntax_file_path(name), 'wt') as syntaxfile:
                syntaxfile.write(definition)

            # No need to notify sublime, as it is watching the packages folder and applies new or updated
            # syntax definitions immediately.

    def compute_local_hashes(self):
        self.name_to_hash = dict()

        if not os.path.exists(self.dirpath):
            os.makedirs(self.dirpath)

        matches = filter(None, (self.SYNTAX_FILE_PATTERN.match(entry) for entry in os.listdir(self.dirpath)))
        names = (m.group('name') for m in matches)
        self.name_to_hash = {name: self.syntax_file_hash(name) for name in names}

        _logger.debug('Found {} local syntax files in {}.'.format(len(self.name_to_hash), self.dirpath))

    def syntax_file_hash(self, name):
        """Computes hash value of content of syntax file with given name in ``dirpath``."""

        try:
            with open(self.syntax_file_path(name)) as syntaxfile:
                content = syntaxfile.read()
                hash_ = self.syntax_hash(content)
                return hash_
        except FileNotFoundError:
            return None
        except Exception as ex:
            _logger.warning('Cannot access syntax file {}: {}'.format(name, ex))
            return None

    def syntax_file_path(self, name):
        return os.path.join(self.dirpath, self.SYNTAX_FILE_FORMAT.format(name=name))

    @classmethod
    def syntax_hash(cls, syntaxtext):
        return hashlib.sha1(syntaxtext.encode()).digest()
