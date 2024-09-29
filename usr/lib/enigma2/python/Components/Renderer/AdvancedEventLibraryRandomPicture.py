from os.path import isdir
from glob import glob
from random import randint
from enigma import ePixmap, eTimer, loadJPG
from Components.Renderer.Renderer import Renderer
from Tools.AdvancedEventLibrary import getPictureDir


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
				self.Path = str(self.Path).replace('//', '/')
			elif attrib == "delay":
				self.delay = int(value)
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		if isdir(self.Path):
			self.animate(self.Path)
		return Renderer.applySkin(self, desktop, parent)

	GUI_WIDGET = ePixmap

	def changed(self, what):
		pass

	def animate(self, path):
		self.piclist = glob(path + "*.jpg")
		self.picchanger = eTimer()
		self.picchanger.callback.append(self.changepic)
		self.picchanger.start(100, True)

	def changepic(self):
		self.picchanger.stop()
		self.instance.setScale(1)
		number = randint(1, len(self.piclist) - 1)
		self.instance.setPixmap(loadJPG(self.piclist[number]))
		self.picchanger.start(self.delay, True)
