from datetime import datetime
from html import unescape
from os.path import getsize, getmtime, isfile, join
from enigma import getDesktop, eListbox, eLabel, gFont, eListboxPythonMultiContent, ePoint, RT_HALIGN_LEFT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, BT_SCALE, BT_FIXRATIO
from skin import skin, fonts, parameters, variables, parseFont, parseColor
from Components.config import config
from Components.GUIComponent import GUIComponent
from Components.VariableText import VariableText
from Tools.Alternatives import GetWithAlternative
from Tools.LoadPixmap import LoadPixmap
from Tools.AdvancedEventLibrary import PicLoader, write_log


DEFAULT_MODULE_NAME = __name__.split(".")[-1]


class ImageList(GUIComponent, object):
	GUI_WIDGET = eListbox

	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		desktopSize = getDesktop(0).size()
		if desktopSize.width() == 1920:
			ffont, fsize = fonts.get("EventLibraryPictureListsFirstFont", ('Regular', 30))
			sfont, ssize = fonts.get("EventLibraryPictureListsSecondFont", ('Regular', 26))
			self.l.setItemHeight(int(parameters.get("EventLibraryPictureListsItemHeight", (108,))[0]))
		else:
			ffont, fsize = fonts.get("EventLibraryPictureListsFirstFont", ('Regular', 20))
			sfont, ssize = fonts.get("EventLibraryPictureListsSecondFont", ('Regular', 16))
			self.l.setItemHeight(int(parameters.get("EventLibraryPictureListsItemHeight", (80,))[0]))
		self.l.setFont(0, gFont(ffont, fsize))
		self.l.setFont(1, gFont(sfont, ssize))
		self.l.setBuildFunc(self.buildEntry)
		sel_changedCB = None
		self.onsel_changed = []
		if sel_changedCB is not None:   # TODO: wird nie aufgerufen, ist immer False
			self.onsel_changed.append(sel_changedCB)
		self.l.setSelectableFunc(self.isSelectable)
		self.list = []

	def applySkin(self, desktop, parent):
		attribs = []
		if self.skinAttributes is not None:
			for (attrib, value) in self.skinAttributes:
				if attrib == 'size':
					attribs.append((attrib, value))
					w, h = value.split(',')
					self.wList, self.hList = int(w), int(h)
				elif attrib == 'position':
					attribs.append((attrib, value))
					x, y = value.split(',')
					self.xList, self.yList = int(x), int(y)
				else:
					attribs.append((attrib, value))
			self.skinAttributes = attribs
			return GUIComponent.applySkin(self, desktop, parent)

	def getPosition(self):
		return self.yList

	def setList(self, list, how=1):
		self.how = how
		self.l.setBuildFunc(self.buildEntry)
		self.l.setList(list)
		self.list = list

	def buildEntry(self, data):
		try:
			desktopSize = getDesktop(0).size()
			if desktopSize.width() == 1920:
				xcp, ycp, wcp, hcp = parameters.get("EventLibraryCoverListCoverPosition", (10, 0, 192, 108))
				x1c, y1c, w1c, h1c = parameters.get("EventLibraryCoverListFirstLine", (220, 0, 700, 54))
				x2c, y2c, w2c, h2c = parameters.get("EventLibraryCoverListSecondLine", (220, 54, 700, 54))
				xpp, ypp, wpp, hpp = parameters.get("EventLibraryCoverListPosterPosition", (10, 0, 70, 108))
				x1p, y1p, w1p, h1p = parameters.get("EventLibraryPosterListFirstLine", (100, 0, 700, 54))
				x2p, y2p, w2p, h2p = parameters.get("EventLibraryPosterListSecondLine", (100, 54, 700, 54))
			else:
				xcp, ycp, wcp, hcp = parameters.get("EventLibraryCoverListCoverPosition", (10, 0, 142, 80))
				x1c, y1c, w1c, h1c = parameters.get("EventLibraryCoverListFirstLine", (160, 0, 500, 40))
				x2c, y2c, w2c, h2c = parameters.get("EventLibraryCoverListSecondLine", (160, 30, 500, 40))
				xpp, ypp, wpp, hpp = parameters.get("EventLibraryCoverListPosterPosition", (10, 0, 70, 80))
				x1p, y1p, w1p, h1p = parameters.get("EventLibraryPosterListFirstLine", (80, 0, 500, 40))
				x2p, y2p, w2p, h2p = parameters.get("EventLibraryPosterListSecondLine", (80, 30, 500, 40))

			nDp = int(x1p) - int(wpp)
			nDc = int(x1c) - int(wcp)
			if self.how == 1:
				if data[1] == 'Cover':
					if data[5]:
						desktopSize = getDesktop(0).size()
						self.picloader = PicLoader(192, 108) if desktopSize.width() == 1920 else PicLoader(142, 80)
						picon = self.picloader.load('/tmp/' + data[5])
						self.picloader.destroy()
						fSize = round(float(getsize('/tmp/' + data[5]) / 1024.0), 1)
						fSize = str(fSize) + " kB "
						res = [None]
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, xcp, ycp, wcp, hcp, picon))
						res.append((eListboxPythonMultiContent.TYPE_TEXT, x1c, y1c, w1c, h1c, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, str(data[0])))
						res.append((eListboxPythonMultiContent.TYPE_TEXT, x2c, y2c, w2c, h2c, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, data[1] + ' ' + fSize + ' ' + data[2]))
						return res
					else:
						res = [None]
						res.append((eListboxPythonMultiContent.TYPE_TEXT, nDc, y1c, w1c, h1c, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, data[0]))
						res.append((eListboxPythonMultiContent.TYPE_TEXT, nDc, y2c, 820, h2c, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, data[1]))
						return res
				else:
					if data[5]:
						self.picloader = PicLoader(70, 108)
						picon = self.picloader.load('/tmp/' + data[5])
						self.picloader.destroy()
						fSize = round(float(getsize('/tmp/' + data[5]) / 1024.0), 1)
						fSize = str(fSize) + " kB "
						res = [None]
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, xpp, ypp, wpp, hpp, picon))
						res.append((eListboxPythonMultiContent.TYPE_TEXT, x1p, y1p, w1p, h1p, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, str(data[0])))
						res.append((eListboxPythonMultiContent.TYPE_TEXT, x2p, y2p, w2p, h2p, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, data[1] + ' ' + fSize + ' ' + data[2]))
						return res
					else:
						res = [None]
						res.append((eListboxPythonMultiContent.TYPE_TEXT, nDp, y1p, w1p, h1p, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, data[0]))
						res.append((eListboxPythonMultiContent.TYPE_TEXT, nDp, y2p, 820, h2p, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, data[1]))
						return res
			else:
				if data[1] == 'Cover' or data[1] == 'Preview':
					if data[3]:
						self.picloader = PicLoader(192, 108)
						picon = self.picloader.load(data[3])
						self.picloader.destroy()
						fSize = round(float(getsize(data[3]) / 1024.0), 1)
						fSize = str(fSize) + " kB "
						date = getmtime(data[3])
						timeobj = datetime.fromtimestamp(date)
						_time = timeobj.strftime("%d.%m.%Y-%H:%M")
						res = [None]
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, xcp, ycp, wcp, hcp, picon, None, None, BT_SCALE | BT_FIXRATIO))
						res.append((eListboxPythonMultiContent.TYPE_TEXT, x1c, y1c, w1c, h1c, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, str(data[0])))
						res.append((eListboxPythonMultiContent.TYPE_TEXT, x2c, y2c, w2c, h2c, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, data[1] + ' : ' + fSize + ' vom ' + _time))
						return res
					else:
						res = [None]
						res.append((eListboxPythonMultiContent.TYPE_TEXT, nDc, y1c, w1c, h1c, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, data[0]))
						res.append((eListboxPythonMultiContent.TYPE_TEXT, nDc, y2c, 820, h2c, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, data[1]))
						return res
				else:
					if data[3]:
						self.picloader = PicLoader(70, 108)
						picon = self.picloader.load(data[3])
						self.picloader.destroy()
						fSize = round(float(getsize(data[3]) / 1024.0), 1)
						fSize = str(fSize) + " kB "
						date = getmtime(data[3])
						timeobj = datetime.fromtimestamp(date)
						_time = timeobj.strftime("%d.%m.%Y-%H:%M")
						res = [None]
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, xpp, ypp, wpp, hpp, picon))
						res.append((eListboxPythonMultiContent.TYPE_TEXT, x1p, y1p, w1p, h1p, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, str(data[0])))
						res.append((eListboxPythonMultiContent.TYPE_TEXT, x2p, y2p, w2p, h2p, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, data[1] + ' : ' + fSize + ' vom ' + _time))
						return res
					else:
						res = [None]
						res.append((eListboxPythonMultiContent.TYPE_TEXT, nDp, y1p, w1p, h1p, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, data[0]))
						res.append((eListboxPythonMultiContent.TYPE_TEXT, nDp, y2p, 820, h2p, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, data[1]))
						return res
		except Exception as ex:
			return []

	@staticmethod
	def isSelectable(data):
		return True

	def connectsel_changed(self, func):
		if not self.onsel_changed.count(func):
			self.onsel_changed.append(func)

	def disconnectsel_changed(self, func):
		self.onsel_changed.remove(func)

	def selectionChanged(self):
		for x in self.onsel_changed:
			if x is not None:
				try:
					x()
				except Exception:  # TODO: FIXME!!!
					print('FIXME in ElementList.selectionChanged')

	def getCurrentSelection(self):
		cur = self.l.getCurrentSelection()
		return cur[0]

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
		self.instance.setWrapAround(True)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)

	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveTop)

	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveEnd)

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)

	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)

	def moveUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def updateListObject(self, row):
		index = self.getCurrentIndex()
		tmp = self.list[index]
		self.list[index] = (row,)
		self.l.invalidateEntry(index)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def setMode(self, mode):
		self.mode = mode

	def getList(self):
		return self.list

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)


