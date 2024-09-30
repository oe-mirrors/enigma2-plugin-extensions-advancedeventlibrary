from os.path import realpath, basename, exists
from enigma import eServiceCenter


def getExtendedMovieDescription(ref):
	serviceHandler = eServiceCenter.getInstance()
	info = serviceHandler.info(ref)
	if info:
		evt = info.getEvent(ref)
		if evt:
			name = evt.getEventName()
			extended_desc = evt.getExtendedDescription()
			return (name, extended_desc)
	name = ""
	filename = ""
	extended_desc = ""
	extensions = ('.txt', '.info')
	info_file = realpath(ref.getPath())
	name = basename(info_file)
	ext_pos = name.rfind('.')
	name = name[:ext_pos].replace('_', ' ') if ext_pos > 0 else name.replace('_', ' ')
	for ext in extensions:
		if exists(info_file + ext):
			filename = info_file + ext
			break
	if not filename:
		ext_pos = info_file.rfind('.')
		name_len = len(info_file)
		ext_len = name_len - ext_pos
		if ext_len <= 5:
			info_file = info_file[:ext_pos]
			for ext in extensions:
				if exists(info_file + ext):
					filename = f"{info_file}{ext}"
					break
	if filename:
		try:
			with open(filename, 'r') as txtfile:
				extended_desc = txtfile.read()
		except IOError:
			pass
	return (name, extended_desc)
