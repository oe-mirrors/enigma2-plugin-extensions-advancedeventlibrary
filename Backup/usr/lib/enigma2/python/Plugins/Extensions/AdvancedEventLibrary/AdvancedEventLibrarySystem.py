from base64 import b64decode
from datetime import datetime
from glob import glob
from json import dumps, loads
from os import statvfs, makedirs, walk, system, remove, stat
from os.path import isfile, getsize, exists, join, basename
from re import compile, IGNORECASE
from shutil import copy
from requests import get
from threading import Thread
from enigma import eTimer, ePicLoad, eServiceReference, eServiceCenter
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.config import config, ConfigText, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.ChannelSelection import service_types_tv
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.Standby import TryQuitMainloop
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.Directories import fileExists
from Tools.LoadPixmap import LoadPixmap

from . import AdvancedEventLibraryPrimeTime, AdvancedEventLibrarySerienStarts, AdvancedEventLibrarySimpleMovieWall, AdvancedEventLibraryChannelSelection, AdvancedEventLibraryLists, AdvancedEventLibraryMediaHub, AdvancedEventLibraryRecommendations, _  # for localized messages
from Tools import AdvancedEventLibrary as AEL

DEFAULT_MODULE_NAME = __name__.split(".")[-1]


def loadskin(filename):
	with open(join(AEL.aelGlobals.SKINPATH, filename), "r") as f:
		skin = f.read()
		f.close()
	return skin