class SearchResultsList(GUIComponent, object):
	GUI_WIDGET = eListbox

	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		ffont, fsize = fonts.get("EventLibrarySearchListFirstFont", ('Regular', 32))
		sfont, ssize = fonts.get("EventLibrarySearchListSecondFont", ('Regular', 28))
		self.l.setItemHeight(int(parameters.get("EventLibrarySearchListItemHeight", (80,))[0]))
		self.l.setFont(0, gFont(ffont, fsize))
		self.l.setFont(1, gFont(sfont, ssize))

		self.l.setBuildFunc(self.buildEntry)
		sel_changedCB = None
		self.onsel_changed = []
		if sel_changedCB is not None:  # TODO: wird nie aufgerufen, ist immer False
			self.onsel_changed.append(sel_changedCB)
		self.l.setSelectableFunc(self.isSelectable)
		self.list = []

	def applySkin(self, desktop, parent):
		attribs = []
		if self.skinAttributes is not None:
			for (attrib, value) in self.skinAttributes:
				if attrib == 'size':
					attribs.append((attrib, value))
					w, h = value.split(',')
					self.wList, self.hList = int(w), int(h)
				elif attrib == 'position':
					attribs.append((attrib, value))
					x, y = value.split(',')
					self.xList, self.yList = int(x), int(y)
				else:
					attribs.append((attrib, value))
			self.skinAttributes = attribs
			return GUIComponent.applySkin(self, desktop, parent)

	def getPosition(self):
		return self.yList + self.hList

	def setList(self, list):
		self.l.setBuildFunc(self.buildEntry)
		self.l.setList(list)
		self.list = list

	def buildEntry(self, data, dummy=None):
		try:
			x1, y1, w1, h1 = parameters.get("EventLibrarySearchListFirstLine", (20, 0, 1600, 40))
			x2, y2, w2, h2 = parameters.get("EventLibrarySearchListSecondLine", (20, 40, 1600, 40))
			res = [None]
			countries = ""
			year = ""
			genres = ""
			rating = ""
			fsk = ""
			if not data[6]:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, x1, y1, w1, h1, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, str(data[0])))
				return res
			else:
				if data[1]:
					countries = str(data[1]) + " " + str(unescape('&#xB7;')) + " "
				if data[2]:
					year = str(data[2]) + " " + str(unescape('&#xB7;')) + " "
				if data[3]:
					genres = str(data[3]) + " " + str(unescape('&#xB7;')) + " "
				if data[4]:
					rating = "Bewertung : " + str(data[4]) + " " + str(unescape('&#xB7;')) + " "
				if data[5]:
					fsk = "FSK : " + str(data[5]) + " " + str(unescape('&#xB7;')) + " "
				details = genres + countries + year + rating + fsk
				details = details[:-2]
				res.append((eListboxPythonMultiContent.TYPE_TEXT, x1, y1, w1, h1, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, str(data[0]) + " " + str(unescape('&#xB7;')) + " (" + str(data[6]) + ")"))
				res.append((eListboxPythonMultiContent.TYPE_TEXT, x2, y2, w2, h2, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, details))
				return res
		except Exception as ex:
			return []

	@staticmethod
	def isSelectable(data):
		return True

	def connectsel_changed(self, func):
		if not self.onsel_changed.count(func):
			self.onsel_changed.append(func)

	def disconnectsel_changed(self, func):
		self.onsel_changed.remove(func)

	def selectionChanged(self):
		for x in self.onsel_changed:
			if x is not None:
				try:
					x()
				except Exception:  # TODO: FIXME!!!
					print('FIXME in ElementList.selectionChanged')

	def getCurrentSelection(self):
		cur = self.l.getCurrentSelection()
		return cur[0]

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
		self.instance.setWrapAround(True)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)

	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveTop)

	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveEnd)

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)

	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)

	def moveUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def updateListObject(self, row):
		index = self.getCurrentIndex()
		tmp = self.list[index]
		self.list[index] = (row,)
		self.l.invalidateEntry(index)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def setMode(self, mode):
		self.mode = mode

	def getList(self):
		return self.list

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)

