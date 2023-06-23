# coding=utf-8
from operator import itemgetter
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
from Screens.ChannelSelection import service_types_tv
from Screens.ChoiceBox import ChoiceBox
from Screens.TimerEntry import TimerEntry
from Screens.InfoBar import InfoBar, MoviePlayer
from Components.Label import Label, MultiColorLabel
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Sources.StaticText import StaticText
from Components.GUIComponent import GUIComponent
from Components.AVSwitch import AVSwitch
from Components.Pixmap import Pixmap
from Components.Sources.ServiceEvent import ServiceEvent
from Tools.Alternatives import GetWithAlternative
from time import time, localtime, mktime, strftime
import datetime
import os
import re
import json
import NavigationInstance
import HTMLParser
import skin
import cPickle as pickle
import struct
from datetime import timedelta
from RecordTimer import RecordTimerEntry, RecordTimer, parseEvent, AFTEREVENT
from enigma import eEPGCache, iServiceInformation, eServiceReference, eServiceCenter, ePixmap, loadJPG
from ServiceReference import ServiceReference
from enigma import eTimer, eListbox, ePicLoad, eLabel, eWallPythonMultiContent, eListboxPythonMultiContent, gFont, eRect, eSize, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_VALIGN_BOTTOM, RT_WRAP, BT_SCALE, BT_FIXRATIO
from threading import Timer, Thread
from thread import start_new_thread
from Components.ConfigList import ConfigListScreen, getSelectionChoices
from Components.config import getConfigListEntry, ConfigEnableDisable, \
    ConfigYesNo, ConfigText, ConfigNumber, ConfigSelection, ConfigClock, \
    ConfigDateTime, config, NoSave, ConfigSubsection, ConfigInteger, ConfigIP, configfile, fileExists, ConfigNothing, ConfigDescription

import .AdvancedEventLibrarySystem
import .AdvancedEventLibrarySimpleMovieWall
import .AdvancedEventLibraryChannelSelection
from .AdvancedEventLibraryLists import AELBaseWall, MultiColorNTextLabel
from Tools.AdvancedEventLibrary import getPictureDir, convertDateInFileName, convertTitle, convertTitle2, convert2base64, convertSearchName, getDB, getImageFile, clearMem
from Tools.LoadPixmap import LoadPixmap

htmlParser = HTMLParser.HTMLParser()

pluginpath = '/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/'
skinpath = pluginpath + 'skin/'
piconpaths = [config.usage.servicelist_picon_dir.value, config.usage.picon_dir.value]
imgpath = '/usr/share/enigma2/AELImages/'
log = "/var/tmp/AdvancedEventLibrary.log"

global active
active = False


def write_log(svalue):
	t = localtime()
	logtime = '%02d:%02d:%02d' % (t.tm_hour, t.tm_min, t.tm_sec)
	AdvancedEventLibrary_log = open(log, "a")
	AdvancedEventLibrary_log.write(str(logtime) + " : [Media-Hub] : " + str(svalue) + "\n")
	AdvancedEventLibrary_log.close()


def loadskin(filename):
	path = skinpath + filename
	with open(path, "r") as f:
		skin = f.read()
		f.close()
	return skin


class ChannelEntry():
	def __init__(self, serviceref, eit, servicename, title, timespan, duration, progress, picon, image, bouquet, hasTimer, number, begin, hasTrailer=""):
		self.serviceref = serviceref
		self.servicename = servicename
		self.eit = eit
		self.title = title
		self.timespan = timespan
		self.duration = duration
		self.progress = progress
		self.picon = picon
		self.image = image
		self.bouquet = bouquet
		self.hasTimer = hasTimer
		self.number = number
		self.begin = begin
		self.hasTrailer = hasTrailer

	def __setitem__(self, item, value):
		if item == "image":
			self.image = value
		elif item == "hasTimer":
			self.hasTimer = value

	def __repr__(self):
		return '{%s}' % str(', '.join('%s : %s' % (k, repr(v)) for (k, v) in self.__dict__.iteritems()))


class MovieEntry():
	def __init__(self, filename, date, name, service, image, isFolder, progress, desc, hasTrailer=""):
		self.filename = filename
		self.name = name
		self.date = date
		self.service = service
		self.image = image
		self.isFolder = isFolder
		self.progress = progress
		self.desc = desc
		self.hasTrailer = hasTrailer

	def __setitem__(self, item, value):
		if item == "progress":
			self.progress = value
		elif item == "image":
			self.image = value

	def __repr__(self):
		return '{%s}' % str(', '.join('%s : %s' % (k, repr(v)) for (k, v) in self.__dict__.iteritems()))