class AELMenu(Screen):
	ALLOW_SUSPEND = True
	skin = str(loadskin("AdvancedEventLibraryMenu.xml"))

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.skinName = 'Advanced-Event-Library-Menu'
		self.title = f"Advanced-Event-Library Menüauswahl: (R{AEL.aelGlobals.CURRENTVERSION})"
		imgpath = join(AEL.aelGlobals.SHAREPATH, "AELImages/")
		self.menulist = [(_('Settingsn'), _('Making basic settings for AEL'), LoadPixmap(imgpath + 'settings.png'), 'setup'),
				   		(_('Editor'), _('Edit event information'), LoadPixmap(imgpath + 'keyboard.png'), 'editor'),
						('Prime-Time-Planer', 'zeigt nach Genres gegliederte Sendungen zur Prime-Time an', LoadPixmap(imgpath + 'primetime.png'), 'ptp'),
						('Serien-Starts-Planer', 'zeigt aktuelle Serien- und Staffelstarts an', LoadPixmap(imgpath + 'serien.png'), 'ssp'),
						('Favoriten-Planer', 'Deine Empfehlungen im TV', LoadPixmap(imgpath + 'favoriten.png'), 'fav'),
						('Simple-Movie-Wall', 'zeigt Aufnahmen im Wall-Format an', LoadPixmap(imgpath + 'movies.png'), 'smw'),
						('AEL-Channel-Selection', 'zeigt AEL Kanalübersicht an', LoadPixmap(imgpath + 'sender.png'), 'scs'),
						('AEL-Media-Hub', 'Aktuelles aus TV/Aufnahmen', LoadPixmap(imgpath + 'mediahub.png'), 'hub')]
		self["menulist"] = List(self.menulist, enableWrapAround=True)
		self["myActionMap"] = ActionMap(["AdvancedEventLibraryActions"],
		{
			"key_cancel": self.do_close,
			"key_red": self.do_close,
			"key_green": self.key_green_handler,
			"key_yellow": self.key_yellow_handler,
			"key_ok": self.key_ok_handler,
		}, -1)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Start scan..."))
		self["key_yellow"] = StaticText(_("Create Backup..."))
		self["info"] = StaticText("")
		self["status"] = StaticText("")
		self.refreshStatus = eTimer()
		self.refreshStatus.callback.append(self.getStatus)
		self.reload = eTimer()
		self.reload.callback.append(self.goReload)
		self.statistic = ""
		self.memInfo = ""
		self.onShow.append(self.afterInit)
		self.getStatus()

	def afterInit(self):
		self.db = AEL.getDB()
		confdir = join(AEL.aelGlobals.CONFIGPATH, "eventLibrary.db") if config.plugins.AdvancedEventLibrary.dbFolder.value == "Flash" else f"{config.plugins.AdvancedEventLibrary.Location.value}eventLibrary.db"
		if isfile(confdir):
			posterCount = self.db.parameter(AEL.PARAMETER_GET, 'posterCount', None, 0)
			posterSize = self.db.parameter(AEL.PARAMETER_GET, 'posterSize', None, 0)
			coverCount = self.db.parameter(AEL.PARAMETER_GET, 'coverCount', None, 0)
			previewCount = self.db.parameter(AEL.PARAMETER_GET, 'previewCount', None, 0)
			coverSize = self.db.parameter(AEL.PARAMETER_GET, 'coverSize', None, 0)
			previewSize = self.db.parameter(AEL.PARAMETER_GET, 'previewSize', None, 0)
			usedInodes = self.db.parameter(AEL.PARAMETER_GET, 'usedInodes', None, 0)
			lastposterCount = self.db.parameter(AEL.PARAMETER_GET, 'lastposterCount', None, 0)
			lastcoverCount = self.db.parameter(AEL.PARAMETER_GET, 'lastcoverCount', None, 0)
			lasteventInfoCount = self.db.parameter(AEL.PARAMETER_GET, 'lasteventInfoCount', None, 0)
			lasteventInfoCountSuccsess = self.db.parameter(AEL.PARAMETER_GET, 'lasteventInfoCountSuccsess', None, 0)
			lastpreviewImageCount = self.db.parameter(AEL.PARAMETER_GET, 'lastpreviewImageCount', None, 0)
			lastadditionalDataCount = self.db.parameter(AEL.PARAMETER_GET, 'lastadditionalDataCount', None, 0)
			lastadditionalDataCountBlacklist = self.db.parameter(AEL.PARAMETER_GET, 'lastadditionalDataCountSuccess', None, 0)
			lastadditionalDataCountSuccess = int(lastadditionalDataCount) - int(lastadditionalDataCountBlacklist)
			dbSize = getsize(confdir) / 1024.0
			titleCount = self.db.getTitleInfoCount()
			blackListCount = self.db.getblackListCount()
			percent = f"{100 * titleCount / (titleCount + blackListCount) if (titleCount + blackListCount) > 0 else 0} %"
			liveTVtitleCount = self.db.getliveTVCount()
			liveTVidtitleCount = self.db.getliveTVidCount()
			percentTV = f"{100 * liveTVidtitleCount / liveTVtitleCount if (liveTVidtitleCount + liveTVtitleCount) > 0 else 0} %"
			cpS = round(float(str(posterSize).replace('G', '')) * 1024.0, 2) if 'G' in str(posterSize) else posterSize
			ccS = round(float(str(coverSize).replace('G', '')) * 1024.0, 2) if 'G' in str(coverSize) else coverSize
			pcS = round(float(str(previewSize).replace('G', '')) * 1024.0, 2) if 'G' in str(previewSize) else previewSize
			percentlIC = f"{100 * int(lasteventInfoCountSuccsess) / int(lasteventInfoCount) if int(lasteventInfoCount) > 0 else 0} %"
			percentlaC = f"{100 * int(lastadditionalDataCountSuccess) / int(lastadditionalDataCount) if int(lastadditionalDataCount) > 0 else 0} %"
			trailers = self.db.getTrailerCount()
			size = int(float(str(cpS).replace('G', '').replace('M', '').replace('kB', '').replace('K', '')) + float(str(ccS).replace('G', '').replace('M', '').replace('kB', '').replace('K', '')) + float(str(pcS).replace('G', '').replace('M', '').replace('kB', '').replace('K', '')) + round(float(dbSize / 1024.0), 1))
			self.statistic = 'Statistik letzter Suchlauf:\nAnzahl Poster | Cover | Vorschaubilder:\t' + str(lastposterCount) + ' | ' + str(lastcoverCount) + ' | ' + str(lastpreviewImageCount) + '\ngesuchte Event-Informationen:\t' + str(lasteventInfoCount) + '\tgefunden:\t' + str(lasteventInfoCountSuccsess) + ' | ' + str(percentlIC) + '\ngesuchte Extradaten:     \t' + str(lastadditionalDataCount) + '\tgefunden:\t' + str(lastadditionalDataCountSuccess) + ' | ' + str(percentlaC) + str(self.getlastUpdateInfo(self.db))
			self.statistic += '\n\nStatistik gesamt:\nAnzahl Poster:\t' + str(posterCount) + '\tGröße:\t' + str(posterSize) + '\nAnzahl Cover:\t' + str(coverCount) + '\tGröße:\t' + str(coverSize) + '\nAnzahl Previews:\t' + str(previewCount) + '\tGröße:\t' + str(previewSize) + '\nAnzahl Trailer: \t' + str(trailers) + '\nDatenbankgröße: \t' + str(dbSize) + ' kB\nEinträge:\t' + str(titleCount) + ' | ' + str(blackListCount) + ' | ' + str(percent) + '\tExtradaten:\t' + str(liveTVtitleCount) + ' | ' + str(liveTVidtitleCount) + ' | ' + str(percentTV) + '\nSpeicherplatz:\t' + str(size) + ' / ' + str(int(config.plugins.AdvancedEventLibrary.MaxSize.value * 1024.0)) + ' MB' + '\tbenutzte Inodes\t' + str(usedInodes)
			self.memInfo = '\n\nSpeicherbelegung :\n' + str(self.getDiskInfo('/'))
			self.memInfo += str(self.getMemInfo('Mem'))
			self.memInfo += '\nMountpoints :\n' + self.getDiskInfo()
			self["info"].setText(self.statistic + self.memInfo)
		else:
			self["info"].setText('Es wurden noch keine Daten gefunden.')
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
		return "%s :\t%s\tFrei: %s\tBelegt: %s (%s%%)\n" % ('RAM', AEL.getSizeStr(result[0]), AEL.getSizeStr(result[2]), AEL.getSizeStr(result[1]), result[3])

	def getDiskInfo(self, path=None):
		def getMountPoints():
			mounts = []
			fd = open('/proc/mounts', 'r')
			for line in fd:
				l = line.split()
				if len(l) > 1:
					mounts.append(l[1])
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
			res += "%s :\t%s\tFrei: %s\tBelegt: %s (%s%%)\n" % (result[4], AEL.getSizeStr(result[0]), AEL.getSizeStr(result[2]), AEL.getSizeStr(result[1]), result[3])
		return res.replace('/ :', 'Flash :')

	def getlastUpdateInfo(self, db):
		lastUpdateStart = self.convertTimestamp(db.parameter(AEL.PARAMETER_GET, 'laststart', None, 0))
		lastUpdateDuration = self.convertDuration(float(db.parameter(AEL.PARAMETER_GET, 'laststop', None, 0)) - float(db.parameter(AEL.PARAMETER_GET, 'laststart', None, 0)) - 3600)
		return '\nausgeführt am:\t' + str(lastUpdateStart) + '\tDauer:\t' + str(lastUpdateDuration)

	def convertTimestamp(self, val):
		value = datetime.fromtimestamp(float(val))
		return value.strftime('%d.%m. %H:%M')

	def convertDuration(self, val):
		value = datetime.fromtimestamp(float(val))
		return value.strftime('%H:%M:%S')

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
		self["status"].setText('starte Suchlauf...')
		self.createDirs(config.plugins.AdvancedEventLibrary.Location.value)
		AEL.startUpdate()

	def key_yellow_handler(self):
		thread = Thread(target=AEL.createBackup, args=())
		thread.start()

	def createDirs(self, path):
		if not exists(path):
			makedirs(path)
		if not exists(path + 'poster/'):
			makedirs(path + 'poster/')
		if not exists(path + 'cover/'):
			makedirs(path + 'cover/')
		if not exists(path + 'preview/'):
			makedirs(path + 'preview/')

	def getStatus(self):
		if AEL.aelGlobals.STATUS:
			self["status"].setText(AEL.aelGlobals.STATUS)
		else:
			self["status"].setText(_("No search is currently running."))
		self.memInfo = '\n\nSpeicherbelegung :\n' + str(self.getDiskInfo('/'))
		self.memInfo += str(self.getMemInfo('Mem'))
		self.memInfo += '\nMountpoints :\n' + self.getDiskInfo()
		self["info"].setText(self.statistic + self.memInfo)
		self.refreshStatus.start(3000, True)

	def do_close(self):
		if self.refreshStatus.isActive():
			self.refreshStatus.stop()
		self.close()

	def open_serienstarts(self):
		self.viewType = config.plugins.AdvancedEventLibrary.ViewType.value
		self.screenType = 0
		self.session.openWithCallback(self.goRestart, AdvancedEventLibrarySerienStarts.AdvancedEventLibraryPlanerScreens, self.viewType)

	def open_primetime(self):
		self.viewType = config.plugins.AdvancedEventLibrary.ViewType.value
		self.screenType = 1
		self.session.openWithCallback(self.goRestart, AdvancedEventLibraryPrimeTime.AdvancedEventLibraryPlanerScreens, self.viewType)

	def open_moviewall(self):
		while AEL.aelGlobals.saving:
			pass
		self.viewType = config.plugins.AdvancedEventLibrary.ViewType.value
		self.screenType = 2
		self.session.openWithCallback(self.goRestart, AdvancedEventLibrarySimpleMovieWall.AdvancedEventLibrarySimpleMovieWall, self.viewType)

	def open_favourites(self):  # reload_module(AdvancedEventLibraryRecommendations)
		self.viewType = config.plugins.AdvancedEventLibrary.ViewType.value
		self.screenType = 3
		self.session.openWithCallback(self.goRestart, AdvancedEventLibraryRecommendations.AdvancedEventLibraryPlanerScreens, self.viewType)

	def open_channelSelection(self):
		self.session.open(AdvancedEventLibraryChannelSelection.AdvancedEventLibraryChannelSelection)

	def open_mediaHub(self):
		self.session.open(AdvancedEventLibraryMediaHub.AdvancedEventLibraryMediaHub)

	def main(self):
		self.session.open(AdvancedEventLibrarySetup)

	def editor(self):
		self.session.open(Editor)

	def goRestart(self, ret=None):
		if ret:
			AEL.aelGlobals.write_log('return ' + str(ret), DEFAULT_MODULE_NAME)
			config.plugins.AdvancedEventLibrary.ViewType.value = ret
			config.plugins.AdvancedEventLibrary.ViewType.save()
		if self.viewType != config.plugins.AdvancedEventLibrary.ViewType.value:
			self.reload.start(50, True)
		else:
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


