#################################################################################
#							  AdvancedEventLibrary								#
#							Copyright: tsiegel 2019								#
#################################################################################
from os.path import join, realpath, basename, exists
from re import compile, IGNORECASE
from pickle import load, dump
from time import time
from enigma import eEPGCache, eTimer, eServiceReference, addFont
from Components.config import config
from Plugins.Plugin import PluginDescriptor
from Scheduler import functionTimer
from Tools.Directories import fileExists

from . import AdvancedEventLibrarySystem, AdvancedEventLibrarySerienStarts, AdvancedEventLibraryPrimeTime, AdvancedEventLibraryChannelSelection, AdvancedEventLibraryMediaHub, AdvancedEventLibraryRecommendations
from Tools.AdvancedEventLibrary import aelGlobals, aelHelper

DEFAULT_MODULE_NAME = __name__.split(".")[-1]
gSession = None
ServiceTrack = None
addFont(join(aelGlobals.PLUGINPATH, "fonts/Normal.ttf"), 'Normal', 100, False)
addFont(join(aelGlobals.PLUGINPATH, "fonts/Small.ttf"), 'Small', 100, False)
addFont(join(aelGlobals.PLUGINPATH, "fonts/andale.ttf"), 'andale', 100, False)  # liegt auch in '/usr/share/fonts'


def sessionstart(reason, **kwargs):
	if 'session' in kwargs and reason == 0:
		global ServiceTrack
		ServiceTrack = Recommendations()
		global gSession
		gSession = kwargs["session"]
		foundTimer = False
		foundBackup = False
		aelHelper.setRequestLoggingLevel()
		fTimers = functionTimer.get()
		for fTimer in fTimers:
			if 'AdvancedEventLibraryUpdate' in fTimer:
				foundTimer = True
			if 'AdvancedEventLibraryBackup' in fTimer:
				foundBackup = True
		if not foundTimer:
			functionTimer.add(("AdvancedEventLibraryUpdate", {"name": "Advanced-Event-Library-Update", "fnc": aelHelper.getallEventsfromEPG}))
		if not foundBackup:
			functionTimer.add(("AdvancedEventLibraryBackup", {"name": "Advanced-Event-Library-Backup", "fnc": aelHelper.createBackup}))
#			for evt in systemevents.getSystemEvents():
			#	writeLog('available event : ' + str(systemevents.getfriendlyName(evt)) + ' - ' + str(evt), DEFAULT_MODULE_NAME)
#				if (evt == systemevents.RECORD_STOP or evt == systemevents.PVRDESCRAMBLE_STOP):
#					refreshMovieWall = config.plugins.AdvancedEventLibrary.UpdateAELMovieWall.value
#					if refreshMovieData and refreshMovieWall:
#						systemevents.addEventHook(evt, _refreshMovieWall, "refreshMovieWallData_" + evt, evt)
#				if evt == systemevents.SERVICE_START:
#					systemevents.addEventHook(evt, _serviceStart, "newServiceStart_" + evt, evt)


#def _serviceStart(evt, *args):
#		global ServiceTrack
#		# writeLog("new service detected : " + str(args[1]), DEFAULT_MODULE_NAME)
#		if len(args) > 0 and ServiceTrack and not Screens.Standby.inStandby:
#			ServiceTrack.newServiceStarted(args)


#def _refreshMovieWall(evt, *args):
#		if len(args) > 0:
#			writeLog('refresh MovieWallData because of : ' + str(evt) + ' args : ' + str(args), DEFAULT_MODULE_NAME)
#		if (evt == systemevents.RECORD_START or evt == systemevents.RECORD_STOP or evt == systemevents.PVRDESCRAMBLE_STOP):
#			refreshData = Timer(30, refreshMovieWallData)
#			refreshData.start()


#def refreshMovieWallData():
#	threading.start_new_thread(saveMovieWallData, ())


#def saveMovieWallData():
#	try:
#		if not AdvancedEventLibrarySimpleMovieWall.saving:
#			writeLog("create MovieWall data after new record detected", DEFAULT_MODULE_NAME)
#			try:
#				itype = None
#				if isfile('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/imageType.data'):
#					with open('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/imageType.data', 'r') as f:
#						itype = f.read()
#						f.close()
#				if itype:
#					from .AdvancedEventLibrarySimpleMovieWall import saveList
#					saveList(itype)
#					writeLog("MovieWall data saved with " + str(itype), DEFAULT_MODULE_NAME)
#			except Exception as ex:
#				writeLog('save moviewall data : ' + str(ex), DEFAULT_MODULE_NAME)
#	except:
#		writeLog('saveMovieWallData ' + str(ex), DEFAULT_MODULE_NAME)


