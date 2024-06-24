#!/usr/bin/env python
# -*- coding: utf-8 -*-
#################################################################################
#																				#
#								AdvancedEventLibrary							#
#																				#
#							Copyright: tsiegel 2019								#
#																				#
#################################################################################
from __future__ import absolute_import
from __future__ import print_function
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.EventView import EventViewSimple, EventViewBase, EventViewMovieEvent
from Screens.EpgSelection import EPGSelection
from Screens.TimerEntry import TimerEntry
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.ChoiceBox import ChoiceBox
from Screens.TimerEdit import TimerSanityConflict, TimerEditList
from Screens.InfoBar import InfoBar, MoviePlayer
from Screens.InfoBarGenerics import InfoBarSimpleEventView
from Screens.MovieSelection import MovieSelection
from Screens.HelpMenu import HelpableScreen
from Components.EpgList import EPGList, EPG_TYPE_SINGLE, EPG_TYPE_MULTI, EPG_TYPE_INFOBAR
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Sources.StaticText import StaticText
from Components.config import config, ConfigSubsection, ConfigYesNo, ConfigText, ConfigSelection, ConfigInteger
from Tools.Directories import fileExists
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.FunctionTimer import functionTimer
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.Button import Button
from Components.UsageConfig import preferredTimerPath
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Plugins.Plugin import PluginDescriptor
from RecordTimer import RecordTimerEntry, RecordTimer, parseEvent, AFTEREVENT
from enigma import eEPGCache, eTimer, eServiceReference, addFont, eServiceCenter
from threading import Timer
import threading
from Tools.SystemEvents import systemevents
from Tools.LoadPixmap import LoadPixmap
from ServiceReference import ServiceReference
from time import time, localtime
import Tools.AutoTimerHook as AutoTimerHook
#from Tools.MovieInfoParser import getExtendedMovieDescription
import os
import re
from . import skin
import pickle
import Screens.Standby

from . import AdvancedEventLibrarySystem
from . import AdvancedEventLibrarySimpleMovieWall
from . import AdvancedEventLibrarySerienStarts
from . import AdvancedEventLibraryPrimeTime
from . import AdvancedEventLibraryChannelSelection
from . import AdvancedEventLibraryMediaHub
from . import AdvancedEventLibraryRecommendations
from Tools.AdvancedEventLibrary import getDB, convertTitle, convert2base64

global leavePlayerfromTrailer
leavePlayerfromTrailer = False

PARAMETER_SET = 0
PARAMETER_GET = 1

pluginpath = '/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/'

pdesc = 'AdvancedEventLibrary'
config.plugins.AdvancedEventLibrary = ConfigSubsection()
useAELEPGLists = config.plugins.AdvancedEventLibrary.UseAELEPGLists = ConfigYesNo(default=False)
useEPGLists = useAELEPGLists.value or useAELEPGLists.value == 'true'
showinEPG = config.plugins.AdvancedEventLibrary.ShowInEPG = ConfigYesNo(default=False)
setEPGList = showinEPG.value or showinEPG.value == 'true'
useAELMW = config.plugins.AdvancedEventLibrary.UseAELMovieWall = ConfigYesNo(default=False)
useMW = useAELMW.value or useAELMW.value == 'true'
viewType = config.plugins.AdvancedEventLibrary.ViewType = ConfigSelection(default="Wallansicht", choices=["Listenansicht", "Wallansicht"])
favouritesMaxAge = config.plugins.AdvancedEventLibrary.FavouritesMaxAge = ConfigInteger(default=14, limits=(5, 90))
refreshMW = config.plugins.AdvancedEventLibrary.RefreshMovieWall = ConfigYesNo(default=True)
refreshMovieData = refreshMW.value or refreshMW.value == 'true'
updateAELMovieWall = config.plugins.AdvancedEventLibrary.UpdateAELMovieWall = ConfigYesNo(default=True)
refreshMovieWall = updateAELMovieWall.value or updateAELMovieWall.value == 'true'

baseEPGSelection__init__ = None
baseEventViewBase__init__ = None
baseEventViewMovieEvent__init__ = None
baseInfoBarSimpleEventView__init__ = None
gSession = None
ServiceTrack = None

addFont('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/fonts/Normal.ttf', 'Normal', 100, False)
addFont('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/fonts/Small.ttf', 'Small', 100, False)

log = "/var/tmp/AdvancedEventLibrary.log"


def write_log(svalue):
	t = localtime()
	logtime = '%02d:%02d:%02d' % (t.tm_hour, t.tm_min, t.tm_sec)
	AEL_log = open(log, "a")
	AEL_log.write(str(logtime) + " : [AdvancedEventLibraryPlugin] - " + str(svalue) + "\n")
	AEL_log.close()


def sessionstart(reason, **kwargs):
	try:
		if 'session' in kwargs and reason == 0:
			global ServiceTrack
			ServiceTrack = Recommendations()
			global gSession
			gSession = kwargs["session"]
			foundTimer = False
			foundBackup = False
			fTimers = functionTimer.get()
			for fTimer in fTimers:
				if 'AdvancedEventLibraryUpdate' in fTimer:
					foundTimer = True
				if 'AdvancedEventLibraryBackup' in fTimer:
					foundBackup = True
			if not foundTimer:
				functionTimer.add(("AdvancedEventLibraryUpdate", {"name": "Advanced-Event-Library-Update", "imports": "Tools.AdvancedEventLibrary", "fnc": "getallEventsfromEPG"}))
			if not foundBackup:
				functionTimer.add(("AdvancedEventLibraryBackup", {"name": "Advanced-Event-Library-Backup", "imports": "Tools.AdvancedEventLibrary", "fnc": "createBackup"}))

			# InfoBarSimpleEventViewInit()
			# EPGSelectionInit()
			# EventViewInit()
			# EventViewMovieEventInit()
			# InfoBar.showMovies_org = InfoBar.showMovies
			# InfoBar.showMovies = iBshowMovies
			# MoviePlayer.handleLeave = handleLeaveNew
			# MoviePlayer.showMovies = showMoviesNew
			# MoviePlayer.setPlayMode = setPlayModeNew
			# MovieSelection.showEventInformation = showEventInformationNew
			# getExtendedMovieDescription = getExtendedMovieDescriptionNew
#			for evt in systemevents.getSystemEvents():
			#	write_log('available event : ' + str(systemevents.getfriendlyName(evt)) + ' - ' + str(evt))