#		LocationBox.__init__(
#			self,
#			session,
#			text=_("What do you want to set as the default movie location?"),
#			# filename="",
#			currDir=config.usage.default_path.value,
#			bookmarks=config.movielist.videodirs,
#			windowTitle=_("Select Playback Location"),
#			# minFree=None,
#			autoAdd=True,
#			editDir=True,
#			inhibitDirs=DEFAULT_INHIBIT_DIRECTORIES,
#			# inhibitMounts=None
#		)


####################################################################################
class AdvancedEventLibrarySetup(Setup):
	ALLOW_SUSPEND = True  # skin = str(loadskin("AdvancedEventLibrarySetup.xml"))

	def __init__(self, session):
		self.session = session
		Setup.__init__(self, session, "Advanced-Event-Library-Setup", plugin="Extensions/AdvancedEventLibrary", PluginLanguageDomain="AdvancedEventLibrary")
#		self.title = "Advanced-Event-Library-Setup"
#		bestmount = defaultRecordingLocation().replace('movie/', '') + 'AdvancedEventLibrary/'
#		config.plugins.AdvancedEventLibrary = ConfigSubsection()
#		self.mypath = config.plugins.AdvancedEventLibrary.Location = ConfigText(default=bestmount)
#		self.backuppath = config.plugins.AdvancedEventLibrary.Backup = ConfigText(default="/media/hdd/AdvancedEventLibraryBackup/")
#		self.maxSize = config.plugins.AdvancedEventLibrary.MaxSize = ConfigInteger(default=1, limits=(1, 100))
#		self.previewCount = config.plugins.AdvancedEventLibrary.PreviewCount = ConfigInteger(default=20, limits=(1, 50))
#		self.showinEPG = config.plugins.AdvancedEventLibrary.ShowInEPG = ConfigYesNo(default=False)
#		self.useAELEPGLists = config.plugins.AdvancedEventLibrary.UseAELEPGLists = ConfigYesNo(default=False)
#		# self.useAELIS = config.plugins.AdvancedEventLibrary.UseAELIS = ConfigYesNo(default=True)
#		self.useAELMW = config.plugins.AdvancedEventLibrary.UseAELMovieWall = ConfigYesNo(default=False)
#		self.addlog = config.plugins.AdvancedEventLibrary.Log = ConfigYesNo(default=False)
#NEW		# self.usePreviewImages = config.plugins.AdvancedEventLibrary.UsePreviewImages = ConfigYesNo(default=True)
#		self.coverquality = config.plugins.AdvancedEventLibrary.coverQuality = ConfigSelection(default="w1280", choices=[("w300", "300x169"), ("w780", "780x439"), ("w1280", "1280x720"), ("w1920", "1920x1080")])
#		self.posterquality = config.plugins.AdvancedEventLibrary.posterQuality = ConfigSelection(default="w780", choices=[("w185", "185x280"), ("w342", "342x513"), ("w500", "500x750"), ("w780", "780x1170")])
#		self.dbfolder = config.plugins.AdvancedEventLibrary.dbFolder = ConfigSelection(default="Datenverzeichnis", choices=["Datenverzeichnis", "Flash"])
#		self.maxImageSize = config.plugins.AdvancedEventLibrary.MaxImageSize = ConfigSelection(default="200", choices=[("100", "100kB"), ("150", "150kB"), ("200", "200kB"), ("300", "300kB"), ("400", "400kB"), ("500", "500kB"), ("750", "750kB"), ("1024", "1024kB"), ("1000000", "unbegrenzt")])
#		self.maxCompression = config.plugins.AdvancedEventLibrary.MaxCompression = ConfigInteger(default=50, limits=(10, 90))
#		self.searchPlaces = config.plugins.AdvancedEventLibrary.searchPlaces = ConfigText(default='')
#		self.tmdbKey = config.plugins.AdvancedEventLibrary.tmdbKey = ConfigText(default='intern')
#		self.tvdbV4Key = config.plugins.AdvancedEventLibrary.tvdbV4Key = ConfigText(default='unbenutzt')
#		self.tvdbKey = config.plugins.AdvancedEventLibrary.tvdbKey = ConfigText(default='intern')
#		self.omdbKey = config.plugins.AdvancedEventLibrary.omdbKey = ConfigText(default='intern')
#		self.searchfor = config.plugins.AdvancedEventLibrary.SearchFor = ConfigSelection(default="Extradaten und Bilder", choices=["Extradaten und Bilder", "nur Extradaten"])
#		self.delPreviewImages = config.plugins.AdvancedEventLibrary.DelPreviewImages = ConfigYesNo(default=True)
#		self.closeMenu = config.plugins.AdvancedEventLibrary.CloseMenu = ConfigYesNo(default=True)
#		self.refreshMW = config.plugins.AdvancedEventLibrary.RefreshMovieWall = ConfigYesNo(default=True)
#		self.refreshMWAtStop = config.plugins.AdvancedEventLibrary.RefreshMovieWallAtStop = ConfigYesNo(default=True)
#		self.refreshMWAtStart = config.plugins.AdvancedEventLibrary.RefreshMovieWallAtStart = ConfigYesNo(default=False)
#		self.ignoreSortSeriesdetection = config.plugins.AdvancedEventLibrary.ignoreSortSeriesdetection = ConfigYesNo(default=False)
#		self.searchLinks = config.plugins.AdvancedEventLibrary.SearchLinks = ConfigYesNo(default=True)
#		self.maxUsedInodes = config.plugins.AdvancedEventLibrary.MaxUsedInodes = ConfigInteger(default=90, limits=(20, 95))
#		self.createMetaData = config.plugins.AdvancedEventLibrary.CreateMetaData = ConfigYesNo(default=False)
#		self.updateAELMovieWall = config.plugins.AdvancedEventLibrary.UpdateAELMovieWall = ConfigYesNo(default=True)
		self.searchOptions = {}
		if config.plugins.AdvancedEventLibrary.searchPlaces.value != '':
			self.searchOptions = eval(config.plugins.AdvancedEventLibrary.searchPlaces.value)
#		if self.searchOptions:
#			self.vtidb = ConfigYesNo(default=self.searchOptions.get("VTiDB", False))
#			self.usePictures = ConfigYesNo(default=self.searchOptions.get("Pictures", True))
#		else:
#			self.vtidb = ConfigYesNo(default=True)
#			self.usePictures = ConfigYesNo(default=True)

		#inhibitDirs = ["/bin", "/boot", "/dev", "/home", "/lib", "/config", "/proc", "/sbin", "/share", "/sys", "/tmp", "/usr", "/var", "/media/VMC", "/media/VMC5", "/.cache", "/.local", "/autofs", "/mnt", "/run"]
		#for root, directories, files in walk("/etc"):
		#	if str(root) != "/etc" and str(root) != "/etc/enigma2":
		#		inhibitDirs.append(str(root))
		#self["myFileList"] = FileList("/media/hdd/", showDirectories=True, showFiles=False, inhibitDirs=inhibitDirs)
		#self["myFileList"].hide()
		self.myFileListActive = False
