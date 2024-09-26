import fcntl
import socket
import struct


def getUniqueID(device='eth0'):
	try:
		with open('/proc/stb/info/vumodel', 'r') as f:
			model = f.read()
	except OSError:
		model = "vustb"
	model = model.strip()
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack('256s', bytes(device[:15], 'utf-8')))
	key = "".join(['%02x' % char for char in info[18:24]])
	id = ''
	j = len(key) - 1
	for i in range(0, len(key)):
		if i < len(model):
			id += key[j] + model[i] + key[i]
		else:
			id += key[j] + key[i]
		j -= 1
	return id[:12]
