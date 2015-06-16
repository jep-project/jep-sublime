"""Infrastructure to connect Sublime and JEP."""
import datetime
from jep.frontend import BackendListener, Frontend, State
from jep.schema import ContentSync, CompletionRequest
import sublime

FRONTEND_POLL_DURATION_MS = 100
FRONTEND_POLL_PERIOD_MS = 1000


class BackendAdapter(BackendListener):
    def __init__(self):
        self.frontend = Frontend([self])
        self.connections = set()
        self.next_token_id = 0
        self.connecting_views = {}
        self.completion_response = None

    def on_completion_response(self, response, context):
        self.completion_response = response

    def request_completion(self, view, file, data, pos):
        con = self._get_connection(file)
        if con:
            if con.state is State.Connected:
                token = str(self.next_token_id)
                self.next_token_id += 1
                con.send_message(ContentSync(file=file, data=data))
                con.send_message(CompletionRequest(token=token, file=file, pos=pos))
                self.completion_response = None
                for i in range(0, 50):
                    con.run(datetime.timedelta(milliseconds=FRONTEND_POLL_DURATION_MS))
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

    def _get_connection(self, file):
        con = self.frontend.get_connection(file)
        self.connections.add(con)
        return con

    def run(self):
        for con in self.connections:
            con.run(datetime.timedelta(milliseconds=FRONTEND_POLL_DURATION_MS))
            if con.state is not State.Connecting and self.connecting_views.get(con, False):
                self.connecting_views[con].set_status("jep-status", "JEP Backend Ready!")
                self.connecting_views.pop(con, None)

    def run_periodically(self):
        self.run()
        sublime.set_timeout(self.run_periodically, FRONTEND_POLL_PERIOD_MS)
