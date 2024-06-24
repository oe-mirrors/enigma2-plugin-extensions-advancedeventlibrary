#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
from Components.GUIComponent import GUIComponent
from Components.VariableText import VariableText
from Components.HTMLComponent import HTMLComponent
from enigma import getDesktop, eListbox, eLabel, gFont, eListboxPythonMultiContent, ePicLoad, eRect, eSize, ePoint, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_VALIGN_BOTTOM, RT_WRAP, BT_SCALE, BT_FIXRATIO
from skin import parseColor
from collections import OrderedDict
from Components.AVSwitch import AVSwitch
from Tools.Directories import fileExists
from time import time, localtime
from Components.config import config
from Tools.Alternatives import GetWithAlternative
from Tools.LoadPixmap import LoadPixmap
from html.parser import HTMLParser
import glob
import os
import skin
import datetime

piconpath = config.usage.picon_dir.value

log = "/var/tmp/AdvancedEventLibrary.log"


def write_log(svalue):
	t = localtime()
	logtime = '%02d:%02d:%02d' % (t.tm_hour, t.tm_min, t.tm_sec)
	AdvancedEventLibrary_log = open(log, "a")
	AdvancedEventLibrary_log.write(str(logtime) + " : [AEL-Lists] : " + str(svalue) + "\n")
	AdvancedEventLibrary_log.close()


class ImageList(GUIComponent, object):
	GUI_WIDGET = eListbox

	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		desktopSize = getDesktop(0).size()
		if desktopSize.width() == 1920:
			ffont, fsize = skin.fonts.get("EventLibraryPictureListsFirstFont", ('Regular', 30))
			sfont, ssize = skin.fonts.get("EventLibraryPictureListsSecondFont", ('Regular', 26))
			self.l.setItemHeight(int(skin.parameters.get("EventLibraryPictureListsItemHeight", (108,))[0]))
		else:
			ffont, fsize = skin.fonts.get("EventLibraryPictureListsFirstFont", ('Regular', 20))
			sfont, ssize = skin.fonts.get("EventLibraryPictureListsSecondFont", ('Regular', 16))
			self.l.setItemHeight(int(skin.parameters.get("EventLibraryPictureListsItemHeight", (80,))[0]))
		self.l.setFont(0, gFont(ffont, fsize))
		self.l.setFont(1, gFont(sfont, ssize))
		self.l.setBuildFunc(self.buildEntry)
		sel_changedCB = None
		self.onsel_changed = []
		if sel_changedCB is not None:
			self.onsel_changed.append(sel_changedCB)
		self.l.setSelectableFunc(self.isSelectable)
		self.list = []
		return

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
				xcp, ycp, wcp, hcp = skin.parameters.get("EventLibraryCoverListCoverPosition", (10, 0, 192, 108))
				x1c, y1c, w1c, h1c = skin.parameters.get("EventLibraryCoverListFirstLine", (220, 0, 700, 54))
				x2c, y2c, w2c, h2c = skin.parameters.get("EventLibraryCoverListSecondLine", (220, 54, 700, 54))
				xpp, ypp, wpp, hpp = skin.parameters.get("EventLibraryCoverListPosterPosition", (10, 0, 70, 108))
				x1p, y1p, w1p, h1p = skin.parameters.get("EventLibraryPosterListFirstLine", (100, 0, 700, 54))
				x2p, y2p, w2p, h2p = skin.parameters.get("EventLibraryPosterListSecondLine", (100, 54, 700, 54))
			else:
				xcp, ycp, wcp, hcp = skin.parameters.get("EventLibraryCoverListCoverPosition", (10, 0, 142, 80))
				x1c, y1c, w1c, h1c = skin.parameters.get("EventLibraryCoverListFirstLine", (160, 0, 500, 40))
				x2c, y2c, w2c, h2c = skin.parameters.get("EventLibraryCoverListSecondLine", (160, 30, 500, 40))
				xpp, ypp, wpp, hpp = skin.parameters.get("EventLibraryCoverListPosterPosition", (10, 0, 70, 80))
				x1p, y1p, w1p, h1p = skin.parameters.get("EventLibraryPosterListFirstLine", (80, 0, 500, 40))
				x2p, y2p, w2p, h2p = skin.parameters.get("EventLibraryPosterListSecondLine", (80, 30, 500, 40))

			nDp = int(x1p) - int(wpp)
			nDc = int(x1c) - int(wcp)
			if self.how == 1:
				if data[1] == 'Cover':
					if data[5]:
						desktopSize = getDesktop(0).size()
						if desktopSize.width() == 1920:
							self.picloader = PicLoader(192, 108)
						else:
							self.picloader = PicLoader(142, 80)
						picon = self.picloader.load('/tmp/' + data[5])
						self.picloader.destroy()
						fSize = round(float(os.path.getsize('/tmp/' + data[5]) / 1024.0), 1)
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
						fSize = round(float(os.path.getsize('/tmp/' + data[5]) / 1024.0), 1)
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
						fSize = round(float(os.path.getsize(data[3]) / 1024.0), 1)
						fSize = str(fSize) + " kB "
						date = os.path.getmtime(data[3])
						timeobj = datetime.datetime.fromtimestamp(date)
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
						fSize = round(float(os.path.getsize(data[3]) / 1024.0), 1)
						fSize = str(fSize) + " kB "
						date = os.path.getmtime(data[3])
						timeobj = datetime.datetime.fromtimestamp(date)
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
				except:
					print('FIXME in ElementList.selectionChanged')

	def getCurrentSelection(self):
		cur = self.l.getCurrentSelection()
		return cur[0]

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
		self.instance.setWrapAround(True)
		return

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)
		return

	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveTop)
		return

	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveEnd)
		return

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)
		return

	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)
		return

	def moveUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)
		return

	def moveDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)
		return

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
		return