#		ConfigListScreen.__init__(self, self.configlist, session=self.session, on_change=self.changedEntry)
		self["entryActions"] = HelpableActionMap(self, ["ColorActions"],
														{
														"green": (self.do_close, _("Save")),
														"yellow": (self.key_yellow_handler, _("TVS-Setup"))
														}, prio=0, description=_("Advanced-Event-Library-Setup"))

	def key_ok_handler(self):
		return
		try:
			cur = self['config'].getCurrent()
			if cur:
				if (cur[0] == 'Daten-Verzeichnis (OK drücken)' or cur[0] == 'Backup-Verzeichnis (OK drücken)') and not self.myFileListActive:
					self["key_blue"].setText("Übernehmen")
					self.myFileListActive = True
					self["myFileList"].show()
				elif (cur[0] == 'Daten-Verzeichnis (OK drücken)' or cur[0] == 'Backup-Verzeichnis (OK drücken)') and self.myFileListActive:
					if self["myFileList"].canDescent():
						self["myFileList"].descent()
					self.updatePath()
				self.buildConfigList()
		except Exception as ex:
			AEL.aelGlobals.write_log("Setup - keyok : " + str(ex), DEFAULT_MODULE_NAME)

	def updatePath(self, confirmed=False, cur=""):
		return
		if self["myFileList"].getSelection():
			cur = self['config'].getCurrent()
			path = self["myFileList"].getSelection()[0]
			path = str(path).replace('poster/', '').replace('cover/', '')
			if not path.endswith('/'):
				path = path + '/'
			if cur[0] == 'Daten-Verzeichnis (OK drücken)':
				if not path.endswith('AdvancedEventLibrary/'):
					path = path + 'AdvancedEventLibrary/'
			if cur[0] == 'Backup-Verzeichnis (OK drücken)':
				if not path.endswith('AdvancedEventLibraryBackup/'):
					path = path + 'AdvancedEventLibraryBackup/'
			if confirmed:
				if cur[0] == 'Daten-Verzeichnis (OK drücken)':
					config.plugins.AdvancedEventLibrary.Location.value = path
				elif cur[0] == 'Backup-Verzeichnis (OK drücken)':
					self.backuppath.value = path
				self.createDirs(path)
				cur = self["config"].getCurrent()
				#self["config"].updateConfigListView(cur)
				self.buildConfigList()

	def createDirs(self, path):
		return
		if not exists(path):
			makedirs(path)
		if not exists(path + 'poster/'):
			makedirs(path + 'poster/')
		if not exists(path + 'cover/'):
			makedirs(path + 'cover/')

#	def key_up_handler(self):
#		if self.myFileListActive:
#			self["myFileList"].up()
#			self.updatePath()
#		else:
#			self["config"].instance.moveSelection(self["config"].instance.moveUp)

#	def key_down_handler(self):
#		if self.myFileListActive:
#			self["myFileList"].down()
#			self.updatePath()
#		else:
#			self["config"].instance.moveSelection(self["config"].instance.moveDown)

#	def key_blue_handler(self):
#		if self.myFileListActive:
#			self["key_blue"].setText("")
#			self["myFileList"].hide()
#			self.myFileListActive = False
#			self.updatePath(True)
#			self.buildConfigList()

	def key_yellow_handler(self):
		self.session.openWithCallback(self.return_from_setup, TVSSetup)

	def return_from_setup(self):
		pass

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
#			self.configlist.append(getConfigListEntry("suche in VTiDB", self.vtidb))

#			mask = (eServiceReference.isMarker | eServiceReference.isDirectory)
#			root = eServiceReference(str(service_types_tv + ' FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
#			serviceHandler = eServiceCenter.getInstance()
#			tvbouquets = serviceHandler.list(root).getContent("SN", True)
#			for bouquet in tvbouquets:
#				bpath = ConfigYesNo(default=self.searchOptions.get(bouquet[1], True))
#				self.configlist.append(getConfigListEntry("suche in Bouquet " + str(bouquet[1]), bpath))
#
#			recordPaths = config.movielist.videodirs.value
#			if recordPaths:
#				for recdir in recordPaths:
#					if isdir(recdir):
#						rpath = ConfigYesNo(default=self.searchOptions.get(recdir, False))
#						subpaths = ConfigYesNo(default=self.searchOptions.get('subpaths_' + recdir, False))
#
#						self.configlist.append(getConfigListEntry("suche in " + str(recdir), rpath))
#						self.configlist.append(getConfigListEntry("suche in Unterverzeichnissen von " + str(recdir), subpaths))
#
#		except Exception as ex:
#			AEL.aelGlobals.write_log("Error in buildConfigList : " + str(ex),DEFAULT_MODULE_NAME)

	def changedEntry(self):
		return
		cur = self["config"].getCurrent()
		if cur and cur is not None and "suche in" not in cur[0]:
			self.buildConfigList()
		self["config"].setList(self.configlist)
		if cur and cur is not None:
			if cur[0] == "Daten-Verzeichnis (OK drücken)":
				if "AdvancedEventLibrary/" not in cur[1].value:
					cur[1].value = cur[1].value + "AdvancedEventLibrary/"
					self.buildConfigList()
					self["config"].setList(self.configlist)
			if cur[0] == "Backup-Verzeichnis (OK drücken)":
				if "AdvancedEventLibraryBackup/" not in cur[1].value:
					cur[1].value = cur[1].value + "AdvancedEventLibraryBackup/"
					self.buildConfigList()
					self["config"].setList(self.configlist)
			#self["config"].updateConfigListView(cur)

	def do_close(self):
		restartbox = self.session.openWithCallback(self.restartGUI, MessageBox, _("GUI needs a restart to apply new configuration.\nDo you want to restart the GUI now ?"), MessageBox.TYPE_YESNO)
		restartbox.setTitle(_("GUI needs a restart."))

	def restartGUI(self, answer):
		if answer is True:
			for x in self["config"].list:
				if len(x) > 1:
					if "suche" not in x[0] and "Einstellungen" not in x[0] and x[0]:
						AEL.aelGlobals.write_log('save : ' + str(x[0]) + ' - ' + str(x[1].value), DEFAULT_MODULE_NAME)
						x[1].save()
					else:
						if 'suche in Unterverzeichnissen von ' in str(x[0]):
							for root, directories, files in walk(str(x[0]).replace('suche in Unterverzeichnissen von ', '')):
								if str(x[0]).replace('suche in Unterverzeichnissen von ', '') != str(root):
									self.searchOptions[str(root)] = x[1].value
							self.searchOptions[x[0].replace("suche in Unterverzeichnissen von ", "subpaths_")] = x[1].value
						else:
							self.searchOptions[x[0].replace("suche vorhandene Bilder in Aufnahmeverzeichnissen", "Pictures").replace("suche in Bouquet ", "").replace("suche in ", "")] = x[1].value
			config.plugins.AdvancedEventLibrary.searchPlaces.value = str(self.searchOptions)
			config.plugins.AdvancedEventLibrary.searchPlaces.save()
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close()

####################################################################################


