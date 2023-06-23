# -*- coding: utf-8 -*-

############################################################
####################  tsiegel 09.2019  #####################
############################################################

from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Converter.Poll import Poll
from time import localtime
from Tools import AdvancedEventLibrary as AEL

log = "/var/tmp/AdvancedEventLibrary.log"

def write_log(svalue):
	t = localtime()
	logtime = '%02d:%02d:%02d' % (t.tm_hour, t.tm_min, t.tm_sec)
	Chamaeleon_log = open(log,"a")
	Chamaeleon_log.write(str(logtime) + " : [AdvancedEventLibraryUpdateInfo] - " + str(svalue) + "\n")
	Chamaeleon_log.close()

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
		try:
			for x in self.downstream_elements:
				if AEL.STATUS == None:
					if self.invert:
						x.visible = True
					else:
						x.visible = False
				else:
					if self.invert:
						x.visible = False
					else:
						x.visible = True
					return AEL.STATUS
		except Exception as ex:
			write_log("Fehler in getText : " + str(ex))

	text = property(getText)

	def changed(self, what):
		if what[0] == self.CHANGED_POLL:
			Converter.changed(self, what)

	def connectDownstream(self, downstream):
		Converter.connectDownstream(self, downstream)