class AdvancedEventLibraryMediaHub(Screen):
	ALLOW_SUSPEND = True
	skin = str(loadskin("AdvancedEventLibraryMediaHub.xml"))

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		global active
		active = True

		self.title = "Advanced-Event-Library-Media-Hub"
		self.skinName = "AdvancedEventLibraryMediaHub"
		self.db = getDB()
		self.isinit = False
		self.channelList = []
		self.timers = []
		self.channelListLen = 0
		self.movieListLen = 0
		self.idx = 0
		self.channelType = 0
		self.movieType = 0
		self.activeList = "TV"
		self.currentBouquet = None
		self.switchWithPVR = False
		self.myFavourites = None
		self.shaper = LoadPixmap('/usr/share/enigma2/AELImages/shaper.png')

		self.userBouquets = []
		self.userBouquets.append(('Alle Bouquets',))

		config.plugins.AdvancedEventLibrary = ConfigSubsection()
		self.myBouquet = config.plugins.AdvancedEventLibrary.ChannelSelectionStartBouquet = ConfigSelection(default="Alle Bouquets", choices=['Alle Bouquets', 'aktuelles Bouquet'])
		self.recordingsCount = config.plugins.AdvancedEventLibrary.RecordingsCount = ConfigInteger(default=12, limits=(5, 100))
		self.maxEventAge = config.plugins.AdvancedEventLibrary.MaxEventAge = ConfigInteger(default=5, limits=(0, 60))
		self.maxEventStart = config.plugins.AdvancedEventLibrary.MaxEventStart = ConfigInteger(default=10, limits=(1, 60))
		self.epgViewType = config.plugins.AdvancedEventLibrary.EPGViewType = ConfigSelection(default="EventView", choices=['EPGSelection', 'EventView'])
		self.channelStartType = config.plugins.AdvancedEventLibrary.MediaHubStartType = ConfigSelection(default="0", choices=[("0", "aktuelles Programm"), ("1", "nächste Sendungen"), ("2", "gerade begonnen/startet gleich"), ("3", "Prime-Time-Programm"), ("4", "Empfehlungen")])
		self.primeTimeStart = config.plugins.AdvancedEventLibrary.StartTime = ConfigClock(default=69300)  # 20:15
		self.viewType = config.plugins.AdvancedEventLibrary.ViewType = ConfigSelection(default="Wallansicht", choices=["Listenansicht", "Wallansicht"])
		self.favouritesViewCount = config.plugins.AdvancedEventLibrary.FavouritesViewCount = ConfigInteger(default=2, limits=(0, 10))
		self.favouritesPreviewDuration = config.plugins.AdvancedEventLibrary.FavouritesPreviewDuration = ConfigInteger(default=12, limits=(2, 240))
		self.excludedGenres = config.plugins.AdvancedEventLibrary.ExcludedGenres = ConfigText(default='Wetter,Dauerwerbesendung')

		self.channelType = int(self.channelStartType.value)
		self.CHANSEL = InfoBar.instance.servicelist
		ref = ServiceReference(self.session.nav.getCurrentlyPlayingServiceReference()).__str__()
		for protocol in ("http", "rtmp", "rtsp", "mms", "rtp"):
			pos = ref.rfind(':' + protocol)
			if pos != -1:
				ref = ref.split(protocol)[0]
				break
		self.current_service_ref = ref

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

		root = eServiceReference(str(service_types_tv + ' FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
		serviceHandler = eServiceCenter.getInstance()
		self.tvbouquets = serviceHandler.list(root).getContent("SN", True)
		self.channelNumbers = {}
		channelNumber = 1
		for bouquet in self.tvbouquets:
			self.channelNumbers[bouquet[1]] = {}
			self.userBouquets.append((bouquet[1],))
			root = eServiceReference(str(bouquet[0]))
			serviceHandler = eServiceCenter.getInstance()
			ret = serviceHandler.list(root).getContent("SN", True)
			for (serviceref, servicename) in ret:
				self.channelNumbers[bouquet[1]][serviceref] = [channelNumber, servicename, bouquet[0]]
				channelNumber += 1
		self.epgcache = eEPGCache.getInstance()

		self["channelList"] = AELBaseWall()
		self["channelList"].l.setBuildFunc(self.buildChannelList)
		self['movieList'] = AELBaseWall()
		self["movieList"].l.setBuildFunc(self.buildMovieList)

		self["trailer"] = Pixmap()
		self["channelsText"] = MultiColorNTextLabel()
		self["moviesText"] = MultiColorNTextLabel()
		self["channelsInfo"] = MultiColorLabel()
		self["moviesInfo"] = MultiColorLabel()
		self["timeInfo"] = MultiColorNTextLabel()

		self["key_red"] = StaticText("Beenden")
		self["key_green"] = StaticText("Kanalliste")
		self["key_yellow"] = StaticText("Bouquetauswahl")  # (self.myBouquet.value)
		self["key_blue"] = StaticText("Advanced-Event-Library")

		self["Service"] = ServiceEvent()
		self.current_event = None

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
			"key_ok": self.key_ok_handler,
			"key_pvr": self.key_pvr_handler,
			'key_play': self.key_play_handler,
			"key_info": self.key_info_handler,
		}, -1)

		self["TeletextActions"] = HelpableActionMap(self, "InfobarTeletextActions",
			{
				"startTeletext": (self.infoKeyPressed, _("Switch between views")),
			}, -1)

		self.onShow.append(self.refreshAll)

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

	def refreshAll(self):
		if not self.isinit:
			self.channelParameter = self["channelList"].getParameter()
			self.channelImageType = str(self.channelParameter[3])
			self.channelSubstituteImage = str(self.channelParameter[5])
			self.channelListControl = eval(self.channelParameter[22])
			self.channelListCoverings = eval(str(self.channelParameter[23]))
			self.channelListFontOrientation = self.getFontOrientation(self.channelParameter[25])

			self.myFavourites = self.getFavourites()

			if self.myBouquet.value == 'Alle Bouquets':
				self.getChannelList(self.tvbouquets, self.channelType)
			else:
				bName = ServiceReference(self.CHANSEL.servicelist.getRoot()).getServiceName()
				bRoot = ServiceReference(self.CHANSEL.servicelist.getRoot()).getPath()
				self.getChannelList([('1:7:1:0:0:0:0:0:0:0:' + bRoot, bName)])
			if self.channelList:
				self["channelList"].setlist(self.channelList)
				self["channelList"].movetoIndex(self.idx)
				self["channelsInfo"].setText(str(self["channelList"].getCurrentIndex() + 1) + '/' + str(self.channelListLen))
				self["channelList"].refresh()
				self.channel_changed()

			imgpath = skin.variables.get("EventLibraryImagePath", '/usr/share/enigma2/AELImages/,').replace(',', '')
			ptr = LoadPixmap(os.path.join(imgpath, "play.png"))
			self["trailer"].instance.setPixmap(ptr)

			self.movieParameter = self["movieList"].getParameter()
			self.movieImageType = str(self.movieParameter[3])
			self.movieSubstituteImage = str(self.movieParameter[5])
			self.movieListControl = eval(self.movieParameter[22])
			self.movieListCoverings = eval(str(self.movieParameter[23]))
			self.movieListFontOrientation = self.getFontOrientation(self.movieParameter[25])
			if fileExists(os.path.join(pluginpath, 'moviewall.data')):
				self.moviedict = self.load_pickle(os.path.join(pluginpath, 'moviewall.data'))
				self.getMovieList()
			else:
				self.moviedict = None

			self["channelList"].setSelectionEnable(True)
			self["movieList"].setSelectionEnable(False)
			self["channelList"].refresh()
			self["movieList"].refresh()
			self["channelsText"].setForegroundColorNum(1)
			self["channelsText"].setBackgroundColorNum(1)
			self["moviesText"].setForegroundColorNum(0)
			self["moviesText"].setBackgroundColorNum(0)
			self["channelsInfo"].setForegroundColorNum(1)
			self["channelsInfo"].setBackgroundColorNum(1)
			self["moviesInfo"].setForegroundColorNum(0)
			self["moviesInfo"].setBackgroundColorNum(0)

			self.switchWithPVR = self.channelListControl.get('switchControl', False) or self.movieListControl.get('switchControl', False)
			self.isinit = True

	def load_pickle(self, filename):
		with open(filename, 'rb') as f:
			data = pickle.load(f)
		return data

	def infoKeyPressed(self):
		try:
			if self.activeList == "TV":
				if self.channelType < 4:
					self.channelType += 1
				else:
					self.channelType = 0
				self.getChannelList(self.currentBouquet, self.channelType)
				if self.channelList:
					self["channelList"].setlist(self.channelList)
					self["channelList"].movetoIndex(self.idx)
					self["channelList"].refresh()
					self["channelsInfo"].setText(str(self["channelList"].getCurrentIndex() + 1) + '/' + str(self.channelListLen))
					self.channel_changed()
			else:
				if self.movieType < 1:
					self.movieType += 1
				else:
					self.movieType = 0
				self.getMovieList(self.movieType)
				if self.moviedict:
					self.movie_changed()
		except Exception as ex:
			write_log('infoKeyPressed : ' + str(ex))

	def getMovieList(self, typ=0):
		currentList = []
		mlist = []
		try:
			for k in self.moviedict:
				for v in self.moviedict[k]:
					if 'files' in self.moviedict[k][v]:
						for file in self.moviedict[k][v]['files']:
							mlist.append(file)
			if mlist:
				mlist = [t for t in (set(tuple(i) for i in mlist))]
				if typ == 0:
					mlist.sort(key=lambda x: x[1], reverse=True)
					mlist = mlist[:self.recordingsCount.value]
				else:
					mlist.sort(key=lambda x: x[2], reverse=False)
				for item in mlist:
					image = getImageFile(getPictureDir() + self.movieImageType, item[2])
					if image is None:
						image = self.movieSubstituteImage
					if len(item) > 7:
						itm = MovieEntry(item[0], item[1], item[2], eServiceReference(item[3]), image, False, self.getProgress(item[0], item[4]), item[6], item[7])
					else:
						itm = MovieEntry(item[0], item[1], item[2], eServiceReference(item[3]), image, False, self.getProgress(item[0], item[4]), item[6])
					currentList.append((itm,))
				del mlist
			if currentList:
				self.movieListLen = len(currentList)
				self["movieList"].setlist(currentList)
				self["movieList"].movetoIndex(0)
				self["moviesInfo"].setText(str(self["movieList"].getCurrentIndex() + 1) + '/' + str(self.movieListLen))
				del currentList
				self["moviesText"].setTXT(typ)
			else:
				self.moviedict = None
		except Exception as ex:
			self.moviedict = None
			write_log("getMovieList : " + str(ex))

	def getChannelList(self, bouquets, typ=0):
		self.currentBouquet = bouquets
		self.channelList = []
		mask = (eServiceReference.isMarker | eServiceReference.isDirectory)
		self.idx = 0
		id = 0
		number = 0
		if typ == 4:
			favs = set()
			sList = []
			for key, value in self.myFavourites['titles'].items():
				for fav in value:
					favs.add((fav[0], str(fav[1])))
			for k, v in self.myFavourites.items():
				if k != 'titles':
					for fav in v:
						favs.add((fav[0], str(fav[1])))
			for favourite in favs:
				event = self.epgcache.lookupEventId(eServiceReference(str(favourite[1])), int(favourite[0]))
				if event:
					if str(favourite[1]) == self.current_service_ref:
						self.idx = id
					id += 1
					picon = self.findPicon(str(favourite[1]), None)
					if picon is None:
						picon = imgpath + 'folder.png'

					if int(event.getDuration()) > 0:
						_progress = (int(time()) - event.getBeginTime()) * 100 / event.getDuration()
					else:
						_progress = 0

					image = None
					name = ''
					hasTrailer = None
					evt = self.db.getliveTV(event.getEventId(), event.getEventName(), event.getBeginTime())
					if evt:
						if evt[0][16].endswith('mp4'):
							hasTrailer = evt[0][16]
					if hasTrailer is None:
						dbdata = self.db.getTitleInfo(convert2base64(event.getEventName()))
						if dbdata and dbdata[7].endswith('mp4'):
							hasTrailer = dbdata[7]
					if self.channelImageType in ["poster", "poster/thumbnails", "cover", "cover/thumbnails"]:
						if evt:
							if evt[0][3] != '':
								image = getImageFile(getPictureDir() + self.channelImageType, evt[0][3])
								name = evt[0][3]
						if image is None:
							image = getImageFile(getPictureDir() + self.channelImageType, event.getEventName())

					cleanname = str(event.getEventName()).strip().replace(".", "").replace(":", "").replace("-", "").replace("  ", " ").upper()
					hasTimer = False
					if cleanname in self.timers or str(event.getEventId()) in self.timers or name in self.timers:
						hasTimer = True
					number = ''
					servicename = ''
					bouquet = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet'
					for key, value in self.channelNumbers.items():
						if str(favourite[1]) in value:
							number = self.channelNumbers[key].get(str(favourite[1]), 0)[0]
							servicename = self.channelNumbers[key].get(str(favourite[1]), '')[1]
							bouquet = self.channelNumbers[key].get(str(favourite[1]), '')[2]
							break
					sList.append((str(favourite[1]), event.getEventId(), servicename, event.getEventName(), '', '', _progress, picon, image, bouquet, hasTimer, number, event.getBeginTime(), hasTrailer))

			sList.sort(key=lambda x: x[12], reverse=False)
			for item in sList:
				itm = ChannelEntry(item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7], item[8], item[9], item[10], item[11], item[12], item[13])
				self.channelList.append((itm,))
		else:
			for bouquet in bouquets:
				root = eServiceReference(str(bouquet[0]))
				serviceHandler = eServiceCenter.getInstance()
				ret = serviceHandler.list(root).getContent("SN", True)

				for (serviceref, servicename) in ret:
					if typ != 3:
						t = int(time())
					else:
						now = localtime(time())
						dt = datetime.datetime(now.tm_year, now.tm_mon, now.tm_mday, self.primeTimeStart.value[0], self.primeTimeStart.value[1])
						if time() > mktime(dt.timetuple()):
							dt += timedelta(days=1)
						t = int(mktime(dt.timetuple()))
					if not self.epgcache.startTimeQuery(eServiceReference(serviceref), t):
						event = None
						if typ == 0:  # Alle laufenden Sendungen
							event = self.epgcache.getNextTimeEntry()
						elif typ == 1:  # nächsten Sendungen
							event = self.epgcache.getNextTimeEntry()
							event = self.epgcache.getNextTimeEntry()
						elif typ == 2:  # gerade gestartet oder starten gleich
							event_now = self.epgcache.getNextTimeEntry()
							if int(time() - event_now.getBeginTime()) < (self.maxEventAge.value * 60):
								event = event_now
							else:
								event_next = self.epgcache.getNextTimeEntry()
								if int(event_next.getBeginTime() - time()) < (self.maxEventStart.value * 60):
									event = event_next
						else:  # Prime-Time
							event = self.epgcache.getNextTimeEntry()
						if event:
							if serviceref == self.current_service_ref:
								self.idx = id
							id += 1
							picon = self.findPicon(serviceref, servicename)
							if picon is None:
								picon = imgpath + 'folder.png'

							if int(event.getDuration()) > 0:
								_progress = (int(time()) - event.getBeginTime()) * 100 / event.getDuration()
							else:
								_progress = 0

							image = None
							name = ''
							hasTrailer = None
							evt = self.db.getliveTV(event.getEventId(), event.getEventName(), event.getBeginTime())
							if evt:
								if evt[0][16].endswith('mp4'):
									hasTrailer = evt[0][16]
							if self.channelImageType in ["poster", "poster/thumbnails", "cover", "cover/thumbnails"]:
								if evt:
									if evt[0][3] != '':
										image = getImageFile(getPictureDir() + self.channelImageType, evt[0][3])
										name = evt[0][3]
								if image is None:
									image = getImageFile(getPictureDir() + self.channelImageType, event.getEventName())

							cleanname = str(event.getEventName()).strip().replace(".", "").replace(":", "").replace("-", "").replace("  ", " ").upper()
							hasTimer = False
							if cleanname in self.timers or str(event.getEventId()) in self.timers or name in self.timers:
								hasTimer = True
							try:
								number = self.channelNumbers[bouquet[1]].get(serviceref, 0)[0]
							except:
								number = ""
							itm = ChannelEntry(serviceref, event.getEventId(), servicename, event.getEventName(), '', '', _progress, picon, image, bouquet[0], hasTimer, number, event.getBeginTime(), hasTrailer)
							self.channelList.append((itm,))
		self.channelListLen = len(self.channelList)
		if self.channelList:
			self["channelsText"].setTXT(typ)
		else:
			self["channelsText"].setText("keine Ergebnisse gefunden")

	def buildMovieList(self, entrys):
		try:
			maxLength = self.movieParameter[2]
			if len(entrys.name) > maxLength:
				name = str(entrys.name)[:maxLength] + '...'
			else:
				name = entrys.name
			self.picloader = PicLoader(int(self.movieParameter[0]), int(self.movieParameter[1]))
			image = self.picloader.load(entrys.image)
			self.picloader.destroy()

			ret = [entrys]
			ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.movieParameter[17][0], self.movieParameter[17][1], self.movieParameter[17][0], self.movieParameter[17][1], self.movieParameter[17][2], self.movieParameter[17][3], self.movieParameter[17][2], self.movieParameter[17][3], image, None, None, BT_SCALE))
			for covering in self.movieListCoverings:
				ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, covering[0], covering[1], covering[0], covering[1], covering[2], covering[3], covering[2], covering[3], self.shaper, None, None, BT_SCALE))
			ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.movieParameter[19][0], self.movieParameter[19][1], self.movieParameter[19][0], self.movieParameter[19][1], self.movieParameter[19][2], self.movieParameter[19][3], self.movieParameter[19][2], self.movieParameter[19][3], self.movieParameter[19][5], self.movieParameter[19][5], self.movieListFontOrientation, name, skin.parseColor(self.movieParameter[6]).argb(), skin.parseColor(self.movieParameter[7]).argb()))
			ret.append((eWallPythonMultiContent.TYPE_PROGRESS, eWallPythonMultiContent.SHOW_ALWAYS, self.movieParameter[24][0], self.movieParameter[24][1], self.movieParameter[24][0], self.movieParameter[24][1], self.movieParameter[24][2], self.movieParameter[24][3], self.movieParameter[24][2], self.movieParameter[24][3], entrys.progress, self.movieParameter[13], skin.parseColor(self.movieParameter[9]).argb(), skin.parseColor(self.movieParameter[11]).argb(), skin.parseColor(self.movieParameter[10]).argb(), skin.parseColor(self.movieParameter[12]).argb()))
			return ret
		except Exception as ex:
			write_log("setMovieEntry : " + str(ex))
			return [entrys,
								(eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, 2, 2, 2, 2, 96, 96, 96, 96, 0, 0, RT_WRAP | RT_HALIGN_CENTER | RT_VALIGN_CENTER, str(ex), skin.parseColor(self.movieParameter[6]).argb(), skin.parseColor(self.movieParameter[7]).argb()),
								]

	def buildChannelList(self, entrys):
		try:
			maxLength = self.channelParameter[2]
			if len(entrys.servicename) > maxLength:
				entrys.servicename = str(entrys.servicename)[:maxLength] + '...'
			if len(entrys.title) > maxLength:
				title = str(entrys.title)[:maxLength] + '...'
			else:
				title = entrys.title
			self.picloader = PicLoader(int(self.channelParameter[0]), int(self.channelParameter[1]))
			if entrys.image:
				image = self.picloader.load(entrys.image)
			else:
				if self.channelSubstituteImage == "replaceWithPicon":
					image = LoadPixmap(str(entrys.picon))  # self.picloader.load(entrys.picon)
				else:
					image = self.picloader.load(self.channelSubstituteImage)
			self.picloader.destroy()
