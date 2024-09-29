from os.path import isfile, exists
from time import localtime
from threading import Thread
from enigma import ePixmap, ePicLoad, ePoint, eSize, eWidget, loadPNG, iPlayableServicePtr, eServiceCenter
from skin import parseColor, parseColor
from Components.Renderer.Renderer import Renderer
from Components.Sources.CurrentService import CurrentService
from Components.Sources.ServiceEvent import ServiceEvent
from Tools import AdvancedEventLibrary

log = "/var/tmp/AdvancedEventLibrary.log"
screensWithEvent = ["ChannelSelection", "ChannelSelectionHorizontal", "InfoBarZapHistory", "NumberZapWithName", "ChannelSelection_summary", "AdvancedEventLibraryMediaHub", "AdvancedEventLibraryChannelSelection"]


class AdvancedEventLibraryImage(Renderer):
	IMAGE = "Image"
	PREFER_IMAGE = "preferImage"
	POSTER = "Poster"
	PREFER_POSTER = "preferPoster"
	IMAGE_THUMBNAIL = "ImageThumbnail"
	POSTER_THUMBNAIL = "PosterThumbnail"

	def __init__(self):
		Renderer.__init__(self)
		self.nameCache = {}
		self.ishide = True
		self.imageType = self.IMAGE
		self.WCover = self.HCover = 0
		self.foundImage = False
		self.foundPoster = False
		self.ifilename = None
		self.pfilename = None
		self.scalertype = 2
		self.sizetype = 'Poster'
		self.noImage = None
		self.rotate = "left"
		self.frameImage = None
		self.lastName = (None, None)
		self.screenName = ""
		if isfile('/usr/share/enigma2/Chamaeleon/png/pigframe.png'):
			self.frameImage = '/usr/share/enigma2/Chamaeleon/png/pigframe.png'
		self.coverPath = AdvancedEventLibrary.getPictureDir() + 'cover/'
		self.posterPath = AdvancedEventLibrary.getPictureDir() + 'poster/'
		self.db = AdvancedEventLibrary.getDB()
		self.ptr = None
		self.ptr2 = None

	GUI_WIDGET = eWidget

	def applySkin(self, desktop, screen):
		self.screenName = screen.skinName if (isinstance(screen.skinName, str)) else ', '.join(screen.skinName)
		if self.skinAttributes:
			attribs = []
			for attrib, value in self.skinAttributes:
				if attrib == 'size':
					attribs.append((attrib, value))
					x, y = value.split(',')
					self.WCover, self.HCover = int(x), int(y)
				elif attrib == 'position':
					attribs.append((attrib, value))
					x, y = value.split(',')
					self.x, self.y = int(x), int(y)
				elif attrib == 'foregroundColor':
					self.fg = parseColor(str(value))
				elif attrib == 'scale':
					self.scalertype = int(value)
				elif attrib == 'backgroundColor':
					attribs.append((attrib, value))
					self.bg = parseColor(str(value))
				elif attrib == 'imageType':
					params = str(value).split(",")
					self.imageType = params[0]
					if self.imageType == self.IMAGE_THUMBNAIL:
						self.coverPath = AdvancedEventLibrary.getPictureDir() + 'cover/thumbnails/'
					if self.imageType == self.POSTER_THUMBNAIL:
						self.posterPath = AdvancedEventLibrary.getPictureDir() + 'poster/thumbnails/'
					if len(params) > 1:
						self.frameImage = params[1]
						self.imageframe.setPixmap(loadPNG(self.frameImage)) if self.imageframe and isfile(self.frameImage) else None
					if len(params) > 2:
						self.noImage = params[2]
					if len(params) > 3:
						self.rotate = params[3]
				else:
					attribs.append((attrib, value))
			self.skinAttributes = attribs
		if self.frameImage and self.image and self.imageframe:
			self.image.resize(eSize(self.WCover - 20, self.HCover - 20))
			self.imageframe.resize(eSize(self.WCover, self.HCover))
			self.imageframe.setScale(1)
			self.imageframe.setAlphatest(1)
			self.image.move(ePoint(10, 10))
		elif self.image:
			self.image.resize(eSize(self.WCover, self.HCover))
		if self.image:
			self.image.setScale(self.scalertype)
		ret = Renderer.applySkin(self, desktop, screen)
		return ret

	def changed(self, what):
		if what[0] != self.CHANGED_CLEAR:
			event = None
			self.ptr = None
			self.ptr2 = None
			if not self.instance:
				return
			if isinstance(self.source, ServiceEvent):
				service = self.source.getCurrentService()
				sRef = service.toString()
				if '/' in sRef and '//' not in sRef:
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
						event = info.getEvent(service)
				else:
					if self.screenName in screensWithEvent:
						event = self.source.event
					else:
						info = eServiceCenter.getInstance().info(service)
						event = info.getEvent(service)
			elif hasattr(self.source, 'getEvent'):
				event = self.source.getEvent()
				if event and (isinstance(event, tuple) and event):
					event = event[0]
			elif hasattr(self.source, 'event'):
				if hasattr(self.source, 'service'):
					service = self.source.service
					if isinstance(service, iPlayableServicePtr):
						info = service and service.info()
						if not isinstance(self.source, CurrentService):
							ref = self.source.getCurrentlyPlayingServiceReference().toString()
							if '/' in ref:
								self.ptr = info.getName()
								event = info.getEvent(0)
							else:
								event = info.getEvent(0)
						else:
							self.ptr = info.getName()
							event = info.getEvent(0)
					else:
						event = self.source.event
						if (isinstance(event, tuple) and event):
							event = event[0]
				else:
					event = self.source.event
					if (isinstance(event, tuple) and event):
						event = event[0]
			if event:
				if not self.ptr:
					self.ptr = event.getEventName()
				self.ptr2 = self.ptr
				self.evt = self.db.getliveTV(event.getEventId(), str(event.getEventName()), event.getBeginTime())
				if self.evt and self.evt[0][3] != '':
					self.ptr = str(self.evt[0][3])
