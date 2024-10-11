#=================================================
# R140 by MyFriendVTI
# usr/lib/enigma2/python/Components/Renderer/AdvancedEventLibraryImage.py
# Aenderungen kommentiert mit hinzugefuegt, geaendert oder geloescht
# Aenderung (#1): ePicload Crash verhindern
# Aenderung (#2): Fehler reRun behoben
# Aenderung (#3): Fix-Poster (Streaming) [by schomi]
# Hinzugefuegt (#4): preferType
# Hinzugefuegt (#5): FrameSize
# Hinzugefuegt (#6): Fix BlackCover at Startup
# Hinzugefuegt (#7): Fix Image-Timing
# Hinzugefuegt (#8): Fix Kanalliste-Sendungswechsel
# Aenderung (#9): Fix Bildpfad-Cache
# ==================================================
from os import makedirs, remove
from os.path import isfile, exists, join
from PIL import Image
from twisted.internet.reactor import callInThread
from enigma import ePixmap, ePicLoad, ePoint, eSize, eWidget, loadPNG, iPlayableServicePtr, eServiceCenter
from skin import parseColor
from Components.Renderer.Renderer import Renderer
from Components.Sources.CurrentService import CurrentService
from Components.Sources.ServiceEvent import ServiceEvent
from Tools.AdvancedEventLibrary import write_log, getDB, convertDateInFileName, convertSearchName, clearMem, getImageFile, aelGlobals
from Tools.BoundFunction import boundFunction

DEFAULT_MODULE_NAME = __name__.split(".")[-1]
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
		filename = join(aelGlobals.SHAREPATH, "Chamaeleon/png/pigframe.png")
		if isfile(filename):
			self.frameImage = filename
		self.coverPath = aelGlobals.COVERPATH
		self.posterPath = aelGlobals.POSTERPATH
		self.db = getDB()
		self.ptr = None
		self.ptr2 = None
		#==== Hinzugefugt (#4/#5/#7) =====
		self.preferType = ""
		tempImgFolder = "/tmp/AELTemp"
		if not exists(tempImgFolder):
			makedirs(tempImgFolder)
		self.preferImgPath = join(tempImgFolder, f"{str(id(self))}.jpg")
		self.frameSize = 10
		self.requestNr = 0
		# ==========================
	GUI_WIDGET = eWidget

	def applySkin(self, desktop, screen):
		self.screenName = screen.skinName if (isinstance(screen.skinName, str)) else ', '.join(screen.skinName)
		#==== Hinzugefugt (#8) =====
		if "ChannelSelection" in str(screen):
			screen.onShown.append(boundFunction(self.changed, (1,)))
		# ==========================
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
						self.coverPath = f"{aelGlobals.COVERPATH}thumbnails/"
					if self.imageType == self.POSTER_THUMBNAIL:
						self.posterPath = f"{aelGlobals.POSTERPATH}thumbnails/"
					if len(params) > 1:
						self.frameImage = params[1]
						self.imageframe.setPixmap(loadPNG(self.frameImage)) if self.imageframe and isfile(self.frameImage) else None
					if len(params) > 2:
						self.noImage = params[2]
					if len(params) > 3:
						self.rotate = params[3]
					#==== Hinzugefugt (#4/#5) =====
					if len(params) > 4 and params[4]:
						self.preferType = params[4]
						if self.preferType.startswith("PI"):
							self.imageType = self.PREFER_POSTER
						elif self.preferType.startswith("IP"):
							self.imageType = self.PREFER_IMAGE
						if self.preferType.endswith("_Thumb"):
							self.coverPath = f"{aelGlobals.COVERPATH}thumbnails/"
							self.posterPath = f"{aelGlobals.POSTERPATH}thumbnails"
							self.preferType.replace("_Thumb", "")
						else:
							self.coverPath = aelGlobals.COVERPATH
							self.posterPath = aelGlobals.POSTERPATH
					if len(params) > 5 and params[5]:
						self.frameImage = params[5]
						if self.imageframe and isfile(self.frameImage):
							self.imageframe.setPixmap(loadPNG(self.frameImage))
						else:
							self.frameImage = None
					if len(params) > 6 and params[6]:
						self.frameSize = int(params[6])
					# ==========================
				else:
					attribs.append((attrib, value))
			self.skinAttributes = attribs
		if self.frameImage and self.image and self.imageframe:
			#==== geaendert (#5) =====
			#self.image.resize(eSize(self.WCover-20, self.HCover-20))
			self.image.resize(eSize(self.WCover - (2 * self.frameSize), self.HCover - (2 * self.frameSize)))
			# ==========================
			self.imageframe.resize(eSize(self.WCover, self.HCover))
			self.imageframe.setScale(1)
			self.imageframe.setAlphatest(1)
			#==== geaendert (#5) =====
			#self.image.move(ePoint(10, 10))
			self.image.move(ePoint(self.frameSize, self.frameSize))
			# ==========================
		elif self.image:
			self.image.resize(eSize(self.WCover, self.HCover))
			#==== hinzugefuegt (#5) =====
			self.frameSize = 0
			# ==========================
		if self.image:
			self.image.setScale(self.scalertype)
			#=========== hinzugefuegt (#6) =========
			self.hideimage()
			# ==========================
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
				self.ptr = convertDateInFileName(convertSearchName(self.ptr))
			if self.ptr2:
				self.ptr2 = convertDateInFileName(convertSearchName(self.ptr2))
			eventName = (self.ptr, self.ptr2)
			if self.lastName != eventName:
				callInThread(self.setthePixmap, (eventName,))
