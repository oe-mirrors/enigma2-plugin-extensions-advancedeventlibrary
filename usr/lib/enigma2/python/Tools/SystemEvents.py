from os import makedirs, chmod
from os.path import exists, join
from enigma import eConsoleAppContainer
from Tools.AdvancedEventLibrary import aelGlobals
from Plugins.Extensions.AdvancedEventLibrary import _  # for localized messages


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
		self.eventIds = {self.STANDBY_ENTER: _("Standby"),
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
		self.eventList = {}
		self.ignoreScriptExec = []
		self.cmdPath = join(aelGlobals.CONFIGPATH, "events/")
		self.cmdFiletype = ".sh"
		dummyText = "#!/bin/sh\n\n"
		dummyText += "# this script will be executed when script is modified and given event hook will be called\n"
		dummyText += "# PLEASE NOTE !!!!\n"
		dummyText += "# Event hook calls can have some command-line arguments, which can be accessed via $1, $2 ...\n\n"
		dummyText += "exit 0\n"
		for evt in self.eventIds:
			self.eventList[evt] = []
		if not exists(self.cmdPath):
			try:
				makedirs(self.cmdPath)
			except OSError:
				pass
		for key in self.eventList:
			script_file = f"{self.cmdPath}{key}{self.cmdFiletype}"
			if not exists(script_file):
				try:
					with open(script_file, "w") as f:
						f.write(dummyText)
					chmod(script_file, 0o0775)
				except Exception:
					pass
				self.ignoreScriptExec.append(key)
			else:
				t = ""
				try:
					with open(script_file, "r") as f:
						t = f.read()
				except Exception:
					pass
				if t or t == dummyText:
					self.ignoreScriptExec.append(key)

	def getfriendlyName(self, evt):
		return self.eventIds[evt] if evt in self.eventIds else ""

	def getSystemEvents(self):
		eventList = []
		for key in self.eventList:
			eventList.append(key)
		return eventList

	def callEventHook(self, what, *eventargs):
		if what in self.eventList and eventargs:
			print(f"[SystemEvent] {what} {', '.join(eventargs)}")
			for hook in self.eventList[what]:
				args = []
				for arg in range(2, len(hook)):
					args.append(hook[arg])
				for eventarg in eventargs:
					args.append(eventarg)
				hook[0](*args)
			if what not in self.ignoreScriptExec:
				cmd = self.cmdPath + what + self.cmdFiletype
				for eventarg in eventargs:
					cmd += f' "{eventarg}"'
				appContainer = eConsoleAppContainer()
				appContainer.execute(cmd)

	def addEventHook(self, what, fnc, name, *args):
		if what in self.eventList:
			hook = [fnc, name]
			for arg in args:
				hook.append(arg)
			if hook not in self.eventList[what]:
				self.eventList[what].append(hook)

	def removeEventHook(self, what, fnc, name):
		if what in self.eventList:
			fncs = self.eventList[what]
			fncs_new = self.eventList[what]
			fnc_to_del = []
			for f in fncs:
				if f[0] == fnc and f[1] == name:
					fnc_to_del.append(f)
			for f in fnc_to_del:
				if f in fncs_new:
					fncs_new.remove(f)
			self.eventList[what] = fncs_new


systemevents = SystemEvents()
