# coding=utf-8
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.Standby import TryQuitMainloop
from Screens.InfoBar import MoviePlayer
from Screens.LocationBox import MovieLocationBox
from Screens.TaskList import TaskListScreen
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Sources.StaticText import StaticText
from Components.Sources.ServiceEvent import ServiceEvent
from Components.FileTransfer import FileTransferJob
from Components.Task import job_manager
from time import time, localtime
from enigma import iServiceInformation, eServiceReference, eServiceCenter, ePixmap
from ServiceReference import ServiceReference
from enigma import eTimer, ePicLoad, eLabel, eWall, eWallPythonMultiContent, eListboxPythonMultiContent, gFont, eRect, eSize, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_VALIGN_BOTTOM, RT_WRAP, BT_SCALE, BT_FIXRATIO, eWidget, fontRenderClass, ePoint
from Components.ConfigList import ConfigListScreen, getSelectionChoices
from Components.config import getConfigListEntry, ConfigYesNo, ConfigText, ConfigNumber, ConfigSelection, config, ConfigSubsection, ConfigInteger, configfile, fileExists, ConfigDescription
from glob import glob
import .AdvancedEventLibrarySystem
from Tools.AdvancedEventLibrary import getPictureDir, getImageFile, setStatus, clearMem, getDB, convert2base64
from .AdvancedEventLibraryLists import AELBaseWall, MovieList
from Tools.LoadPixmap import LoadPixmap
from thread import start_new_thread
import datetime
import os
import re
import skin
import struct
import shutil
import linecache
import cPickle as pickle

pluginpath = '/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/'
skinpath = pluginpath + 'skin/'
imgpath = '/usr/share/enigma2/AELImages/'
log = "/var/tmp/AdvancedEventLibrary.log"

global active
active = False
global saving
saving = False

isTMDb = False
if os.path.isfile('/usr/lib/enigma2/python/Plugins/Extensions/tmdb/plugin.pyo'):
	from Plugins.Extensions.tmdb import tmdb
	isTMDb = True


class MovieEntry():
	def __init__(self, filename, date, name, service, image, isFolder, progress, desc, trailer="", mlen=0):
		self.filename = filename
		self.name = name
		self.date = date
		self.service = service
		self.image = image
		self.isFolder = isFolder
		self.progress = progress
		self.desc = desc
		self.trailer = trailer
		self.mlen = mlen

	def __setitem__(self, item, value):
		if item == "progress":
			self.progress = value
		elif item == "image":
			self.image = value

	def __repr__(self):
		return '{%s}' % str(', '.join('%s : %s' % (k, repr(v)) for (k, v) in self.__dict__.iteritems()))


def write_log(svalue, logging=True):
	if logging:
		t = localtime()
		logtime = '%02d:%02d:%02d' % (t.tm_hour, t.tm_min, t.tm_sec)
		AEL_log = open(log, "a")
		AEL_log.write(str(logtime) + " : [AdvancedEventLibrarySimpleMovieWall] - " + str(svalue) + "\n")
		AEL_log.close()


def loadskin(filename):
	path = skinpath + filename
	with open(path, "r") as f:
		skin = f.read()
		f.close()
	return skin