#				self.setthePixmap(eventName)

	def GUIcreate(self, parent):
		self.instance = eWidget(parent)
		#==== hinzugefuegt (#6) ====
		self.instance.setTransparent(1)
		# ==========================
		self.imageframe = ePixmap(self.instance)
		#====== hinzugefuegt (#5) ========
		self.imageframe.hide()
		# ================================
		self.image = ePixmap(self.instance)
		if self.imageframe and self.frameImage:
			self.imageframe.setPixmap(loadPNG(self.frameImage))

	def GUIdelete(self):
		self.imageframe = None
		self.image = None
		self.instance = None
		clearMem(self.screenName)

	def showimage(self):
		if self.instance:
			self.instance.show()
		if self.imageframe:
			self.imageframe.show()
		if self.image:
			self.image.show()
		self.ishide = False

	#======= geaendert (#4) =======
	#def hideimage(self):
	def hideimage(self, isSizeSwitch=False):
	# ==============================
		if self.image:
			self.image.hide()
		if self.imageframe:
			self.imageframe.hide()
		if self.instance:
			#======= geaendert (#4) =======
			#self.instance.hide()
			if not isSizeSwitch:
				self.instance.hide()
			# ============================
		self.ishide = True

	def onShow(self):
		self.suspended = False

	def onHide(self):
		self.suspended = True

	def setthePixmap(self, eventNames, run=0):
		self.lastName = eventNames
		#======= hinzugefuegt (#7) =======
		self.requestNr = self.requestNr + 1
		# ==============================
		#======= hinzugefuegt (#4) =======
