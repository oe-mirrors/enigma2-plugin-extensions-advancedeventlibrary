# coding=utf-8
from __future__ import absolute_import
from operator import itemgetter
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
from Screens.ChannelSelection import service_types_tv
from Screens.ChoiceBox import ChoiceBox
from Screens.TimerEntry import TimerEntry
from Screens.InfoBar import MoviePlayer
from Components.Label import Label
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Sources.StaticText import StaticText
from Components.GUIComponent import GUIComponent
from Components.AVSwitch import AVSwitch
from Components.Pixmap import Pixmap
from time import time, localtime, mktime
import datetime
import os
import re
import json
import NavigationInstance
import pickle
from html.parser import HTMLParser
from skin import loadSkin
from RecordTimer import RecordTimerEntry, RecordTimer, parseEvent, AFTEREVENT
from enigma import eEPGCache, iServiceInformation, eServiceReference, eServiceCenter, ePixmap, loadJPG
from ServiceReference import ServiceReference
from enigma import eTimer, eListbox, ePicLoad, eLabel, eListboxPythonMultiContent, gFont, eRect, eSize, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, BT_SCALE, BT_FIXRATIO
from threading import Timer, Thread
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry, ConfigEnableDisable, \
    ConfigYesNo, ConfigText, ConfigNumber, ConfigSelection, ConfigClock, \
    ConfigDateTime, config, NoSave, ConfigSubsection, ConfigInteger, ConfigIP, configfile, ConfigNothing
from Tools.Directories import fileExists
from Components.Sources.Event import Event

from . import AdvancedEventLibrarySystem
from . import AdvancedEventLibraryLists
from Tools.AdvancedEventLibrary import getPictureDir, convertDateInFileName, convertTitle, convertTitle2, convert2base64, convertSearchName, getDB, getImageFile, clearMem
from Tools.LoadPixmap import LoadPixmap

htmlParser = HTMLParser()

pluginpath = '/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/'
skinpath = pluginpath + 'skin/'
imgpath = '/usr/share/enigma2/AELImages/'
log = "/var/tmp/AdvancedEventLibrary.log"

global active
active = False


def write_log(svalue):
	t = localtime()
	logtime = '%02d:%02d:%02d' % (t.tm_hour, t.tm_min, t.tm_sec)
	AdvancedEventLibrary_log = open(log, "a")
	AdvancedEventLibrary_log.write(str(logtime) + " : [Favoriten] : " + str(svalue) + "\n")
	AdvancedEventLibrary_log.close()


class EventEntry():
	def __init__(self, name, serviceref, eit, begin, duration, hasTimer, edesc, sname, image, hasTrailer):
		self.name = name
		self.serviceref = serviceref
		self.eit = eit
		self.begin = begin
		self.duration = duration
		self.hasTimer = hasTimer
		self.edesc = edesc
		self.sname = sname
		self.image = image
		self.hasTrailer = hasTrailer

	def __setitem__(self, item, value):
		if item == "hasTimer":
			self.hasTimer = value

	def __getitem__(self):
		return '{%s}' % str(', '.join('%s : %s' % (k, repr(v)) for (k, v) in self.__dict__.iteritems()))

	def __repr__(self):
		return '{%s}' % str(', '.join('%s : %s' % (k, repr(v)) for (k, v) in self.__dict__.iteritems()))


