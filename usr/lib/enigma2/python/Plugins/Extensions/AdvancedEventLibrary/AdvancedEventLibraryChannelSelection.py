# coding=utf-8
from __future__ import absolute_import
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
from time import time, localtime, mktime
import datetime
import os
import re
import json
import NavigationInstance
from html.parser import HTMLParser
from skin import loadSkin
from RecordTimer import RecordTimerEntry, RecordTimer, parseEvent, AFTEREVENT
from enigma import eEPGCache, iServiceInformation, eServiceReference, eServiceCenter, ePixmap, loadJPG
from ServiceReference import ServiceReference
from enigma import eTimer, eListbox, ePicLoad, eLabel, eListboxPythonMultiContent, gFont, eRect, eSize, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_VALIGN_BOTTOM, RT_WRAP, BT_SCALE, BT_FIXRATIO
from threading import Timer, Thread
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry, ConfigEnableDisable, \
    ConfigYesNo, ConfigText, ConfigNumber, ConfigSelection, ConfigClock, \
    ConfigDateTime, config, NoSave, ConfigSubsection, ConfigInteger, ConfigIP, configfile, ConfigNothing, ConfigDescription
from Tools.Directories import fileExists
from Components.Sources.Event import Event

from . import AdvancedEventLibrarySystem
from .AdvancedEventLibraryLists import AELBaseWall
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
	AdvancedEventLibrary_log.write(str(logtime) + " : [ChannelSelection] : " + str(svalue) + "\n")
	AdvancedEventLibrary_log.close()


def loadskin(filename):
	path = skinpath + filename
	with open(path, "r") as f:
		skin = f.read()
		f.close()
	return skin


class ChannelEntry():
	def __init__(self, serviceref, eit, servicename, title, timespan, duration, progress, picon, image, bouquet, hasTimer, number, hasTrailer):
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
		self.hasTrailer = hasTrailer

	def __setitem__(self, item, value):
		if item == "image":
			self.image = value
		elif item == "hasTimer":
			self.hasTimer = value

	def __repr__(self):
		return '{%s}' % str(', '.join('%s : %s' % (k, repr(v)) for (k, v) in self.__dict__.iteritems()))


class AdvancedEventLibraryChannelSelection(Screen):
	ALLOW_SUSPEND = True
	skin = str(loadskin("AdvancedEventLibraryChannelSelection.xml"))
