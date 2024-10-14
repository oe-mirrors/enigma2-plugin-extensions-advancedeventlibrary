#=================================================
# R141 by MyFriendVTI
# usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/AdvancedEventLibrarySystem.py
# Aenderungen kommentiert mit hinzugefuegt, geaendert oder geloescht
# Aenderung (#0): Versionsnummer
# Aenderung (#1): Option Update Moviewall after RecordStart [Einst. fuer plugin.py]
# Aenderung (#2): Option Serienerk. bei der Sortierung ignoriern [Einst. fuer AdvancedEventLibrarySimpleMovieWall.py]
# Enfernt AELImageServer
# Aenderung (#3): Fix: Uebernahme Däfen im Editor mit Exit
# Aenderung (#4): Rating von LiveOnTV entfernt
# Hinzugefuegt (#5): Default-Werte einstellbar fuer neue Bouquests/Bookmarks (Suche)
# Hinzugefuegt (#6): Search-Options bereingen mit KeyBlue
# Aenderung (#7): Fix: Such-Einstellungen (True/False bei Lesezeichen in Unterordner)
# Aenderung (#8): Fix: IPTV-Sender in TVSSetup
# ==================================================

from base64 import b64decode
from datetime import datetime
from glob import glob
from json import loads, dumps
from os import rename, system, remove, stat, statvfs
from os.path import isfile, getsize, exists, join, basename
from PIL import Image
from re import match, compile, IGNORECASE
from shutil import copy
from twisted.internet.reactor import callInThread
from enigma import eTimer, eServiceReference, eServiceCenter
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.config import config, ConfigText, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Sources.ServiceList import ServiceList
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.ChannelSelection import service_types_tv
from Screens.ChoiceBox import ChoiceBox
from Screens.LocationBox import defaultInhibitDirs, LocationBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup
#from Screens.Standby import TryQuitMainloop
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.Directories import fileExists
from Tools.LoadPixmap import LoadPixmap
from .AdvancedEventLibraryLists import ImageList, SearchResultsList
from Tools.AdvancedEventLibrary import aelGlobals, getDB, getSizeStr, startUpdate, createDirs, createBackup, getAPIdata, write_log, convertSearchName, convertDateInFileName, createSingleThumbnail, reduceSigleImageSize, convert2base64, get_searchResults, checkAllImages, convertTitle, convertTitle2, getImageFile, get_PictureList, clearMem, PicLoader

from . import _  # for localized messages

DEFAULT_MODULE_NAME = __name__.split(".")[-1]


def loadskin(filename):
	with open(join(aelGlobals.SKINPATH, filename), "r") as f:
		skin = f.read()
		f.close()
	return skin