class TVSSetup(Screen, ConfigListScreen):  # TODO: Erstmal so belassen
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.skinName = ["TV Spielfilm-Setup", "Setup"]
		self.title = "TV Spielfilm-Setup"
		self.cur = None
		self.setup_title = "TV Spielfilm-Setup"
		self["title"] = StaticText(self.title)
		self["footnote"] = StaticText("")
		self["description"] = Label("")
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Speichern"))
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
		tvsref = {}
		if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/tvsreflist.data'):
			self.tvsref = self.load_json('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/tvsreflist.data')
		for bouquet in tvbouquets:
			root = eServiceReference(str(bouquet[0]))
			serviceHandler = eServiceCenter.getInstance()
			ret = serviceHandler.list(root).getContent("SN", True)
			doIt = False
			if str(bouquet[1]) in sPDict:
				if sPDict[str(bouquet[1])]:
					doIt = True
			else:
				doIt = True
			if doIt:
				for (serviceref, servicename) in ret:
					playable = not (eServiceReference(serviceref).flags & mask)
					if playable and "p%3a" not in serviceref and "<n/a>" not in servicename and servicename != "." and not serviceref.startswith('4097'):
						if servicename not in self.senderlist:
							self.senderlist.append(servicename)
						self.senderdict[serviceref] = servicename
		lists = self.get_tvsRefList()
		self.tvsRefList = lists[0]
		self.tvsKeys = lists[1]
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
		self.cur = self['config'].getCurrent()
		if self.cur:
			list = []
			for sender in self.tvsKeys:
				for k, v in self.tvsRefList.items():
					if str(sender) == str(k):
						itm = (k, v)
						list.append(itm)
						break
			list.insert(0, (_("unused"), ""))
			choices, idx = (list, 0)
			keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
			self.session.openWithCallback(self.menuCallBack, ChoiceBox, title='Referenz auswählen', keys=keys, list=choices, selection=idx)

	def menuCallBack(self, ret=None):
		if ret and self.cur:
			self.cur[1].value = ret[1]

	def load_json(self, filename):
		f = open(filename, 'r')
		data = f.read().replace('null', '""')
		f.close()
		return eval(data)

	def save_json(self, data, filename):
		DataFile = open(filename, 'w')
		DataFile.write(dumps(data, indent=4, sort_keys=False))
		DataFile.close()

	def get_tvsRefList(self):
		refList = {}
		keyList = []
		url = 'https://live.tvspielfilm.de/static/content/channel-list/livetv'
		results = loads(get(url, timeout=4).text)
		if results:
			for service in results:
				if "id" in service and "name" in service:
					refList[str(service["name"])] = str(service["id"])
			for k, v in refList.items():
				keyList.append(k)
			keyList.sort()
		return (refList, keyList)

	def buildConfigList(self):
		if self.configlist:
			del self.configlist[:]
		if self.tvsRefList:
			for sender in sorted(self.senderlist):
				for k, v in self.senderdict.items():
					if str(v) == str(sender):
						entry = ConfigText(default=self.tvsref.get(k, ""))
						self.configlist.append(getConfigListEntry(sender, entry))
						break

	def changedEntry(self):
#		self.buildConfigList()
		cur = self["config"].getCurrent()
		self["config"].setList(self.configlist)
		#if cur and cur is not None:
		#	self["config"].updateConfigListView(cur)

	def do_close(self):
		restartbox = self.session.openWithCallback(self.restartGUI, MessageBox, _("Sollen die Einstellungen gespeichert werden ?"), MessageBox.TYPE_YESNO)
		restartbox.setTitle(_("Einstellungen speichern"))

	def restartGUI(self, answer):
		if answer is True:
			ref = {}
			for x in self["config"].list:
				if x[1].value:
					for k, v in self.senderdict.items():
						if str(v) == str(x[0]):
							ref[k] = x[1].value
							break
			self.save_json(ref, '/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/tvsreflist.data')
			self.close()
		else:
			self.close()

####################################################################################


