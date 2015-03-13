import sublime, sublime_plugin

class JEPAutocomplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
    	print("pos:    "+str(locations[0]))
    	print("prefix: '"+prefix+"'")
    	print("file    " + view.file_name())
    	return [["jeptest1", "jeptest1"], ["jeptest2", "jeptest2"]] 