#				if (evt == systemevents.RECORD_STOP or evt == systemevents.PVRDESCRAMBLE_STOP):
#					if refreshMovieData and refreshMovieWall:
#						systemevents.addEventHook(evt, _refreshMovieWall, "refreshMovieWallData_" + evt, evt)
#				if evt == systemevents.SERVICE_START:
#					systemevents.addEventHook(evt, _serviceStart, "newServiceStart_" + evt, evt)
	except Exception as ex:
		write_log('sessionstart ' + str(ex))


def _serviceStart(evt, *args):
		global ServiceTrack
#		write_log("new service detected : " + str(args[1]))
		if len(args) > 0 and ServiceTrack and not Screens.Standby.inStandby:
			ServiceTrack.newServiceStarted(args)


def openMoviePlayerEventViewMI(self):
	write_log('call MediaInfo openMoviePlayerEventView')
	already_open = False
	if True and not already_open:
		already_open = True
		service = self.session.nav.getCurrentService()
		filename = service.info().getName()
		url = self.session.nav.getCurrentlyPlayingServiceReference().getPath()
		if re.match('.*?http://', url, re.S):
			self.session.open(MediaInfo)
		else:
			InfoBarSimpleEventViewBase_openEventView(self)
	else:
		InfoBarSimpleEventViewBase_openEventView(self)


def InfoBarSimpleEventViewBase__init__(self):
	self["EPGActions"] = HelpableActionMap(self, "InfobarEPGActions",
		{
			"showEventInfo": (self.openEventView, _("show event details")),
			"showInfobarOrEpgWhenInfobarAlreadyVisible": self.showEventInfoWhenNotVisible,
		})


def InfoBarSimpleEventViewBase_openEventView(self):
	epglist = []
	self.epglist = epglist
	service = self.session.nav.getCurrentService()
	ref = self.session.nav.getCurrentlyPlayingServiceReference()
	write_log('openEventViewNew ' + str(ref.toString()))
	info = service.info()
	ptr = info.getEvent(0)
	if ptr:
		epglist.append(ptr)
	ptr = info.getEvent(1)
	if ptr:
		epglist.append(ptr)
	if epglist:
		write_log('open EventViewSimple from Player ' + str(ref.toString()))
		self.session.open(EventViewSimple, epglist[0], ServiceReference(ref), self.eventViewCallback)
	elif ref.toString().startswith("4097") or ref.toString().startswith("1:0:0:0:0:0:0:0:0:0:"):
		path = ref.getPath()
		if path.startswith(("rtsp", "rtmp", "http", "mms")):
			name = ref.getName()
			ext_desc = ""
			length = ""
		else:
			seek = self.getSeek()
			length = ""
			if seek:
				length = seek.getLength()
				if not length[0] and length[1] > 1:
					length = length[1] / 90000
					if config.usage.movielist_duration_in_min.value:
						length = "%d min" % (int(length) / 60)
					else:
						length = "%02d:%02d:%02d" % (length / 3600, length % 3600 / 60, length % 60)
			name, ext_desc = getExtendedMovieDescriptionNew(ref)
		write_log('open EventViewMovieEvent from Player ' + str(ref.toString()))
		self.session.open(EventViewMovieEvent, name, ext_desc, length, ref)


def showEventInformationNew(self):
	evt = self["list"].getCurrentEvent()
	if evt:
		self.session.open(EventViewSimple, evt, ServiceReference(self.getCurrent()))
	else:
		current = self.getCurrent()
		if current is not None and not current.flags & eServiceReference.mustDescent:
			dur = self["list"].getCurrentDuration()
			name, ext_desc = getExtendedMovieDescriptionNew(current)
			self.session.open(EventViewMovieEvent, name, ext_desc, dur, self.getCurrent())


def getExtendedMovieDescriptionNew(ref):
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


def _refreshMovieWall(evt, *args):
		if len(args) > 0:
			write_log('refresh MovieWallData because of : ' + str(evt) + ' args : ' + str(args))
		if (evt == systemevents.RECORD_START or evt == systemevents.RECORD_STOP or evt == systemevents.PVRDESCRAMBLE_STOP):
			refreshData = Timer(30, refreshMovieWallData)
			refreshData.start()


def refreshMovieWallData():
	threading.start_new_thread(saveMovieWallData, ())


def saveMovieWallData():
	try:
		if not AdvancedEventLibrarySimpleMovieWall.saving:
			write_log("create MovieWall data after new record detected")
			try:
				itype = None
				if os.path.isfile('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/imageType.data'):
					with open('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/imageType.data', 'r') as f:
						itype = f.read()
						f.close()
				if itype:
					from .AdvancedEventLibrarySimpleMovieWall import saveList
					saveList(itype)
					write_log("MovieWall data saved with " + str(itype))
			except Exception as ex:
				write_log('save moviewall data : ' + str(ex))
	except:
		write_log('saveMovieWallData ' + str(ex))


def showMoviesNew(self):
	from .AdvancedEventLibrarySimpleMovieWall import active as MWactive
	from .AdvancedEventLibraryMediaHub import active as MHactive
	if not MWactive and not MHactive:
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		try:
			self.session.openWithCallback(self.movieSelected, MovieSelection, ref, isVirtualDir=self.isVirtualDir)
		except:
			self.session.openWithCallback(self.movieSelected, MovieSelection, ref)


