from Components.Converter.Converter import Converter
from Components.Element import cached


class AdvancedEventLibraryShowHideText(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.txt = type

	@cached
	def getText(self):
		if self.source.text == self.txt or self.source.text.endswith(' B') or self.source.text.endswith('KB'):
			return ""
		else:
			return self.source.text

	text = property(getText)