class AELMenu(Screen):  # Einstieg mit 'AEL-Übersicht'
	ALLOW_SUSPEND = True
	skin = str(loadskin("AdvancedEventLibraryMenu.xml"))

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		write_log("##### starting Advanced Event Library GUI #####")
		self.skinName = 'Advanced-Event-Library-Menu'
		self.title = f"{_('Advanced-Event-Library Menüauswahl')}: (R{aelGlobals.CURRENTVERSION})"
		self.memInfo = ""
		self.statistic = ""
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Start scan"))
		self["key_yellow"] = StaticText(_("Create backup"))
		self["key_blue"] = StaticText(_("Create TVS reference"))
		#=============== geaendert (#6) ================
		#self["key_blue"] = StaticText("")
		#self["key_blue"] = StaticText(_("Bereinigen"))
		# ==*=========================================
		self["info"] = StaticText("")
		self["status"] = StaticText("")
		imgpath = join(aelGlobals.SHAREPATH, "AELImages/")
		self.menulist = [('Settings', _('Making basic settings for AEL'), LoadPixmap(imgpath + 'settings.png'), 'setup'),
				   		('Editor', _('Edit event information'), LoadPixmap(imgpath + 'keyboard.png'), 'editor'),
						('Prime-Time-Planer', 'shows prime-time programs sorted by genre', LoadPixmap(imgpath + 'primetime.png'), 'ptp'),
						('Serien-Starts-Planer', 'shows current series and season starts', LoadPixmap(imgpath + 'serien.png'), 'ssp'),
						('Favoriten-Planer', 'Your recommendations on TV', LoadPixmap(imgpath + 'favoriten.png'), 'fav'),
						('Simple-Movie-Wall', 'Displays recordings in wall format', LoadPixmap(imgpath + 'movies.png'), 'smw'),
						('AEL-Channel-Selection', 'Displays AEL channel overview', LoadPixmap(imgpath + 'sender.png'), 'scs'),
						('AEL-Media-Hub', 'News from TV/recordings', LoadPixmap(imgpath + 'mediahub.png'), 'hub')
						]
		self["menulist"] = List(self.menulist, enableWrapAround=True)
		self["myActionMap"] = ActionMap(["AdvancedEventLibraryActions"],
		{
			"key_cancel": self.do_close,
			"key_red": self.do_close,
			"key_green": self.key_green_handler,
			"key_yellow": self.key_yellow_handler,
			"key_blue": self.key_blue_handler,
			"key_ok": self.key_ok_handler,
		}, -1)
		self.refreshStatus = eTimer()
		self.refreshStatus.callback.append(self.getStatus)
		self.reload = eTimer()
		self.reload.callback.append(self.goReload)
		self.delayedStart = eTimer()
		self.delayedStart.callback.append(self.readMandatoryFiles)  # unfortunately necessary, because self.session.open(MessageBox,...) returns a modal error
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.delayedStart.start(250, True)
		self.getStatus()
		self.db = getDB()
		confdir = join(aelGlobals.CONFIGPATH, "eventLibrary.db") if config.plugins.AdvancedEventLibrary.dbFolder.value == "Flash" else f"{config.plugins.AdvancedEventLibrary.Location.value}eventLibrary.db"
		if isfile(confdir):
			posterCount = self.db.parameter(aelGlobals.PARAMETER_GET, 'posterCount', None, 0)
			posterSize = str(self.db.parameter(aelGlobals.PARAMETER_GET, 'posterSize', None, 0))
			coverCount = self.db.parameter(aelGlobals.PARAMETER_GET, 'coverCount', None, 0)
			coverSize = str(self.db.parameter(aelGlobals.PARAMETER_GET, 'coverSize', None, 0))
			previewCount = self.db.parameter(aelGlobals.PARAMETER_GET, 'previewCount', None, 0)
			previewSize = str(self.db.parameter(aelGlobals.PARAMETER_GET, 'previewSize', None, 0))
			usedInodes = self.db.parameter(aelGlobals.PARAMETER_GET, 'usedInodes', None, 0)
			lastposterCount = self.db.parameter(aelGlobals.PARAMETER_GET, 'lastposterCount', None, 0)
			lastcoverCount = self.db.parameter(aelGlobals.PARAMETER_GET, 'lastcoverCount', None, 0)
			lasteventInfoCount = str(self.db.parameter(aelGlobals.PARAMETER_GET, 'lasteventInfoCount', None, 0))
			lasteventInfoCountSuccsess = str(self.db.parameter(aelGlobals.PARAMETER_GET, 'lasteventInfoCountSuccsess', None, 0))
			lastpreviewImageCount = str(self.db.parameter(aelGlobals.PARAMETER_GET, 'lastpreviewImageCount', None, 0))
			lastadditionalDataCount = str(self.db.parameter(aelGlobals.PARAMETER_GET, 'lastadditionalDataCount', None, 0))
			lastadditionalDataCountBlacklist = str(self.db.parameter(aelGlobals.PARAMETER_GET, 'lastadditionalDataCountSuccess', None, 0))
			lastadditionalDataCountSuccess = int(lastadditionalDataCount) - int(lastadditionalDataCountBlacklist)
			lastUpdateStart, lastUpdateDuration = self.getlastUpdateInfo(self.db)
			dbSize = getsize(confdir) / 1024.0
			titleCount = self.db.getTitleInfoCount()
			blackListCount = self.db.getblackListCount()
			percent = round(100 * titleCount / (titleCount + blackListCount)) if (titleCount + blackListCount) > 0 else 0
			liveTVtitleCount = self.db.getliveTVCount()
			liveTVidtitleCount = self.db.getliveTVidCount()
			percentTV = round(100 * liveTVidtitleCount / liveTVtitleCount) if (liveTVidtitleCount + liveTVtitleCount) > 0 else 0
			percentlIC = round(100 * int(lasteventInfoCountSuccsess) / int(lasteventInfoCount)) if int(lasteventInfoCount) > 0 else 0
			percentlaC = round(100 * int(lastadditionalDataCountSuccess) / int(lastadditionalDataCount)) if int(lastadditionalDataCount) > 0 else 0
			cpS = round(float(posterSize.replace('G', '')) * 1024.0, 2) if 'G' in posterSize else posterSize
			ccS = round(float(coverSize.replace('G', '')) * 1024.0, 2) if 'G' in coverSize else coverSize
			pcS = round(float(previewSize.replace('G', '')) * 1024.0, 2) if 'G' in previewSize else previewSize
			trailers = self.db.getTrailerCount()
			size = int(float(str(cpS).replace('G', '').replace('M', '').replace('kB', '').replace('K', '')) + float(str(ccS).replace('G', '').replace('M', '').replace('kB', '').replace('K', '')) + float(str(pcS).replace('G', '').replace('M', '').replace('kB', '').replace('K', '')) + round(float(dbSize / 1024.0), 1))
			statistic = f"{_('Statistics last search run:')}\n"
			statistic += f"{_('Number of posters | Cover | Preview images:')} {lastposterCount} | {lastcoverCount} | {lastpreviewImageCount}\n"
			statistic += f"{_('Event information:')}\t{lasteventInfoCount}\tfound:\t{lasteventInfoCountSuccsess} | {percentlIC} %\n"
			statistic += f"{_('Extra data sought:')}\t{lastadditionalDataCount}\t{_('found:')}\t{lastadditionalDataCountSuccess} | {percentlaC} %\n"
			statistic += f"{_('Executed on:')}\t{lastUpdateStart} h\t{_('Duration:')}\t{lastUpdateDuration} h\n\n"
			statistic += f"{_('Total statistics:')}\n"
			statistic += f"{_('Number of posters:')}\t{posterCount} {_('Size:')} {posterSize}\n"
			statistic += f"{_('Number of previews:')}\t{previewCount} {_('Size:')} {previewSize}\n"
			statistic += f"{_('Number of trailers:')}\t{trailers}\n"
			statistic += f"{_('Database size:')}\t{dbSize} KB\n"
			statistic += f"{_('Entries:')}\t{'{:5d}'.format(titleCount)} | {'{:5d}'.format(blackListCount)} | {'{:3d}'.format(percent)} %\n"
			statistic += f"{_('Extra data:')}\t{'{:5d}'.format(liveTVtitleCount)} | {'{:5d}'.format(liveTVidtitleCount)} | {'{:3d}'.format(percentTV)} %\n"
			statistic += f"{_('Storage space:')}\t{size} / {int(config.plugins.AdvancedEventLibrary.MaxSize.value * 1024.0)} MB\t{_('Inodes used:')}\t{usedInodes}\n"
			self.statistic = statistic
			memInfo = f"\n{_('Memory allocation:')}\n{self.getDiskInfo('/')}{self.getMemInfo('Mem')}"
			memInfo += f"\n{_('Mountpoints:')}\n{self.getDiskInfo()}"
			self.memInfo = memInfo
			self["info"].setText(f"{self.statistic}{self.memInfo}")
		else:
			self["info"].setText('No data has been found yet.')
		del self.db

	def getMemInfo(self, value):
		result = [0, 0, 0, 0]  # (size, used, avail, use%)
		check = 0
		fd = open("/proc/meminfo")
		for line in fd:
			if value + "Total" in line:
				check += 1
				result[0] = int(line.split()[1]) * 1024		# size
			elif value + "Free" in line:
				check += 1
				result[2] = int(line.split()[1]) * 1024		# avail
			if check > 1:
				if result[0] > 0:
					result[1] = result[0] - result[2]  # used
					result[3] = result[1] * 100 // result[0]  # use%
				break
		fd.close()
		return f"{_('RAM')}:\t{getSizeStr(result[0])}\t{_('free')}: {getSizeStr(result[2])}\t{_('Occupied')}: {getSizeStr(result[1])} ({result[3]}%)\n"

	def getDiskInfo(self, path=None):
		def getMountPoints():
			mounts = []
			fd = open('/proc/mounts', 'r')
			for line in fd:
				ln = line.split()
				if len(ln) > 1:
					mounts.append(ln[1])
			fd.close()
			return mounts
		resultList = []
		mountPoints = [path] if path else getMountPoints()
		for mountPoint in mountPoints:
			st = None
			if '/media' in mountPoint or path:
				st = statvfs(mountPoint)
			if st is not None and 0 not in (st.f_bsize, st.f_blocks):
				result = [0, 0, 0, 0, mountPoint.replace('/media/net/autonet', '/...').replace('/media/net', '/...')]  # (size, used, avail, use%)
				result[0] = st.f_bsize * st.f_blocks  # size
				result[2] = st.f_bsize * st.f_bavail  # avail
				result[1] = result[0] - result[2]  # used
				result[3] = result[1] * 100 // result[0]  # use%
				resultList.append(result)
		res = ""
		for result in resultList:
			res += f"{result[4]} :\t{getSizeStr(result[0])}\t{_('Free')}: {getSizeStr(result[2])}\t{_('Occupied')}: {getSizeStr(result[1])} ({result[3]}%)\n"
		return res.replace('/ :', _('Flash:'))

	def getlastUpdateInfo(self, db):
		lastUpdateStart = self.convertTimestamp(db.parameter(aelGlobals.PARAMETER_GET, 'laststart', None, 0))
		lastUpdateDuration = self.convertDuration(float(db.parameter(aelGlobals.PARAMETER_GET, 'laststop', None, 0)) - float(db.parameter(aelGlobals.PARAMETER_GET, 'laststart', None, 0)) - 3600)
		return lastUpdateStart, lastUpdateDuration

	def convertTimestamp(self, val):
		value = datetime.fromtimestamp(float(val))
		return value.strftime('%d.%m. %H:%M')

	def convertDuration(self, val):
		value = datetime.fromtimestamp(float(val))
		return value.strftime('%H:%M:%S')

	def readMandatoryFiles(self):
		self.delayedStart.stop()
		if exists(aelGlobals.NETWORKFILE):
			try:
				with open(aelGlobals.NETWORKFILE, "r") as file:
					aelGlobals.NETWORKDICT = loads(file.read())
					write_log(f"AEL network file '{aelGlobals.NETWORKFILE}' successfully loaded.")
			except Exception as errmsg:
				write_log(f"Exception in module 'readMandatoryFiles' for AEL networks file '{aelGlobals.NETWORKFILE}': {errmsg}")
				self.session.open(MessageBox, _("Exception error while reading AEL networks file '%s': %s\nCan't continue Advanced Event Library!" % (aelGlobals.NETWORKFILE, errmsg)), MessageBox.TYPE_ERROR, timeout=10, close_on_any_key=True)
				self.do_close()
		else:
			write_log(f"Error in module 'readMandatoryFiles': AEL networks file '{aelGlobals.NETWORKFILE}' not found.")
			self.session.open(MessageBox, _("AEL networks file '%s' not found.\nCan't continue Advanced Event Library!" % aelGlobals.NETWORKFILE), MessageBox.TYPE_ERROR, timeout=10, close_on_any_key=True)
			self.do_close()
		if exists(aelGlobals.TVS_REFFILE):
			try:
				with open(aelGlobals.TVS_REFFILE, "r") as file:
					aelGlobals.TVS_REFDICT = loads(file.read())
					write_log(f"TV Spielfilm reference file '{aelGlobals.TVS_REFFILE}' successfully loaded.")
			except Exception as errmsg:
				write_log(f"Exception in module 'readMandatoryFiles' for TVS reference file '{aelGlobals.TVS_REFFILE}': {errmsg}")
				self.session.open(MessageBox, _("Exception error while reading file '%s': %s\nTV Spielfilm services can't be supported at all!" % (aelGlobals.TVS_REFFILE, errmsg)), MessageBox.TYPE_ERROR, timeout=10, close_on_any_key=True)
		else:
			write_log(f"Error in module 'readMandatoryFiles': TVS reference file '{aelGlobals.TVS_REFFILE}' not found.")
			msg = _("TV Spielfilm reference file '%s' not found.\nTV Spielfilm services can't be supported at all!\n\nDo you now want to create this reference file starting TVS import?" % aelGlobals.TVS_REFFILE)
			self.session.openWithCallback(self.TVSimport_answer, MessageBox, msg, MessageBox.TYPE_YESNO, timeout=10, default=True)

	def TVSimport_answer(self, answer):
		if answer is True:
			self.key_blue_handler()

	def key_ok_handler(self):
		current = self["menulist"].getCurrent()
		if current:
			if current[3] == 'setup':
				self.main()
				if config.plugins.AdvancedEventLibrary.CloseMenu.value:
					self.do_close()
			elif current[3] == 'editor':
				self.editor()
				if config.plugins.AdvancedEventLibrary.CloseMenu.value:
					self.do_close()
			elif current[3] == 'ptp':
				self.open_primetime()
			elif current[3] == 'ssp':
				self.open_serienstarts()
			elif current[3] == 'smw':
				self.open_moviewall()
			elif current[3] == 'scs':
				self.open_channelSelection()
			elif current[3] == 'hub':
				self.open_mediaHub()
			elif current[3] == 'fav':
				self.open_favourites()

	def key_green_handler(self):
		if exists(aelGlobals.TVS_REFFILE):
			self["status"].setText(_("start search run..."))
			createDirs(config.plugins.AdvancedEventLibrary.Location.value)
			startUpdate()
		else:
			msg = _("The TVS reference file was not found.\nTV Spielfilm can therefore not be supported!\n\nShould a bouquets import be carried out now (recommended)?")
			self.session.openWithCallback(self.key_green_answer, MessageBox, msg, MessageBox.TYPE_YESNO, timeout=5, default=False)

	def key_green_answer(self, answer):
		if answer is True:
			self.key_blue_handler()
		else:
			startUpdate()

	def key_yellow_handler(self):
		callInThread(createBackup)

	def key_blue_handler(self):
		self.session.open(TVSmakeReferenceFile)

	def getStatus(self):
		self["status"].setText(aelGlobals.STATUS if aelGlobals.STATUS else _("No search is currently running."))
		self.memInfo = f"\nSpeicherbelegung :\n{self.getDiskInfo('/')}"
		self.memInfo += str(self.getMemInfo('Mem'))
		self.memInfo += f"\nMountpoints:\n{self.getDiskInfo()}"
		self["info"].setText(f"{self.statistic}{self.memInfo}")
		self.refreshStatus.start(3000, True)

	def do_close(self):
		if self.refreshStatus.isActive():
			self.refreshStatus.stop()
		self.close()

	def open_serienstarts(self):
		from .AdvancedEventLibrarySerienStarts import AdvancedEventLibraryPlanerScreens
		#self.viewType = config.plugins.AdvancedEventLibrary.ViewType.value
		self.screenType = 0
		self.session.openWithCallback(self.goRestart, AdvancedEventLibraryPlanerScreens, "Listenansicht")

	def open_primetime(self):
		from .AdvancedEventLibraryPrimeTime import AdvancedEventLibraryPlanerScreens
		#self.viewType = config.plugins.AdvancedEventLibrary.ViewType.value
		self.screenType = 1
		self.session.openWithCallback(self.goRestart, AdvancedEventLibraryPlanerScreens, "Listenansicht")

	def open_moviewall(self):
		while aelGlobals.saving:
			pass
		from .AdvancedEventLibrarySimpleMovieWall import AdvancedEventLibrarySimpleMovieWall
		#self.viewType = config.plugins.AdvancedEventLibrary.ViewType.value
		self.screenType = 2
		self.session.openWithCallback(self.goRestart, AdvancedEventLibrarySimpleMovieWall, "Listenansicht")

	def open_favourites(self):  # reload_module(AdvancedEventLibraryRecommendations)
		from .AdvancedEventLibraryRecommendations import AdvancedEventLibraryPlanerScreens
		#self.viewType = config.plugins.AdvancedEventLibrary.ViewType.value
		self.screenType = 3
		self.session.openWithCallback(self.goRestart, AdvancedEventLibraryPlanerScreens, "Listenansicht")

	def open_channelSelection(self):
		from .AdvancedEventLibraryChannelSelection import AdvancedEventLibraryChannelSelection
		self.session.open(AdvancedEventLibraryChannelSelection)

	def open_mediaHub(self):
		from .AdvancedEventLibraryMediaHub import AdvancedEventLibraryMediaHub
		self.session.open(AdvancedEventLibraryMediaHub)

	def main(self):
		self.session.open(AdvancedEventLibrarySetup)

	def editor(self):
		self.session.open(Editor)

	def goRestart(self, ret=None):
#		if ret:
#			write_log(f"return {ret}", DEFAULT_MODULE_NAME)
#			config.plugins.AdvancedEventLibrary.ViewType.value = ret
#			config.plugins.AdvancedEventLibrary.ViewType.save()
#		if self.viewType != config.plugins.AdvancedEventLibrary.ViewType.value:
#			self.reload.start(50, True)
#		else:
		if config.plugins.AdvancedEventLibrary.CloseMenu.value:
			self.do_close()

	def goReload(self):
		if self.screenType == 0:
			self.open_serienstarts()
		elif self.screenType == 1:
			self.open_primetime()
		elif self.screenType == 2:
			self.open_moviewall()
		elif self.screenType == 3:
			self.open_favourites()


#class AdvancedEventLibrarySetup(Setup):
#	def __init__(self, session):
#		Setup.__init__(self, session, "Advanced-Event-Library-Setup", plugin="Extensions/AdvancedEventLibrary", PluginLanguageDomain="AdvancedEventLibrary")
#		self["key_yellow"] = StaticText(_("TVS-Setup"))
#		self["coloractions"] = HelpableActionMap(self, ["ColorActions"], {
#			"yellow": (self.key_yellow_handler, _(" "))
#		}, prio=0)

#	def keySelect(self):
#		if self.getCurrentItem() == config.plugins.MetrixWeather.iconpath:
#			self.session.openWithCallback(self.keySelectCallback, WeatherSettingsLocationBox, currDir=config.plugins.MetrixWeather.iconpath.value)
#			return
#		if self.getCurrentItem() == config.plugins.MetrixWeather.weathercity:
#			self.checkcity = True
#		Setup.keySelect(self)

