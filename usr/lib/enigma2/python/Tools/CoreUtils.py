from fcntl import ioctl
from socket import socket, AF_INET, SOCK_DGRAM
from struct import pack


def getUniqueID(device='eth0'):
	try:
		with open('/proc/stb/info/vumodel', 'r') as f:
			model = f.read()
	except OSError:
		model = "vustb"
	model = model.strip()
	s = socket(AF_INET, SOCK_DGRAM)
	info = ioctl(s.fileno(), 0x8927, pack('256s', bytes(device[:15], 'utf-8')))
	key = "".join([f'{char:02x}' for char in info[18:24]])
	keyid = ''
	j = len(key) - 1
	for i in range(0, len(key)):
		keyid += key[j] + model[i] + key[i] if i < len(model) else key[j] + key[i]
		j -= 1
	return keyid[:12]