class SearchResultsList(GUIComponent, object):
	GUI_WIDGET = eListbox

	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		ffont, fsize = skin.fonts.get("EventLibrarySearchListFirstFont", ('Regular', 32))
		sfont, ssize = skin.fonts.get("EventLibrarySearchListSecondFont", ('Regular', 28))
		self.l.setItemHeight(int(skin.parameters.get("EventLibrarySearchListItemHeight", (80,))[0]))
		self.l.setFont(0, gFont(ffont, fsize))
		self.l.setFont(1, gFont(sfont, ssize))

		self.l.setBuildFunc(self.buildEntry)
		sel_changedCB = None
		self.onsel_changed = []
		if sel_changedCB is not None:
			self.onsel_changed.append(sel_changedCB)
		self.l.setSelectableFunc(self.isSelectable)
		self.list = []
		self.htmlParser = HTMLParser()
		return

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
			x1, y1, w1, h1 = skin.parameters.get("EventLibrarySearchListFirstLine", (20, 0, 1600, 40))
			x2, y2, w2, h2 = skin.parameters.get("EventLibrarySearchListSecondLine", (20, 40, 1600, 40))
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
					countries = str(data[1]) + " " + str(self.htmlParser.unescape('&#xB7;')) + " "
				if data[2]:
					year = str(data[2]) + " " + str(self.htmlParser.unescape('&#xB7;')) + " "
				if data[3]:
					genres = str(data[3]) + " " + str(self.htmlParser.unescape('&#xB7;')) + " "
				if data[4]:
					rating = "Bewertung : " + str(data[4]) + " " + str(self.htmlParser.unescape('&#xB7;')) + " "
				if data[5]:
					fsk = "FSK : " + str(data[5]) + " " + str(self.htmlParser.unescape('&#xB7;')) + " "
				details = genres + countries + year + rating + fsk
				details = details[:-2]
				res.append((eListboxPythonMultiContent.TYPE_TEXT, x1, y1, w1, h1, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, str(data[0]) + " " + str(self.htmlParser.unescape('&#xB7;')) + " (" + str(data[6]) + ")"))
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
				except:
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
		return

	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveTop)
		return

	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveEnd)
		return

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)
		return

	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)
		return

	def moveUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)
		return

	def moveDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)
		return

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
		return

####################################################################################################################################