class AdvancedEventLibrarySimpleMovieWall(Screen):
	ALLOW_SUSPEND = True
	skin = skin.loadSkin(skinpath + "AdvancedEventLibraryMovieLists.xml")

	def __init__(self, session, viewType="Wallansicht"):
		global active
		active = True
		self.session = session
		Screen.__init__(self, session)
		self.viewType = viewType
		if self.viewType == 'Listenansicht':
			self.title = "Simple-Movie-List"
			self.skinName = "Advanced-Event-Library-MovieList"
		else:
			self.title = "Simple-Movie-Wall"
			self.skinName = "Advanced-Event-Library-MovieWall"
		self.isinit = False
		self.lastFolder = []
		self.listlen = 0
		self.pageCount = 0

		config.plugins.AdvancedEventLibrary = ConfigSubsection()
		self.showProgress = config.plugins.AdvancedEventLibrary.Progress = ConfigYesNo(default=True)
		self.startPath = config.plugins.AdvancedEventLibrary.StartPath = ConfigText(default="None")
		sortType = config.plugins.AdvancedEventLibrary.SortType = ConfigSelection(default="Datum absteigend", choices=["Datum absteigend", "Datum aufsteigend", "Name aufsteigend", "Name absteigend"])
		if sortType.value == "Datum absteigend":
			self.sortType = 0
		elif sortType.value == "Datum aufsteigend":
			self.sortType = 1
		elif sortType.value == "Name aufsteigend":
			self.sortType = 2
		elif sortType.value == "Name absteigend":
			self.sortType = 3
		self.oldSortOrder = sortType.value

		self["key_red"] = StaticText("Beenden")
		self["key_green"] = StaticText("Advanced-Event-Library")
		if isTMDb:
			self["key_yellow"] = StaticText("TMDb Infos...")
		else:
			self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText(str(sortType.value))

		self['NaviInfo'] = Label('')

		if self.viewType == 'Listenansicht':
			self["movielist"] = MovieList()
			self["movielist"].l.setBuildFunc(self.setMovieEntry)
			self["movielist"].connectsel_changed(self.sel_changed)
		else:
			self['PageInfo'] = Label('')
			self['moviewall'] = AELBaseWall()
			self["moviewall"].l.setBuildFunc(self.setMovieEntry)
			self.shaper = LoadPixmap('/usr/share/enigma2/AELImages/shaper.png')

		self["trailer"] = Pixmap()
		self["Service"] = ServiceEvent()

		self["myActionMap"] = ActionMap(["AdvancedEventLibraryActions"],
		{
			"key_red": self.go_close,
			"key_green": self.key_green_handler,
			"key_yellow": self.key_yellow_handler,
			"key_blue": self.key_blue_handler,
			"key_cancel": self.go_close,
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

		self.scrambledVideoList = []
		if fileExists("/etc/enigma2/.scrambled_video_list"):
			with open("/etc/enigma2/.scrambled_video_list", "r") as scrambledFiles:
				for line in scrambledFiles:
					self.scrambledVideoList.append(line.replace('\n', ''))

		self.refresh = False
		self.progressTimer = eTimer()
		self.progressTimer.callback.append(self.progressUpdate)
		self.progressTimer.start(2000, True)
		self.onShow.append(self.refreshAll)

	def infoKeyPressed(self):
		try:
			if self.viewType == 'Listenansicht':
				self.close('Wallansicht')
			else:
				self.close('Listenansicht')
		except Exception as ex:
			write_log('infoKeyPressed : ' + str(ex))

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

	def getList(self, goToFolder=None, createUpdate=False):
		if self.viewType == 'Wallansicht':
			self.parameter = self['moviewall'].getParameter()
		else:
			self.parameter = self['movielist'].getParameter()
		self.imageType = str(self.parameter[3])
		self.folderImage = str(self.parameter[4])
		self.scrambledImage = LoadPixmap(self.parameter[16])
		self.recordImage = LoadPixmap(self.parameter[15])
		self.fontOrientation = self.getFontOrientation(self.parameter[25])
		if fileExists(str(self.folderImage).replace('.jpg', '.png')):
			self.tfolderImage = LoadPixmap(str(self.folderImage).replace('.jpg', '.png'))
		else:
			self.tfolderImage = LoadPixmap(self.folderImage)
		self.substituteImage = str(self.parameter[5])

		if createUpdate or not fileExists(os.path.join(pluginpath, 'moviewall.data')):
			saveList(self.imageType)
		self.moviedict = self.load_pickle(os.path.join(pluginpath, 'moviewall.data'))

		for k in self.moviedict:
			for v in self.moviedict[k]:
				self.currentFolder = [k, v]
				break
			break

		if goToFolder is None:
			if self.startPath.value != "None":
				for k, v in self.moviedict.items():
					for ik, iv in v.items():
						if str(ik) == str(self.startPath.value):
							self.currentFolder = [k, ik]
							break
		else:
			self.currentFolder = goToFolder

	def save_pickle(self, data, filename):
		write_log('save data : ' + str(filename))
		with open(filename, 'wb') as f:
			pickle.dump(data, f)

	def load_pickle(self, filename):
		write_log('load : ' + str(filename))
		with open(filename, 'rb') as f:
			data = pickle.load(f)
		return data

	def getMovieList(self, sorttype=0):
		currentList = []
		hasElements = False
		try:
			if self.currentFolder[0] == "root":
				for k in self.moviedict:
					img = getImageFile(getPictureDir() + self.imageType + '/', k.split('/')[-1])
					if not img:
						img = self.folderImage
					itm = MovieEntry([k, k], 0, k.split('/')[-1] + '...', eServiceReference('2:0:1:0:0:0:0:0:0:0:' + k.split('/')[-1] + '/'), img, True, 0, "")
					hasElements = True
					if not itm in currentList:
						currentList.append((itm,))
			else:
				if 'parent' in self.moviedict[self.currentFolder[0]][self.currentFolder[1]]:
					if self.moviedict[self.currentFolder[0]][self.currentFolder[1]]['parent'] != self.currentFolder[1]:
						img = getImageFile(getPictureDir() + self.imageType + '/', self.moviedict[self.currentFolder[0]][self.currentFolder[1]]['parent'].split('/')[-1])
						if not img:
							img = self.folderImage
						itm = MovieEntry([self.currentFolder[0], self.moviedict[self.currentFolder[0]][self.currentFolder[1]]['parent']], 0, '...', eServiceReference('2:0:1:0:0:0:0:0:0:0:' + self.moviedict[self.currentFolder[0]][self.currentFolder[1]]['parent'].split('/')[-1] + '/'), img, True, 0, "")
						hasElements = True
						if not itm in currentList:
							currentList.append((itm,))
					else:
						for k in self.moviedict:
							if self.moviedict[self.currentFolder[0]][self.currentFolder[1]]['parent'] != k:
								img = self.folderImage
								itm = MovieEntry(["root", ""], 0, '...', eServiceReference('2:0:1:0:0:0:0:0:0:0:' + k.split('/')[-1] + '/'), img, True, 0, "")
								currentList.append((itm,))
								hasElements = True
								break

				if 'directories' in self.moviedict[self.currentFolder[0]][self.currentFolder[1]]:
					folderlist = self.moviedict[self.currentFolder[0]][self.currentFolder[1]]['directories']
					folderlist.sort()
					for path in folderlist:
						if self.currentFolder[1] + '/' + path in self.moviedict[self.currentFolder[0]]:
							img = getImageFile(getPictureDir() + self.imageType + '/', path)
							if not img:
								img = self.folderImage
							itm = MovieEntry([self.currentFolder[0], self.currentFolder[1] + '/' + path], 0, path + '...', eServiceReference('2:0:1:0:0:0:0:0:0:0:' + self.currentFolder[1] + '/' + path + '/'), img, True, 0, "")
							hasElements = True
							if not itm in currentList:
								currentList.append((itm,))

				if 'files' in self.moviedict[self.currentFolder[0]][self.currentFolder[1]]:
					self.movielist = self.moviedict[self.currentFolder[0]][self.currentFolder[1]]['files']

				if self.movielist:
					if sorttype != 2:
						foundEpisodes = False
						for entry in self.movielist:
							if self.findEpisode(entry[2]):
								sorttype = 2
								self["key_blue"].setText("Name aufsteigend")
								foundEpisodes = True
								break
						if not foundEpisodes:
							self["key_blue"].setText(str(self.oldSortOrder))
					hasElements = True
					if sorttype == 0:
						self.movielist.sort(key=lambda x: x[1], reverse=True)
					elif sorttype == 1:
						self.movielist.sort(key=lambda x: x[1], reverse=False)
					elif sorttype == 2:
						self.movielist.sort(key=lambda x: x[2].lower(), reverse=False)
					elif sorttype == 3:
						self.movielist.sort(key=lambda x: x[2].lower(), reverse=True)
					elif sorttype == 4:
						self.movielist.sort(key=lambda x: x[6].lower(), reverse=False)
					elif sorttype == 5:
						self.movielist.sort(key=lambda x: x[6].lower(), reverse=True)
					for item in self.movielist:
						if str(item[5]) == 'None':
							image = self.substituteImage
						else:
							image = item[5]
						if len(item) > 7:
							if self.showProgress.value:
								itm = MovieEntry(item[0], item[1], item[2], eServiceReference(item[3]), image, False, self.getProgress(item[0], item[4]), item[6], item[7], item[4])
							else:
								itm = MovieEntry(item[0], item[1], item[2], eServiceReference(item[3]), image, False, 0, item[6], item[7], item[4])
						else:
							if self.showProgress.value:
								itm = MovieEntry(item[0], item[1], item[2], eServiceReference(item[3]), image, False, self.getProgress(item[0], item[4]), item[6])
							else:
								itm = MovieEntry(item[0], item[1], item[2], eServiceReference(item[3]), image, False, 0, item[6])
						currentList.append((itm,))
					del self.movielist
		except Exception as ex:
			if self.lastFolder:
				itm = MovieEntry([self.lastFolder[0], self.lastFolder[1]], 0, 'Error...', eServiceReference('1:0:0:0:0:0:0:0:0:0:' + self.lastFolder[1].split('/')[-1]), self.folderImage, True, 0, "")
				currentList.append((itm,))
			write_log("getMovieList : " + str(ex))
		try:
			if hasElements:
				self.listlen = len(currentList)
				if self.viewType == 'Wallansicht':
					self["moviewall"].setlist(currentList)
					self["moviewall"].movetoIndex(0)
					self.pageCount = self['moviewall'].getPageCount()
					self['PageInfo'].setText('Seite ' + str(self['moviewall'].getCurrentPage()) + ' von ' + str(self.pageCount))
				else:
					self["movielist"].setList(currentList)
				self.lastFolder = self.currentFolder
				del currentList
		except Exception as ex:
			write_log("getMovieList : " + str(ex))

	def findEpisode(self, title):
		try:
			regexfinder = re.compile('[Ss]\d{2}[Ee]\d{2}', re.MULTILINE | re.DOTALL)
			ex = regexfinder.findall(str(title))
			if ex:
				return True
			return False
		except:
			return False

	def setMovieEntry(self, entrys):
		try:
			maxLength = self.parameter[2]
			textHeight = int(self.parameter[8])
			textBegin = 100 - textHeight
			if len(entrys.name) > maxLength:
				name = str(entrys.name)[:maxLength] + '...'
			else:
				name = entrys.name
			if len(entrys.desc) > maxLength:
				entrys.desc = str(entrys.desc)[:maxLength] + '...'
			self.picloader = PicLoader(int(self.parameter[0]), int(self.parameter[1]))
			image = self.picloader.load(entrys.image)
			self.picloader.destroy()
			if not entrys.isFolder:
				scrambled_or_rec = None
				if fileExists(entrys.filename + '.rec'):
					scrambled_or_rec = self.recordImage
				if fileExists(entrys.filename + '.meta'):
					if linecache.getline(entrys.filename + '.meta', 9).replace("\n", "").strip() == '1' or entrys.filename in self.scrambledVideoList:
						scrambled_or_rec = self.scrambledImage
				elif entrys.filename in self.scrambledVideoList:
					scrambled_or_rec = self.scrambledImage

			if self.viewType == 'Wallansicht':
				if entrys.isFolder and entrys.image != self.folderImage:
					return [entrys,
										(eWallPythonMultiContent.TYPE_PIXMAP, eWallPythonMultiContent.SHOW_ALWAYS, 0, 0, 0, 0, 100, 100, 100, 100, image, None, None, BT_SCALE),
										(eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, 0, 0, 0, 0, 18, 20, 18, 20, self.tfolderImage, None, None, BT_SCALE),
										(eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, 0, textBegin, 0, textBegin, 100, textHeight, 100, textHeight, self.shaper, None, None, BT_SCALE),
										(eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, 2, textBegin, 2, textBegin, 96, textHeight, 96, textHeight, 0, 0, self.fontOrientation, name, skin.parseColor(self.parameter[6]).argb(), skin.parseColor(self.parameter[7]).argb()),
										]
				else:
					if entrys.isFolder:
						return [entrys,
											(eWallPythonMultiContent.TYPE_PIXMAP, eWallPythonMultiContent.SHOW_ALWAYS, 0, 0, 0, 0, 100, 100, 100, 100, image, None, None, BT_SCALE),
											(eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, 0, textBegin, 0, textBegin, 100, textHeight, 100, textHeight, self.shaper, None, None, BT_SCALE),
											(eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, 2, textBegin, 2, textBegin, 96, textHeight, 96, textHeight, 0, 0, self.fontOrientation, name, skin.parseColor(self.parameter[6]).argb(), skin.parseColor(self.parameter[7]).argb()),
											]
					else:
						if self.showProgress.value:
							if scrambled_or_rec:
								return [entrys,
													(eWallPythonMultiContent.TYPE_PIXMAP, eWallPythonMultiContent.SHOW_ALWAYS, 0, 0, 0, 0, 100, 100, 100, 100, image, None, None, BT_SCALE),
													(eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.parameter[18][0], self.parameter[18][1], self.parameter[18][0], self.parameter[18][1], self.parameter[18][2], self.parameter[18][3], self.parameter[18][2], self.parameter[18][3], scrambled_or_rec, None, None, BT_SCALE),
													(eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, 0, textBegin - 3, 0, textBegin - 3, 100, textHeight, 100, textHeight, self.shaper, None, None, BT_SCALE),
													(eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, 2, textBegin - 3, 2, textBegin - 3, 96, textHeight, 96, textHeight, 0, 0, self.fontOrientation, name, skin.parseColor(self.parameter[6]).argb(), skin.parseColor(self.parameter[7]).argb()),
													(eWallPythonMultiContent.TYPE_PROGRESS, eWallPythonMultiContent.SHOW_ALWAYS, 0, 97, 0, 97, 100, 3, 100, 3, entrys.progress, self.parameter[13], skin.parseColor(self.parameter[9]).argb(), skin.parseColor(self.parameter[11]).argb(), skin.parseColor(self.parameter[10]).argb(), skin.parseColor(self.parameter[12]).argb()),
													]
							else:
								return [entrys,
													(eWallPythonMultiContent.TYPE_PIXMAP, eWallPythonMultiContent.SHOW_ALWAYS, 0, 0, 0, 0, 100, 100, 100, 100, image, None, None, BT_SCALE),
													(eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, 0, textBegin - 3, 0, textBegin - 3, 100, textHeight, 100, textHeight, self.shaper, None, None, BT_SCALE),
													(eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, 2, textBegin - 3, 2, textBegin - 3, 96, textHeight, 96, textHeight, 0, 0, self.fontOrientation, name, skin.parseColor(self.parameter[6]).argb(), skin.parseColor(self.parameter[7]).argb()),
													(eWallPythonMultiContent.TYPE_PROGRESS, eWallPythonMultiContent.SHOW_ALWAYS, 0, 97, 0, 97, 100, 3, 100, 3, entrys.progress, self.parameter[13], skin.parseColor(self.parameter[9]).argb(), skin.parseColor(self.parameter[11]).argb(), skin.parseColor(self.parameter[10]).argb(), skin.parseColor(self.parameter[12]).argb()),
													]
						else:
							if scrambled_or_rec:
								return [entrys,
													(eWallPythonMultiContent.TYPE_PIXMAP, eWallPythonMultiContent.SHOW_ALWAYS, 0, 0, 0, 0, 100, 100, 100, 100, image, None, None, BT_SCALE),
													(eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, self.parameter[18][0], self.parameter[18][1], self.parameter[18][0], self.parameter[18][1], self.parameter[18][2], self.parameter[18][3], self.parameter[18][2], self.parameter[18][3], scrambled_or_rec, None, None, BT_SCALE),
													(eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, 0, textBegin, 0, textBegin, 100, textHeight, 100, textHeight, self.shaper, None, None, BT_SCALE),
													(eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, 2, textBegin, 2, textBegin, 96, textHeight, 96, textHeight, 0, 0, self.fontOrientation, name, skin.parseColor(self.parameter[6]).argb(), skin.parseColor(self.parameter[7]).argb()),
													]
							else:
								return [entrys,
													(eWallPythonMultiContent.TYPE_PIXMAP, eWallPythonMultiContent.SHOW_ALWAYS, 0, 0, 0, 0, 100, 100, 100, 100, image, None, None, BT_SCALE),
													(eWallPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, eWallPythonMultiContent.SHOW_ALWAYS, 0, textBegin, 0, textBegin, 100, textHeight, 100, textHeight, self.shaper, None, None, BT_SCALE),
													(eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, 2, textBegin, 2, textBegin, 96, textHeight, 96, textHeight, 0, 0, self.fontOrientation, name, skin.parseColor(self.parameter[6]).argb(), skin.parseColor(self.parameter[7]).argb()),
													]
				write_log("error in entrys : " + str(entrys))
				return [entrys,
									(eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, 2, 2, 2, 2, 96, 96, 96, 96, 0, 0, self.fontOrientation, 'Das war wohl nix', skin.parseColor(self.parameter[6]).argb(), skin.parseColor(self.parameter[7]).argb()),
									]
			else:
				width = self["movielist"].l.getItemSize().width()
				height = self["movielist"].l.getItemSize().height()
				res = [None]
				if entrys.isFolder:
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.parameter[19][0], self.parameter[19][1], self.parameter[19][2], self.parameter[19][3], image, None, None, BT_SCALE))
					res.append((eListboxPythonMultiContent.TYPE_TEXT, self.parameter[20][0], 0, (width - self.parameter[20][0] - 20), height, self.parameter[20][5], RT_HALIGN_LEFT | RT_VALIGN_CENTER, name, skin.parseColor(self.parameter[24]).argb(), skin.parseColor(self.parameter[25]).argb()))
				else:
					timeobj = datetime.datetime.fromtimestamp(entrys.date)
					_time = timeobj.strftime(self.parameter[23])
					_time = _time + '  ' + str(int(entrys.mlen / 60)) + ' Min.'
					if self.showProgress.value:
						if scrambled_or_rec:
							res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.parameter[19][0], self.parameter[19][1], self.parameter[19][2], self.parameter[19][3], image, None, None, BT_SCALE))
							res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.parameter[22][0], self.parameter[22][1], self.parameter[22][2], self.parameter[22][3], scrambled_or_rec, None, None, BT_SCALE))
							res.append((eListboxPythonMultiContent.TYPE_TEXT, (self.parameter[20][0] + self.parameter[20][4]), self.parameter[20][1], self.parameter[20][2], self.parameter[20][3], self.parameter[20][5], RT_HALIGN_LEFT | RT_VALIGN_CENTER, name, skin.parseColor(self.parameter[24]).argb(), skin.parseColor(self.parameter[25]).argb()))
							res.append((eListboxPythonMultiContent.TYPE_PROGRESS, (self.parameter[17][0] + self.parameter[17][4]), self.parameter[17][1], self.parameter[17][2], self.parameter[17][3], entrys.progress, self.parameter[13], skin.parseColor(self.parameter[9]).argb(), skin.parseColor(self.parameter[11]).argb(), skin.parseColor(self.parameter[10]).argb(), skin.parseColor(self.parameter[12]).argb()))
							res.append((eListboxPythonMultiContent.TYPE_TEXT, (self.parameter[21][0] + self.parameter[21][4]), self.parameter[21][1], self.parameter[21][2], self.parameter[21][3], self.parameter[21][5], RT_HALIGN_LEFT | RT_VALIGN_CENTER, entrys.desc, skin.parseColor(self.parameter[26]).argb(), skin.parseColor(self.parameter[27]).argb()))
							res.append((eListboxPythonMultiContent.TYPE_TEXT, (self.parameter[18][0] + self.parameter[18][4]), self.parameter[18][1], self.parameter[18][2], self.parameter[18][3], self.parameter[18][5], RT_HALIGN_RIGHT | RT_VALIGN_CENTER, self.correctweekdays(_time), skin.parseColor(self.parameter[28]).argb(), skin.parseColor(self.parameter[29]).argb()))
						else:
							res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.parameter[19][0], self.parameter[19][1], self.parameter[19][2], self.parameter[19][3], image, None, None, BT_SCALE))
							res.append((eListboxPythonMultiContent.TYPE_TEXT, self.parameter[20][0], self.parameter[20][1], self.parameter[20][2], self.parameter[20][3], self.parameter[20][5], RT_HALIGN_LEFT | RT_VALIGN_CENTER, name, skin.parseColor(self.parameter[24]).argb(), skin.parseColor(self.parameter[25]).argb()))
							res.append((eListboxPythonMultiContent.TYPE_PROGRESS, self.parameter[17][0], self.parameter[17][1], self.parameter[17][2], self.parameter[17][3], entrys.progress, self.parameter[13], skin.parseColor(self.parameter[9]).argb(), skin.parseColor(self.parameter[11]).argb(), skin.parseColor(self.parameter[10]).argb(), skin.parseColor(self.parameter[12]).argb()))
							res.append((eListboxPythonMultiContent.TYPE_TEXT, self.parameter[21][0], self.parameter[21][1], self.parameter[21][2], self.parameter[21][3], self.parameter[21][5], RT_HALIGN_LEFT | RT_VALIGN_CENTER, entrys.desc, skin.parseColor(self.parameter[26]).argb(), skin.parseColor(self.parameter[27]).argb()))
							res.append((eListboxPythonMultiContent.TYPE_TEXT, self.parameter[18][0], self.parameter[18][1], self.parameter[18][2], self.parameter[18][3], self.parameter[18][5], RT_HALIGN_RIGHT | RT_VALIGN_CENTER, self.correctweekdays(_time), skin.parseColor(self.parameter[28]).argb(), skin.parseColor(self.parameter[29]).argb()))
					else:
						if scrambled_or_rec:
							res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.parameter[19][0], self.parameter[19][1], self.parameter[19][2], self.parameter[19][3], image, None, None, BT_SCALE))
							res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.parameter[22][0], self.parameter[22][1], self.parameter[22][2], self.parameter[22][3], scrambled_or_rec, None, None, BT_SCALE))
							res.append((eListboxPythonMultiContent.TYPE_TEXT, (self.parameter[20][0] + self.parameter[20][4]), self.parameter[20][1], self.parameter[20][2], self.parameter[20][3], self.parameter[20][5], RT_HALIGN_LEFT | RT_VALIGN_CENTER, name, skin.parseColor(self.parameter[24]).argb(), skin.parseColor(self.parameter[25]).argb()))
							res.append((eListboxPythonMultiContent.TYPE_TEXT, (self.parameter[21][0] + self.parameter[21][4]), self.parameter[21][1], self.parameter[21][2], self.parameter[21][3], self.parameter[21][5], RT_HALIGN_LEFT | RT_VALIGN_CENTER, entrys.desc, skin.parseColor(self.parameter[26]).argb(), skin.parseColor(self.parameter[27]).argb()))
							res.append((eListboxPythonMultiContent.TYPE_TEXT, (self.parameter[18][0] + self.parameter[18][4]), self.parameter[18][1], self.parameter[18][2], self.parameter[18][3], self.parameter[18][5], RT_HALIGN_RIGHT | RT_VALIGN_CENTER, self.correctweekdays(_time), skin.parseColor(self.parameter[28]).argb(), skin.parseColor(self.parameter[29]).argb()))
						else:
							res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.parameter[19][0], self.parameter[19][1], self.parameter[19][2], self.parameter[19][3], image, None, None, BT_SCALE))
							res.append((eListboxPythonMultiContent.TYPE_TEXT, self.parameter[20][0], self.parameter[20][1], self.parameter[20][2], self.parameter[20][3], self.parameter[20][5], RT_HALIGN_LEFT | RT_VALIGN_CENTER, name, skin.parseColor(self.parameter[24]).argb(), skin.parseColor(self.parameter[25]).argb()))
							res.append((eListboxPythonMultiContent.TYPE_TEXT, self.parameter[21][0], self.parameter[21][1], self.parameter[21][2], self.parameter[21][3], self.parameter[21][5], RT_HALIGN_LEFT | RT_VALIGN_CENTER, entrys.desc, skin.parseColor(self.parameter[26]).argb(), skin.parseColor(self.parameter[27]).argb()))
							res.append((eListboxPythonMultiContent.TYPE_TEXT, self.parameter[18][0], self.parameter[18][1], self.parameter[18][2], self.parameter[18][3], self.parameter[18][5], RT_HALIGN_RIGHT | RT_VALIGN_CENTER, self.correctweekdays(_time), skin.parseColor(self.parameter[28]).argb(), skin.parseColor(self.parameter[29]).argb()))
				return res

		except Exception as ex:
			write_log("setMovieEntry : " + str(ex))
			if self.viewType == 'Wallansicht':
				return [entrys,
									(eWallPythonMultiContent.TYPE_TEXT, eWallPythonMultiContent.SHOW_ALWAYS, 2, 2, 2, 2, 96, 96, 96, 96, 0, 0, RT_WRAP | RT_HALIGN_CENTER | RT_VALIGN_CENTER, str(ex), skin.parseColor(self.parameter[6]).argb(), skin.parseColor(self.parameter[7]).argb()),
									]
			else:
				res = [None]
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 20, 0, (width - 40), height, 1, RT_HALIGN_CENTER | RT_VALIGN_CENTER, str(ex)))
				return res

	def key_menu_handler(self):
		keys = ["1", "2", "3", "4", "5", "6", "7", "8"]
		if self.viewType == 'Listenansicht':
			cs = self['movielist'].getCurrentSelection()
		else:
			cs = self['moviewall'].getcurrentselection()
		if cs.isFolder:
			if self.currentFolder[0] != "root" and cs.name != "...":
				choices, idx = ([('Einstellungen',), ('aktualisiere Ansicht',), ('verschiebe : ' + cs.filename[1],), ('kopiere : ' + cs.filename[1],), ('lösche : ' + cs.filename[1],), ('Abrechen',)], 0)
				self.session.openWithCallback(self.menuCallBack, ChoiceBox, title='Menüauswahl', keys=keys, list=choices, selection=idx)
			else:
				self.menuCallBack(ret=["Einstellungen"])
		else:
			if config.usage.movielist_use_moviedb_trash.value:
				choices, idx = ([('Einstellungen',), ('aktualisiere Ansicht',), ('verschiebe : ' + cs.name,), ('kopiere : ' + cs.name,), ('lösche : ' + cs.name,), ('lösche (Papierkorb) : ' + cs.name,), ('Abrechen',)], 0)
			else:
				choices, idx = ([('Einstellungen',), ('aktualisiere Ansicht',), ('verschiebe : ' + cs.name,), ('kopiere : ' + cs.name,), ('lösche : ' + cs.name,), ('Abrechen',)], 0)
			self.session.openWithCallback(self.menuCallBack, ChoiceBox, title='Menüauswahl', keys=keys, list=choices, selection=idx)

	def menuCallBack(self, ret=None):
		if ret:
			if self.viewType == 'Listenansicht':
				cs = self['movielist'].getCurrentSelection()
			else:
				cs = self['moviewall'].getcurrentselection()
			if ret[0] == "Einstellungen":
				paths = []
				for k, v in self.moviedict.items():
					for ik, iv in v.items():
						paths.append(ik)
				self.session.openWithCallback(self.return_from_setup, MySetup, paths)
			elif 'verschiebe : ' in ret[0]:
				paths = []
				for k, v in self.moviedict.items():
					for ik, iv in v.items():
						paths.append((ik,))
				paths.sort()
				choices, idx = (paths, 0)
				keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
				self.session.openWithCallback(self.moveCallBack, ChoiceBox, title='Ziel', keys=keys, list=choices, selection=idx)
			elif 'kopiere : ' in ret[0]:
				paths = []
				for k, v in self.moviedict.items():
					for ik, iv in v.items():
						paths.append((ik,))
				paths.sort()
				choices, idx = (paths, 0)
				keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
				self.session.openWithCallback(self.copyCallBack, ChoiceBox, title='Ziel', keys=keys, list=choices, selection=idx)
			elif 'lösche : ' in ret[0]:
				if cs.isFolder:
					msg = "Möchtest Du den Ordner und dessen Inhalt " + cs.filename[1] + " wirklich löschen?"
				else:
					msg = "Möchtest Du die Aufnahme " + cs.name + " wirklich löschen?"
				movebox = self.session.openWithCallback(self.remove, MessageBox, msg, MessageBox.TYPE_YESNO)
				movebox.setTitle(_("Löschen"))
			elif '(Papierkorb)' in ret[0]:
				msg = "Möchtest Du die Aufnahme " + cs.name + " wirklich in den Papierkorb verschieben?"
				movebox = self.session.openWithCallback(self.recycle, MessageBox, msg, MessageBox.TYPE_YESNO)
				movebox.setTitle(_("Löschen (Papierkorb)"))
			elif ret[0] == "aktualisiere Ansicht":
				self.getList(self.currentFolder, True)
				self.getMovieList(self.sortType)
				self.sel_changed()
				if self.viewType == 'Wallansicht':
					self['PageInfo'].setText('Seite ' + str(self['moviewall'].getCurrentPage()) + ' von ' + str(self.pageCount))

	def moveCallBack(self, ret=None):
		if ret:
			if self.viewType == 'Listenansicht':
				cs = self['movielist'].getCurrentSelection()
			else:
				cs = self['moviewall'].getcurrentselection()
			self.destination = ret[0]
			if cs.isFolder:
				msg = "Möchtest Du den Ordner " + cs.filename[1] + " nach " + self.destination + " verschieben?"
			else:
				msg = "Möchtest Du die Aufnahme " + cs.name + " nach " + self.destination + " verschieben?"
			movebox = self.session.openWithCallback(self.move, MessageBox, msg, MessageBox.TYPE_YESNO)
			movebox.setTitle(_("Verschieben"))

	def move(self, answer):
		if answer is True:
			if self.viewType == 'Listenansicht':
				cs = self['movielist'].getCurrentSelection()
			else:
				cs = self['moviewall'].getcurrentselection()
			if cs.isFolder:
				write_log('move folder : ' + str(cs.filename[1]) + ' to ' + str(self.destination))