class AdvancedEventLibrarySetupLocationBox(LocationBox):
	def __init__(self, session, currDir):
		inhibit = defaultInhibitDirs[:]
		inhibit.remove("/usr")
		inhibit.remove("/share")
		if currDir == "":
			currDir = None
		LocationBox.__init__(
			self,
			session,
			text=_("Where do you want to get the MetrixWeather icons?"),
			currDir=currDir,
			inhibitDirs=inhibit,
		)


####################################################################################
class AdvancedEventLibrarySetup(Setup):
	ALLOW_SUSPEND = True  # skin = str(loadskin("AdvancedEventLibrarySetup.xml"))

	def __init__(self, session):
		self.searchOptions = {}
		#=============== hinzugefuegt (#5/#6) ================
		#self.searchOptionsInUse = []
		#self.searchOptionsInUse.append("VTiDB")
		#self.searchOptionsInUse.append("Pictures")
		#self.newBouquetsSearchDefault = config.plugins.AdvancedEventLibrary.newBouquetsSearchDefault = ConfigYesNo(default = False)
		#self.newBookmarksSearchDefault = config.plugins.AdvancedEventLibrary.newBookmarksSearchDefault = ConfigYesNo(default = False)
		# ==*=========================================
		if config.plugins.AdvancedEventLibrary.searchPlaces.value != '':
			self.searchOptions = eval(config.plugins.AdvancedEventLibrary.searchPlaces.value)
		Setup.__init__(self, session, "Advanced-Event-Library-Setup", plugin="Extensions/AdvancedEventLibrary", PluginLanguageDomain="AdvancedEventLibrary")
		self["key_yellow"] = StaticText(_("TVS-Setup"))
		self["coloractions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyYellow, _(" "))
		}, prio=0)

#		self.myFileListActive = False
#		self["config"].onSelectionChanged.append(self.selectionChanged)

	def keyYellow(self):
		pass
#		self.session.open(TVSSetup)  # TODO: fliegt raus

	def keySelect(self):
		def keySelectCallback(value):
			self.getCurrentItem().value = value
			#createDirs(value) # TODO
		if self.getCurrentItem() in (config.plugins.AdvancedEventLibrary.Location, config.plugins.AdvancedEventLibrary.dbFolder):
			self.session.openWithCallback(keySelectCallback, AdvancedEventLibrarySetupLocationBox, currDir=self.getCurrentItem().value)
			return
		Setup.keySelect(self)

	def key_blue_handler(self):
		if self.myFileListActive:
			#====== geaendert (#6) =========
			#self["key_blue"].setText("")
			self["key_blue"].setText(_("Bereinigen"))
			# ==============================
			self["myFileList"].hide()
			self.myFileListActive = False
			self.updatePath(True)
			self.buildConfigList()
		#=============== hinzugefuegt (#6) ================
		else:
			bouquetCount = 0
			movieFolderCount = 0
			movieFolderList = []
			for k, v in self.searchOptions.items():
				if str(k) and str(k) not in self.searchOptionsInUse and (str(k) + "/") not in self.searchOptionsInUse:
					key = str(k)
					if key.startswith("/"):
						if key.endswith("/"):
							key = key[:-1]
						if key not in movieFolderList:
							movieFolderList.append(key)
							movieFolderCount = movieFolderCount + 1
					elif not key.startswith("subpaths_") and not key.startswith("Einstellungen"):
						bouquetCount = bouquetCount + 1

			if bouquetCount > 0 or movieFolderCount > 0:
				msg = str(bouquetCount) + _(" Bouquets und ") + str(movieFolderCount) + _(" Movie-Ordner, die nicht mehr vorhanden oder aktuell nicht erreichbar sind, aus den AEL-Search-Options entfernen?") + "\n\n" + _("Im Anschluss muss ein GUI-Neustart durchgeführt werden!") + "\n\n" + _("Info: Die Search-Options werden am Anfang im Log aufgelistet")
				MsgBox = self.session.openWithCallback(self.cleanUpSearchOptions, MessageBox, msg, MessageBox.TYPE_YESNO)
			else:
				msg = _("Aktuell keine Bereinigung erforderlich!") + "\n\n" + _("Keine Bouquets oder Movie-Ordner, die nicht mehr vorhanden oder aktuell nicht erreichbar sind, in den AEL-Search-Options gefunden") + "\n\n"
				MsgBox = self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, timeout=10)
			MsgBox.setTitle(_("Bereinigen"))
		# ====================================================

	#=============== hinzugefuegt (#6) ================
	def cleanUpSearchOptions(self, answer=False):
		if answer:
			for k, v in self.searchOptions.items():
				if str(k) and str(k) not in self.searchOptionsInUse and (str(k) + "/") not in self.searchOptionsInUse:
					del self.searchOptions[k]
			self.do_close()
	# ====================================================
#	def buildConfigList(self):
#		try:
#			if self.configlist:
#				del self.configlist[:]
#			self.configlist.append(getConfigListEntry("Einstellungen Allgemein"))
#			self.configlist.append(getConfigListEntry("Daten-Verzeichnis (OK drücken)", config.plugins.AdvancedEventLibrary.Location))
#			self.configlist.append(getConfigListEntry("Datenbank-Verzeichnis", config.plugins.AdvancedEventLibrary.dbFolder))
#			self.configlist.append(getConfigListEntry("Backup-Verzeichnis (OK drücken)", self.backuppath))
#			self.configlist.append(getConfigListEntry("benutzter TVDb API-V4-USER-PIN", self.tvdbV4Key))
#			self.configlist.append(getConfigListEntry("benutzter TVDb API-Key", self.tvdbKey))
#			self.configlist.append(getConfigListEntry("benutzter TMDb API-Key", self.tmdbKey))
#			self.configlist.append(getConfigListEntry("benutzter OMDB API-Key", self.omdbKey))
#			self.configlist.append(getConfigListEntry("maximaler Speicherplatz (GB)", self.maxSize))
#			self.configlist.append(getConfigListEntry("maximal zu benutzende Inodes (%)", self.maxUsedInodes))
#			self.configlist.append(getConfigListEntry("AEL-Menü automatisch schließen", self.closeMenu))
#			self.configlist.append(getConfigListEntry("schreibe erweitertes Logfile", self.addlog))

#			self.configlist.append(getConfigListEntry("Einstellungen Download"))
#			self.configlist.append(getConfigListEntry("Art der Suche", self.searchfor))
#			if str(self.searchfor.value) == "Extradaten und Bilder":
#				# self.configlist.append(getConfigListEntry("benutze AEL Image-Server", self.useAELIS))
#				self.configlist.append(getConfigListEntry("lade Previewbilder", self.usePreviewImages))
#				if self.usePreviewImages.value:
#					self.configlist.append(getConfigListEntry("lösche alte Previewbilder beim Suchlauf", self.delPreviewImages))
#				self.configlist.append(getConfigListEntry("maximale Auflösung der Poster", self.posterquality))
#				self.configlist.append(getConfigListEntry("maximale Auflösung der Cover", self.coverquality))
#				self.configlist.append(getConfigListEntry("maximale Speichergröße pro Bild", self.maxImageSize))
#				self.configlist.append(getConfigListEntry("minimale JPEG-Qualität (%)", self.maxCompression))
#				self.configlist.append(getConfigListEntry("Anzahl Vorschaubilder im Editor", self.previewCount))
#
#			self.configlist.append(getConfigListEntry("Einstellungen EPG und MovieWall",))
#			self.configlist.append(getConfigListEntry("benutze AEL EPG-Listenstil", self.useAELEPGLists))
#			self.configlist.append(getConfigListEntry("benutze EPG-Taste in EPGSelection für Plugin-Aufruf", self.showinEPG))
#			self.configlist.append(getConfigListEntry("benutze AEL-Movie-Wall", self.updateAELMovieWall))
#			self.configlist.append(getConfigListEntry("ignoriere die Serienerkennung bei der Sortierung (Movie-Wall)", self.ignoreSortSeriesdetection))
#			if self.updateAELMovieWall.value:
#				self.configlist.append(getConfigListEntry("benutze PVR-Taste zum Start für Movie-Wall", self.useAELMW))
#				self.configlist.append(getConfigListEntry("beziehe Symlinks in die Suche nach Aufnahmen ein", self.searchLinks))
#				self.configlist.append(getConfigListEntry("aktualisiere Movie-Wall automatisch nach Aufnahmestop", self.refreshMWAtStop))
#				self.configlist.append(getConfigListEntry("aktualisiere Movie-Wall automatisch nach Aufnahmestart", self.refreshMWAtStart))

#			self.configlist.append(getConfigListEntry("Einstellungen Suche"))
#			self.configlist.append(getConfigListEntry("erstelle nicht vorhandene Metadaten", self.createMetaData))
#			self.configlist.append(getConfigListEntry("suche vorhandene Bilder in Aufnahmeverzeichnissen", self.usePictures))
			#================== hinzugefuegt (#5) ============
#			self.configlist.append(getConfigListEntry("neue Bouquets in der Suchliste anwählen", self.newBouquetsSearchDefault))
#			self.configlist.append(getConfigListEntry("neue Lesezeichen-Ordner in der Suchliste anwählen", self.newBookmarksSearchDefault))
			# ===============================*=*===*==========
#			self.configlist.append(getConfigListEntry("suche in VTiDB", self.vtidb))

#			mask = (eServiceReference.isMarker | eServiceReference.isDirectory)
#			root = eServiceReference(str(service_types_tv + ' FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
#			serviceHandler = eServiceCenter.getInstance()
#			tvbouquets = serviceHandler.list(root).getContent("SN", True)
#			for bouquet in tvbouquets:
#				bpath = ConfigYesNo(default=self.searchOptions.get(bouquet[1], True))
#				bpath = ConfigYesNo(default = self.searchOptions.get(bouquet[1], self.newBouquetsSearchDefault.value))
#				self.searchOptionsInUse.append(str(bouquet[1]))
#				self.configlist.append(getConfigListEntry("suche in Bouquet " + str(bouquet[1]), bpath))
#
#			recordPaths = config.movielist.videodirs.value
#			if recordPaths:
#				for recdir in recordPaths:
#					if isdir(recdir):
						#=============== geaendert (#5) ================
						#rpath = ConfigYesNo(default = self.searchOptions.get(dir, False))
						#subpaths = ConfigYesNo(default = self.searchOptions.get('subpaths_' + dir, False))
#						rpath = ConfigYesNo(default = self.searchOptions.get(dir, self.newBookmarksSearchDefault.value))
#						subpaths = ConfigYesNo(default = self.searchOptions.get('subpaths_' + dir, self.newBookmarksSearchDefault.value))
						# ===============================================

						#=========== hinzugefuegt (#6) =======================
#						self.searchOptionsInUse.append(str(dir))
#						self.searchOptionsInUse.append("subpaths_" + str(dir))
#						for root, directories, files in os.walk(str(dir)):
#							if str(dir) != str(root):
#								self.searchOptionsInUse.append(str(root))
						# =====================================================
#
#						self.configlist.append(getConfigListEntry("suche in " + str(recdir), rpath))
#						self.configlist.append(getConfigListEntry("suche in Unterverzeichnissen von " + str(recdir), subpaths))
#
#		except Exception as ex:
#			write_log(f"Error in buildConfigList : {ex}", DEFAULT_MODULE_NAME)