class MovieList(GUIComponent, object):
	GUI_WIDGET = eListbox

	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.recIcon = str(skin.variables.get("EventLibraryEPGListsRecordIcon", '/usr/share/enigma2/AELImages/timer.png,')).replace(',', '')
		ffont, fsize = skin.fonts.get("EventLibraryPlanersEventListFirstFont", ('Regular', 26))
		sfont, ssize = skin.fonts.get("EventLibraryPlanersEventListSecondFont", ('Regular', 30))
		self.l.setFont(0, gFont(ffont, fsize))
		self.l.setFont(1, gFont(sfont, ssize))
		sel_changedCB = None
		self.onsel_changed = []
		if sel_changedCB is not None:
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
		return

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
					self.l.setFont(0, skin.parseFont(value, ((1, 1), (1, 1))))
				elif attrib == "secondFont":
					self.l.setFont(1, skin.parseFont(value, ((1, 1), (1, 1))))
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
		recIcon = str(skin.variables.get("EventLibraryEPGListsRecordIcon", '/usr/share/enigma2/AELImages/timer.png,')).replace(',', '')
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
				except:  # FIXME!!!
					print("FIXME in EPGList.selectionChanged")
					pass

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
		return

	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)
		return

	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)
		return

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)
		return

	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)
		return

	def moveUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)
		return

	def moveDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)
		return

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
		return

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
				elif attrib == "viewMode":
					self.instance.setOrientation(
						{"wall": eListbox.orGrid,
						 "list_horizontal": eListbox.orHorizontal,
							"list_vertical": eListbox.orVertical,
						 }[value])
				elif attrib == "itemSize":
					self.l.setItemWidth(int(value.split(',')[0]))
					self.l.setItemHeight(int(value.split(',')[1]))
				elif attrib == "itemScale":
					self.instance.setSelectionZoom(float(value))
				elif attrib == "itemSpace":
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
				#elif attrib == "useShadow":
				#	self.l.setShadow(int(value))
				elif attrib == "useOverlay":
					self.l.setOverlay(int(value))
				elif attrib == "downloadPath":
					self.l.setDownloadPath(str(value))
				#elif attrib == "backgroundColorGlobal":
				#	self.l.setGlobalBackgroundColor(skin.parseColor(str(value)))
				elif attrib == "borderColor":
					self.instance.setBorderColor(skin.parseColor(str(value)))
				elif attrib == "borderWidth":
					self.borderwidth = int(value)
					self.instance.setBorderWidth(self.borderwidth)
				elif attrib == "animated":
					self.instance.setAnimation(int(value))
				elif attrib == "backgroundColor":
					self.instance.setBackgroundColor(skin.parseColor(str(value)))
					self.backgroundColor = str(value)
				elif attrib == "backgroundColorSelected":
					self.instance.setBackgroundColorSelected(skin.parseColor(str(value)))
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
		recIcon = str(skin.variables.get("EventLibraryEPGListsRecordIcon", '/usr/share/enigma2/AELImages/timer.png,')).replace(',', '')
		return (self.l.getItemSize().width(), self.l.getItemSize().height(), self.maxTextLength, self.imageType, self.folderImage, self.substituteImage, self.fc, self.fcs, self.textHeightPercent, self.progressForegroundColor, self.progressBackgroundColor, self.progressForegroundColorSelected, self.progressBackgroundColorSelected, self.progressBorderWidth, recIcon, self.scrambledImage, self.imagePos, self.recIconPos, self.firstLinePos, self.secondLinePos, self.piconPos, self.control, self.coverings, self.progressPos, self.fontOrientation, self.backgroundColor, self.timeFormat)

	def isselectable(self, data):
		return True

	def refresh(self):
		#TODO add refresh function
		# self.l.refresh()
		return

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
			write_log('AEL BaseWall selectionchanged : ' + str(self.selectedItem) + '  ' + str(ex))

	def itemupdated(self, index=0):
		self.l.invalidateEntry(index)

	#def getCurrentPage(self):
	#	return self.instance.getCurrentPage()

	#def getPageCount(self):
	#	return self.instance.getPageCount()

	#def getItemsPerPage(self):
	#	return self.instance.getItemsPerPage()

	def getcurrentselection(self):
		try:
			cur = self.l.getCurrentSelection()
			if cur:
				return cur[0]
			else:
				return None
		except Exception as ex:
			write_log('AEL BaseWall getcurrentselectiond : ' + str(cur) + '  ' + str(ex))
			return None

	def postWidgetCreate(self, instance):
		self.instance = instance
		self.instance.setTransparent(1)
		self.instance.setContent(self.l)
		self.instance.selectionChanged.get().append(self.itemupdated)
		self.instance.selectionChanged.get().append(self.selectionchanged)
		self.instance.setWrapAround(True)

	def preWidgetRemove(self, instance):
		self.instance.selectionChanged.get().remove(self.itemupdated)
		self.instance.selectionChanged.get().remove(self.selectionchanged)
		self.instance.setContent(None)
		return

	def setlist(self, l):
		try:
			if self.instance is not None:
				self.instance.moveSelectionTo(0)
			self.l.setList(l)
			self.list = l
		except Exception as ex:
			write_log('set list : ' + str(ex))

	def getlist(self):
		return self.list

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)
		return

	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)
		return

	def left(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveLeft)
		return

	def right(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveRight)
		return

	def nextPage(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.nextPage)
		return

	def prevPage(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.prevPage)
		return

	def movetoIndex(self, index):
		if self.instance is not None:
			self.instance.moveSelectionTo(index)
		return

	def movetoItem(self, item):
		pass

	def setentry(self, data):
		res = [None]
		print(data)
		return res

	def setSelectionEnable(self, how):
		self.instance.setSelectionEnable(how)