#				elif self.evt[0][7] != '':
#					name = self.evt[0][7] + ' - '
#					if self.evt[0][12] != '':
#						name += 'S' + str(self.evt[0][12]).zfill(2)
#					if self.evt[0][13] != "":
#						name += 'E' + str(self.evt[0][12]).zfill(2) + ' - '
#					if self.evt[0][2] != "":
#						name += self.evt[0][2] + ' - '
#					self.ptr = str(name[:-3])
			if self.ptr:
				self.ptr = AdvancedEventLibrary.convertDateInFileName(AdvancedEventLibrary.convertSearchName(self.ptr))
			if self.ptr2:
				self.ptr2 = AdvancedEventLibrary.convertDateInFileName(AdvancedEventLibrary.convertSearchName(self.ptr2))
			eventName = (self.ptr, self.ptr2)
			if self.lastName != eventName:
				thread = Thread(target=self.setthePixmap, args=(eventName,))
				thread.start()
#				self.setthePixmap(eventName)

	def GUIcreate(self, parent):
		self.instance = eWidget(parent)
		self.imageframe = ePixmap(self.instance)
		self.image = ePixmap(self.instance)
		if self.imageframe and self.frameImage:
			self.imageframe.setPixmap(loadPNG(self.frameImage))

	def GUIdelete(self):
		self.imageframe = None
		self.image = None
		self.instance = None
		AdvancedEventLibrary.clearMem(self.screenName)

	def showimage(self):
		if self.instance:
			self.instance.show()
		if self.imageframe:
			self.imageframe.show()
		if self.image:
			self.image.show()
		self.ishide = False

	def hideimage(self):
		if self.image:
			self.image.hide()
		if self.imageframe:
			self.imageframe.hide()
		if self.instance:
			self.instance.hide()
		self.ishide = True

	def onShow(self):
		self.suspended = False

	def onHide(self):
		self.suspended = True

	def setthePixmap(self, eventNames, run=0):
		self.lastName = eventNames
		self.foundPoster = False
		self.foundImage = False
		self.pfilename = None
		self.ifilename = None
		eventName = str(eventNames[0]) if run == 0 else str(eventNames[1])
		inCache = self.nameCache.get(eventName + str(self.imageType), "")
		if str(self.IMAGE) in inCache or str(self.IMAGE_THUMBNAIL) in inCache or str(self.PREFER_IMAGE) in inCache or str(self.PREFER_POSTER) in inCache:
			if isfile(inCache):
				self.ifilename = inCache
				self.foundImage = True
		elif (self.imageType == self.PREFER_IMAGE or self.imageType == self.IMAGE or self.imageType == self.IMAGE_THUMBNAIL or self.imageType == self.PREFER_POSTER):
			if not self.foundImage:
				self.ifilename = AdvancedEventLibrary.getImageFile(self.coverPath, eventName)
				if self.ifilename:
					self.foundImage = True
		if str(self.POSTER) in inCache or str(self.POSTER_THUMBNAIL) in inCache or str(self.PREFER_POSTER) in inCache or str(self.PREFER_IMAGE) in inCache:
			if isfile(inCache):
				self.pfilename = inCache
				self.foundPoster = True
		elif (self.imageType == self.PREFER_POSTER or self.imageType == self.POSTER or self.imageType == self.POSTER_THUMBNAIL or self.imageType == self.PREFER_IMAGE):
			self.pfilename = AdvancedEventLibrary.getImageFile(self.posterPath, eventName)
			if self.pfilename:
				self.foundPoster = True
		isLastRun = self.checkIsLastRun(run, str(eventNames[0]), str(eventNames[1]))
		# set alternative falls angegeben und nix gefunden
		if self.noImage and not self.foundImage and (self.imageType == self.PREFER_IMAGE or self.imageType == self.IMAGE or self.imageType == self.IMAGE_THUMBNAIL) and isLastRun:
			if (exists(self.noImage)):
				self.foundImage = True
				self.ifilename = self.noImage
		if self.noImage and not self.foundPoster and (self.imageType == self.PREFER_POSTER or self.imageType == self.POSTER or self.imageType == self.POSTER_THUMBNAIL) and isLastRun:
			if (exists(self.noImage)):
				self.foundPoster = True
				self.pfilename = self.noImage
		if self.ifilename:
			self.nameCache[eventName + str(self.imageType)] = str(self.ifilename)
		if self.pfilename:
			self.nameCache[eventName + str(self.imageType)] = str(self.pfilename)
		if (self.imageType == self.IMAGE or self.imageType == self.IMAGE_THUMBNAIL) and self.foundImage:
			self.loadPic(self.ifilename)
		elif (self.imageType == self.POSTER or self.imageType == self.POSTER_THUMBNAIL) and self.foundPoster:
			self.loadPic(self.pfilename)
		elif self.imageType == self.PREFER_IMAGE and self.foundImage:
			if self.sizetype != 'Image':
				self.calcSize('Image')
			self.sizetype = 'Image'
			self.loadPic(self.ifilename)
		elif self.imageType == self.PREFER_IMAGE and self.foundPoster:
			if self.sizetype != 'Poster':
				self.calcSize('Poster')
			self.sizetype = 'Poster'
			self.loadPic(self.pfilename)
		elif self.imageType == self.PREFER_POSTER and self.foundPoster:
			if self.sizetype != 'Poster':
				self.calcSize('Poster')
			self.sizetype = 'Poster'
			self.loadPic(self.pfilename)
		elif self.imageType == self.PREFER_POSTER and self.foundImage:
			if self.sizetype != 'Image':
				self.calcSize('Image')
			self.sizetype = 'Image'
			self.loadPic(self.ifilename)
		else:
			# if run == 0 and (str(eventNames[1]) != str(eventNames[0])) and (str(eventNames[1]) != "None"):
			if not isLastRun:
				self.setthePixmap(eventNames, 1)
			else:
				self.hideimage()

	def checkIsLastRun(self, run, eventName0, eventName1):
		return False if run == 0 and (eventName0 != eventName1) and (eventName1 != "None") else True

	def calcSize(self, how):
		if self.instance and how == 'Poster':
			self.instance.move(ePoint(self.x, self.y))
			self.instance.resize(eSize(self.WCover, self.HCover))
			if self.image and self.imageframe:
				self.image.resize(eSize(self.WCover - 20, self.HCover - 20))
				self.imageframe.resize(eSize(self.WCover, self.HCover))
			elif self.image:
				self.image.resize(eSize(self.WCover, self.HCover))
		elif self.instance and how == 'Image':
			if self.rotate == "left":
				self.instance.move(ePoint(self.x - self.HCover + self.WCover, self.y - self.WCover + self.HCover))
			self.instance.resize(eSize(self.HCover, self.WCover))
			if self.image and self.imageframe:
				self.image.resize(eSize(self.HCover - 20, self.WCover - 20))
				self.imageframe.resize(eSize(self.HCover, self.WCover))
			elif self.image:
				self.image.resize(eSize(self.HCover, self.WCover))
		else:
			return
		if self.image and self.imageframe:
			self.imageframe.setScale(1)
			self.imageframe.setAlphatest(1)
			self.image.move(ePoint(10, 10))

	def removeExtension(self, ext):
		ext = ext.replace('.wmv', '').replace('.mpeg2', '').replace('.ts', '').replace('.m2ts', '').replace('.mkv', '').replace('.avi', '').replace('.mpeg', '').replace('.mpg', '').replace('.iso', '').replace('.mp4', '')
		return ext

	def loadPic(self, picname):
		if self.image and picname != "":
			size = self.image.size()
			self.picload = ePicLoad()
			self.picload.PictureData.get().append(self.showCallback)
			if self.picload:
					self.picload.setPara((size.width(), size.height(), 0, 0, False, 1, "#00000000"))
					if self.picload.startDecode(picname) != 0:
						del self.picload
		else:
			self.hideimage()

	def showCallback(self, picInfo=None):
		if self.picload:
			picload = self.picload
			ptr = picload.getData()
			if self.image and ptr != None:
				self.image.setPixmap(ptr)
				if self.ishide:
					self.showimage()
			del picload
