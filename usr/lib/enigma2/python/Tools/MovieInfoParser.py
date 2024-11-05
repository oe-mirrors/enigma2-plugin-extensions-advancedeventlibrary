from os.path import realpath, basename, exists
from enigma import eServiceCenter


def getExtendedMovieDescription(ref):
	serviceHandler = eServiceCenter.getInstance()
	info = serviceHandler.info(ref)
	if info:
		evt = info.getEvent(ref)
		if evt:
			name = evt.getEventName()
			extendedDesc = evt.getExtendedDescription()
			return (name, extendedDesc)
	name, filename, extendedDesc = "", "", ""
	extensions = (".txt", ".info")
	infoFile = realpath(ref.getPath())
	name = basename(infoFile)
	extPos = name.rfind(".")
	name = name[:extPos].replace("_", " ") if extPos > 0 else name.replace("_", " ")
	for ext in extensions:
		if exists(infoFile + ext):
			filename = f"{infoFile}{ext}"
			break
	if not filename:
		extPos = infoFile.rfind(".")
		nameLen = len(infoFile)
		extLen = nameLen - extPos
		if extLen <= 5:
			infoFile = infoFile[:extPos]
			for ext in extensions:
				if exists(infoFile + ext):
					filename = f"{infoFile}{ext}"
					break
	if filename:
		try:
			with open(filename, "r") as txtfile:
				extendedDesc = txtfile.read()
		except IOError:
			pass
	return (name, extendedDesc)