#			self.picloader = PicLoader(100, 60)
			picon = LoadPixmap(str(entrys.picon))  # self.picloader.load(entrys.picon)
#			self.picloader.destroy()

			ret = [entrys]
			ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[17][0], self.channelParameter[17][1], self.channelParameter[17][0], self.channelParameter[17][1], self.channelParameter[17][2], self.channelParameter[17][3], self.channelParameter[17][2], self.channelParameter[17][3], image, None, None, BT_SCALE))
			for covering in self.channelListCoverings:
				ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, covering[0], covering[1], covering[0], covering[1], covering[2], covering[3], covering[2], covering[3], self.shaper, None, None, BT_SCALE))
			ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[21][0], self.channelParameter[21][1], self.channelParameter[21][0], self.channelParameter[21][1], self.channelParameter[21][2], self.channelParameter[21][3], self.channelParameter[21][2], self.channelParameter[21][3], picon, None, None, BT_SCALE))
			ret.append((eWallPythonMultiContent.TYPE_PROGRESS, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[24][0], self.channelParameter[24][1], self.channelParameter[24][0], self.channelParameter[24][1], self.channelParameter[24][2], self.channelParameter[24][3], self.channelParameter[24][2], self.channelParameter[24][3], entrys.progress, self.channelParameter[13], skin.parseColor(self.channelParameter[9]).argb(), skin.parseColor(self.channelParameter[11]).argb(), skin.parseColor(self.channelParameter[10]).argb(), skin.parseColor(self.channelParameter[12]).argb()))
			if entrys.hasTimer and fileExists(self.channelParameter[15]):
				ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[19][0] + self.channelParameter[19][4], self.channelParameter[19][1], self.channelParameter[19][0] + self.channelParameter[19][4], self.channelParameter[19][1], self.channelParameter[19][2], self.channelParameter[19][3], self.channelParameter[19][2], self.channelParameter[19][3], self.channelParameter[19][5], self.channelParameter[19][5], self.channelListFontOrientation, str(entrys.number) + ' ' + entrys.servicename, skin.parseColor(self.channelParameter[6]).argb(), skin.parseColor(self.channelParameter[7]).argb()))
				ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[20][0] + self.channelParameter[20][4], self.channelParameter[20][1], self.channelParameter[20][0] + self.channelParameter[20][4], self.channelParameter[20][1], self.channelParameter[20][2], self.channelParameter[20][3], self.channelParameter[20][2], self.channelParameter[20][3], self.channelParameter[20][5], self.channelParameter[20][5], self.channelListFontOrientation, title, skin.parseColor(self.channelParameter[6]).argb(), skin.parseColor(self.channelParameter[7]).argb()))
				ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[18][0], self.channelParameter[18][1], self.channelParameter[18][0], self.channelParameter[18][1], self.channelParameter[18][2], self.channelParameter[18][3], self.channelParameter[18][2], self.channelParameter[18][3], LoadPixmap(self.channelParameter[15]), None, None, BT_SCALE))
			else:
				ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[19][0], self.channelParameter[19][1], self.channelParameter[19][0], self.channelParameter[19][1], self.channelParameter[19][2], self.channelParameter[19][3], self.channelParameter[19][2], self.channelParameter[19][3], self.channelParameter[19][5], self.channelParameter[19][5], self.channelListFontOrientation, str(entrys.number) + ' ' + entrys.servicename, skin.parseColor(self.channelParameter[6]).argb(), skin.parseColor(self.channelParameter[7]).argb()))
				ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[20][0], self.channelParameter[20][1], self.channelParameter[20][0], self.channelParameter[20][1], self.channelParameter[20][2], self.channelParameter[20][3], self.channelParameter[20][2], self.channelParameter[20][3], self.channelParameter[20][5], self.channelParameter[20][5], self.channelListFontOrientation, title, skin.parseColor(self.channelParameter[6]).argb(), skin.parseColor(self.channelParameter[7]).argb()))
			return ret

			write_log("error in entrys : " + str(entrys))
			return [entrys,
								(eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, 2, 2, 2, 2, 96, 96, 96, 96, 0, 0, RT_WRAP | RT_HALIGN_CENTER | RT_VALIGN_CENTER, 'Das war wohl nix', skin.parseColor(self.channelParameter[6]).argb(), skin.parseColor(self.channelParameter[7]).argb()),
								]
		except Exception as ex:
			write_log('Fehler in buildChannelList : ' + str(ex))

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
			for piconpath in piconpaths:
				pngname = os.path.join(piconpath, service + ".png")
				if os.path.isfile(pngname):
					return pngname
		if serviceName is not None:
			for piconpath in piconpaths:
				pngname = os.path.join(piconpath, serviceName + ".png")
				if os.path.isfile(pngname):
					return pngname
		return None

	def key_menu_handler(self):
		self.session.openWithCallback(self.return_from_setup, MySetup)

	def return_from_setup(self):
		pass

	def key_pvr_handler(self):
		if self.moviedict:
			if self.activeList == "TV":
				self["channelList"].setSelectionEnable(False)
				self["movieList"].setSelectionEnable(True)
				self["key_green"].setText("zeige Aufnahmeliste")
				self["channelsText"].setForegroundColorNum(0)
				self["channelsText"].setBackgroundColorNum(0)
				self["moviesText"].setForegroundColorNum(1)
				self["moviesText"].setBackgroundColorNum(1)
				self["channelsInfo"].setForegroundColorNum(0)
				self["channelsInfo"].setBackgroundColorNum(0)
				self["moviesInfo"].setForegroundColorNum(1)
				self["moviesInfo"].setBackgroundColorNum(1)
				self["timeInfo"].setPosition(1)
				self.activeList = "Recordings"
				self.movie_changed()
			else:
				self["channelList"].setSelectionEnable(True)
				self["movieList"].setSelectionEnable(False)
				self["key_green"].setText("zeige Kanalliste")
				self["channelsText"].setForegroundColorNum(1)
				self["channelsText"].setBackgroundColorNum(1)
				self["moviesText"].setForegroundColorNum(0)
				self["moviesText"].setBackgroundColorNum(0)
				self["channelsInfo"].setForegroundColorNum(1)
				self["channelsInfo"].setBackgroundColorNum(1)
				self["moviesInfo"].setForegroundColorNum(0)
				self["moviesInfo"].setBackgroundColorNum(0)
				self["timeInfo"].setPosition(0)
				self.activeList = "TV"
				self.channel_changed()
			self["channelList"].refresh()
			self["movieList"].refresh()

	def key_ok_handler(self):
		if self.activeList == "TV":
			selection = self["channelList"].getcurrentselection()
			sRef = selection.serviceref
			if not "::" in sRef:
				bouquet = selection.bouquet

				if (ServiceReference(self.CHANSEL.servicelist.getRoot()).getPath()) != bouquet.split(':')[-1]:
					self.CHANSEL.clearPath()
					if ServiceReference(self.CHANSEL.bouquet_root).getPath() != bouquet.split(':')[-1]:
						self.CHANSEL.enterPath(self.CHANSEL.bouquet_root)
					self.CHANSEL.enterPath(eServiceReference(bouquet))
				self.CHANSEL.setCurrentSelection(eServiceReference(sRef))
				self.CHANSEL.zap()

				self.CHANSEL.addToHistory(eServiceReference(sRef))
				self.key_red_handler()
		else:
			sRef = self["movieList"].getcurrentselection().service
			self.session.open(MoviePlayer, sRef)

	def key_play_handler(self):
		try:
			if self.activeList == "TV":
				selected_element = self["channelList"].l.getCurrentSelection()[0]
				if selected_element:
					if selected_element.hasTrailer:
						sRef = eServiceReference(4097, 0, str(selected_element.hasTrailer))
						sRef.setName(str(selected_element.title))
						self.session.open(MoviePlayer, sRef)
			else:
				selected_element = self["movieList"].l.getCurrentSelection()[0]
				if selected_element:
					if selected_element.hasTrailer:
						sRef = eServiceReference(4097, 0, str(selected_element.hasTrailer))
						sRef.setName(str(selected_element.name))
						self.session.open(MoviePlayer, sRef)
		except Exception as ex:
			write_log("key_play : " + str(ex))

	def key_red_handler(self):
		clearMem("MediaHub")
		global active
		active = False
		self.close()

	def key_green_handler(self):
		if self.activeList == "TV":
			self.session.open(AdvancedEventLibraryChannelSelection.AdvancedEventLibraryChannelSelection, self["channelList"].getcurrentselection().serviceref)
		else:
			self.session.open(AdvancedEventLibrarySimpleMovieWall.AdvancedEventLibrarySimpleMovieWall, self.viewType.value)

	def key_yellow_handler(self):
		choices, idx = (self.userBouquets, 0)
		keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
		self.session.openWithCallback(self.yellowCallBack, ChoiceBox, title='Bouquetauswahl', keys=keys, list=choices, selection=idx)

	def yellowCallBack(self, ret=None):
		if ret:
			self["key_yellow"].setText(ret[0])
			if ret[0] == "Alle Bouquets":
				self.getChannelList(self.tvbouquets, self.channelType)
			else:
				for bouquet in self.tvbouquets:
					if ret[0] == bouquet[1]:
						self.getChannelList([bouquet], self.channelType)
						break
			if self.channelList:
				self["channelList"].setlist(self.channelList)
				self["channelList"].movetoIndex(self.idx)
				self["channelList"].refresh()
				self.channel_changed()

	def key_blue_handler(self):
		if self.activeList == "TV":
			selection = self["channelList"].getcurrentselection()
			eventName = (selection.title, selection.eit)
			self.session.openWithCallback(self.channel_changed, AdvancedEventLibrarySystem.Editor, eventname=eventName)
		else:
			selection = self["movieList"].getcurrentselection()
			self.session.openWithCallback(self.movie_changed, AdvancedEventLibrarySystem.Editor, service=selection.service, eventname=None)

	def key_right_handler(self):
		if self.switchWithPVR:
			if self.activeList == "TV":
				self.controlChannelList(self.channelListControl["right"])
			else:
				self.controlMovieList(self.movieListControl["right"])
		else:
			self.controlChannelList(self.channelListControl["right"])
			self.controlMovieList(self.movieListControl["right"])

	def key_left_handler(self):
		if self.switchWithPVR:
			if self.activeList == "TV":
				self.controlChannelList(self.channelListControl["left"])
			else:
				self.controlMovieList(self.movieListControl["left"])
		else:
			self.controlChannelList(self.channelListControl["left"])
			self.controlMovieList(self.movieListControl["left"])

	def key_down_handler(self):
		if self.switchWithPVR:
			if self.activeList == "TV":
				self.controlChannelList(self.channelListControl["down"])
			else:
				self.controlMovieList(self.movieListControl["down"])
		else:
			self.controlChannelList(self.channelListControl["down"])
			self.controlMovieList(self.movieListControl["down"])

	def key_up_handler(self):
		if self.switchWithPVR:
			if self.activeList == "TV":
				self.controlChannelList(self.channelListControl["up"])
			else:
				self.controlMovieList(self.movieListControl["up"])
		else:
			self.controlChannelList(self.channelListControl["up"])
			self.controlMovieList(self.movieListControl["up"])

	def key_channel_up_handler(self):
		if self.switchWithPVR:
			if self.activeList == "TV":
				self.controlChannelList(self.channelListControl["pageUp"])
			else:
				self.controlMovieList(self.movieListControl["pageUp"])
		else:
			self.controlChannelList(self.channelListControl["pageUp"])
			self.controlMovieList(self.movieListControl["pageUp"])

	def key_channel_down_handler(self):
		if self.switchWithPVR:
			if self.activeList == "TV":
				self.controlChannelList(self.channelListControl["pageDown"])
			else:
				self.controlMovieList(self.movieListControl["pageDown"])
		else:
			self.controlChannelList(self.channelListControl["pageDown"])
			self.controlMovieList(self.movieListControl["pageDown"])

	def controlChannelList(self, what):
		if what == "right":
			old_idx = int(self['channelList'].getCurrentIndex())
			if old_idx == self.channelListLen - 1:
				self['channelList'].movetoIndex(0)
			else:
				self['channelList'].right()
				new_idx = int(self['channelList'].getCurrentIndex())
				if new_idx <= old_idx:
					if (old_idx + 1) >= self.channelListLen:
						dest = 0
					else:
						dest = old_idx + 1
					self['channelList'].movetoIndex(dest)
		elif what == "left":
			old_idx = int(self['channelList'].getCurrentIndex())
			if old_idx == 0:
				dest = self.channelListLen - 1
				self['channelList'].movetoIndex(dest)
			else:
				self['channelList'].left()
				new_idx = int(self['channelList'].getCurrentIndex())
				if new_idx >= old_idx:
					if (new_idx - 1) < 0:
						dest = self.channelListLen - 1
					else:
						dest = old_idx - 1
					self['channelList'].movetoIndex(dest)
		elif what == "down":
			old_idx = int(self['channelList'].getCurrentIndex())
			if old_idx == self.channelListLen - 1:
				self['channelList'].movetoIndex(0)
			else:
				self['channelList'].down()
				new_idx = int(self['channelList'].getCurrentIndex())
				if new_idx <= old_idx:
					if (new_idx + self.channelParameter[14]) >= self.channelListLen:
						dest = 0
					else:
						dest = new_idx + self.channelParameter[14]
					self['channelList'].movetoIndex(dest)
		elif what == "up":
			old_idx = int(self['channelList'].getCurrentIndex())
			if old_idx == 0:
				dest = self.channelListLen - 1
				self['channelList'].movetoIndex(dest)
			else:
				self['channelList'].up()
				new_idx = int(self['channelList'].getCurrentIndex())
				if new_idx >= old_idx:
					if (new_idx - self.channelParameter[14]) < 0:
						dest = self.channelListLen - 1
					else:
						dest = new_idx - self.channelParameter[14]
					self['channelList'].movetoIndex(dest)
		elif what == "pageDown":
			self['channelList'].prevPage()
		elif what == "pageUp":
			self['channelList'].nextPage()
		if what in ["up", "down", "left", "right", "pageUp", "pageDown"]:
			self["channelList"].refresh()
			self.channel_changed()
			self["channelsInfo"].setText(str(self["channelList"].getCurrentIndex() + 1) + '/' + str(self.channelListLen))

	def controlMovieList(self, what):
		if what == "right":
			old_idx = int(self['movieList'].getCurrentIndex())
			if old_idx == self.movieListLen - 1:
				self['movieList'].movetoIndex(0)
			else:
				self['movieList'].right()
				new_idx = int(self['movieList'].getCurrentIndex())
				if new_idx <= old_idx:
					if (old_idx + 1) >= self.movieListLen:
						dest = 0
					else:
						dest = old_idx + 1
					self['movieList'].movetoIndex(dest)
		elif what == "left":
			old_idx = int(self['movieList'].getCurrentIndex())
			if old_idx == 0:
				dest = self.movieListLen - 1
				self['movieList'].movetoIndex(dest)
			else:
				self['movieList'].left()
				new_idx = int(self['movieList'].getCurrentIndex())
				if new_idx >= old_idx:
					if (new_idx - 1) < 0:
						dest = self.movieListLen - 1
					else:
						dest = old_idx - 1
					self['movieList'].movetoIndex(dest)
		elif what == "down":
			old_idx = int(self['movieList'].getCurrentIndex())
			if old_idx == self.movieListLen - 1:
				self['movieList'].movetoIndex(0)
			else:
				self['movieList'].down()
				new_idx = int(self['movieList'].getCurrentIndex())
				if new_idx <= old_idx:
					if (new_idx + self.movieParameter[14]) >= self.movieListLen:
						dest = 0
					else:
						dest = new_idx + self.movieParameter[14]
					self['movieList'].movetoIndex(dest)
		elif what == "up":
			old_idx = int(self['movieList'].getCurrentIndex())
			if old_idx == 0:
				dest = self.movieListLen - 1
				self['movieList'].movetoIndex(dest)
			else:
				self['movieList'].up()
				new_idx = int(self['movieList'].getCurrentIndex())
				if new_idx >= old_idx:
					if (new_idx - self.movieParameter[14]) < 0:
						dest = self.movieListLen - 1
					else:
						dest = new_idx - self.movieParameter[14]
					self['movieList'].movetoIndex(dest)
		elif what == "pageDown":
			self['movieList'].prevPage()
		elif what == "pageUp":
			self['movieList'].nextPage()
		if what in ["up", "down", "left", "right", "pageUp", "pageDown"]:
			self["movieList"].refresh()
			self.movie_changed()
			self["moviesInfo"].setText(str(self["movieList"].getCurrentIndex() + 1) + '/' + str(self.movieListLen))

	def channel_changed(self):
		try:
			events = []
			selected_channel = self["channelList"].getcurrentselection()
			if selected_channel:
				sRef = str(selected_channel.serviceref)
				eit = int(selected_channel.eit)
				self.current_event = self.epgcache.lookupEventId(eServiceReference(sRef), eit)
				self["Service"].newService(eServiceReference(sRef), self.current_event)
				if self.channelType in [0, 1, 2]:
					if int(selected_channel.begin) > int(time()):
						beginTime = int((int(selected_channel.begin) - int(time())) / 60)
					else:
						beginTime = int((int(time()) - int(selected_channel.begin)) / 60)
					_timeInfo = str(beginTime) + " Min."
					if int(selected_channel.begin) > int(time()):
						timeText = "beginnt in " + _timeInfo
					else:
						timeText = "begann vor " + _timeInfo
					self["timeInfo"].setText(timeText.replace('beginnt in 0 Min.', 'beginnt jetzt').replace('begann vor 0 Min.', 'beginnt jetzt'))
				elif self.channelType == 3:
					_timeInfo = "beginnt um %s Uhr" % (strftime("%H:%M", localtime(selected_channel.begin)))
					self["timeInfo"].setText(_timeInfo)
				else:
					_timeInfo = "beginnt am %s Uhr" % (strftime("%a, %H:%M", localtime(selected_channel.begin)))
					self["timeInfo"].setText(self.correctweekdays(_timeInfo))
				if selected_channel.hasTrailer:
					self["trailer"].show()
				else:
					self["trailer"].hide()
		except Exception as ex:
			write_log("channel_changed : " + str(ex))
			self["Service"].newService(None)

	def movie_changed(self):
		try:
			cs = self['movieList'].getcurrentselection()
			info = eServiceCenter.getInstance().info(cs.service)
			if info:
				self.current_event = info.getEvent(cs.service)
				if self.current_event:
					self["Service"].newService(cs.service, self.current_event)
				else:
					self["Service"].newService(cs.service)
			beginTime = datetime.datetime.fromtimestamp(cs.date)
			_timeInfo = beginTime.strftime("%d.%m.%Y - %H:%M")
			timeText = "Aufnahme vom " + _timeInfo
			self["timeInfo"].setText(timeText)
			if cs.hasTrailer:
				self["trailer"].show()
			else:
				self["trailer"].hide()
		except Exception as ex:
			write_log("movie_changed : " + str(ex))
			self["Service"].newService(None)

	def key_info_handler(self):
		from Screens.EventView import EventViewSimple, EventViewMovieEvent
		if self.activeList == "TV":
			selected_event = self["channelList"].getcurrentselection()
			if selected_event:
				sRef = str(selected_event.serviceref)
				if self.epgViewType.value == "EPGSelection":
					from Screens.EpgSelection import EPGSelection
					self.session.open(EPGSelection, sRef)
				else:
					if self.current_event:
						self.session.open(EventViewSimple, self.current_event, ServiceReference(sRef))
		else:
			cs = self['movieList'].getcurrentselection()
			mlen = ""
			info = eServiceCenter.getInstance().info(cs.service)
			if info:
				evt = info.getEvent(cs.service)
				if evt:
					self.session.open(EventViewSimple, evt, ServiceReference(cs.service))
				else:
					if info.getLength(cs.service) > 0:
						mlen = str(info.getLength(cs.service) / 60) + ' min'
					name, ext_desc = self.getExtendedMovieDescription(cs.service)
					self.session.open(EventViewMovieEvent, name=name, ext_desc=ext_desc, dur=mlen, service=cs.service)

	def getExtendedMovieDescription(self, ref):
		extended_desc = ""
		name = ""
		serviceHandler = eServiceCenter.getInstance()
		info = serviceHandler.info(ref)
		if info:
			evt = info.getEvent(ref)
			if evt:
				name = evt.getEventName()
				extended_desc = evt.getExtendedDescription()
		f = None
		if extended_desc != "":
			extended_desc += "\n\n"
		extensions = (".txt", ".info")
		info_file = os.path.realpath(ref.getPath())
		name = os.path.basename(info_file)
		ext_pos = name.rfind('.')
		if ext_pos > 0:
			name = (name[:ext_pos]).replace("_", " ")
		else:
			name = name.replace("_", " ")
		for ext in extensions:
			if os.path.exists(info_file + ext):
				f = info_file + ext
				break
		if not f:
			ext_pos = info_file.rfind('.')
			name_len = len(info_file)
			ext_len = name_len - ext_pos
			if ext_len <= 5:
				info_file = info_file[:ext_pos]
				for ext in extensions:
					if os.path.exists(info_file + ext):
						f = info_file + ext
						break
		if f:
			try:
				with open(f, "r") as txtfile:
					extended_desc = txtfile.read()
			except IOError:
				pass
		return (name, extended_desc)

	def getMovieLen(self, moviename):
		if fileExists(moviename + ".cuts"):
			try:
				f = open(moviename + ".cuts", "rb")
				packed = f.read()
				f.close()
				while len(packed) > 0:
					packedCue = packed[:12]
					packed = packed[12:]
					cue = struct.unpack('>QI', packedCue)
					if cue[1] == 5:
						movie_len = cue[0] / 90000
						return movie_len
			except Exception as ex:
				write_log("getMovieLen : " + str(ex))
		return 0

	def getProgress(self, moviename, movie_len):
		if movie_len <= 0:
			movie_len = self.getMovieLen(moviename)
		cut_list = []
		if fileExists(moviename + ".cuts"):
			try:
				f = open(moviename + ".cuts", "rb")
				packed = f.read()
				f.close()

				while len(packed) > 0:
					packedCue = packed[:12]
					packed = packed[12:]
					cue = struct.unpack('>QI', packedCue)
					cut_list.append(cue)
			except Exception as ex:
				movie_len = -1
				write_log(ex)

		last_end_point = None

		if len(cut_list):
			for (pts, what) in cut_list:
				if what == 3:
					last_end_point = pts / 90000

		if movie_len > 0 and last_end_point is not None:
			play_progress = (last_end_point * 100) / movie_len
		else:
			play_progress = 0

		if play_progress > 100:
			play_progress = 100
		return play_progress

	def correctweekdays(self, itm):
		_itm = str(itm)
		_itm = _itm.replace("Mon", "Mo").replace("Tue", "Di").replace("Wed", "Mi").replace("Thu", "Do").replace("Fri", "Fr").replace("Sat", "Sa").replace("Sun", "So")
		return _itm