#	def do_close(self):
#		restartbox = self.session.openWithCallback(self.restartGUI, MessageBox, _("GUI needs a restart to apply new configuration.\nDo you want to restart the GUI now ?"), MessageBox.TYPE_YESNO)
#		restartbox.setTitle(_("GUI needs a restart."))

#	def restartGUI(self, answer):
#		if answer is True:
#			for x in self["config"].list:
#				if len(x) > 1:
#					if "suche" not in x[0] and "Einstellungen" not in x[0] and x[0]:
#						write_log(f"save : {x[0]} - {x[1].value}", DEFAULT_MODULE_NAME)
#						x[1].save()
#					else:
#						if 'suche in Unterverzeichnissen von ' in str(x[0]):
#							for root, directories, files in walk(str(x[0]).replace('suche in Unterverzeichnissen von ', '')):
#								if str(x[0]).replace('suche in Unterverzeichnissen von ', '') != str(root):
#									self.searchOptions[str(root)] = x[1].value
#							self.searchOptions[x[0].replace("suche in Unterverzeichnissen von ", "subpaths_")] = x[1].value
						#============== geaendert (#7) ==============*
						#else:
						#	self.searchOptions[x[0].replace("suche vorhandene Bilder in Aufnahmeverzeichnissen","Pictures").replace("suche in Bouquet ","").replace("suche in ","")] = x[1].value
#						elif x[0] and not x[0].startswith("Einstellungen"):
#							if "suche in " in x[0] and not "VTiDB" in x[0] and not "suche in Bouquet" in x[0]:
#								folder = x[0].replace("suche in ","")
#								self.searchOptions[folder] = x[1].value
#								if folder.endswith("/"):
#									self.searchOptions[folder[:-1]] = x[1].value
#							else:
#								self.searchOptions[x[0].replace("suche vorhandene Bilder in Aufnahmeverzeichnissen","Pictures").replace("suche in Bouquet ","").replace("suche in VTiDB","VTiDB")] = x[1].value
						# =========================================================
#			config.plugins.AdvancedEventLibrary.searchPlaces.value = str(self.searchOptions)
#			config.plugins.AdvancedEventLibrary.searchPlaces.save()
#			self.session.open(TryQuitMainloop, 3)
#		else:
#			self.close()

####################################################################################


