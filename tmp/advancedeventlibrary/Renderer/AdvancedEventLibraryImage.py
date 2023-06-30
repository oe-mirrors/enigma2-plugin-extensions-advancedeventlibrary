#!/usr/bin/env python
# -*- coding: utf-8 -*-
#################################################################################
#																				#
#								AdvancedEventLibrary							#
#																				#
#							Copyright: tsiegel 2019								#
#																				#
#################################################################################

import os
import skin
import linecache
import requests
import json
import shutil
import re
import datetime
from time import localtime, mktime, sleep
from enigma import eLabel, ePixmap, ePicLoad, ePoint, eSize, eTimer, eWidget, loadPNG
from Components.Renderer.Renderer import Renderer
from skin import parseColor, parseColor
from Components.Sources.Event import Event
from Components.Sources.CurrentService import CurrentService
from Components.Sources.ServiceEvent import ServiceEvent
from Components.config import config, ConfigText, ConfigSubsection, ConfigYesNo
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceCenter, eServiceReference
from ServiceReference import ServiceReference
from Tools import AdvancedEventLibrary
import threading
from datetime import datetime

config.plugins.AdvancedEventLibrary = ConfigSubsection()
usePreviewImages = config.plugins.AdvancedEventLibrary.UsePreviewImages = ConfigYesNo(default=False)
previewImages = usePreviewImages.value or usePreviewImages.value == 'true'

log = "/var/tmp/AdvancedEventLibrary.log"

screensWithEvent = ["ChannelSelection", "ChannelSelectionHorizontal", "InfoBarZapHistory", "NumberZapWithName", "ChannelSelection_summary", "AdvancedEventLibraryMediaHub", "AdvancedEventLibraryChannelSelection"]


def write_log(svalue):
	t = localtime()
	logtime = '%02d:%02d:%02d' % (t.tm_hour, t.tm_min, t.tm_sec)
	AEL_log = open(log, "a")
	AEL_log.write(str(logtime) + " : [AdvancedEventLibraryImage] - " + str(svalue) + "\n")
	AEL_log.close()


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
		if os.path.isfile('/usr/share/enigma2/Chamaeleon/png/pigframe.png'):
			self.frameImage = '/usr/share/enigma2/Chamaeleon/png/pigframe.png'
		self.coverPath = AdvancedEventLibrary.getPictureDir() + 'cover/'
		self.posterPath = AdvancedEventLibrary.getPictureDir() + 'poster/'
		self.db = AdvancedEventLibrary.getDB()
		self.ptr = None
		self.ptr2 = None
		return

	GUI_WIDGET = eWidget

	def applySkin(self, desktop, screen):
		if (isinstance(screen.skinName, str)):
			self.screenName = screen.skinName
		else:
			self.screenName = ', '.join(screen.skinName)
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
						if os.path.isfile(self.frameImage):
							self.imageframe.setPixmap(loadPNG(self.frameImage))
						else:
							self.frameImage = None
					if len(params) > 2:
						self.noImage = params[2]
					if len(params) > 3:
						self.rotate = params[3]
				else:
					attribs.append((attrib, value))

			self.skinAttributes = attribs

		if self.frameImage:
			self.image.resize(eSize(self.WCover - 20, self.HCover - 20))
			self.imageframe.resize(eSize(self.WCover, self.HCover))
			self.imageframe.setScale(1)
			self.imageframe.setAlphatest(1)
			self.image.move(ePoint(10, 10))
		else:
			self.image.resize(eSize(self.WCover, self.HCover))

		self.image.setScale(self.scalertype)
		ret = Renderer.applySkin(self, desktop, screen)
		return ret

	def changed(self, what):
		try:
			if what[0] != self.CHANGED_CLEAR:
				event = None
				self.ptr = None
				self.ptr2 = None
				if not self.instance:
					return
				try:
					if isinstance(self.source, ServiceEvent):
						service = self.source.getCurrentService()
						sRef = service.toString()
						if '/' in sRef:
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
						if event:
							if (isinstance(event, tuple) and event):
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
						if self.evt:
							if self.evt[0][3] != '':
								self.ptr = str(self.evt[0][3])
#							elif self.evt[0][7] != '':
#								name = self.evt[0][7] + ' - '
#								if self.evt[0][12] != '':
#									name += 'S' + str(self.evt[0][12]).zfill(2)
#								if self.evt[0][13] != "":
#									name += 'E' + str(self.evt[0][12]).zfill(2) + ' - '
#								if self.evt[0][2] != "":
#									name += self.evt[0][2] + ' - '
#								self.ptr = str(name[:-3])
				except Exception as ex:
					write_log('find event ' + str(ex))

				if self.ptr:
					self.ptr = AdvancedEventLibrary.convertDateInFileName(AdvancedEventLibrary.convertSearchName(self.ptr))
				if self.ptr2:
					self.ptr2 = AdvancedEventLibrary.convertDateInFileName(AdvancedEventLibrary.convertSearchName(self.ptr2))
				eventName = (self.ptr, self.ptr2)
#				write_log('eventName : ' + str(eventName))

				if self.lastName != eventName:
					thread = threading.Thread(target=self.setthePixmap, args=(eventName,))
					thread.start()