class Editor(Screen, ConfigListScreen):
	ALLOW_SUSPEND = True
	skin = str(loadskin("AdvancedEventLibraryEditor.xml"))

	def __init__(self, session, service=None, parent=None, servicelist=None, eventname=None, args=0):
		Screen.__init__(self, session, parent=parent)
		self.session = session
		self.skinName = 'Advanced-Event-Library-Editor'
		self.title = "Advanced-Event-Library-Editor"
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
		self.db = AEL.getDB()
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
					AEL.aelGlobals.write_log('ptr.getEventName() ' + str(self.ptr), DEFAULT_MODULE_NAME)
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
		self.ptr = AEL.convertSearchName(AEL.convertDateInFileName(self.ptr))
		if self.ptr2:
			self.ptr2 = AEL.convertSearchName(AEL.convertDateInFileName(self.ptr2))
			AEL.aelGlobals.write_log('found second name : ' + str(self.ptr2), DEFAULT_MODULE_NAME)
		AEL.aelGlobals.write_log('search name : ' + str(self.ptr), DEFAULT_MODULE_NAME)
		self["key_red"] = StaticText(_("Activate"))
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText(_("Activate poster selection"))
		self["key_blue"] = StaticText(_("Activate Cover selection"))
		self.activeList = 'editor'
		self.jahr = ''
		self["pList"] = AdvancedEventLibraryLists.ImageList()
		self["cList"] = AdvancedEventLibraryLists.ImageList()
		self["sList"] = AdvancedEventLibraryLists.SearchResultsList()
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
		self.onShow.append(self.checkDoupleNames)
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
				thread = Thread(target=self.searchPics, args=())
				thread.start()
			elif self.activeList == 'editor':
				if self['config'].getCurrent()[0] == 'Event Name (suche mit OK)':
					self.session.openWithCallback(self.searchEvents, VirtualKeyBoard, title="Eventsuche...", text=self['config'].getCurrent()[1].value)
				else:
					self.session.openWithCallback(self.donothing, VirtualKeyBoard, title="Daten bearbeiten...", text=self['config'].getCurrent()[1].value)
			elif self.activeList == 'poster':
				selection = self['pList'].l.getCurrentSelection()[0]
				if selection:
					if str(selection[0]) != "Keine Ergebnisse gefunden" and str(selection[0]) != "lade Daten, bitte warten...":
						if self.pSource == 1:
							AEL.aelGlobals.write_log('Selection to move : ' + str(selection), DEFAULT_MODULE_NAME)
							AEL.createSingleThumbnail('/tmp/' + selection[5], selection[4])
							if int(getsize('/tmp/' + selection[5]) / 1024.0) > int(config.plugins.AdvancedEventLibrary.MaxImageSize.value):
								AEL.reduceSigleImageSize('/tmp/' + selection[5], selection[4])
							else:
								copy('/tmp/' + selection[5], selection[4])
			elif self.activeList == 'cover':
				selection = self['cList'].l.getCurrentSelection()[0]
				if selection:
					if str(selection[0]) != "Keine Ergebnisse gefunden" and str(selection[0]) != "lade Daten, bitte warten...":
						if self.cSource == 1:
							AEL.aelGlobals.write_log('Selection to move : ' + str(selection), DEFAULT_MODULE_NAME)
							AEL.createSingleThumbnail('/tmp/' + selection[5], selection[4])
							if int(getsize('/tmp/' + selection[5]) / 1024.0) > int(config.plugins.AdvancedEventLibrary.MaxImageSize.value):
								AEL.reduceSigleImageSize('/tmp/' + selection[5], selection[4])
							else:
								copy('/tmp/' + selection[5], selection[4])
			elif "screenshot" in self.activeList:
				fname = AEL.convertSearchName(AEL.convert2base64(self.removeExtension(self.ptr))) + '.jpg'
				cmd = "grab -v -j 100 /tmp/" + fname
				ret = system(cmd)
				if ret == 0:
					if "poster" in self.activeList:
						from PIL import Image
						im = Image.open("/tmp/" + fname)
						region = im.crop((640, 0, 1280, 1080))
						region.save("/tmp/" + fname)
						typ = "poster/"
					else:
						typ = "cover/"
					AEL.createSingleThumbnail('/tmp/' + fname, join(AEL.getPictureDir() + typ, fname))
					if int(getsize('/tmp/' + fname) / 1024.0) > int(config.plugins.AdvancedEventLibrary.MaxImageSize.value):
						AEL.reduceSigleImageSize('/tmp/' + fname, join(AEL.getPictureDir() + typ, fname))
					else:
						copy('/tmp/' + fname, join(AEL.getPictureDir() + typ, fname))
					self.session.open(MessageBox, 'AEL - Screenshot\nNeues Bild für ' + str(self.ptr) + ' erfolgreich erstellt.', MessageBox.TYPE_INFO, timeout=10)
				else:
					self.session.open(MessageBox, 'AEL - Screenshot\nBild ' + str(self.ptr) + ' konnte nicht erstellt werden.', MessageBox.TYPE_INFO, timeout=10)
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
			itm = ["lade Daten, bitte warten...", None, None, None, None, None, None]
			waitList.append((itm,))
			self['sList'].setList(waitList)
			self["key_yellow"].setText("")
			self["key_blue"].setText("")
			self["cover"].hide()
			self["poster"].hide()
			self['sList'].show()
			self.activeList = 'choiceBox'
			self.text = text
			thread = Thread(target=self.searchAll, args=())
			thread.start()

	def searchAll(self):
		self['sList'].setList(AEL.get_searchResults(self.text, self.language))

	def key_menu_handler(self):
		if self.ptr != 'nothing found':
			if self.cSource == 0 and self.activeList == 'cover' and "/etc" not in str(config.plugins.AdvancedEventLibrary.Location.value):
				choices, idx = ([('Sprachauswahl',), ('lade Cover',), ('erzeuge Screenshot',), ('Eintrag löschen',), ('Eintrag löschen und auf Blacklist setzen',), ('Cover löschen',), ('Thumbnails löschen',), ('BlackList löschen',), ('Bilder überprüfen',)], 0)
			elif self.pSource == 0 and self.activeList == 'poster' and "/etc" not in str(config.plugins.AdvancedEventLibrary.Location.value):
				choices, idx = ([('Sprachauswahl',), ('lade Poster',), ('erzeuge Screenshot',), ('Eintrag löschen',), ('Eintrag löschen und auf Blacklist setzen',), ('Poster löschen',), ('Thumbnails löschen',), ('BlackList löschen',), ('Bilder überprüfen',)], 0)
			else:
				choices, idx = ([('Sprachauswahl',), ('erzeuge Poster aus Screenshot',), ('erzeuge Cover aus Screenshot',), ('Eintrag löschen',), ('Eintrag löschen und auf Blacklist setzen',), ('Thumbnails löschen',), ('BlackList löschen',), ('Bilder überprüfen',)], 0)
			keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
			self.session.openWithCallback(self.menuCallBack, ChoiceBox, title='Bearbeiten', keys=keys, list=choices, selection=idx)

	def menuCallBack(self, ret=None):
		if ret:
			if ret[0] == 'Sprachauswahl':
				choices, idx = ([('Deutsch', 'de'), ('Englisch', 'en'), ('Französisch', 'fr'), ('Spanisch', 'es'), ('Italienisch', 'it'), ('Alle Sprachen', '')], 0)
				keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
				self.session.openWithCallback(self.languageCallBack, ChoiceBox, title='benutzte Sprache für Suche', keys=keys, list=choices, selection=idx)
			if ret[0] == 'Eintrag löschen':
				self.db.cleanDB(AEL.convertSearchName(AEL.convert2base64(self.ptr)))
				if self.eid is not None:
					self.db.cleanliveTVEntry(self.eid)
				if self.cSource == 0:
					for file in self['cList'].getList():
						try:
							remove(file[0][3])
							remove(file[0][3].replace('/cover/', '/cover/thumbnails/'))
						except Exception as ex:
							AEL.aelGlobals.write_log('remove images : ' + str(ex), DEFAULT_MODULE_NAME)
							continue
				if self.pSource == 0:
					for file in self['pList'].getList():
						try:
							remove(file[0][3])
							remove(file[0][3].replace('/poster/', '/poster/thumbnails/'))
						except Exception as ex:
							AEL.aelGlobals.write_log('remove images : ' + str(ex), DEFAULT_MODULE_NAME)
							continue
				self.eventCountry.value = ''
				self.eventFSK.value = ''
				self.eventGenre.value = ''
				self.eventRating.value = ''
				self.eventYear.value = ''
				self.eventOverview = None
			elif ret[0] == 'Eintrag löschen und auf Blacklist setzen':
				self.db.cleanNadd2BlackList(AEL.convertSearchName(AEL.convert2base64(self.ptr)))
				if self.eid is not None:
					self.db.cleanliveTVEntry(self.eid)
				if self.cSource == 0:
					for file in self['cList'].getList():
						try:
							remove(file[0][3])
							remove(file[0][3].replace('/cover/', '/cover/thumbnails/'))
						except Exception as ex:
							AEL.aelGlobals.write_log('remove images : ' + str(ex), DEFAULT_MODULE_NAME)
							continue
				if self.pSource == 0:
					for file in self['pList'].getList():
						try:
							remove(file[0][3])
							remove(file[0][3].replace('/poster/', '/poster/thumbnails/'))
						except Exception as ex:
							AEL.aelGlobals.write_log('remove images : ' + str(ex), DEFAULT_MODULE_NAME)
							continue
				self.eventCountry.value = ''
				self.eventFSK.value = ''
				self.eventGenre.value = ''
				self.eventRating.value = ''
				self.eventYear.value = ''
				self.eventOverview = None
			elif ret[0] == 'Poster löschen':
				try:
					selection = self['pList'].l.getCurrentSelection()[0]
					if selection and isfile(selection[3]):
						remove(selection[3])
						remove(selection[3].replace('/poster/', '/poster/thumbnails/'))
						self.afterInit(True, False)
				except Exception as ex:
					AEL.aelGlobals.write_log('remove image : ' + str(ex), DEFAULT_MODULE_NAME)
			elif ret[0] == 'Cover löschen':
				try:
					selection = self['cList'].l.getCurrentSelection()[0]
					if selection and isfile(selection[3]):
						remove(selection[3])
						remove(selection[3].replace('/cover/', '/cover/thumbnails/').replace('/preview/', '/preview/thumbnails/'))
						self.afterInit(False, True)
				except Exception as ex:
					AEL.aelGlobals.write_log('remove image : ' + str(ex), DEFAULT_MODULE_NAME)
			elif ret[0] == 'BlackList löschen':
				self.db.cleanblackList()
			elif ret[0] == 'Thumbnails löschen':
				tmp = config.plugins.AdvancedEventLibrary.Location.value + 'cover/thumbnails/'
				if exists(tmp):
					filelist = glob(join(tmp, "*.jpg"))
					for f in filelist:
						remove(f)
					del filelist
				tmp = config.plugins.AdvancedEventLibrary.Location.value + 'poster/thumbnails/'
				if exists(tmp):
					filelist = glob(join(tmp, "*.jpg"))
					for f in filelist:
						remove(f)
					del filelist
				tmp = config.plugins.AdvancedEventLibrary.Location.value + 'preview/thumbnails/'
				if exists(tmp):
					filelist = glob(join(tmp, "*.jpg"))
					for f in filelist:
						remove(f)
					del filelist
			elif ret[0] == 'lade Bilder von AEL-Image-Server (nicht vorhandene)':
				thread = Thread(target=AEL.downloadAllImagesfromAELImageServer, args=())
				thread.start()
			elif ret[0] == 'lade Bilder von AEL-Image-Server (ersetzen)':
				thread = Thread(target=AEL.downloadAllImagesfromAELImageServer, args=(True,))
				thread.start()
			elif ret[0] == 'Bilder überprüfen':
				thread = Thread(target=AEL.checkAllImages, args=())
				thread.start()
			elif ret[0] == 'lade Cover':
				waitList = []
				itm = ["lade Daten, bitte warten...", None, None, None, None, None, None]
				waitList.append((itm,))
				self.cSource = 1
				self['cList'].setList(waitList)
				thread = Thread(target=self.searchPics, args=(False, True))
				thread.start()
			elif ret[0] == 'lade Poster':
				waitList = []
				itm = ["lade Daten, bitte warten...", None, None, None, None, None, None]
				waitList.append((itm,))
				self.pSource = 1
				self['pList'].setList(waitList)
				thread = Thread(target=self.searchPics, args=(False, True))
				thread.start()
			elif 'Screenshot' in ret[0]:
				if self.activeList == "cover":
					self.activeList = 'screenshot cover'
				elif self.activeList == "poster":
					self.activeList = 'screenshot poster'
				elif 'Poster' in ret[0]:
					self.activeList = 'screenshot poster'
				elif 'Cover' in ret[0]:
					self.activeList = 'screenshot cover'
				self.hide()
			AEL.aelGlobals.write_log('Menü : ' + str(ret[0]) + ' - ' + str(self.ptr), DEFAULT_MODULE_NAME)

	def languageCallBack(self, ret=None):
		if ret:
			AEL.aelGlobals.write_log('current language: ' + str(ret[0]), DEFAULT_MODULE_NAME)
			self.language = str(ret[1])

	def key_up_handler(self):
		if self.activeList == 'editor':
			self["config"].instance.moveSelection(self["config"].instance.moveUp)
		elif self.activeList == 'poster':
			self['pList'].moveUp()
		elif self.activeList == 'cover':
			self['cList'].moveUp()
		elif self.activeList == 'choiceBox':
			self['sList'].moveUp()
		self.showPreview()

	def key_down_handler(self):
		if self.activeList == 'editor':
			self["config"].instance.moveSelection(self["config"].instance.moveDown)
		elif self.activeList == 'poster':
			self['pList'].moveDown()
		elif self.activeList == 'cover':
			self['cList'].moveDown()
		elif self.activeList == 'choiceBox':
			self['sList'].moveDown()
		self.showPreview()

	def key_left_handler(self):
		if self.activeList == 'poster':
			self['pList'].pageUp()
		elif self.activeList == 'cover':
			self['cList'].pageUp()
		elif self.activeList == 'choiceBox':
			self['sList'].pageUp()
		self.showPreview()

	def key_right_handler(self):
		if self.activeList == 'poster':
			self['pList'].pageDown()
		elif self.activeList == 'cover':
			self['cList'].pageDown()
		elif self.activeList == 'choiceBox':
			self['sList'].pageDown()
		self.showPreview()

	def checkDoupleNames(self):
		if not self.isInit:
			self.isInit = True
			if self.ptr2 and str(self.ptr2) != str(self.ptr):
				choices, idx = ([(self.ptr,), (self.ptr2,)], 0)
				keys = ["1", "2"]
				self.session.openWithCallback(self.correctNames, ChoiceBox, title='Welchen Titel möchtest Du bearbeiten?', keys=keys, list=choices, selection=idx)
			else:
				self.correctNames(None)

	def correctNames(self, ret):
		if ret and ret[0] == self.ptr2:
			self.ptr = self.ptr2
			self.evt = None
			self.eid = None
		eventData = self.db.getTitleInfo(AEL.convertSearchName(AEL.convert2base64(self.ptr)))
		if not eventData:
			eventData = self.db.getTitleInfo(AEL.convertSearchName(AEL.convert2base64(AEL.convertTitle(self.ptr))))
			if not eventData:
				eventData = self.db.getTitleInfo(AEL.convertSearchName(AEL.convert2base64(AEL.convertTitle2(self.ptr))))
		if not eventData:
			eventData = [AEL.convertSearchName(AEL.convert2base64(self.ptr)), self.ptr, '', '', '', '', '']
		if not self.db.checkTitle(AEL.convert2base64(self.ptr)):
			if self.ptr != 'nothing found':
				self.db.addTitleInfo(AEL.convertSearchName(AEL.convert2base64(self.ptr)), self.ptr, '', '', '', '', '')
		self.eventData = [AEL.convertSearchName(AEL.convert2base64(self.ptr)), self.ptr, '', '', '', '', '']
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
#					if tmp.find('Ohne Altersbe') > 0:
#						self.eventData[5] = str(0)
#					elif (tmp == 'KeineJugendfreigabe' or tmp == 'KeineJugendfreige'):
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
		if self.ptr != 'nothing found':
			if refreshCover and refreshPoster:
				pName1 = AEL.convert2base64(self.ptr) + '.jpg'
				pName2 = AEL.convert2base64(AEL.convertTitle(self.ptr)) + '.jpg'
				pName3 = AEL.convert2base64(AEL.convertTitle2(self.ptr)) + '.jpg'
				AEL.aelGlobals.write_log('1. possible picture name : ' + str(self.ptr) + " as " + str(pName1), DEFAULT_MODULE_NAME)
				if pName1 != pName2:
					AEL.aelGlobals.write_log('2. possible picture name : ' + str(AEL.convertTitle(self.ptr)) + " as " + str(pName2), DEFAULT_MODULE_NAME)
				if pName2 != pName3:
					AEL.aelGlobals.write_log('3. possible picture name : ' + str(AEL.convertTitle2(self.ptr)) + " as " + str(pName3), DEFAULT_MODULE_NAME)
				if isfile(join(config.plugins.AdvancedEventLibrary.Location.value + 'cover/', pName1)):
					AEL.aelGlobals.write_log('found 1. possible cover : ' + str(pName1), DEFAULT_MODULE_NAME)
				if isfile(join(config.plugins.AdvancedEventLibrary.Location.value + 'cover/', pName2)) and pName1 != pName2:
					AEL.aelGlobals.write_log('found 2. possible cover : ' + str(pName2), DEFAULT_MODULE_NAME)
				if isfile(join(config.plugins.AdvancedEventLibrary.Location.value + 'cover/', pName3)) and pName2 != pName3:
					AEL.aelGlobals.write_log('found 3. possible cover : ' + str(pName3), DEFAULT_MODULE_NAME)
				if isfile(join(config.plugins.AdvancedEventLibrary.Location.value + 'poster/', pName1)):
					AEL.aelGlobals.write_log('found 1. possible poster : ' + str(pName1), DEFAULT_MODULE_NAME)
				if isfile(join(config.plugins.AdvancedEventLibrary.Location.value + 'poster/', pName2)) and pName1 != pName2:
					AEL.aelGlobals.write_log('found 2. possible poster: ' + str(pName2), DEFAULT_MODULE_NAME)
				if isfile(join(config.plugins.AdvancedEventLibrary.Location.value + 'poster/', pName3)) and pName2 != pName3:
					AEL.aelGlobals.write_log('found 3. possible poster : ' + pName3, DEFAULT_MODULE_NAME)
			self.coverList = []
			self.posterList = []
			waitList = []
			itm = ["lade Daten, bitte warten...", None, None, None, None, None, None]
			waitList.append((itm,))
			if refreshCover:
				coverFiles = glob(config.plugins.AdvancedEventLibrary.Location.value + 'cover/' + AEL.convert2base64(self.ptr.strip()) + '.jpg')
				c2 = glob(config.plugins.AdvancedEventLibrary.Location.value + 'cover/' + AEL.convert2base64(AEL.convertTitle(self.ptr).strip()) + '.jpg')
				for file in c2:
					if file not in coverFiles:
						coverFiles.append(file)
				c2 = glob(config.plugins.AdvancedEventLibrary.Location.value + 'cover/' + AEL.convert2base64(AEL.convertTitle2(self.ptr).strip()) + '.jpg')
				for file in c2:
					if file not in coverFiles:
						coverFiles.append(file)
				del c2
				coverFile = AEL.getImageFile(config.plugins.AdvancedEventLibrary.Location.value + 'cover/', self.ptr)
				if coverFile and coverFile not in coverFiles:
					coverFiles.append(coverFile)
				if self.orgName and self.orgName != self.ptr:
					coverFiles2 = glob(config.plugins.AdvancedEventLibrary.Location.value + 'cover/' + AEL.convert2base64(self.orgName.strip()) + '.jpg')
					for file in coverFiles2:
						if file not in coverFiles:
							coverFiles.append(file)
					p2 = glob(config.plugins.AdvancedEventLibrary.Location.value + 'cover/' + AEL.convert2base64(AEL.convertTitle(self.orgName).strip()) + '.jpg')
					for file in p2:
						if file not in coverFiles:
							coverFiles.append(file)
					c2 = glob(config.plugins.AdvancedEventLibrary.Location.value + 'cover/' + AEL.convert2base64(AEL.convertTitle2(self.orgName).strip()) + '.jpg')
					for file in p2:
						if file not in coverFiles:
							coverFiles.append(file)
					del p2
					coverFile = AEL.getImageFile(config.plugins.AdvancedEventLibrary.Location.value + 'cover/', self.orgName)
					if coverFile and coverFile not in coverFiles:
						coverFiles.append(coverFile)
				for files in coverFiles:
					name = basename(files).replace('.jpg', '')