####################################################################################################################################


class MovieList(GUIComponent, object):
	GUI_WIDGET = eListbox

	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.recIcon = str(variables.get("EventLibraryEPGListsRecordIcon", '/usr/share/enigma2/AELImages/timer.png,')).replace(',', '')
		ffont, fsize = fonts.get("EventLibraryPlanersEventListFirstFont", ('Regular', 26))
		sfont, ssize = fonts.get("EventLibraryPlanersEventListSecondFont", ('Regular', 30))
		self.l.setFont(0, gFont(ffont, fsize))
		self.l.setFont(1, gFont(sfont, ssize))
		sel_changedCB = None
		self.onsel_changed = []
		if sel_changedCB is not None:  # TODO: wird nie aufgerufen, ist immer False
			self.onsel_changed.append(sel_changedCB)
		self.pixmapCache = {}
		self.selectedID = None
		self.l.setSelectableFunc(self.isSelectable)
		self.list = []
		self.folderImage = "/usr/share/enigma2/AELImages/folder.jpg"
		self.substituteImage = "/usr/share/enigma2/AELImages/backdrop.jpg"
		self.scrambledImage = "/usr/share/enigma2/AELImages/scrambled.png"
		self.progressForegroundColor = "#00aaaaaa"
		self.progressBackgroundColor = "#00161616"
		self.progressForegroundColorSelected = "#00aaaaaa"
		self.progressBackgroundColorSelected = "#00161616"
		self.firstLineColorSelected = "#00ffffff"
		self.secondLineColorSelected = "#00ffffff"
		self.dateColorSelected = "#00ffffff"
		self.firstLineColor = "#00dddddd"
		self.secondLineColor = "#00dddddd"
		self.dateColor = "#00dddddd"
		self.progressBorderWidth = 1
		self.borderwidth = 0
		self.maxTextLength = 100
		self.textHeightPercent = 15
		self.imageType = 'cover'
		self.dateFormat = '%d.%m.%Y'
		self.progressPos = [0, 0, 0, 0, 0]
		self.datePos = [0, 0, 0, 0, 0, 0]
		self.imagePos = [0, 0, 0, 0]
		self.recIconPos = [0, 0, 0, 0]
		self.firstLinePos = [0, 0, 0, 0, 0, 0]
		self.secondLinePos = [0, 0, 0, 0, 0, 0]

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			pfcremove = None
			pbcremove = None
			pbwremove = None
			pfcsremove = None
			pbcsremove = None
			scIremove = None
			lremove = None
			pPremove = None
			dPremove = None
			iPremove = None
			fFremove = None
			sFremove = None
			fLPremove = None
			sLPremove = None
			rIPremove = None
			dFremove = None
			fLCSremove = None
			sLCSremove = None
			dCSremove = None
			fLCremove = None
			sLCremove = None
			dCremove = None
			attribs = []
			for (attrib, value) in self.skinAttributes:
				if attrib == "progressForegroundColor":
					self.progressForegroundColor = str(value)
					pfcremove = ('progressForegroundColor', value)
				elif attrib == "progressBackgroundColor":
					self.progressBackgroundColor = str(value)
					pbcremove = ('progressBackgroundColor', value)
				elif attrib == "progressForegroundColorSelected":
					self.progressForegroundColorSelected = str(value)
					pfcsremove = ('progressForegroundColorSelected', value)
				elif attrib == "progressBackgroundColorSelected":
					self.progressBackgroundColorSelected = str(value)
					pbcsremove = ('progressBackgroundColorSelected', value)
				elif attrib == "progressBorderWidth":
					self.progressBorderWidth = int(value)
					pbwremove = ('progressBorderWidth', value)
				elif attrib == "firstLineColorSelected":
					self.firstLineColorSelected = str(value)
					fLCSremove = ('firstLineColorSelected', value)
				elif attrib == "secondLineColorSelected":
					self.secondLineColorSelected = str(value)
					sLCSremove = ('secondLineColorSelected', value)
				elif attrib == "dateColorSelected":
					self.dateColorSelected = str(value)
					dCSremove = ('dateColorSelected', value)
				elif attrib == "firstLineColor":
					self.firstLineColor = str(value)
					fLCremove = ('firstLineColor', value)
				elif attrib == "secondLineColor":
					self.secondLineColor = str(value)
					sLCremove = ('secondLineColor', value)
				elif attrib == "dateColor":
					self.dateColor = str(value)
					dCremove = ('dateColor', value)
				elif attrib == "substituteImage":
					self.substituteImage = str(value)
					sIremove = ('substituteImage', value)
				elif attrib == "folderImage":
					self.folderImage = str(value)
					fIremove = ('folderImage', value)
				elif attrib == "scrambledImage":
					self.scrambledImage = str(value)
					scIremove = ('scrambledImage', value)
				elif attrib == "imageType":
					self.imageType = str(value)
					tremove = ('imageType', value)
				elif attrib == "maxTextLength":
					self.maxTextLength = int(value)
					lremove = ('maxTextLength', value)
				elif attrib == "firstLinePos":
					pos = value.split(',')
					self.firstLinePos = [int(pos[0].strip()), int(pos[1].strip()), int(pos[2].strip()), int(pos[3].strip()), int(pos[4].strip()), int(pos[5].strip())]
				elif attrib == "secondLinePos":
					pos = value.split(',')
					self.secondLinePos = [int(pos[0].strip()), int(pos[1].strip()), int(pos[2].strip()), int(pos[3].strip()), int(pos[4].strip()), int(pos[5].strip())]
				elif attrib == "progressPos":
					pos = value.split(',')
					self.progressPos = [int(pos[0].strip()), int(pos[1].strip()), int(pos[2].strip()), int(pos[3].strip()), int(pos[4].strip())]
				elif attrib == "datePos":
					pos = value.split(',')
					self.datePos = [int(pos[0].strip()), int(pos[1].strip()), int(pos[2].strip()), int(pos[3].strip()), int(pos[4].strip()), int(pos[5].strip())]
				elif attrib == "imagePos":
					pos = value.split(',')
					self.imagePos = [int(pos[0].strip()), int(pos[1].strip()), int(pos[2].strip()), int(pos[3].strip())]
				elif attrib == "recIconPos":
					pos = value.split(',')
					self.recIconPos = [int(pos[0].strip()), int(pos[1].strip()), int(pos[2].strip()), int(pos[3].strip())]
				elif attrib == "firstFont":
					self.l.setFont(0, parseFont(value, ((1, 1), (1, 1))))
				elif attrib == "secondFont":
					self.l.setFont(1, parseFont(value, ((1, 1), (1, 1))))
				elif attrib == "dateFormat":
					self.dateFormat = str(value)
					dFremove = ('dateFormat', value)
				else:
					attribs.append((attrib, value))
			if pfcremove:
				attribs = [x for x in attribs if x != pfcremove]
			if pbcremove:
				attribs = [x for x in attribs if x != pbcremove]
			if pfcsremove:
				attribs = [x for x in attribs if x != pfcsremove]
			if pbcsremove:
				attribs = [x for x in attribs if x != pbcsremove]
			if pbwremove:
				attribs = [x for x in attribs if x != pbwremove]
			if scIremove:
				attribs = [x for x in attribs if x != scIremove]
			if lremove:
				attribs = [x for x in attribs if x != lremove]
			if pPremove:
				attribs = [x for x in attribs if x != pPremove]
			if dPremove:
				attribs = [x for x in attribs if x != dPremove]
			if iPremove:
				attribs = [x for x in attribs if x != iPremove]
			if fFremove:
				attribs = [x for x in attribs if x != fFremove]
			if sFremove:
				attribs = [x for x in attribs if x != sFremove]
			if fLPremove:
				attribs = [x for x in attribs if x != fLPremove]
			if sLPremove:
				attribs = [x for x in attribs if x != sLPremove]
			if rIPremove:
				attribs = [x for x in attribs if x != rIPremove]
			if dFremove:
				attribs = [x for x in attribs if x != dFremove]
			if fLCSremove:
				attribs = [x for x in attribs if x != fLCSremove]
			if sLCSremove:
				attribs = [x for x in attribs if x != sLCSremove]
			if dCSremove:
				attribs = [x for x in attribs if x != dCSremove]
			if fLCremove:
				attribs = [x for x in attribs if x != fLCremove]
			if sLCremove:
				attribs = [x for x in attribs if x != sLCremove]
			if dCremove:
				attribs = [x for x in attribs if x != dCremove]
			self.skinAttributes = attribs
			return GUIComponent.applySkin(self, desktop, screen)

	def getParameter(self):
		recIcon = str(variables.get("EventLibraryEPGListsRecordIcon", '/usr/share/enigma2/AELImages/timer.png,')).replace(',', '')
		return (self.l.getItemSize().width(), self.l.getItemSize().height(), self.maxTextLength, self.imageType, self.folderImage, self.substituteImage, 0, 0, 0, self.progressForegroundColor, self.progressBackgroundColor, self.progressForegroundColorSelected, self.progressBackgroundColorSelected, self.progressBorderWidth, 0, recIcon, self.scrambledImage, self.progressPos, self.datePos, self.imagePos, self.firstLinePos, self.secondLinePos, self.recIconPos, self.dateFormat, self.firstLineColor, self.firstLineColorSelected, self.secondLineColor, self.secondLineColorSelected, self.dateColor, self.dateColorSelected)

	def setList(self, list):
		self.l.setList(list)
		self.list = list

	@staticmethod
	def isSelectable(data):
		return True

	def connectsel_changed(self, func):
		if not self.onsel_changed.count(func):
			self.onsel_changed.append(func)

	def disconnectsel_changed(self, func):
		self.onsel_changed.remove(func)

	def selectionChanged(self):
		for x in self.onsel_changed:
			if x is not None:
				try:
					x()
				except Exception:  # TODO: FIXME!!!
					print("FIXME in EPGList.selectionChanged")

	def getCurrentSelection(self):
		cur = self.l.getCurrentSelection()
		return cur[0]

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
		self.instance.setWrapAround(True)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)

	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)

	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)

	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)

	def moveUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def updateListObject(self, row):
		index = self.getCurrentIndex()
		tmp = self.list[index]
		self.list[index] = (row,)
		self.l.invalidateEntry(index)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def setMode(self, mode):
		self.mode = mode

	def getList(self):
		return self.list

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)

