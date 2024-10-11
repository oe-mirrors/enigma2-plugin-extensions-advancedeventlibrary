from time import time, localtime, mktime, strftime
from datetime import datetime, timedelta
from os.path import join, isfile, realpath, basename, exists
from html.parser import HTMLParser
from pickle import load
from struct import unpack
from enigma import getDesktop, eEPGCache, eServiceReference, eServiceCenter, eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_VALIGN_BOTTOM, RT_WRAP, BT_SCALE
from skin import variables, parseColor
from Components.config import config
from Components.Label import MultiColorLabel
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.Sources.ServiceEvent import ServiceEvent
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
from Screens.ChannelSelection import service_types_tv
from Screens.ChoiceBox import ChoiceBox
from Screens.InfoBar import InfoBar, MoviePlayer
from Screens.Setup import Setup
from ServiceReference import ServiceReference
from Tools.Alternatives import GetWithAlternative
from Tools.Directories import fileExists
import NavigationInstance

from . import AdvancedEventLibrarySystem, AdvancedEventLibrarySimpleMovieWall, AdvancedEventLibraryChannelSelection
from . AdvancedEventLibraryLists import AELBaseWall, MultiColorNTextLabel
from Tools.AdvancedEventLibrary import PicLoader, aelGlobals, write_log, convert2base64, getDB, getImageFile, clearMem
from Tools.LoadPixmap import LoadPixmap

DEFAULT_MODULE_NAME = __name__.split(".")[-1]
htmlParser = HTMLParser()
pluginpath = '/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/'
desktopSize = getDesktop(0).size()
skinpath = pluginpath + 'skin/1080/' if desktopSize.width() == 1920 else pluginpath + 'skin/720/'
imgpath = '/usr/share/enigma2/AELImages/'
log = "/var/tmp/AdvancedEventLibrary.log"

global active
active = False


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
		return '{%s}' % str(', '.join('%s : %s' % (k, repr(v)) for (k, v) in self.__dict__.keys()))


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
		return '{%s}' % str(', '.join('%s : %s' % (k, repr(v)) for (k, v) in self.__dict__.keys()))


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
		self.myFavourites = {}
		imgpath = variables.get("EventLibraryImagePath", '/usr/share/enigma2/AELImages/,').replace(',', '')
		self.shaper = LoadPixmap(imgpath + "shaper.png") if fileExists(imgpath + "shaper.png") else LoadPixmap('/usr/share/enigma2/AELImages/shaper.png')
		self.userBouquets = []
		self.userBouquets.append(('Alle Bouquets',))
		self.channelType = 0
