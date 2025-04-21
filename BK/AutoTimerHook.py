from Plugins.Extensions.AdvancedEventLibrary import _  # for localized messages

addAutotimerFromEvent = None
AutoTimerOverView = None
AUTOTIMER_OK = False
CHECKAUTOTIMER = None


def initAutoTimerGlobals():
	global CHECKAUTOTIMER
	global AUTOTIMER_OK
	global addAutotimerFromEvent
	global AutoTimerOverView
	try:
		from Plugins.Extensions.AutoTimer.AutoTimerEditor import addAutotimerFromEvent
		from Plugins.Extensions.AutoTimer.plugin import main as AutoTimerOverView
		AUTOTIMER_OK = True
	except ImportError:
		AUTOTIMER_OK = False
	CHECKAUTOTIMER = True


def getChoiceList():
	return [(_("Add timer"), "default"), (_("AutoTimer"), "autotimer"), (_("View AutoTimers"), "show_autotimer"), (_("show timer list"), "show_timerlist")]