def handleLeaveNew(self, how):
	if self.session.pipshown:
		self.InfoBar_Instance.showPiP()
	self.is_closing = True
	global leavePlayerfromTrailer
	from .AdvancedEventLibrarySimpleMovieWall import active as MWactive
	from .AdvancedEventLibraryMediaHub import active as MHactive
	from .AdvancedEventLibraryChannelSelection import active as CSactive
	from .AdvancedEventLibraryPrimeTime import active as PTactive
	from .AdvancedEventLibrarySerienStarts import active as SSactive
	from .AdvancedEventLibraryRecommendations import active as Favactive
	if MWactive or MHactive or CSactive or PTactive or SSactive or Favactive or leavePlayerfromTrailer:
		if not self.playmode and how == "ask":
			if config.usage.setup_level.index < 2:  # -expert
				list = (
					(_("Yes"), "quit"),
					(_("No"), "continue")
				)
			else:
				list = (
					(_("Yes"), "quit"),
					(_("No"), "continue"),
					(_("No, but restart from begin"), "restart"),
				)

			from Screens.ChoiceBox import ChoiceBox
			self.session.openWithCallback(self.leavePlayerConfirmed, ChoiceBox, title=_("Stop playing this movie?"), list=list)
		elif self.playmode and self.playmode in ("random", "loop"):
			self.leavePlayerConfirmed([True, "playnext"])
		else:
			self.leavePlayerConfirmed([True, "quit"])
	else:
		if not self.playmode and how == "ask":
			if config.usage.setup_level.index < 2:  # -expert
				list = (
					(_("Yes"), "quit"),
					(_("No"), "continue")
				)
			else:
				list = (
					(_("Yes"), "quit"),
					(_("Yes, returning to movie list"), "movielist"),
					(_("Yes, and delete this movie"), "quitanddelete"),
					(_("Yes, delete this movie and go back to movie list"), "quit_and_delete_movielist"),
					(_("Yes, and play next media file"), "playnext"),
					(_("No"), "continue"),
					(_("No, but restart from begin"), "restart"),
				)

			from Screens.ChoiceBox import ChoiceBox
			self.session.openWithCallback(self.leavePlayerConfirmed, ChoiceBox, title=_("Stop playing this movie?"), list=list)
		elif self.playmode and self.playmode in ("random", "loop"):
			self.leavePlayerConfirmed([True, "playnext"])
		else:
			self.leavePlayerConfirmed([True, how])


def setPlayModeNew(self):
	from .AdvancedEventLibrarySimpleMovieWall import active as MWactive
	from .AdvancedEventLibraryMediaHub import active as MHactive
	if not MWactive and not MHactive and self.movie_playlist:
		if len(self.movie_playlist):
			choicelist = (
					(_("Default play mode"), "default"),
					(_("Shuffle play"), "random"),
					(_("Play all"), "loop"),
				)
			from Screens.ChoiceBox import ChoiceBox
			self.session.openWithCallback(self.playModeChanged, ChoiceBox, title=_("Please select play mode :"), list=choicelist)


def cancelTimerFunction():
	print("[Advanced-Event-Library-Update] Aufgabe beendet!")


def InfoBarSimpleEventViewInit():
	global baseInfoBarSimpleEventView__init__
	if baseInfoBarSimpleEventView__init__ is None:
		baseInfoBarSimpleEventView__init__ = InfoBarSimpleEventView.__init__
	InfoBarSimpleEventView.__init__ = InfoBarSimpleEventViewBase__init__
	InfoBarSimpleEventView.openEventView = InfoBarSimpleEventViewBase_openEventView


def EventViewInit():
	global baseEventViewBase__init__
	if baseEventViewBase__init__ is None:
		baseEventViewBase__init__ = EventViewBase.__init__
	EventViewBase.__init__ = EventViewBase__init__
	EventViewBase.setService = EventViewBase_setService
	EventViewBase.setEvent = EventViewBase_setEvent
	EventViewBase.onCreate = EventViewBase_onCreate


def EventViewMovieEventInit():
	global baseEventViewMovieEvent__init__
	if baseEventViewMovieEvent__init__ is None:
		baseEventViewMovieEvent__init__ = EventViewMovieEvent.__init__
	EventViewMovieEvent.__init__ = EventViewMovieEvent__init__
	EventViewMovieEvent.onCreate = EventViewMovieEvent_onCreate


def EventViewMovieEvent__init__(self, session, name=None, ext_desc=None, dur=None, service=None):
	Screen.__init__(self, session)
	from Components.Sources.ExtEvent import ExtEvent
	from Components.Sources.ServiceEvent import ServiceEvent
	self.screentitle = _("Eventview")
	self.skinName = "EventView"
	self.db = getDB()
	self.name = name
	self.trailer = None
	self.duration = ""
	self.service = service
	self.session = session
	if dur:
		self.duration = dur
	self.ext_desc = ""
	if name:
		self.ext_desc = name + "\n\n"
	if ext_desc:
		self.ext_desc += ext_desc
	if self.service:
		txt = getMovieDescriptionFromTXT(self.service)[1]
		if txt != ext_desc:
			self.ext_desc += "\n\n"
			self.ext_desc += getMovieDescriptionFromTXT(self.service)[1]
	self["epg_description"] = ScrollLabel()
	self["datetime"] = Label()
	self["channel"] = Label()
	self["duration"] = Label()

	self["ExtEvent"] = ServiceEvent()
	self["Service"] = ServiceEvent()
	self["trailer"] = Pixmap()

	self["key_red"] = Button("")
	self["key_green"] = Button("")
	self["key_yellow"] = Button("")
	self["key_blue"] = Button("")

	def key_play_handler():
		if self.trailer:
			global leavePlayerfromTrailer
			leavePlayerfromTrailer = True
			sRef = eServiceReference(4097, 0, str(self.trailer))
			sRef.setName(str(getMovieDescriptionFromTXT(self.service)[0]))
			self.session.open(MoviePlayer, sRef)

	self["actions"] = ActionMap(["OkCancelActions", "EventViewActions"],
		{
			"cancel": self.close,
			"ok": self.close,
			"pageUp": self.pageUp,
			"pageDown": self.pageDown,
		})
	self["aelactions"] = ActionMap(["AdvancedEventLibraryActions"],
		{
			"key_play": key_play_handler,
		}, -1)
	self.onShown.append(self.onCreate)


def EventViewMovieEvent_onCreate(self):
	self.setTitle(self.screentitle)
	self["epg_description"].setText(self.ext_desc)
	self["duration"].setText(self.duration)
	try:
		if self.service:
			self["Service"].newService(self.service)
			self["ExtEvent"].newService(self.service)
		imgpath = skin.variables.get("EventLibraryImagePath", '/usr/share/enigma2/AELImages/,').replace(',', '')
		ptr = LoadPixmap(os.path.join(imgpath, "play.png"))
		self["trailer"].instance.setPixmap(ptr)
		self["trailer"].hide()
		if self.name is not None:
			if self.db and "trailer" in self:
				dbdata = self.db.getTitleInfo(convert2base64(self.name))
				if dbdata and dbdata[7].endswith('mp4'):
					self.trailer = dbdata[7]
					self["trailer"].show()
	except Exception as ex:
		write_log('EventViewMovieEvent_onCreate ' + str(ex))


def getMovieDescriptionFromTXT(ref):
	f = None
	extended_desc = ""
	name = ""
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


