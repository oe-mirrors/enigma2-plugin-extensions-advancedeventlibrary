from datetime import datetime
from math import trunc
from os.path import join
from enigma import eEPGCache, eListbox, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_VALIGN_TOP, ePicLoad
from skin import skin, variables, parameters, parseColor
from Components.config import config
from Components.Renderer.Renderer import Renderer
from Tools.AdvancedEventLibrary import aelGlobals, getPictureDir, getDB, getImageFile, clearMem, PicLoader


class AdvancedEventLibraryNextEventsList(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.nameCache = {}
		self.imageType = str(variables.get('EventLibraryEPGListsImageType', ('cover',))).replace(',', '').replace('(', '').replace(')', '').replace("'", '')
		self.imagePath = f"{getPictureDir()}{self.imageType}/thumbnails/"
		self.x = 1
		self.y = 140
		self.onSelChanged = []
		self.epgcache = eEPGCache.getInstance()
		self.l = eListboxPythonMultiContent()
		self.defaultImage = str(variables.get('EventLibraryEPGListsDefaultImage', (join(aelGlobals.SHAREPATH, "AELImages/movies.png"),))).replace(',', '').replace('(', '').replace(')', '').replace("'", '')
		ffont, fsize = parameters.get('EventLibraryEPGSingleListFirstFont', ('Regular', 26))
		sfont, ssize = parameters.get('EventLibraryEPGSingleListSecondFont', ('Regular', 30))
		self.l.setItemHeight(int(parameters.get('EventLibraryEPGSingleListItemHeight', (70,))[0]))
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

	def changed(self, what):
		if what[0] == self.CHANGED_CLEAR:
			self.text = ''
		else:
			elist = self.epgcache.lookupEvent(['RIBDT', (self.source.text, 0, -1, 720)])
			count = self.y / int(parameters.get('EventLibraryEPGSingleListItemHeight', (70,))[0])
			liste = elist[:trunc(count)]
			if liste and len(liste):
				liste.sort(key=lambda x: x[2])
			self.l.setList(liste)

	def correctweekdays(self, itm):
		_itm = str(itm)
		_itm = _itm.replace('Mon', 'Mo').replace('Tue', 'Di').replace('Wed', 'Mi').replace('Thu', 'Do').replace('Fri', 'Fr').replace('Sat', 'Sa').replace('Sun', 'So')
		return _itm

	def buildSingleEntry(self, service, eventId, beginTime, duration, EventName):
		xp, yp, wp, hp = parameters.get('EventLibraryEPGSingleListImagePosition', (10, 5, 100, 60))
		xrp, yrp, wrp, hrp = parameters.get('EventLibraryEPGSingleListRecordPiconPosition', (130, 5, 55, 30))
		x1, y1, w1, h1 = parameters.get('EventLibraryEPGSingleListFirstLine', (130, 0, 1100, 30))
		x2, y2, w2, h2 = parameters.get('EventLibraryEPGSingleListSecondLine', (130, 25, 1100, 60))
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
		timeobj = datetime.fromtimestamp(beginTime)
		_time = timeobj.strftime('%a   %d.%m.%Y   %H:%M')
		timeobj = datetime.fromtimestamp(beginTime + duration)
		_timeend = timeobj.strftime(' - %H:%M')
		dauer = '   (%d Min.)' % (duration / 60)
		dauer = str(dauer).replace('+', '')
		self.picloader = PicLoader(wp, hp)
		picon = self.picloader.load(self.getImageFiles(EventName, eventId))
		self.picloader.destroy()
		res.append((eListboxPythonMultiContent.TYPE_TEXT, x1, y1, w1, h1, 0, RT_HALIGN_LEFT | RT_VALIGN_TOP, self.correctweekdays(_time) + _timeend + str(dauer), parseColor(flc).argb(), parseColor(flcs).argb()))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, x2, y2, w2, h2, 1, RT_HALIGN_LEFT | RT_VALIGN_TOP, EventName, parseColor(slc).argb(), parseColor(slcs).argb()))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, xp, yp, wp, hp, picon))
		return res

	def getImageFiles(self, eventName, eventId):
		if self.nameCache.get(eventName, '') != '':
			return self.nameCache.get(eventName, '')
		else:
			if config.plugins.AdvancedEventLibrary.UsePreviewImages.value:
				evt = self.db.getliveTV(eventId, eventName)
				if evt and evt[0][3] != '' and not str(evt[0][3]).endswith('.jpg'):
					eventName = str(evt[0][3])
			coverFileName = getImageFile(self.imagePath, eventName)
			if coverFileName:
				self.nameCache[eventName] = str(coverFileName)
				return coverFileName
			return self.defaultImage
