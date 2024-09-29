# PYTHON IMPORTS
from gettext import bindtextdomain, dgettext, gettext
from os.path import join

# ENIGMA IMPORTS
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

PLUGINPATH = resolveFilename(SCOPE_PLUGINS, "Extensions/AdvancedEventLibrary/")


def localeInit():
	bindtextdomain("AdvancedEventLibrary", join(PLUGINPATH, "locale"))


def _(txt):
	t = dgettext("AdvancedEventLibrary", txt)
	t = gettext(txt) if t == txt else t


localeInit()
language.addCallback(localeInit)
