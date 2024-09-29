from os import makedirs, chmod
from os.path import exists
from enigma import eConsoleAppContainer


class SystemEvents:
	STANDBY_ENTER = "STANDBY_ENTER"
	STANDBY_LEAVE = "STANDBY_LEAVE"
	RECORD_START = "RECORD_START"
	RECORD_STOP = "RECORD_STOP"
	GUI_REBOOT = "GUI_REBOOT"
	REBOOT = "REBOOT"
	STBBOOT = "STBBOOT"
	SHUTDOWN = "SHUTDOWN"
	E2START = "E2START"
	RECORD_WAKEUP = "RECORD_WAKEUP"
	RECORD_REMIND = "RECORD_REMIND"
	SERVICE_START = "SERVICE_START"
	SERVICE_STOP = "SERVICE_STOP"
	PVRDESCRAMBLE_START = "PVRDESCRAMBLE_START"
	PVRDESCRAMBLE_STOP = "PVRDESCRAMBLE_STOP"
	TASK_START = "TASK_START"
	TASK_CANCEL = "TASK_CANCEL"
	TASK_FINISH = "TASK_FINISH"
	DBTASK_START = "DBTASK_START"
	DBTASK_CANCEL = "DBTASK_CANCEL"
	DBTASK_FINISH = "DBTASK_FINISH"

	def __init__(self):
		self.event_ids = {self.STANDBY_ENTER: _("Standby"),
						self.STANDBY_LEAVE: _("Leave Standby"),
						self.RECORD_START: _("Start record timer"),
						self.RECORD_STOP: _("Record timer finished"),
						self.GUI_REBOOT: _("GUI reboot"),
						self.PVRDESCRAMBLE_START: _("Start descrambling movie"),
						self.PVRDESCRAMBLE_STOP: _("Descrambling of movie finished"),
						self.STBBOOT: _("Start Set-Top-Box"),
						self.REBOOT: _("Reboot"),
						self.SHUTDOWN: _("Shutdown"),
						self.E2START: _("Start enigma2"),
						self.RECORD_WAKEUP: _("Start Set-Top-Box for upcoming timer"),
						self.RECORD_REMIND: _("Reminder for service event"),
						self.SERVICE_START: _("Start playing service"),
						self.SERVICE_STOP: _("Stop playing service"),
						self.TASK_START: _("Task started"),
						self.TASK_FINISH: _("Task stopped"),
						self.TASK_CANCEL: _("Task cancelled"),
						self.DBTASK_START: _("Database Task started"),
						self.DBTASK_FINISH: _("Database Task stopped"),
						self.DBTASK_CANCEL: _("Database Task cancelled"),
					}
		self.event_list = {}
		self.ignore_script_exec = []
		self.cmd_path = '/etc/enigma2/events/'
		self.cmd_filetype = '.sh'
		dummy_txt = "#!/bin/sh\n\n"
		dummy_txt += "# this script will be executed when script is modified and given event hook will be called\n"
		dummy_txt += "# PLEASE NOTE !!!!\n"
		dummy_txt += "# Event hook calls can have some command-line arguments, which can be accessed via $1, $2 ...\n\n"
		dummy_txt += "exit 0\n"
		for evt in self.event_ids:
			self.event_list[evt] = []
		if not exists(self.cmd_path):
			try:
				makedirs(self.cmd_path)
			except OSError:
				pass
		for key in self.event_list:
			script_file = self.cmd_path + key + self.cmd_filetype
			if not exists(script_file):
				try:
					with open(script_file, "w") as f:
						f.write(dummy_txt)
					chmod(script_file, 0o0775)
				except Exception:
					pass
				self.ignore_script_exec.append(key)
			else:
				t = ""
				try:
					with open(script_file, "r") as f:
						t = f.read()
				except Exception:
					pass
				if t == dummy_txt or t == "":
					self.ignore_script_exec.append(key)

	def getfriendlyName(self, evt):
		if evt in self.event_ids:
			return self.event_ids[evt]
		else:
			return ""

	def getSystemEvents(self):
		event_list = []
		for key in self.event_list:
			event_list.append(key)
		return event_list

	def callEventHook(self, what, *eventargs):
		if what in self.event_list:
			e_a = ""
			for a in eventargs:
				e_a += a + ", "
			if e_a.endswith(', '):
				e_a = e_a[:-2]
			print("[SystemEvent] " + what + " " + e_a)
			for hook in self.event_list[what]:
				args = []
				for arg in range(2, len(hook)):
					args.append(hook[arg])
				for eventarg in eventargs:
					args.append(eventarg)
				hook[0](*args)
			if not what in self.ignore_script_exec:
				cmd = self.cmd_path + what + self.cmd_filetype
				for eventarg in eventargs:
					cmd += ' "' + eventarg + '"'
				appContainer = eConsoleAppContainer()
				appContainer.execute(cmd)

	def addEventHook(self, what, fnc, name, *args):
		if what in self.event_list:
			hook = [fnc, name]
			for arg in args:
				hook.append(arg)
			if hook not in self.event_list[what]:
				self.event_list[what].append(hook)

	def removeEventHook(self, what, fnc, name):
		if what in self.event_list:
			fncs = self.event_list[what]
			fncs_new = self.event_list[what]
			fnc_to_del = []
			i = 0
			for f in fncs:
				if f[0] == fnc and f[1] == name:
					fnc_to_del.append(f)
			for f in fnc_to_del:
				if f in fncs_new:
					fncs_new.remove(f)
			self.event_list[what] = fncs_new


systemevents = SystemEvents()