#		self.channelType = int(config.plugins.AdvancedEventLibrary.MediaHubStartType.value)
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
		self.favourites = self.load_pickle(join(pluginpath, 'favourites.data')) if fileExists(join(pluginpath, 'favourites.data')) else {'genres': {'Nachrichten': [2, time()]}, 'titles': {}}
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

		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Channellist"))
		self["key_yellow"] = StaticText(_("Bouqueta"))
		self["key_blue"] = StaticText(_("Advanced-Event-Library"))

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
		excludedGenres = config.plugins.AdvancedEventLibrary.ExcludedGenres.value.split(',')
		for k, v in self.favourites['genres'].items():
			if k not in excludedGenres and v[0] >= config.plugins.AdvancedEventLibrary.FavouritesViewCount.value:
				res = self.db.getFavourites("genre LIKE '" + k + "'", (config.plugins.AdvancedEventLibrary.FavouritesPreviewDuration.value * 3600))
				if res:
					favs[k] = res
		for k, v in self.favourites['titles'].items():
			if v[0] >= config.plugins.AdvancedEventLibrary.FavouritesViewCount.value:
				res = self.db.getFavourites("title LIKE '%" + k + "%'", (config.plugins.AdvancedEventLibrary.FavouritesPreviewDuration.value * 3600))
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
			self.channelListControl = eval(str(self.channelParameter[22]))
			self.channelListCoverings = eval(str(self.channelParameter[23]))
			self.channelListFontOrientation = self.getFontOrientation(self.channelParameter[25])

			self.myFavourites = self.getFavourites()

			if config.plugins.AdvancedEventLibrary.ChannelSelectionStartBouquet.value == 'Alle Bouquets':
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

			imgpath = variables.get("EventLibraryImagePath", '/usr/share/enigma2/AELImages/,').replace(',', '')
			ptr = LoadPixmap(join(imgpath, "play.png"))
			self["trailer"].instance.setPixmap(ptr)

			self.movieParameter = self["movieList"].getParameter()
			self.movieImageType = str(self.movieParameter[3])
			self.movieSubstituteImage = str(self.movieParameter[5])
			self.movieListControl = eval(self.movieParameter[22])
			self.movieListCoverings = eval(str(self.movieParameter[23]))
			self.movieListFontOrientation = self.getFontOrientation(self.movieParameter[25])
			if fileExists(join(pluginpath, 'moviewall.data')):
				self.moviedict = self.load_pickle(join(pluginpath, 'moviewall.data'))
				self.getMovieList()
			else:
				self.moviedict = {}

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
			data = load(f)
		return data

	def infoKeyPressed(self):
		if self.activeList == "TV":
			self.channelType += 1 if self.channelType < 4 else 0
			self.getChannelList(self.currentBouquet, self.channelType)
			if self.channelList:
				self["channelList"].setlist(self.channelList)
				self["channelList"].movetoIndex(self.idx)
				self["channelList"].refresh()
				self["channelsInfo"].setText(str(self["channelList"].getCurrentIndex() + 1) + '/' + str(self.channelListLen))
				self.channel_changed()
		else:
			self.movieType += 1 if self.movieType < 1 else 0
			self.getMovieList(self.movieType)
			if self.moviedict:
				self.movie_changed()

	def getMovieList(self, typ=0):
		currentList = []
		mlist = []
		for k in self.moviedict:
			for v in self.moviedict[k]:
				if 'files' in self.moviedict[k][v]:
					for file in self.moviedict[k][v]['files']:
						mlist.append(file)
		if mlist:
			mlist = [t for t in (set(tuple(i) for i in mlist))]
			if typ == 0:
				mlist.sort(key=lambda x: x[1], reverse=True)
				mlist = mlist[:config.plugins.AdvancedEventLibrary.RecordingsCount.value]
			else:
				mlist.sort(key=lambda x: x[2], reverse=False)
			for item in mlist:
				image = getImageFile(aelGlobals.HDDPATH + self.movieImageType, item[2])
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
			self.moviedict = {}

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
					_progress = (int(time()) - event.getBeginTime()) * 100 / event.getDuration() if int(event.getDuration()) > 0 else 0
					image = None
					name = ''
					hasTrailer = None
					evt = self.db.getliveTV(event.getEventId(), event.getEventName(), event.getBeginTime())
					if evt and evt[0][16].endswith('mp4'):
						hasTrailer = evt[0][16]
					if hasTrailer is None:
						dbdata = self.db.getTitleInfo(convert2base64(event.getEventName()))
						if dbdata and dbdata[7].endswith('mp4'):
							hasTrailer = dbdata[7]
					if self.channelImageType in ["poster", "poster/thumbnails", "cover", "cover/thumbnails"]:
						if evt and evt[0][3] != '':
							image = getImageFile(aelGlobals.HDDPATH + self.channelImageType, evt[0][3])
							name = evt[0][3]
						if image is None:
							image = getImageFile(aelGlobals.HDDPATH + self.channelImageType, event.getEventName())
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
						dt = datetime(now.tm_year, now.tm_mon, now.tm_mday, config.plugins.AdvancedEventLibrary.StartTime.value[0], config.plugins.AdvancedEventLibrary.StartTime.value[1])
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
							if int(time() - event_now.getBeginTime()) < (config.plugins.AdvancedEventLibrary.MaxEventAge.value * 60):
								event = event_now
							else:
								event_next = self.epgcache.getNextTimeEntry()
								if int(event_next.getBeginTime() - time()) < (config.plugins.AdvancedEventLibrary.MaxEventStart.value * 60):
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
							_progress = (int(time()) - event.getBeginTime()) * 100 / event.getDuration() if int(event.getDuration()) > 0 else 0
							image = None
							name = ''
							hasTrailer = ""
							evt = self.db.getliveTV(event.getEventId(), event.getEventName(), event.getBeginTime())
							if evt and evt[0][16].endswith('mp4'):
								hasTrailer = evt[0][16]
							if self.channelImageType in ["poster", "poster/thumbnails", "cover", "cover/thumbnails"]:
								if evt and evt[0][3] != '':
									image = getImageFile(aelGlobals.HDDPATH + self.channelImageType, evt[0][3])
									name = evt[0][3]
								if image is None:
									image = getImageFile(aelGlobals.HDDPATH + self.channelImageType, event.getEventName())

							cleanname = str(event.getEventName()).strip().replace(".", "").replace(":", "").replace("-", "").replace("  ", " ").upper()
							hasTimer = False
							if cleanname in self.timers or str(event.getEventId()) in self.timers or name in self.timers:
								hasTimer = True
								number = self.channelNumbers[bouquet[1]].get(serviceref, 0)[0]
							itm = ChannelEntry(serviceref, event.getEventId(), servicename, event.getEventName(), '', '', _progress, picon, image, bouquet[0], hasTimer, number, event.getBeginTime(), hasTrailer)
							self.channelList.append((itm,))
		self.channelListLen = len(self.channelList)
		if self.channelList:
			self["channelsText"].setTXT(typ)
		else:
			self["channelsText"].setText("keine Ergebnisse gefunden")

	def buildMovieList(self, entrys):
		maxLength = self.movieParameter[2]
		name = str(entrys.name)[:maxLength] + '...' if len(entrys.name) > maxLength else entrys.name
		self.picloader = PicLoader(int(self.movieParameter[0]), int(self.movieParameter[1]))
		image = self.picloader.load(entrys.image)
		self.picloader.destroy()
		ret = [entrys]
		#ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.movieParameter[17][0], self.movieParameter[17][1], self.movieParameter[17][0], self.movieParameter[17][1], self.movieParameter[17][2], self.movieParameter[17][3], self.movieParameter[17][2], self.movieParameter[17][3], image, None, None, BT_SCALE))
		ret.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.movieParameter[17][0], self.movieParameter[17][1], self.movieParameter[17][2], self.movieParameter[17][3], image, None, None, BT_SCALE))
		for covering in self.movieListCoverings:
			ret.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, covering[0], covering[1], covering[2], covering[3], self.shaper, None, None, BT_SCALE))
		ret.append((eListboxPythonMultiContent.TYPE_TEXT, self.movieParameter[19][0], self.movieParameter[19][1], self.movieParameter[19][2], self.movieParameter[19][3], self.movieParameter[19][5], self.movieParameter[19][5], self.movieListFontOrientation, name, parseColor(self.movieParameter[6]).argb(), parseColor(self.movieParameter[7]).argb()))
		ret.append((eListboxPythonMultiContent.TYPE_PROGRESS, self.movieParameter[24][0], self.movieParameter[24][1], self.movieParameter[24][2], self.movieParameter[24][3], entrys.progress, self.movieParameter[13], parseColor(self.movieParameter[9]).argb(), parseColor(self.movieParameter[11]).argb(), parseColor(self.movieParameter[10]).argb(), parseColor(self.movieParameter[12]).argb()))
		return ret

	def buildChannelList(self, entrys):
		maxLength = self.channelParameter[2]
		if len(entrys.servicename) > maxLength:
			entrys.servicename = str(entrys.servicename)[:maxLength] + '...'
		title = str(entrys.title)[:maxLength] + '...' if len(entrys.title) > maxLength else entrys.title
		self.picloader = PicLoader(int(self.channelParameter[0]), int(self.channelParameter[1]))
		if entrys.image:
			image = self.picloader.load(entrys.image)
		else:
			image = LoadPixmap(str(entrys.picon)) if self.channelSubstituteImage == "replaceWithPicon" else self.picloader.load(self.channelSubstituteImage)  # self.picloader.load(entrys.picon)
		self.picloader.destroy()
