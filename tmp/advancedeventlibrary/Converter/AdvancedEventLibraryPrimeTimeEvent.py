# -*- coding: utf-8 -*-
#
# PrimeTime - Converter
#
# Coded by tsiegel (c) 2020

from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config, ConfigClock, ConfigSubsection
from Components.Sources.CurrentService import CurrentService
from enigma import eEPGCache, eServiceReference, iServiceInformation, iPlayableService
from time import localtime, strftime, mktime, time
from datetime import datetime, timedelta
import HTMLParser

class AdvancedEventLibraryPrimeTimeEvent(Converter, object):
	htmlParser = HTMLParser.HTMLParser()
	def __init__(self, type):
		Converter.__init__(self, type)
		self.epgcache = eEPGCache.getInstance()
		config.plugins.AdvancedEventLibrary = ConfigSubsection()
		self.primeTimeStart = config.plugins.AdvancedEventLibrary.StartTime = ConfigClock(default = 69300) # 20:15

	def getServiceRef(self):
		ref = None
		if not isinstance(self.source, CurrentService):
			ref = self.source.service
		else:
			service = self.source.service
			info = service and service.info()
			if info:
				ref = info.getInfoString(iServiceInformation.sServiceref)
		return ref


	@cached
	def getText(self):
		ref = self.getServiceRef()
		if ref:
			return self.getResult(ref, 0)
		return None

	@cached
	def getEvent(self):
		ref = self.getServiceRef()
		if ref:
			return self.getResult(ref, 1)
		return None

	text = property(getText)
	event = property(getEvent)
#	service = property(getEvent)

	def getResult(self, ref, what=0):
		if not isinstance(ref, eServiceReference):
			ref = eServiceReference(ref)
		now = localtime(time())
		dt = datetime(now.tm_year, now.tm_mon, now.tm_mday, self.primeTimeStart.value[0], self.primeTimeStart.value[1])
		if time() > mktime(dt.timetuple()):
			dt += timedelta(days=1)
		primeTime = int(mktime(dt.timetuple()))
		if not self.epgcache.startTimeQuery(ref, primeTime):
			event = self.epgcache.getNextTimeEntry()
			if event and (event.getBeginTime() <= int(mktime(dt.timetuple()))):
				if what == 0:
					return self.getPrimeTimeEvent(event)
				else:
					return event
			else:
				if what == 0:
					return ""
				else:
					return None
		else:
			if what == 0:
				return ""
			else:
				return None
		if what == 0:
			return ""
		else:
			return None


	def getPrimeTimeEvent(self,event):
		time = "%s - %s" % (strftime("%H:%M", localtime(event.getBeginTime())), strftime("%H:%M", localtime(event.getBeginTime() + event.getDuration())))
		title = event.getEventName()
		duration = "%d Min." % (event.getDuration() / 60)
		return str(time) +  " " + str(title) + ' (' + str(duration) + ')' + str(self.getOneLineDescription(title, event))

	def getOneLineDescription(self, title, event):
		if(event != None):
			desc = event.getShortDescription()
			if(desc != "" and desc != None and desc != title):
				desc = desc.replace(title+'\n', '')
				if '\n' in desc:
					desc = desc.replace('\n', ' ' + str(self.htmlParser.unescape('&#xB7;')) + ' ')
				else:
					tdesc = desc.split("\n")
					desc = tdesc[0].replace('\\n', ' ' + str(self.htmlParser.unescape('&#xB7;')) + ' ')

				if desc.find(' Altersfreigabe: Ohne Altersbe') > 0:
					desc = desc[:desc.find(' Altersfreigabe: Ohne Altersbe')] + ' FSK: 0'
				return '\n' + self.getMaxWords(desc.replace('Altersfreigabe: ab', 'FSK:'), 18)
		return ""

	def getMaxWords(self, desc, maxWords):
		try:
			wordList = desc.split(" ")
			if (len(wordList) >= maxWords):
				del wordList[maxWords:len(wordList)]
				sep = ' '
				return sep.join(wordList) + '...'
			return desc
		except Exception as ex:
			return ""
		return ""

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart,):
			Converter.changed(self, what)