def EventViewBase__init__(self, Event, Ref, callback=None, similarEPGCB=None):
	from Components.Sources.ExtEvent import ExtEvent
	from Components.Sources.ServiceEvent import ServiceEvent
	self.db = getDB()
	self.trailer = None
	if not AutoTimerHook.CHECKAUTOTIMER:
		AutoTimerHook.initAutoTimerGlobals()
	self.screentitle = _("Eventview")
	self.similarEPGCB = similarEPGCB
	self.cbFunc = callback
	self.currentService = Ref
	path = Ref.ref.getPath()
	self.isRecording = (not Ref.ref.flags & eServiceReference.isGroup) and path
	if path.find('://') != -1:
		self.isRecording = None
	self.event = Event
	self["epg_description"] = ScrollLabel()
	self["datetime"] = Label()
	self["channel"] = Label()
	self["duration"] = Label()
	self["key_red"] = Button("")
	self["ExtEvent"] = ExtEvent()
	self["Service"] = ServiceEvent()
	self["trailer"] = Pixmap()
	if similarEPGCB is not None:
		self.SimilarBroadcastTimer = eTimer()
		self.SimilarBroadcastTimer.callback.append(self.getSimilarEvents)
	else:
		self.SimilarBroadcastTimer = None
	self.key_green_choice = self.ADD_TIMER
	if self.isRecording:
		self["key_green"] = Button("")
	else:
		self["key_green"] = Button(_("Add timer"))
	self["key_yellow"] = Button("")
	self["key_blue"] = Button("")

	def key_play_handler():
		if self.trailer:
			global leavePlayerfromTrailer
			leavePlayerfromTrailer = True
			sRef = eServiceReference(4097, 0, str(self.trailer))
			sRef.setName(str(self.event.getEventName()))
			self.session.open(MoviePlayer, sRef)

	self["actions"] = ActionMap(["OkCancelActions", "EventViewActions"],
		{
			"cancel": self.close,
			"ok": self.close,
			"pageUp": self.pageUp,
			"pageDown": self.pageDown,
			"prevEvent": self.prevEvent,
			"nextEvent": self.nextEvent,
			"timerAdd": self.timerAdd,
			"instantTimer": self.addInstantTimer,
			"openSimilarList": self.openSimilarList
		})
	self["menu_actions"] = HelpableActionMap(self, "MenuActions", {
			"menu": (self.menuClicked, _("Setup")),
		}, -2)
	self["aelactions"] = ActionMap(["AdvancedEventLibraryActions"],
		{
			"key_play": key_play_handler,
		}, -1)
	self.onShown.append(self.onCreate)


def EventViewBase_onCreate(self):
	imgpath = skin.variables.get("EventLibraryImagePath", '/usr/share/enigma2/AELImages/,').replace(',', '')
	ptr = LoadPixmap(os.path.join(imgpath, "play.png"))
	self["trailer"].instance.setPixmap(ptr)
	self.setService(self.currentService)
	self.setEvent(self.event)
	self.setTitle(self.screentitle)


def EventViewBase_setService(self, service):
	self.currentService = service
	if self.isRecording:
		self["channel"].setText(_("Recording"))
	else:
		name = self.currentService.getServiceName()
		if name is not None:
			self["channel"].setText(name)
		else:
			self["channel"].setText(_("unknown service"))
	self["Service"].newService(service.ref)
	self["ExtEvent"].newService(service.ref)


def EventViewBase_setEvent(self, event):
	self.event = event
	text = ''
	short = ''
	ext = ''
	if "trailer" in self:
		self["trailer"].hide()
		self.trailer = None
	if event:
		text = event.getEventName()
		short = event.getShortDescription()
		ext = event.getExtendedDescription()
		self["datetime"].setText(event.getBeginTimeString())
		self["duration"].setText(_("%d min") % (event.getDuration() / 60))
		if self.db and "trailer" in self:
			(begin, end, name, description, eit) = parseEvent(event)
			val = self.db.getliveTV(eit, name)
			if val:
				if val[0][16].endswith('mp4'):
					self.trailer = val[0][16]
					self["trailer"].show()
			if self.trailer is None:
				dbdata = self.db.getTitleInfo(convert2base64(name))
				if dbdata and dbdata[7].endswith('mp4'):
					self.trailer = dbdata[7]
					self["trailer"].show()
	if short and short != text:
		text += '\n\n' + short
	if ext:
		if text:
			text += '\n\n'
		text += ext
	if self.isRecording:
		txt = getMovieDescriptionFromTXT(self.currentService.ref)[1]
		if txt != ext:
			if text:
				text += '\n\n'
			text += txt
	if "epg_description" in self:
		self["epg_description"].setText(text)
	self["key_red"].setText("")
	if event:
		if self.SimilarBroadcastTimer is not None:
			self.SimilarBroadcastTimer.start(400, True)
		serviceref = self.currentService
		eventid = self.event.getEventId()
		refstr = serviceref.ref.toString()
		isRecordEvent = False
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				isRecordEvent = True
				break
		if isRecordEvent and self.key_green_choice != self.REMOVE_TIMER:
			self["key_green"].setText(_("Remove timer"))
			self.key_green_choice = self.REMOVE_TIMER
		elif not isRecordEvent and self.key_green_choice != self.ADD_TIMER:
			self["key_green"].setText(_("Add timer"))
			self.key_green_choice = self.ADD_TIMER
		self["ExtEvent"].newEvent(event)
	self["ExtEvent"].newService(self.currentService)


def EPGSelectionInit(reason=None):
	if reason is not None:
		write_log('EPGSelectionInit : ' + str(reason))
	global baseEPGSelection__init__
	if baseEPGSelection__init__ is None:
		baseEPGSelection__init__ = EPGSelection.__init__
	EPGSelection.__init__ = EPGSelection__init__
	if setEPGList:
		EPGSelection.timerAdd = EPGSelection_timerAdd
		EPGSelection.askTimerPath = EPGSelection_askTimerPath
		EPGSelection.onSelectionChanged = EPGSelection_onSelectionChanged
		EPGSelection.onCreate = EPGSelection_onCreate


