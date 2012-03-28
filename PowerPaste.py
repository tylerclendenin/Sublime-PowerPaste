import sublime, sublime_plugin, threading, re

class PowerpasteCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.window().show_input_panel('Input a comma delimited list, a span of numbers, or a single number', '', lambda s: self.run_replacement(s), None, None)

	def run_replacement(self, replace_with):
		sels = self.view.sel() 
		offset = 0
		threads = []
		
		for sel in sels:
			string = self.view.substr(sel)
			thread = PowerpasteApiCall(sel, string, replace_with, 5)
			threads.append(thread)
			thread.start()

		self.view.sel().clear()

		edit = self.view.begin_edit('powerpaste')

		self.handle_threads(edit, threads)

	def handle_threads(self, edit, threads, offset=0, i=0, dir=1):
		next_threads = []
		for thread in threads:
			if thread.is_alive():
				next_threads.append(thread)
				continue
			if thread.result == False:
				continue
			offset = self.replace(edit, thread, offset)
		threads = next_threads

		if len(threads):
			before = i % 8
			after = (7) - before
			if not after:
				dir = -1
			if not  before:
				dir = 1
			i += dir

			self.view.set_status('powerpaste', 'Powerpaste [%s=%s]' % \
				(' ' * before, ' ' * after))

			sublime.set_timeout(lambda: self.handle_threads(edit, threads, offset, i, dir), 100)

			return

		self.view.end_edit(edit)

		self.view.erase_status('powerpaste')
		selections = len(self.view.sel())
		sublime.status_message('Powerpaste successfully run on %s selection%s' % \
			(selections, '' if selections == 1 else 's'))

	def replace(self, edit, thread, offset):
		sel = thread.sel
		original = thread.original
		result = thread.result

		# Here we adjust each selection for any text we have already inserted
		if offset:
			sel = sublime.Region(sel.begin() + offset,
				sel.end() + offset)

		result = self.normalize_line_endings(result)
		(prefix, main, suffix) = self.fix_whitespace(original, result, sel)
		self.view.replace(edit, sel, prefix + main + suffix)
		#self.view.replace(edit, sel, result)

		# We add the end of the new text to the selection
		end_point = sel.begin() + len(prefix) + len(main)
		#end_point = sel.begin() + len(result)
		self.view.sel().add(sublime.Region(end_point, end_point))

		return offset + len(prefix + main + suffix) - len(original)
		#return offset + len(result) - len(original)

	def normalize_line_endings(self, string):  
		string = string.replace('\r\n', '\n').replace('\r', '\n')  
		line_endings = self.view.settings().get('default_line_ending')  
		if line_endings == 'windows':  
			string = string.replace('\n', '\r\n')  
		elif line_endings == 'mac':  
			string = string.replace('\n', '\r')  
		return string

	def fix_whitespace(self, original, prefixed, sel):  
		#short circuit fix_whitespace method until I know what I am doing
		return ('', prefixed, '')  

		(row, col) = self.view.rowcol(sel.begin())  
		indent_region = self.view.find('^\s+', self.view.text_point(row, 0))  
		
		if indent_region != None:
			if self.view.rowcol(indent_region.begin())[0] == row:  
				indent = self.view.substr(indent_region)  
			else:  
				indent = ''
		else:
			indent = ''

		prefixed = prefixed.strip()  
		prefixed = re.sub(re.compile('^\s+', re.M), '', prefixed)  

		settings = self.view.settings()  
		use_spaces = settings.get('translate_tabs_to_spaces')  
		tab_size = int(settings.get('tab_size', 8))  
		indent_characters = '\t'  
		if use_spaces:  
			indent_characters = ' ' * tab_size  
		prefixed = prefixed.replace('\n', '\n' + indent + indent_characters)  

		match = re.search('^(\s*)', original)  
		prefix = match.groups()[0]  
		match = re.search('(\s*)\Z', original)  
		suffix = match.groups()[0]  
		  
		return (prefix, prefixed, suffix)  

class PowerpasteApiCall(threading.Thread):
		def __init__(self, sel, string, replace_with, timeout):
			super(PowerpasteApiCall, self).__init__()
			self.sel = sel
			self.original = string
			self.timeout = timeout
			self.result = None
			self.replace_with = replace_with
			threading.Thread.__init__(self)

		def tonum(self, str):
			try:
				return int(str)
			except ValueError:
				return 0

		def run(self):
			replacements = []
			if self.replace_with.find(',') != -1:
				replacements = self.replace_with.split(',')
			elif self.replace_with.find('-') != -1:
				replacements = range(
					self.tonum(
						self.replace_with[0:self.replace_with.find('-')]
					), self.tonum(
						self.replace_with[self.replace_with.find('-')+1:len(self.replace_with)]
					)
				)
			else:
				replacements = range(self.tonum(self.replace_with))

			print replacements
			replace_result = []
			for replace_with_value in replacements:
				replace_result.append(self.original.replace('[*]', str(replace_with_value)))

			if len(replace_result) > 0:
				self.result = '\n'.join(replace_result)
			else:
				self.result = self.original
