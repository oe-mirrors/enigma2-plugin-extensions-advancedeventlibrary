from datetime import datetime
from os.path import isfile, join
from time import localtime
from enigma import eEPGCache, eListbox, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_TOP
from skin import skin, variables, parameters, parseColor
from Components.config import config
from GUIComponent import GUIComponent
from ServiceReference import ServiceReference
from Tools.AdvancedEventLibrary import PicLoader, getImageFile, clearMem, aelGlobals
from Tools.LoadPixmap import LoadPixmap
import NavigationInstance
from Plugins.Extensions.AdvancedEventLibrary import _  # for localized messages

EPG_TYPE_SINGLE = 0
EPG_TYPE_MULTI = 1
EPG_TYPE_SIMILAR = 2
EPG_TYPE_INFOBAR = 3


class Rect:
	def __init__(self, x, y, width, height):
		self.x = x
		self.y = y
		self.w = width
		self.h = height

	def left(self):  # silly, but backward compatible
		return self.x

	def top(self):
		return self.y

	def height(self):
		return self.h

	def width(self):
		return self.w


class AEL_EPGList(GUIComponent):
	def __init__(self, type=EPG_TYPE_SINGLE, selChangedCB=None, timer=None):
		self.nameCache = {}
		self.days = (_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun"))
		self.imageType = str(variables.get("EventLibraryEPGListsImageType", ("cover",))).replace(",", "").replace("(", "").replace(")", "").replace(""", "")
		self.imagePath = f"{aelGlobals.HDDPATH}{self.imageType}/thumbnails/"
		self.timer = timer
		self.db = getDB()
		self.onSelChanged = []
		if selChangedCB is not None:
			self.onSelChanged.append(selChangedCB)
		GUIComponent.__init__(self)
		self.type = type
		self.l = eListboxPythonMultiContent()
		self.defaultImage = str(variables.get("EventLibraryEPGListsDefaultImage", (join(aelGlobals.SHAREPATH, "AELImages/movies.png"),))).replace(",", "").replace("(", "").replace(")", "").replace(""", "")
		if type == EPG_TYPE_SINGLE or type == EPG_TYPE_INFOBAR:
			ffont, fsize = parameters.get("EventLibraryEPGSingleListFirstFont", ("Regular", 26))
			sfont, ssize = parameters.get("EventLibraryEPGSingleListSecondFont", ("Regular", 30))
			self.l.setItemHeight(int(parameters.get("EventLibraryEPGSingleListItemHeight", (70,))[0]))
			self.l.setFont(0, gFont(ffont, fsize))
			self.l.setFont(1, gFont(sfont, ssize))
			self.l.setBuildFunc(self.buildSingleEntry)
		elif type == EPG_TYPE_MULTI:
			ffont, fsize = parameters.get("EventLibraryEPGMultiListFirstFont", ("Regular", 26))
			sfont, ssize = parameters.get("EventLibraryEPGMultiListSecondFont", ("Regular", 30))
			self.l.setItemHeight(int(parameters.get("EventLibraryEPGMultiListItemHeight", (70,))[0]))
			self.l.setFont(0, gFont(ffont, fsize))
			self.l.setFont(1, gFont(sfont, ssize))
			self.l.setBuildFunc(self.buildMultiEntry)
		else:
			assert (type == EPG_TYPE_SIMILAR)
			self.l.setFont(0, gFont("Regular", 28))
			self.l.setFont(1, gFont("Regular", 22))
			self.l.setBuildFunc(self.buildSimilarEntry)
		self.epgcache = eEPGCache.getInstance()
		self.clockPixmap = LoadPixmap(cached=True, path=join(aelGlobals.SKINPATH, "skin_default/icons/epgclock.png"))
		self.clockAddPixmap = LoadPixmap(cached=True, path=join(aelGlobals.SKINPATH, "skin_default/icons/epgclock_add.png"))
		self.clockPrePixmap = LoadPixmap(cached=True, path=join(aelGlobals.SKINPATH, "skin_default/icons/epgclock_pre.png"))
		self.clockPostPixmap = LoadPixmap(cached=True, path=join(aelGlobals.SKINPATH, "skin_default/icons/epgclock_post.png"))
		self.clockPrepostPixmap = LoadPixmap(cached=True, path=join(aelGlobals.SKINPATH, "skin_default/icons/epgclock_prepost.png"))

	def getEventFromId(self, service, eventid):
		event = None
		if self.epgcache is not None and eventid is not None:
			event = self.epgcache.lookupEventId(service.ref, eventid)
		return event

	def getCurrentChangeCount(self):
		if self.type == EPG_TYPE_MULTI and self.l.getCurrentSelection() is not None:
			return self.l.getCurrentSelection()[0]
		return 0

	def getCurrent(self):
		idx = 0
		if self.type == EPG_TYPE_MULTI:
			idx += 1
		tmp = self.l.getCurrentSelection()
		if tmp is None:
			return (None, None)
		eventid = tmp[idx + 1]
		service = ServiceReference(tmp[idx])
		event = self.getEventFromId(service, eventid)
		return (event, service)

	def moveUp(self):
		self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)