#				shutil.move(cs.filename[1], self.destination)
				job_manager.AddJob(FileTransferJob(cs.filename[1], self.destination, True, False, "%s : %s" % (_("move folder"), cs.filename[1])))
				self.openTasklist()
			else:
				files = glob(self.removeExtension(cs.filename) + '.*')
				for file in files:
					write_log('move file : ' + str(file) + ' to ' + str(os.path.join(self.destination, os.path.basename(file))))
#					shutil.move(file, os.path.join(self.destination, os.path.basename(file)))
					job_manager.AddJob(FileTransferJob(file, self.destination, False, False, "%s : %s" % (_("move file"), file)))
				self.openTasklist()
				del files

	def copyCallBack(self, ret=None):
		if ret:
			if self.viewType == 'Listenansicht':
				cs = self['movielist'].getCurrentSelection()
			else:
				cs = self['moviewall'].getcurrentselection()
			self.destination = ret[0]
			if cs.isFolder:
				msg = "Möchtest Du den Ordner " + cs.filename[1] + " nach " + self.destination + " kopieren?"
			else:
				msg = "Möchtest Du die Aufnahme " + cs.name + " nach " + self.destination + " kopieren?"
			movebox = self.session.openWithCallback(self.copy, MessageBox, msg, MessageBox.TYPE_YESNO)
			movebox.setTitle(_("Kopieren"))

	def copy(self, answer):
		if answer is True:
			if self.viewType == 'Listenansicht':
				cs = self['movielist'].getCurrentSelection()
			else:
				cs = self['moviewall'].getcurrentselection()
			if cs.isFolder:
				write_log('copy folder : ' + str(cs.filename[1]) + ' to ' + str(self.destination))
				job_manager.AddJob(FileTransferJob(cs.filename[1], self.destination, True, True, "%s : %s" % (_("copy folder"), cs.filename[1])))
				self.openTasklist()
			else:
				files = glob(self.removeExtension(cs.filename) + '.*')
				for file in files:
					write_log('copy file : ' + str(file) + ' to ' + str(os.path.join(self.destination, os.path.basename(file))))
					job_manager.AddJob(FileTransferJob(file, self.destination, False, True, "%s : %s" % (_("copy file"), file)))
				self.openTasklist()
				del files

	def openTasklist(self):
		self.tasklist = []
		for job in job_manager.getPendingJobs():
			self.tasklist.append((job, job.name, job.getStatustext(), int(100 * job.progress / float(job.end)), str(100 * job.progress / float(job.end)) + "%"))
		if len(self.tasklist):
			self.session.open(TaskListScreen, self.tasklist)
			self.progressTimer.start(3000, True)

	def progressUpdate(self):
		foundJobs = False
		for job in job_manager.getPendingJobs():
			if 'move' in job.name or 'copy' in job.name:
				self["NaviInfo"].setText(job.getStatustext() + ' : ' + job.name + ' ' + str(100 * job.progress / float(job.end)) + '%')
				foundJobs = True
				break
		if foundJobs:
			self.refresh = True
			self.progressTimer.start(2000, True)
		else:
			if self.refresh:
				self.progressTimer.stop()
				self.getList(self.currentFolder, True)
				self.getMovieList(self.sortType)
				self.sel_changed()
				if self.viewType == 'Wallansicht':
					self['PageInfo'].setText('Seite ' + str(self['moviewall'].getCurrentPage()) + ' von ' + str(self.pageCount))

	def remove(self, answer):
		if answer is True:
			if self.viewType == 'Listenansicht':
				cs = self['movielist'].getCurrentSelection()
			else:
				cs = self['moviewall'].getcurrentselection()
			if cs.isFolder:
				write_log('delete folder : ' + str(cs.filename[1]))
				shutil.rmtree(cs.filename[1], ignore_errors=True)
				self.getList(None, True)
			else:
				files = glob(self.removeExtension(cs.filename) + '.*')
				for file in files:
					try:
						write_log('delete file : ' + str(file))
						os.remove(file)
					except Exception as ex:
						write_log('Fehler beim löschen : ' + str(ex))
						continue
				del files
				self.getList(self.currentFolder, True)
			self.getMovieList(self.sortType)
			self.sel_changed()
			if self.viewType == 'Wallansicht':
				self['PageInfo'].setText('Seite ' + str(self['moviewall'].getCurrentPage()) + ' von ' + str(self.pageCount))

	def recycle(self, answer):
		if answer is True:
			if self.viewType == 'Listenansicht':
				cs = self['movielist'].getCurrentSelection()
			else:
				cs = self['moviewall'].getcurrentselection()
			f = open(cs.filename + '.del', "w")
			f.write("")
			f.close()
			self.getList(self.currentFolder, True)
			self.getMovieList(self.sortType)
			self.sel_changed()
			if self.viewType == 'Wallansicht':
				self['PageInfo'].setText('Seite ' + str(self['moviewall'].getCurrentPage()) + ' von ' + str(self.pageCount))

	def return_from_setup(self):
		pass

	def key_play_handler(self):
		try:
			if self.viewType == 'Listenansicht':
				cs = self['movielist'].getCurrentSelection()
			else:
				cs = self['moviewall'].getcurrentselection()
			if cs:
				if str(cs.trailer).endswith('mp4'):
					write_log('Trailer: ' + str(cs.name) + ' URL: ' + str(cs.trailer))
					sRef = eServiceReference(4097, 0, str(cs.trailer))
					sRef.setName(str(cs.name))
					self.session.open(MoviePlayer, sRef)
		except Exception as ex:
			write_log("key_play : " + str(ex))

	def key_pvr_handler(self):
		if self.currentFolder[0] != 'root':
			self.session.openWithCallback(self.return_from_bookmarks, MovieLocationBox, "MovieWall", self.currentFolder[0] + '/')
		else:
			if self.viewType == 'Listenansicht':
				cs = self['movielist'].getCurrentSelection()
			else:
				cs = self['moviewall'].getcurrentselection()
			self.session.openWithCallback(self.return_from_bookmarks, MovieLocationBox, "MovieWall", cs.filename[0] + '/')

	def return_from_bookmarks(self, ret=None):
		if ret:
			if ret.endswith('/'):
				ret = ret[:-1]
			found = False
			for k, v in self.moviedict.items():
				for ik, iv in v.items():
					if str(ik) == str(ret):
						self.currentFolder = [k, ik]
						found = True
						break
			if not found:
				self.getList(createUpdate=True)
			self.getMovieList(self.sortType)
			self.sel_changed()
			if self.viewType == 'Wallansicht':
				self['PageInfo'].setText('Seite ' + str(self['moviewall'].getCurrentPage()) + ' von ' + str(self.pageCount))
			self["NaviInfo"].setText("Verzeichnis : " + self.currentFolder[1])

	def key_ok_handler(self):
		try:
			if self.viewType == 'Listenansicht':
				cs = self['movielist'].getCurrentSelection()
			else:
				cs = self['moviewall'].getcurrentselection()
			if not cs.isFolder:
				self.session.openWithCallback(self.return_from_player, MoviePlayer, cs.service)
			else:
				self.currentFolder = cs.filename
				self.getMovieList(self.sortType)
				self.sel_changed()
		except Exception as ex:
			write_log('key ok handler : ' + str(ex))

	def return_from_player(self):
		mlen = 0
		if self.viewType == 'Listenansicht':
			cs = self['movielist'].getCurrentSelection()
		else:
			cs = self['moviewall'].getcurrentselection()
		info = eServiceCenter.getInstance().info(cs.service)
		if info:
			mlen = info.getLength(cs.service)
		cs.__setitem__('progress', self.getProgress(cs.filename, mlen))
		if self.viewType == 'Wallansicht':
			self["moviewall"].refresh()
		self.sel_changed()

	def return_from_AEL(self):
		if self.viewType == 'Wallansicht':
			self["moviewall"].refresh()
		self.sel_changed()

	def refreshAll(self):
		try:
			if not self.isinit:
				self.isinit = True
				self.getList(createUpdate=False)
				self.getMovieList(self.sortType)
				self.sel_changed()
				if self.viewType == 'Wallansicht':
					self['PageInfo'].setText('Seite ' + str(self['moviewall'].getCurrentPage()) + ' von ' + str(self.pageCount))
				imgpath = skin.variables.get("EventLibraryImagePath", '/usr/share/enigma2/AELImages/,').replace(',', '')
				ptr = LoadPixmap(os.path.join(imgpath, "play.png"))
				self["trailer"].instance.setPixmap(ptr)
		except Exception as ex:
			write_log("refreshAll : " + str(ex))

	def key_info_handler(self):
		from Screens.EventView import EventViewSimple, EventViewMovieEvent
		if self.viewType == 'Listenansicht':
			cs = self['movielist'].getCurrentSelection()
		else:
			cs = self['moviewall'].getcurrentselection()
		if not cs.isFolder:
			mlen = ""
			try:
				info = eServiceCenter.getInstance().info(cs.service)
				if info:
					evt = info.getEvent(cs.service)
					if evt:
						self.session.open(EventViewSimple, evt, ServiceReference(cs.service))
					else:
						if info.getLength(cs.service) > 0:
							mlen = str(info.getLength(cs.service) / 60) + ' min'
						else:
							mlen = str(self.getMovieLen(cs.filename) / 60) + ' min'
						name, ext_desc = self.getExtendedMovieDescription(cs.service)
						self.session.open(EventViewMovieEvent, name=name, ext_desc=ext_desc, dur=mlen, service=cs.service)
			except Exception as ex:
				write_log("call EventView : " + str(ex))

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

	def key_red_handler(self):
		clearMem("Simple-Movie-Lists")
		self.close()

	def key_green_handler(self):
		if self.viewType == 'Listenansicht':
			cs = self['movielist'].getCurrentSelection()
		else:
			cs = self['moviewall'].getcurrentselection()
		isFolder = cs.isFolder
		if isFolder:
			self.session.openWithCallback(self.return_from_AEL, AdvancedEventLibrarySystem.Editor, service=None, eventname=(cs.name.replace("...", ""), 0))
		else:
			self.session.openWithCallback(self.return_from_AEL, AdvancedEventLibrarySystem.Editor, service=cs.service, eventname=None)

	def key_yellow_handler(self):
		if self.viewType == 'Listenansicht':
			cs = self['movielist'].getCurrentSelection()
		else:
			cs = self['moviewall'].getcurrentselection()
		if isTMDb and not cs.isFolder:
			self.session.open(tmdb.tmdbScreen, cs.service, 1)

	def key_blue_handler(self):
		choices, idx = ([('Datum absteigend',), ('Datum aufsteigend',), ('Name aufsteigend',), ('Name absteigend',), ('Tag aufsteigend',), ('Tag absteigend',)], 0)
		keys = ["1", "2", "3", "4", "5", "6"]
		self.session.openWithCallback(self.blueCallBack, ChoiceBox, title='Sortierung', keys=keys, list=choices, selection=idx)

	def blueCallBack(self, ret=None):
		if ret:
			if ret[0] == "Datum absteigend":
				self.sortType = 0
			elif ret[0] == "Datum aufsteigend":
				self.sortType = 1
			elif ret[0] == "Name aufsteigend":
				self.sortType = 2
			elif ret[0] == "Name absteigend":
				self.sortType = 3
			elif ret[0] == "Tag aufsteigend":
				self.sortType = 4
			elif ret[0] == "Tag absteigend":
				self.sortType = 5
			self.oldSortOrder = ret[0]
			self["key_blue"].setText(str(ret[0]))
			self.getMovieList(self.sortType)
			self.sel_changed()
			if self.viewType == 'Wallansicht':
				self['PageInfo'].setText('Seite ' + str(self['moviewall'].getCurrentPage()) + ' von ' + str(self.pageCount))

	def key_right_handler(self):
		if self.viewType == 'Listenansicht':
			self['movielist'].pageDown()
		else:
			self['moviewall'].right()
			self.sel_changed()

	def key_left_handler(self):
		if self.viewType == 'Listenansicht':
			self['movielist'].pageUp()
		else:
			self['moviewall'].left()
			self.sel_changed()

	def key_down_handler(self):
		if self.viewType == 'Listenansicht':
			self['movielist'].moveDown()
		else:
			old_idx = int(self['moviewall'].getCurrentIndex())
			if old_idx == self.listlen - 1:
				self['moviewall'].movetoIndex(0)
				self['PageInfo'].setText('Seite ' + str(self['moviewall'].getCurrentPage()) + ' von ' + str(self.pageCount))
			else:
				self['moviewall'].down()
				new_idx = int(self['moviewall'].getCurrentIndex())
				if new_idx <= old_idx:
					if (new_idx + self.parameter[14]) >= self.listlen:
						dest = 0
					else:
						dest = new_idx + self.parameter[14]
					self['moviewall'].movetoIndex(dest)
					self['PageInfo'].setText('Seite ' + str(self['moviewall'].getCurrentPage()) + ' von ' + str(self.pageCount))
			self.sel_changed()

	def key_up_handler(self):
		if self.viewType == 'Listenansicht':
			self['movielist'].moveUp()
		else:
			old_idx = int(self['moviewall'].getCurrentIndex())
			if old_idx == 0:
				dest = self.listlen - 1
				self['moviewall'].movetoIndex(dest)
				self['PageInfo'].setText('Seite ' + str(self['moviewall'].getCurrentPage()) + ' von ' + str(self.pageCount))
			else:
				self['moviewall'].up()
				new_idx = int(self['moviewall'].getCurrentIndex())
				if new_idx >= old_idx:
					if (new_idx - self.parameter[14]) < 0:
						dest = self.listlen - 1
					else:
						dest = new_idx - self.parameter[14]
					self['moviewall'].movetoIndex(dest)
					self['PageInfo'].setText('Seite ' + str(self['moviewall'].getCurrentPage()) + ' von ' + str(self.pageCount))
			self.sel_changed()

	def key_channel_up_handler(self):
		if self.viewType == 'Listenansicht':
			self['movielist'].pageUp()
		else:
			self['moviewall'].prevPage()
			self['PageInfo'].setText('Seite ' + str(self['moviewall'].getCurrentPage()) + ' von ' + str(self.pageCount))
		self.sel_changed()

	def key_channel_down_handler(self):
		if self.viewType == 'Listenansicht':
			self['movielist'].pageDown()
		else:
			self['moviewall'].nextPage()
			self['PageInfo'].setText('Seite ' + str(self['moviewall'].getCurrentPage()) + ' von ' + str(self.pageCount))
		self.sel_changed()

	def sel_changed(self):
		try:
			if self.viewType == 'Listenansicht':
				cs = self['movielist'].getCurrentSelection()
			else:
				cs = self['moviewall'].getcurrentselection()
			if cs:
				if cs.isFolder:
					self["NaviInfo"].setText("Verzeichnis : " + cs.filename[1])
				else:
					self["NaviInfo"].setText("Ziel : " + str(cs.filename))
				self["Service"].newService(cs.service)
				if str(cs.trailer).endswith('mp4'):
					self["trailer"].show()
				else:
					self["trailer"].hide()
		except Exception as ex:
			write_log("sel_changed : " + str(ex))

	def removeExtension(self, ext):
		ext = ext.replace('.wmv', '').replace('.mpeg2', '').replace('.ts', '').replace('.m2ts', '').replace('.mkv', '').replace('.avi', '').replace('.mpeg', '').replace('.mpg', '').replace('.iso', '').replace('.mp4', '')
		return ext

	def go_close(self):
		global active
		active = False
		if self.progressTimer.isActive():
			self.progressTimer.stop()
		del self.progressTimer
		del self.moviedict
		clearMem("Simple-Movie-Lists")
		self.close()

	def correctweekdays(self, itm):
		_itm = str(itm)
		_itm = _itm.replace("Mon", "Mo").replace("Tue", "Di").replace("Wed", "Mi").replace("Thu", "Do").replace("Fri", "Fr").replace("Sat", "Sa").replace("Sun", "So")
		return _itm