#		if run == 0:
		# ==============================
		self.foundPoster = False
		self.foundImage = False
		self.pfilename = None
		self.ifilename = None
		eventName = str(eventNames[0]) if run == 0 else str(eventNames[1])
		inCache = self.nameCache.get(eventName + str(self.imageType), "")
		#======= geaendert (#9) Alter Code unplausibel =======
		#if str(self.IMAGE) in inCache or str(self.IMAGE_THUMBNAIL) in inCache or str(self.PREFER_IMAGE) in inCache or str(self.PREFER_POSTER) in inCache:
		if inCache and not self.foundImage and self.imageType != self.PREFER_POSTER and self.imageType != self.PREFER_IMAGE:
		# ==============================
			if isfile(inCache):
				self.ifilename = inCache
				self.foundImage = True
		elif (self.imageType == self.PREFER_IMAGE or self.imageType == self.IMAGE or self.imageType == self.IMAGE_THUMBNAIL or self.imageType == self.PREFER_POSTER):
			if not self.foundImage:
				self.ifilename = getImageFile(self.coverPath, eventName)
				if self.ifilename:
					self.foundImage = True
		#======= geaendert (#9) Alter Code unplausibel =======
		#if str(self.POSTER) in inCache or str(self.POSTER_THUMBNAIL) in inCache or str(self.PREFER_POSTER) in inCache or str(self.PREFER_IMAGE) in inCache:
		if inCache and not self.foundPoster and self.imageType != self.PREFER_POSTER and self.imageType != self.PREFER_IMAGE:
		# ==============================
			if isfile(inCache):
				self.pfilename = inCache
				self.foundPoster = True
		elif (self.imageType == self.PREFER_POSTER or self.imageType == self.POSTER or self.imageType == self.POSTER_THUMBNAIL or self.imageType == self.PREFER_IMAGE):
			if not self.foundPoster:
				self.pfilename = getImageFile(self.posterPath, eventName)
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
		#======= geaendert (#9) =======
		#if self.ifilename:
		if self.ifilename and self.ifilename != self.noImage:
		# ==============================
			self.nameCache[eventName + str(self.imageType)] = str(self.ifilename)
		#======= geaendert (#9) =======
		#if self.pfilename:
		if self.pfilename and self.pfilename != self.noImage:
		# ==============================
			self.nameCache[eventName + str(self.imageType)] = str(self.pfilename)
		if (self.imageType == self.IMAGE or self.imageType == self.IMAGE_THUMBNAIL) and self.foundImage:
			self.loadPic(self.ifilename)
		elif (self.imageType == self.POSTER or self.imageType == self.POSTER_THUMBNAIL) and self.foundPoster:
			self.loadPic(self.pfilename)
		#======= geaendert (#2/#4) =======
		#elif self.imageType == self.PREFER_IMAGE and self.foundImage:
		elif self.imageType == self.PREFER_IMAGE and self.foundImage and not (self.ifilename == self.noImage and self.foundPoster and self.pfilename != self.noImage):
		# =================================
			#======= hinzugefuegt (#4) =======
			if not self.preferType:
			# =================================
				if self.sizetype != 'Image':
					self.calcSize('Image')
				self.sizetype = 'Image'
				self.loadPic(self.ifilename)
			#======= hinzugefuegt (#4) =======
			else:
				self.prepareImg("II", self.ifilename)
			# =================================
		#======= geaendert (#2/#4) =======
		#elif self.imageType == self.PREFER_IMAGE and self.foundPoster:
		elif self.imageType == self.PREFER_IMAGE and self.foundPoster and isLastRun:
		# =================================
			#======= hinzugefuegt (#4) =======
			if not self.preferType:
			# =================================
				if self.sizetype != 'Poster':
					self.calcSize('Poster')
				self.sizetype = 'Poster'
				self.loadPic(self.pfilename)
			#======= hinzugefuegt (#4) =======
			else:
				self.prepareImg("IP", self.pfilename)
			# =================================
		#======= geaendert (#2/#4) =======
		#elif self.imageType == self.PREFER_POSTER and self.foundPoster:
		elif self.imageType == self.PREFER_POSTER and self.foundPoster and not (self.pfilename == self.noImage and self.foundImage and self.ifilename != self.noImage):
		# =================================
			#======= hinzugefuegt (#4) =======
			if not self.preferType:
			# =================================
				if self.sizetype != 'Poster':
					self.calcSize('Poster')
				self.sizetype = 'Poster'
				self.loadPic(self.pfilename)
			#======= hinzugefuegt (#4) =======
			else:
				self.prepareImg("PP", self.pfilename)
			# =================================
		#======= geaendert (#2/#4) =======
		#elif self.imageType == self.PREFER_POSTER and self.foundImage:
		elif self.imageType == self.PREFER_POSTER and self.foundImage and isLastRun:
		# =================================
			#======= hinzugefuegt (#4) =======
			if not self.preferType:
			# =================================
				if self.sizetype != 'Image':
					self.calcSize('Image')
				self.sizetype = 'Image'
				self.loadPic(self.ifilename)
			#======= hinzugefuegt (#4) =======
			else:
				self.prepareImg("PI", self.ifilename)
			# =================================
		else:
			# if run == 0 and (str(eventNames[1]) != str(eventNames[0])) and (str(eventNames[1]) != "None"):
			if not isLastRun:
				self.setthePixmap(eventNames, 1)
			else:
				self.hideimage()

	def checkIsLastRun(self, run, eventName0, eventName1):
		return False if run == 0 and (eventName0 != eventName1) and (eventName1 != "None") else True

	def calcSize(self, how):
		#======= hinzugefuegt (#4) =======
		self.hideimage()
		# ==============================
		if how == 'Poster' and self.instance:
			self.instance.move(ePoint(self.x, self.y))
			self.instance.resize(eSize(self.WCover, self.HCover))
			if self.image and self.imageframe:
				#======= geaendert (#5) =======
				#self.image.resize(eSize(self.WCover-20, self.HCover-20))
				self.image.resize(eSize(self.WCover - (2 * self.frameSize), self.HCover - (2 * self.frameSize)))
				# ==============================
				self.imageframe.resize(eSize(self.WCover, self.HCover))
			elif self.image:
				self.image.resize(eSize(self.WCover, self.HCover))
		elif self.instance and how == 'Image':
			if self.rotate == "left":
				self.instance.move(ePoint(self.x - self.HCover + self.WCover, self.y - self.WCover + self.HCover))
			self.instance.resize(eSize(self.HCover, self.WCover))
			if self.image and self.imageframe:
				#======= geaendert (#5) =======
				#self.image.resize(eSize(self.HCover-20, self.WCover-20))
				self.image.resize(eSize(self.HCover - (2 * self.frameSize), self.WCover - (2 * self.frameSize)))
				# ==============================
				self.imageframe.resize(eSize(self.HCover, self.WCover))
			elif self.image:
				self.image.resize(eSize(self.HCover, self.WCover))
		else:
			return
		if self.image and self.imageframe:
			self.imageframe.setScale(1)
			self.imageframe.setAlphatest(1)
			#======= geaendert (#5) =======
			#self.image.move(ePoint(10, 10))
			self.image.move(ePoint(self.frameSize, self.frameSize))
			# ==============================
		return

	#======= hinzugefuegt (#4) =======
	def prepareImg(self, peparetype, fileName):
		if self.preferType.startswith(peparetype) and fileName and exists(fileName):
			try:
				if self.image and self.instance and self.preferType == "PI_Top":
					self.hideimage(True)
					img = Image.open(fileName)
					imgW = int(img.size[0])
					imgH = int(img.size[1])
					w = self.WCover - (2 * self.frameSize)
					h = self.HCover - (2 * self.frameSize)
					scale = imgW / (w * 1.0)
					newH = int(imgH / scale)
					self.image.resize(eSize(w, newH))
					if self.frameImage and self.imageframe:
						self.imageframe.resize(eSize(self.WCover, newH + (2 * self.frameSize)))
					self.instance.resize(eSize(self.WCover, newH + (2 * self.frameSize)))
					self.loadPic(fileName)

				elif self.image and self.instance and self.preferType == "PI_Center":
					self.hideimage(True)
					img = Image.open(fileName)
					imgW = int(img.size[0])
					imgH = int(img.size[1])
					w = self.WCover - (2 * self.frameSize)
					h = self.HCover - (2 * self.frameSize)
					scale = imgW / (w * 1.0)
					newH = int(imgH / scale)
					self.image.resize(eSize(w, newH))
					if self.frameImage and self.imageframe:
						self.imageframe.resize(eSize(self.WCover, newH + (2 * self.frameSize)))
					self.instance.resize(eSize(self.WCover, newH + (2 * self.frameSize)))
					self.instance.move(ePoint(self.x, self.y + int((self.HCover - newH - (2 * self.frameSize)) / 2)))
					self.loadPic(fileName)

				elif self.image and self.instance and self.preferType == "PI_Bottom":
					self.hideimage(True)
					img = Image.open(fileName)
					imgW = int(img.size[0])
					imgH = int(img.size[1])
					w = self.WCover - (2 * self.frameSize)
					h = self.HCover - (2 * self.frameSize)
					scale = imgW / (w * 1.0)
					newH = int(imgH / scale)
					self.image.resize(eSize(w, newH))
					if self.frameImage and self.imageframe:
						self.imageframe.resize(eSize(self.WCover, newH + (2 * self.frameSize)))
					self.instance.resize(eSize(self.WCover, newH + (2 * self.frameSize)))
					self.instance.move(ePoint(self.x, self.y + self.HCover - newH - (2 * self.frameSize)))
					self.loadPic(fileName)

				elif self.preferType == "PI_Stacked":
					margin = 2
					w = self.WCover - (2 * self.frameSize)
					h = self.HCover - (2 * self.frameSize)
					newH = int((h / 2) - margin)
					img = Image.new(mode="RGBA", size=(w, h))
					img1 = Image.open(fileName)
					img1 = img1.resize((w, newH))
					img2 = img1.copy()
					img.paste(img1, (0, 0))
					img.paste(img2, (0, h - newH))
					img.save(self.preferImgPath)
					self.loadPic(self.preferImgPath)

				elif self.preferType == "PI_90L":
					img = Image.open(fileName)
					img = img.rotate(90)
					img.save(self.preferImgPath)
					self.loadPic(self.preferImgPath)

				elif self.preferType == "PI_90R":
					img = Image.open(fileName)
					img = img.rotate(270)
					img.save(self.preferImgPath)
					self.loadPic(self.preferImgPath)

				elif self.image and self.instance and self.preferType == "PI_FreeCover_LB":
					self.hideimage(True)
					img = Image.open(fileName)
					imgW = int(img.size[0])
					imgH = int(img.size[1])
					#WCover=neue Hoehe
					newH = self.WCover - (2 * self.frameSize)
					scale = imgH / (newH * 1.0)
					newW = int(imgW / scale)
					if (newW + (2 * self.frameSize)) > self.HCover:
						#HCover=neue Breite
						newW = self.HCover - (2 * self.frameSize)
						scale = imgW / (newW * 1.0)
						newH = int(imgH / scale)
					self.image.resize(eSize(newW, newH))
					if self.frameImage and self.imageframe:
						self.imageframe.resize(eSize(newW + (2 * self.frameSize), newH + (2 * self.frameSize)))
					self.instance.resize(eSize(newW + (2 * self.frameSize), newH + (2 * self.frameSize)))
					self.instance.move(ePoint(self.x, self.y + self.HCover - newH - (2 * self.frameSize)))
					self.loadPic(fileName)

				elif self.image and self.instance and self.preferType == "PI_FreeCover_RB":
					self.hideimage(True)
					img = Image.open(fileName)
					imgW = int(img.size[0])
					imgH = int(img.size[1])
					#WCover=neue Hoehe
					newH = self.WCover - (2 * self.frameSize)
					scale = imgH / (newH * 1.0)
					newW = int(imgW / scale)
					if (newW + (2 * self.frameSize)) > self.HCover:
						#HCover=neue Breite
						newW = self.HCover - (2 * self.frameSize)
						scale = imgW / (newW * 1.0)
						newH = int(imgH / scale)
					self.image.resize(eSize(newW, newH))
					if self.frameImage and self.imageframe:
						self.imageframe.resize(eSize(newW + (2 * self.frameSize), newH + (2 * self.frameSize)))
					self.instance.resize(eSize(newW + (2 * self.frameSize), newH + (2 * self.frameSize)))
					self.instance.move(ePoint(self.x - (newW + (2 * self.frameSize) - self.WCover), self.y + self.HCover - newH - (2 * self.frameSize)))
					self.loadPic(fileName)

				elif self.image and self.instance and self.preferType == "IP_Left":
					self.hideimage(True)
					img = Image.open(fileName)
					imgW = int(img.size[0])
					imgH = int(img.size[1])
					w = self.WCover - (2 * self.frameSize)
					h = self.HCover - (2 * self.frameSize)
					scale = imgH / (h * 1.0)
					newW = int(imgW / scale)
					self.image.resize(eSize(newW, h))
					if self.frameImage and self.imageframe:
						self.imageframe.resize(eSize(newW + (2 * self.frameSize), self.HCover))
					self.instance.resize(eSize(newW + (2 * self.frameSize), self.HCover))
					self.loadPic(fileName)

				elif self.image and self.instance and self.preferType == "IP_Center":
					self.hideimage(True)
					img = Image.open(fileName)
					imgW = int(img.size[0])
					imgH = int(img.size[1])
					w = self.WCover - (2 * self.frameSize)
					h = self.HCover - (2 * self.frameSize)
					scale = imgH / (h * 1.0)
					newW = int(imgW / scale)
					self.image.resize(eSize(newW, h))
					if self.frameImage and self.imageframe:
						self.imageframe.resize(eSize(newW + (2 * self.frameSize), self.HCover))
					self.instance.resize(eSize(newW + (2 * self.frameSize), self.HCover))
					self.instance.move(ePoint(self.x + int((self.WCover - newW - (2 * self.frameSize)) / 2), self.y))
					self.loadPic(fileName)

				elif self.image and self.instance and self.preferType == "IP_Right":
					self.hideimage(True)
					img = Image.open(fileName)
					imgW = int(img.size[0])
					imgH = int(img.size[1])
					w = self.WCover - (2 * self.frameSize)
					h = self.HCover - (2 * self.frameSize)
					scale = imgH / (h * 1.0)
					newW = int(imgW / scale)
					self.image.resize(eSize(newW, h))
					if self.frameImage and self.imageframe:
						self.imageframe.resize(eSize(newW + (2 * self.frameSize), self.HCover))
					self.instance.resize(eSize(newW + (2 * self.frameSize), self.HCover))
					self.instance.move(ePoint(self.x + self.WCover - newW - (2 * self.frameSize), self.y))
					self.loadPic(fileName)

				elif self.image and self.instance and self.preferType == "IP_Stacked":
					margin = 2
					w = self.WCover - (2 * self.frameSize)
					h = self.HCover - (2 * self.frameSize)
					newW = int((w / 2) - margin)
					img = Image.new(mode="RGBA", size=(w, h))
					img1 = Image.open(fileName)
					img1 = img1.resize((newW, h))
					img2 = img1.copy()
					img.paste(img1, (0, 0))
					img.paste(img2, (w - newW, 0))
					img.save(self.preferImgPath)
					self.loadPic(self.preferImgPath)
			except Exception as e:
				write_log(f"========= AdvancedEventLibraryImage - Error - prepareImg: {e}", DEFAULT_MODULE_NAME)
		#II,PP
		elif self.frameImage and self.instance and self.image and self.imageframe:
			if self.instance.size().width() != self.WCover or self.instance.size().height() != self.HCover:
				self.hideimage(True)
				self.image.resize(eSize(self.WCover - (2 * self.frameSize), self.HCover - (2 * self.frameSize)))
				self.image.move(ePoint(self.frameSize, self.frameSize))
				self.imageframe.resize(eSize(self.WCover, self.HCover))
				self.imageframe.move(ePoint(0, 0))
				self.instance.resize(eSize(self.WCover, self.HCover))
				self.instance.move(ePoint(self.x, self.y))
			if fileName and exists(fileName):
					self.loadPic(fileName)
		else:
			if self.instance and self.image and (self.instance.size().width() != self.WCover or self.instance.size().height() != self.HCover):
				self.hideimage(True)
				self.image.resize(eSize(self.WCover, self.HCover))
				self.image.move(ePoint(0, 0))
				self.instance.resize(eSize(self.WCover, self.HCover))
				self.instance.move(ePoint(self.x, self.y))
			if fileName and exists(fileName):
				self.loadPic(fileName)
		# ==============================================

	def removeExtension(self, ext):
		ext = ext.replace('.wmv', '').replace('.mpeg2', '').replace('.ts', '').replace('.m2ts', '').replace('.mkv', '').replace('.avi', '').replace('.mpeg', '').replace('.mpg', '').replace('.iso', '').replace('.mp4', '')
		return ext

	def loadPic(self, picname):
		if self.image and picname != "":
			size = self.image.size()
			self.picload = ePicLoad()
			#======= geaendert (#7) =======
			#self.picload.PictureData.get().append(self.showCallback)
			self.picload.PictureData.get().append(boundFunction(self.showCallback, requestNr=self.requestNr))
			# =============================
			if self.picload:
					self.picload.setPara((size.width(), size.height(), 0, 0, False, 1, "#00000000"))
					if self.picload.startDecode(picname) != 0:
						del self.picload
		else:
			self.hideimage()

	def showCallback(self, picInfo=None, requestNr=0):
		try:
			if self.picload:
				#======== geaendert (#1) =======
				#ptr = self.picload.getData()
				#if ptr != None:
				#	self.image.setPixmap(ptr)
				#	if self.ishide:
				#		self.showimage()
				#del self.picload

				picload = self.picload
				ptr = picload.getData()
				#======= geaendert (#7) =======
				#if ptr != None:
				if ptr is not None and requestNr >= self.requestNr and self.image:
				# =**=*========*=========*=====
					self.image.setPixmap(ptr)
					if self.ishide:
						self.showimage()
				del picload
				# ==============================

				#======= hinzugefuegt (#4) =======
				if self.preferType and exists(self.preferImgPath):
					remove(self.preferImgPath)
				# ==============================
		except Exception:
			self.hideimage()
