import sublime, sublime_plugin
import sys
import datetime
from os.path import dirname, join

sys.path.append(join(dirname(__file__), "contrib"))
sys.path.append(join(dirname(__file__), "..", "jep-python"))
from jep.frontend import Frontend, BackendListener, State
from jep.schema import CompletionRequest, ContentSync

# TODO for cleanup
#
# Move jep specific classes (adapter, ...) to separate module, move to sub package to prevent being loaded by Sublime directly.
#
# Properly inject instances (adapter into plugin). Sublime instantiates listeners once per application instance.
#
# Move synchronous call logic to frontend connection class.

class BackendAdapter(BackendListener):
    def __init__(self):
        self.frontend = Frontend([self])
        self.connections = []
        self.next_token_id = 0
        self.connecting_views = {}
        self.completion_response = None

    def on_backend_alive(self, context):
        pass

    def on_completion_response(self, response, context):
        self.completion_response = response

    def request_completion(self, view, file, data, pos):
        con = self._connection(file)
        if con:
            if con.state is State.Connected:
                token = str(self.next_token_id)
                self.next_token_id += 1
                con.send_message(ContentSync(file=file, data=data))
                con.send_message(CompletionRequest(token=token, file=file, pos=pos))
                self.completion_response = None
                for i in range(0, 50):
                    con.run(datetime.timedelta(seconds=0.1))
                    if self.completion_response:
                        break
                return self.completion_response
            elif con.state is State.Connecting:
                view.set_status("jep-status", "JEP Backend Starting ...")
                self.connecting_views[con] = view
                return None
            elif con.state is State.Disconnected:
                view.set_status("jep-status", "JEP Backend Disconnected!")
                return None
            else:
                view.set_status("jep-status", "Unknown ...")
                return None
        else:
            print("no connection")
            return None

    def _connection(self, file):
        con = self.frontend.get_connection(file)
        if con and con not in self.connections:
            self.connections.append(con)
        return con

    def run(self):
        for con in self.connections:
            con.run(datetime.timedelta(seconds=0.1))
            if con.state is not State.Connecting and self.connecting_views.get(con, False):
                self.connecting_views[con].set_status("jep-status", "JEP Backend Ready!")
                self.connecting_views.pop(con, None)


class TimeoutHandler:
    def timeout(self):
        if self == timeout_handler:
            backend_adapter.run()
            sublime.set_timeout(self.timeout, 1000)


backend_adapter = BackendAdapter()

timeout_handler = TimeoutHandler()
timeout_handler.timeout()


class JEPAutocomplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        res = backend_adapter.request_completion(view, view.file_name(), view.substr(sublime.Region(0, view.size())), locations[0])
        result = []
        if res:
            desc_len = 60
            for option in res.options:
                desc = str(option.desc)
                if len(desc) > desc_len:
                    desc = str(option.desc)[0:desc_len - 3] + "..."
                else:
                    desc = str(option.desc).ljust(desc_len)
                result.append([option.insert + "\t" + desc, option.insert])
        return result


class JEPErrorAnnotation(sublime_plugin.EventListener):
    def __init__(self):
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
            view.set_status("jep-status", str(len(errors)) + " errors")

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