#################################################################################################################################


class AELBaseWall(GUIComponent, object):
	GUI_WIDGET = eListbox

	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setBuildFunc(self.setentry)
		self.l.setFont(0, gFont('Regular', 22))
		self.l.setFont(1, gFont('Regular', 22))
		self.onselectionchanged = []
		self.l.setSelectableFunc(self.isselectable)
		#self.l.setViewMode(eListboxPythonMultiContent.MODE_WALL)
		#self.l.setScrollMode(eListboxPythonMultiContent.SCROLLMODE_PAGE)
		self.list = []
		self.selectedItem = None
		self.instance = None
		self.folderImage = "/usr/share/enigma2/AELImages/folder.jpg"
		self.substituteImage = "/usr/share/enigma2/AELImages/missing.jpg"
		self.scrambledImage = "/usr/share/enigma2/AELImages/scrambled.png"
		self.fc = "#00ffffff"
		self.fcs = "#00ffffff"
		self.progressForegroundColor = "#00aaaaaa"
		self.progressBackgroundColor = "#00161616"
		self.progressForegroundColorSelected = "#00aaaaaa"
		self.progressBackgroundColorSelected = "#00161616"
		self.backgroundColor = "#00000000"
		self.progressBorderWidth = 1
		self.borderwidth = 0
		self.maxTextLength = 100
		self.textHeightPercent = 15
		self.imageType = ''
		self.imagePos = [0, 0, 100, 100]
		self.recIconPos = [0, 0, 0, 0]
		self.piconPos = [0, 0, 0, 0]
		self.progressPos = [0, 0, 0, 0]
		self.firstLinePos = [0, 0, 0, 0, 0, 0]
		self.secondLinePos = [0, 0, 0, 0, 0, 0]
		self.timeFormat = "weekday,date,start,end,duration"
		self.control = {'left': 'left', 'right': 'right', 'up': 'up', 'down': 'down', 'pageUp': 'pageUp', 'pageDown': 'pageDown'}
		self.coverings = []
		self.fontOrientation = "RT_WRAP,RT_HALIGN_CENTER,RT_VALIGN_CENTER"

	def applySkin(self, desktop, screen):
		attribs = []
		if self.skinAttributes is not None:
			fremove = None
			sfremove = None
			fIremove = None
			sIremove = None
			lremove = None
			tremove = None
			fcremove = None
			fcsremove = None
			thpremove = None
			pfcremove = None
			pbcremove = None
			pbwremove = None
			pfcsremove = None
			pbcsremove = None
			scIremove = None
			for (attrib, value) in self.skinAttributes:
				if attrib == "progressForegroundColor":
					self.progressForegroundColor = str(value)
					pfcremove = ('progressForegroundColor', value)
				elif attrib == "control":
					self.control = value
				elif attrib == "coverings":
					self.coverings = value
				elif attrib == "fontOrientation":
					self.fontOrientation = value
				elif attrib == "progressPos":
					pos = value.split(',')
					self.progressPos = [int(pos[0].strip()), int(pos[1].strip()), int(pos[2].strip()), int(pos[3].strip())]
				elif attrib == "firstLinePos":
					pos = value.split(',')
					self.firstLinePos = [int(pos[0].strip()), int(pos[1].strip()), int(pos[2].strip()), int(pos[3].strip()), int(pos[4].strip()), int(pos[5].strip())]
				elif attrib == "secondLinePos":
					pos = value.split(',')
					self.secondLinePos = [int(pos[0].strip()), int(pos[1].strip()), int(pos[2].strip()), int(pos[3].strip()), int(pos[4].strip()), int(pos[5].strip())]
				elif attrib == "timeFormat":
					self.timeFormat = str(value)
				elif attrib == "progressBackgroundColor":
					self.progressBackgroundColor = str(value)
					pbcremove = ('progressBackgroundColor', value)
				elif attrib == "progressForegroundColorSelected":
					self.progressForegroundColorSelected = str(value)
					pfcsremove = ('progressForegroundColorSelected', value)
				elif attrib == "progressBackgroundColorSelected":
					self.progressBackgroundColorSelected = str(value)
					pbcsremove = ('progressBackgroundColorSelected', value)
				elif attrib == "progressBorderWidth":
					self.progressBorderWidth = int(value)
					pbwremove = ('progressBorderWidth', value)
				elif attrib == "textHeightPercent":
					self.textHeightPercent = int(value)
					thpremove = ('textHeightPercent', value)
				elif attrib == "fontColor":
					self.fc = str(value)
					fcremove = ('fontColor', value)
				elif attrib == "fontColorSelected":
					self.fcs = str(value)
					fcsremove = ('fontColorSelected', value)
				elif attrib == "substituteImage":
					self.substituteImage = str(value)
					sIremove = ('substituteImage', value)
				elif attrib == "folderImage":
					self.folderImage = str(value)
					fIremove = ('folderImage', value)
				elif attrib == "scrambledImage":
					self.scrambledImage = str(value)
					scIremove = ('scrambledImage', value)
				elif attrib == "imageType":
					self.imageType = str(value)
					tremove = ('imageType', value)
				elif attrib == "piconPos":
					pos = value.split(',')
					self.piconPos = [int(pos[0].strip()), int(pos[1].strip()), int(pos[2].strip()), int(pos[3].strip())]
				elif attrib == "imagePos":
					pos = value.split(',')
					self.imagePos = [int(pos[0].strip()), int(pos[1].strip()), int(pos[2].strip()), int(pos[3].strip())]
				elif attrib == "recIconPos":
					pos = value.split(',')
					self.recIconPos = [int(pos[0].strip()), int(pos[1].strip()), int(pos[2].strip()), int(pos[3].strip())]
				elif attrib == "font":
					self.l.setFont(0, gFont(value.split(';')[0].strip(), int(value.split(';')[1].strip())))
					fremove = ('font', value)
				elif attrib == "secondFont":
					self.l.setFont(1, gFont(value.split(';')[0].strip(), int(value.split(';')[1].strip())))
					sfremove = ('secondFont', value)
				elif attrib == "maxTextLength":
					self.maxTextLength = int(value)
					lremove = ('maxTextLength', value)
				#	if str(value).find(",") != -1:
				#		self.l.setItemScale_H(int(value.split(',')[0]))
				#		self.l.setItemScale_V(int(value.split(',')[1]))
				#	else:
				#		self.l.setItemScale_V(int(value))
				#		self.l.setItemScale_H(int(value))
				elif attrib == "viewMode" and self.instance:
					self.instance.setOrientation({"wall": eListbox.orGrid, "list_horizontal": eListbox.orHorizontal, "list_vertical": eListbox.orVertical, }[value])
				elif attrib == "itemSize":
					self.l.setItemWidth(int(value.split(',')[0]))
					self.l.setItemHeight(int(value.split(',')[1]))
				elif attrib == "itemScale" and self.instance:
					self.instance.setSelectionZoom(float(value))
				elif attrib == "itemSpace" and self.instance:
					if str(value).find(",") != -1:
						h = int(value.split(',')[0])
						v = int(value.split(',')[0])
					else:
						h = v = int(value)
					self.instance.setItemSpacing(ePoint(h, v))
				#elif attrib == "aspectRatio":
				#	self.l.setAspectRatio(
				#		{"dvd": eListboxPythonMultiContent.ASPECT_DVD,
				#		 "cd": eListboxPythonMultiContent.ASPECT_CD,
				#			"screen": eListboxPythonMultiContent.ASPECT_SCREEN,
				#			"banner": eListboxPythonMultiContent.ASPECT_BANNER,
				#		 }[value])
				#elif attrib == "scrollMode":
				#	self.l.setScrollMode(
				#		{"page": eListboxPythonMultiContent.SCROLLMODE_PAGE,
				#		 "flow": eListboxPythonMultiContent.SCROLLMODE_FLOW,
				#		 }[value])
				elif attrib == "dimensions":
					self.l.setColumnCount(int(value.split(',')[0]))
					self.l.setRowCount(int(value.split(',')[1]))
				elif attrib == "useShadow":
					pass
				#	self.l.setShadow(int(value))
				elif attrib == "useOverlay":
					self.l.setOverlay(int(value))
				elif attrib == "downloadPath":
					self.l.setDownloadPath(str(value))
				elif attrib == "backgroundColorGlobal":
					pass
				#	self.l.setGlobalBackgroundColor(parseColor(str(value)))
				elif attrib == "borderColor" and self.instance:
					self.instance.setBorderColor(parseColor(str(value)))
				elif attrib == "borderWidth" and self.instance:
					self.borderwidth = int(value)
					self.instance.setBorderWidth(self.borderwidth)
				elif attrib == "animated" and self.instance:
					self.instance.setAnimation(int(value))
				elif attrib == "backgroundColor" and self.instance:
					self.instance.setBackgroundColor(parseColor(str(value)))
					self.backgroundColor = str(value)
				elif attrib == "backgroundColorSelected" and self.instance:
					self.instance.setBackgroundColorSelected(parseColor(str(value)))
				else:
					attribs.append((attrib, value))
			if fremove:
				attribs = [x for x in attribs if x != fremove]
			if sfremove:
				attribs = [x for x in attribs if x != sfremove]
			if lremove:
				attribs = [x for x in attribs if x != lremove]
			if tremove:
				attribs = [x for x in attribs if x != tremove]
			if fIremove:
				attribs = [x for x in attribs if x != fIremove]
			if sIremove:
				attribs = [x for x in attribs if x != sIremove]
			if fcremove:
				attribs = [x for x in attribs if x != fcremove]
			if fcsremove:
				attribs = [x for x in attribs if x != fcsremove]
			if thpremove:
				attribs = [x for x in attribs if x != thpremove]
			if pfcremove:
				attribs = [x for x in attribs if x != pfcremove]
			if pbcremove:
				attribs = [x for x in attribs if x != pbcremove]
			if pfcsremove:
				attribs = [x for x in attribs if x != pfcsremove]
			if pbcsremove:
				attribs = [x for x in attribs if x != pbcsremove]
			if pbwremove:
				attribs = [x for x in attribs if x != pbwremove]
			if scIremove:
				attribs = [x for x in attribs if x != scIremove]
			self.skinAttributes = attribs
			return GUIComponent.applySkin(self, desktop, screen)

	def getParameter(self):
		recIcon = str(variables.get("EventLibraryEPGListsRecordIcon", '/usr/share/enigma2/AELImages/timer.png,')).replace(',', '')
		return (self.l.getItemSize().width(), self.l.getItemSize().height(), self.maxTextLength, self.imageType, self.folderImage, self.substituteImage, self.fc, self.fcs, self.textHeightPercent, self.progressForegroundColor, self.progressBackgroundColor, self.progressForegroundColorSelected, self.progressBackgroundColorSelected, self.progressBorderWidth, recIcon, self.scrambledImage, self.imagePos, self.recIconPos, self.firstLinePos, self.secondLinePos, self.piconPos, self.control, self.coverings, self.progressPos, self.fontOrientation, self.backgroundColor, self.timeFormat)

	def isselectable(self, data):
		return True

	def refresh(self):
		pass
		#TODO add refresh function
		# self.l.refresh()

	def connectSelChanged(self, fnc):
		if fnc not in self.onselectionchanged:
			self.onselectionchanged.append(fnc)

	def disconnectSelChanged(self, fnc):
		if fnc in self.onselectionchanged:
			self.onselectionchanged.remove(fnc)

	def selectionchanged(self):
		try:
			self.selectedItem = self.getcurrentselection()
			for fnc in self.onselectionchanged:
				fnc()
		except Exception as ex:
			write_log('AEL BaseWall selectionchanged : ' + str(self.selectedItem) + '  ' + str(ex), DEFAULT_MODULE_NAME)

	def itemupdated(self, index=0):
		self.l.invalidateEntry(index)

	#def getCurrentPage(self):
	#	return self.instance.getCurrentPage()

	#def getPageCount(self):
	#	return self.instance.getPageCount()

	#def getItemsPerPage(self):
	#	return self.instance.getItemsPerPage()

	def getcurrentselection(self):
		cur = self.l.getCurrentSelection()
		return cur[0] if cur else None

	def postWidgetCreate(self, instance):
		self.instance = instance
		self.instance.setTransparent(1)
		self.instance.setContent(self.l)
		self.instance.selectionChanged.get().append(self.itemupdated)
		self.instance.selectionChanged.get().append(self.selectionchanged)
		self.instance.setWrapAround(True)

	def preWidgetRemove(self, instance):
		if self.instance:
			self.instance.selectionChanged.get().remove(self.itemupdated)
			self.instance.selectionChanged.get().remove(self.selectionchanged)
			self.instance.setContent(None)

	def setlist(self, lst):
		try:
			if self.instance is not None:
				self.instance.moveSelectionTo(0)
			self.l.setList(lst)
			self.list = lst
		except Exception as ex:
			write_log('set list : ' + str(ex), DEFAULT_MODULE_NAME)

	def getlist(self):
		return self.list

	def getCurrentIndex(self):
		if self.instance:
			return self.instance.getCurrentIndex()

	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)

	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)

	def left(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveLeft)

	def right(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveRight)

	def nextPage(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.nextPage)

	def prevPage(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.prevPage)

	def movetoIndex(self, index):
		if self.instance is not None:
			self.instance.moveSelectionTo(index)

	def movetoItem(self, item):
		pass

	def setentry(self, data):
		res = [None]
		return res

	def setSelectionEnable(self, how):
		if self.instance:
			self.instance.setSelectionEnable(how)