#	def connectSelectionChanged(func):
#		if not self.onSelChanged.count(func):
#			self.onSelChanged.append(func)

#	def disconnectSelectionChanged(func):
#		self.onSelChanged.remove(func)

	def selectionChanged(self):
		for x in self.onSelChanged:
			if x is not None:
				x()

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setWrapAround(True)
		instance.selectionChanged.get().append(self.selectionChanged)
		instance.setContent(self.l)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)
		clearMem("AEL-EPG-List")
		del self.nameCache

	def recalcEntrySize(self):
		esize = self.l.getItemSize()
		width = esize.width()
		height = esize.height()
		if self.type == EPG_TYPE_MULTI:
			xpos = 0
			w = width / 10 * 3
			self.serviceRect = Rect(xpos, 0, w - 10, height)
			xpos += w
			w = width / 10 * 2
			self.startEndRect = Rect(xpos, 0, w - 10, height)
			self.progress_rect = Rect(xpos, 4, w - 10, height - 8)
			xpos += w
			w = width / 10 * 5
			self.descrRect = Rect(xpos, 0, width, height)
		else:  # EPG_TYPE_SIMILAR
			self.weekdayRect = Rect(0, 0, width / 20 * 2 - 10, height)
			self.datetimeRect = Rect(width / 20 * 2, 0, width / 20 * 5 - 15, height)
			self.serviceRect = Rect(width / 20 * 7, 0, width / 20 * 13, height)

	def getClockPixmap(self, refstr, beginTime, duration, eventId):
		preClock = 1
		postClock = 2
		clockType = 0
		endTime = f"{beginTime}{duration}"
		if self.timer:
			for x in self.timer.timer_list:
				if x.service_ref.ref.toString() == refstr:
					if x.eit == eventId:
						return self.clockPixmap
					beg = x.begin
					end = x.end
					if beginTime > beg and beginTime < end and endTime > end:
						clockType |= preClock
					elif beginTime < beg and endTime > beg and endTime < end:
						clockType |= postClock
		if clockType == 0:
			return self.clockAddPixmap
		elif clockType == preClock:
			return self.clockPrePixmap
		elif clockType == postClock:
			return self.clockPostPixmap
		else:
			return self.clockPrepostPixmap

	def getPixmapForEntry(self, service, eventId, beginTime, duration):
		if self.timer:
			rec = beginTime and (self.timer.isInTimer(eventId, beginTime, duration, service))
			clockPic = self.getClockPixmap(service, beginTime, duration, eventId) if rec else ""
			return (clockPic, rec)

	def correctweekdays(self, itm):
		_itm = str(itm)
		_itm = _itm.replace("Mon", "Mo").replace("Tue", "Di").replace("Wed", "Mi").replace("Thu", "Do").replace("Fri", "Fr").replace("Sat", "Sa").replace("Sun", "So")
		return _itm

	def buildSingleEntry(self, service, eventId, beginTime, duration, EventName):
		(clockPic, rec) = self.getPixmapForEntry(service, eventId, beginTime, duration)

		xp, yp, wp, hp = parameters.get("EventLibraryEPGSingleListImagePosition", (10, 5, 100, 60))
		xrp, yrp, wrp, hrp = parameters.get("EventLibraryEPGSingleListRecordPiconPosition", (130, 5, 55, 30))
		x1, y1, w1, h1 = parameters.get("EventLibraryEPGSingleListFirstLine", (130, 0, 1100, 30))
		x2, y2, w2, h2 = parameters.get("EventLibraryEPGSingleListSecondLine", (130, 25, 1100, 60))
		width = self.l.getItemSize().width()
		flc, flcs, slc, slcs = "#00ffffff", "#00ffffff", "#00ffffff", "#00ffffff"
		if "EventLibraryListsFirstLineColor" in skin.colorNames:
			flc = "#00{:03x}".format(parseColor("EventLibraryListsFirstLineColor").argb())
		if "EventLibraryListsSecondLineColor" in skin.colorNames:
			slc = "#00{:03x}".format(parseColor("EventLibraryListsSecondLineColor").argb())
		if "EventLibraryListsFirstLineColorSelected" in skin.colorNames:
			flcs = "#00{:03x}".format(parseColor("EventLibraryListsFirstLineColorSelected").argb())
		if "EventLibraryListsSecondLineColorSelected" in skin.colorNames:
			slcs = "#00{:03x}".format(parseColor("EventLibraryListsSecondLineColorSelected").argb())
		res = [None]
		if beginTime is not None and duration is not None and eventId is not None:
			timeobj = datetime.fromtimestamp(beginTime)
			_time = timeobj.strftime("%a   %d.%m.%Y   %H:%M")
			timeobj = datetime.fromtimestamp(beginTime + duration)
			_timeend = timeobj.strftime(" - %H:%M")
			dauer = "   (%d Min.)" % (duration / 60)
			dauer = str(dauer).replace("+", "")
			self.picloader = PicLoader(wp, hp)
			picon = self.picloader.load(self.getImageFiles(EventName, eventId))
			self.picloader.destroy()
		else:
			dauer = ""
			_time = ""
			_timeend = ""
			rec = None
			picon = None
		if rec:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, xrp, yrp, wrp, hrp, clockPic))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, x1 + wrp + 20, y1, w1, h1, 0, RT_HALIGN_LEFT | RT_VALIGN_TOP, self.correctweekdays(_time) + _timeend + str(dauer), parseColor(flc).argb(), parseColor(flcs).argb()))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, x1, y1, w1, h1, 0, RT_HALIGN_LEFT | RT_VALIGN_TOP, self.correctweekdays(_time) + _timeend + str(dauer), parseColor(flc).argb(), parseColor(flcs).argb()))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, x2, y2, w2, h2, 1, RT_HALIGN_LEFT | RT_VALIGN_TOP, EventName, parseColor(slc).argb(), parseColor(slcs).argb()))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, xp, yp, wp, hp, picon))
		return res

	def buildSimilarEntry(self, service, eventId, beginTime, serviceName, duration):
		(clockPic, rec) = self.getPixmapForEntry(service, eventId, beginTime, duration)
		r1 = self.weekdayRect
		r2 = self.datetimeRect
		r3 = self.serviceRect
		t = localtime(beginTime)
		res = [
			None,  # no private data needed
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_RIGHT, self.days[t[6]]),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, r2.w, r1.h, 0, RT_HALIGN_RIGHT, "%2d.%02d, %02d:%02d" % (t[2], t[1], t[3], t[4]))
		]
		if rec:
			res.extend((
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, r3.x, r3.y, 21, 21, clockPic),
				(eListboxPythonMultiContent.TYPE_TEXT, r3.x + 25, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT, serviceName)
			))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT, serviceName))
		return res

	def buildMultiEntry(self, changecount, service, eventId, beginTime, duration, EventName, nowTime, serviceName):
		xp, yp, wp, hp = parameters.get("EventLibraryEPGMultiListImagePosition", (10, 5, 100, 60))
		xrp, yrp, wrp, hrp = parameters.get("EventLibraryEPGMultiListRecordPiconPosition", (130, 5, 55, 30))
		xpr, ypr, wpr, hpr = parameters.get("EventLibraryEPGMultiListProgressPosition", (10, 40, 55, 20))
		x1, y1, w1, h1 = parameters.get("EventLibraryEPGMultiListFirstLine", (130, 0, 1100, 30))
		x2, y2, w2, h2 = parameters.get("EventLibraryEPGMultiListSecondLine", (130, 25, 1100, 60))
		flc, flcs, slc, slcs = "#00ffffff", "#00ffffff", "#00ffffff", "#00ffffff"
		if "EventLibraryListsFirstLineColor" in skin.colorNames:
			flc = "#00{:03x}".format(parseColor("EventLibraryListsFirstLineColor").argb())
		if "EventLibraryListsSecondLineColor" in skin.colorNames:
			slc = "#00{:03x}".format(parseColor("EventLibraryListsSecondLineColor").argb())
		if "EventLibraryListsFirstLineColorSelected" in skin.colorNames:
			flcs = "#00{:03x}".format(parseColor("EventLibraryListsFirstLineColorSelected").argb())
		if "EventLibraryListsSecondLineColorSelected" in skin.colorNames:
			slcs = "#00{:03x}".format(parseColor("EventLibraryListsSecondLineColorSelected").argb())
		if beginTime is not None and duration is not None and eventId is not None:
			(clockPic, rec) = self.getPixmapForEntry(service, eventId, beginTime, duration)
			timeobj = datetime.fromtimestamp(beginTime)
			_time = timeobj.strftime("%a   %d.%m.%Y   %H:%M")
			timeobj = datetime.fromtimestamp(beginTime + duration)
			_timeend = timeobj.strftime(" - %H:%M")
			dauer = "   (%d Min.)" % (duration / 60)
			dauer = str(dauer).replace("+", "")
			self.picloader = PicLoader(wp, hp)
			picon = self.picloader.load(self.getImageFiles(EventName, eventId))
			self.picloader.destroy()
		else:
			dauer = ""
			_time = ""
			_timeend = ""
			rec = None
			picon = None
		res = [None]  # no private data needed
		if rec:
			res.extend(((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, xrp, yrp, wrp, hrp, clockPic),
						(eListboxPythonMultiContent.TYPE_TEXT, x1 + wrp + 20, y1, w1, h1, 0, RT_HALIGN_LEFT | RT_VALIGN_TOP, f"{self.correctweekdays(_time)}{_timeend}{dauer}", parseColor(flc).argb(), parseColor(flcs).argb())
						))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, x1, y1, w1, h1, 0, RT_HALIGN_LEFT | RT_VALIGN_TOP, f"{self.correctweekdays(_time)}{_timeend}{dauer}", parseColor(flc).argb(), parseColor(flcs).argb()))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, xp, yp, wp, hp, picon))
		if beginTime is not None:
			if nowTime < beginTime:
				begin = localtime(beginTime)
				end = localtime(beginTime + duration)
				res.append((eListboxPythonMultiContent.TYPE_TEXT, x2, y2, w2, h2, 1, RT_HALIGN_LEFT, f"{serviceName} - {EventName}", parseColor(slc).argb(), parseColor(slcs).argb()))
			else:
				percent = (nowTime - beginTime) * 100 / duration
				res.extend(((eListboxPythonMultiContent.TYPE_PROGRESS, xpr, ypr, wpr, hpr, percent),
							(eListboxPythonMultiContent.TYPE_TEXT, x2, y2, w2, h2, 1, RT_HALIGN_LEFT, f"{serviceName} - {EventName}", parseColor(slc).argb(), parseColor(slcs).argb())
							))
		return res

	def queryEPG(self, list, buildFunc=None):
		if self.epgcache is not None:
			return self.epgcache.lookupEvent(list, buildFunc) if buildFunc is not None else self.epgcache.lookupEvent(list)
		return []

	def fillMultiEPG(self, services, stime=-1):
		self.l.setItemHeight(int(parameters.get("EventLibraryEPGMultiListItemHeight", (70,))[0]))
		test = [(service.ref.toString(), 0, stime) for service in services]
		test.insert(0, "X0RIBDTCn")
		self.list = self.queryEPG(test)
		self.l.setList(self.list)
		self.selectionChanged()

	def updateMultiEPG(self, direction):
		test = [x[3] and (x[1], direction, x[3]) or (x[1], direction, 0) for x in self.list]
		test.insert(0, "XRIBDTCn")
		tmp = self.queryEPG(test)
		cnt = 0
		for x in tmp:
			changecount = self.list[cnt][0] + direction
			if changecount >= 0 and x[2] is not None:
				self.list[cnt] = (changecount, x[0], x[1], x[2], x[3], x[4], x[5], x[6])
			cnt += 1
		self.l.setList(self.list)
		self.selectionChanged()

	def fillSingleEPG(self, service):
		self.l.setItemHeight(int(parameters.get("EventLibraryEPGSingleListItemHeight", (70,))[0]))
		test = ["RIBDT", (service.ref.toString(), 0, -1, -1)]
		self.list = self.queryEPG(test)
		self.l.setList(self.list)
		self.selectionChanged()

	def sortSingleEPG(self, type):
		elist = self.list
		if elist:
			eventId = self.getSelectedEventId()
			if type == 1:
				elist.sort(key=lambda x: (x[4] and x[4].lower(), x[2]))
			else:
				assert (type == 0)
				elist.sort(key=lambda x: x[2])
			self.l.invalidate()
			self.moveToEventId(eventId)

	def getSelectedEventId(self):
		x = self.l.getCurrentSelection()
		return x and x[1]

	def moveToService(self, serviceref):
		if not serviceref:
			return
		index = 0
		refstr = serviceref.toString()
		for x in self.list:
			if x[1] == refstr:
				self.instance.moveSelectionTo(index)
				break
			index += 1

	def moveToEventId(self, eventId):
		if not eventId:
			return
		index = 0
		for x in self.list:
			if x[1] == eventId:
				self.instance.moveSelectionTo(index)
				break
			index += 1

	def fillSimilarList(self, refstr, eventId):
		if eventId is None:  # search similar broadcastings
			return
		ln = self.epgcache.search(("RIBND", 1024, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, refstr, eventId))
		if ln and len(ln):
			ln.sort(key=lambda x: x[2])
		self.l.setList(ln)
		self.selectionChanged()

	def fillEPGBar(self, service):
		self.fillSingleEPG(service)

	def reload(self):
		self.timer = NavigationInstance.instance.RecordTimer
		eventId = self.getSelectedEventId()
		cur = self.getCurrent()
		if cur[1]:
			if self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_INFOBAR:
				self.fillSingleEPG(cur[1])
				if eventId:
					self.moveToEventId(eventId)
			elif self.type == EPG_TYPE_MULTI:
				self.fillMultiEPG([cur[1]])

	def getImageFiles(self, eventName, eventId):
		niC = self.nameCache.get(eventName, "")
		if niC != "":
			if isfile(niC):
				return self.nameCache.get(eventName, "")
		else:
			if config.plugins.AdvancedEventLibrary.UsePreviewImages.value:
				evt = self.db.getliveTV(eventId, eventName)
				if evt and evt[0][3] != "" and not str(evt[0][3]).endswith(".jpg"):
					eventName = str(evt[0][3])
			coverFileName = getImageFile(self.imagePath, eventName)
			if coverFileName:
				self.nameCache[eventName] = str(coverFileName)
				return coverFileName
			return self.defaultImage
