# -*- coding: utf-8 -*-
#
# EventList - Converter
#
# Coded by tsiegel (c) 2020

from Components.Converter.Converter import Converter
from Components.Element import cached
from enigma import eEPGCache, eServiceReference, iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceCenter


class AdvancedEventLibraryNextEvents(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.epgcache = eEPGCache.getInstance()
		self.eventcount = 10
		self.element = 0
		if type:
			self.element = int(type)

	@cached
	def getEvent(self):
		try:
			curEvent = None
			ref = self.source.service

			if hasattr(self.source, 'getEvent'):
				curEvent = self.source.getEvent()
			elif hasattr(self.source, 'event'):
				curEvent = self.source.event
			else:
				curEvent = self.source.getCurrentEvent()
			if (isinstance(curEvent, tuple) and curEvent):
				curEvent = curEvent[0]
			if curEvent and ref:
				if self.element < 0:
					return curEvent
				else:
					if not isinstance(ref, str):
						ref = eServiceReference(ref.toString())
					else:
						ref = eServiceReference(ref)
					return self.getResults(curEvent, ref, self.element)
			return None
		except Exception as ex:
			return None

	event = property(getEvent)

	def getResults(self, curEvent, ref, element=0):
		try:
			if not self.epgcache.startTimeQuery(ref, curEvent.getBeginTime() + curEvent.getDuration()):
				i = 1
				eventlist = []
				while i <= (self.eventcount):
					eventlist.append(self.epgcache.getNextTimeEntry())
					i += 1
				if eventlist:
					if len(eventlist) >= element:
						return eventlist[element]
		except Exception as ex:
			write_log("Fehler in getResultst : " + str(ex))
			return None
		return None

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC:
			Converter.changed(self, what)