class AdvancedEventLibraryPlanerScreens(Screen):
	ALLOW_SUSPEND = True
	skin = loadSkin(skinpath + "AdvancedEventLibraryPlaners.xml")

	def __init__(self, session, viewType):
		global active
		active = True
		self.session = session
		Screen.__init__(self, session)
		self.title = "Favoriten-Planer"
		self.viewType = viewType
		if self.viewType == 'Listenansicht':
			self.skinName = "AdvancedEventLibraryListPlaners"
		else:
			self.skinName = "AdvancedEventLibraryWallPlaners"
		self.db = getDB()
		self.isinit = False
		self.lastidx = 0
		self.listlen = 0
		self.pageCount = 0
		self.timers = []
		self.epgcache = eEPGCache.getInstance()

		config.plugins.AdvancedEventLibrary = ConfigSubsection()
		self.favouritesMaxAge = config.plugins.AdvancedEventLibrary.FavouritesMaxAge = ConfigInteger(default=14, limits=(5, 90))
		self.favouritesViewCount = config.plugins.AdvancedEventLibrary.FavouritesViewCount = ConfigInteger(default=2, limits=(0, 10))
		self.favouritesPreviewDuration = config.plugins.AdvancedEventLibrary.FavouritesPreviewDuration = ConfigInteger(default=12, limits=(2, 240))
		self.excludedGenres = config.plugins.AdvancedEventLibrary.ExcludedGenres = ConfigText(default='Wetter,Dauerwerbesendung')

		self["key_red"] = StaticText("Beenden")
		self["key_green"] = StaticText("Timer hinzufügen")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("Umschalten")

		self["Content"] = StaticText("")
		if self.viewType == 'Listenansicht':
			self["eventList"] = AdvancedEventLibraryLists.EPGList()
			self["eventList"].connectsel_changed(self.sel_changed)
		else:
			self["eventWall"] = AdvancedEventLibraryLists.AELBaseWall()
			self["eventWall"].l.setBuildFunc(self.seteventEntry)
			self["ServiceRef"] = StaticText("")
			self["ServiceName"] = StaticText("")
			self['PageInfo'] = Label('')
			self.shaper = LoadPixmap('/usr/share/enigma2/AELImages/shaper.png')

		self["trailer"] = Pixmap()
		self["Event"] = Event()
		self["genreList"] = AdvancedEventLibraryLists.MenuList()
		self["genreList"].connectsel_changed(self.menu_sel_changed)
		self.current_event = None

		mask = (eServiceReference.isMarker | eServiceReference.isDirectory)
		root = eServiceReference(str(service_types_tv + ' FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
		serviceHandler = eServiceCenter.getInstance()
		self.tvbouquets = serviceHandler.list(root).getContent("SN", True)
		self.slist = {}
		for bouquet in self.tvbouquets:
			root = eServiceReference(str(bouquet[0]))
			serviceHandler = eServiceCenter.getInstance()
			ret = serviceHandler.list(root).getContent("SN", True)
			for (serviceref, servicename) in ret:
				playable = not (eServiceReference(serviceref).flags & mask)
				if playable and "p%3a" not in serviceref and "<n/a>" not in servicename and servicename != ".":
					self.slist[serviceref] = servicename

		recordHandler = NavigationInstance.instance.RecordTimer
		for timer in recordHandler.timer_list:
			if timer and timer.service_ref:
				_timer = str(timer.name)
				_timer = _timer.strip().replace(".", "").replace(":", "").replace("-", "").replace("  ", " ").upper()
				self.timers.append(_timer)
			if timer and timer.eit:
				_timer = str(timer.eit)
				self.timers.append(_timer)

		if fileExists(os.path.join(pluginpath, 'favourites.data')):
			self.favourites = self.load_pickle(os.path.join(pluginpath, 'favourites.data'))
		else:
			self.favourites = {'genres': {'Nachrichten': [2, time()]}, 'titles': {}}
		self.myFavourites = self.getFavourites()

		self["myActionMap"] = ActionMap(["AdvancedEventLibraryActions"],
		{
			"key_red": self.key_red_handler,
			"key_green": self.key_green_handler,
			"key_yellow": self.key_yellow_handler,
			"key_blue": self.key_blue_handler,
			"key_cancel": self.key_red_handler,
			"key_left": self.key_left_handler,
			"key_right": self.key_right_handler,
			"key_up": self.key_up_handler,
			"key_down": self.key_down_handler,
			"key_channel_up": self.key_channel_up_handler,
			"key_channel_down": self.key_channel_down_handler,
			"key_menu": self.key_menu_handler,
			'key_play': self.key_play_handler,
			"key_ok": self.key_ok_handler,
		}, -1)

		self["TeletextActions"] = HelpableActionMap(self, "InfobarTeletextActions",
			{
				"startTeletext": (self.infoKeyPressed, _("Switch between views")),
			}, -1)

		self.buildGenreList()
		self.onShow.append(self.refreshAll)

	def getFontOrientation(self, flag):
		fontOrientation = 0
		if "RT_WRAP" in flag:
			fontOrientation |= RT_WRAP
		else:
			fontOrientation &= ~RT_WRAP
		if "RT_HALIGN_LEFT" in flag:
			fontOrientation |= RT_HALIGN_LEFT
		if "RT_HALIGN_RIGHT" in flag:
			fontOrientation |= RT_HALIGN_RIGHT
		if "RT_HALIGN_CENTER" in flag:
			fontOrientation |= RT_HALIGN_CENTER
		if "RT_VALIGN_TOP" in flag:
			fontOrientation |= RT_VALIGN_TOP
		if "RT_VALIGN_BOTTOM" in flag:
			fontOrientation |= RT_VALIGN_BOTTOM
		if "RT_VALIGN_CENTER" in flag:
			fontOrientation |= RT_VALIGN_CENTER
		return fontOrientation

	def getFavourites(self):
		favs = {'titles': {}}
		excludedGenres = self.excludedGenres.value.split(',')
		for k, v in self.favourites['genres'].items():
			if k not in excludedGenres:
				if v[0] >= self.favouritesViewCount.value:
					res = self.db.getFavourites("genre LIKE '" + k + "'", (self.favouritesPreviewDuration.value * 3600))
					if res:
						favs[k] = res
		for k, v in self.favourites['titles'].items():
			if v[0] >= self.favouritesViewCount.value:
				res = self.db.getFavourites("title LIKE '%" + k + "%'", (self.favouritesPreviewDuration.value * 3600))
				if res:
					favs['titles'][k] = res
		return favs

	def load_pickle(self, filename):
		with open(filename, 'rb') as f:
			data = pickle.load(f)
		return data

	def key_menu_handler(self):
		self.session.openWithCallback(self.return_from_setup, MySetup)

	def return_from_setup(self):
		pass

	def key_ok_handler(self):
		if self.viewType == 'Listenansicht':
			selection = self["eventList"].l.getCurrentSelection()[0]
			eventName = (selection[0], selection[2])
		else:
			selection = self["eventWall"].getcurrentselection()
			eventName = (selection.name, selection.eit)
		self.session.openWithCallback(self.CELcallBack, AdvancedEventLibrarySystem.Editor, eventname=eventName)

	def CELcallBack(self):
		selected_element = self["genreList"].l.getCurrentSelection()[0]
		if self.viewType == 'Listenansicht':
			self["eventList"].setList(self.getEPGdata(selected_element[0]))
		else:
			self["eventWall"].setlist(self.getEPGdata(selected_element[0]))
			self["eventWall"].movetoIndex(0)
			self.pageCount = self['eventWall'].getPageCount()
			self['PageInfo'].setText('Seite ' + str(self['eventWall'].getCurrentPage()) + ' von ' + str(self.pageCount))
		self.sel_changed()

	def buildGenreList(self):
		imgpath = skin.variables.get("EventLibraryImagePath", '/usr/share/enigma2/AELImages/,').replace(',', '')
		genrelist = []
		for k, v in self.myFavourites.items():
			if k != 'titles':
				itm = [str(k), imgpath + "movies.png"]
				genrelist.append((itm,))
		genrelist.sort(key=lambda x: x[0][0])
		itm = ['Meist gesehen', imgpath + "filme.png"]
		genrelist.insert(0, (itm,))
		self["genreList"].setList(genrelist)

	def refreshAll(self):
		if not self.isinit:
			if self.viewType != 'Listenansicht':
				self.parameter = self["eventWall"].getParameter()
				self.imageType = str(self.parameter[3])
				self.substituteImage = str(self.parameter[5])
				self.FontOrientation = self.getFontOrientation(self.parameter[25])
				self.Coverings = eval(str(self.parameter[23]))
			imgpath = skin.variables.get("EventLibraryImagePath", '/usr/share/enigma2/AELImages/,').replace(',', '')
			ptr = LoadPixmap(os.path.join(imgpath, "play.png"))
			self["trailer"].instance.setPixmap(ptr)
			self.isinit = True
			self.menu_sel_changed()

	def infoKeyPressed(self):
		try:
			if self.viewType == 'Listenansicht':
				self.close('Wallansicht')
			else:
				self.close('Listenansicht')
		except Exception as ex:
			write_log('infoKeyPressed : ' + str(ex))

	def key_red_handler(self):
		clearMem("Favoriten-Planer")
		global active
		active = False
		self.close()

	def key_green_handler(self):
		self.addtimer()

	def key_yellow_handler(self):
		pass

	def key_blue_handler(self):
		if self.viewType == 'Listenansicht':
			selected_element = self["eventList"].l.getCurrentSelection()[0]
			sRef = str(selected_element[1])
		else:
			selected_element = self["eventWall"].getcurrentselection()
			sRef = str(selected_element.serviceref)
		self.session.nav.playService(eServiceReference(sRef))
		self.close()

	def key_right_handler(self):
		if self.viewType == 'Listenansicht':
			self['eventList'].pageDown()
		else:
			old_idx = int(self['eventWall'].getCurrentIndex())
			if old_idx == self.listlen - 1:
				self['eventWall'].movetoIndex(0)
			else:
				self['eventWall'].right()
				new_idx = int(self['eventWall'].getCurrentIndex())
				if new_idx <= old_idx:
					if (old_idx + 1) >= self.listlen:
						dest = 0
					else:
						dest = old_idx + 1
					self['eventWall'].movetoIndex(dest)
			self['eventWall'].refresh()
			self['PageInfo'].setText('Seite ' + str(self['eventWall'].getCurrentPage()) + ' von ' + str(self.pageCount))
			self.sel_changed()

	def key_left_handler(self):
		if self.viewType == 'Listenansicht':
			self['eventList'].pageUp()
		else:
			old_idx = int(self['eventWall'].getCurrentIndex())
			if old_idx == 0:
				dest = self.listlen - 1
				self['eventWall'].movetoIndex(dest)
			else:
				self['eventWall'].left()
				new_idx = int(self['eventWall'].getCurrentIndex())
				if new_idx >= old_idx:
					if (new_idx - 1) < 0:
						dest = self.listlen - 1
					else:
						dest = old_idx - 1
					self['eventWall'].movetoIndex(dest)
			self['eventWall'].refresh()
			self['PageInfo'].setText('Seite ' + str(self['eventWall'].getCurrentPage()) + ' von ' + str(self.pageCount))
			self.sel_changed()

	def key_down_handler(self):
		if self.viewType == 'Listenansicht':
			self['eventList'].moveDown()
		else:
			old_idx = int(self['eventWall'].getCurrentIndex())
			if old_idx == self.listlen - 1:
				self['eventWall'].movetoIndex(0)
			else:
				self['eventWall'].down()
				new_idx = int(self['eventWall'].getCurrentIndex())
				if new_idx <= old_idx:
					if (new_idx + self.parameter[14]) >= self.listlen:
						dest = 0
					else:
						dest = new_idx + self.parameter[14]
					self['eventWall'].movetoIndex(dest)
			self['eventWall'].refresh()
			self['PageInfo'].setText('Seite ' + str(self['eventWall'].getCurrentPage()) + ' von ' + str(self.pageCount))
			self.sel_changed()

	def key_up_handler(self):
		if self.viewType == 'Listenansicht':
			self['eventList'].moveUp()
		else:
			old_idx = int(self['eventWall'].getCurrentIndex())
			if old_idx == 0:
				dest = self.listlen - 1
				self['eventWall'].movetoIndex(dest)
			else:
				self['eventWall'].up()
				new_idx = int(self['eventWall'].getCurrentIndex())
				if new_idx >= old_idx:
					if (new_idx - self.parameter[14]) < 0:
						dest = self.listlen - 1
					else:
						dest = new_idx - self.parameter[14]
					self['eventWall'].movetoIndex(dest)
			self['eventWall'].refresh()
			self['PageInfo'].setText('Seite ' + str(self['eventWall'].getCurrentPage()) + ' von ' + str(self.pageCount))
			self.sel_changed()

	def key_channel_up_handler(self):
		self.lastidx = 0
		self['genreList'].moveUp()
		self.menu_sel_changed()

	def key_channel_down_handler(self):
		self.lastidx = 0
		self['genreList'].moveDown()
		self.menu_sel_changed()

	def key_play_handler(self):
		try:
			if self.viewType == 'Listenansicht':
				selected_element = self["eventList"].l.getCurrentSelection()[0]
				if selected_element:
					if selected_element[8]:
						sRef = eServiceReference(4097, 0, str(selected_element[8]))
						sRef.setName(str(selected_element[0]))
						self.session.open(MoviePlayer, sRef)
			else:
				selected_element = self["eventWall"].getcurrentselection()
				if selected_element:
					if selected_element.hasTrailer:
						sRef = eServiceReference(4097, 0, str(selected_element.hasTrailer))
						sRef.setName(str(selected_element.name))
						self.session.open(MoviePlayer, sRef)
		except Exception as ex:
			write_log("key_play : " + str(ex))

	def addtimer(self):
		try:
			if self.current_event is None:
				return False

			if self.viewType == 'Listenansicht':
				selected_element = self["eventList"].l.getCurrentSelection()[0]
				sRef = str(selected_element[1])
				eit = int(selected_element[2])
			else:
				selected_element = self["eventWall"].getcurrentselection()
				sRef = str(selected_element.serviceref)
				eit = int(selected_element.eit)
			(begin, end, name, description, eit) = parseEvent(self.current_event)
			recname = name
			recdesc = ""
			val = self.db.getliveTV(eit, name, begin)
			if val:
				if str(val[0][11]) != "Spielfilm":
					if str(val[0][2]) != "":
						recname = convertTitle(recname) + ' - '
					else:
						recname += ' - '
					if str(val[0][12]) != "":
						recname += "S" + str(val[0][12]).zfill(2)
					if str(val[0][13]) != "":
						recname += "E" + str(val[0][13]).zfill(2) + ' - '
					if str(val[0][2]) != "":
						recname += str(val[0][2]) + ' - '
					if recname.endswith(' - '):
						recname = recname[:-3]
				else:
					if str(val[0][4]) != "":
						recname = recname + " (" + str(val[0][4]) + ")"
				if str(val[0][2]) != "":
					recdesc = str(val[0][2]) + ', '
				if str(val[0][12]) != "":
					recdesc = recdesc + 'Staffel ' + str(val[0][12]) + ' '
				if str(val[0][13]) != "":
					recdesc = recdesc + 'Folge ' + str(val[0][13]) + ', '
				if str(val[0][14]) != "":
					recdesc = recdesc + str(val[0][14]) + ', '
				if str(val[0][15]) != "":
					recdesc = recdesc + str(val[0][15]) + ', '
				if str(val[0][4]) != "":
					recdesc = recdesc + str(val[0][4]) + ', '
				if recdesc != "":
					recdesc = recdesc[:-2]
			else:
				recdesc = description

			timer = RecordTimerEntry(ServiceReference(sRef), begin, end, recname, recdesc, eit, False, False, afterEvent=AFTEREVENT.AUTO, dirname=config.usage.default_path.value, tags=None)
			timer.repeated = 0
			timer.tags = ['AEL-Favoriten-Planer']

			self.session.openWithCallback(self.finishedAdd, TimerEntry, timer)
		except Exception as ex:
			write_log("addtimer : " + str(ex))

	def finishedAdd(self, answer, instantTimer=False):
		if answer[0]:
			entry = answer[1]
			simulTimerList = self.session.nav.RecordTimer.record(entry)
			if simulTimerList is not None:
				for x in simulTimerList:
					if x.setAutoincreaseEnd(entry):
						self.session.nav.RecordTimer.timeChanged(x)
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList is not None:
					self.session.openWithCallback(self.finishSanityCorrection, TimerSanityConflict, simulTimerList)
			if self.viewType == 'Listenansicht':
				self.lastidx = self["eventList"].getCurrentIndex()
				cs = self["eventList"].l.getCurrentSelection()[0]
				cs[5] = True
				self["eventList"].updateListObject(cs)
			else:
				cs = self["eventWall"].getcurrentselection()
				cs.__setitem__('hasTimer', True)
				self["eventWall"].refresh()

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def sel_changed(self):
		try:
			selected_element = None
			if self.viewType == 'Listenansicht':
				selected_element = self["eventList"].l.getCurrentSelection()[0]
				if selected_element:
					sRef = str(selected_element[1])
					eit = int(selected_element[2])
					epgcache = eEPGCache.getInstance()
					self.current_event = epgcache.lookupEventId(eServiceReference(sRef), eit)
					self["Event"].newEvent(self.current_event)

					if selected_element[6]:
						self["Content"].setText(selected_element[6] + self.getSimilarEvents(eit, sRef))
					else:
						self["Content"].setText('')
					if selected_element[8]:
						self["trailer"].show()
					else:
						self["trailer"].hide()
			else:
				selected_element = self["eventWall"].getcurrentselection()
				if selected_element:
					sRef = str(selected_element.serviceref)
					eit = int(selected_element.eit)
					epgcache = eEPGCache.getInstance()
					self.current_event = epgcache.lookupEventId(eServiceReference(sRef), eit)
					self["Event"].newEvent(self.current_event)

					if selected_element.edesc:
						self["Content"].setText(selected_element.edesc + self.getSimilarEvents(eit, sRef))
					else:
						self["Content"].setText('')
					if selected_element.hasTrailer:
						self["trailer"].show()
					else:
						self["trailer"].hide()
					self["ServiceRef"].setText(sRef)
					self["ServiceName"].setText(selected_element.sname)
		except Exception as ex:
			write_log("sel_changed : " + str(ex))
			self["Content"].setText("Keine Sendetermine im EPG gefunden\n" + str(ex))
			self["Event"].newEvent(None)

	def menu_sel_changed(self):
		try:
			selected_element = self["genreList"].l.getCurrentSelection()[0]
			if self.viewType == 'Listenansicht':
				self["eventList"].setList(self.getEPGdata(selected_element[0]))
				self["eventList"].moveToIndex(self.lastidx)
			else:
				self["eventWall"].setlist(self.getEPGdata(selected_element[0]))
				self["eventWall"].movetoIndex(0)
				self["eventWall"].refresh()
				self.pageCount = self['eventWall'].getPageCount()
				self['PageInfo'].setText('Seite ' + str(self['eventWall'].getCurrentPage()) + ' von ' + str(self.pageCount))
			self.sel_changed()
		except Exception as ex:
			self["Content"].setText("Keine Sendetermine im EPG gefunden")
			write_log("menu_sel_changed : " + str(ex))

	def getSimilarEvents(self, id, ref):
		epgcache = eEPGCache.getInstance()
		ret = epgcache.search(('NB', 100, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, ref, id))
#		l = epgcache.search(('NBIR', 100, eEPGCache.EXAKT_TITLE_SEARCH, str(name), eEPGCache.NO_CASE_CHECK))
		if ret is not None:
			ret.sort(self.sort_func)
			text = '\n\nWeitere Sendetermine:'
			for x in ret:
				t = localtime(x[1])
				text += '\n%d.%d.%d, %02d:%02d  -  %s' % (t[2], t[1], t[0], t[3], t[4], x[0])
			return text
		return ''

	def sort_func(self, x, y):
		if x[1] < y[1]:
			return -1
		elif x[1] == y[1]:
			return 0
		else:
			return 1

	def getEPGdata(self, what="Serien"):
		try:
			favs = set()
			sList = []
			if what != "Meist gesehen":
				for fav in self.myFavourites[str(what).decode('utf-8')]:
					favs.add((fav[0], str(fav[1])))
			else:
				for key, value in self.myFavourites['titles'].items():
					for fav in value:
						favs.add((fav[0], str(fav[1])))

			for favourite in favs:
				try:
					event = self.epgcache.lookupEventId(eServiceReference(str(favourite[1])), int(favourite[0]))
					if event:
						serviceref = str(favourite[1])
						eit = int(favourite[0])
						name = event.getEventName()
						begin = event.getBeginTime()
						duration = event.getDuration()
						shortdesc = event.getShortDescription()
						extdesc = event.getExtendedDescription()
						desc = None
						cleanname = name.strip().replace(".", "").replace(":", "").replace("-", "").replace("  ", " ").upper()
						hasTimer = False
						if cleanname in self.timers or str(eit) in self.timers:
							hasTimer = True

						desc = name + ' ' + shortdesc + ' ' + extdesc
						if extdesc and extdesc != '':
							edesc = extdesc
						else:
							edesc = shortdesc
						sname = self.slist.get(serviceref, None)
						image = None
						hasTrailer = None
						evt = self.db.getliveTV(eit, name, begin)
						if evt:
							if evt[0][16].endswith('mp4'):
								hasTrailer = evt[0][16]
						if hasTrailer is None:
							dbdata = self.db.getTitleInfo(convert2base64(name))
							if dbdata and dbdata[7].endswith('mp4'):
								hasTrailer = dbdata[7]
						if self.viewType != 'Listenansicht':
							if self.imageType == "cover":
								if evt:
									if evt[0][3] != '':
										image = getImageFile(getPictureDir() + self.imageType + '/', evt[0][3])
							if image is None:
								image = getImageFile(getPictureDir() + self.imageType + '/', name)
						itm = (name, serviceref, eit, begin, duration, hasTimer, edesc, sname, image, hasTrailer)
						sList.append(itm)
				except Exception as ex:
					write_log("getEPGdata : " + str(ex))
					continue

			eList = []
			if sList:
				sList.sort(key=lambda x: x[3], reverse=False)
				self.listlen = len(sList)
				for item in sList:
					if self.viewType == 'Listenansicht':
						itm = [item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7], item[9]]
					else:
						itm = EventEntry(item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7], item[8], item[9])
					eList.append((itm,))
			else:
				if self.viewType == 'Listenansicht':
					itm = ['Keine Sendungen gefunden', 0, 0, 0, 0, False, ' ', ' ', None, None]
				else:
					itm = EventEntry('Keine Sendungen gefunden', 0, 0, 0, 0, False, ' ', ' ', None, None)
				eList.append((itm,))
			return eList
		except Exception as ex:
			write_log("getEPGdata : " + str(ex))
			return []

	def seteventEntry(self, entrys):
		try:
			picon = None
			image = None
			pic = self.findPicon(entrys.serviceref, entrys.sname)
			maxLength = self.parameter[2]
			if len(entrys.sname) > maxLength:
				entrys.sname = str(entrys.sname)[:maxLength] + '...'
			if len(entrys.name) > maxLength:
				name = str(entrys.name)[:maxLength] + '...'
			else:
				name = str(entrys.name)
			self.picloader = PicLoader(int(self.parameter[0]), int(self.parameter[1]))
			if entrys.image:
				image = self.picloader.load(entrys.image)
			else:
				if self.substituteImage == "replaceWithPicon":
					if pic:
						image = LoadPixmap(str(pic))
				else:
					image = self.picloader.load(self.substituteImage)
			self.picloader.destroy()
			if pic:
				picon = LoadPixmap(pic)  # self.picloader.load(entrys.picon)

			ret = [entrys]
			#rework
			#if image:
			#	ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.parameter[17][0], self.parameter[17][1], self.parameter[17][0], self.parameter[17][1], self.parameter[17][2], self.parameter[17][3], self.parameter[17][2], self.parameter[17][3], image, None, None, BT_SCALE))
			#for covering in self.Coverings:
			#	ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, covering[0], covering[1], covering[0], covering[1], covering[2], covering[3], covering[2], covering[3], self.shaper, None, None, BT_SCALE))
			#if picon:
			#	ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.parameter[21][0], self.parameter[21][1], self.parameter[21][0], self.parameter[21][1], self.parameter[21][2], self.parameter[21][3], self.parameter[21][2], self.parameter[21][3], picon, None, None, BT_SCALE))
			#if entrys.hasTimer and fileExists(self.parameter[15]):
			#	ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.parameter[19][0] + self.parameter[19][4], self.parameter[19][1], self.parameter[19][0] + self.parameter[19][4], self.parameter[19][1], self.parameter[19][2], self.parameter[19][3], self.parameter[19][2], self.parameter[19][3], self.parameter[19][5], self.parameter[19][5], self.FontOrientation, entrys.sname, skin.parseColor(self.parameter[6]).argb(), skin.parseColor(self.parameter[7]).argb()))
			#	ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.parameter[20][0] + self.parameter[20][4], self.parameter[20][1], self.parameter[20][0] + self.parameter[20][4], self.parameter[20][1], self.parameter[20][2], self.parameter[20][3], self.parameter[20][2], self.parameter[20][3], self.parameter[20][5], self.parameter[20][5], self.FontOrientation, name, skin.parseColor(self.parameter[6]).argb(), skin.parseColor(self.parameter[7]).argb()))
			#	ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.parameter[18][0], self.parameter[18][1], self.parameter[18][0], self.parameter[18][1], self.parameter[18][2], self.parameter[18][3], self.parameter[18][2], self.parameter[18][3], LoadPixmap(self.parameter[15]), None, None, BT_SCALE))
			#else:
			#	ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.parameter[19][0], self.parameter[19][1], self.parameter[19][0], self.parameter[19][1], self.parameter[19][2], self.parameter[19][3], self.parameter[19][2], self.parameter[19][3], self.parameter[19][5], self.parameter[19][5], self.FontOrientation, entrys.sname, skin.parseColor(self.parameter[6]).argb(), skin.parseColor(self.parameter[7]).argb()))
			#	ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.parameter[20][0], self.parameter[20][1], self.parameter[20][0], self.parameter[20][1], self.parameter[20][2], self.parameter[20][3], self.parameter[20][2], self.parameter[20][3], self.parameter[20][5], self.parameter[20][5], self.FontOrientation, name, skin.parseColor(self.parameter[6]).argb(), skin.parseColor(self.parameter[7]).argb()))
			return ret

			write_log("error in entrys : " + str(entrys))
			#return [entrys,
			#					(eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, 2, 2, 2, 2, 96, 96, 96, 96, 0, 0, RT_WRAP | RT_HALIGN_CENTER | RT_VALIGN_CENTER, 'Das war wohl nix', skin.parseColor(self.parameter[6]).argb(), skin.parseColor(self.parameter[7]).argb()),
			#					]
		except Exception as ex:
			write_log('Fehler in seteventEntry : ' + str(ex))

	def findPicon(self, service=None, serviceName=None):
		if service is not None:
			pos = service.rfind(':')
			if pos != -1:
				if service.startswith("1:134"):
					service = GetWithAlternative(service)
					pos = service.rfind(':')
				service = service[:pos].rstrip(':').replace(':', '_')
			pos = service.rfind('_http')
			if pos != -1:
					service = service[:pos].rstrip('_http').replace(':', '_')
			pngname = os.path.join(config.usage.picon_dir.value, service + ".png")
			if os.path.isfile(pngname):
				return pngname
		if serviceName is not None:
			pngname = os.path.join(config.usage.picon_dir.value, serviceName + ".png")
			if os.path.isfile(pngname):
				return pngname
		return None

