from os.path import join, isfile
from time import localtime, mktime
from html.parser import HTMLParser
from enigma import getDesktop, eEPGCache, eServiceReference, eServiceCenter, eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_VALIGN_BOTTOM, RT_WRAP, BT_SCALE
from skin import loadSkin, variables, parseColor
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.config import config
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.Event import Event
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
from Screens.ChannelSelection import service_types_tv
from Screens.ChoiceBox import ChoiceBox
from Screens.TimerEntry import TimerEntry
from Screens.InfoBar import MoviePlayer
from Screens.Setup import Setup
from ServiceReference import ServiceReference
from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT
from Tools.Directories import fileExists
from Tools.LoadPixmap import LoadPixmap
import NavigationInstance
from . import AdvancedEventLibrarySystem
from . import AdvancedEventLibraryLists
from Tools.AdvancedEventLibrary import PicLoader, write_log, convertDateInFileName, convertTitle, convertTitle2, convert2base64, convertSearchName, getDB, getImageFile, clearMem, aelGlobals

pluginpath = '/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/'
desktopSize = getDesktop(0).size()
skinpath = pluginpath + 'skin/1080/' if desktopSize.width() == 1920 else pluginpath + 'skin/720/'
imgpath = '/usr/share/enigma2/AELImages/'
log = "/var/tmp/AdvancedEventLibrary.log"
Movies = ["Abenteuer", "Abenteuerfilm", "Abenteuerkomödie", "Action", "Action Abenteuer", "Action-Abenteuer", "Action-Fantasyfilm", "Actionabenteuer", "Actiondrama", "Actionfilm", "Actionkomödie", "Actionkrimi", "Actionthriller", "Agentenfilm", "Agentenkomödie", "Agententhriller", "Beziehungsdrama", "Beziehungskomödie", "Bibelverfilmung", "Bollywoodfilm", "Comicverfilmung", "Crime", "Deutsche Komödie", "Drama", "Dramedy", "Ehedrama", "Ehekomödie", "Episodenfilm", "Erotikdrama", "Erotikfilm", "Erotikkomödie", "Familie", "Familiendrama", "Familienfilm", "Familienkomödie", "Familiensaga", "Fantasy", "Fantasy-Abenteuer", "Fantasy-Abenteuerfilm", "Fantasy-Action", "Fantasyabenteuer", "Fantasyaction", "Fantasydrama", "Fantasyfilm", "Fantasykomödie", "Fernsehfilm", "Gangsterdrama", "Gangsterkomödie", "Gangsterthriller", "Gaunerkomödie", "Geföngnisdrama", "Geschichtliches Drama", "Gesellschaftsdrama", "Gesellschaftskomödie", "Gesellschaftssatire", "Gruselfilm", "Gruselkomödie", "Heimatdrama", "Heimatfilm", "Heimatkomödie", "Historienabenteuer", "Historiendrama", "Historienfilm", "Historisches Drama", "Horror", "Horror-Actionfilm", "Horrorfilm", "Horrorkomödie", "Horrorthriller", "Italo-Western", "Jugenddrama", "Jugendfilm", "Jugendkomödie", "Justizdrama", "Justizthriller", "Katastrophendrama", "Katastrophenfilm", "Kriegsdrama", "Komödie", "Kriegsfilm", "Krimi", "Krimidrama", "Krimikomödie", "Krimikömödie", "Kriminalfilm", "Krimiparodie", "Liebesdrama", "Liebesdramödie", "Liebesfilm", "Liebesgeschichte", "Liebeskomödie", "Liebesmelodram", "Literaturverfilmung", "Mediensatire", "Melodram", "Monumentalfilm", "Mystery", "Mysterydrama", "Mysteryfilm", "Mysterythriller", "Psychodrama", "Psychokrimi", "Psychothriller", "Revuefilm", "Politdrama", "Politkomödie", "Politsatire", "Politthriller", "Road Movie", "Romance", "Romantic Comedy", "Romantikkomödie", "Romantische Komödie", "Romanverfilmung", "Romanze", "Satire", "Schwarze Komödie", "Sci-Fi-Fantasy", "Science-Fiction", "Science-Fiction-Abenteuer", "Science-Fiction-Action", "Science-Fiction-Film", "Science-Fiction-Horror", "Science-Fiction-Komödie", "Science-Fiction-Thriller", "Spielfilm", "Spionagethriller", "Sportfilm", "Sportlerkomödie", "Tanzfilm", "Teenagerfilm", "Teenagerkomödie", "Teeniekomödie", "Thriller", "Thrillerkomödie", "Tierfilm", "Tragikomödie", "TV-Movie", "Vampirfilm", "Vampirkomödie", "Western", "Westerndrama", "Westernkomödie"]
Series = ["Abenteuer-Serie", "Actionserie", "Arztreihe", "Crime-Serie", "Episode", "Familien-Serie", "Staffel", "Folge", "Familienserie", "Fernsehserie", "Fernsehspiel", "Heimatserie", "Horror-Serie", "Comedy-Serie", "Dramaserie", "Krankenhaus-Serie", "Krankenhaus-Soap", "Krimireihe", "Krimi-Serie", "Krimiserie", "Polizeiserie", "Reality", "Scripted Reality", "Scripted-Reality", "Science-Fiction-Serie", "Sci-Fi-Serie", "Serie", "Serien", "Sitcom", "Soap", "Telenovela"]
Dokus = ["Doku-Experiment", "Doku-Reihe", "Doku-Serie", "Documentary", "Documentary-Serie", "Dokumentarfilm", "Dokumentarreihe", "Dokumentarserie", "Dokumentation", "Dokumentation-Serie", "Dokumentationsreihe", "Dokureihe", "Dokuserie", "Dokutainment", "Dokutainment-Reihe", "History", "Naturdokumentarreihe", "Naturdokumentation", "Naturdokumentationsreihe", "Real Life Doku", "Reality-Doku", "Reality-TV", "Reisedoku", "Reportage", "Reportagemagazin", "Reportagereihe", "Biografie", "Biographie", "Familienchronik", "Ermittler-Doku", "Koch-Doku", "Portröt", "War", "War & Politics", "Wissenschaftsmagazin", "Wissensmagazin"]
Music = ["Disco", "Musical", "Musik", "Music", "Musikdokumentation", "Musikfilm", "Musikkomödie", "Konzertfilm", "Konzert"]
Kinder = ["Animation", "Animations-Serie", "Animationsfilm", "Animationsserie", "Kinder-Abenteuerfilm", "Kinder-Animationsfilm", "Kinder-Fantasyfilm", "Kinder-Komödie", "Kinder-Zeichentrickfilm", "Kinderabenteuer", "Kinderfilm", "Kinderserie", "Kinder-Serie", "Mörchenfilm", "Trickfilm", "Zeichentrick-Serie", "Zeichentrick-Special", "Zeichentrickfilm"]
Shows = ["Clipshow", "Comedy Show", "Information", "Informationssendung", "Infotainment", "Kochshow", "Kulturmagazin", "Live Shopping", "Magazin", "Quizshow", "Show", "Sketch-Comedy", "Talk", "Talkshow", "Unterhaltung", "Unterhaltungs-Show", "Unterhaltungsshow"]
Sport = ["Sport", "Fuöball", "Bundesliga", "PL:", "Handball", "Champions-League", "Tennis", "Sportschau", "Sportmagazin", "Sportnachrichten", "Boxen", "Formel 1", "Wrestling", "Sportclub", "Blickpunkt Sport", "Golf"]