def EPGSelection__init__(self, session, service, zapFunc=None, eventid=None, bouquetChangeCB=None, serviceChangeCB=None, isEPGBar=None, switchBouquet=None, EPGNumberZap=None, togglePiP=None):
	baseEPGSelection__init__(self, session, service, zapFunc, eventid, bouquetChangeCB, serviceChangeCB, isEPGBar, switchBouquet, EPGNumberZap, togglePiP)
	self.db = getDB()
	self.trailer = None
	self["trailer"] = Pixmap()
	self.eventName = ''

	def key_play_handler():
		write_log('key play pressed')
		if self.trailer:
			global leavePlayerfromTrailer
			leavePlayerfromTrailer = True
			sRef = eServiceReference(4097, 0, str(self.trailer))
			sRef.setName(str(self.eventName))
			self.session.open(MoviePlayer, sRef)

	if useEPGLists:
		from Components.AdvancedEventLibraryEpgList import AEL_EPGList
		self["list"] = AEL_EPGList(type=self.type, selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer)

	if self.type != EPG_TYPE_MULTI and setEPGList:
		def infoClicked():
			cur = self["list"].getCurrent()
			if cur[0] is not None:
				name = cur[0].getEventName()
				id = cur[0].getEventId()
			else:
				id = 0
				name = ''
			session.open(AdvancedEventLibrarySystem.Editor, eventname=(name, id))

		self["AEL_actions"] = ActionMap(["EPGSelectActions", "OkCancelActions"],
			{
			"info": infoClicked,
			}, -1)

	self["aelactions"] = ActionMap(["AdvancedEventLibraryActions"],
		{
			"key_play": key_play_handler,
		}, -1)

#	check TMDb
	if os.path.isfile('/usr/lib/enigma2/python/Plugins/Extensions/tmdb/plugin.pyc'):
		#config.plugins.tmdb = ConfigSubsection()
		if self.type != EPG_TYPE_MULTI and config.plugins.tmdb.keyyellow.value:
			write_log('Overwrite TMDb Key Yellow')
			from Plugins.Extensions.tmdb import tmdb

			def yellowClicked():
				cur = self["list"].getCurrent()
				if cur[0] is not None:
					name = cur[0].getEventName()
				else:
					name = ''
				session.open(tmdb.tmdbScreen, name, 2)
			self["tmdb_actions"] = ActionMap(["EPGSelectActions"],
					{
						"yellow": yellowClicked,
					})
			self["key_yellow"].text = "TMDb Infos..."

#	check EPGSearch
	if os.path.isfile('/usr/lib/enigma2/python/Plugins/Extensions/EPGSearch/plugin.pyc'):
		if self.type != EPG_TYPE_MULTI and config.plugins.epgsearch.add_search_to_epg.value:
			from Plugins.Extensions.EPGSearch import EPGSearch
			from Components.Sources.StaticText import StaticText
			from Components.Sources.ExtEvent import ExtEvent

			def bluePressed():
				cur = self["list"].getCurrent()
				if cur[0] is not None:
					name = cur[0].getEventName()
				else:
					name = ''
				self.session.open(EPGSearch.EPGSearch, name, False)
			self["SelectedEvent"] = StaticText()
			self["ExtEvent"] = ExtEvent()
			self["epgsearch_actions"] = ActionMap(["EPGSelectActions"],
					{
						"blue": bluePressed,
					})
			self["key_blue"].text = "Suche..."


def EPGSelection_onCreate(self):
	imgpath = skin.variables.get("EventLibraryImagePath", '/usr/share/enigma2/AELImages/,').replace(',', '')
	ptr = LoadPixmap(os.path.join(imgpath, "play.png"))
	self["trailer"].instance.setPixmap(ptr)
	l = self["list"]
	l.recalcEntrySize()
	if self.type == EPG_TYPE_MULTI:
		l.fillMultiEPG(self.services, self.ask_time)
		l.moveToService(self.session.nav.getCurrentlyPlayingServiceReference())
	elif self.type == EPG_TYPE_SINGLE:
		service = self.currentService
		self["Service"].newService(service.ref)
		if self.saved_title is None:
			self.saved_title = self.instance.getTitle()
		title = self.saved_title + ' - ' + service.getServiceName()
		self.instance.setTitle(title)
		l.fillSingleEPG(service)
	elif self.type == EPG_TYPE_INFOBAR:
		service = self.currentService
		self["Service"].newService(service.ref)
		l.fillEPGBar(service)
	else:
		l.fillSimilarList(self.currentService, self.eventid)


