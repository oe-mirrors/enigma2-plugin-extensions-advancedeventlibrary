#################################################################################
#							  AdvancedEventLibrary								#
#							Copyright: tsiegel 2019								#
#################################################################################
from os.path import join, realpath, basename, exists
from re import compile, IGNORECASE
from pickle import load, dump
from time import time
from enigma import eEPGCache, eTimer, eServiceReference, addFont
from Components.ActionMap import HelpableActionMap
from Components.Button import Button
from Components.config import config
from Components.EpgList import EPG_TYPE_SINGLE
from Components.FunctionTimer import functionTimer  # TODO: später dann from Janitor import functionTimer
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Plugins.Plugin import PluginDescriptor
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen
from Tools.Directories import fileExists

from . import AdvancedEventLibrarySystem, AdvancedEventLibrarySerienStarts, AdvancedEventLibraryPrimeTime, AdvancedEventLibraryRecommendations, _  # for localized messages
from Tools.AdvancedEventLibrary import getDB, convert2base64, getallEventsfromEPG, createBackup, aelGlobals

gSession = None
ServiceTrack = None
VIEWTYPE = config.plugins.AdvancedEventLibrary.ViewType
addFont(join(aelGlobals.PLUGINPATH, "fonts/Normal.ttf"), 'Normal', 100, False)
addFont(join(aelGlobals.PLUGINPATH, "fonts/Small.ttf"), 'Small', 100, False)


def sessionstart(reason, **kwargs):
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
			functionTimer.add(("AdvancedEventLibraryUpdate", {"name": "Advanced-Event-Library-Update", "fnc": getallEventsfromEPG}))
		if not foundBackup:
			functionTimer.add(("AdvancedEventLibraryBackup", {"name": "Advanced-Event-Library-Backup", "fnc": createBackup}))

#			for evt in systemevents.getSystemEvents():
			#	aelGlobals.write_log('available event : ' + str(systemevents.getfriendlyName(evt)) + ' - ' + str(evt))
#				if (evt == systemevents.RECORD_STOP or evt == systemevents.PVRDESCRAMBLE_STOP):
#					refreshMovieWall = config.plugins.AdvancedEventLibrary.UpdateAELMovieWall.value
#					if refreshMovieData and refreshMovieWall:
#						systemevents.addEventHook(evt, _refreshMovieWall, "refreshMovieWallData_" + evt, evt)
#				if evt == systemevents.SERVICE_START:
#					systemevents.addEventHook(evt, _serviceStart, "newServiceStart_" + evt, evt)


#def _serviceStart(evt, *args):
#		global ServiceTrack
#		# aelGlobals.write_log("new service detected : " + str(args[1]))
#		if len(args) > 0 and ServiceTrack and not Screens.Standby.inStandby:
#			ServiceTrack.newServiceStarted(args)


#def _refreshMovieWall(evt, *args):
#		if len(args) > 0:
#			aelGlobals.write_log('refresh MovieWallData because of : ' + str(evt) + ' args : ' + str(args))
#		if (evt == systemevents.RECORD_START or evt == systemevents.RECORD_STOP or evt == systemevents.PVRDESCRAMBLE_STOP):
#			refreshData = Timer(30, refreshMovieWallData)
#			refreshData.start()


#def refreshMovieWallData():
#	threading.start_new_thread(saveMovieWallData, ())


#def saveMovieWallData():
#	try:
#		if not AdvancedEventLibrarySimpleMovieWall.saving:
#			aelGlobals.write_log("create MovieWall data after new record detected")
#			try:
#				itype = None
#				if isfile('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/imageType.data'):
#					with open('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/imageType.data', 'r') as f:
#						itype = f.read()
#						f.close()
#				if itype:
#					from .AdvancedEventLibrarySimpleMovieWall import saveList
#					saveList(itype)
#					aelGlobals.write_log("MovieWall data saved with " + str(itype))
#			except Exception as ex:
#				aelGlobals.write_log('save moviewall data : ' + str(ex))
#	except:
#		aelGlobals.write_log('saveMovieWallData ' + str(ex))


def cancelTimerFunction():
	print("[Advanced-Event-Library-Update] Aufgabe beendet!")


def getMovieDescriptionFromTXT(ref):
	f = None
	extended_desc = ""
	name = ""
	extensions = (".txt", ".info")
	info_file = realpath(ref.getPath())
	name = basename(info_file)
	ext_pos = name.rfind('.')
	if ext_pos > 0:
		name = (name[:ext_pos]).replace("_", " ")
	else:
		name = name.replace("_", " ")
	for ext in extensions:
		if exists(info_file + ext):
			f = info_file + ext
			break
	if not f:
		ext_pos = info_file.rfind('.')
		name_len = len(info_file)
		ext_len = name_len - ext_pos
		if ext_len <= 5:
			info_file = info_file[:ext_pos]
			for ext in extensions:
				if exists(info_file + ext):
					f = info_file + ext
					break
	if f:
		try:
			with open(f, "r") as txtfile:
				extended_desc = txtfile.read()
		except OSError:
			pass

	return (name, extended_desc)


def mlist(session, service, **kwargs):
	session.open(AdvancedEventLibrarySystem.Editor, service, session.current_dialog, None, **kwargs)


def main(session, **kwargs):
	session.open(AdvancedEventLibrarySystem.Editor)


def open_primetime(session, **kwargs):
	session.openWithCallback(restartPTP, AdvancedEventLibraryPrimeTime.AdvancedEventLibraryPlanerScreens, VIEWTYPE.value)