global active
active = False


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

	def __repr__(self):
		return '{%s}' % str(', '.join('%s : %s' % (k, repr(v)) for (k, v) in self.__dict__.keys()))


class AdvancedEventLibraryPlanerScreens(Screen):
	ALLOW_SUSPEND = True
	skin = loadSkin(skinpath + "AdvancedEventLibraryPlaners.xml")

	def __init__(self, session, viewType):
		global active
		active = True
		self.session = session
		Screen.__init__(self, session)
		self.title = "Prime-Time-Planer"
		self.viewType = viewType
		self.skinName = "AdvancedEventLibraryListPlaners" if self.viewType == 1 else "AdvancedEventLibraryWallPlaners"
		self.db = getDB()
		self.isinit = False
		self.lastidx = 0
		self.listlen = 0
		self.pageCount = 0
		self["key_red"] = StaticText("Beenden")
		self["key_green"] = StaticText("Timer hinzufügen")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("Umschalten")
		self["trailer"] = Pixmap()
		root = eServiceReference(str(service_types_tv + ' FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
		serviceHandler = eServiceCenter.getInstance()
		self.tvbouquets = serviceHandler.list(root).getContent("SN", True)
		self.userBouquets = []
		self.userBouquets.append('Alle Bouquets')
		for bouquet in self.tvbouquets:
			self.userBouquets.append(bouquet[1])
		self["Content"] = StaticText("")
		if self.viewType == 1:  # 'Listenansicht'
			self["eventList"] = AdvancedEventLibraryLists.EPGList()
			self["eventList"].connectsel_changed(self.sel_changed)
		else:
			self["eventWall"] = AdvancedEventLibraryLists.AELBaseWall()
			self["eventWall"].l.setBuildFunc(self.seteventEntry)
			self["ServiceRef"] = StaticText("")
			self["ServiceName"] = StaticText("")
			self['PageInfo'] = Label('')
			imgpath = variables.get("EventLibraryImagePath", '/usr/share/enigma2/AELImages/,').replace(',', '')
			self.shaper = LoadPixmap(imgpath + "shaper.png") if fileExists(imgpath + "shaper.png") else LoadPixmap('/usr/share/enigma2/AELImages/shaper.png')
		self["Event"] = Event()
		self["genreList"] = AdvancedEventLibraryLists.MenuList()
		self["genreList"].connectsel_changed(self.menu_sel_changed)
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
			'key_play': self.key_play_handler,
			"key_ok": self.key_ok_handler,
			"key_info": self.key_info_handler,
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

	def infoKeyPressed(self):
		try:
			if self.viewType == 1:  # 'Listenansicht'
				self.close('Wallansicht')
			else:
				self.close('Listenansicht')
		except Exception as ex:
			write_log(f"infoKeyPressed : {ex}")

	def key_menu_handler(self):
		self.session.openWithCallback(self.return_from_setup, MySetup)

	def return_from_setup(self):
		pass

	def key_ok_handler(self):
		if self.viewType == 1:  # 'Listenansicht'
			selection = self["eventList"].l.getCurrentSelection()[0]
			eventName = (selection[0], selection[2])
		else:
			selection = self["eventWall"].getcurrentselection()
			eventName = (selection.name, selection.eit)
		self.session.openWithCallback(self.CELcallBack, AdvancedEventLibrarySystem.Editor, eventname=eventName)

	def CELcallBack(self):
		selected_element = self["genreList"].l.getCurrentSelection()[0]
		if self.viewType == 1:  # 'Listenansicht'
			self["eventList"].setList(self.getEPGdata(selected_element[0]))
		else:
			self["eventWall"].setlist(self.getEPGdata(selected_element[0]))
			self["eventWall"].movetoIndex(0)
			self.pageCount = self['eventWall'].getPageCount()
			self['PageInfo'].setText('Seite ' + str(self['eventWall'].getCurrentPage()) + ' von ' + str(self.pageCount))
		self.sel_changed()

	def buildGenreList(self):
		imgpath = "/usr/share/enigma2/AELImages/"
		genreTypes = (["Filme", imgpath + "filme.png"], ["Serien", imgpath + "serien.png"], ["Dokus", imgpath + "dokus.png"], ["Kinder", imgpath + "kinder.png"], ["Shows", imgpath + "shows.png"], ["Sport", imgpath + "sport.png"], ["Music", imgpath + "music.png"], ["Sonstiges", imgpath + "sonstiges.png"])
		genrelist = []
		for genre in genreTypes:
			genrelist.append((genre,))
		self["genreList"].setList(genrelist)

	def refreshAll(self):
		if not self.isinit:
			if self.viewType != 1:  # 'Listenansicht'
				self.parameter = self["eventWall"].getParameter()
				self.imageType = str(self.parameter[3])
				self.substituteImage = str(self.parameter[5])
				self.FontOrientation = self.getFontOrientation(self.parameter[25])
				self.Coverings = eval(str(self.parameter[23]))
			imgpath = variables.get("EventLibraryImagePath", '/usr/share/enigma2/AELImages/,').replace(',', '')
			ptr = LoadPixmap(join(imgpath, "play.png"))
			self["trailer"].instance.setPixmap(ptr)
			self.isinit = True
			self.getAllEvents(currentBouquet=config.plugins.AdvancedEventLibrary.StartBouquet.value)
			self.menu_sel_changed(config.plugins.AdvancedEventLibrary.Genres.value)

	def key_red_handler(self):
		clearMem("Prime-Time-Planer")
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
			config.plugins.AdvancedEventLibrary.StartBouquet.value = ret[0]
			self.getAllEvents(ret[0])
			selected_element = self["genreList"].l.getCurrentSelection()[0]
			if self.viewType == 1:  # 'Listenansicht'
				self["eventList"].setList(self.getEPGdata(selected_element[0]))
			else:
				self["eventWall"].setlist(self.getEPGdata(selected_element[0]))
				self["eventWall"].movetoIndex(0)
				self.pageCount = self['eventWall'].getPageCount()
				self['PageInfo'].setText('Seite ' + str(self['eventWall'].getCurrentPage()) + ' von ' + str(self.pageCount))
			self.sel_changed()

	def key_blue_handler(self):
		if self.viewType == 1:  # 'Listenansicht'
			selected_element = self["eventList"].l.getCurrentSelection()[0]
			sRef = str(selected_element[1])
		else:
			selected_element = self["eventWall"].getcurrentselection()
			sRef = str(selected_element.serviceref)
		self.session.nav.playService(eServiceReference(sRef))
		self.close()

	def key_right_handler(self):
		if self.viewType == 1:  # 'Listenansicht'
			self['eventList'].pageDown()
		else:
			old_idx = int(self['eventWall'].getCurrentIndex())
			if old_idx == self.listlen - 1:
				self['eventWall'].movetoIndex(0)
			else:
				self['eventWall'].right()
				new_idx = int(self['eventWall'].getCurrentIndex())
				if new_idx <= old_idx:
					dest = 0 if (old_idx + 1) >= self.listlen else old_idx + 1
					self['eventWall'].movetoIndex(dest)
			self['eventWall'].refresh()
			self['PageInfo'].setText('Seite ' + str(self['eventWall'].getCurrentPage()) + ' von ' + str(self.pageCount))
			self.sel_changed()

	def key_left_handler(self):
		if self.viewType == 1:  # 'Listenansicht'
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
					dest = self.listlen - 1 if (new_idx - 1) < 0 else old_idx - 1
					self['eventWall'].movetoIndex(dest)
			self['eventWall'].refresh()
			self['PageInfo'].setText('Seite ' + str(self['eventWall'].getCurrentPage()) + ' von ' + str(self.pageCount))
			self.sel_changed()

	def key_down_handler(self):
		if self.viewType == 1:  # 'Listenansicht'
			self['eventList'].moveDown()
		else:
			old_idx = int(self['eventWall'].getCurrentIndex())
			if old_idx == self.listlen - 1:
				self['eventWall'].movetoIndex(0)
			else:
				self['eventWall'].down()
				new_idx = int(self['eventWall'].getCurrentIndex())
				if new_idx <= old_idx:
					print("debug self.parameter", self.parameter)
					print("debug new_idx", new_idx)
					print("debug old_idx", old_idx)
					print("debug self.listlen", self.listlen)
					dest = 0 if (new_idx + int(self.parameter[13])) >= self.listlen else new_idx + int(self.parameter[13])
					self['eventWall'].movetoIndex(dest)
					print("debug dest", dest)
					print("debug dest", type(dest))
			self['eventWall'].refresh()
			self['PageInfo'].setText(f"Seite {self['eventWall'].getCurrentPage()} von {self.pageCount}")
			self.sel_changed()

	def key_up_handler(self):
		if self.viewType == 1:  # 'Listenansicht'
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
					dest = self.listlen - 1 if (new_idx - self.parameter[14]) < 0 else new_idx - self.parameter[14]
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
			if self.viewType == 1:  # 'Listenansicht'
				selected_element = self["eventList"].l.getCurrentSelection()[0]
				if selected_element and selected_element[8]:
					sRef = eServiceReference(4097, 0, str(selected_element[8]))
					sRef.setName(str(selected_element[0]))
					self.session.open(MoviePlayer, sRef)
			else:
				selected_element = self["eventWall"].getcurrentselection()
				if selected_element and selected_element.hasTrailer:
					sRef = eServiceReference(4097, 0, str(selected_element.hasTrailer))
					sRef.setName(str(selected_element.name))
					self.session.open(MoviePlayer, sRef)
		except Exception as ex:
			write_log(f"key_play : {ex}")

	def key_info_handler(self):
		from Screens.EventView import EventViewSimple
		try:
			sRef = ""
			if self.viewType == 1:  # 'Listenansicht'
				selected_element = self["eventList"].l.getCurrentSelection()[0]
				sRef = str(selected_element[1])
			else:
				selected_element = self["eventWall"].getcurrentselection()
				sRef = str(selected_element.serviceref)

			if self.current_event and sRef:
				self.session.open(EventViewSimple, self.current_event, ServiceReference(sRef))
		except Exception as ex:
			write_log(f"call EventView : {ex}")

	def addtimer(self):
		try:
			if self.current_event is None:
				return False
			if self.viewType == 1:  # 'Listenansicht'
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
			timer.tags = ['AEL-Prime-Time-Planer']

			self.session.openWithCallback(self.finishedAdd, TimerEntry, timer)
		except Exception as ex:
			write_log(f"addtimer : {ex}")

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
			if self.viewType == 1:  # 'Listenansicht'
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
			if self.viewType == 1:  # 'Listenansicht'
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
			write_log(f"sel_changed : {ex}")
			self["Content"].setText("Keine Sendetermine im EPG gefunden\n" + str(ex))
			self["Event"].newEvent(None)

	def menu_sel_changed(self, what=None):
		try:
			if what:
				self['genreList'].moveToIndex(what)
			selected_element = self["genreList"].l.getCurrentSelection()[0]
			choices = {0: _("Filme"), 1: _("Serien"), 2: _("Dokus"), 3: _("Music"), 4: _("Kinder"), 5: _("Shows"), 6: _("Sport")}
			if self.viewType == 1:  # 'Listenansicht'
				self["eventList"].setList(self.getEPGdata(str(choices.get(selected_element[0]))))
				self["eventList"].moveToIndex(self.lastidx)
			else:
				self["eventWall"].movetoIndex(0)
				self["eventWall"].setlist(self.getEPGdata(str(choices.get(selected_element[0]))))
				self["eventWall"].refresh()
				self.pageCount = self['eventWall'].getPageCount()
				self['PageInfo'].setText('Seite ' + str(self['eventWall'].getCurrentPage()) + ' von ' + str(self.pageCount))
			self.sel_changed()
		except Exception as ex:
			self["Content"].setText("Keine Sendetermine im EPG gefunden")
			write_log(f"menu_sel_changed : {ex}")

	def getAllEvents(self, currentBouquet='Favourites'):
		try:
			self["key_yellow"].setText(currentBouquet)
			foundBouquet = False
			lines = []
			self.movielist = []
			self.doculist = []
			self.serieslist = []
			self.kidslist = []
			self.showslist = []
			self.sportslist = []
			self.musiclist = []
			self.unknownlist = []
			mask = (eServiceReference.isMarker | eServiceReference.isDirectory)
			root = eServiceReference(str(service_types_tv + ' FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
			serviceHandler = eServiceCenter.getInstance()
			self.tvbouquets = serviceHandler.list(root).getContent("SN", True)
			self.userBouquets = []
			self.userBouquets.append(('Alle Bouquets',))
			for bouquet in self.tvbouquets:
				self.userBouquets.append((bouquet[1],))
				if currentBouquet == bouquet[1]:
					foundBouquet = True
					root = eServiceReference(str(bouquet[0]))
					serviceHandler = eServiceCenter.getInstance()
					ret = serviceHandler.list(root).getContent("SN", True)

					for (serviceref, servicename) in ret:
						playable = not (eServiceReference(serviceref).flags & mask)
						if playable and "p%3a" not in serviceref and "<n/a>" not in servicename and servicename != ".":
							if not config.plugins.AdvancedEventLibrary.HDonly.value or "1:0:19:" in serviceref:
								line = [serviceref, servicename]
								if line not in lines:
									lines.append(line)

			if not foundBouquet:
				self["key_yellow"].setText('Alle Bouquets')
				for bouquet in self.tvbouquets:
					root = eServiceReference(str(bouquet[0]))
					serviceHandler = eServiceCenter.getInstance()
					ret = serviceHandler.list(root).getContent("SN", True)

					for (serviceref, servicename) in ret:
						playable = not (eServiceReference(serviceref).flags & mask)
						if playable and "p%3a" not in serviceref and "<n/a>" not in servicename and servicename != ".":
							if not config.plugins.AdvancedEventLibrary.HDonly.value or "1:0:19:" in serviceref:
								line = [serviceref, servicename]
								if line not in lines:
									lines.append(line)

			now = localtime()
			primetime = mktime((now.tm_year, now.tm_mon, now.tm_mday, config.plugins.AdvancedEventLibrary.StartTime.value[0], config.plugins.AdvancedEventLibrary.StartTime.value[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst))

			test = ['RITBDSEn']
			for line in lines:
				test.append((line[0], 0, primetime, config.plugins.AdvancedEventLibrary.Duration.value))

			epgcache = eEPGCache.getInstance()
			self.allevents = epgcache.lookupEvent(test) or []

			timers = []
			recordHandler = NavigationInstance.instance.RecordTimerRecordTimer
			for timer in recordHandler.timer_list:
				if timer and timer.service_ref:
					_timer = str(timer.name)
					_timer = _timer.strip().replace(".", "").replace(":", "").replace("-", "").replace("  ", " ").upper()
					timers.append(_timer)
				if timer and timer.eit:
					_timer = str(timer.eit)
					timers.append(_timer)

			for serviceref, eit, name, begin, duration, shortdesc, extdesc, service_name in self.allevents:
				if 'Sendepause' not in name and 'Sendeschluss' not in name:
					desc = None
					cleanname = name.strip().replace(".", "").replace(":", "").replace("-", "").replace("  ", " ").upper()
					hasTimer = False
					if cleanname in timers or str(eit) in timers:
						hasTimer = True

					desc = name + ' ' + shortdesc + ' ' + extdesc
					edesc = extdesc if extdesc and extdesc != '' else shortdesc
					eventGenre = self.getEventGenre(eit, serviceref, name, desc, begin)
					if eventGenre:
						hasTrailer = None
						evt = self.db.getliveTV(eit, name, begin)
						if evt and evt[0][16].endswith('mp4'):
							hasTrailer = evt[0][16]
						if hasTrailer is None:
							dbdata = self.db.getTitleInfo(convert2base64(name))
							if dbdata and dbdata[7].endswith('mp4'):
								hasTrailer = dbdata[7]
						if self.viewType == 1:  # 'Listenansicht'
							itm = [name, serviceref, eit, begin, duration, hasTimer, edesc, service_name, hasTrailer]
						else:
							image = None
							if self.imageType == "cover" and evt and evt[0][3] != '':
								image = getImageFile(aelGlobals.HDDPATH + self.imageType + '/', evt[0][3])
							if image is None:
								image = getImageFile(aelGlobals.HDDPATH + self.imageType + '/', name)
							itm = EventEntry(name, serviceref, eit, begin, duration, hasTimer, edesc, service_name, image, hasTrailer)
						if 'Spielfilm' in eventGenre:
							self.movielist.append((itm,))
						elif 'Reportage' in eventGenre:
							self.doculist.append((itm,))
						elif 'Serien' in eventGenre:
							self.serieslist.append((itm,))
						elif 'Kinder' in eventGenre:
							self.kidslist.append((itm,))
						elif 'Unterhaltung' in eventGenre:
							self.showslist.append((itm,))
						elif 'Sport' in eventGenre:
							self.sportslist.append((itm,))
						elif 'Music' in eventGenre:
							self.musiclist.append((itm,))
						elif 'Sonstiges' in eventGenre:
							self.unknownlist.append((itm,))

			if self.viewType == 1:  # 'Listenansicht'
				itm = ['habe leider keine Sendungen zum Genre gefunden', '0', -1, 0, 0, False, '', '', None]
			else:
				itm = EventEntry('habe leider keine Sendungen zum Genre gefunden', None, -1, 0, 0, False, '', '', imgpath + "substituteImage.jpg", None)
			if not self.movielist:
				self.movielist.append((itm,))
			if not self.doculist:
				self.doculist.append((itm,))
			if not self.musiclist:
				self.musiclist.append((itm,))
			if not self.showslist:
				self.showslist.append((itm,))
			if not self.kidslist:
				self.kidslist.append((itm,))
			if not self.serieslist:
				self.serieslist.append((itm,))
			if not self.sportslist:
				self.sportslist.append((itm,))
			if not self.unknownlist:
				self.unknownlist.append((itm,))
		except Exception as ex:
			write_log(f"getAllEvents : {ex}")

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

	def getEPGdata(self, what="Filme"):
		try:
			if what == 'Filme':
				cList = self.movielist
			elif what == 'Dokus':
				cList = self.doculist
			elif what == 'Music':
				cList = self.musiclist
			elif what == 'Shows':
				cList = self.showslist
			elif what == 'Kinder':
				cList = self.kidslist
			elif what == 'Serien':
				cList = self.serieslist
			elif what == 'Sport':
				cList = self.sportslist
			elif what == 'Sonstiges':
				cList = self.unknownlist
			else:
				self.listlen = 0
				return []
			self.listlen = len(cList)
			return cList
		except Exception as ex:
			write_log(f"getEPGdata : {ex}")

	def getEventGenre(self, eit, serviceref, name, desc, begin):
		try:
			val = self.db.getliveTV(eit, name, begin)
			if val and len(str(val[0][11]).strip()) > 0:
				return str(val[0][11]).strip()
			eventName = convertDateInFileName(convertSearchName(name))
			dbData = self.db.getTitleInfo(convert2base64(eventName))
			if not dbData:
				dbData = self.db.getTitleInfo(convert2base64(convertTitle(eventName)))
				if not dbData:
					dbData = self.db.getTitleInfo(convert2base64(convertTitle2(eventName)))
			if dbData and len(dbData[2]) > 0:
				if 'Serie' in str(dbData[2]):
					if 'Dokumentation' in str(dbData[2]) or 'Documentary' in str(dbData[2]):
						return 'Reportage'
					elif 'Kinder' in str(dbData[2]) or 'Children' in str(dbData[2]):
						return 'Kinder'
					elif 'Talk' in str(dbData[2]) or 'Show' in str(dbData[2]):
						return 'Unterhaltung'
					elif 'Music' in str(dbData[2]) or 'Musik' in str(dbData[2]):
						return 'Music'
					elif 'Sport' in str(dbData[2]):
						return 'Sport'
					else:
						return 'Serien'
				genres = dbData[2].split()
				if genres:
					for genre in genres:
						for items in [(Dokus, 'Reportage'), (Sport, 'Sport'), (Music, 'Music'), (Kinder, 'Kinder'), (Shows, 'Unterhaltung'), (Movies, 'Spielfilm'), (Series, 'Serien')]:
							if str(genre).strip() in map(lambda x: x.strip(), items[0]):
								return items[1]
			for item in ["Folge", "Staffel", "Episode", "Soap", "Reihe", "Serie"]:
				if item in desc:
					return "Serien"
			if "film" in desc:
				return 'Spielfilm'
			for items in [(Dokus, 'Reportage'), (Sport, 'Sport'), (Music, 'Music'), (Kinder, 'Kinder'), (Shows, 'Unterhaltung'), (Movies, 'Spielfilm'), (Series, 'Serien')]:
				for genre in items[0]:
					if genre in desc:
						return items[1]
			return 'Sonstiges'
		except Exception as ex:
			write_log(f"getEventGenre : {name} - {ex}")
			return 'Sonstiges'

	def seteventEntry(self, entrys):
		try:
			picon = None
			image = None
			pic = self.findPicon(entrys.serviceref, entrys.sname)
			maxLength = self.parameter[2]
			if len(entrys.sname) > maxLength:
				entrys.sname = str(entrys.sname)[:maxLength] + '...'
			name = str(entrys.name)[:maxLength] + '...' if len(entrys.name) > maxLength else str(entrys.name)
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
			if image:
				ret.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.parameter[17][0], self.parameter[17][1], self.parameter[17][0], self.parameter[17][1], self.parameter[17][2], self.parameter[17][3], self.parameter[17][2], self.parameter[17][3], image, None, None, BT_SCALE))
			for covering in self.Coverings:
				ret.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, covering[0], covering[1], covering[0], covering[1], covering[2], covering[3], covering[2], covering[3], self.shaper, None, None, BT_SCALE))
			if picon:
				ret.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.parameter[21][0], self.parameter[21][1], self.parameter[21][0], self.parameter[21][1], self.parameter[21][2], self.parameter[21][3], self.parameter[21][2], self.parameter[21][3], picon, None, None, BT_SCALE))
			if entrys.hasTimer and fileExists(self.parameter[15]):
				ret.append((eListboxPythonMultiContent.TYPE_TEXT, self.parameter[19][0] + self.parameter[19][4], self.parameter[19][1], self.parameter[19][0] + self.parameter[19][4], self.parameter[19][1], self.parameter[19][2], self.parameter[19][3], self.parameter[19][2], self.parameter[19][3], self.parameter[19][5], self.parameter[19][5], self.FontOrientation, entrys.sname, parseColor(self.parameter[6]).argb(), parseColor(self.parameter[7]).argb()))
				ret.append((eListboxPythonMultiContent.TYPE_TEXT, self.parameter[20][0] + self.parameter[20][4], self.parameter[20][1], self.parameter[20][0] + self.parameter[20][4], self.parameter[20][1], self.parameter[20][2], self.parameter[20][3], self.parameter[20][2], self.parameter[20][3], self.parameter[20][5], self.parameter[20][5], self.FontOrientation, name, parseColor(self.parameter[6]).argb(), parseColor(self.parameter[7]).argb()))
				ret.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.parameter[18][0], self.parameter[18][1], self.parameter[18][0], self.parameter[18][1], self.parameter[18][2], self.parameter[18][3], self.parameter[18][2], self.parameter[18][3], LoadPixmap(self.parameter[15]), None, None, BT_SCALE))
			else:
				ret.append((eListboxPythonMultiContent.TYPE_TEXT, self.parameter[19][0], self.parameter[19][1], self.parameter[19][0], self.parameter[19][1], self.parameter[19][2], self.parameter[19][3], self.parameter[19][2], self.parameter[19][3], self.parameter[19][5], self.parameter[19][5], self.FontOrientation, entrys.sname, parseColor(self.parameter[6]).argb(), parseColor(self.parameter[7]).argb()))
				ret.append((eListboxPythonMultiContent.TYPE_TEXT, self.parameter[20][0], self.parameter[20][1], self.parameter[20][0], self.parameter[20][1], self.parameter[20][2], self.parameter[20][3], self.parameter[20][2], self.parameter[20][3], self.parameter[20][5], self.parameter[20][5], self.FontOrientation, name, parseColor(self.parameter[6]).argb(), parseColor(self.parameter[7]).argb()))
			return ret
			write_log(f"error in entrys : {entrys}")
			return [entrys,
								(eListboxPythonMultiContent.TYPE_TEXT, 2, 2, 2, 2, 96, 96, 96, 96, 0, 0, RT_WRAP | RT_HALIGN_CENTER | RT_VALIGN_CENTER, 'Das war wohl nix', parseColor(self.parameter[6]).argb(), parseColor(self.parameter[7]).argb()),
								]
		except Exception as ex:
			write_log(f"Error in seteventEntry : {ex}")
			return [entrys,
								(eListboxPythonMultiContent.TYPE_TEXT, 2, 2, 2, 2, 96, 96, 96, 96, 0, 0, RT_WRAP | RT_HALIGN_CENTER | RT_VALIGN_CENTER, 'habe leider keine Sendungen zum Genre gefunden', parseColor(self.parameter[6]).argb(), parseColor(self.parameter[7]).argb()),
								]

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

####################################################################################


class MySetup(Setup):
	def __init__(self, session):
		self.session = session
		Setup.__init__(self, session, "PrimeTime-Planer-Setup", plugin="Extensions/AdvancedEventLibrary", PluginLanguageDomain="AdvancedEventLibrary")
		root = eServiceReference(str(service_types_tv + ' FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
		serviceHandler = eServiceCenter.getInstance()
		self.tvbouquets = serviceHandler.list(root).getContent("SN", True)
		self.userBouquets = []
		self.userBouquets.append('Alle Bouquets')
		for bouquet in self.tvbouquets:
			self.userBouquets.append(bouquet[1])
		self["entryActions"] = HelpableActionMap(self, ["ColorActions"],
														{
														"green": (self.do_close, _("save")),
														"yellow": (self.key_yellow_handler, _("TVS-Setup"))
														}, prio=0, description=_("Advanced-Event-Library-Setup"))

	def changedEntry(self):  # TODO: kann man bestimmt besser machen
#		self.buildConfigList()
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
