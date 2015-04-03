import sublime, sublime_plugin
import sys
import string
from os.path import realpath, dirname, join

sys.path.append(join(dirname(realpath(__file__)), "..", "jep-python"))
from jep.config import ServiceConfigProvider 

class JEPAutocomplete(sublime_plugin.EventListener):
	def on_query_completions(self, view, prefix, locations):
		print("pos:		"+str(locations[0]))
		print("prefix: '"+prefix+"'")
		print("file		" + view.file_name())
		provider = ServiceConfigProvider()
		sc = provider.provide_for(view.file_name())
		if sc:
			print("command: "+sc.command)
		else:
			print("no JEP config")
		return [["jeptest1\thinter", "jeptest1"], ["jeptest2", "jeptest2"]]

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
			regions.append(view.line(view.text_point(e[0],0)))
		if len(regions) > 0:
			# * we don't have our own scopes, so use an existing one ("invalid.illegal")
			#	 if we wanted our own scopes, all the user's color schemes would have to be extended as Sublimelinter does
			# * tinting of gutter icons doesn't seem to work (use icon="dot" for a test)
			view.add_regions("jep-marker", regions, "invalid.illegal", flags=sublime.DRAW_SQUIGGLY_UNDERLINE|sublime.DRAW_NO_FILL|sublime.DRAW_NO_OUTLINE)
		self.update_status_bar(view)

	def update_status_bar(self, view):
		errors = self.errors_by_file.get(view.file_name(), [])
		# sublime doesn't support tooltips, so error hovers aren't possible
		# show errors in the status bar instead
		cur_line = self.cursor_line(view)
		in_error_line = False
		for e in errors:
			if cur_line == e[0]:
				view.set_status("jep-status", "Error: "+e[1])
				in_error_line = True
		if not in_error_line:
			view.set_status("jep-status", str(len(errors))+" errors")

	def cursor_line(self, view):
		region = view.sel()[0]
		return view.rowcol(region.a)[0]

	def fake_errors(self, text):
		errors = []
		lines = text.split("\n")
		i = 0
		for line in lines:
			if line.find("error") >= 0:
				errors.append([i, "there's an error"])
			i += 1 
		return errors