#					try:
					fn = b64decode(basename(files).replace('.jpg', ''))
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
					i = 0
					for name in self.coverList:
						if name[0][0] == self.eventTitle.value.lower():
							self['cList'].moveToIndex(i)
							break
						i += 1
				else:
					self.cSource = 1
					self['cList'].setList(waitList)
					thread = Thread(target=self.searchPics, args=(False, True))
					thread.start()
				del coverFiles
			if refreshPoster:
				posterFiles = glob(config.plugins.AdvancedEventLibrary.Location.value + 'poster/' + AEL.convert2base64(self.ptr.strip()) + '.jpg')
				p2 = glob(config.plugins.AdvancedEventLibrary.Location.value + 'poster/' + AEL.convert2base64(AEL.convertTitle(self.ptr).strip()) + '.jpg')
				for file in p2:
					if file not in posterFiles:
						posterFiles.append(file)
				c2 = glob(config.plugins.AdvancedEventLibrary.Location.value + 'poster/' + AEL.convert2base64(AEL.convertTitle2(self.ptr).strip()) + '.jpg')
				for file in p2:
					if file not in posterFiles:
						posterFiles.append(file)
				del p2
				posterFile = AEL.getImageFile(config.plugins.AdvancedEventLibrary.Location.value + 'poster/', self.ptr)
				if posterFile and posterFile not in posterFiles:
					posterFiles.append(posterFile)

				if self.orgName and self.orgName != self.ptr:
					posterFiles2 = glob(config.plugins.AdvancedEventLibrary.Location.value + 'poster/' + AEL.convert2base64(self.orgName.strip()) + '.jpg')
					for file in posterFiles2:
						if file not in posterFiles:
							posterFiles.append(file)
					p2 = glob(config.plugins.AdvancedEventLibrary.Location.value + 'poster/' + AEL.convert2base64(AEL.convertTitle(self.orgName).strip()) + '.jpg')
					for file in p2:
						if file not in posterFiles:
							posterFiles.append(file)
					c2 = glob(config.plugins.AdvancedEventLibrary.Location.value + 'poster/' + AEL.convert2base64(AEL.convertTitle2(self.orgName).strip()) + '.jpg')
					for file in p2:
						if file not in posterFiles:
							posterFiles.append(file)
					del p2
					posterFile = AEL.getImageFile(config.plugins.AdvancedEventLibrary.Location.value + 'poster/', self.orgName)
					if posterFile and posterFile not in posterFiles:
							posterFiles.append(posterFile)
				for files in posterFiles:
					name = basename(files).replace('.jpg', '')