####################################################################################


class MySetup(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.skinName = ["AEL-Media-Hub-Setup", "Setup"]
		self.title = "AEL-Media-Hub-Setup"

		self.setup_title = "AEL-Media-Hub-Setup"
		self["title"] = StaticText(self.title)

		self["key_red"] = StaticText("Beenden")
		self["key_green"] = StaticText("Speichern")

		config.plugins.AdvancedEventLibrary = ConfigSubsection()
		self.myBouquet = config.plugins.AdvancedEventLibrary.ChannelSelectionStartBouquet = ConfigSelection(default="Alle Bouquets", choices=['Alle Bouquets', 'aktuelles Bouquet'])
		self.epgViewType = config.plugins.AdvancedEventLibrary.EPGViewType = ConfigSelection(default="EventView", choices=['EPGSelection', 'EventView'])
		self.recordingsCount = config.plugins.AdvancedEventLibrary.RecordingsCount = ConfigInteger(default=12, limits=(5, 100))
		self.maxEventAge = config.plugins.AdvancedEventLibrary.MaxEventAge = ConfigInteger(default=5, limits=(0, 60))
		self.maxEventStart = config.plugins.AdvancedEventLibrary.MaxEventStart = ConfigInteger(default=10, limits=(1, 60))
		self.channelStartType = config.plugins.AdvancedEventLibrary.MediaHubStartType = ConfigSelection(default="0", choices=[("0", "aktuelles Programm"), ("1", "nächste Sendungen"), ("2", "gerade begonnen/startet gleich"), ("3", "Prime-Time-Programm"), ("4", "Empfehlungen")])

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
			self.configlist.append(getConfigListEntry("Einstellungen", ConfigDescription()))
			self.configlist.append(getConfigListEntry("Startbouquet", self.myBouquet))
			self.configlist.append(getConfigListEntry("Startansicht im Kanalbereich", self.channelStartType))
			self.configlist.append(getConfigListEntry("EPG-Taste öffnet", self.epgViewType))
			self.configlist.append(getConfigListEntry("zeige Events gestartet vor maximal (Minuten)", self.maxEventAge))
			self.configlist.append(getConfigListEntry("zeige Events die starten in maximal (Minuten)", self.maxEventStart))
			self.configlist.append(getConfigListEntry("Anzahl neuester Aufnahmen", self.recordingsCount))
		except Exception as ex:
			write_log("Fehler in buildConfigList : " + str(ex))

	def changedEntry(self):
		self.buildConfigList()
		cur = self["config"].getCurrent()
		self["config"].setList(self.configlist)
		if cur and cur is not None:
			self["config"].updateConfigListView(cur)

	def do_close(self):
		restartbox = self.session.openWithCallback(self.restartGUI, MessageBox, _("GUI needs a restart to apply new configuration.\nDo you want to restart the GUI now ?"), MessageBox.TYPE_YESNO)
		restartbox.setTitle(_("GUI needs a restart."))

	def restartGUI(self, answer):
		if answer is True:
			for x in self["config"].list:
				x[1].save()
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