def removeExtension(ext):
	ext = ext.replace('.wmv', '').replace('.mpeg2', '').replace('.ts', '').replace('.m2ts', '').replace('.mkv', '').replace('.avi', '').replace('.mpeg', '').replace('.mpg', '').replace('.iso', '').replace('.mp4', '')
	return ext


def getMovieLen(moviename):
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


def saveList(imageType):
	try:
		global saving
		saving = True
		config.plugins.AdvancedEventLibrary = ConfigSubsection()
		searchLinks = config.plugins.AdvancedEventLibrary.SearchLinks = ConfigYesNo(default=True)
		setStatus('Advanced-Event-Library SimpleMovieWall aktualisiert Deine Daten.')
		f = open(os.path.join(pluginpath, 'imageType.data'), "w")
		f.write(str(imageType))
		f.close()
		moviedict = {}
		paths = []
		db = getDB()
		if os.path.isfile(os.path.join(pluginpath, 'movieplaces.data')):
			with open(os.path.join(pluginpath, 'movieplaces.data'), 'r') as f:
				lines = f.readlines()
				for line in lines:
					line = line.replace('\r', '').replace('\n', '')
					if line.endswith('/'):
						paths.append(line[:-1])
					else:
						paths.append(line)
		else:
			paths = config.movielist.videodirs.value
		paths.sort()
		recordPaths = []
		for path in paths:
			if path == '/media/hdd/' or path == '/media/hdd':
				path = '/media/hdd/movie'
			if path.endswith('/'):
				if path not in recordPaths:
					recordPaths.append(path[:-1])
			else:
				if path not in recordPaths:
					recordPaths.append(path)

		for x in range(0, len(recordPaths)):
			for recordPath in recordPaths:
				search = recordPath
				result = [recordPath for recordPath in recordPaths if search in recordPath]
				if len(result) > 1:
					recordPaths.remove(result[1])

		for recordPath in recordPaths:
			recordPath = os.path.normpath(os.path.realpath(recordPath))
			if os.path.isdir(recordPath):
				if recordPath.endswith('/'):
					recordPath = recordPath[:-1]
				for root, directories, files in os.walk(recordPath, followlinks=True):
					root = os.path.normpath(os.path.realpath(root))
					if os.path.isdir(root) and not 'trash' in root and not 'recycle' in root and ((searchLinks.value and os.path.islink(root)) or not os.path.islink(root)):
						if root.endswith('/'):
							root = root[:-1]
						movielist = []
						if files:
							for filename in files:
									try:
										if (filename.endswith('.ts') or filename.endswith('.mkv') or filename.endswith('.avi') or filename.endswith('.mpg') or filename.endswith('.mp4') or filename.endswith('.mpeg2')):
											if not fileExists(os.path.join(root, filename + '.del')):
												service = None
												image = None
												mlen = 0
												date = 0
												image = None
												desc = ""
												trailer = ""
												info = None
												name = str(removeExtension(filename)).split('/')[-1].replace('__', ': ').replace('_ ', ': ').replace('_', ' ')
												try:
													if filename.endswith('.ts'):
														s_service = '1:0:0:0:0:0:0:0:0:0:' + os.path.join(root, filename)
														service = eServiceReference('1:0:0:0:0:0:0:0:0:0:' + os.path.join(root, filename))
													else:
														s_service = '4097:0:0:0:0:0:0:0:0:0:' + os.path.join(root, filename)
														service = eServiceReference('4097:0:0:0:0:0:0:0:0:0:' + os.path.join(root, filename))
													try:
														info = eServiceCenter.getInstance().info(service)
														name = info.getName(service)
														mlen = info.getLength(service)
														desc = info.getInfoString(service, iServiceInformation.sDescription)
													except:
														pass
													date = os.path.getmtime(os.path.join(root, filename))
													dbdata = db.getTitleInfo(convert2base64(name))
													if dbdata:
														if str(dbdata[7]).endswith('mp4'):
															trailer = dbdata[7]
													image = getImageFile(getPictureDir() + imageType + '/', name)
													if info:
														ptr = info.getEvent(service)
														if ptr:
															if image is None:
																image = getImageFile(getPictureDir() + imageType + '/', ptr.getEventName())
															if trailer == "":
																dbdata = db.getTitleInfo(convert2base64(ptr.getEventName()))
																if dbdata:
																	if str(dbdata[7]).endswith('mp4'):
																		trailer = dbdata[7]
													if mlen <= 0:
														mlen = getMovieLen(os.path.join(root, filename))
												except Exception as ex:
													write_log(ex)
												itm = (str(os.path.join(root, filename)), date, removeExtension(name), s_service, mlen, image, desc, trailer)
												if not itm in movielist:
													movielist.append(itm)
									except Exception as ex:
										continue
						if recordPath not in moviedict:
							moviedict[recordPath] = {}
						if root not in moviedict[recordPath]:
							moviedict[recordPath][root] = {}
						if root == recordPath:
							parent = root
						else:
							parent = os.path.dirname(root)
						moviedict[recordPath][root] = {'directories': directories, 'parent': parent, 'files': movielist}
					del files
		with open(os.path.join(pluginpath, 'moviewall.data'), 'wb') as f:
			pickle.dump(moviedict, f)
		del movielist
		del moviedict
		saving = False
		setStatus()
	except Exception as ex:
		write_log('saveList : ' + str(ex))
		setStatus()
		saving = False