def cancelTimerFunction():
	aelHelper.writeLog("[Advanced-Event-Library-Update] Aufgabe beendet!", DEFAULT_MODULE_NAME)


def getMovieDescriptionFromTXT(ref):
	f = None
	extended_desc = ""
	name = ""
	extensions = (".txt", ".info")
	info_file = realpath(ref.getPath())
	name = basename(info_file)
	ext_pos = name.rfind('.')
	name = (name[:ext_pos]).replace("_", " ") if ext_pos > 0 else name.replace("_", " ")
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
	session.open(AdvancedEventLibraryPrimeTime.AdvancedEventLibraryPlanerScreens, 1)  # = "Listenansicht"


def open_serienstarts(session, **kwargs):
	session.open(AdvancedEventLibrarySerienStarts.AdvancedEventLibraryPlanerScreens, 1)  # = "Listenansicht"


def open_favourites(session, **kwargs):
	session.open(AdvancedEventLibraryRecommendations.AdvancedEventLibraryPlanerScreens, 1)  # = "Listenansicht"


def open_channelselection(session, **kwargs):
	session.open(AdvancedEventLibraryChannelSelection.AdvancedEventLibraryChannelSelection)


def open_mediaHub(session, **kwargs):
	session.open(AdvancedEventLibraryMediaHub.AdvancedEventLibraryMediaHub)


def open_aelMenu(session, **kwargs):  # Einstieg mit 'AEL-Übersicht'
	session.open(AdvancedEventLibrarySystem.AELMenu)


def aelMenu_in_mainmenu(menuid, **kwargs):
	if menuid == 'mainmenu':
		return [('Advanced-Event-Library', open_aelMenu, 'Advanced-Event-Library', 1)]
	return []


def autostart(reason, **kwargs):
	if reason == 0:
		return


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
	#desc_eventinfohb = PluginDescriptor(name='AEL-Media-Hub', description="Advanced-Event-Library-Media-Hub", where=PluginDescriptor.WHERE_EVENTINFO, icon="plugin.png", fnc=open_mediaHub)
	#desc_movielist = PluginDescriptor(name='AdvancedEventLibrary', description="AdvancedEventLibrary", where=PluginDescriptor.WHERE_MOVIELIST, icon="plugin.png", fnc=mlist)
	desc_sessionstart = PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc=sessionstart)
	desc_aelmenumainmenu = PluginDescriptor(name='Advanced-Event-Library', description="AdvancedEventLibrary", where=PluginDescriptor.WHERE_MENU, icon='plugin.png', fnc=aelMenu_in_mainmenu)
	plist = []
	plist.append(epgSearch)
	plist.append(desc_pluginmenu)
	plist.append(desc_pluginmenued)
	plist.append(desc_pluginmenupt)
	plist.append(desc_pluginmenuss)
	plist.append(desc_pluginmenufav)
	plist.append(desc_pluginmenuhb)
	plist.append(desc_pluginmenucs)
	plist.append(desc_sessionstart)
	plist.append(desc_aelmenumainmenu)
	return plist


class Recommendations(object):
	def __init__(self):
		self.wait = eTimer()
		self.wait.callback.append(self.checkEvent)
		self.processFav = eTimer()
		self.processFav.callback.append(self.newFavourite)
		self.currentService = None
		self.currentEventName = None
		self.epgcache = eEPGCache.getInstance()
		self.db = aelHelper.getDB()
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
				aelHelper.writeLog('remove genre from favourites : ' + str(k))
				del self.favourites['genres'][key]
		keys = []
		for k, v in self.favourites['titles'].items():
			if v[1] < (time() - (86400 * favouritesMaxAge)):
				keys.append(k)
		if keys:
			for key in keys:
				aelHelper.writeLog('remove title from favourites : ' + str(k))
				del self.favourites['titles'][key]

	def convertTitle(self, name):
		if name.find(' (') > 0:
			regexfinder = compile(r"\([12][90]\d{2}\)", IGNORECASE)
			ex = regexfinder.findall(name)
			if not ex:
				name = name[:name.find(' (')].strip()
		return name