def EPGSelection_onSelectionChanged(self):
	if "trailer" in self:
		self.trailer = None
		self["trailer"].hide()
	cur = self["list"].getCurrent()
	if cur is None:
		if self.key_green_choice != self.EMPTY:
			self["key_green"].setText("")
			self.key_green_choice = self.EMPTY
		if self.key_red_choice != self.EMPTY:
			self["key_red"].setText("")
			self.key_red_choice = self.EMPTY
		return
	event = cur[0]
	self["Event"].newEvent(event)
	if self.type == EPG_TYPE_MULTI:
		count = self["list"].getCurrentChangeCount()
		if self.ask_time != -1:
			self.applyButtonState(0)
		elif count > 1:
			self.applyButtonState(3)
		elif count > 0:
			self.applyButtonState(2)
		else:
			self.applyButtonState(1)
		days = [_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun")]
		datestr = ""
		if event is not None:
			now = time()
			beg = event.getBeginTime()
			nowTime = localtime(now)
			begTime = localtime(beg)
			if nowTime[2] != begTime[2]:
				datestr = '%s %d.%d.' % (days[begTime[6]], begTime[2], begTime[1])
			else:
				datestr = '%s %d.%d.' % (_("Today"), begTime[2], begTime[1])
		self["date"].setText(datestr)
		if cur[1] is None:
			self["Service"].newService(None)
		else:
			self["Service"].newService(cur[1].ref)

	if cur[1] is None or cur[1].getServiceName() == "":
		if self.key_green_choice != self.EMPTY:
			self["key_green"].setText("")
			self.key_green_choice = self.EMPTY
		if self.key_red_choice != self.EMPTY and self.type != EPG_TYPE_INFOBAR and self.type != EPG_TYPE_SINGLE:
			self["key_red"].setText("")
			self.key_red_choice = self.EMPTY
		return
	elif self.key_red_choice != self.ZAP and (self.type == EPG_TYPE_MULTI or self.type == EPG_TYPE_INFOBAR or self.type == EPG_TYPE_SINGLE):
			if self.zapFunc:
				self["key_red"].setText(_("Zap"))
				self.key_red_choice = self.ZAP

	if event is None:
		if self.key_green_choice != self.EMPTY:
			self["key_green"].setText("")
			self.key_green_choice = self.EMPTY
		return
	self["SelectedEvent"].setText((cur[0], cur[1]))
	self["ExtEvent"].newEvent(cur[0])
	self["ExtEvent"].newService(cur[1])
	if "trailer" in self:
		if self.db:
			(begin, end, name, description, eit) = parseEvent(event)
			val = self.db.getliveTV(eit, name)
			self.eventName = name
			if val:
				if val[0][16].endswith('mp4'):
					self.trailer = val[0][16]
					self["trailer"].show()
			if self.trailer is None:
				dbdata = self.db.getTitleInfo(convert2base64(name))
				if dbdata and dbdata[7].endswith('mp4'):
					self.trailer = dbdata[7]
					self["trailer"].show()
	serviceref = cur[1]
	eventid = event.getEventId()
	refstr = serviceref.ref.toString()
	isRecordEvent = False
	isDisabled = False
	for timer in self.session.nav.RecordTimer.timer_list:
		if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
			isRecordEvent = True
			break
	if not isRecordEvent:
		for timer in self.session.nav.RecordTimer.processed_timers:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr and timer.disabled == True:
				isDisabled = True
				break
	if isDisabled:
		self["key_green"].setText(_("Remove timer") + "\n" + _("Enable timer"))
		self.key_green_choice = self.ENABLE_TIMER
	elif isRecordEvent:
		self["key_green"].setText(_("Remove timer") + "\n" + _("Disable timer"))
		self.key_green_choice = self.REMOVE_TIMER
	elif not isRecordEvent and self.key_green_choice != self.ADD_TIMER:
		self["key_green"].setText(_("Add timer"))
		self.key_green_choice = self.ADD_TIMER


def getRecordName(event):
	db = getDB()
	if db:
		(begin, end, name, description, eit) = parseEvent(event)
		recname = name
		recdesc = ""
		val = db.getliveTV(eit, name)
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
		return recdesc, recname, begin, end, eit


def EPGSelection_timerAdd(self, instantTimer=False):
	cur = self["list"].getCurrent()
	event = cur[0]
	serviceref = cur[1]
	if event is None:
		return
	eventid = event.getEventId()
	refstr = serviceref.ref.toString()

	if self.key_green_choice == self.ENABLE_TIMER:
		for timer in self.session.nav.RecordTimer.processed_timers:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr and timer.disabled == True:
				if instantTimer:
					self.removeTimer(timer, True)
				else:
					cb_func = lambda ret: not ret or self.removeTimer(timer)
					self.session.openWithCallback(cb_func, MessageBox, _("Do you really want to delete %s?") % event.getEventName())
				break
	else:
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				if instantTimer:
					self.removeTimer(timer, True)
				else:
					cb_func = lambda ret: not ret or self.removeTimer(timer)
					self.session.openWithCallback(cb_func, MessageBox, _("Do you really want to delete %s?") % event.getEventName())
				break
		else:
			recdesc, recname, begin, end, eit = getRecordName(event)

			newEntry = RecordTimerEntry(serviceref, begin, end, recname, recdesc, eit, False, False, afterEvent=AFTEREVENT.AUTO, dirname=preferredTimerPath(), tags=None)
			newEntry.repeated = 0
			newEntry.tags = ['Advanced-Event-Library']

			if instantTimer:
				if config.usage.timer_ask_path.value and config.movielist.videodirs.value:
					choicelist = []
					for x in config.movielist.videodirs.value:
						choicelist.append((x, x))
					idx = 0
					pref = (preferredTimerPath(), preferredTimerPath())
					if pref in choicelist:
						idx = choicelist.index(pref)
					self.session.openWithCallback(self.askTimerPath, ChoiceBox, title=_("Timer record location"), list=choicelist, selection=idx)
				else:
					self.session.nav.RecordTimer.saveTimer()
					self.finishedAdd((True, newEntry), True)
			else:
				if AutoTimerHook.AUTOTIMER_OK and config.usage.ask_for_timer_typ.value:
					self.session.openWithCallback(self.askTimerType, ChoiceBox, title=_("Select timer type..."), list=AutoTimerHook.getChoiceList())
				else:
					self.session.openWithCallback(self.finishedAdd, TimerEntry, newEntry)


def EPGSelection_askTimerPath(self, ret=None):
	if ret and ret[0] and os.path.exists(ret[0]):
		cur = self["list"].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		recdesc, recname, begin, end, eit = getRecordName(event)

		newEntry = RecordTimerEntry(serviceref, begin, end, recname, recdesc, eit, False, False, checkOldTimers=True, afterEvent=AFTEREVENT.AUTO, dirname=ret[0], allow_duplicate=config.usage.timer_allow_duplicate.value, tags=None)
		newEntry.repeated = 0
		newEntry.tags = ['Advanced-Event-Library']

		self.session.nav.RecordTimer.saveTimer()
		self.finishedAdd((True, newEntry), True)


def mlist(session, service, **kwargs):
	session.open(AdvancedEventLibrarySystem.Editor, service, session.current_dialog, None, **kwargs)


def main(session, **kwargs):
	session.open(AdvancedEventLibrarySystem.Editor)


def iBshowMovies(session, **kwargs):
	global gSession
#	check MediaInfo
	if os.path.isfile('/usr/lib/enigma2/python/Plugins/Extensions/MediaInfo/plugin.pyc'):
		MoviePlayer.openEventView = openMoviePlayerEventViewMI
	if useMW:
		open_moviewall(gSession)
	else:
		InfoBar.showMovies_org(InfoBar.instance)


def open_moviewall(session, **kwargs):
	global gSession
	while AdvancedEventLibrarySimpleMovieWall.saving:
		pass
		if gSession:
			gSession.openWithCallback(restartMW, AdvancedEventLibrarySimpleMovieWall.AdvancedEventLibrarySimpleMovieWall, viewType.value)
		else:
			session.openWithCallback(restartMW, AdvancedEventLibrarySimpleMovieWall.AdvancedEventLibrarySimpleMovieWall, viewType.value)


def open_primetime(session, **kwargs):
	session.openWithCallback(restartPTP, AdvancedEventLibraryPrimeTime.AdvancedEventLibraryPlanerScreens, viewType.value)


def open_serienstarts(session, **kwargs):
	session.openWithCallback(restartSSP, AdvancedEventLibrarySerienStarts.AdvancedEventLibraryPlanerScreens, viewType.value)


def open_favourites(session, **kwargs):
	session.openWithCallback(restartFav, AdvancedEventLibraryRecommendations.AdvancedEventLibraryPlanerScreens, viewType.value)


def open_channelselection(session, **kwargs):
	session.open(AdvancedEventLibraryChannelSelection.AdvancedEventLibraryChannelSelection)


def open_mediaHub(session, **kwargs):
	session.open(AdvancedEventLibraryMediaHub.AdvancedEventLibraryMediaHub)


def open_aelMenu(session, **kwargs):
	session.open(AdvancedEventLibrarySystem.AELMenu)


def aelMenu_in_mainmenu(menuid, **kwargs):
	if menuid == 'mainmenu':
		return [('Advanced-Event-Library',
		  open_aelMenu,
		  'Advanced-Event-Library',
		  1)]
	return []


def restartMW(ret=None):
	global gSession
	if ret:
		write_log('return ' + str(ret))
		if viewType.value != ret:
			viewType.value = ret
			viewType.save()
			open_moviewall(gSession)


def restartPTP(ret=None):
	global gSession
	if ret:
		write_log('return ' + str(ret))
		if viewType.value != ret:
			viewType.value = ret
			viewType.save()
			open_primetime(gSession)


def restartSSP(ret=None):
	global gSession
	if ret:
		write_log('return ' + str(ret))
		if viewType.value != ret:
			viewType.value = ret
			viewType.save()
			open_serienstarts(gSession)


def restartFav(ret=None):
	global gSession
	if ret:
		write_log('return ' + str(ret))
		if viewType.value != ret:
			viewType.value = ret
			viewType.save()
			open_favourites(gSession)


def EPGSearch__init__(self, session, *args):
	from Components.Sources.ServiceEvent import ServiceEvent
	from Components.Sources.Event import Event
	from Plugins.Extensions.EPGSearch import EPGSearch
	write_log('AEL initialize EPGSearch-Screen')
	Screen.__init__(self, session)
	HelpableScreen.__init__(self)
	self.skinName = ["EPGSearch", "EPGSelection"]
	self["trailer"] = Pixmap()
	self["trailer"].hide()
	self.trailer = None
	self.db = getDB()
	self["popup"] = Label()
	self["popup"].hide()
	self.hidePopup = eTimer()

	self["SelectedEvent"] = StaticText()
	self["ExtEvent"] = ExtEvent()

	self.searchargs = args
	self.currSearch = ""
	self.searchType = eEPGCache.PARTIAL_TITLE_SEARCH  # default search type
	self.search_string = ""

	self.bouquetservices = []
	self.limit_to_bouquet = config.plugins.epgsearch.limit_to_bouquet.value
	self.show_short_description = config.plugins.epgsearch.show_short_description.value
	self.match_type = config.plugins.epgsearch.match_type.value

	# XXX: we lose sort begin/end here
	self["key_yellow"] = Button(_("New Search"))
	self["key_blue"] = Button(_("History"))

	# begin stripped copy of EPGSelection.__init__
	self.switchBouquet = None
	self.bouquetChangeCB = None
	self.serviceChangeCB = None
	self.ask_time = -1  # now
	self["key_red"] = Button(_("Edit Search"))
	self.closeRecursive = False
	self.saved_title = None
	self["Service"] = ServiceEvent()
	self["Event"] = Event()
	self.type = EPG_TYPE_SINGLE
	self.currentService = None
	self.zapFunc = None
	self.sort_type = 0
	self["key_green"] = Button(_("Add timer"))
	self.key_green_choice = self.ADD_TIMER
	self.key_red_choice = self.EMPTY
	self["list"] = EPGSearch.EPGSearchList(type=self.type, selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer)
	self["actions"] = HelpableActionMap(self, "EPGSelectActions",
		{
			"timerAdd": self.timerAdd,
			"timerEnableDisable": self.timerEnableDisable,
			"instantToggleTimerState": self.instantToggleTimerState,
			"instantTimer": self.addInstantTimer,
			"yellow": self.yellowButtonPressed,
			"blue": self.blueButtonPressed,
			"info": self.infoKeyPressed,
			"red": self.redButtonPressed,
			"nextBouquet": self.nextBouquet,  # just used in multi epg yet
			"prevBouquet": self.prevBouquet,  # just used in multi epg yet
			"nextService": self.nextService,  # just used in single epg yet
			"prevService": self.prevService,  # just used in single epg yet
		}, -1)
	self["MenuActions"] = HelpableActionMap(self, "MenuActions",
		{
			"menu": (self.menu, _("Settings")),
		}, -1)
	self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
		{
			"cancel": (self.closeScreen, _("Exit")),
			"ok": (self.eventSelected, _("Select")),
		}, -1)
	self["NumberActions"] = HelpableActionMap(self, "NumberActions",
		{
			"0": (self.Number0, _("Reset search result list")),
			"1": (self.Number1, _("Remove Channel from result list")),
			"3": (self.Number3, _("Keep only this Channel in result list")),
			"4": (self.Number4, _("Remove Event from result list")),
			"5": (self.Number5, _("Toggle: show event short description in result list")),
			"6": (self.Number6, _("Keep only this Event in result list")),
			"7": (self.Number7, _("Match of search string: exact, from begin or any substring")),
			"9": (self.Number9, _("Toggle: search all Channels or only Channels in Bouquet")),
		}, -1)

	self.initTimer = eTimer()
	self.initTimer.callback.append(self.createFinished)

	self["actions"].csel = self
	self.onLayoutFinish.append(self.onCreate)