####################################################################################
class MySetup(Screen, ConfigListScreen):
	def __init__(self, session, paths=[]):
		Screen.__init__(self, session)
		self.session = session
		self.paths = paths
		self.skinName = ["Simple-Movie-Wall-Setup", "Setup"]
		self.title = "Simple-Movie-Wall-Setup"

		self.setup_title = "Simple-Movie-Wall-Setup"
		self["title"] = StaticText(self.title)

		self["key_red"] = StaticText("Beenden")
		self["key_green"] = StaticText("Speichern")

		config.plugins.AdvancedEventLibrary = ConfigSubsection()
		self.sortType = config.plugins.AdvancedEventLibrary.SortType = ConfigSelection(default="Datum absteigend", choices=["Datum absteigend", "Datum aufsteigend", "Name aufsteigend", "Name absteigend", "Tag aufsteigend", "Tag absteigend"])
		if self.paths:
			self.startPath = config.plugins.AdvancedEventLibrary.StartPath = ConfigSelection(default=self.paths[0], choices=self.paths)
		self.showProgress = config.plugins.AdvancedEventLibrary.Progress = ConfigYesNo(default=True)
		self.viewType = config.plugins.AdvancedEventLibrary.ViewType = ConfigSelection(default="Wallansicht", choices=["Listenansicht", "Wallansicht"])

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
			self.configlist.append(getConfigListEntry("Sortierung", self.sortType))
			if self.paths:
				self.configlist.append(getConfigListEntry("Startpfad", self.startPath))
			self.configlist.append(getConfigListEntry("zeige Fortschritt gesehen", self.showProgress))
			self.configlist.append(getConfigListEntry("Ansicht", self.viewType))
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
