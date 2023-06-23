#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Coded by tsiegel (c) 2020
from Renderer import Renderer
from enigma import ePixmap, eTimer, loadJPG
from Tools.AdvancedEventLibrary import getPictureDir
import os
import glob
import random


class AdvancedEventLibraryRandomPicture(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.delay = 2000
		self.Path = getPictureDir()

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes:
			if attrib == "path":
				self.Path += value
				str(self.Path).replace('//', '/')
			elif attrib == "delay":
				self.delay = int(value)
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		if os.path.isdir(self.Path):
			self.animate(self.Path)
		return Renderer.applySkin(self, desktop, parent)

	GUI_WIDGET = ePixmap

	def changed(self, what):
		pass

	def animate(self, path):
		self.piclist = glob.glob(path + "*.jpg")
		self.picchanger = eTimer()
		self.picchanger.callback.append(self.changepic)
		self.picchanger.start(100, True)

	def changepic(self):
		self.picchanger.stop()
		self.instance.setScale(1)
		try:
			number = random.randint(1, len(self.piclist) - 1)
			self.instance.setPixmap(loadJPG(self.piclist[number]))
		except:
			pass
		self.picchanger.start(self.delay, True)
