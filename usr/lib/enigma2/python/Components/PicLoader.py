from enigma import ePicLoad


class PicLoader:
	def __init__(self, width, height):
		self.picload = ePicLoad()
		self.picload.setPara((width, height, 0, 0, False, 1, "#ff000000"))

	def load(self, imgfile):
		self.picload.startDecode(imgfile, 0, 0, False)
		data = self.picload.getData()
		return data

	def destroy(self):
		del self.picload