#					self.setthePixmap(eventName)
		except Exception as e:
			self.hideimage()
			write_log("changed : " + str(e))
		return

	def GUIcreate(self, parent):
		self.instance = eWidget(parent)
		self.imageframe = ePixmap(self.instance)
		self.image = ePixmap(self.instance)
		if self.imageframe:
			self.imageframe.setPixmap(loadPNG(self.frameImage))

	def GUIdelete(self):
		self.imageframe = None
		self.image = None
		self.instance = None
		AdvancedEventLibrary.clearMem(self.screenName)
		return

	def showimage(self):
		self.instance.show()
		if self.imageframe:
			self.imageframe.show()
		self.image.show()
		self.ishide = False

	def hideimage(self):
		self.image.hide()
		if self.imageframe:
			self.imageframe.hide()
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

		if run == 0:
			eventName = str(eventNames[0])
		else:
			eventName = str(eventNames[1])
		inCache = self.nameCache.get(eventName + str(self.imageType), "")
		if str(self.IMAGE) in inCache or str(self.IMAGE_THUMBNAIL) in inCache or str(self.PREFER_IMAGE) in inCache or str(self.PREFER_POSTER) in inCache:
			if os.path.isfile(inCache):
				self.ifilename = inCache
				self.foundImage = True
		elif (self.imageType == self.PREFER_IMAGE or self.imageType == self.IMAGE or self.imageType == self.IMAGE_THUMBNAIL or self.imageType == self.PREFER_POSTER):
			if not self.foundImage:
				self.ifilename = AdvancedEventLibrary.getImageFile(self.coverPath, eventName)
				if self.ifilename:
					self.foundImage = True

		if str(self.POSTER) in inCache or str(self.POSTER_THUMBNAIL) in inCache or str(self.PREFER_POSTER) in inCache or str(self.PREFER_IMAGE) in inCache:
			if os.path.isfile(inCache):
				self.pfilename = inCache
				self.foundPoster = True
		elif (self.imageType == self.PREFER_POSTER or self.imageType == self.POSTER or self.imageType == self.POSTER_THUMBNAIL or self.imageType == self.PREFER_IMAGE):
			self.pfilename = AdvancedEventLibrary.getImageFile(self.posterPath, eventName)
			if self.pfilename:
				self.foundPoster = True

		# set alternative falls angegeben und nix gefunden
		if self.noImage and not self.foundImage and (self.imageType == self.PREFER_IMAGE or self.imageType == self.IMAGE or self.imageType == self.IMAGE_THUMBNAIL):
			if (os.path.exists(self.noImage)):
				self.foundImage = True
				self.ifilename = self.noImage
		if self.noImage and not self.foundPoster and (self.imageType == self.PREFER_POSTER or self.imageType == self.POSTER or self.imageType == self.POSTER_THUMBNAIL):
			if (os.path.exists(self.noImage)):
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
			if run == 0 and (str(eventNames[1]) != str(eventNames[0])) and (str(eventNames[1]) != "None"):
				self.setthePixmap(eventNames, 1)
			else:
				self.hideimage()

	def calcSize(self, how):
		if how == 'Poster':
			self.instance.move(ePoint(self.x, self.y))
			self.instance.resize(eSize(self.WCover, self.HCover))
			if self.imageframe:
				self.image.resize(eSize(self.WCover - 20, self.HCover - 20))
				self.imageframe.resize(eSize(self.WCover, self.HCover))
			else:
				self.image.resize(eSize(self.WCover, self.HCover))
		elif how == 'Image':
			if self.rotate == "left":
				self.instance.move(ePoint(self.x - self.HCover + self.WCover, self.y - self.WCover + self.HCover))
			self.instance.resize(eSize(self.HCover, self.WCover))
			if self.imageframe:
				self.image.resize(eSize(self.HCover - 20, self.WCover - 20))
				self.imageframe.resize(eSize(self.HCover, self.WCover))
			else:
				self.image.resize(eSize(self.HCover, self.WCover))
		else:
			return
		if self.imageframe:
			self.imageframe.setScale(1)
			self.imageframe.setAlphatest(1)
			self.image.move(ePoint(10, 10))
		return

	def removeExtension(self, ext):
		ext = ext.replace('.wmv', '').replace('.mpeg2', '').replace('.ts', '').replace('.m2ts', '').replace('.mkv', '').replace('.avi', '').replace('.mpeg', '').replace('.mpg', '').replace('.iso', '').replace('.mp4', '')
		return ext

	def loadPic(self, picname):
		try:
			if picname != "":
				size = self.image.size()
				self.picload = ePicLoad()
				self.picload.PictureData.get().append(self.showCallback)
				if self.picload:
						self.picload.setPara((size.width(), size.height(), 0, 0, False, 1, "#00000000"))
						if self.picload.startDecode(picname) != 0:
							del self.picload
			else:
				self.hideimage()
		except:
			self.hideimage()

	def showCallback(self, picInfo=None):
		try:
			if self.picload:
				ptr = self.picload.getData()
				if ptr != None:
					self.image.setPixmap(ptr)
					if self.ishide:
						self.showimage()
				del self.picload
		except:
			self.hideimage()