#					try:
					fn = b64decode(basename(files).replace('.jpg', ''))
#					except:
#						fn = basename(files).replace('.jpg', '')
					itm = [fn, 'Poster', name, files]
					self.posterList.append((itm,))
				if self.posterList:
					self.posterList.sort(key=lambda x: x[0], reverse=False)
					self.pSource = 0
					self['pList'].setList(self.posterList, 0)
					i = 0
					for name in self.posterList:
						if name[0][0] == self.eventTitle.value.lower():
							self['pList'].moveToIndex(i)
							break
						i += 1
				else:
					self.pSource = 1
					self['pList'].setList(waitList)
					thread = Thread(target=self.searchPics, args=(False, True))
					thread.start()
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
				self['pList'].setList(AEL.get_PictureList(searchtext, 'Poster', self.ImageCount, self.eventData[0], self.language, " Serie"))
			else:
				self['pList'].setList(AEL.get_PictureList(searchtext, 'Poster', self.ImageCount, self.eventData[0], self.language, " Film"))
		if cover:
			if "Serie" in self.eventGenre.value:
				self['cList'].setList(AEL.get_PictureList(searchtext, 'Cover', self.ImageCount, self.eventData[0], self.language, " Serie"))
			else:
				self['cList'].setList(AEL.get_PictureList(searchtext, 'Cover', self.ImageCount, self.eventData[0], self.language, " Film"))

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
			AdvancedEventLibraryLists.removeFiles()
			AEL.clearMem("AEL-Editor")
			self.close()


####################################################################################################################################################################
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
