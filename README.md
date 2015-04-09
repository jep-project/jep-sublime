# JEP Sublime Plugin

This is the JEP frontend plugin for sublime.

## Installation

Clone jep-sublime and jep-python into your Sublime package directory.

## Dependencies

Sublime 3 with a Python 3.3 setup.

## Usage

The JEP plugin will look for a file named ".jep" in the directory of the
file which is currently being edited or any of its parent folders.
If such a file is found and a configuration entry exists with a pattern
matching the current file's name, the corresponding backend startup
command line is executed and the plugin tries to connect to the new process.
See the JEP protocol description for details [https://github.com/jep-project/jep].

Backend startup is triggered on demand, e.g. when content completion is
invoked for the first time. In this case there will be a note in the
status bar telling that the backend is currently starting up. The command
which triggered the startup will not complete. 

Once the backend is loaded, Sublime will display a note in the status bar
and subsequent plugin operations should work as expected.

### Content Completion

Sublime will automatically suggest completions while you type and any
completion options contributed by a JEP backend will be merged with
options provided by Sublime's built-in functionality.
Press Ctrl-Space to trigger content completion manually.