####################################################################################################################################


class EPGList(GUIComponent, object):
	GUI_WIDGET = eListbox

	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.recIcon = str(variables.get("EventLibraryEPGListsRecordIcon", '/usr/share/enigma2/AELImages/timer.png,')).replace(',', '')
		ffont, fsize = fonts.get("EventLibraryPlanersEventListFirstFont", ('Regular', 26))
		sfont, ssize = fonts.get("EventLibraryPlanersEventListSecondFont", ('Regular', 30))
		self.l.setItemHeight(int(parameters.get("EventLibraryPlanersEventListItemHeight", (70,))[0]))
		self.l.setFont(0, gFont(ffont, fsize))
		self.l.setFont(1, gFont(sfont, ssize))
		self.l.setBuildFunc(self.buildEntry)
		sel_changedCB = None
		self.onsel_changed = []
		if sel_changedCB is not None:  # TODO: wird nie aufgerufen, ist immer False
			self.onsel_changed.append(sel_changedCB)
		self.pixmapCache = {}
		self.selectedID = None
		self.l.setSelectableFunc(self.isSelectable)
		self.list = []

	def setList(self, list):
		self.l.setItemHeight(int(parameters.get("EventLibraryPlanersEventListItemHeight", (70,))[0]))
		self.l.setBuildFunc(self.buildEntry)
		self.l.setList(list)
		self.list = list

	def buildEntry(self, data):
		xp, yp, wp, hp = parameters.get("EventLibraryPlanersEventListPiconPosition", (10, 5, 100, 60))
		xrp, yrp, wrp, hrp = parameters.get("EventLibraryPlanersEventListRecordPiconPosition", (130, 5, 55, 30))
		x1, y1, w1, h1 = parameters.get("EventLibraryPlanersEventListFirstLine", (130, 0, 1100, 30))
		x2, y2, w2, h2 = parameters.get("EventLibraryPlanersEventListSecondLine", (130, 25, 1100, 60))
		width = self.l.getItemSize().width()
		height = self.l.getItemSize().height()
		flc = '#00ffffff'
		flcs = '#00ffffff'
		slc = '#00ffffff'
		slcs = '#00ffffff'
		if "EventLibraryListsFirstLineColor" in skin.colorNames:
			flc = f"#00{parseColor('EventLibraryListsFirstLineColor').argb():03x}"
		if "EventLibraryListsSecondLineColor" in skin.colorNames:
			slc = f"#00{parseColor('EventLibraryListsSecondLineColor').argb():03x}"
		if "EventLibraryListsFirstLineColorSelected" in skin.colorNames:
			flcs = f"#00{parseColor('EventLibraryListsFirstLineColorSelected').argb():03x}"
		if "EventLibraryListsSecondLineColorSelected" in skin.colorNames:
			slcs = f"#00{parseColor('EventLibraryListsSecondLineColorSelected').argb():03x}"
		res = [None]
		if int(data[2]) > 0:
			timeobj = datetime.fromtimestamp(data[3])
			_time = timeobj.strftime("%a   %d.%m.%Y   %H:%M")
			picon = self.findPicon(data[1], data[7])
			if data[5]:
				if isfile(self.recIcon):
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, xrp, yrp, wrp, hrp, LoadPixmap(self.recIcon), None, None, BT_SCALE | BT_FIXRATIO))
				res.append((eListboxPythonMultiContent.TYPE_TEXT, x1 + wrp + 20, y1, w1, h1, 0, RT_HALIGN_LEFT | RT_VALIGN_TOP, self.correctweekdays(_time), parseColor(flc).argb(), parseColor(flcs).argb()))
			else:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, x1, y1, w1, h1, 0, RT_HALIGN_LEFT | RT_VALIGN_TOP, self.correctweekdays(_time), parseColor(flc).argb(), parseColor(flcs).argb()))

			res.append((eListboxPythonMultiContent.TYPE_TEXT, x2, y2, w2, h2, 1, RT_HALIGN_LEFT | RT_VALIGN_TOP, data[0], parseColor(slc).argb(), parseColor(slcs).argb()))
			if picon:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, xp, yp, wp, hp, LoadPixmap(picon), None, None, BT_SCALE | BT_FIXRATIO))
			else:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, x1 + 300, y1, w1, h1, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, data[7], parseColor(flc).argb(), parseColor(flcs).argb()))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 20, 0, (width - 40), height, 1, RT_HALIGN_CENTER | RT_VALIGN_CENTER, data[0]))
		return res

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

	@staticmethod
	def isSelectable(data):
		return True

	def correctweekdays(self, itm):