def autostart(reason, **kwargs):
	if reason == 0:
		try:
		#	check EPGSearch
			if os.path.isfile('/usr/lib/enigma2/python/Plugins/Extensions/EPGSearch/plugin.pyc'):
				from Plugins.Extensions.EPGSearch import plugin as epgS
				from Plugins.Extensions.EPGSearch import EPGSearch
				epgS.autostart = EPGSelectionInit
				EPGSearch.EPGSearch.__init__ = EPGSearch__init__
				write_log('Overwrite EPGSearch EPGSelectionInit')
		except Exception as ex:
			write_log('Fehler in EPGSearch EPGSelectionInit : ' + str(ex))
		try:
		#	check TMDb
			if os.path.isfile('/usr/lib/enigma2/python/Plugins/Extensions/tmdb/plugin.pyc'):
				#config.plugins.tmdb = ConfigSubsection()
				#if config.plugins.tmdb.keyyellow.value:
				from Plugins.Extensions.tmdb import plugin as tmdbP
				tmdbP.autostart = EPGSelectionInit
				write_log('Overwrite TMDb EPGSelectionInit')
		except Exception as ex:
			write_log('Fehler in TMDb EPGSelectionInit : ' + str(ex))


def Plugins(**kwargs):
	epgSearch = PluginDescriptor(where=PluginDescriptor.WHERE_AUTOSTART, fnc=autostart, needsRestart=False, weight=100)
	desc_pluginmenu = PluginDescriptor(name='AEL-Übersicht', description="AEL Menü & Statistik", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=open_aelMenu)
	desc_pluginmenued = PluginDescriptor(name='AEL-Editor', description="Eventinformationen bearbeiten", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main)
	#desc_pluginmenumw = PluginDescriptor(name='AEL-Movie-Lists', description="Advanced-Event-Library-MovieLists", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=open_moviewall)
	desc_pluginmenupt = PluginDescriptor(name='AEL-Prime-Time-Planer', description="Advanced-Event-Library-Prime-Time-Planer", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=open_primetime)
	desc_pluginmenuss = PluginDescriptor(name='AEL-Serien-Starts-Planer', description="Advanced-Event-Library-Serien-Starts-Planer", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=open_serienstarts)
	desc_pluginmenufav = PluginDescriptor(name='AEL-Favoriten-Planer', description="Advanced-Event-Library-Favourites-Planer", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=open_favourites)
	desc_pluginmenucs = PluginDescriptor(name='AEL-Channel-Selection', description="Advanced-Event-Library-Channel-Selection", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=open_channelselection)
	desc_pluginmenuhb = PluginDescriptor(name='AEL-Media-Hub', description="Advanced-Event-Library-Media-Hub", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=open_mediaHub)
	#desc_eventinfocs = PluginDescriptor(name='AEL-Channel-Selection', description="Advanced-Event-Library-Channel-Selection", where=PluginDescriptor.WHERE_EVENTINFO, icon="plugin.png", fnc=open_channelselection)
	#desc_eventinfohb = PluginDescriptor(name='AEL-Media-Hub', description="Advanced-Event-Library-Media-Hub", where=PluginDescriptor.WHERE_EVENTINFO, icon="plugin.png", fnc=open_mediaHub)
	#desc_movielist = PluginDescriptor(name='AdvancedEventLibrary', description=pdesc, where=PluginDescriptor.WHERE_MOVIELIST, icon="plugin.png", fnc=mlist)
	desc_sessionstart = PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc=sessionstart)
	desc_aelmenumainmenu = PluginDescriptor(name='Advanced-Event-Library', description=pdesc, where=PluginDescriptor.WHERE_MENU, icon='plugin.png', fnc=aelMenu_in_mainmenu)
	list = []
	list.append(epgSearch)
	list.append(desc_pluginmenu)
	list.append(desc_pluginmenued)
	#list.append(desc_pluginmenumw)
	list.append(desc_pluginmenupt)
	list.append(desc_pluginmenuss)
	list.append(desc_pluginmenucs)
	list.append(desc_pluginmenuhb)
	list.append(desc_pluginmenufav)
	#list.append(desc_movielist)
	list.append(desc_sessionstart)
	list.append(desc_aelmenumainmenu)
	#list.append(desc_eventinfocs)
	#list.append(desc_eventinfohb)
	return list