####################################################################################################################################


class EPGList(GUIComponent, object):
	GUI_WIDGET = eListbox

	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.recIcon = str(skin.variables.get("EventLibraryEPGListsRecordIcon", '/usr/share/enigma2/AELImages/timer.png,')).replace(',', '')
		ffont, fsize = skin.fonts.get("EventLibraryPlanersEventListFirstFont", ('Regular', 26))
		sfont, ssize = skin.fonts.get("EventLibraryPlanersEventListSecondFont", ('Regular', 30))
		self.l.setItemHeight(int(skin.parameters.get("EventLibraryPlanersEventListItemHeight", (70,))[0]))
		self.l.setFont(0, gFont(ffont, fsize))
		self.l.setFont(1, gFont(sfont, ssize))
		self.l.setBuildFunc(self.buildEntry)
		sel_changedCB = None
		self.onsel_changed = []
		if sel_changedCB is not None:
			self.onsel_changed.append(sel_changedCB)
		self.pixmapCache = {}
		self.selectedID = None
		self.l.setSelectableFunc(self.isSelectable)
		self.list = []
		return

	def setList(self, list):
		self.l.setItemHeight(int(skin.parameters.get("EventLibraryPlanersEventListItemHeight", (70,))[0]))
		self.l.setBuildFunc(self.buildEntry)
		self.l.setList(list)
		self.list = list

	def buildEntry(self, data):
		xp, yp, wp, hp = skin.parameters.get("EventLibraryPlanersEventListPiconPosition", (10, 5, 100, 60))
		xrp, yrp, wrp, hrp = skin.parameters.get("EventLibraryPlanersEventListRecordPiconPosition", (130, 5, 55, 30))
		x1, y1, w1, h1 = skin.parameters.get("EventLibraryPlanersEventListFirstLine", (130, 0, 1100, 30))
		x2, y2, w2, h2 = skin.parameters.get("EventLibraryPlanersEventListSecondLine", (130, 25, 1100, 60))
		width = self.l.getItemSize().width()
		height = self.l.getItemSize().height()

		flc = '#00ffffff'
		flcs = '#00ffffff'
		slc = '#00ffffff'
		slcs = '#00ffffff'
		if "EventLibraryListsFirstLineColor" in skin.colorNames:
			flc = '#00{:03x}'.format(skin.parseColor("EventLibraryListsFirstLineColor").argb())
		if "EventLibraryListsSecondLineColor" in skin.colorNames:
			slc = '#00{:03x}'.format(skin.parseColor("EventLibraryListsSecondLineColor").argb())
		if "EventLibraryListsFirstLineColorSelected" in skin.colorNames:
			flcs = '#00{:03x}'.format(skin.parseColor("EventLibraryListsFirstLineColorSelected").argb())
		if "EventLibraryListsSecondLineColorSelected" in skin.colorNames:
			slcs = '#00{:03x}'.format(skin.parseColor("EventLibraryListsSecondLineColorSelected").argb())

		res = [None]
		if int(data[2]) > 0:
			timeobj = datetime.datetime.fromtimestamp(data[3])
			_time = timeobj.strftime("%a   %d.%m.%Y   %H:%M")

			picon = self.findPicon(data[1], data[7])

			if data[5]:
				if os.path.isfile(self.recIcon):
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, xrp, yrp, wrp, hrp, LoadPixmap(self.recIcon), None, None, BT_SCALE | BT_FIXRATIO))
				res.append((eListboxPythonMultiContent.TYPE_TEXT, x1 + wrp + 20, y1, w1, h1, 0, RT_HALIGN_LEFT | RT_VALIGN_TOP, self.correctweekdays(_time), skin.parseColor(flc).argb(), skin.parseColor(flcs).argb()))
			else:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, x1, y1, w1, h1, 0, RT_HALIGN_LEFT | RT_VALIGN_TOP, self.correctweekdays(_time), skin.parseColor(flc).argb(), skin.parseColor(flcs).argb()))

			res.append((eListboxPythonMultiContent.TYPE_TEXT, x2, y2, w2, h2, 1, RT_HALIGN_LEFT | RT_VALIGN_TOP, data[0], skin.parseColor(slc).argb(), skin.parseColor(slcs).argb()))
			if picon:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, xp, yp, wp, hp, LoadPixmap(picon), None, None, BT_SCALE | BT_FIXRATIO))
			else:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, x1 + 300, y1, w1, h1, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, data[7], skin.parseColor(flc).argb(), skin.parseColor(flcs).argb()))
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
			pngname = os.path.join(piconpath, service + ".png")
			if os.path.isfile(pngname):
				return pngname
		if serviceName is not None:
			pngname = os.path.join(piconpath, serviceName + ".png")
			if os.path.isfile(pngname):
				return pngname
		return None

	@staticmethod
	def isSelectable(data):
		return True

	def correctweekdays(self, itm):
		_itm = str(itm)
		_itm = _itm.replace("Mon", "Mo").replace("Tue", "Di").replace("Wed", "Mi").replace("Thu", "Do").replace("Fri", "Fr").replace("Sat", "Sa").replace("Sun", "So")
		return _itm

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
				except:  # FIXME!!!
					print("FIXME in EPGList.selectionChanged")
					pass

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
		return

	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)
		return

	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)
		return

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)
		return

	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)
		return

	def moveUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)
		return

	def moveDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)
		return

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
		ffont, fsize = skin.fonts.get("EventLibraryPlanersGenreListFont", ('Regular', 28))
		self.l.setItemHeight(int(skin.parameters.get("EventLibraryPlanersGenreListItemHeight", (100,))[0]))
		self.l.setFont(0, gFont(ffont, fsize))
		self.l.setBuildFunc(self.buildEntry)
		sel_changedCB = None
		self.onsel_changed = []
		if sel_changedCB is not None:
			self.onsel_changed.append(sel_changedCB)
		self.pixmapCache = {}
		self.selectedID = None
		self.l.setSelectableFunc(self.isSelectable)
		self.list = []
		return

	def setList(self, list):
		self.l.setItemHeight(int(skin.parameters.get("EventLibraryPlanersGenreListItemHeight", (100,))[0]))
		self.l.setBuildFunc(self.buildEntry)
		self.l.setList(list)
		self.list = list

	def buildEntry(self, data):
		xp, yp, wp, hp = skin.parameters.get("EventLibraryPlanersGenreListPiconPosition", (40, 5, 60, 60))
		x1, y1, w1, h1 = skin.parameters.get("EventLibraryPlanersGenreListText", (0, 60, 140, 40))
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
				except:  # FIXME!!!
					print("FIXME in EPGList.selectionChanged")
					pass

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
		return

	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)
		return

	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)
		return

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)
		return

	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)
		return

	def moveUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)
		return

	def moveDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)
		return

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


class AELLabel(VariableText, HTMLComponent, GUIComponent):
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
		if self.instance:
			if len(self.foreColors) > x:
				self.instance.setForegroundColor(self.foreColors[x])

	def setBackgroundColorNum(self, x):
		if self.instance:
			if len(self.backColors) > x:
				self.instance.setBackgroundColor(self.backColors[x])

	def setTXT(self, x):
		if self.instance:
			if len(self.texts) > x:
				self.instance.setText(self.texts[x])

	def setPosition(self, x):
		if self.instance:
			if len(self.positions) > x:
				self.instance.move(ePoint(self.positions[x][0], self.positions[x][1]))


class PicLoader:
	def __init__(self, width, height, sc=None, color="#ff000000"):
		self.picload = ePicLoad()
		if not sc:
			sc = AVSwitch().getFramebufferScale()
			self.picload.setPara((width, height, sc[0], sc[1], False, 1, color))

	def load(self, filename):
		if fileExists(filename):
			self.picload.startDecode(filename, 0, 0, False)
			data = self.picload.getData()
			return data
		else:
			return None

	def destroy(self):
		del self.picload


def removeFiles():
	filelist = glob.glob(os.path.join("/tmp/", "*.jpg"))
	for f in filelist:
		os.remove(f)