#		_itm = _itm.replace("Mon", "Mo").replace("Tue", "Di").replace("Wed", "Mi").replace("Thu", "Do").replace("Fri", "Fr").replace("Sat", "Sa").replace("Sun", "So")
		return (_(itm))

	def connectsel_changed(self, func):
		if not self.onsel_changed.count(func):
			self.onsel_changed.append(func)

	def disconnectsel_changed(self, func):
		self.onsel_changed.remove(func)

	def selectionChanged(self):
		for x in self.onsel_changed:
			if x is not None:
				try:
					x()
				except Exception:  # TODO: FIXME!!!
					print("FIXME in EPGList.selectionChanged")

	def getCurrentSelection(self):
		cur = self.l.getCurrentSelection()
		return cur[0]

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
		self.instance.setWrapAround(True)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)

	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)

	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)

	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)

	def moveUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def updateListObject(self, row):
		index = self.getCurrentIndex()
		tmp = self.list[index]
		self.list[index] = (row,)
		self.l.invalidateEntry(index)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def setMode(self, mode):
		self.mode = mode

	def getList(self):
		return self.list

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)


class MenuList(GUIComponent, object):
	GUI_WIDGET = eListbox

	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		ffont, fsize = fonts.get("EventLibraryPlanersGenreListFont", ('Regular', 28))
		self.l.setItemHeight(int(parameters.get("EventLibraryPlanersGenreListItemHeight", (100,))[0]))
		self.l.setFont(0, gFont(ffont, fsize))
		self.l.setBuildFunc(self.buildEntry)
		sel_changedCB = None
		self.onsel_changed = []
		if sel_changedCB is not None:  # TODO: wird nie aufgerufen, ist immer False
			self.onsel_changed.append(sel_changedCB)
		self.pixmapCache = {}
		self.selectedID = None
		self.l.setSelectableFunc(self.isSelectable)
		self.list = []

	def setList(self, list):
		self.l.setItemHeight(int(parameters.get("EventLibraryPlanersGenreListItemHeight", (100,))[0]))
		self.l.setBuildFunc(self.buildEntry)
		self.l.setList(list)
		self.list = list

	def buildEntry(self, data):
		xp, yp, wp, hp = parameters.get("EventLibraryPlanersGenreListPiconPosition", (40, 5, 60, 60))
		x1, y1, w1, h1 = parameters.get("EventLibraryPlanersGenreListText", (0, 60, 140, 40))
		width = self.l.getItemSize().width()
		res = [None]

		res.append((eListboxPythonMultiContent.TYPE_TEXT, x1, y1, (width), h1, 0, RT_WRAP | RT_HALIGN_CENTER | RT_VALIGN_CENTER, data[0]))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, (int((width / 2) - (wp / 2))), yp, wp, hp, LoadPixmap(data[1]), None, None, BT_SCALE | BT_FIXRATIO))
		return res

	@staticmethod
	def isSelectable(data):
		return True

	def connectsel_changed(self, func):
		if not self.onsel_changed.count(func):
			self.onsel_changed.append(func)

	def disconnectsel_changed(self, func):
		self.onsel_changed.remove(func)

	def selectionChanged(self):
		for x in self.onsel_changed:
			if x is not None:
				try:
					x()
				except Exception:  # TODO: FIXME!!!
					print("FIXME in EPGList.selectionChanged")

	def getCurrentSelection(self):
		cur = self.l.getCurrentSelection()
		return cur[0]

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
		self.instance.setWrapAround(True)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)

	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)

	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)

	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)

	def moveUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def updateListObject(self, row):
		index = self.getCurrentIndex()
		tmp = self.list[index]
		self.list[index] = (row,)
		self.l.invalidateEntry(index)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def setMode(self, mode):
		self.mode = mode

	def getList(self):
		return self.list

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)


