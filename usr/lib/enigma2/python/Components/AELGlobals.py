from os.path import exists, join, makedirs
from enigma import eEnv, getDesktop
from Components.config import config
from Tools.Directory import resolveFilename, SCOPE_CURRENT_SKIN, SCOPE_SKIN_IMAGE, SCOPE_CONFIG, SCOPE_CURRENT_PLUGIN


class AELGlobals():
	CURRENTVERSION = 141
	AGENTS = [
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
			"Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
			"Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)",
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edge/87.0.664.75",
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363"
			]
	MODULE_NAME = __name__.split(".")[-1]
	SIZE_UNITS = ["B ", "KB", "MB", "GB", "TB", "PB", "EB"]
	API_ERRDICT = {"TMDB": 0, "TVDB": 0, "TVMAZE": 0, "OMDB": 0, "TVS": 0, "TVMOVIE": 0}
	FSKDICT = {"R": "18", "TV-MA": "18", "TV-PG": "16", "TV-14": "12", "TV-Y7": "6", "PG-13": "12", "PG": "6", "G": "16"}
	SPDICT = {}
	if config.plugins.AdvancedEventLibrary.searchPlaces.value:
		SPDICT = eval(config.plugins.AdvancedEventLibrary.searchPlaces.value)
	SCAN_STOPPED = True
	COVERQUALITYDICT = {"w300": "300x169", "w780": "780x439", "w1280": "1280x720", "w1920": "1920x1080"}
	POSTERQUALITYDICT = {"w185": "185x280", "w342": "342x513", "w500": "500x750", "w780": "780x1170"}
	TMDB_GENRES = {10759: "Action-Abenteuer", 16: "Animation", 10762: "Kinder", 10763: "News", 10764: "Reality", 10765: "Sci-Fi-Fantasy", 10766: "Soap", 10767: "Talk", 10768: "War & Politics", 28: "Action", 12: "Abenteuer", 35: "Comedy", 80: "Crime", 99: "Dokumentation", 18: "Drama", 10751: "Familie", 14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Science-Fiction", 10770: "TV-Movie", 53: "Thriller", 10752: "War", 37: "Western"}
	EXCLUDENAMES = ["RTL UHD", "--", "Sendeschluss", "Dokumentation", "EaZzzy", "MediaShop", "Dauerwerbesendung", "Impressum"]
	APIKEYS = {"tmdb": ["ZTQ3YzNmYzJkYzRlMWMwN2UxNGE4OTc1YjI5MTE1NWI=", "MDA2ZTU5NGYzMzFiZDc1Nzk5NGQwOTRmM2E0ZmMyYWM=", "NTRkMzg1ZjBlYjczZDE0NWZhMjNkNTgyNGNiYWExYzM="],
		   	"tvdb": ["NTRLVFNFNzFZWUlYM1Q3WA==", "MzRkM2ZjOGZkNzQ0ODA5YjZjYzgwOTMyNjI3ZmE4MTM=", "Zjc0NWRiMDIxZDY3MDQ4OGU2MTFmNjY2NDZhMWY4MDQ="],
			"omdb": ["ZjQ3MjgxM2E=", "ZDNhMGNjMGI=", "MWRiMWVhMTc="]}
	DESKTOPSIZE = getDesktop(0).size()  # TODO: fliegt später raus, nutze ab dann RESOLUTION
	RESOLUTION = "FHD" if getDesktop(0).size().width() > 1300 else "HD"
	LIBFILE = "eventLibrary.db"
	TEMPPATH = "/var/volatile/tmp"
	LOGPATH = "/home/root/logs/"
	SKINPATH = resolveFilename(SCOPE_CURRENT_SKIN)  # e.g. /usr/share/enigma2/MetrixHD/
	SHAREPATH = resolveFilename(SCOPE_SKIN_IMAGE)  # /usr/share/enigma2/
	CONFIGPATH = resolveFilename(SCOPE_CONFIG, "AEL/")  # /etc/enigma2/AEL/
	PYTHONPATH = eEnv.resolve("${libdir}/enigma2/python/")  # /usr/lib/enigma2/python/
	PLUGINPATH = resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/AdvancedEventLibrary/")  # /usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/
	SKINPATH = f"{PLUGINPATH}skin/1080/" if DESKTOPSIZE.width() == 1920 else f"{PLUGINPATH}skin/720/"  # TODO: fliegt später raus
	NETWORKDICT = {}
	NETWORKFILE = join(CONFIGPATH, "networks.json")
	LOGFILE = join(LOGPATH, "ael_debug.log")
	TVS_MAPDICT = {}
	TVS_MAPFILE = join(CONFIGPATH, "tvs_mapping.txt")
	TVS_REFDICT = {}
	TVS_REFFILE = join(CONFIGPATH, "tvs_imported.json")

	def __init__(self):
		self.saving = False
		self.STATUS = ""
		self.setPaths()
		config.plugins.AdvancedEventLibrary.Location.addNotifier(self.setPaths)

	def setPaths(self, configItem=None):
		self.HDDPATH = config.plugins.AdvancedEventLibrary.Location.value
		if "AEL/" not in self.HDDPATH:
			self.HDDPATH = f"{self.HDDPATH}AEL/"
		self.createDirs(self.HDDPATH)
		self.POSTERPATH = f"{self.HDDPATH}poster/"
		self.COVERPATH = f"{self.HDDPATH}cover/"
		self.PREVIEWPATH = f"{self.HDDPATH}preview/"

	def createDirs(self, path):
		if not exists(path):
			makedirs(path)
		for subpath in ["poster/", "cover/", "preview/", "cover/thumbnails/", "poster/thumbnails/"]:
			if not exists(join(path, subpath)):
				makedirs(join(path, subpath))


aelGlobals = AELGlobals()