#		self.picloader = PicLoader(100, 60)
		picon = LoadPixmap(str(entrys.picon))  # self.picloader.load(entrys.picon)
#		self.picloader.destroy()
		ret = [entrys]
#		ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[17][0], self.channelParameter[17][1], self.channelParameter[17][0], self.channelParameter[17][1], self.channelParameter[17][2], self.channelParameter[17][3], self.channelParameter[17][2], self.channelParameter[17][3], image, None, None, BT_SCALE))
		ret.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.channelParameter[17][0], self.channelParameter[17][1], self.channelParameter[17][2], self.channelParameter[17][3], image, None, None, BT_SCALE))
		for covering in self.channelListCoverings:
			# ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, covering[0], covering[1], covering[0], covering[1], covering[2], covering[3], covering[2], covering[3], self.shaper, None, None, BT_SCALE))
			ret.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, covering[0], covering[1], covering[2], covering[3], self.shaper, None, None, BT_SCALE))
		# ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[21][0], self.channelParameter[21][1], self.channelParameter[21][0], self.channelParameter[21][1], self.channelParameter[21][2], self.channelParameter[21][3], self.channelParameter[21][2], self.channelParameter[21][3], picon, None, None, BT_SCALE))
		ret.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.channelParameter[21][0], self.channelParameter[21][1], self.channelParameter[21][2], self.channelParameter[21][3], picon, None, None, BT_SCALE))
		# ret.append((eWallPythonMultiContent.TYPE_PROGRESS, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[24][0], self.channelParameter[24][1], self.channelParameter[24][0], self.channelParameter[24][1], self.channelParameter[24][2], self.channelParameter[24][3], self.channelParameter[24][2], self.channelParameter[24][3], entrys.progress, self.channelParameter[13], parseColor(self.channelParameter[9]).argb(), parseColor(self.channelParameter[11]).argb(), parseColor(self.channelParameter[10]).argb(), parseColor(self.channelParameter[12]).argb()))
		ret.append((eListboxPythonMultiContent.TYPE_PROGRESS, self.channelParameter[24][0], self.channelParameter[24][1], self.channelParameter[24][2], self.channelParameter[24][3], entrys.progress, self.channelParameter[13], parseColor(self.channelParameter[9]).argb(), parseColor(self.channelParameter[11]).argb(), parseColor(self.channelParameter[10]).argb(), parseColor(self.channelParameter[12]).argb()))
		if entrys.hasTimer and fileExists(self.channelParameter[15]):
			# ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[19][0] + self.channelParameter[19][4], self.channelParameter[19][1], self.channelParameter[19][0] + self.channelParameter[19][4], self.channelParameter[19][1], self.channelParameter[19][2], self.channelParameter[19][3], self.channelParameter[19][2], self.channelParameter[19][3], self.channelParameter[19][5], self.channelParameter[19][5], self.channelListFontOrientation, str(entrys.number) + ' ' + entrys.servicename, parseColor(self.channelParameter[6]).argb(), parseColor(self.channelParameter[7]).argb()))
			# ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[20][0] + self.channelParameter[20][4], self.channelParameter[20][1], self.channelParameter[20][0] + self.channelParameter[20][4], self.channelParameter[20][1], self.channelParameter[20][2], self.channelParameter[20][3], self.channelParameter[20][2], self.channelParameter[20][3], self.channelParameter[20][5], self.channelParameter[20][5], self.channelListFontOrientation, title, parseColor(self.channelParameter[6]).argb(), parseColor(self.channelParameter[7]).argb()))
			# ret.append((eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[18][0], self.channelParameter[18][1], self.channelParameter[18][0], self.channelParameter[18][1], self.channelParameter[18][2], self.channelParameter[18][3], self.channelParameter[18][2], self.channelParameter[18][3], LoadPixmap(self.channelParameter[15]), None, None, BT_SCALE))
			ret.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.channelParameter[18][0], self.channelParameter[18][1], self.channelParameter[18][2], self.channelParameter[18][3], LoadPixmap(self.channelParameter[15]), None, None, BT_SCALE))
		else:
			# ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[19][0], self.channelParameter[19][1], self.channelParameter[19][0], self.channelParameter[19][1], self.channelParameter[19][2], self.channelParameter[19][3], self.channelParameter[19][2], self.channelParameter[19][3], self.channelParameter[19][5], self.channelParameter[19][5], self.channelListFontOrientation, str(entrys.number) + ' ' + entrys.servicename, parseColor(self.channelParameter[6]).argb(), parseColor(self.channelParameter[7]).argb()))
			ret.append((eListboxPythonMultiContent.TYPE_TEXT, self.channelParameter[19][0], self.channelParameter[19][1], self.channelParameter[19][2], self.channelParameter[19][3], self.channelParameter[19][5], self.channelParameter[19][5], self.channelListFontOrientation, str(entrys.number) + ' ' + entrys.servicename, parseColor(self.channelParameter[6]).argb(), parseColor(self.channelParameter[7]).argb()))
			# ret.append((eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, self.channelParameter[20][0], self.channelParameter[20][1], self.channelParameter[20][0], self.channelParameter[20][1], self.channelParameter[20][2], self.channelParameter[20][3], self.channelParameter[20][2], self.channelParameter[20][3], self.channelParameter[20][5], self.channelParameter[20][5], self.channelListFontOrientation, title, parseColor(self.channelParameter[6]).argb(), parseColor(self.channelParameter[7]).argb()))
			ret.append((eListboxPythonMultiContent.TYPE_TEXT, self.channelParameter[20][0], self.channelParameter[20][1], self.channelParameter[20][2], self.channelParameter[20][3], self.channelParameter[20][5], self.channelParameter[20][5], self.channelListFontOrientation, title, parseColor(self.channelParameter[6]).argb(), parseColor(self.channelParameter[7]).argb()))
		return ret
