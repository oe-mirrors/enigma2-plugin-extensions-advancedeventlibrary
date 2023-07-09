# -*- coding: utf-8 -*-

class FunctionTimer:
	def __init__(self):
		self.fnclist = {}

	def add(self, fnc):
		if isinstance(fnc, (tuple, list)) and len(fnc) == 2:
			if isinstance(fnc[0], str) and isinstance(fnc[1], dict):
				if fnc[0] not in self.fnclist:
					self.fnclist[fnc[0]] = fnc[1]

	def remove(self, fncid):
		if isinstance(fncid, str):
			if fncid in self.fnclist:
				self.fnclist.pop(fncid)

	def get(self):
		return self.fnclist

functionTimer = FunctionTimer()