class TVSSetup(Screen, ConfigListScreen):  # TODO: Erstmal so belassen
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.skinName = ["TV Spielfilm-Setup", "Setup"]
		self.cur = None
		self.TVSrefDict = {}
		self.title = _("TV Spielfilm-Setup")
		self.setup_title = _("TV Spielfilm-Setup")
		self["title"] = StaticText(self.title)
		self["footnote"] = StaticText("")
		self["description"] = Label("")
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Save"))
#		self.searchPlaces = config.plugins.AdvancedEventLibrary.searchPlaces = ConfigText(default='')
		sPDict = {}
		if config.plugins.AdvancedEventLibrary.searchPlaces.value != '':
			sPDict = eval(config.plugins.AdvancedEventLibrary.searchPlaces.value)
		self.senderlist = []
		self.senderdict = {}
		mask = (eServiceReference.isMarker | eServiceReference.isDirectory)
		root = eServiceReference(str(service_types_tv + ' FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
		serviceHandler = eServiceCenter.getInstance()
		tvbouquets = serviceHandler.list(root).getContent("SN", True)
		for bouquet in tvbouquets:
			root = eServiceReference(str(bouquet[0]))
			serviceHandler = eServiceCenter.getInstance()
			ret = serviceHandler.list(root).getContent("SN", True)
			isInsPDict = bouquet[1] in sPDict
			if not isInsPDict or (isInsPDict and sPDict[bouquet[1]]):
				for (serviceref, servicename) in ret:
					playable = not (eServiceReference(serviceref).flags & mask)
					#============ geaendert (#8) ==============
					#if playable and "p%3a" not in serviceref and "<n/a>" not in servicename and servicename != "." and not serviceref.startswith('4097'):
					if playable and "p%3a" not in serviceref and "ps%3a" not in serviceref and "<n/a>" not in servicename and servicename != "." and not serviceref.startswith('4097') and not serviceref.startswith('5001') and not serviceref.startswith('5002'):
					# ========================================
						if servicename not in self.senderlist:
							self.senderlist.append(servicename)
						self.senderdict[serviceref] = servicename
#		tvslist = self.get_tvsRefList()  # TODO: Schlecht: nicht alle möglichen TVS-Sender abklappern sondern nur die importieren (neue Funktionalität nutzen)
#		self.tvsRefList = tvslist[0] # TODO: entfernen nach Umbau auf neues TVS-System
#		self.tvsKeys = tvslist[1]  # TODO: entfernen nach Umbau auf neues TVS-System
		self.configlist = []
		self.buildConfigList()
		ConfigListScreen.__init__(self, self.configlist, session=self.session, on_change=self.changedEntry)
		self["myActionMap"] = ActionMap(["AdvancedEventLibraryActions"],
		{
			"key_cancel": self.close,
			"key_red": self.close,
			"key_green": self.do_close,
			"key_ok": self.key_ok_handler,
		}, -1)

	def key_ok_handler(self):
		pass
#		self.cur = self['config'].getCurrent()
#		if self.cur:
#			tvslist = []
#			for sender in self.tvsKeys:  # TODO: Schlecht: nicht alle möglichen TVS-Sender abklappern sondern nur die importieren (neue Funktionalität nutzen)
#				for k, v in self.tvsRefList.items():
#					if str(sender) == str(k):
#						tvslist.append((k, v))
#						break
#			tvslist.insert(0, (_("unused"), ""))
#			choices, idx = (tvslist, 0)
#			keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
#			self.session.openWithCallback(self.menuCallBack, ChoiceBox, title=_("Select reference"), keys=keys, list=choices, selection=idx)

	def menuCallBack(self, ret=None):
		if ret and self.cur:
			self.cur[1].value = ret[1]

	def load_json(self, filename):
		with open(filename, 'r') as file:
			data = file.read().replace('null', '""')
		return eval(data)

	def get_tvsRefList(self):  # TODO: Das mit TVS muss noch sauber durchdacht werden, derzeit ist es Kuddelmuddel
		refList = {}
		keyList = []
		# TODO: Hier holt er sich alle verfügbaren TVS-Sender, das wird später nur zum Check der "tvs_mapping.txt" verwendet, ob alle nötigen Regex vorhanden sind
		tvsurl = b64decode(b"aHR0cHM6Ly9saXZlLnR2c3BpZWxmaWxtLmRlL3N0YXRpYy9jb250ZW50L2NoYW5uZWwtbGlzdC9saXZldHY=k"[:-1]).decode()
		errmsg, results = getAPIdata(tvsurl)
		if errmsg:
			write_log("API download error in module 'get_tvsRefList", DEFAULT_MODULE_NAME)
		if results:
			for service in results:
				if "id" in service.items() and "name" in service:
					refList[service["name"]] = service.get("id", "")
			for k, v in refList.items():
				keyList.append(k)
			keyList.sort()
		return (refList, keyList)

	def readTVSrefList(self):
		pass

	def buildConfigList(self):
		if self.configlist:
			del self.configlist[:]
		if self.tvsRefList:
			aelGlobals.TVS_REFDICT = self.load_json(aelGlobals.TVS_REFFILE) if fileExists(aelGlobals.TVS_REFFILE) else {}
			for sender in sorted(self.senderlist):
				for k, v in self.senderdict.items():
					if str(v) == str(sender):
						entry = ConfigText(default=aelGlobals.TVS_REFDICT.get(k, ""))
						self.configlist.append(getConfigListEntry(sender, entry))
						break

	def changedEntry(self):
#		self.buildConfigList()
		cur = self["config"].getCurrent()
		self["config"].setList(self.configlist)
		#if cur and cur is not None:
		#	self["config"].updateConfigListView(cur)

	def do_close(self):
		restartbox = self.session.openWithCallback(self.restartGUI, MessageBox, _("Sollen die Einstellungen gespeichert werden ?"), MessageBox.TYPE_YESNO, timeout=5, default=False)
		restartbox.setTitle(_("Einstellungen speichern"))

	def restartGUI(self, answer):
		if answer is True:
			refdict = {}
			for x in self["config"].list:
				if x[1].value:
					for k, v in self.senderdict.items():  # TODO: Das mit TVS muss noch sauber durchdacht werden, derzeit ist es Kuddelmuddel
						if str(v) == str(x[0]):
							refdict[k] = x[1].value
							break
			with open(join(aelGlobals.PLUGINPATH, "tvsreflist.data"), "w") as file:  # TODO: "tvsreflist.data" (alt) ist nicht die "tvs_reflist.json" (neu)
				file.write(dumps(refdict, indent=4, sort_keys=False))
		self.close()

####################################################################################


class Editor(Screen, ConfigListScreen):
	ALLOW_SUSPEND = True
	skin = str(loadskin("AdvancedEventLibraryEditor.xml"))

	def __init__(self, session, service=None, parent=None, servicelist=None, eventname=None, args=0):
		Screen.__init__(self, session, parent=parent)
		self.session = session
		self.skinName = 'Advanced-Event-Library-Editor'
		self.title = _("Advanced-Event-Library-Editor")
		self.ptr = ""
		self.ptr2 = ""
		self.evt = None
		self.orgName = None
		self.fileName = None
		self.eid = None
		self.isInit = False
		self.ImageCount = config.plugins.AdvancedEventLibrary.PreviewCount.value
#		self.currentService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.language = 'de'
		self.pSource = 1
		self.cSource = 1
		self.db = getDB()
		if service:
			self.ptr = ((service.getPath().split('/')[-1]).rsplit('.', 1)[0]).replace('__', ' ').replace('_', ' ')
			self.fileName = service.getPath()
			if self.fileName.endswith("/"):
				name = self.fileName[:-1]
				self.ptr = self.removeExtension(str(name).split('/')[-1])
			else:
				info = eServiceCenter.getInstance().info(service)
				name = info.getName(service)
				if name:
					self.ptr = self.removeExtension(name)
				ptr = info.getEvent(service)
				if ptr:
					self.ptr2 = ptr.getEventName()
		elif eventname:
			self.ptr = eventname[0]
			self.ptr2 = eventname[0]
			self.evt = self.db.getliveTV(eventname[1], eventname[0])
			if self.evt:
				self.eid = self.evt[0][0]
				if self.evt[0][3] != '':
					self.ptr = str(self.evt[0][3])
					self.orgName = eventname[0]
				elif self.evt[0][7] != '':
					name = self.evt[0][7] + ' - '
					if self.evt[0][12] != '':
						name += 'S' + str(self.evt[0][12]).zfill(2)
					if self.evt[0][13] != "":
						name += 'E' + str(self.evt[0][12]).zfill(2) + ' - '
					if self.evt[0][2] != "":
						name += self.evt[0][2] + ' - '
					self.ptr = str(name[:-3])
		else:
			service = self.session.nav.getCurrentService()
			info = service.info()
			ref = self.session.nav.getCurrentlyPlayingServiceReference().toString()
			if '/' in ref:
				self.ptr = info.getName()
				ptr = info.getEvent(0)
				if ptr:
					self.ptr2 = ptr.getEventName()
			else:
				ptr = info.getEvent(0)
				if ptr:
					self.ptr = ptr.getEventName()
					self.ptr2 = self.ptr
					write_log(f"{ptr.getEventName()} {self.ptr}", DEFAULT_MODULE_NAME)
					self.evt = self.db.getliveTV(ptr.getEventId(), str(self.ptr))
					if self.evt:
						self.eid = self.evt[0][0]
						if self.evt[0][3] != '':
							self.orgName = self.ptr
							self.ptr = str(self.evt[0][3])
						elif self.evt[0][7] != '':
							name = self.evt[0][7] + ' - '
							if self.evt[0][12] != '':
								name += 'S' + str(self.evt[0][12]).zfill(2)
							if self.evt[0][13] != "":
								name += 'E' + str(self.evt[0][12]).zfill(2) + ' - '
							if self.evt[0][2] != "":
								name += self.evt[0][2] + ' - '
							self.ptr = str(name[:-3])
		if not self.ptr:
			self.ptr = "nothing found"
		self.ptr = convertSearchName(convertDateInFileName(self.ptr))
		if self.ptr2:
			self.ptr2 = convertSearchName(convertDateInFileName(self.ptr2))
			write_log(f"found second name : {self.ptr2}", DEFAULT_MODULE_NAME)
		write_log(f"search name : {self.ptr}", DEFAULT_MODULE_NAME)
		self["key_red"] = StaticText(_("Activate"))
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText(_("Activate poster selection"))
		self["key_blue"] = StaticText(_("Activate Cover selection"))
		self.activeList = 'editor'
		self.jahr = ''
		self["pList"] = ImageList()
		self["cList"] = ImageList()
		self["sList"] = SearchResultsList()
		self["cover"] = Pixmap()
		self["poster"] = Pixmap()
		self["cover"].hide()
		self["poster"].hide()
		self["sList"].hide()
		self.eventTitle = ConfigText(default="")
		self.eventGenre = ConfigText(default="")
		self.eventYear = ConfigText(default="")
		self.eventRating = ConfigText(default="")
		self.eventFSK = ConfigText(default="")
		self.eventCountry = ConfigText(default="")
		self.eventOverview = None
		self.configlist = []
		ConfigListScreen.__init__(self, self.configlist, session=self.session, on_change=self.changedEntry)
		self["myActionMap"] = ActionMap(["AdvancedEventLibraryActions"],
		{
			"key_cancel": self.doClose,
			"key_red": self.key_red_handler,
			"key_green": self.key_green_handler,
			"key_yellow": self.key_yellow_handler,
			"key_blue": self.key_blue_handler,
			"key_up": self.key_up_handler,
			"key_down": self.key_down_handler,
			"key_left": self.key_left_handler,
			"key_right": self.key_right_handler,
			"key_ok": self.key_ok_handler,
			"key_menu": self.key_menu_handler
		}, -1)
		self.onShow.append(self.checkDoupleNames)

	def removeExtension(self, ext):
		ext = ext.replace('.wmv', '').replace('.mpeg2', '').replace('.ts', '').replace('.m2ts', '').replace('.mkv', '').replace('.avi', '').replace('.mpeg', '').replace('.mpg', '').replace('.iso', '').replace('.mp4', '')
		return ext

	def checkPositions(self):
		return True if int(self['sList'].getPosition()) > int(self['cList'].getPosition()) else False

	def key_ok_handler(self):
		if self.ptr != 'nothing found':
			if self.activeList == 'choiceBox':
				selection = self['sList'].l.getCurrentSelection()[0]
				if selection and self.eventData:
					if str(selection[0]) != "Keine Ergebnisse gefunden":
						self.eventTitle.value = selection[0]
						self.eventGenre.value = selection[3]
						self.eventYear.value = selection[2]
						self.eventRating.value = selection[4]
						self.eventFSK.value = selection[5]
						self.eventCountry.value = selection[1]
						self.eventOverview = selection[7]
						self.changedEntry()
				self["key_yellow"] = StaticText(_("Activate poster selection"))
				self["key_blue"] = StaticText(_("Activate Cover selection"))
				self['sList'].hide()
				self['config'].show()
				self.activeList = 'editor'
				if self.checkPositions():
					self['cList'].show()
					self['pList'].show()
				waitList = []
				itm = [_("load data, please wait..."), None, None, None, None, None, None]
				waitList.append((itm,))
				self['cList'].setList(waitList)
				self['pList'].setList(waitList)
				self.cSource = 1
				self.pSource = 1
				callInThread(self.searchPics)
			elif self.activeList == 'editor':
				if self['config'].getCurrent()[0] == 'Event Name (suche mit OK)':
					self.session.openWithCallback(self.searchEvents, VirtualKeyBoard, title="Eventsuche...", text=self['config'].getCurrent()[1].value)
				else:
					self.session.openWithCallback(self.donothing, VirtualKeyBoard, title="Daten bearbeiten...", text=self['config'].getCurrent()[1].value)
			elif self.activeList == 'poster':
				selection = self['pList'].l.getCurrentSelection()[0]
				if selection:
					if str(selection[0]) != "Keine Ergebnisse gefunden" and str(selection[0]) != _("load data, please wait..."):
						if self.pSource == 1:
							write_log(f"Selection to move : {selection}", DEFAULT_MODULE_NAME)
							fileName = f"/tmp/{selection[5]}"  # NOSONAR
							createSingleThumbnail(fileName, selection[4])
							if int(getsize(fileName) / 1024.0) > config.plugins.AdvancedEventLibrary.MaxImageSize.value:
								reduceSigleImageSize(fileName, selection[4])
							else:
								copy(fileName, selection[4])
			elif self.activeList == 'cover':
				selection = self['cList'].l.getCurrentSelection()[0]
				if selection:
					if str(selection[0]) != "Keine Ergebnisse gefunden" and str(selection[0]) != _("load data, please wait..."):
						if self.cSource == 1:
							fileName = f"/tmp/{selection[5]}"  # NOSONAR
							write_log(f"Selection to move : {selection}", DEFAULT_MODULE_NAME)
							createSingleThumbnail(fileName, selection[4])
							if int(getsize(fileName) / 1024.0) > config.plugins.AdvancedEventLibrary.MaxImageSize.value:
								reduceSigleImageSize(fileName, selection[4])
							else:
								copy(fileName, selection[4])
			elif "screenshot" in self.activeList.lower():
				fname = f"{convertSearchName(convert2base64(self.removeExtension(self.ptr)))}.jpg"
				cmd = f"grab -v -j 100 /tmp/{fname}"
				ret = system(cmd)
				if ret == 0:
					fileName = f"/tmp/{fname}"  # NOSONAR
					if "poster" in self.activeList:
						im = Image.open(fileName)
						region = im.crop((640, 0, 1280, 1080))
						region.save(fileName)
						typ = "poster/"
					else:
						typ = "cover/"
					createSingleThumbnail(fileName, join(aelGlobals.HDDPATH + typ, fname))
					if int(getsize(fileName) / 1024.0) > int(config.plugins.AdvancedEventLibrary.MaxImageSize.value):
						reduceSigleImageSize(fileName, join(aelGlobals.HDDPATH + typ, fname))
					else:
						copy(fileName, join(aelGlobals.HDDPATH + typ, fname))
					self.session.open(MessageBox, f"AEL - Screenshot\nNew image for {self.ptr} successfully created.", MessageBox.TYPE_INFO, timeout=3, close_on_any_key=True)
				else:
					self.session.open(MessageBox, f"AEL - Screenshot\nImage {self.ptr} could not be created.", MessageBox.TYPE_INFO, timeout=5, close_on_any_key=True)
#				self.session.nav.playService(self.currentServiceService)
				self.doClose()

	def donothing(self, text):
		if text:
			self['config'].getCurrent()[1].value = text
		else:
			self['config'].getCurrent()[1].value = ""

	def searchEvents(self, text):
		if text:
			self['config'].hide()
			if self.checkPositions():
				self['cList'].hide()
				self['pList'].hide()
			waitList = []
			itm = [_("load data, please wait..."), None, None, None, None, None, None]
			waitList.append((itm,))
			self['sList'].setList(waitList)
			self["key_yellow"].setText("")
			self["key_blue"].setText("")
			self["cover"].hide()
			self["poster"].hide()
			self['sList'].show()
			self.activeList = "choiceBox"
			self.text = text
			callInThread(self.searchAll)

	def searchAll(self):
		self['sList'].setList(get_searchResults(self.text, self.language))

	def key_menu_handler(self):
		if self.ptr != 'nothing found':
			if self.cSource == 0 and self.activeList == "cover" and "/etc" not in str(config.plugins.AdvancedEventLibrary.Location.value):
				choices, idx = ([(_("Language selection"),), (_("Load cover"),), (_("create screenshot"),), (_("Delete entry"),), (_("Delete entry and set to blacklist"),), (_("Delete cover"),), (_("Delete thumbnails"),), (_("Delete BlackList"),), (_("Check images"),)], 0)
			elif self.pSource == 0 and self.activeList == "poster" and "/etc" not in str(config.plugins.AdvancedEventLibrary.Location.value):
				choices, idx = ([(_("Language selection"),), (_("Load poster"),), (_("create screenshot"),), (_("Delete entry"),), (_("Delete entry and set to blacklist"),), (_("Delete poster"),), (_("Delete thumbnails"),), (_("Delete BlackList"),), (_("Check images"),)], 0)
			else:
				choices, idx = ([(_("Language selection"),), (_("create poster from screenshot"),), (_("create cover from screenshot"),), (_("Delete entry"),), (_("Delete entry and set to blacklist"),), (_("Delete thumbnails"),), (_("Delete BlackList"),), (_("Check images"),)], 0)
			keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
			self.session.openWithCallback(self.menuCallBack, ChoiceBox, title="Bearbeiten", keys=keys, list=choices, selection=idx)

	def menuCallBack(self, ret=None):
		if ret:
			if ret[0] == _("Language selection"):
				choices, idx = ([(_("German"), "de"), (_("English"), "en"), (_("French"), "fr"), (_("Spanish"), "es"), (_("Italian"), "it"), (_("All languages"), "")], 0)
				keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
				self.session.openWithCallback(self.languageCallBack, ChoiceBox, title=_("Language used for search"), keys=keys, list=choices, selection=idx)
			if ret[0] == _("Delete entry"):
				self.db.cleanDB(convertSearchName(convert2base64(self.ptr)))
				if self.eid is not None:
					self.db.cleanliveTVEntry(self.eid)
				if self.cSource == 0:
					for file in self["cList"].getList():
						try:
							remove(file[0][3])
							remove(file[0][3].replace("/cover/", "/cover/thumbnails/"))
						except Exception as ex:
							write_log(f"remove images : {ex}", DEFAULT_MODULE_NAME)
							continue
				if self.pSource == 0:
					for file in self["pList"].getList():
						try:
							remove(file[0][3])
							remove(file[0][3].replace("/poster/", "/poster/thumbnails/"))
						except Exception as ex:
							write_log(f"remove images : {ex}", DEFAULT_MODULE_NAME)
							continue
				self.eventCountry.value = ""
				self.eventFSK.value = ""
				self.eventGenre.value = ""
				self.eventRating.value = ""
				self.eventYear.value = ""
				self.eventOverview = None
			elif ret[0] == _("Delete entry and set to blacklist"):
				self.db.cleanNadd2BlackList(convertSearchName(convert2base64(self.ptr)))
				if self.eid is not None:
					self.db.cleanliveTVEntry(self.eid)
				if self.cSource == 0:
					for file in self["cList"].getList():
						try:
							remove(file[0][3])
							remove(file[0][3].replace("/cover/", "/cover/thumbnails/"))
						except Exception as ex:
							write_log(f"remove images : {ex}", DEFAULT_MODULE_NAME)
							continue
				if self.pSource == 0:
					for file in self["pList"].getList():
						try:
							remove(file[0][3])
							remove(file[0][3].replace("/poster/", "/poster/thumbnails/"))
						except Exception as ex:
							write_log(f"remove images : {ex}", DEFAULT_MODULE_NAME)
							continue
				self.eventCountry.value = ""
				self.eventFSK.value = ""
				self.eventGenre.value = ""
				self.eventRating.value = ""
				self.eventYear.value = ""
				self.eventOverview = None
			elif ret[0] == _("Delete Poster"):
				try:
					selection = self["pList"].l.getCurrentSelection()[0]
					if selection and isfile(selection[3]):
						remove(selection[3])
						remove(selection[3].replace("/poster/", "/poster/thumbnails/"))
						self.afterInit(True, False)
				except Exception as ex:
					write_log(f"remove images : {ex}", DEFAULT_MODULE_NAME)
			elif ret[0] == _("Delete cover"):
				try:
					selection = self["cList"].l.getCurrentSelection()[0]
					if selection and isfile(selection[3]):
						remove(selection[3])
						remove(selection[3].replace("/cover/", "/cover/thumbnails/").replace("/preview/", "/preview/thumbnails/"))
						self.afterInit(False, True)
				except Exception as ex:
					write_log(f"remove image : {ex}", DEFAULT_MODULE_NAME)
			elif ret[0] == _("Delete BlackList"):
				self.db.cleanblackList()
			elif ret[0] == _("Delete thumbnails"):
				for subpath in [aelGlobals.COVERPATH, aelGlobals.POSTERPATH, aelGlobals.PREVIEWPATH]:
					tmppath = f"{subpath}tumbnails"
					if exists(tmppath):
						filelist = glob(join(tmppath, "*.jpg"))
						for file in filelist:
							remove(file)
						del filelist
			elif ret[0] == _("Check images"):
				callInThread(checkAllImages)
			elif ret[0] == _("Load cover"):
				waitList = []
				itm = [_("load data, please wait..."), None, None, None, None, None, None]
				waitList.append((itm,))
				self.cSource = 1
				self["cList"].setList(waitList)
				callInThread(self.searchPics, (False, True))
			elif ret[0] == _("Load poster"):
				waitList = []
				itm = [_("load data, please wait..."), None, None, None, None, None, None]
				waitList.append((itm,))
				self.pSource = 1
				self["pList"].setList(waitList)
				callInThread(self.searchPics, (False, True))
			elif "screenshot" in ret[0].lower():
				if self.activeList == "cover":
					self.activeList = "screenshot cover"
				elif self.activeList == "poster":
					self.activeList = "screenshot poster"
				elif "poster" in ret[0].lower():
					self.activeList = "screenshot poster"
				elif "cover" in ret[0].lower():
					self.activeList = "screenshot cover"
				self.hide()
			write_log(f"Menü : {ret[0]} - {self.ptr}", DEFAULT_MODULE_NAME)

	def languageCallBack(self, ret=None):
		if ret:
			write_log(f"current language: {ret[0]}", DEFAULT_MODULE_NAME)
			self.language = str(ret[1])

	def key_up_handler(self):
		if self.activeList == "editor":
			self["config"].instance.moveSelection(self["config"].instance.moveUp)
		elif self.activeList == "poster":
			self["pList"].moveUp()
		elif self.activeList == "cover":
			self["cList"].moveUp()
		elif self.activeList == "choiceBox":
			self["sList"].moveUp()
		self.showPreview()

	def key_down_handler(self):
		if self.activeList == "editor":
			self["config"].instance.moveSelection(self["config"].instance.moveDown)
		elif self.activeList == "poster":
			self["pList"].moveDown()
		elif self.activeList == "cover":
			self["cList"].moveDown()
		elif self.activeList == "choiceBox":
			self["sList"].moveDown()
		self.showPreview()

	def key_left_handler(self):
		if self.activeList == "poster":
			self["pList"].pageUp()
		elif self.activeList == "cover":
			self["cList"].pageUp()
		elif self.activeList == "choiceBox":
			self["sList"].pageUp()
		self.showPreview()

	def key_right_handler(self):
		if self.activeList == "poster":
			self["pList"].pageDown()
		elif self.activeList == "cover":
			self["cList"].pageDown()
		elif self.activeList == "choiceBox":
			self["sList"].pageDown()
		self.showPreview()

	def checkDoupleNames(self):
		if not self.isInit:
			self.isInit = True
			if self.ptr2 and str(self.ptr2) != str(self.ptr):
				choices, idx = ([(self.ptr,), (self.ptr2,)], 0)
				keys = ["1", "2"]
				self.session.openWithCallback(self.correctNames, ChoiceBox, title="Welchen Titel möchtest Du bearbeiten?", keys=keys, list=choices, selection=idx)
			else:
				self.correctNames(None)

	def correctNames(self, ret):
		if ret and ret[0] == self.ptr2:
			self.ptr = self.ptr2
			self.evt = None
			self.eid = None
		eventData = self.db.getTitleInfo(convertSearchName(convert2base64(self.ptr)))
		if not eventData:
			eventData = self.db.getTitleInfo(convertSearchName(convert2base64(convertTitle(self.ptr))))
			if not eventData:
				eventData = self.db.getTitleInfo(convertSearchName(convert2base64(convertTitle2(self.ptr))))
		if not eventData:
			eventData = [convertSearchName(convert2base64(self.ptr)), self.ptr, "", "", "", "", ""]
		if not self.db.checkTitle(convert2base64(self.ptr)):
			if self.ptr != "nothing found":
				self.db.addTitleInfo(convertSearchName(convert2base64(self.ptr)), self.ptr, "", "", "", "", "")
		self.eventData = [convertSearchName(convert2base64(self.ptr)), self.ptr, "", "", "", "", ""]
		if self.evt:  # genre
			self.eventData[2] = self.evt[0][14] if len(str(self.evt[0][14]).strip()) > 0 else eventData[2]
		else:
			self.eventData[2] = eventData[2]
		if self.evt:  # year
			self.eventData[3] = self.evt[0][4] if len(str(self.evt[0][4]).strip()) > 0 else eventData[3]
		else:
			self.eventData[3] = eventData[3]
		#if self.evt:  # rating
		#	if len(str(self.evt[0][6]).strip()) > 0:
		#		self.eventData[4] = self.evt[0][6]
		#	else:
		#		self.eventData[4] = eventData[4]
		#else:
		#	self.eventData[4] = eventData[4]
		if self.evt:  # fsk
			if len(str(self.evt[0][5]).strip()) > 0:
#				try:
				tmp = int(str(self.evt[0][5]).strip())
				if tmp in range(0, 6):
					self.eventData[5] = str(0)
				elif tmp in range(6, 12):
					self.eventData[5] = str(6)
				elif tmp in range(12, 16):
					self.eventData[5] = str(12)
				elif tmp in range(16, 18):
					self.eventData[5] = str(16)
				elif tmp >= 18:
					self.eventData[5] = str(18)
				else:
					self.eventData[5] = eventData[5]
#				except:
#					if tmp.find("Ohne Altersbe") > 0:
#						self.eventData[5] = str(0)
#					elif (tmp == "KeineJugendfreigabe" or tmp == "KeineJugendfreige"):
#						self.eventData[5] = str(18)
#					else:
#						self.eventData[5] = eventData[5]
			else:
				self.eventData[5] = eventData[5]
		else:
			self.eventData[5] = eventData[5]

		if self.evt:  # country
			self.eventData[6] = self.evt[0][15] if len(str(self.evt[0][15]).strip()) > 0 else eventData[6]
		else:
			self.eventData[6] = eventData[6]
		self.eventTitle.value = self.eventData[1]
		self.eventGenre.value = self.eventData[2]
		self.eventYear.value = self.eventData[3]
		self.eventRating.value = self.eventData[4]
		self.eventFSK.value = self.eventData[5]
		self.eventCountry.value = self.eventData[6]
		self.buildConfigList()
		self.afterInit()
		self.key_down_handler()

	def afterInit(self, refreshPoster=True, refreshCover=True):
		if self.ptr != "nothing found":
			if refreshCover and refreshPoster:
				pName1 = f"{convert2base64(self.ptr)}.jpg"
				pName2 = f"{convert2base64(convertTitle(self.ptr))}.jpg"
				pName3 = f"{convert2base64(convertTitle2(self.ptr))}.jpg"
				write_log(f"1. possible picture name : {self.ptr} as {pName1}", DEFAULT_MODULE_NAME)
				if pName1 != pName2:
					write_log(f"2. possible picture name : {convertTitle(self.ptr)} as {pName2}", DEFAULT_MODULE_NAME)
				if pName2 != pName3:
					write_log(f"3. possible picture name : {convertTitle2(self.ptr)} as {pName3}", DEFAULT_MODULE_NAME)
				if isfile(join(aelGlobals.COVERPATH, pName1)):
					write_log(f"found 1. possible cover : {pName1}", DEFAULT_MODULE_NAME)
				if isfile(join(aelGlobals.COVERPATH, pName2)) and pName1 != pName2:
					write_log(f"found 2. possible cover : {pName2}", DEFAULT_MODULE_NAME)
				if isfile(join(aelGlobals.COVERPATH, pName3)) and pName2 != pName3:
					write_log(f"found 3. possible cover : {pName3}", DEFAULT_MODULE_NAME)
				if isfile(join(aelGlobals.POSTERPATH, pName1)):
					write_log(f"found 1. possible poster : {pName1}", DEFAULT_MODULE_NAME)
				if isfile(join(aelGlobals.POSTERPATH, pName2)) and pName1 != pName2:
					write_log(f"found 2. possible poster : {pName2}", DEFAULT_MODULE_NAME)
				if isfile(join(aelGlobals.POSTERPATH, pName3)) and pName2 != pName3:
					write_log(f"found 3. possible poster : {pName3}", DEFAULT_MODULE_NAME)
			self.coverList = []
			self.posterList = []
			waitList = []
			itm = [_("load data, please wait..."), None, None, None, None, None, None]
			waitList.append((itm,))
			if refreshCover:
				coverFiles = glob(join(aelGlobals.COVERPATH, f"{convert2base64(self.ptr.strip())}.jpg"))
				c2 = glob(join(aelGlobals.COVERPATH, f"{convert2base64(convertTitle(self.ptr).strip())}.jpg"))
				for file in c2:
					if file not in coverFiles:
						coverFiles.append(file)
				c2 = glob(join(aelGlobals.COVERPATH, f"{convert2base64(convertTitle2(self.ptr).strip())}.jpg"))
				for file in c2:
					if file not in coverFiles:
						coverFiles.append(file)
				del c2
				coverFile = getImageFile(aelGlobals.COVERPATH, self.ptr)
				if coverFile and coverFile not in coverFiles:
					coverFiles.append(coverFile)
				if self.orgName and self.orgName != self.ptr:
					coverFiles2 = glob(join(aelGlobals.COVERPATH, f"{convert2base64(self.orgName.strip())}.jpg"))
					for file in coverFiles2:
						if file not in coverFiles:
							coverFiles.append(file)
					p2 = glob(join(aelGlobals.COVERPATH, f"{convert2base64(convertTitle(self.orgName).strip())}.jpg"))
					for file in p2:
						if file not in coverFiles:
							coverFiles.append(file)
					p2 = glob(join(aelGlobals.COVERPATH, f"{convert2base64(convertTitle2(self.orgName).strip())}.jpg"))
					for file in p2:
						if file not in coverFiles:
							coverFiles.append(file)
					del p2
					coverFile = getImageFile(aelGlobals.COVERPATH, self.orgName)
					if coverFile and coverFile not in coverFiles:
						coverFiles.append(coverFile)
				for files in coverFiles:
					name = basename(files).replace('.jpg', '')
#					try:
					fn = b64decode(basename(files).replace('.jpg', '')).decode()
#					except:
#						fn = basename(files).replace('.jpg', '')
					if 'cover' in files:
						itm = [fn, 'Cover', name, files]
					elif 'preview' in files:
						itm = [fn, 'Preview', name, files]
					else:
						itm = [files, 'unknown', name, files]
					self.coverList.append((itm,))
				if self.coverList:
					self.coverList.sort(key=lambda x: x[0], reverse=False)
					self.cSource = 0
					self['cList'].setList(self.coverList, 0)
					for idx, name in enumerate(self.coverList):
						if name[0][0] == self.eventTitle.value.lower():
							self['cList'].moveToIndex(idx)
							break
				else:
					self.cSource = 1
					self['cList'].setList(waitList)
					callInThread(self.searchPics, (False, True))
				del coverFiles
			if refreshPoster:
				posterFiles = glob(join(aelGlobals.POSTERPATH, f"{convert2base64(self.ptr.strip())}.jpg"))
				p2 = glob(join(aelGlobals.POSTERPATH, f"{convert2base64(convertTitle(self.ptr).strip())}.jpg"))
				for file in p2:
					if file not in posterFiles:
						posterFiles.append(file)
				p2 = glob(join(aelGlobals.POSTERPATH, f"{convert2base64(convertTitle2(self.ptr).strip())}.jpg"))
				for file in p2:
					if file not in posterFiles:
						posterFiles.append(file)
				del p2
				posterFile = getImageFile(aelGlobals.POSTERPATH, self.ptr)
				if posterFile and posterFile not in posterFiles:
					posterFiles.append(posterFile)

				if self.orgName and self.orgName != self.ptr:
					posterFiles2 = glob(join(aelGlobals.POSTERPATH, f"{convert2base64(self.orgName.strip())}.jpg"))
					for file in posterFiles2:
						if file not in posterFiles:
							posterFiles.append(file)
					p2 = glob(join(aelGlobals.POSTERPATH, f"{convert2base64(convertTitle(self.orgName).strip())}.jpg"))
					for file in p2:
						if file not in posterFiles:
							posterFiles.append(file)
					p2 = glob(join(aelGlobals.POSTERPATH, f"{convert2base64(convertTitle2(self.orgName).strip())}.jpg"))
					for file in p2:
						if file not in posterFiles:
							posterFiles.append(file)
					del p2
					posterFile = getImageFile(aelGlobals.POSTERPATH, self.orgName)
					if posterFile and posterFile not in posterFiles:
							posterFiles.append(posterFile)
				for files in posterFiles:
					name = basename(files).replace('.jpg', '')
#					try:
					fn = b64decode(basename(files).replace('.jpg', '')).decode()
#					except:
#						fn = basename(files).replace('.jpg', '')
					itm = [fn, 'Poster', name, files]
					self.posterList.append((itm,))
				if self.posterList:
					self.posterList.sort(key=lambda x: x[0], reverse=False)
					self.pSource = 0
					self['pList'].setList(self.posterList, 0)
					for idx, name in enumerate(self.posterList):
						if name[0][0] == self.eventTitle.value.lower():
							self['pList'].moveToIndex(idx)
							break
				else:
					self.pSource = 1
					self['pList'].setList(waitList)
					callInThread(self.searchPics, (False, True))
				del posterFiles
			self['sList'].setList(waitList)
			del self.posterList
			del self.coverList

	def searchPics(self, poster=True, cover=True):
		regexfinder = compile(r"\([12][90]\d{2}\)", IGNORECASE)
		ex = regexfinder.findall(self.eventTitle.value)
		searchtext = self.eventTitle.value + " (" + self.eventYear.value + ")" if self.eventYear.value and self.eventYear.value != "" and not ex else self.eventTitle.value
		if poster:
			if "Serie" in self.eventGenre.value:
				self['pList'].setList(get_PictureList(searchtext, 'Poster', self.ImageCount, self.eventData[0], self.language, " Serie"))
			else:
				self['pList'].setList(get_PictureList(searchtext, 'Poster', self.ImageCount, self.eventData[0], self.language, " Film"))
		if cover:
			if "Serie" in self.eventGenre.value:
				self['cList'].setList(get_PictureList(searchtext, 'Cover', self.ImageCount, self.eventData[0], self.language, " Serie"))
			else:
				self['cList'].setList(get_PictureList(searchtext, 'Cover', self.ImageCount, self.eventData[0], self.language, " Film"))

	def showPreview(self):
		if self.ptr != 'nothing found':
			self["poster"].hide()
			self["cover"].hide()
			if self.activeList == 'poster':
				selection = self['pList'].l.getCurrentSelection()[0]
				if selection:
					size = self["poster"].instance.size()
					picloader = PicLoader(size.width(), size.height())
					if self.pSource == 1:
						self["poster"].instance.setPixmap(picloader.load('/tmp/' + selection[5]))
					else:
						self["poster"].instance.setPixmap(picloader.load(selection[3]))
					picloader.destroy()
					self["poster"].show()
			elif self.activeList == 'cover':
				selection = self['cList'].l.getCurrentSelection()[0]
				if selection:
					size = self["cover"].instance.size()
					picloader = PicLoader(size.width(), size.height())
					if self.cSource == 1:
						self["cover"].instance.setPixmap(picloader.load('/tmp/' + selection[5]))
					else:
						self["cover"].instance.setPixmap(picloader.load(selection[3]))
					picloader.destroy()
					self["cover"].show()

	def key_red_handler(self):
		if self.ptr != 'nothing found':
			if self.eid:
				self.db.updateliveTVInfo(self.eventTitle.value, self.eventGenre.value, self.eventYear.value, self.eventRating.value, self.eventFSK.value, self.eventCountry.value, self.eid)
			if self.db.checkTitle(self.eventData[0]):
				self.db.updateTitleInfo(self.eventTitle.value, self.eventGenre.value, self.eventYear.value, self.eventRating.value, self.eventFSK.value, self.eventCountry.value, self.eventData[0])
				if config.plugins.AdvancedEventLibrary.CreateMetaData.value:
					if self.fileName and not isfile(self.fileName.replace('.ts', '.eit').replace('.mkv', '.eit').replace('.avi', '.eit').replace('.mpg', '.eit').replace('.mp4', '.eit')):
						if self.eventOverview:
							txt = open(self.fileName + ".txt", "w")
							txt.write(self.eventOverview)
							txt.close()
					if self.fileName and not isfile(self.fileName + ".meta"):
						filedt = int(stat(self.fileName).st_mtime)
						txt = open(self.fileName + ".meta", "w")
						minfo = "1:0:0:0:B:0:C00000:0:0:0:\n" + str(self.eventTitle.value) + "\n"
						if str(self.eventGenre.value) != "":
							minfo += str(self.eventGenre.value) + ", "
						if str(self.eventCountry.value) != "":
							minfo += str(self.eventCountry.value) + ", "
						if str(self.eventYear.value) != "":
							minfo += str(self.eventYear.value) + ", "
						if minfo.endswith(', '):
							minfo = minfo[:-2]
						else:
							minfo += "\n"
						minfo += "\n" + str(filedt) + "\nAdvanced-Event-Library\n"
						txt.write(minfo)
						txt.close()
		self.doClose()

	def key_green_handler(self):
		if self.activeList != 'choiceBox':
			self["key_green"].setText("")
			self["key_yellow"] = StaticText(_("Activate poster selection"))
			self["key_blue"] = StaticText(_("Activate Cover selection"))
			self.activeList = 'editor'

	def key_yellow_handler(self):
		if self.activeList != 'choiceBox':
			self["key_green"].setText("Activate Editor")
			self["key_yellow"].setText("")
			self["key_blue"].setText("Activate Cover selection")
			self.activeList = 'poster'
			self.showPreview()

	def key_blue_handler(self):
		if self.activeList != 'choiceBox':
			self["key_green"].setText("Activate Editor")
			self["key_yellow"].setText("Activate poster selection")
			self["key_blue"].setText("")
			self.activeList = 'cover'
			self.showPreview()

	def buildConfigList(self):
		if self.configlist:
			del self.configlist[:]
		self.configlist.append(getConfigListEntry(_("Event-Informations")))
		self.configlist.append(getConfigListEntry(_("Event name (search with OK)"), self.eventTitle))
		self.configlist.append(getConfigListEntry(_("Genre"), self.eventGenre))
		self.configlist.append(getConfigListEntry(_("Country"), self.eventCountry))
		self.configlist.append(getConfigListEntry(_("Year of publication"), self.eventYear))
		self.configlist.append(getConfigListEntry(_("Rating"), self.eventRating))
		self.configlist.append(getConfigListEntry(_("FSK (Germany only)"), self.eventFSK))

	def changedEntry(self):
		self.buildConfigList()
		cur = self["config"].getCurrent()
		self["config"].setList(self.configlist)
#		if cur and cur is not None:
#			self["config"].updateConfigListView(cur)

	def doClose(self):
		if self.activeList == 'choiceBox':
			self["key_yellow"] = StaticText(_("Activate poster selection"))
			self["key_blue"] = StaticText(_("Activate Cover selection"))
			self['sList'].hide()
			self['config'].show()
			self.activeList = 'editor'
		else:
			filelist = glob(join("/tmp/", "*.jpg"))
			for f in filelist:
				remove(f)
			clearMem("AEL-Editor")
			self.close()


class TVSmakeReferenceFile(Screen):
	skin = """
	<screen name="TVSmakeReferenceFile" position="480,90" size="320,540" backgroundColor="#10f5f5f5" flags="wfNoBorder" resolution="1280,720" title="TV Spielfilm">
		<widget source="headline" render="Label" position="0,0" size="320,60" font="Regular;24" transparent="1" foregroundColor="#00373f43" backgroundColor="#10f5f5f5" halign="center" valign="center" zPosition="3" />
		<widget source="bouquetslist" render="Listbox" position="0,60" size="320,440" backgroundColor="#10f5f5f5" enableWrapAround="1" scrollbarMode="showNever" scrollbarBorderWidth="2" scrollbarForegroundColor="#10f5f5f5" scrollbarBorderColor="#7e7e7e">
			<convert type="TemplatedMultiContent">
				{"template": [
				MultiContentEntryText(pos=(0,0), size=(320,30), font=0, color="#10152e4e", backcolor="#10f5f5f5", color_sel="#10f5f5f5", backcolor_sel="#10152e4e", flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text=0),  # menutext
				],
				"fonts": [gFont("Regular",20)],
				"itemHeight":30
				}
			</convert>
		</widget>
		<eLabel name="blue" position="86,504" size="8,30" backgroundColor="blue" zPosition="1" />
		<widget name="key_blue" position="100,506" size="210,30" font="Regular;20" foregroundColor="#00373f43" backgroundColor="#10f5f5f5" />
	</screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.mappinglog = join(aelGlobals.LOGPATH, "AEL_TVSmapping.log")
		self.totaldupes = []
		self.totalimport = []
		self.totalunsupp = []
		self["headline"] = StaticText(_("TV Spielfilm\nBouquets import"))
		self["key_blue"] = Label(_("check converting rules"))
		self["bouquetslist"] = List()
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
							  {"ok": self.keyOk,
								"blue": self.keyBlue,
								"cancel": self.keyExit
								}, -1)
		self.onLayoutFinish.append(self.layoutFinished)
		self.maplist = self.readMappingList()

	def layoutFinished(self):
		if not exists(aelGlobals.TVS_MAPFILE):
			write_log(f"Error in module 'TVSmakeReferenceFile:onShownFinished': file '{aelGlobals.TVS_MAPFILE}' not found.")
			self.session.open(MessageBox, _("File '%s' not found.\nTV Spielfilm import function can't be supported" % aelGlobals.TVS_MAPFILE), MessageBox.TYPE_ERROR, timeout=10, close_on_any_key=True)
			self.keyExit()
		self.getAllBouquets()

	def keyExit(self):
		self.close(False)

	def keyBlue(self):
		self.checkMappingList()
		self.session.open(MessageBox, _("Conversion rules in file '%s' have been ckecked.\nThe detailed analysis can be found in the logfile:\n'%s'" % (aelGlobals.TVS_MAPFILE, self.mappinglog)), MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)

	def keyOk(self):
		current = self["bouquetslist"].getCurrent()  # e.g. ('Favoriten (TV)', <enigma.eServiceReference; proxy of <Swig Object of type 'eServiceReference *' at 0xa70d46f8> >)
		importlist, dupeslist, unsupported = self.importBouquet(current[1])
		if importlist:
			for item in importlist:
				if item[1][0] in [x[1][0] for x in self.totalimport]:  # TVS service already listed?
					self.totaldupes.append(item)
				else:
					self.totalimport.append(item)
			self.totaldupes += dupeslist
			self.totalunsupp += unsupported
			totalfound = importlist + dupeslist + unsupported
			self.appendImportLog(current[0], totalfound, importlist, dupeslist, unsupported)
			msg = "\nChannels just found in the bouquet: %s" % len(totalfound)
			msg += "\nChannel shortcuts just successfully imported: %s" % len(importlist)
			msg += "\nDuplicate channel shortcuts that have not yet been imported: %s" % len(dupeslist)
			msg += "\nChannels not supported by TV Spielfilm: %s" % len(unsupported)
			msg += f"\n{'-' * 80}"
			msg += "\nTotal number of successfully imported channels to date: %s" % len(importlist)
			msg += "\nDuplicate channel shortcuts that have not yet been imported: %s" % len(dupeslist)
			msg += "\n\nWould you like to import another TV bouquet?"
		else:
			msg = "\nNo TV Spielfilm channels found.\nPlease select another TV bouquet."
		self.session.openWithCallback(self.anotherBouquet, MessageBox, msg, MessageBox.TYPE_YESNO, timeout=30, default=False)

	def anotherBouquet(self, answer):
		if answer is True:
			self.getAllBouquets()
		else:  # create TVS service-, dupes and unsupported JSONs and finish successfully
			if self.totalimport:
				with open(f"{aelGlobals.TVS_REFFILE}.new", "w") as file:
					file.write(dumps(dict(self.totalimport)))
				rename(f"{aelGlobals.TVS_REFFILE}.new", aelGlobals.TVS_REFFILE)
			if self.totaldupes:
				dupesfile = join(aelGlobals.CONFIGPATH, "tvs_dupes.json")
				with open(f"{dupesfile}.new", 'w') as file:
					file.write(dumps(dict(self.totaldupes)))
				rename(f"{dupesfile}.new", dupesfile)
			if self.totalunsupp:
				unsuppfile = join(aelGlobals.CONFIGPATH, "tvs_unsupported.json")
				with open(f"{unsuppfile}.new", 'w') as file:
					file.write(dumps(dict(self.totalunsupp)))
				rename(f"{unsuppfile}.new", unsuppfile)
			self.session.open(MessageBox, _("The bouquet(s) import was successful.\nThe detailed analysis can be found in the logfile:\n'%s'" % f"{aelGlobals.LOGPATH}AEL_TVSbouquets.log"), MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
			self.close(True)

	def getAllBouquets(self):
		bouquetstr = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet' if config.usage.multibouquet.value else '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet'
		root = eServiceReference(bouquetstr)
		serviceHandler = eServiceCenter.getInstance()
		bouquetsList = []
		if config.usage.multibouquet.value:
			serviceList = serviceHandler.list(root)
			while True:
				service = serviceList.getNext()
				if not service.valid():
					del serviceList
					break
				if service.flags & eServiceReference.isDirectory:
					info = serviceHandler.info(service)
					if info:
						bouquetsList.append((info.getName(service), service))
		else:
			info = serviceHandler.info(root)
			if info:
				bouquetsList.append((info.getName(root), root))
		self["bouquetslist"].updateList(bouquetsList)

	def importBouquet(self, bouquet=None):
		if not bouquet:  # fallback to favorites
			bouquet = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet'
			bouquet = eServiceReference(bouquet)
		supported, unsupported, importlist, dupeslist, = [], [], [], []
		slist = ServiceList(bouquet, validate_commands=False)
		services = slist.getServicesAsList(format='SN')  # z.B. [('1:0:27:212F:31B:1:FFFF0000:0:0:0:', 'Das Erste HD'), ...]
		for service in services:
			found = ""
			sname = service[1].strip()
			sref = f"{service[0].split("http")[0]}{{IPTV-Stream}}" if "http" in service[0].lower() else service[0]
			for tvskey, regstr in self.maplist:  # find TVS shortcut for channelname
				if match(compile(regstr), sname.lower()):
					found = tvskey
					break
			if found:
				supported.append((sref.rstrip(), tuple((found.rstrip(), sname.rstrip()))))
			else:
				unsupported.append((sref.rstrip(), tuple(("", sname.rstrip()))))
		for item in supported:  # divide into import and duplicate
			if item[1][0] in [x[1][0] for x in importlist]:
				dupeslist.append(item)
			else:
				importlist.append(item)
		return importlist, dupeslist, unsupported

	def readMappingList(self):  # read mapping (=conversion rules (TVS channel abbreviation: E2 service name))
		maplist = []
		with open(aelGlobals.TVS_MAPFILE, "r") as file:  # read line-by-line to show the faulty error line
			line = "{No line evaluated yet}"
			try:
				for line in file.read().replace(",", "").strip().split("\n"):
					if not line.startswith("#"):
						items = line.strip().split(": ")
						if items:
							maplist.append((items[0], items[1]))
			except Exception as error:
				write_log(f"Exception error class 'TVSmakeReferenceFile:readMappingList' in {line}: {error}")
		return maplist

	def appendImportLog(self, bouquetname, totalfound, importlist, dupeslist, unsupported):  # append last import results to logfile
		with open(join(aelGlobals.LOGPATH, "AEL_TVSbouquets.log"), "a") as file:
			file.write(_("%s\n%i channel(s) found in bouquet '%s' (incl. duplicate TVS shortcuts)\n%s\n") % ('=' * 78, len(totalfound), bouquetname, '=' * 78))
			formatstr = "{0:<10} {1:<40} {2:<0}\n"
			for item in totalfound:
				file.write(formatstr.format(*(item[1][0] or _("n/a"), item[0], item[1][1])))
			file.write(_("\n%i imported TV movie channel(s) (without duplicate TVS shortcuts):\n%s\n") % (len(importlist), '-' * 78))
			for item in importlist:
				file.write(formatstr.format(*(item[1][0], item[0], item[1][1])))
			file.write(_("\n%i not imported channel(s) (because duplicate TVS shortcuts):\n%s\n") % (len(dupeslist), '-' * 78))
			for item in dupeslist:
				file.write(formatstr.format(*(item[1][0], item[0], item[1][1])))
			file.write(_("\n%i channel(s) not supported by TV Spielfilm:\n%s\n") % (len(unsupported), '-' * 78))
			for item in unsupported:
				file.write(formatstr.format(*(_("n/a"), item[0], item[1][1])))
			file.write("\n")

	def checkMappingList(self):  # tool: checks whether conversion rules are missing / obsolete / double in the mapping file
		maplist = sorted(self.maplist, key=lambda x: x[0])
		mapkeys = [x[0] for x in maplist]
		tvsurl = b64decode(b"aHR0cHM6Ly9saXZlLnR2c3BpZWxmaWxtLmRlL3N0YXRpYy9jb250ZW50L2NoYW5uZWwtbGlzdC9saXZldHY=u"[:-1]).decode()
		errmsg, results = getAPIdata(tvsurl)
		if errmsg:
			write_log("API download error in module 'checkMappingList", DEFAULT_MODULE_NAME)
		if results:
			reskeys = [x.get("id", _("n/a")).lower() for x in results]
			formatstr = "{0:<10} {1:<0}\n"
			with open(self.mappinglog, "w") as file:
				file.write("Found %s channels that are supported by TV Spielfilm\n" % len(results))
				file.write(_("\nMissing rules for channels supported by TV Spielfilm: "))
				notfound = []
				for service in results:  # search for missing conversion rules
					shortkey = service.get("id", _("n/a")).lower()
					if shortkey not in mapkeys:
						notfound.append((shortkey, service.get("name", _("n/v"))))
				if notfound:
					file.write(f"\n{formatstr.format(*(_('shortkey'), _('Channel name')))}")
					file.write("%s\n" % ('-' * 58))
					for service in notfound:
						file.write(formatstr.format(*service))
				else:
					file.write(_("{No missing rules found}\n"))
				file.write(_("\nObsolete rules for channels supported by TV Spielfilm: "))
				obsolete = []
				for service in maplist:  # search for obsolete conversion rules
					if service[0] not in reskeys:
						obsolete.append((service[0], service[1]))
				if obsolete:
					file.write(f"\n{formatstr.format(*(_('shortkey'), _('conversion rule')))}")
					file.write("%s\n" % ('-' * 58))
					for service in obsolete:
						file.write(formatstr.format(*service))
				else:
					file.write(_("{No obsolete rules found}\n"))
				file.write(_("\nDuplicate rules for channels supported by TV Spielfilm: "))
				double = []
				for idx in [i for i, x in enumerate(mapkeys) if mapkeys.count(x) > 1]:  # search for duplicate rules and get indexes
					double.append((maplist[idx][0], maplist[idx][1]))
				if double:
					file.write(f"\n{formatstr.format(*(_('shortkey'), _('conversion rule')))}")
					file.write("%s\n" % ('-' * 58))
					for service in double:
						file.write(formatstr.format(*service))
				else:
					file.write(_("{No duplicate rules found}\n"))