#	skin = loadSkin(skinpath + "AdvancedEventLibraryChannelSelection.xml")

	def __init__(self, session, sRef=None):
		global active
		active = True
		self.session = session
		Screen.__init__(self, session)

		self.nameCache = {}
		self.title = "Advanced-Event-Library-ChannelSelection"
		self.skinName = "AdvancedEventLibraryChannelSelection"
		self.db = getDB()
		self.isinit = False
		self.channelList = []
		self.timers = []
		self.channelListLen = 0
		self.eventListLen = 0
		self.activeList = "Channels"
		self.idx = 0
		self.shaper = LoadPixmap('/usr/share/enigma2/AELImages/shaper.png')
		self.switchWithPVR = False

		self.userBouquets = []
		self.userBouquets.append(('Alle Bouquets',))

		config.plugins.AdvancedEventLibrary = ConfigSubsection()
		self.myBouquet = config.plugins.AdvancedEventLibrary.ChannelSelectionStartBouquet = ConfigSelection(default="Alle Bouquets", choices=['Alle Bouquets', 'aktuelles Bouquet'])
		self.channelSelectionEventListDuration = config.plugins.AdvancedEventLibrary.ChannelSelectionEventListDuration = ConfigInteger(default=12, limits=(1, 240))
		self.epgViewType = config.plugins.AdvancedEventLibrary.EPGViewType = ConfigSelection(default="EventView", choices=['EPGSelection', 'EventView'])

		self.CHANSEL = InfoBar.instance.servicelist
		if sRef:
			ref = sRef
		else:
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
				if not "::" in serviceref:
					self.channelNumbers[bouquet[1]][serviceref] = channelNumber
					channelNumber += 1
		self.epgcache = eEPGCache.getInstance()

		self["channelList"] = AELBaseWall()
		self["channelList"].l.setBuildFunc(self.buildChannelList)
		self["eventList"] = AELBaseWall()
		self["eventList"].l.setBuildFunc(self.buildEventList)
		self["trailer"] = Pixmap()

		self["key_red"] = StaticText("Beenden")
		self["key_green"] = StaticText("Timer hinzufügen")
		self["key_yellow"] = StaticText("Bouquetauswahl")  # (self.myBouquet.value)
		self["key_blue"] = StaticText("Advanced-Event-Library")

		self["channelsInfo"] = MultiColorLabel()
		self["eventsInfo"] = MultiColorLabel()

		self["Event"] = Event()
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

	def refreshAll(self):
		if not self.isinit:
			self.channelParameter = self["channelList"].getParameter()
			self.channelImageType = str(self.channelParameter[3])
			self.channelSubstituteImage = str(self.channelParameter[5])
			self.channelListControl = eval(self.channelParameter[22])
			self.channelListCoverings = eval(str(self.channelParameter[23]))
			self.channelListFontOrientation = self.getFontOrientation(self.channelParameter[25])
			self.eventParameter = self["eventList"].getParameter()
			self.eventImageType = str(self.eventParameter[3])
			self.eventSubstituteImage = str(self.eventParameter[5])
			self.eventListControl = eval(self.eventParameter[22])
			self.eventListCoverings = eval(str(self.eventParameter[23]))
			self.eventListFontOrientation = self.getFontOrientation(self.eventParameter[25])

			imgpath = skin.variables.get("EventLibraryImagePath", '/usr/share/enigma2/AELImages/,').replace(',', '')
			ptr = LoadPixmap(os.path.join(imgpath, "play.png"))
			self["trailer"].instance.setPixmap(ptr)

			if self.myBouquet.value == 'Alle Bouquets':
				self.getChannelList(self.tvbouquets)
			else:
				bName = ServiceReference(self.CHANSEL.servicelist.getRoot()).getServiceName()
				bRoot = ServiceReference(self.CHANSEL.servicelist.getRoot()).getPath()
				self.getChannelList([('1:7:1:0:0:0:0:0:0:0:' + bRoot, bName)])
			self["channelList"].setlist(self.channelList)
			self["channelList"].movetoIndex(self.idx)
			self["channelsInfo"].setText(str(self["channelList"].getCurrentIndex() + 1) + '/' + str(self.channelListLen))
			self["channelsInfo"].setForegroundColorNum(1)
			self["channelsInfo"].setBackgroundColorNum(1)
			self.channel_changed()
			self["eventsInfo"].setText(str(self["eventList"].getCurrentIndex() + 1) + '/' + str(self.eventListLen))
			self["eventsInfo"].setForegroundColorNum(0)
			self["eventsInfo"].setBackgroundColorNum(0)

			self.switchWithPVR = self.channelListControl.get('switchControl', False) or self.eventListControl.get('switchControl', False)
			if self.switchWithPVR:
				self["eventList"].setSelectionEnable(False)
			self.isinit = True

	def getChannelList(self, bouquets):
		self.time = time()
		self.channelList = []
		mask = (eServiceReference.isMarker | eServiceReference.isDirectory)
		self.idx = 0
		id = 0
		number = 0
		for bouquet in bouquets:
			root = eServiceReference(str(bouquet[0]))
			serviceHandler = eServiceCenter.getInstance()
			ret = serviceHandler.list(root).getContent("SN", True)

			for (serviceref, servicename) in ret:
				if not "::" in serviceref:
					if serviceref == self.current_service_ref:
						self.idx = id
					id += 1
					events = self.epgcache.lookupEvent(['ITBD', (serviceref, 0, -1, 10)]) or [(0, 'kein EPG!', 0, 0)]
					picon = self.findPicon(serviceref, servicename)
					if picon is None:
						picon = imgpath + 'folder.png'
					beginTime = datetime.datetime.fromtimestamp(events[0][2])
					endTime = datetime.datetime.fromtimestamp(events[0][2] + events[0][3])
					duration = int((events[0][3] - (int(time()) - events[0][2])) / 60)
					_timespan = ""
					if "weekday" in self.channelParameter[27]:
						_timespan += beginTime.strftime("%a. ")
					if "date" in self.channelParameter[27]:
						_timespan += beginTime.strftime("%d.%m. ")
					if "start" in self.channelParameter[27]:
						_timespan += beginTime.strftime("%H:%M")
					if "end" in self.channelParameter[27]:
						_timespan += endTime.strftime("-%H:%M")
					if "duration" in self.channelParameter[27]:
						_timespan += '  ' + str(duration) + ' Min.'
					_duration = str(duration) + ' Min.'
					if int(events[0][3]) > 0:
						_progress = (int(time()) - events[0][2]) * 100 / events[0][3]
					else:
						_progress = 0

					image = None
					name = ''
					hasTrailer = None
					evt = self.db.getliveTV(events[0][0], events[0][1], events[0][2])
					if evt:
						if evt[0][16].endswith('mp4'):
							hasTrailer = evt[0][16]
					if hasTrailer is None:
						dbdata = self.db.getTitleInfo(convert2base64(events[0][1]))
						if dbdata and dbdata[7].endswith('mp4'):
							hasTrailer = dbdata[7]
					if self.channelImageType in ["poster", "poster/thumbnails", "cover", "cover/thumbnails"]:
						if evt:
							if evt[0][3] != '':
								niC = self.nameCache.get(evt[0][3], '')
								if niC != '':
									image = niC
								else:
									image = getImageFile(getPictureDir() + self.channelImageType, evt[0][3])
									if image is not None:
										self.nameCache[evt[0][3]] = str(image)
								name = evt[0][3]
						if image is None:
							niC = self.nameCache.get(events[0][1], '')
							if niC != '':
								image = niC
							else:
								image = getImageFile(getPictureDir() + self.channelImageType, events[0][1])
								if image is not None:
									self.nameCache[events[0][1]] = str(image)

					cleanname = str(events[0][1]).strip().replace(".", "").replace(":", "").replace("-", "").replace("  ", " ").upper()
					hasTimer = False
					if cleanname in self.timers or str(events[0][0]) in self.timers or name in self.timers:
						hasTimer = True
					number = self.channelNumbers[bouquet[1]].get(serviceref, 0)
					itm = ChannelEntry(serviceref, events[0][0], servicename, events[0][1], _timespan, _duration, _progress, picon, image, bouquet[0], hasTimer, number, hasTrailer)
					self.channelList.append((itm,))
		self.channelListLen = len(self.channelList)

	def buildChannelList(self, entrys):
		try:
			maxLength = self.channelParameter[2]
			textHeight = int(self.channelParameter[8])
			textBegin = 100 - textHeight
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
					image = LoadPixmap(entrys.picon)  # self.picloader.load(entrys.picon)
				else:
					image = self.picloader.load(self.channelSubstituteImage)
			self.picloader.destroy()
			picon = LoadPixmap(entrys.picon)  # self.picloader.load(entrys.picon)

			ret = [entrys]
			#rework
			#ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[17][0], self.channelParameter[17][1], self.channelParameter[17][0], self.channelParameter[17][1], self.channelParameter[17][2], self.channelParameter[17][3], self.channelParameter[17][2], self.channelParameter[17][3], image, None, None, BT_SCALE))
			#for covering in self.channelListCoverings:
			#	ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, covering[0], covering[1], covering[0], covering[1], covering[2], covering[3], covering[2], covering[3], self.shaper, None, None, BT_SCALE))
			r  # et.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[21][0], self.channelParameter[21][1], self.channelParameter[21][0], self.channelParameter[21][1], self.channelParameter[21][2], self.channelParameter[21][3], self.channelParameter[21][2], self.channelParameter[21][3], picon, None, None, BT_SCALE))
			#ret.append((eWallPythonMultiContent.TYPE_PROGRESS, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[24][0], self.channelParameter[24][1], self.channelParameter[24][0], self.channelParameter[24][1], self.channelParameter[24][2], self.channelParameter[24][3], self.channelParameter[24][2], self.channelParameter[24][3], entrys.progress, self.channelParameter[13], skin.parseColor(self.channelParameter[9]).argb(), skin.parseColor(self.channelParameter[11]).argb(), skin.parseColor(self.channelParameter[10]).argb(), skin.parseColor(self.channelParameter[12]).argb()))
			#if entrys.hasTimer and fileExists(self.channelParameter[15]):
			#	ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[19][0] + self.channelParameter[19][4], self.channelParameter[19][1], self.channelParameter[19][0] + self.channelParameter[19][4], self.channelParameter[19][1], self.channelParameter[19][2], self.channelParameter[19][3], self.channelParameter[19][2], self.channelParameter[19][3], self.channelParameter[19][5], self.channelParameter[19][5], self.channelListFontOrientation, str(entrys.number) + ' ' + str(entrys.servicename), skin.parseColor(self.channelParameter[6]).argb(), skin.parseColor(self.channelParameter[7]).argb()))
			#	ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[20][0] + self.channelParameter[20][4], self.channelParameter[20][1], self.channelParameter[20][0] + self.channelParameter[20][4], self.channelParameter[20][1], self.channelParameter[20][2], self.channelParameter[20][3], self.channelParameter[20][2], self.channelParameter[20][3], self.channelParameter[20][5], self.channelParameter[20][5], self.channelListFontOrientation, str(title), skin.parseColor(self.channelParameter[6]).argb(), skin.parseColor(self.channelParameter[7]).argb()))
			#	ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[18][0], self.channelParameter[18][1], self.channelParameter[18][0], self.channelParameter[18][1], self.channelParameter[18][2], self.channelParameter[18][3], self.channelParameter[18][2], self.channelParameter[18][3], LoadPixmap(self.channelParameter[15]), None, None, BT_SCALE))
			#else:
			#	ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[19][0], self.channelParameter[19][1], self.channelParameter[19][0], self.channelParameter[19][1], self.channelParameter[19][2], self.channelParameter[19][3], self.channelParameter[19][2], self.channelParameter[19][3], self.channelParameter[19][5], self.channelParameter[19][5], self.channelListFontOrientation, str(entrys.number) + ' ' + str(entrys.servicename), skin.parseColor(self.channelParameter[6]).argb(), skin.parseColor(self.channelParameter[7]).argb()))
			#	ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[20][0], self.channelParameter[20][1], self.channelParameter[20][0], self.channelParameter[20][1], self.channelParameter[20][2], self.channelParameter[20][3], self.channelParameter[20][2], self.channelParameter[20][3], self.channelParameter[20][5], self.channelParameter[20][5], self.channelListFontOrientation, str(title), skin.parseColor(self.channelParameter[6]).argb(), skin.parseColor(self.channelParameter[7]).argb()))
			return ret
		except Exception as ex:
			write_log('Fehler in buildChannelList : ' + str(ex))

	def buildEventList(self, entrys):
		try:
			maxLength = self.eventParameter[2]
			if len(entrys.title) > maxLength:
				title = str(entrys.title)[:maxLength] + '...'
			else:
				title = entrys.title
			self.picloader = PicLoader(int(self.eventParameter[0]), int(self.eventParameter[1]))
			if entrys.image:
				image = self.picloader.load(entrys.image)
			else:
				if self.eventSubstituteImage == "replaceWithPicon":
					image = LoadPixmap(entrys.picon)  # self.picloader.load(entrys.picon)
				else:
					image = self.picloader.load(self.eventSubstituteImage)
			self.picloader.destroy()

			ret = [entrys]
			#rework
			#ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.eventParameter[17][0], self.eventParameter[17][1], self.eventParameter[17][0], self.eventParameter[17][1], self.eventParameter[17][2], self.eventParameter[17][3], self.eventParameter[17][2], self.eventParameter[17][3], image, None, None, BT_SCALE))
			#for covering in self.eventListCoverings:
			#	ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, covering[0], covering[1], covering[0], covering[1], covering[2], covering[3], covering[2], covering[3], self.shaper, None, None, BT_SCALE))
			#if entrys.hasTimer and fileExists(self.eventParameter[15]):
			#	ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.eventParameter[19][0] + self.eventParameter[19][4], self.eventParameter[19][1], self.eventParameter[19][0] + self.eventParameter[19][4], self.eventParameter[19][1], self.eventParameter[19][2], self.eventParameter[19][3], self.eventParameter[19][2], self.eventParameter[19][3], self.eventParameter[19][5], self.eventParameter[19][5], self.eventListFontOrientation, str(title), skin.parseColor(self.eventParameter[6]).argb(), skin.parseColor(self.eventParameter[7]).argb()))
			#	ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.eventParameter[20][0] + self.eventParameter[20][4], self.eventParameter[20][1], self.eventParameter[20][0] + self.eventParameter[20][4], self.eventParameter[20][1], self.eventParameter[20][2], self.eventParameter[20][3], self.eventParameter[20][2], self.eventParameter[20][3], self.eventParameter[20][5], self.eventParameter[20][5], self.eventListFontOrientation, str(self.correctweekdays(entrys.timespan)), skin.parseColor(self.eventParameter[6]).argb(), skin.parseColor(self.eventParameter[7]).argb()))
			#	ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.eventParameter[18][0], self.eventParameter[18][1], self.eventParameter[18][0], self.eventParameter[18][1], self.eventParameter[18][2], self.eventParameter[18][3], self.eventParameter[18][2], self.eventParameter[18][3], LoadPixmap(self.eventParameter[15]), None, None, BT_SCALE))
			#else:
			#	ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.eventParameter[19][0], self.eventParameter[19][1], self.eventParameter[19][0], self.eventParameter[19][1], self.eventParameter[19][2], self.eventParameter[19][3], self.eventParameter[19][2], self.eventParameter[19][3], self.eventParameter[19][5], self.eventParameter[19][5], self.eventListFontOrientation, str(title), skin.parseColor(self.eventParameter[6]).argb(), skin.parseColor(self.eventParameter[7]).argb()))
			#	ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.eventParameter[20][0], self.eventParameter[20][1], self.eventParameter[20][0], self.eventParameter[20][1], self.eventParameter[20][2], self.eventParameter[20][3], self.eventParameter[20][2], self.eventParameter[20][3], self.eventParameter[20][5], self.eventParameter[20][5], self.eventListFontOrientation, str(self.correctweekdays(entrys.timespan)), skin.parseColor(self.eventParameter[6]).argb(), skin.parseColor(self.eventParameter[7]).argb()))
			return ret
		except Exception as ex:
			write_log('Fehler in buildEventList : ' + str(ex))

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

	def key_pvr_handler(self):
		if self.switchWithPVR:
			if self.activeList == "Channels":
				self["channelList"].setSelectionEnable(False)
				self["eventList"].setSelectionEnable(True)
				self.activeList = "Events"
				self.event_changed()
				self["channelsInfo"].setForegroundColorNum(0)
				self["channelsInfo"].setBackgroundColorNum(0)
				self["eventsInfo"].setForegroundColorNum(1)
				self["eventsInfo"].setBackgroundColorNum(1)
			else:
				self["channelList"].setSelectionEnable(True)
				self["eventList"].setSelectionEnable(False)
				self.activeList = "Channels"
				self["channelsInfo"].setForegroundColorNum(1)
				self["channelsInfo"].setBackgroundColorNum(1)
				self["eventsInfo"].setForegroundColorNum(0)
				self["eventsInfo"].setBackgroundColorNum(0)
				self.channel_changed()
		self["channelList"].refresh()
		self["eventList"].refresh()

	def key_menu_handler(self):
		self.session.openWithCallback(self.return_from_setup, MySetup)

	def return_from_setup(self):
		pass

	def key_play_handler(self):
		try:
			if self.activeList == "Channels":
				selected_element = self["channelList"].getcurrentselection()
				if selected_element:
					if selected_element.hasTrailer:
						sRef = eServiceReference(4097, 0, str(selected_element.hasTrailer))
						sRef.setName(str(selected_element.title))
						self.session.open(MoviePlayer, sRef)
			else:
				selected_element = self["eventList"].getcurrentselection()
				if selected_element:
					if selected_element.hasTrailer:
						sRef = eServiceReference(4097, 0, str(selected_element.hasTrailer))
						sRef.setName(str(selected_element.title))
						self.session.open(MoviePlayer, sRef)
		except Exception as ex:
			write_log("key_play : " + str(ex))

	def key_ok_handler(self):
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

	def key_red_handler(self):
		clearMem("ChannelSelection")
		global active
		active = False
		self.close()

	def key_green_handler(self):
		self.addtimer()

	def key_yellow_handler(self):
		choices, idx = (self.userBouquets, 0)
		keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
		self.session.openWithCallback(self.yellowCallBack, ChoiceBox, title='Bouquetauswahl', keys=keys, list=choices, selection=idx)

	def yellowCallBack(self, ret=None):
		if ret:
			if ret[0] == "Alle Bouquets":
				self.getChannelList(self.tvbouquets)
			else:
				for bouquet in self.tvbouquets:
					if ret[0] == bouquet[1]:
						self.getChannelList([bouquet])
						break
			self["channelList"].setlist(self.channelList)
			self["channelList"].movetoIndex(self.idx)
			self["channelsInfo"].setText(str(self["channelList"].getCurrentIndex() + 1) + '/' + str(self.channelListLen))
			self.channel_changed()

	def key_blue_handler(self):
		if self.current_event:
			if self.activeList != "Channels":
				selection = self["eventList"].getcurrentselection()
			else:
				selection = self["channelList"].getcurrentselection()
			eventName = (selection.title, selection.eit)
			self.session.openWithCallback(self.channel_changed, AdvancedEventLibrarySystem.Editor, eventname=eventName)

	def key_right_handler(self):
		self.controlChannelList(self.channelListControl["right"])
		self.controlEventList(self.eventListControl["right"])

	def key_left_handler(self):
		self.controlChannelList(self.channelListControl["left"])
		self.controlEventList(self.eventListControl["left"])

	def key_down_handler(self):
		self.controlChannelList(self.channelListControl["down"])
		self.controlEventList(self.eventListControl["down"])

	def key_up_handler(self):
		self.controlChannelList(self.channelListControl["up"])
		self.controlEventList(self.eventListControl["up"])

	def key_channel_up_handler(self):
		self.controlChannelList(self.channelListControl["pageUp"])
		self.controlEventList(self.eventListControl["pageUp"])

	def key_channel_down_handler(self):
		self.controlChannelList(self.channelListControl["pageDown"])
		self.controlEventList(self.eventListControl["pageDown"])

	def controlChannelList(self, what):
		if (self.switchWithPVR and self.activeList == "Channels") or not self.switchWithPVR:
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

	def controlEventList(self, what):
		if (self.switchWithPVR and self.activeList == "Events") or not self.switchWithPVR:
			if what == "right":
				old_idx = int(self['eventList'].getCurrentIndex())
				if old_idx == self.eventListLen - 1:
					self['eventList'].movetoIndex(0)
				else:
					self['eventList'].right()
					new_idx = int(self['eventList'].getCurrentIndex())
					if new_idx <= old_idx:
						if (old_idx + 1) >= self.eventListLen:
							dest = 0
						else:
							dest = old_idx + 1
						self['eventList'].movetoIndex(dest)
			elif what == "left":
				old_idx = int(self['eventList'].getCurrentIndex())
				if old_idx == 0:
					dest = self.eventListLen - 1
					self['eventList'].movetoIndex(dest)
				else:
					self['eventList'].left()
					new_idx = int(self['eventList'].getCurrentIndex())
					if new_idx >= old_idx:
						if (new_idx - 1) < 0:
							dest = self.eventListLen - 1
						else:
							dest = old_idx - 1
						self['eventList'].movetoIndex(dest)
			elif what == "down":
				old_idx = int(self['eventList'].getCurrentIndex())
				if old_idx == self.eventListLen - 1:
					self['eventList'].movetoIndex(0)
				else:
					self['eventList'].down()
					new_idx = int(self['eventList'].getCurrentIndex())
					if new_idx <= old_idx:
						if (new_idx + self.eventParameter[14]) >= self.eventListLen:
							dest = 0
						else:
							dest = new_idx + self.eventParameter[14]
						self['eventList'].movetoIndex(dest)
			elif what == "up":
				old_idx = int(self['eventList'].getCurrentIndex())
				if old_idx == 0:
					dest = self.eventListLen - 1
					self['eventList'].movetoIndex(dest)
				else:
					self['eventList'].up()
					new_idx = int(self['eventList'].getCurrentIndex())
					if new_idx >= old_idx:
						if (new_idx - self.eventParameter[14]) < 0:
							dest = self.eventListLen - 1
						else:
							dest = new_idx - self.eventParameter[14]
						self['eventList'].movetoIndex(dest)
			elif what == "pageDown":
				self['eventList'].prevPage()
			elif what == "pageUp":
				self['eventList'].nextPage()
			if what in ["up", "down", "left", "right", "pageUp", "pageDown"]:
				self["eventList"].refresh()
				self.event_changed()
				self["eventsInfo"].setText(str(self["eventList"].getCurrentIndex() + 1) + '/' + str(self.eventListLen))
				self["channelList"].refresh()

	def addtimer(self):
		try:
			if self.current_event is None:
				return False

			selected_element = self["eventList"].getcurrentselection()
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
			timer.tags = ['AEL-Channel-Selection']

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
			cs = self["eventList"].getcurrentselection()
			cs.__setitem__('hasTimer', True)
			self["eventList"].refresh()

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def channel_changed(self):
		try:
			self.time = time()
			events = []
			selected_channel = self["channelList"].getcurrentselection()
			if selected_channel:
				sRef = str(selected_channel.serviceref)
				eit = int(selected_channel.eit)
				self.current_event = self.epgcache.lookupEventId(eServiceReference(sRef), eit)
				self["Event"].newEvent(self.current_event)
				self["Service"].newService(eServiceReference(sRef), self.current_event)
				if selected_channel.hasTrailer:
					self["trailer"].show()
				else:
					self["trailer"].hide()
				evts = self.epgcache.lookupEvent(['ITBD', (sRef, 0, -1, (self.channelSelectionEventListDuration.value * 60))]) or [(0, ' ', 0, 0), (0, ' ', 0, 0)]
				for event in evts:
						etime = time()
						beginTime = datetime.datetime.fromtimestamp(event[2])
						endTime = datetime.datetime.fromtimestamp(event[2] + event[3])
						duration = int(event[3] / 60)
						_timespan = ""
						if "weekday" in self.eventParameter[27]:
							_timespan += beginTime.strftime("%a ")
						if "date" in self.eventParameter[27]:
							_timespan += beginTime.strftime("%d.%m. ")
						if "start" in self.eventParameter[27]:
							_timespan += beginTime.strftime("%H:%M")
						if "end" in self.eventParameter[27]:
							_timespan += endTime.strftime("-%H:%M")
						if "duration" in self.eventParameter[27]:
							_timespan += '  ' + str(duration) + ' Min.'
						_duration = str(duration) + ' Min.'

						picon = self.findPicon(sRef, selected_channel.servicename)
						if picon is None:
							picon = imgpath + 'folder.png'
						image = None
						name = ""
						hasTrailer = None
						evt = self.db.getliveTV(event[0], event[1], event[2])
						if evt:
							if evt[0][16].endswith('mp4'):
								hasTrailer = evt[0][16]
						if hasTrailer is None:
							dbdata = self.db.getTitleInfo(convert2base64(event[1]))
							if dbdata and dbdata[7].endswith('mp4'):
								hasTrailer = dbdata[7]
						if self.eventImageType in ["poster", "poster/thumbnails", "cover", "cover/thumbnails"]:
							if evt:
								if evt[0][3] != '':
									niC = self.nameCache.get(evt[0][3], '')
									if niC != '':
										image = niC
									else:
										image = getImageFile(getPictureDir() + self.eventImageType, evt[0][3])
										if image is not None:
											self.nameCache[evt[0][3]] = str(image)
									name = evt[0][3]
							if image is None:
								niC = self.nameCache.get(event[1], '')
								if niC != '':
									image = niC
								else:
									image = getImageFile(getPictureDir() + self.eventImageType, event[1])
									if image is not None:
										self.nameCache[event[1]] = str(image)

						cleanname = str(event[1]).strip().replace(".", "").replace(":", "").replace("-", "").replace("  ", " ").upper()
						hasTimer = False
						if cleanname in self.timers or str(event[0]) in self.timers or name in self.timers:
							hasTimer = True

						if event == (0, ' ', 0, 0):
							itm = ChannelEntry(sRef, event[0], ' ', 'keine Sendungsinformation', ' ', ' ', 0, picon, image, selected_channel.bouquet, False, 0, hasTrailer)
						else:
							itm = ChannelEntry(sRef, event[0], ' ', event[1], _timespan, _duration, 0, picon, image, selected_channel.bouquet, hasTimer, 0, hasTrailer)
						events.append((itm,))
				if len(events) > 1:
					del events[0]
				else:
					if not events:
						itm = ChannelEntry(sRef, 0, ' ', 'uppps...', ' ', ' ', 0, imgpath + 'folder.png', None, selected_channel.bouquet, False, 0)
						events.append((itm,))
				self.eventListLen = len(events)
				self["eventList"].setlist(events)
				self["eventList"].movetoIndex(0)
				self["eventList"].refresh()
				self["eventsInfo"].setText(str(self["eventList"].getCurrentIndex() + 1) + '/' + str(self.eventListLen))
		except Exception as ex:
			write_log("channel_changed : " + str(ex))
			self["Event"].newEvent(None)

	def event_changed(self):
		try:
			selected_event = self["eventList"].getcurrentselection()
			if selected_event:
				sRef = str(selected_event.serviceref)
				eit = int(selected_event.eit)
				self.current_event = self.epgcache.lookupEventId(eServiceReference(sRef), eit)
				self["Event"].newEvent(self.current_event)
				self["Service"].newService(eServiceReference(sRef), self.current_event)
				if selected_event.hasTrailer:
					self["trailer"].show()
				else:
					self["trailer"].hide()
		except Exception as ex:
			write_log("event_changed : " + str(ex))
			self["Event"].newEvent(None)

	def key_info_handler(self):
		from Screens.EventView import EventViewSimple
		selected_event = self["eventList"].getcurrentselection()
		if selected_event:
			sRef = str(selected_event.serviceref)
			if self.epgViewType.value == "EPGSelection":
				from Screens.EpgSelection import EPGSelection
				self.session.open(EPGSelection, sRef)
			else:
				if self.current_event:
						self.session.open(EventViewSimple, self.current_event, ServiceReference(sRef))

	def correctweekdays(self, itm):
		_itm = str(itm)
		_itm = _itm.replace("Mon", "Mo").replace("Tue", "Di").replace("Wed", "Mi").replace("Thu", "Do").replace("Fri", "Fr").replace("Sat", "Sa").replace("Sun", "So")
		return _itm


####################################################################################
class MySetup(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.skinName = ["AEL-Channel-Selection-Setup", "Setup"]
		self.title = "AEL-Channel-Selection-Setup"

		self.setup_title = "AEL-Channel-Selection-Setup"
		self["title"] = StaticText(self.title)

		self["key_red"] = StaticText("Beenden")
		self["key_green"] = StaticText("Speichern")

		config.plugins.AdvancedEventLibrary = ConfigSubsection()
		self.myBouquet = config.plugins.AdvancedEventLibrary.ChannelSelectionStartBouquet = ConfigSelection(default="Alle Bouquets", choices=['Alle Bouquets', 'aktuelles Bouquet'])
		self.epgViewType = config.plugins.AdvancedEventLibrary.EPGViewType = ConfigSelection(default="EventView", choices=['EPGSelection', 'EventView'])
		self.channelSelectionEventListDuration = config.plugins.AdvancedEventLibrary.ChannelSelectionEventListDuration = ConfigInteger(default=12, limits=(1, 240))

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
			self.configlist.append(getConfigListEntry("EPG-Taste �ffnet", self.epgViewType))
			self.configlist.append(getConfigListEntry("Event-List Dauer (Stunden)", self.channelSelectionEventListDuration))
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
