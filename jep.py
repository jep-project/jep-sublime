import sublime, sublime_plugin
import sys
from os.path import realpath, dirname, join

sys.path.append(join(dirname(realpath(__file__)), "..", "jep-python"))
from jep.config import ServiceConfigProvider 

class JEPAutocomplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
    	print("pos:    "+str(locations[0]))
    	print("prefix: '"+prefix+"'")
    	print("file    " + view.file_name())
    	provider = ServiceConfigProvider()
    	sc = provider.provide_for(view.file_name())
    	if sc:
    		print("command: "+sc.command)
    	else:
    		print("no JEP config")
    	return [["jeptest1\thinter", "jeptest1"], ["jeptest2", "jeptest2"]]
