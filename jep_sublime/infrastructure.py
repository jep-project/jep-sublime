import datetime
from jep.frontend import BackendListener, Frontend, State
from jep.schema import ContentSync, CompletionRequest
import sublime


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
    def __init__(self, backend_adapter):
        self.backend_adapter = backend_adapter

    def timeout(self):
        self.backend_adapter.run()
        sublime.set_timeout(self.timeout, 1000)