#		write_log("error in entrys : " + str(entrys), DEFAULT_MODULE_NAME)
#		return [entrys,
#							(eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, 2, 2, 2, 2, 96, 96, 96, 96, 0, 0, RT_WRAP | RT_HALIGN_CENTER | RT_VALIGN_CENTER, 'Das war wohl nix', parseColor(self.channelParameter[6]).argb(), parseColor(self.channelParameter[7]).argb()),

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
			pngname = join(config.usage.picon_dir.value, service + ".png")
			if isfile(pngname):
				return pngname
		if serviceName is not None:
			pngname = join(config.usage.picon_dir.value, serviceName + ".png")
			if isfile(pngname):
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
			if "::" not in sRef:
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
		if self.activeList == "TV":
			selected_element = self["channelList"].l.getCurrentSelection()[0]
			if selected_element and selected_element.hasTrailer:
					sRef = eServiceReference(4097, 0, str(selected_element.hasTrailer))
					sRef.setName(str(selected_element.title))
					self.session.open(MoviePlayer, sRef)
		else:
			selected_element = self["movieList"].l.getCurrentSelection()[0]
			if selected_element and selected_element.hasTrailer:
					sRef = eServiceReference(4097, 0, str(selected_element.hasTrailer))
					sRef.setName(str(selected_element.name))
					self.session.open(MoviePlayer, sRef)

	def key_red_handler(self):
		clearMem("MediaHub")
		global active
		active = False
		self.close()

	def key_green_handler(self):
		if self.activeList == "TV":
			self.session.open(AdvancedEventLibraryChannelSelection.AdvancedEventLibraryChannelSelection, self["channelList"].getcurrentselection().serviceref)
		else:
			self.session.open(AdvancedEventLibrarySimpleMovieWall.AdvancedEventLibrarySimpleMovieWall, config.plugins.AdvancedEventLibrary.ViewType.value)

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
					dest = 0 if (old_idx + 1) >= self.channelListLen else old_idx + 1
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
					dest = self.channelListLen - 1 if (new_idx - 1) < 0 else old_idx - 1
					self['channelList'].movetoIndex(dest)
		elif what == "down":
			old_idx = int(self['channelList'].getCurrentIndex())
			if old_idx == self.channelListLen - 1:
				self['channelList'].movetoIndex(0)
			else:
				self['channelList'].down()
				new_idx = int(self['channelList'].getCurrentIndex())
				if new_idx <= old_idx:
					dest = 0 if (new_idx + self.channelParameter[14]) >= self.channelListLen else new_idx + self.channelParameter[14]
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
					dest = self.channelListLen - 1 if (new_idx - self.channelParameter[14]) < 0 else new_idx - self.channelParameter[14]
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
					dest = 0 if (old_idx + 1) >= self.movieListLen else old_idx + 1
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
					dest = self.movieListLen - 1 if (new_idx - 1) < 0 else old_idx - 1
					self['movieList'].movetoIndex(dest)
		elif what == "down":
			old_idx = int(self['movieList'].getCurrentIndex())
			if old_idx == self.movieListLen - 1:
				self['movieList'].movetoIndex(0)
			else:
				self['movieList'].down()
				new_idx = int(self['movieList'].getCurrentIndex())
				if new_idx <= old_idx:
					dest = 0 if (new_idx + self.movieParameter[14]) >= self.movieListLen else new_idx + self.movieParameter[14]
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
					dest = self.movieListLen - 1 if (new_idx - self.movieParameter[14]) < 0 else new_idx - self.movieParameter[14]
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
		events = []
		selected_channel = self["channelList"].getcurrentselection()
		if selected_channel:
			sRef = str(selected_channel.serviceref)
			eit = int(selected_channel.eit)
			self.current_event = self.epgcache.lookupEventId(eServiceReference(sRef), eit)
			self["Service"].newService(eServiceReference(sRef), self.current_event)
			if self.channelType in [0, 1, 2]:
				beginTime = int((int(selected_channel.begin) - int(time())) / 60) if int(selected_channel.begin) > int(time()) else int((int(time()) - int(selected_channel.begin)) / 60)
				_timeInfo = str(beginTime) + " Min."
				timeText = "beginnt in " + _timeInfo if int(selected_channel.begin) > int(time()) else "begann vor " + _timeInfo
				self["timeInfo"].setText(timeText.replace('beginnt in 0 Min.', 'beginnt jetzt').replace('begann vor 0 Min.', 'beginnt jetzt'))
			elif self.channelType == 3:
				_timeInfo = f"beginnt um {strftime('%H:%M', localtime(selected_channel.begin))} Uhr"
				self["timeInfo"].setText(_timeInfo)
			else:
				_timeInfo = f"beginnt am {strftime('%a, %H:%M', localtime(selected_channel.begin))} Uhr"
				self["timeInfo"].setText(self.correctweekdays(_timeInfo))
			if selected_channel.hasTrailer:
				self["trailer"].show()
			else:
				self["trailer"].hide()

	def movie_changed(self):
		cs = self['movieList'].getcurrentselection()
		info = eServiceCenter.getInstance().info(cs.service)
		if info:
			self.current_event = info.getEvent(cs.service)
			if self.current_event:
				self["Service"].newService(cs.service, self.current_event)
			else:
				self["Service"].newService(cs.service)
		beginTime = datetime.fromtimestamp(cs.date)
		_timeInfo = beginTime.strftime("%d.%m.%Y - %H:%M")
		timeText = "Aufnahme vom " + _timeInfo
		self["timeInfo"].setText(timeText)
		if cs.hasTrailer:
			self["trailer"].show()
		else:
			self["trailer"].hide()

	def key_info_handler(self):
		from Screens.EventView import EventViewSimple, EventViewMovieEvent
		if self.activeList == "TV":
			selected_event = self["channelList"].getcurrentselection()
			if selected_event:
				sRef = str(selected_event.serviceref)
				if config.plugins.AdvancedEventLibrary.EPGconfig.plugins.AdvancedEventLibrary.ViewType.value == "EPGSelection":
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

	def getMovieLen(self, moviename):
		if fileExists(moviename + ".cuts"):
			try:
				f = open(moviename + ".cuts", "rb")
				packed = f.read()
				f.close()
				while len(packed) > 0:
					packedCue = packed[:12]
					packed = packed[12:]
					cue = unpack('>QI', packedCue)
					if cue[1] == 5:
						movie_len = cue[0] / 90000
						return movie_len
			except Exception as ex:
				write_log("getMovieLen : " + str(ex), DEFAULT_MODULE_NAME)
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
					cue = unpack('>QI', packedCue)
					cut_list.append(cue)
			except Exception as ex:
				movie_len = -1
				write_log(ex, DEFAULT_MODULE_NAME)

		last_end_point = None

		if len(cut_list):
			for (pts, what) in cut_list:
				if what == 3:
					last_end_point = pts / 90000
		play_progress = (last_end_point * 100) / movie_len if movie_len > 0 and last_end_point is not None else 0
		if play_progress > 100:
			play_progress = 100
		return play_progress

	def correctweekdays(self, itm):
		_itm = str(itm)
		_itm = _itm.replace("Mon", "Mo").replace("Tue", "Di").replace("Wed", "Mi").replace("Thu", "Do").replace("Fri", "Fr").replace("Sat", "Sa").replace("Sun", "So")
		return _itm

####################################################################################


class MySetup(Setup):
	def __init__(self, session):
		self.session = session
		Setup.__init__(self, session, "AEL-Media-Hub-Setup", plugin="Extensions/AdvancedEventLibrary", PluginLanguageDomain="AdvancedEventLibrary")
		self["entryActions"] = HelpableActionMap(self, ["ColorActions"],
														{
														"green": (self.do_close, _("save")),
														}, prio=0, description=_("AEL-Media-Hub-Setup"))

	def changedEntry(self):  # TODO: kann man bestimmt besser machen
		cur = self["config"].getCurrent()
		self["config"].setList(self.configlist)
		#if cur and cur is not None:
		#	self["config"].updateConfigListView(cur)

	def do_close(self):
		restartbox = self.session.openWithCallback(self.restartGUI, MessageBox, _("GUI needs a restart to apply new configuration.\nDo you want to restart the GUI now ?"), MessageBox.TYPE_YESNO)
		restartbox.setTitle(_("GUI needs a restart."))

	def restartGUI(self, answer):  # TODO: kann man bestimmt besser machen
		if answer is True:
			for x in self["config"].list:
				x[1].save()
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close()