def open_serienstarts(session, **kwargs):
	session.openWithCallback(restartSSP, AdvancedEventLibrarySerienStarts.AdvancedEventLibraryPlanerScreens, VIEWTYPE.value)


def open_favourites(session, **kwargs):
	session.openWithCallback(restartFav, AdvancedEventLibraryRecommendations.AdvancedEventLibraryPlanerScreens, VIEWTYPE.value)


def open_aelMenu(session, **kwargs):  # Einstieg mit 'AEL-Übersicht'
	session.open(AdvancedEventLibrarySystem.AELMenu)


def aelMenu_in_mainmenu(menuid, **kwargs):
	if menuid == 'mainmenu':
		return [('Advanced-Event-Library',
		  open_aelMenu,
		  'Advanced-Event-Library',
		  1)]
	return []


def restartPTP(ret=None):
	global gSession
	if ret:
		aelGlobals.write_log('return ' + str(ret))
		if VIEWTYPE.value != ret:
			VIEWTYPE.value = ret
			VIEWTYPE.save()
			open_primetime(gSession)


def restartSSP(ret=None):
	global gSession
	if ret:
		aelGlobals.write_log('return ' + str(ret))
		if VIEWTYPE.value != ret:
			VIEWTYPE.value = ret
			VIEWTYPE.save()
			open_serienstarts(gSession)


def restartFav(ret=None):
	global gSession
	if ret:
		aelGlobals.write_log('return ' + str(ret))
		if VIEWTYPE.value != ret:
			VIEWTYPE.value = ret
			VIEWTYPE.save()
			open_favourites(gSession)


def EPGSearch__init__(self, session, *args):
	from Components.Sources.ExtEvent import ExtEvent
	from Components.Sources.ServiceEvent import ServiceEvent
	from Components.Sources.Event import Event
	from Plugins.Extensions.EPGSearch import EPGSearch
	aelGlobals.write_log('AEL initialize EPGSearch-Screen')
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
		return


def Plugins(**kwargs):
	epgSearch = PluginDescriptor(where=PluginDescriptor.WHERE_AUTOSTART, fnc=autostart, needsRestart=False, weight=100)
	desc_pluginmenu = PluginDescriptor(name='AEL-Übersicht', description="AEL Menü & Statistik", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=open_aelMenu)
	desc_pluginmenued = PluginDescriptor(name='AEL-Editor', description="Eventinformationen bearbeiten", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main)
	desc_pluginmenupt = PluginDescriptor(name='AEL-Prime-Time-Planer', description="Advanced-Event-Library-Prime-Time-Planer", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=open_primetime)
	desc_pluginmenuss = PluginDescriptor(name='AEL-Serien-Starts-Planer', description="Advanced-Event-Library-Serien-Starts-Planer", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=open_serienstarts)
	desc_pluginmenufav = PluginDescriptor(name='AEL-Favoriten-Planer', description="Advanced-Event-Library-Favourites-Planer", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=open_favourites)
	desc_sessionstart = PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc=sessionstart)
	desc_aelmenumainmenu = PluginDescriptor(name='Advanced-Event-Library', description="AdvancedEventLibrary", where=PluginDescriptor.WHERE_MENU, icon='plugin.png', fnc=aelMenu_in_mainmenu)
	list = []
	list.append(epgSearch)
	list.append(desc_pluginmenu)
	list.append(desc_pluginmenued)
	list.append(desc_pluginmenupt)
	list.append(desc_pluginmenuss)
	list.append(desc_pluginmenufav)
	list.append(desc_sessionstart)
	list.append(desc_aelmenumainmenu)
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
		if fileExists(join(aelGlobals.PLUGINPATH, 'favourites.data')):
			self.favourites = self.load_pickle(join(aelGlobals.PLUGINPATH, 'favourites.data'))
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
		if event and self.currentEventName == self.convertTitle(event.getEventName()):
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
			self.save_pickle(self.favourites, join(aelGlobals.PLUGINPATH, 'favourites.data'))

	def getEvent(self):
		if not self.epgcache.startTimeQuery(eServiceReference(self.currentService), int(time())):
			event = self.epgcache.getNextTimeEntry()
			if event:
				return event

	def save_pickle(self, data, filename):
		with open(filename, 'wb') as f:
			dump(data, f)

	def load_pickle(self, filename):
		with open(filename, 'rb') as f:
			data = load(f)
		return data

	def cleanFavorites(self):
		k = 0
		keys = []
		favouritesMaxAge = config.plugins.AdvancedEventLibrary.FavouritesMaxAge.value
		for k, v in self.favourites['genres'].items():
			if v[1] < (time() - (86400 * favouritesMaxAge)):
				keys.append(k)
		if keys:
			for key in keys:
				aelGlobals.write_log('remove genre from favourites : ' + str(k))
				del self.favourites['genres'][key]
		keys = []
		for k, v in self.favourites['titles'].items():
			if v[1] < (time() - (86400 * favouritesMaxAge)):
				keys.append(k)
		if keys:
			for key in keys:
				aelGlobals.write_log('remove title from favourites : ' + str(k))
				del self.favourites['titles'][key]

	def convertTitle(self, name):
		if name.find(' (') > 0:
			regexfinder = compile(r"\([12][90]\d{2}\)", IGNORECASE)
			ex = regexfinder.findall(name)
			if not ex:
				name = name[:name.find(' (')].strip()
		return name
