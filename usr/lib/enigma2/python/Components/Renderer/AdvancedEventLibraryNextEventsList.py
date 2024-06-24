from Components.Renderer.Renderer import Renderer
from enigma import eEPGCache, eListbox, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, loadJPG, ePixmap, ePicLoad
from Tools.LoadPixmap import LoadPixmap
from Tools.AdvancedEventLibrary import getPictureDir, convertDateInFileName, convertTitle, convertTitle2, convert2base64, convertSearchName, getDB, getImageFile, clearMem
from Components.AVSwitch import AVSwitch
from Components.Pixmap import Pixmap
from Components.config import config, ConfigText, ConfigSubsection, ConfigYesNo
from time import localtime, time
from ServiceReference import ServiceReference
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
import skin
import datetime
import os
import re
import math

config.plugins.AdvancedEventLibrary = ConfigSubsection()
usePreviewImages = config.plugins.AdvancedEventLibrary.UsePreviewImages = ConfigYesNo(default=False)
previewImages = usePreviewImages.value or usePreviewImages.value == 'true'


class AdvancedEventLibraryNextEventsList(Renderer):

	def __init__(self):
		Renderer.__init__(self)
		self.nameCache = {}
		self.imageType = str(skin.variables.get('EventLibraryEPGListsImageType', ('cover',))).replace(',', '').replace('(', '').replace(')', '').replace("'", '')
		self.imagePath = getPictureDir() + self.imageType + '/thumbnails/'
		self.x = 1
		self.y = 140
		self.onSelChanged = []
		self.epgcache = eEPGCache.getInstance()
		self.l = eListboxPythonMultiContent()
		self.defaultImage = str(skin.variables.get('EventLibraryEPGListsDefaultImage', ('/usr/share/enigma2/AELImages/movies.png',))).replace(',', '').replace('(', '').replace(')', '').replace("'", '')
		ffont, fsize = skin.parameters.get('EventLibraryEPGSingleListFirstFont', ('Regular', 26))
		sfont, ssize = skin.parameters.get('EventLibraryEPGSingleListSecondFont', ('Regular', 30))
		self.l.setItemHeight(int(skin.parameters.get('EventLibraryEPGSingleListItemHeight', (70,))[0]))
		self.l.setFont(0, gFont(ffont, fsize))
		self.l.setFont(1, gFont(sfont, ssize))
		self.l.setBuildFunc(self.buildSingleEntry)
		self.db = getDB()

	def applySkin(self, desktop, parent):
		attribs = []
		for attrib, value in self.skinAttributes:
			if attrib == 'size':
				attribs.append((attrib, value))
				x, y = value.split(',')
				self.x, self.y = int(x), int(y)
			else:
				attribs.append((attrib, value))

		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	GUI_WIDGET = eListbox

	def connect(self, source):
		Renderer.connect(self, source)
		self.changed((self.CHANGED_DEFAULT,))

	def postWidgetCreate(self, instance):
		instance.setWrapAround(True)
		instance.setContent(self.l)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		clearMem("NextEventsList")
		return

	def changed(self, what):
		if what[0] == self.CHANGED_CLEAR:
			self.text = ''
		else:
			elist = self.epgcache.lookupEvent(['RIBDT', (self.source.text, 0, -1, 720)])
			count = self.y / int(skin.parameters.get('EventLibraryEPGSingleListItemHeight', (70,))[0])
			list = elist[:math.trunc(count)]
			if list and len(list):
				list.sort(key=lambda x: x[2])
			self.l.setList(list)

	def correctweekdays(self, itm):
		_itm = str(itm)
		_itm = _itm.replace('Mon', 'Mo').replace('Tue', 'Di').replace('Wed', 'Mi').replace('Thu', 'Do').replace('Fri', 'Fr').replace('Sat', 'Sa').replace('Sun', 'So')
		return _itm

	def buildSingleEntry(self, service, eventId, beginTime, duration, EventName):
		xp, yp, wp, hp = skin.parameters.get('EventLibraryEPGSingleListImagePosition', (10, 5, 100, 60))
		xrp, yrp, wrp, hrp = skin.parameters.get('EventLibraryEPGSingleListRecordPiconPosition', (130, 5, 55, 30))
		x1, y1, w1, h1 = skin.parameters.get('EventLibraryEPGSingleListFirstLine', (130, 0, 1100, 30))
		x2, y2, w2, h2 = skin.parameters.get('EventLibraryEPGSingleListSecondLine', (130, 25, 1100, 60))
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
		timeobj = datetime.datetime.fromtimestamp(beginTime)
		_time = timeobj.strftime('%a   %d.%m.%Y   %H:%M')
		timeobj = datetime.datetime.fromtimestamp(beginTime + duration)
		_timeend = timeobj.strftime(' - %H:%M')
		dauer = '   (%d Min.)' % (duration / 60)
		dauer = str(dauer).replace('+', '')
		self.picloader = PicLoader(wp, hp)
		picon = self.picloader.load(self.getImageFiles(EventName, eventId))
		self.picloader.destroy()
		res.append((eListboxPythonMultiContent.TYPE_TEXT, x1, y1, w1, h1, 0, RT_HALIGN_LEFT | RT_VALIGN_TOP, self.correctweekdays(_time) + _timeend + str(dauer), skin.parseColor(flc).argb(), skin.parseColor(flcs).argb()))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, x2, y2, w2, h2, 1, RT_HALIGN_LEFT | RT_VALIGN_TOP, EventName, skin.parseColor(slc).argb(), skin.parseColor(slcs).argb()))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, xp, yp, wp, hp, picon))
		return res

	def getImageFiles(self, eventName, eventId):
		if self.nameCache.get(eventName, '') != '':
			return self.nameCache.get(eventName, '')
		else:
			if previewImages:
				evt = self.db.getliveTV(eventId, eventName)
				if evt:
					if evt[0][3] != '' and not str(evt[0][3]).endswith('.jpg'):
						eventName = str(evt[0][3])
			coverFileName = getImageFile(self.imagePath, eventName)
			if coverFileName:
				self.nameCache[eventName] = str(coverFileName)
				return coverFileName
			return self.defaultImage


class PicLoader:

	def __init__(self, width, height, sc=None):
		self.picload = ePicLoad()
		if not sc:
			sc = AVSwitch().getFramebufferScale()
			self.picload.setPara((width, height, sc[0], sc[1], False, 1, '#ff000000'))

	def load(self, filename):
		self.picload.startDecode(filename, 0, 0, False)
		data = self.picload.getData()
		return data

	def destroy(self):
		del self.picload