class Recommendations(object):
	def __init__(self):
		self.wait = eTimer()
		self.wait.callback.append(self.checkEvent)
		self.processFav = eTimer()
		self.processFav.callback.append(self.newFavourite)
		self.currentService = None
		self.currentEventName = None
		self.epgcache = eEPGCache.getInstance()
		self.db = getDB()
		if fileExists(os.path.join(pluginpath, 'favourites.data')):
			self.favourites = self.load_pickle(os.path.join(pluginpath, 'favourites.data'))
		else:
			self.favourites = {'genres': {}, 'titles': {}}

	def newServiceStarted(self, what):
		self.currentService = what[0]
		if self.wait.isActive():
			self.wait.stop()
		if self.processFav.isActive():
			self.processFav.stop()
		self.wait.startLongTimer(300)

	def checkEvent(self):
		event = self.getEvent()
		if event:
			self.currentEventName = self.convertTitle(event.getEventName())
			self.processFav.startLongTimer(600)

	def newFavourite(self):
		event = self.getEvent()
		if event:
			if self.currentEventName == self.convertTitle(event.getEventName()):
				evt = self.db.getliveTV(event.getEventId(), event.getEventName(), event.getBeginTime())
				if evt:
					genre = (evt[0][14]).strip()
					if len(genre) > 0:
						if genre not in self.favourites['genres']:
							self.favourites['genres'][genre] = [1, time()]
						else:
							self.favourites['genres'][genre][0] += 1
							self.favourites['genres'][genre][1] = time()
				if self.currentEventName not in self.favourites['titles']:
					self.favourites['titles'][self.currentEventName] = [1, time()]
				else:
					self.favourites['titles'][self.currentEventName][0] += 1
					self.favourites['titles'][self.currentEventName][1] = time()
				self.cleanFavorites()
				self.save_pickle(self.favourites, os.path.join(pluginpath, 'favourites.data'))

	def getEvent(self):
		if not self.epgcache.startTimeQuery(eServiceReference(self.currentService), int(time())):
			event = self.epgcache.getNextTimeEntry()
			if event:
				return event
		return None

	def save_pickle(self, data, filename):
		with open(filename, 'wb') as f:
			pickle.dump(data, f)

	def load_pickle(self, filename):
		with open(filename, 'rb') as f:
			data = pickle.load(f)
		return data

	def cleanFavorites(self):
		keys = []
		for k, v in self.favourites['genres'].items():
			if v[1] < (time() - (86400 * favouritesMaxAge.value)):
				keys.append(k)
		if keys:
			for key in keys:
				write_log('remove genre from favourites : ' + str(k))
				del self.favourites['genres'][key]
		keys = []
		for k, v in self.favourites['titles'].items():
			if v[1] < (time() - (86400 * favouritesMaxAge.value)):
				keys.append(k)
		if keys:
			for key in keys:
				write_log('remove title from favourites : ' + str(k))
				del self.favourites['titles'][key]

	def convertTitle(self, name):
		if name.find(' (') > 0:
			regexfinder = re.compile(r"\([12][90]\d{2}\)", re.IGNORECASE)
			ex = regexfinder.findall(name)
			if not ex:
				name = name[:name.find(' (')].strip()
		return name