####################################################################################


class MySetup(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.skinName = ["Favoriten-Planer-Setup", "Setup"]
		self.title = "Favoriten-Planer-Setup"
		self.db = getDB()
		self.genres = self.db.getGenres()

		self.setup_title = "Favoriten-Planer-Setup"
		self["title"] = StaticText(self.title)

		self["key_red"] = StaticText("Beenden")
		self["key_green"] = StaticText("Speichern")

		config.plugins.AdvancedEventLibrary = ConfigSubsection()
		self.favouritesMaxAge = config.plugins.AdvancedEventLibrary.FavouritesMaxAge = ConfigInteger(default=14, limits=(5, 90))
		self.favouritesViewCount = config.plugins.AdvancedEventLibrary.FavouritesViewCount = ConfigInteger(default=2, limits=(0, 10))
		self.favouritesPreviewDuration = config.plugins.AdvancedEventLibrary.FavouritesPreviewDuration = ConfigInteger(default=12, limits=(2, 240))
		self.viewType = config.plugins.AdvancedEventLibrary.ViewType = ConfigSelection(default="Wallansicht", choices=["Listenansicht", "Wallansicht"])
		self.excludedGenres = config.plugins.AdvancedEventLibrary.ExcludedGenres = ConfigText(default='Wetter,Dauerwerbesendung')

		self.configlist = []
		self.buildConfigList()
		ConfigListScreen.__init__(self, self.configlist, session=self.session, on_change=self.changedEntry)

		self["myActionMap"] = ActionMap(["AdvancedEventLibraryActions"],
		{
			"key_cancel": self.close,
			"key_red": self.close,
			"key_green": self.do_close,
		}, -1)

	def buildConfigList(self):
		try:
			if self.configlist:
				del self.configlist[:]
			self.configlist.append(getConfigListEntry("Einstellungen", ConfigSelection(choices=[('', '<DUMMYENTRY>')])))
			self.configlist.append(getConfigListEntry("entferne Genre/Sendung nach x Tagen nicht gesehen", self.favouritesMaxAge))
			self.configlist.append(getConfigListEntry("zeige Genre/Sendung mindestens x mal gesehen", self.favouritesViewCount))
			self.configlist.append(getConfigListEntry("Vorschaudauer der Favoriten innerhalb x Stunden", self.favouritesPreviewDuration))
			self.configlist.append(getConfigListEntry("Ansicht", self.viewType))
			if self.genres:
				self.configlist.append(getConfigListEntry("Ignorelist", ConfigSelection(choices=[('', '<DUMMYENTRY>')])))
				excluded = self.excludedGenres.value.split(',')
				for genre in self.genres:
					if genre in excluded:
						entry = ConfigYesNo(default=True)
					else:
						entry = ConfigYesNo(default=False)
					self.configlist.append(getConfigListEntry("ignoriere das Genre " + str(genre), entry))

		except Exception as ex:
			write_log("Fehler in buildConfigList : " + str(ex))

	def changedEntry(self):
		cur = self["config"].getCurrent()
		if cur and cur is not None:
			if not "ignoriere" in cur[0]:
				self.buildConfigList()
		self["config"].setList(self.configlist)
		if cur and cur is not None:
			self["config"].updateConfigListView(cur)

	def do_close(self):
		restartbox = self.session.openWithCallback(self.restartGUI, MessageBox, _("GUI needs a restart to apply new configuration.\nDo you want to restart the GUI now ?"), MessageBox.TYPE_YESNO)
		restartbox.setTitle(_("GUI needs a restart."))

	def restartGUI(self, answer):
		if answer is True:
			excludedGenres = ""
			for x in self["config"].list:
				if not "ignoriere" in x[0]:
					x[1].save()
				else:
					if x[1].value:
						excludedGenres += x[0].replace("ignoriere das Genre ", "").strip() + ","
			if excludedGenres.endswith(","):
				excludedGenres = excludedGenres[:-1]
			self.excludedGenres.value = excludedGenres
			self.excludedGenres.save()
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close()

#################################################################################################################################################


class PicLoader:
	def __init__(self, width, height):
		self.picload = ePicLoad()
		self.picload.setPara((width, height, 0, 0, False, 1, "#ff000000"))

	def load(self, filename):
		self.picload.startDecode(filename, 0, 0, False)
		data = self.picload.getData()
		return data

	def destroy(self):
		del self.picload