class AELLabel(VariableText, GUIComponent):
	def __init__(self, text=""):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.setText(text)

# html:
	def produceHTML(self):
		return self.getText()

# GUI:
	GUI_WIDGET = eLabel

	def getSize(self):
		s = self.instance.calculateSize()
		return (s.width(), s.height())


class MultiColorNTextLabel(AELLabel):
	def __init__(self, text=""):
		AELLabel.__init__(self, text)
		self.foreColors = []
		self.backColors = []
		self.texts = []
		self.positions = []

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			foregroundColor = None
			backgroundColor = None
			attribs = []
			for (attrib, value) in self.skinAttributes:
				if attrib == "foregroundColors":
					colors = value.split(',')
					for color in colors:
						self.foreColors.append(parseColor(color))
					if not foregroundColor:
						foregroundColor = colors[0]
				elif attrib == "backgroundColors":
					colors = value.split(',')
					for color in colors:
						self.backColors.append(parseColor(color))
					if not backgroundColor:
						backgroundColor = colors[0]
				elif attrib == "backgroundColor":
					backgroundColor = value
				elif attrib == "foregroundColor":
					foregroundColor = value
				elif attrib == "text":
					text = value.split(',')
					for txt in text:
						self.texts.append(txt)
				elif attrib == "positions":
					self.positions = eval(value)
				else:
					attribs.append((attrib, value))
			if foregroundColor:
				attribs.append(("foregroundColor", foregroundColor))
			if backgroundColor:
				attribs.append(("backgroundColor", backgroundColor))
			self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop, screen)

	def setForegroundColorNum(self, x):
		if self.instance and len(self.foreColors) > x:
			self.instance.setForegroundColor(self.foreColors[x])

	def setBackgroundColorNum(self, x):
		if self.instance and len(self.backColors) > x:
			self.instance.setBackgroundColor(self.backColors[x])

	def setTXT(self, x):
		if self.instance and len(self.texts) > x:
			self.instance.setText(self.texts[x])

	def setPosition(self, x):
		if self.instance and len(self.positions) > x:
			self.instance.move(ePoint(self.positions[x][0], self.positions[x][1]))


#def removeFiles():
#	filelist = glob(join("/tmp/", "*.jpg"))
#	for f in filelist:
#		remove(f)
