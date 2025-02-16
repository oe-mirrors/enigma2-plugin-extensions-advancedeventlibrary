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
from os import rename, system, remove, stat, makedirs, statvfs
from os.path import isfile, getsize, exists, join, basename, getmtime
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
from Tools.AdvancedEventLibrary import aelGlobals, aelHelper, PicLoader

from . import _  # for localized messages

DEFAULT_MODULE_NAME = __name__.split(".")[-1]


def loadskin(filename):
	with open(join(aelGlobals.SKINPATH, filename), "r") as f:
		skin = f.read()
		f.close()
	return skin


class AELinfoBox(Screen):
	skin = """
	<screen name="AELinfoBox" position="390,432" size="500,110" flags="wfNoBorder" resolution="1280,720" title="AEL Infobox">
		<eLabel position="0,0" size="500,110" backgroundColor="#00203060" zPosition="-1" />
		<eLabel position="2,2" size="496,106" zPosition="-1" />
		<widget source="info" render="Label" position="5,5" size="490,100" font="Regular;24" halign="center" valign="center" />
	</screen>
	"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["info"] = StaticText()
		self.isVisible = False
		self.aelinfoboxTimer = eTimer()
		self.aelinfoboxTimer.callback.append(self.hideDialog)

	def showDialog(self, info, timeout=2500):
		self["info"].setText(info)
		self.isVisible = True
		self.show()
		self.aelinfoboxTimer.start(timeout, True)

	def hideDialog(self):
		self.aelinfoboxTimer.stop()
		self.isVisible = False
		self.hide()

	def getIsVisible(self):
		return self.isVisible


class AELMenu(Screen):  # Einstieg mit 'AEL-Übersicht'
	ALLOW_SUSPEND = True
	skin = str(loadskin("AdvancedEventLibraryMenu.xml"))

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		aelHelper.writeLog("##### starting Advanced Event Library GUI #####")
		self.skinName = 'Advanced-Event-Library-Menu'
		self.title = f"{_('Advanced-Event-Library Menüauswahl')}: (R{aelGlobals.CURRENTVERSION})"
		self.memInfo = ""
		self.statistic = ""
		self.lang = "de"
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Start scan"))
		self["key_yellow"] = StaticText(_("Create backup"))
		self["key_blue"] = StaticText(_("Create TVS reference"))
		#=============== geaendert (#6) ================
		#self["key_blue"] = StaticText("")
		#self["key_blue"] = StaticText(_("Clean up"))
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
		self.refreshStatus.callback.append(self.updateStatus)
		self.reload = eTimer()
		self.reload.callback.append(self.goReload)
		self.delayedStart = eTimer()
		self.delayedStart.callback.append(self.readMandatoryFiles)  # unfortunately necessary, because 'self.session.open(MessageBox,...)' returns a modal error
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.delayedStart.start(250, True)
		aelHelper.setScanStopped(True)
		self.updateStatistics()
		self.updateStatus()

	def updateStatistics(self):
		confdir = join(aelGlobals.CONFIGPATH, "eventLibrary.db") if config.plugins.AdvancedEventLibrary.dbFolder.value == "Flash" else f"{config.plugins.AdvancedEventLibrary.Location.value}eventLibrary.db"
		self.db = aelHelper.getDB()
		if isfile(confdir):
			GET = aelGlobals.PARAMETER_GET
			posterCount = self.db.parameter(GET, 'posterCount', None, 0)
			posterSize = str(self.db.parameter(GET, 'posterSize', None, 0))
			coverCount = self.db.parameter(GET, 'coverCount', None, 0)
			coverSize = str(self.db.parameter(GET, 'coverSize', None, 0))
			previewCount = self.db.parameter(GET, 'previewCount', None, 0)
			previewSize = str(self.db.parameter(GET, 'previewSize', None, 0))
			usedInodes = self.db.parameter(GET, 'usedInodes', None, 0)
			lastPosterCount = self.db.parameter(GET, 'lastPosterCount', None, 0)
			lastCoverCount = self.db.parameter(GET, 'lastCoverCount', None, 0)
			lastEventInfoCount = int(str(self.db.parameter(GET, 'lastEventInfoCount', None, 0)))
			lastEventInfoCountSuccsess = int(str(self.db.parameter(GET, 'lastEventInfoCountSuccsess', None, 0)))
			lastPreviewImageCount = int(str(self.db.parameter(GET, 'lastPreviewImageCount', None, 0)))
			lastAdditionalDataCount = int(str(self.db.parameter(GET, 'lastAdditionalDataCount', None, 0)))
			lastAdditionalDataCountBlacklist = int(str(self.db.parameter(GET, 'lastAdditionalDataCountSuccess', None, 0)))
			lastAdditionalDataCountSuccess = lastAdditionalDataCount - lastAdditionalDataCountBlacklist
			lastUpdateStart, lastUpdateDuration = self.getlastUpdateInfo(self.db)
			dbSize = getsize(confdir) / 1024.0
			titleCount = self.db.getTitleInfoCount()
			blackListCount = self.db.getblackListCount()
			percent = round(100 * titleCount / (titleCount + blackListCount)) if (titleCount + blackListCount) > 0 else 0
			liveTVtitleCount = self.db.getliveTVCount()
			liveTVidtitleCount = self.db.getliveTVidCount()
			percentTV = round(100 * liveTVidtitleCount / liveTVtitleCount) if (liveTVidtitleCount + liveTVtitleCount) > 0 else 0
			percentlIC = round(100 * lastEventInfoCountSuccsess / lastEventInfoCount) if lastEventInfoCount > 0 else 0
			percentlaC = round(100 * lastAdditionalDataCountSuccess / lastAdditionalDataCount) if lastAdditionalDataCount > 0 else 0
			cpS = round(float(posterSize.replace('G', '')) * 1024.0, 2) if 'G' in posterSize else posterSize
			ccS = round(float(coverSize.replace('G', '')) * 1024.0, 2) if 'G' in coverSize else coverSize
			pcS = round(float(previewSize.replace('G', '')) * 1024.0, 2) if 'G' in previewSize else previewSize
			trailerCount = self.db.getTrailerCount()
			size = int(float(str(cpS).replace('G', '').replace('M', '').replace('kB', '').replace('K', '')) + float(str(ccS).replace('G', '').replace('M', '').replace('kB', '').replace('K', '')) + float(str(pcS).replace('G', '').replace('M', '').replace('kB', '').replace('K', '')) + round(float(dbSize / 1024.0), 1))
			tabpos = "{0:<22} {1:<17} {2:<0}\n"
			statistic = f"{_('Statistics last search run:')}\n"
			statistic += f"{_('Number of posters | Cover | Preview images:')} {lastPosterCount} | {lastCoverCount} | {lastPreviewImageCount}\n"
			statistic += tabpos.format(f"{_('Event information:')}", lastEventInfoCount, f"found: {'{:5d}'.format(lastEventInfoCountSuccsess)} | {percentlIC} %")
			statistic += tabpos.format(f"{_('Extra data sought:')}", lastAdditionalDataCount, f"{_('found:')} {'{:5d}'.format(lastAdditionalDataCountSuccess)} | {percentlaC} %")
			statistic += tabpos.format(f"{_('Executed on:')}", f"{lastUpdateStart} h", f"{_('Duration:')} {lastUpdateDuration} h")
			statistic += f"\n{_('Total statistics:')}\n"
			statistic += tabpos.format(f"{_('Entries')}:", f"{'{:5d}'.format(titleCount)} | {'{:5d}'.format(blackListCount)} | {percent} %", "")
			statistic += tabpos.format(f"{_('Extra data')}:", f"{'{:5d}'.format(liveTVtitleCount)} | {'{:5d}'.format(liveTVidtitleCount)} | {percentTV} %", "")
			statistic += tabpos.format(f"{_('Number of posters')}:", posterCount, f"{_('Size')}: {posterSize}")
			statistic += tabpos.format(f"{_('Number of covers')}:", coverCount, f"{_('Size')}: {coverSize}")
			statistic += tabpos.format(f"{_('Number of previews')}:", previewCount, f"{_('Size')}: {previewSize}")
			statistic += tabpos.format(f"{_('Number of trailers')}:", trailerCount, "")
			statistic += tabpos.format(f"{_('Database size')}:", f'{dbSize} KB', f"{_('Size')}: {coverSize}")
			statistic += tabpos.format(f"{_('Storage space')}:", f"{size} / {int(config.plugins.AdvancedEventLibrary.MaxSize.value * 1024.0)} MB", f"{_('Inodes used:')} {usedInodes}")
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
		with open("/proc/meminfo") as fd:
			for line in fd:
				if value + "Total" in line:
					check += 1
					result[0] = int(line.split()[1]) * 1024  # size
				elif value + "Free" in line:
					check += 1
					result[2] = int(line.split()[1]) * 1024  # avail
				if check > 1:
					if result[0] > 0:
						result[1] = result[0] - result[2]  # used
						result[3] = result[1] * 100 // result[0]  # use%
					break
		tabpos = "{0:<11} {1:<10} {2:<16} {3:<12} {4:<0}\n"
		return tabpos.format(f"{_('RAM')}:", aelHelper.getSizeStr(result[0]), f"{_('free')}: {aelHelper.getSizeStr(result[2])}", f"{_('occupied')}: {aelHelper.getSizeStr(result[1])}", f"({result[3]} %)")

	def getDiskInfo(self, path=None):
		def getMountPoints():
			mounts = []
			fd = open("/proc/mounts", "r")
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
			if "/media" in mountPoint or path:
				st = statvfs(mountPoint)
			if st is not None and 0 not in (st.f_bsize, st.f_blocks):
				result = [0, 0, 0, 0, mountPoint.replace("/media/net/autonet", "/...").replace("/media/net", "/...")]  # (size, used, avail, use%)
				result[0] = st.f_bsize * st.f_blocks  # size
				result[2] = st.f_bsize * st.f_bavail  # avail
				result[1] = result[0] - result[2]  # used
				result[3] = result[1] * 100 // result[0]  # use%
				resultList.append(result)
		tabpos = "{0:<11} {1:<10} {2:<16} {3:<12} {4:<0}\n"
		res = ""
		for result in resultList:
			result4 = f"{_('Flash')}:" if result[4] == "/" else f"{result[4]}:"
			res += tabpos.format(result4, aelHelper.getSizeStr(result[0]), f"{_('free')}: {aelHelper.getSizeStr(result[2])}", f"{_('occupied')}: {aelHelper.getSizeStr(result[1])}", f"({result[3]} %)")
		return res

	def getlastUpdateInfo(self, db):
		lastUpdateStart = self.convertTimestamp(db.parameter(aelGlobals.PARAMETER_GET, "laststart", None, 0))
		lastUpdateDuration = self.convertDuration(float(db.parameter(aelGlobals.PARAMETER_GET, "laststop", None, 0)) - float(db.parameter(aelGlobals.PARAMETER_GET, "laststart", None, 0)) - 3600)
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
					aelHelper.writeLog(f"AEL network file '{aelGlobals.NETWORKFILE}' successfully loaded.")
			except Exception as errmsg:
				aelHelper.writeLog(f"Exception in module 'readMandatoryFiles' for AEL networks file '{aelGlobals.NETWORKFILE}': {errmsg}")
				self.session.open(MessageBox, _("Exception error while reading AEL networks file '%s': %s\nCan't continue Advanced Event Library!" % (aelGlobals.NETWORKFILE, errmsg)), MessageBox.TYPE_ERROR, timeout=10, close_on_any_key=True)
				self.do_close()
		else:
			aelHelper.writeLog(f"Error in module 'readMandatoryFiles': AEL networks file '{aelGlobals.NETWORKFILE}' not found.")
			self.session.open(MessageBox, _("AEL networks file '%s' not found.\nCan't continue Advanced Event Library!" % aelGlobals.NETWORKFILE), MessageBox.TYPE_ERROR, timeout=10, close_on_any_key=True)
			self.do_close()
		if exists(aelGlobals.TVS_REFFILE):
			try:
				with open(aelGlobals.TVS_REFFILE, "r") as file:
					aelGlobals.TVS_REFDICT = loads(file.read())
					aelHelper.writeLog(f"TV Spielfilm reference file '{aelGlobals.TVS_REFFILE}' successfully loaded.")
			except Exception as errmsg:
				aelHelper.writeLog(f"Exception in module 'readMandatoryFiles' for TVS reference file '{aelGlobals.TVS_REFFILE}': {errmsg}")
				self.session.open(MessageBox, _("Exception error while reading file '%s': %s\nTV Spielfilm services can't be supported at all!" % (aelGlobals.TVS_REFFILE, errmsg)), MessageBox.TYPE_ERROR, timeout=10, close_on_any_key=True)
		else:
			aelHelper.writeLog(f"Error in module 'readMandatoryFiles': TVS reference file '{aelGlobals.TVS_REFFILE}' not found.")
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
		if aelHelper.isScanStopped():
			if exists(aelGlobals.TVS_REFFILE):
				aelHelper.setScanStopped(False)
				self["status"].setText(_("start search run..."))
				self["key_green"].setText(_("Stop scan"))
				aelGlobals.createDirs(config.plugins.AdvancedEventLibrary.Location.value)
				aelHelper.startUpdate(self.lang, self.startUpdateCB)
			else:
				msg = _("The TVS reference file was not found.\nTV Spielfilm can therefore not be supported!\n\nShould a bouquets import be carried out now (recommended)?")
				self.session.openWithCallback(self.key_green_answer, MessageBox, msg, MessageBox.TYPE_YESNO, timeout=5, default=False)
		else:
			msg = _("Should the search run really be canceled?")
			self.session.openWithCallback(self.stopScan_answer, MessageBox, msg, MessageBox.TYPE_YESNO, timeout=5, default=False)

	def key_green_answer(self, answer):
		if answer is True:
			self.key_blue_handler()
		else:
			aelHelper.setScanStopped(False)
			self["status"].setText(_("start search run..."))
			self["key_green"].setText(_("Stop scan"))
			aelHelper.startUpdate(self.lang, self.startUpdateCB)

	def stopScan_answer(self, answer):
		if answer is True:
			aelHelper.setScanStopped(True)
			self["status"].setText(_("stopping search run..."))
			self["key_green"].setText(_("Start scan"))
			aelHelper.writeLog("### ...Update was stopped due to user request ###")

	def startUpdateCB(self):
		aelHelper.setScanStopped(True)
		self.updateStatus()
		self["key_green"].setText(_("Start scan"))
		self.updateStatistics()

	def key_yellow_handler(self):
		callInThread(aelHelper.createBackup)

	def key_blue_handler(self):
		self.session.open(TVSimport)

	def updateStatus(self):
		self["status"].setText(aelGlobals.STATUS if aelGlobals.STATUS else _("No search is currently running."))
		self.memInfo = f"\n{_('Memory allocation')} :\n{self.getDiskInfo('/')}"
		self.memInfo += self.getMemInfo("Mem")
		self.memInfo += f"\n{_('Mountpoints')}:\n{self.getDiskInfo()}"
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
#			aelHelper.writeLog(f"return {ret}", DEFAULT_MODULE_NAME)
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
		self["key_yellow"] = StaticText(_("TV-Spielfilm channel import"))
		self["coloractions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyYellow, _(" "))
		}, prio=0)

#		self.myFileListActive = False
#		self["config"].onSelectionChanged.append(self.selectionChanged)

	def keyYellow(self):
		self.session.open(TVSimport)  # TODO: fliegt raus

	def keySelect(self):
		def keySelectCallback(value):
			self.getCurrentItem().value = value
			#aelHelper.createDirs(value) # TODO
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
#			aelHelper.writeLog(f"Error in buildConfigList : {ex}", DEFAULT_MODULE_NAME)


#	def do_close(self):
#		restartbox = self.session.openWithCallback(self.restartGUI, MessageBox, _("GUI needs a restart to apply new configuration.\nDo you want to restart the GUI now ?"), MessageBox.TYPE_YESNO)
#		restartbox.setTitle(_("GUI needs a restart."))

#	def restartGUI(self, answer):
#		if answer is True:
#			for x in self["config"].list:
#				if len(x) > 1:
#					if "suche" not in x[0] and "Einstellungen" not in x[0] and x[0]:
#						aelHelper.writeLog(f"save : {x[0]} - {x[1].value}", DEFAULT_MODULE_NAME)
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


class TVSimport(Screen):
	skin = """
	<screen name="TVSimport" position="480,90" size="320,500" backgroundColor="#16000000" flags="wfNoBorder" resolution="1280,720" title="TV Spielfilm Import">
		<eLabel position="0,0" size="320,500" backgroundColor="#00203060" zPosition="-2" />
		<eLabel position="2,2" size="316,496" zPosition="-1" />
		<eLabel name="TV_bg" position="2,2" size="316,58" backgroundColor=" black, #00203060, horizontal" zPosition="1" />
		<eLabel name="TV_line" position="2,60" size="316,2" backgroundColor=" #0027153c , #00101093, black , horizontal" zPosition="10" />
		<ePixmap position="0,0" size="220,60" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVSpielfilm/pics/HD/logos/TVSpielfilm.png" alphatest="blend" zPosition="13" />
		<widget source="bouquetslist" render="Listbox" position="2,60" size="316,440" itemCornerRadiusSelected="4" itemGradientSelected=" #051a264d, #10304070, #051a264d, horizontal" enableWrapAround="1" foregroundColorSelected="white" backgroundColor="#16000000" transparent="1" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">{"template": [
				MultiContentEntryText(pos=(0,0), size=(316,40), font=0,  flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text=0)  # menutext
				],
				"fonts": [gFont("Regular",24)],
				"itemHeight":40
				}</convert>
		</widget>
		<eLabel name="button_blue" position="40,460" size="6,36" backgroundColor="#101093,#4040ff,vertical" zPosition="1" />
		<widget source="key_blue" render="Label" position="54,466" size="300,26" font="Regular;18" valign="center" halign="left" foregroundColor="grey" backgroundColor="#16000000" transparent="1" />
	</screen>
	"""

	def __init__(self, session):
		self.session = session
		if aelGlobals.RESOLUTION == "FHD":
			self.skin = self.skin.replace("/HD/", "/FHD/")
		Screen.__init__(self, session)
		self.aelinfobox = session.instantiateDialog(AELinfoBox)
		self.maplist = []
		self.totaldupes = []
		self.totalimport = []
		self.totalsupp = []
		self.totalunsupp = []
		self["bouquetslist"] = List()
		self["key_blue"] = StaticText(_("Verify conversion rules"))
		self['actions'] = ActionMap(["OkCancelActions",
							   		"ColorActions"], {"ok": self.keyOk,
							  						"blue": self.keyBlue,
													"cancel": self.keyExit}, -1)
		self.onShown.append(self.shownFinished)

	def shownFinished(self):
		self.maplist = self.readMappingList()
		if not exists(aelGlobals.CONFIGPATH):
			makedirs(aelGlobals.CONFIGPATH, exist_ok=True)
		sourcefile = join(aelGlobals.PLUGINPATH, "db/tvs_mapping.txt")
		if not exists(aelGlobals.TVS_MAPFILE) or (config.plugins.tvspielfilm.update_mapfile.value and int(getmtime(sourcefile)) < int(getmtime(aelGlobals.TVS_MAPFILE))):  # plugin mapfile older than user mapfile:
			print(f"[{aelGlobals.MODULE_NAME}] Copy '{sourcefile}' to '{aelGlobals.CONFIGPATH}'.")
			copy(sourcefile, aelGlobals.TVS_MAPFILE)
		if exists(aelGlobals.TVS_MAPFILE):
			self.getAllBouquets()
		else:
			print(f"[{aelGlobals.MODULE_NAME}] Error in class 'TVimport:shownFinished': file '{aelGlobals.TVS_MAPFILE}' not found.")
			self.session.open(MessageBox, _("File '%s' can neither be found nor created.\nTVS import can therefore not be continued!") % aelGlobals.TVS_MAPFILE, MessageBox.TYPE_ERROR, timeout=30, close_on_any_key=True)
			self.keyExit()

	def keyExit(self):
		self.close()

	def keyBlue(self):
		self.checkMappingRules()
		self.session.open(MessageBox, _("The channel name conversion rules in the file:\n'%s'\nwere checked.\n\nThe detailed analysis can be found in the log file:\n'%s'" % (aelGlobals.TVS_MAPFILE, self.mappinglog)), MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)

	def keyOk(self):
		current = self["bouquetslist"].getCurrent()  # e.g. ('Favoriten (TV)', <enigma.eServiceReference; proxy of <Swig Object of type 'eServiceReference *' at 0xa70d46f8> >)
		importlist, dupeslist, supplist, unsupplist = self.importBouquet(current[1])
		if importlist:
			# combine two lists without duplicate entries while retaining the sort order
			self.totalimport = list(dict(dict(self.totalimport), **dict(importlist)).items())  # will be later reduced by TVchannelselection
			self.totaldupes = list(dict(dict(self.totaldupes), **dict(dupeslist)).items())
			self.totalsupp = list(dict(dict(self.totalsupp), **dict(supplist)).items())  # complete list of channels supported by the server
			self.totalunsupp = list(dict(dict(self.totalunsupp), **dict(unsupplist)).items())
			totalfound = importlist + dupeslist + unsupplist
			self.appendImportLog(current[0], totalfound, importlist, dupeslist, unsupplist)
			msg = _("\nChannels just found in the bouquet: %s" % len(totalfound))
			msg += _("\nSuccessfully imported channel abbreviations: %s" % len(importlist))
			msg += _("\nDuplicate channel abbreviations not yet imported: %s" % len(dupeslist))
			msg += _("\nChannels just found that are not supported by TVSpielfilm: %s" % len(unsupplist))
			msg += f"\n{'-' * 120}"
			msg += _("\nSuccessfully imported channel abbreviations to date: %s" % len(self.totalimport))
			msg += _("\nDuplicate channel abbreviations not yet imported: %s" % len(self.totaldupes))
			msg += _("\nChannels found so far that are not supported by TVSpielfilm: %s" % len(self.totalunsupp))
			msg += _("\n\nShould another TV bouquet be imported?")
		else:
			msg = _("\nNo TV Spielfilm channels found.\nPlease select another TV bouquet.")
		self.session.openWithCallback(self.anotherBouquet, MessageBox, msg, MessageBox.TYPE_YESNO, timeout=30, default=False)

	def anotherBouquet(self, answer):
		if answer is True:
			self.getAllBouquets()
		else:  # create TVSpielfilm service- and dupesJSON and finish successfully
			self.session.openWithCallback(self.anotherBouquetCB, TVchannelselection, self.totalimport)

	def anotherBouquetCB(self, answer):
		if answer:
			if answer[0] is True:
				if self.totalimport:
					supportedchannels = []
					importedchannels = []
					for index, channel in enumerate(answer[1]):
						if channel[1]:
							supportedchannels.append((self.totalsupp[index][1][0], (self.totalsupp[index][0], self.totalsupp[index][1][1])))
							importedchannels.append((self.totalimport[index][1][0], (self.totalimport[index][0], self.totalimport[index][1][1])))  # e.g. ('ard', ('1:0:19:283D:41B:1:FFFF0000:0:0:0:', 'Das Erste HD'))
					with open(f"{aelGlobals.TVS_REFFILE}.new", 'w') as file:  # all imported channels only
						file.write(dumps(dict(importedchannels)))
						rename(f"{aelGlobals.TVS_REFFILE}.new", aelGlobals.TVS_REFFILE)
					suppfile = join(aelGlobals.CONFIGPATH, "tvs_supported.json")
					with open(f"{suppfile}.new", 'w') as file:  # all channels supported by Server
						file.write(dumps(dict(supportedchannels)))
						rename(f"{suppfile}.new", suppfile)
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
				self.aelinfobox.showDialog(_("Channel import successfully completed."))
			else:
				self.aelinfobox.showDialog(_("Channel import canceled!"))
			self.close()

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
			bouquet = eServiceReference('1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet')
		supported, unsupported, importlist, dupeslist, = [], [], [], []
		slist = ServiceList(bouquet, validate_commands=False)
		services = slist.getServicesAsList(format='SN')  # z.B. [('1:0:27:212F:31B:1:FFFF0000:0:0:0:', 'Das Erste HD'), ...]
		for service in services:
			found = ""
			sname = service[1].strip()
			sref = f"{service[0].split('http')[0]}{{IPTV-Stream}}" if "http" in service[0].lower() else service[0]
			for channelId, regstr in self.maplist:  # find TVSpielfilm shortcut for channelname
				if match(compile(regstr), sname.lower()):
					found = channelId
					break
			if found:
				supported.append((sref.rstrip(), tuple((found.rstrip(), sname.rstrip()))))
			else:
				unsupported.append((sref.rstrip(), tuple(("", sname.rstrip()))))
		for item in supported:  # divide into import and duplicate
			if item[1][0] not in [x[1][0] for x in importlist]:
				importlist.append(item)
			else:
				dupeslist.append(item)

		return importlist, dupeslist, supported, unsupported

	def readMappingList(self):  # Read mapping (=translation rules 'TVSpielfilm channel abbreviation: E2 service name')
		maplist = []
		with open(aelGlobals.TVS_MAPFILE) as file:  # /etc/enigma2/TVSpielfilm
			line = "{No line evaluated yet}"
			try:
				for line in file.read().replace(",", "").strip().split("\n"):
					if not line.startswith("#"):
						items = line.strip().split(": ")
						if items:
							maplist.append((items[0], items[1]))
			except Exception as error:
				print(f"[{aelGlobals.MODULE_NAME}] Exception error class 'TVimport:readMappingList' in {line}: {error}")
		return maplist

	def appendImportLog(self, bouquetname, totalfound, importlist, dupeslist, unsupported):  # append last successful import to logfile
		with open(f"{aelGlobals.LOGPATH}bouquetimport.log", "a") as file:
			file.write(f"{'=' * 78}\n{len(totalfound)} channels found in bouquet '{bouquetname}' (incl. duplicate TVSpielfilm shortcuts)\n{'=' * 78}\n")
			formatstr = "{0:<10} {1:<40} {2:<0}\n"
			for item in totalfound:
				file.write(formatstr.format(*(item[1][0] or "n/a", item[0], item[1][1])))
			file.write(f"\n{len(importlist)} imported TV movie channels (without duplicate TVSpielfilm shortcuts):\n{'-' * 78}\n")
			for item in importlist:
				file.write(formatstr.format(*(item[1][0], item[0], item[1][1])))
			file.write(f"\n{len(dupeslist)} not imported channels (because duplicate TVSpielfilm shortcuts):\n{'-' * 78}\n")
			for item in dupeslist:
				file.write(formatstr.format(*(item[1][0], item[0], item[1][1])))
			file.write(f"\n{len(unsupported)} channels not supported by TV-Spielfilm:\n{'-' * 78}\n")
			for item in unsupported:
				file.write(formatstr.format(*("n/a", item[0], item[1][1])))
			file.write("\n")

	def checkMappingRules(self):  # tool: checks whether conversion rules are missing / outdated / double in the mapping file
		maplist = sorted(self.maplist, key=lambda x: x[0])
		mapkeys = [x[0] for x in maplist]
		url = "https://live.tvspielfilm.de/static/content/channel-list/livetv"   # TODO: encoden
		errmsg, results = aelHelper.getAPIdata(url)
		if errmsg:
			print(f"[{aelGlobals.MODULE_NAME}] API download ERROR in class 'TVchannelselection:checkMappingRules': {errmsg}")
		if results:
			reskeys = [x.get("id", "n/a").lower() for x in results]
			tabpos = "{0:<10} {1:<0}\n"
			self.mappinglog = join(aelGlobals.LOGPATH, "mappingrules.log")
			with open(self.mappinglog, "w") as file:
				file.write(_("%s channels found that are supported by TV Spielfilm\n" % len(results)))
				file.write(_("\nMissing rules for channels supported by TV Spielfilm:"))
				notfound = []
				for service in results:  # search for missing conversion rules
					shortkey = service.get("id", "n/a").lower()
					if shortkey not in mapkeys:
						notfound.append((shortkey, service.get("name", "n/v")))
				if notfound:
					file.write("\n%s" % tabpos.format(*(_('Shortcut'), _('Channel name'))))
					file.write(f"{'-' * 58}\n")
					for service in notfound:
						file.write(tabpos.format(*service))
					file.write(_("RECOMMENDATION: Add this rule(s) to the 'tvs_mapping.txt' file.\n"))
				else:
					file.write(_("{No missing rules found}\n"))
				file.write(_("\nInvalid rules for channels that are not supported by TV Spielfilm: "))
				outdated = []
				for service in maplist:  # search for outdated conversion rules
					if service[0] not in reskeys:
						outdated.append((service[0], service[1]))
				if outdated:
					file.write("\n%s" % tabpos.format(*(_('Shortcut'), _('Channel name'))))
					file.write(f"{'-' * 58}\n")
					for service in outdated:
						file.write(tabpos.format(*service))
					file.write(_("RECOMMENDATION: Remove this rule(s) from the 'tvs_mapping.txt' file.\n"))
				else:
					file.write(_("{No obsolete rules found}\n"))
				file.write(_("\nDouble rules for channels supported by TV Spielfilm: "))
				double = []
				for idx in [i for i, x in enumerate(mapkeys) if mapkeys.count(x) > 1]:  # search for duplicate rules and get indexes
					double.append((maplist[idx][0], maplist[idx][1]))
				if double:
					file.write("\n%s" % tabpos.format(*(_('Shortcut'), _('Channel name'))))
					file.write(f"{'-' * 58}\n")
					for service in double:
						file.write(tabpos.format(*service))
					file.write(_("RECOMMENDATION: If in doubt, leave it in the 'tvs_mapping.txt' file! Channels could, for example, be listed under different names with different providers.\n"))
				else:
					file.write(_("{No duplicate rules found}\n"))


class TVchannelselection(Screen):
	skin = """
	<screen name="TVchannelselection" position="480,20" size="320,660" backgroundColor="#16000000" flags="wfNoBorder" resolution="1280,720" title="TV Spielfilm Kanalauswahl">
		<eLabel position="0,0" size="320,660" backgroundColor="#00203060" zPosition="-2" />
		<eLabel position="2,2" size="316,656" zPosition="-1" />
		<eLabel name="TV_bg" position="2,2" size="316,58" backgroundColor=" black, #00203060, horizontal" zPosition="1" />
		<eLabel name="TV_line" position="2,60" size="316,2" backgroundColor=" #0027153c , #00101093, black , horizontal" zPosition="10" />
		<eLabel name="TV_line" position="2,616" size="316,2" backgroundColor=" #0027153c , #00101093 , black , horizontal" zPosition="10" />
		<ePixmap position="0,0" size="220,60" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVSpielfilm/pics/HD/logos/TVSpielfilm.png" alphatest="blend" zPosition="13" />
		<widget source="release" render="Label" position="180,28" size="70,20" font="Regular;18" textBorderColor="#00505050" textBorderWidth="1" foregroundColor="#00ffff00" backgroundColor="#16000000" valign="center" zPosition="12" transparent="1" />
		<widget source="channelList" render="Listbox" position="2,62" size="316,550" itemCornerRadiusSelected="4" itemGradientSelected="#051a264d,#10304070,#051a264d,horizontal" enableWrapAround="1" foregroundColorSelected="white" backgroundColor="#16000000" transparent="1" scrollbarMode="showOnDemand" scrollbarBorderWidth="1" scrollbarWidth="10" scrollbarBorderColor="blue" scrollbarForegroundColor="#00203060">
			<convert type="TemplatedMultiContent">{"template": [
				MultiContentEntryText(pos=(5,2), size=(270,30), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=0),  # menutext
				MultiContentEntryPixmapAlphaBlend(pos=(280,8), size=(20,20), flags=BT_SCALE, png="/usr/lib/enigma2/python/Plugins/Extensions/TVSpielfilm/pics/HD/icons/checkbox.png"),  # checkbox
			MultiContentEntryText(pos=(282,6), size=(18,18), font=1, color=MultiContentTemplateColor(2), color_sel=MultiContentTemplateColor(2), flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=1)  # checkmark
				],
				"fonts": [gFont("Regular",20),gFont("Regular",20),gFont("Regular",36)],
				"itemHeight":34
				}</convert>
		</widget>
		<eLabel name="button_red" position="10,626" size="6,30" backgroundColor=" #00821c17, #00fe0000, vertical" zPosition="1" />
		<eLabel name="button_green" position="180,626" size="6,30" backgroundColor=" #00006600, #0024a424, vertical" zPosition="1" />
		<widget source="key_red" render="Label" position="24,628" size="150,30" font="Regular;18" foregroundColor="#00ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" halign="left" valign="center" />
		<widget source="key_green" render="Label" position="194,628" size="150,30" font="Regular;18" foregroundColor="#00ffffff" backgroundColor="#00000000" transparent="1" zPosition="1" halign="left" valign="center" />
	</screen>
	"""

	def __init__(self, session, totalimport):
		self.totalimport = totalimport
		if aelGlobals.RESOLUTION == "FHD":
			self.skin = self.skin.replace("/HD/", "/FHD/")
		Screen.__init__(self, session)
		self.aelinfobox = session.instantiateDialog(AELinfoBox)
		self.channellist = []
		self.deselect = True
		self["channelList"] = List()
		self["key_red"] = StaticText(_("Deselect all"))
		self["key_green"] = StaticText(_("Take over"))
		self['actions'] = ActionMap(["OkCancelActions",
									"ColorActions"], {"ok": self.keyOk,
													"red": self.keyRed,
													"green": self.keyGreen,
													"cancel": self.keyExit}, -1)
		self.onShown.append(self.onShownFinished)

	def onShownFinished(self):
		self.channellist = []
		for service in self.totalimport:
			self.channellist.append([service[1][1], True])
		self.updateChannellist()

	def updateChannellist(self):
		skinlist = []
		for channel in self.channellist:
			skinlist.append((channel[0], "✔" if channel[1] else "✘", int("0x0004c81b", 0) if channel[1] else int("0x00f50808", 0)))  # alternatively "✓", "✗"
		self["channelList"].updateList(skinlist)

	def keyOk(self):
		current = self["channelList"].getCurrentIndex()
		if self.channellist:
			self.channellist[current][1] = not self.channellist[current][1]
		self.updateChannellist()

	def keyRed(self):
		if self.channellist:
			if self.deselect:
				for index in range(len(self.channellist)):
					self.channellist[index][1] = False
				self["key_red"].setText(_("Select all"))
			else:
				for index in range(len(self.channellist)):
					self.channellist[index][1] = True
				self["key_red"].setText(_("Deselect all"))
		self.deselect = not self.deselect
		self.updateChannellist()

	def keyGreen(self):
		if self.channellist:
			if all(not x[1] for x in self.channellist):
				self.aelinfobox.showDialog(_("Please select at least one channel!"))
				self.updateChannellist()
			else:
				self.close((True, self.channellist))

	def keyExit(self):
		self.close((False, []))


class Editor(Screen, ConfigListScreen):
	ALLOW_SUSPEND = True
	skin = str(loadskin("AdvancedEventLibraryEditor.xml"))

	def __init__(self, session, service=None, parent=None, servicelist=None, eventname=None, args=0):
		Screen.__init__(self, session, parent=parent)
		self.session = session
		self.skinName = "Advanced-Event-Library-Editor"
		self.title = _("Advanced-Event-Library-Editor")
		self.ptr, self.ptr2, self.evt, self.orgName, self.fileName, self.e2eventId = "", "", "", "", "", ""
		self.isInit = False
		self.ImageCount = config.plugins.AdvancedEventLibrary.PreviewCount.value
#		self.currentService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.language = 'de'
		self.pSource = self.cSource = 1, 1
		self.db = aelHelper.getDB()
		if service:
			self.ptr = ((service.getPath().split('/')[-1]).rsplit('.', 1)[0]).replace('__', ' ').replace('_', ' ')
			self.fileName = service.getPath()
			if self.fileName.endswith("/"):
				name = self.fileName[:-1]
				self.ptr = aelHelper.removeExtension(str(name).split('/')[-1])
			else:
				info = eServiceCenter.getInstance().info(service)
				name = info.getName(service)
				if name:
					self.ptr = aelHelper.removeExtension(name)
				ptr = info.getEvent(service)
				if ptr:
					self.ptr2 = ptr.getEventName()
		elif eventname:
			self.ptr = eventname[0]
			self.ptr2 = eventname[0]
			self.evt = self.db.getliveTV(eventname[1], eventname[0])
			if self.evt:
				self.e2eventId = self.evt[0][0]
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
					aelHelper.writeLog(f"{ptr.getEventName()} {self.ptr}", DEFAULT_MODULE_NAME)
					self.evt = self.db.getliveTV(ptr.getEventId(), str(self.ptr))
					if self.evt:
						self.e2eventId = self.evt[0][0]
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
		self.ptr = aelHelper.removeExtension(aelHelper.convertDateInFileName(self.ptr))
		if self.ptr2:
			self.ptr2 = aelHelper.removeExtension(aelHelper.convertDateInFileName(self.ptr2))
			aelHelper.writeLog(f"found second name : {self.ptr2}", DEFAULT_MODULE_NAME)
		aelHelper.writeLog(f"search name : {self.ptr}", DEFAULT_MODULE_NAME)
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
							aelHelper.writeLog(f"Selection to move : {selection}", DEFAULT_MODULE_NAME)
							fileName = f"/tmp/{selection[5]}"  # NOSONAR
							aelHelper.createSingleThumbnail(fileName, selection[4])
							if int(getsize(fileName) / 1024.0) > config.plugins.AdvancedEventLibrary.MaxImageSize.value:
								aelHelper.reduceSigleImageSize(fileName, selection[4])
							else:
								copy(fileName, selection[4])
			elif self.activeList == 'cover':
				selection = self['cList'].l.getCurrentSelection()[0]
				if selection:
					if str(selection[0]) != "Keine Ergebnisse gefunden" and str(selection[0]) != _("load data, please wait..."):
						if self.cSource == 1:
							fileName = f"/tmp/{selection[5]}"  # NOSONAR
							aelHelper.writeLog(f"Selection to move : {selection}", DEFAULT_MODULE_NAME)
							aelHelper.createSingleThumbnail(fileName, selection[4])
							if int(getsize(fileName) / 1024.0) > config.plugins.AdvancedEventLibrary.MaxImageSize.value:
								aelHelper.reduceSigleImageSize(fileName, selection[4])
							else:
								copy(fileName, selection[4])
			elif "screenshot" in self.activeList.lower():
				fname = f"{aelHelper.removeExtension(aelHelper.removeExtension(self.ptr))}.jpg"
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
					aelHelper.createSingleThumbnail(fileName, join(f"{aelGlobals.HDDPATH}{typ}", fname))
					if int(getsize(fileName) / 1024.0) > int(config.plugins.AdvancedEventLibrary.MaxImageSize.value):
						aelHelper.reduceSigleImageSize(fileName, join(aelGlobals.HDDPATH + typ, fname))
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
		self['sList'].setList(aelHelper.getSearchResults(self.text, self.language))

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
				self.db.cleanDB(aelHelper.removeExtension(self.ptr))
				if self.e2eventId:
					self.db.cleanliveTVEntry(self.e2eventId)
				if self.cSource == 0:
					for file in self["cList"].getList():
						try:
							remove(file[0][3])
							remove(file[0][3].replace("/cover/", "/cover/thumbnails/"))
						except Exception as ex:
							aelHelper.writeLog(f"remove images : {ex}", DEFAULT_MODULE_NAME)
							continue
				if self.pSource == 0:
					for file in self["pList"].getList():
						try:
							remove(file[0][3])
							remove(file[0][3].replace("/poster/", "/poster/thumbnails/"))
						except Exception as ex:
							aelHelper.writeLog(f"remove images : {ex}", DEFAULT_MODULE_NAME)
							continue
				self.eventCountry.value = ""
				self.eventFSK.value = ""
				self.eventGenre.value = ""
				self.eventRating.value = ""
				self.eventYear.value = ""
				self.eventOverview = None
			elif ret[0] == _("Delete entry and set to blacklist"):
				self.db.cleanNadd2BlackList(aelHelper.removeExtension(self.ptr))
				if self.e2eventId:
					self.db.cleanliveTVEntry(self.e2eventId)
				if self.cSource == 0:
					for file in self["cList"].getList():
						try:
							remove(file[0][3])
							remove(file[0][3].replace("/cover/", "/cover/thumbnails/"))
						except Exception as ex:
							aelHelper.writeLog(f"remove images : {ex}", DEFAULT_MODULE_NAME)
							continue
				if self.pSource == 0:
					for file in self["pList"].getList():
						try:
							remove(file[0][3])
							remove(file[0][3].replace("/poster/", "/poster/thumbnails/"))
						except Exception as ex:
							aelHelper.writeLog(f"remove images : {ex}", DEFAULT_MODULE_NAME)
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
					aelHelper.writeLog(f"remove images : {ex}", DEFAULT_MODULE_NAME)
			elif ret[0] == _("Delete cover"):
				try:
					selection = self["cList"].l.getCurrentSelection()[0]
					if selection and isfile(selection[3]):
						remove(selection[3])
						remove(selection[3].replace("/cover/", "/cover/thumbnails/").replace("/preview/", "/preview/thumbnails/"))
						self.afterInit(False, True)
				except Exception as ex:
					aelHelper.writeLog(f"remove image : {ex}", DEFAULT_MODULE_NAME)
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
				callInThread(aelHelper.checkAllImages)
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
			aelHelper.writeLog(f"Menü : {ret[0]} - {self.ptr}", DEFAULT_MODULE_NAME)

	def languageCallBack(self, ret=None):
		if ret:
			aelHelper.writeLog(f"current language: {ret[0]}", DEFAULT_MODULE_NAME)
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
			self.evt, self.e2eventId = "", ""
		eventData = self.db.getEventInfo(aelHelper.removeExtension(self.ptr))
		if not eventData:
			eventData = self.db.getEventInfo(aelHelper.removeExtension(aelHelper.convertTitle(self.ptr)))
			if not eventData:
				eventData = self.db.getEventInfo(aelHelper.removeExtension(aelHelper.convertTitle2(self.ptr)))
		if not eventData:
			eventData = [aelHelper.removeExtension(self.ptr), self.ptr, "", "", "", "", ""]
		if not self.db.checkEventTitle(self.ptr) and self.ptr != "nothing found":
			self.db.addEventInfo(aelHelper.removeExtension(self.ptr), self.ptr, "", "", "", "", "", "", "", "")
		self.eventData = [aelHelper.removeExtension(self.ptr), self.ptr, "", "", "", "", ""]
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
				pName1 = f"{self.ptr}.jpg"
				pName2 = f"{aelHelper.convertTitle(self.ptr)}.jpg"
				pName3 = f"{aelHelper.convertTitle2(self.ptr)}.jpg"
				aelHelper.writeLog(f"1. possible picture name : {self.ptr} as {pName1}", DEFAULT_MODULE_NAME)
				if pName1 != pName2:
					aelHelper.writeLog(f"2. possible picture name : {aelHelper.convertTitle(self.ptr)} as {pName2}", DEFAULT_MODULE_NAME)
				if pName2 != pName3:
					aelHelper.writeLog(f"3. possible picture name : {aelHelper.convertTitle2(self.ptr)} as {pName3}", DEFAULT_MODULE_NAME)
				if isfile(join(aelGlobals.COVERPATH, pName1)):
					aelHelper.writeLog(f"found 1. possible cover : {pName1}", DEFAULT_MODULE_NAME)
				if isfile(join(aelGlobals.COVERPATH, pName2)) and pName1 != pName2:
					aelHelper.writeLog(f"found 2. possible cover : {pName2}", DEFAULT_MODULE_NAME)
				if isfile(join(aelGlobals.COVERPATH, pName3)) and pName2 != pName3:
					aelHelper.writeLog(f"found 3. possible cover : {pName3}", DEFAULT_MODULE_NAME)
				if isfile(join(aelGlobals.POSTERPATH, pName1)):
					aelHelper.writeLog(f"found 1. possible poster : {pName1}", DEFAULT_MODULE_NAME)
				if isfile(join(aelGlobals.POSTERPATH, pName2)) and pName1 != pName2:
					aelHelper.writeLog(f"found 2. possible poster : {pName2}", DEFAULT_MODULE_NAME)
				if isfile(join(aelGlobals.POSTERPATH, pName3)) and pName2 != pName3:
					aelHelper.writeLog(f"found 3. possible poster : {pName3}", DEFAULT_MODULE_NAME)
			self.coverList = []
			self.posterList = []
			waitList = []
			itm = [_("load data, please wait..."), None, None, None, None, None, None]
			waitList.append((itm,))
			if refreshCover:
				coverFiles = glob(join(aelGlobals.COVERPATH, f"{self.ptr.strip()}.jpg"))
				c2 = glob(join(aelGlobals.COVERPATH, f"{aelHelper.convertTitle(self.ptr).strip()}.jpg"))
				for file in c2:
					if file not in coverFiles:
						coverFiles.append(file)
				c2 = glob(join(aelGlobals.COVERPATH, f"{aelHelper.convertTitle2(self.ptr).strip()}.jpg"))
				for file in c2:
					if file not in coverFiles:
						coverFiles.append(file)
				del c2
				coverFile = join(aelGlobals.COVERPATH, self.ptr)
				if coverFile and coverFile not in coverFiles:
					coverFiles.append(coverFile)
				if self.orgName and self.orgName != self.ptr:
					coverFiles2 = glob(join(aelGlobals.COVERPATH, f"{self.orgName.strip()}.jpg"))
					for file in coverFiles2:
						if file not in coverFiles:
							coverFiles.append(file)
					p2 = glob(join(aelGlobals.COVERPATH, f"{aelHelper.convertTitle(self.orgName).strip()}.jpg"))
					for file in p2:
						if file not in coverFiles:
							coverFiles.append(file)
					p2 = glob(join(aelGlobals.COVERPATH, f"{aelHelper.convertTitle2(self.orgName).strip()}.jpg"))
					for file in p2:
						if file not in coverFiles:
							coverFiles.append(file)
					del p2
					coverFile = join(aelGlobals.COVERPATH, self.orgName)
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
				posterFiles = glob(join(aelGlobals.POSTERPATH, f"{self.ptr.strip()}.jpg"))
				p2 = glob(join(aelGlobals.POSTERPATH, f"{aelHelper.convertTitle(self.ptr).strip()}.jpg"))
				for file in p2:
					if file not in posterFiles:
						posterFiles.append(file)
				p2 = glob(join(aelGlobals.POSTERPATH, f"{aelHelper.convertTitle2(self.ptr).strip()}.jpg"))
				for file in p2:
					if file not in posterFiles:
						posterFiles.append(file)
				del p2
				posterFile = join(aelGlobals.POSTERPATH, self.ptr)
				if posterFile and posterFile not in posterFiles:
					posterFiles.append(posterFile)

				if self.orgName and self.orgName != self.ptr:
					posterFiles2 = glob(join(aelGlobals.POSTERPATH, f"{self.orgName.strip()}.jpg"))
					for file in posterFiles2:
						if file not in posterFiles:
							posterFiles.append(file)
					p2 = glob(join(aelGlobals.POSTERPATH, f"{aelHelper.convertTitle(self.orgName).strip()}.jpg"))
					for file in p2:
						if file not in posterFiles:
							posterFiles.append(file)
					p2 = glob(join(aelGlobals.POSTERPATH, f"{aelHelper.convertTitle2(self.orgName).strip()}.jpg"))
					for file in p2:
						if file not in posterFiles:
							posterFiles.append(file)
					del p2
					posterFile = join(aelGlobals.POSTERPATH, self.orgName)
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
		searchtext = f"{self.eventTitle.value} ({self.eventYear.value})" if self.eventYear.value and not ex else self.eventTitle.value
		if poster:
			if "Serie" in self.eventGenre.value:
				self["pList"].setList(aelHelper.getPictureList(searchtext, "Poster", self.ImageCount, self.language, " Serie"))  # Todo: searchtext oder self.eventData[0]?
			else:
				self["pList"].setList(aelHelper.getPictureList(searchtext, "Poster", self.ImageCount, self.language, " Film"))
		if cover:
			if "Serie" in self.eventGenre.value:
				self["cList"].setList(aelHelper.getPictureList(searchtext, "Cover", self.ImageCount, self.language, " Serie"))
			else:
				self["cList"].setList(aelHelper.getPictureList(searchtext, "Cover", self.ImageCount, self.language, " Film"))

	def showPreview(self):
		if self.ptr != "nothing found":
			self["poster"].hide()
			self["cover"].hide()
			if self.activeList == "poster":
				selection = self["pList"].l.getCurrentSelection()[0]
				if selection:
					size = self["poster"].instance.size()
					picloader = PicLoader(size.width(), size.height())
					if self.pSource == 1:
						self["poster"].instance.setPixmap(picloader.load("/tmp/" + selection[5]))
					else:
						self["poster"].instance.setPixmap(picloader.load(selection[3]))
					picloader.destroy()
					self["poster"].show()
			elif self.activeList == "cover":
				selection = self["cList"].l.getCurrentSelection()[0]
				if selection:
					size = self["cover"].instance.size()
					picloader = PicLoader(size.width(), size.height())
					if self.cSource == 1:
						self["cover"].instance.setPixmap(picloader.load("/tmp/" + selection[5]))
					else:
						self["cover"].instance.setPixmap(picloader.load(selection[3]))
					picloader.destroy()
					self["cover"].show()

	def key_red_handler(self):
		if self.ptr != "nothing found":
			if self.e2eventId:
				self.db.updateliveTVInfo(self.eventGenre.value, self.eventYear.value, self.eventRating.value, self.eventFSK.value, self.eventCountry.value, self.e2eventId)
			if self.db.checkEventTitle(self.eventData[0]):
				imdbId = trailer = "", ""  # not supported here
				self.db.updateEventInfo(self.eventGenre.value, self.eventYear.value, self.eventRating.value, self.eventFSK.value, self.eventCountry.value, "", "", imdbId, trailer, self.eventData[0])
				if config.plugins.AdvancedEventLibrary.CreateMetaData.value:
					if self.fileName and not isfile(self.fileName.replace(".ts", ".eit").replace(".mkv", ".eit").replace(".avi", ".eit").replace(".mpg", ".eit").replace(".mp4", ".eit")):
						if self.eventOverview:
							with open(self.fileName + ".txt", "w") as txt:
								txt.write(self.eventOverview)
					if self.fileName and not isfile(self.fileName + ".meta"):
						filedt = int(stat(self.fileName).st_mtime)
						with open(self.fileName + ".meta", "w") as txt:
							minfo = f"1:0:0:0:B:0:C00000:0:0:0:\n{self.eventTitle.value}\n"
							minfo += ", ".join(filter(None, [self.eventGenre.value, self.eventCountry.value, self.eventYear.value]))
							minfo += f"\n\n{filedt}\nAdvanced-Event-Library\n"
							txt.write(minfo)
		self.doClose()

	def key_green_handler(self):
		if self.activeList != "choiceBox":
			self["key_green"].setText("")
			self["key_yellow"] = StaticText(_("Activate poster selection"))
			self["key_blue"] = StaticText(_("Activate Cover selection"))
			self.activeList = "editor"

	def key_yellow_handler(self):
		if self.activeList != "choiceBox":
			self["key_green"].setText("Activate Editor")
			self["key_yellow"].setText("")
			self["key_blue"].setText("Activate Cover selection")
			self.activeList = "poster"
			self.showPreview()

	def key_blue_handler(self):
		if self.activeList != "choiceBox":
			self["key_green"].setText("Activate Editor")
			self["key_yellow"].setText("Activate poster selection")
			self["key_blue"].setText("")
			self.activeList = "cover"
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
		if self.activeList == "choiceBox":
			self["key_yellow"] = StaticText(_("Activate poster selection"))
			self["key_blue"] = StaticText(_("Activate Cover selection"))
			self["sList"].hide()
			self["config"].show()
			self.activeList = "editor"
		else:
			filelist = glob(join("/tmp/", "*.jpg"))
			for f in filelist:
				remove(f)
			aelHelper.clearMem("AEL-Editor")
			self.close()
