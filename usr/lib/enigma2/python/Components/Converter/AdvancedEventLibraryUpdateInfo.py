from time import localtime
from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached
from Tools import AdvancedEventLibrary as AEL


class AdvancedEventLibraryUpdateInfo(Poll, Converter, object):
	def __init__(self, type):
		Poll.__init__(self)
		Converter.__init__(self, type)
		types = type.split(',')
		self.invert = "Invert" in types
		self.poll_interval = 500
		self.poll_enabled = True

	@cached
	def getText(self):
		for x in self.downstream_elements:
			if AEL.STATUS == None:
				x.visible = True if self.invert else False
			else:
				x.visible = False if self.invert else True
				return AEL.STATUS

	text = property(getText)

	def changed(self, what):
		if what[0] == self.CHANGED_POLL:
			Converter.changed(self, what)

	def connectDownstream(self, downstream):
		Converter.connectDownstream(self, downstream)
