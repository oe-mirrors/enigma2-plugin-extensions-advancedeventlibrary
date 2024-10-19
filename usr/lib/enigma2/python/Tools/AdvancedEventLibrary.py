#=================================================
# R140 by MyFriendVTI
# usr/lib/enigma2/python/Tools/AdvancedEventLibrary.py
# Aenderungen kommentiert mit hinzugefuegt, geaendert oder geloescht
# Aenderung (#1): Fix mp4
# Hinzugefuegt (#2): Check ReadOnly at CreateMetaInfo
# Aenderung (#3): Fix FindEpisode s0e0
# Aenderung (#4): Improvement Extradaten-Preview-Search
# Enfernt AELImageServer
# Enfernt Altersfreigaben.de
# Aenderung (#5): Rating von LiveOnTv entfernt
# Aenderung (#6): TMDB-Episoden-Cover Fix (Editor)
# Hinzugefuegt (#7): TMDB-Top-Treffer immer mit anzeigen (Editor)
# Aenderung (#8): Suche auch bei IPTV
# Aenderung (#9): Fix Key not in resultDict
# Aenderung (#10): Serienkennezeichnung 1-4 stellig
# Aenderung (#11): Global 'aelGlobals.NETWORKDICT' eingeführt und im Code ausgetauscht
# Aenderung (#12): POSTERPATH, COVERPATH & PREVIEWPATH im Code umgetauscht, b64decode() mit .decode() ergänzt, TVS-bugfix, Lokalisationen
# Aenderung (#13): new improved handling for TV Spielfilm
# ==================================================
from base64 import b64decode, b64encode
from datetime import datetime
from difflib import get_close_matches
from glob import glob
from io import StringIO
from json import loads
from linecache import getline
from os import makedirs, system, remove, walk, access, stat, listdir, W_OK
from os.path import join, exists, basename, getmtime, isdir, getsize
from PIL import Image
from re import compile, findall, IGNORECASE, MULTILINE, DOTALL
from requests import get, exceptions
from secrets import choice
from shutil import copy2, move
from sqlite3 import connect
from subprocess import check_output
from time import time, mktime
from twisted.internet.reactor import callInThread
from urllib.parse import urlparse, urlunparse
from enigma import eEnv, eEPGCache, eServiceReference, eServiceCenter, getDesktop, ePicLoad
from skin import parameters
from Components.config import config, ConfigText, ConfigSubsection, ConfigInteger, ConfigYesNo, ConfigSelection, ConfigClock
from Screens.ChannelSelection import service_types_tv
from Tools.Bytes2Human import bytes2human
from Tools.Directories import resolveFilename, defaultRecordingLocation, fileExists, SCOPE_CURRENT_PLUGIN, SCOPE_CONFIG, SCOPE_SKIN_IMAGE, SCOPE_CURRENT_SKIN
from Plugins.Extensions.AdvancedEventLibrary import _  # for localized messages
from . import tvdb_api_v4
import tmdbsimple as tmdb
import tvdbsimple as tvdb

config.plugins.AdvancedEventLibrary = ConfigSubsection()
config.plugins.AdvancedEventLibrary.Location = ConfigText(default=f"{defaultRecordingLocation().replace("movie/", "")}AEL/")
config.plugins.AdvancedEventLibrary.Backup = ConfigText(default="/media/hdd/AELbackup/")
config.plugins.AdvancedEventLibrary.MaxSize = ConfigInteger(default=1, limits=(1, 100))
config.plugins.AdvancedEventLibrary.PreviewCount = ConfigInteger(default=20, limits=(1, 50))
config.plugins.AdvancedEventLibrary.ShowInEPG = ConfigYesNo(default=False)
config.plugins.AdvancedEventLibrary.UseAELEPGLists = ConfigYesNo(default=False)
config.plugins.AdvancedEventLibrary.UseAELIS = ConfigYesNo(default=True)
config.plugins.AdvancedEventLibrary.UseAELMovieWall = ConfigYesNo(default=False)
config.plugins.AdvancedEventLibrary.Log = ConfigYesNo(default=False)
config.plugins.AdvancedEventLibrary.UsePreviewImages = ConfigYesNo(default=True)
config.plugins.AdvancedEventLibrary.coverQuality = ConfigSelection(default="w1280", choices=[("w300", "300x169"), ("w780", "780x439"), ("w1280", "1280x720"), ("w1920", "1920x1080")])
config.plugins.AdvancedEventLibrary.posterQuality = ConfigSelection(default="w780", choices=[("w185", "185x280"), ("w342", "342x513"), ("w500", "500x750"), ("w780", "780x1170")])
config.plugins.AdvancedEventLibrary.dbFolder = ConfigSelection(default=0, choices=[(0, _("Data directory")), (1, _("Flash"))])
config.plugins.AdvancedEventLibrary.MaxImageSize = ConfigSelection(default=200, choices=[(100, "100kB"), (150, "150kB"), (200, "200kB"), (300, "300kB"), (400, "400kB"), (500, "500kB"), (750, "750kB"), (1024, "1024kB"), (1000000, "unbegrenzt")])
config.plugins.AdvancedEventLibrary.MaxCompression = ConfigInteger(default=50, limits=(10, 90))
config.plugins.AdvancedEventLibrary.searchPlaces = ConfigText(default="")
config.plugins.AdvancedEventLibrary.SearchFor = ConfigSelection(default=0, choices=[(0, _("Extra data and images")), (1, _("Extra data only"))])
config.plugins.AdvancedEventLibrary.DelPreviewImages = ConfigYesNo(default=True)
config.plugins.AdvancedEventLibrary.CloseMenu = ConfigYesNo(default=True)
config.plugins.AdvancedEventLibrary.ViewType = ConfigSelection(default=0, choices=[(0, _("Wall view")), (1, _("List view"))])
config.plugins.AdvancedEventLibrary.FavouritesMaxAge = ConfigInteger(default=14, limits=(5, 90))
config.plugins.AdvancedEventLibrary.RefreshMovieWall = ConfigYesNo(default=True)
config.plugins.AdvancedEventLibrary.RefreshMovieWallAtStop = ConfigYesNo(default=True)
config.plugins.AdvancedEventLibrary.RefreshMovieWallAtStart = ConfigYesNo(default=False)
config.plugins.AdvancedEventLibrary.SortType = ConfigSelection(default=0, choices=[(0, _("Date descending")), (1, _("Date ascending")), (2, _("Name ascending")), (3, _("Name descending")), (4, _("Day ascending")), (5, _("Day descending"))])
config.plugins.AdvancedEventLibrary.ignoreSortSeriesdetection = ConfigYesNo(default=False)
config.plugins.AdvancedEventLibrary.SearchLinks = ConfigYesNo(default=True)
config.plugins.AdvancedEventLibrary.MaxUsedInodes = ConfigInteger(default=90, limits=(20, 95))
config.plugins.AdvancedEventLibrary.CreateMetaData = ConfigYesNo(default=False)
config.plugins.AdvancedEventLibrary.UpdateAELMovieWall = ConfigYesNo(default=True)
config.plugins.AdvancedEventLibrary.Genres = ConfigSelection(default=0, choices=[(0, _("Movies")), (1, _("Series")), (2, _("Documentaries")), (3, _("Music")), (4, _("Children")), (5, _("Shows")), (6, _("Sport"))])
# config.plugins.AdvancedEventLibrary.ExcludedGenres.value.split(",")
config.plugins.AdvancedEventLibrary.StartBouquet = ConfigSelection(default=0, choices=[(0, _("Favorites")), (1, _("All Bouquets"))])
config.plugins.AdvancedEventLibrary.HDonly = ConfigYesNo(default=True)
config.plugins.AdvancedEventLibrary.StartTime = ConfigClock(default=69300)  # 20:15
config.plugins.AdvancedEventLibrary.Duration = ConfigInteger(default=60, limits=(20, 1440))
config.plugins.AdvancedEventLibrary.tmdbUsage = ConfigSelection(default=3, choices=[(0, _("off")), (1, _("Data only")), (2, _("Image only")), (3, _("Data+Image"))])
config.plugins.AdvancedEventLibrary.tmdbKey = ConfigText(default=_("internal"))
config.plugins.AdvancedEventLibrary.tvdbUsage = ConfigSelection(default=3, choices=[(0, _("off")), (1, _("Data only")), (2, _("Image only")), (3, _("Data+Image"))])
config.plugins.AdvancedEventLibrary.tvdbV4Key = ConfigText(default=_("unused"))
config.plugins.AdvancedEventLibrary.tvdbKey = ConfigText(default=_("internal"))
config.plugins.AdvancedEventLibrary.tvmaszeUsage = ConfigSelection(default=1, choices=[(0, _("off")), (1, _("Data only"))])
config.plugins.AdvancedEventLibrary.omdbUsage = ConfigSelection(default=1, choices=[(0, _("off")), (1, _("Data only"))])
config.plugins.AdvancedEventLibrary.omdbKey = ConfigText(default=_("internal"))
config.plugins.AdvancedEventLibrary.tvsUsage = ConfigSelection(default=1, choices=[(0, _("off")), (1, _("Data only"))])
config.plugins.AdvancedEventLibrary.tvmovieUsage = ConfigSelection(default=1, choices=[(0, _("off")), (1, _("Data only"))])
config.plugins.AdvancedEventLibrary.bingUsage = ConfigSelection(default=2, choices=[(0, _("off")), (2, _("Image only"))])

DEFAULT_MODULE_NAME = __name__.split(".")[-1]
#not used
#vtidb_loc = config.misc.db_path.value + "/vtidb.db"
# convNames = ["Polizeiruf", "Tatort", "Die Bergpolizei", "Axte X", "ANIXE auf Reisen", "Close Up", "Der Zürich-Krimi", "Buffy", "Das Traumschiff", "Die Land", "Faszination Berge", "Hyperraum", "Kreuzfahrt ins Gl", "Lost Places", "Mit offenen Karten", "Newton", "Planet Schule", "Punkt 12", "Regular Show", "News Reportage", "News Spezial", "S.W.A.T", "Xenius", "Der Barcelona-Krimi", "Die ganze Wahrheit", "Firmen am Abgrund", "GEO Reportage", "Kommissar Wallander", "Rockpalast", "SR Memories", "Wildes Deutschland", "Wilder Planet", "Die rbb Reporter", "Flugzeug-Katastrophen", "Heute im Osten", "Kalkofes Mattscheibe", "Neue Nationalparks", "Auf Entdeckungsreise"]


def getDB():
	basepath = aelGlobals.CONFIGPATH if config.plugins.AdvancedEventLibrary.dbFolder.value == 1 else aelGlobals.HDDPATH
	return DB_Functions(join(basepath, "eventLibrary.db"))


def load_json(filename):
	with open(filename, "r") as f:
		data = f.read().replace('null', '""')
	return eval(data)


def get_keys(forwhat):
	selected = {"tmdb": config.plugins.AdvancedEventLibrary.tmdbKey.value,
			   	"tvdb": config.plugins.AdvancedEventLibrary.tvdbKey.value,
				"omdb": config.plugins.AdvancedEventLibrary.omdbKey.value
				}.get(forwhat, "")
	return selected if selected != _("internal") else b64decode(choice(aelGlobals.APIKEYS[forwhat])).decode()


def get_TVDb():
	tvdbV4Key = config.plugins.AdvancedEventLibrary.tvdbV4Key.value
	if tvdbV4Key != _("unused"):
		tvdbV4 = tvdb_api_v4.TVDB(tvdbV4Key)
		if tvdbV4.get_login_state():
			return tvdbV4


def convert2base64(title):
	return b64encode(title.lower().split("(")[0].strip().encode()).decode() if title.find("(") > 1 else b64encode(title.lower().strip().encode()).decode()


def convertSigns(text):
	return text.replace("\xe2\x80\x90", "-").replace("\xe2\x80\x91", "-").replace("\xe2\x80\x92", "-").replace("\xe2\x80\x93", "-")


def createDirs(path):
	if not exists(path):
		makedirs(path)
	for subpath in ["poster/", "cover/", "preview/", "cover/thumbnails/", "poster/thumbnails/"]:
		if not exists(join(path, subpath)):
			makedirs(join(path, subpath))


def write_log(svalue, module=DEFAULT_MODULE_NAME):
	with open(aelGlobals.LOGFILE, "a") as file:
		file.write(f"{datetime.now().strftime("%T")} : [{module}] - {svalue}\n")


def getAPIdata(url, params=None):
	try:
		headers = {"User-Agent": choice(aelGlobals.AGENTS)}
		response = get(url, params=params, headers=headers, timeout=(3.05, 6))
		response.raise_for_status()
		status = response.status_code
		if status == 200:
			jsondict, errmsg = loads(response.text), ""
		else:
			jsondict, errmsg = {}, f"API server access ERROR, response code: {status}"
		return errmsg, jsondict
	except exceptions.RequestException as errmsg:
		write_log(f"ERROR in module 'getAPIdata': {errmsg}")
		return errmsg, {}


def getHTMLdata(url, params=None):
	try:
		headers = {"User-Agent": choice(aelGlobals.AGENTS)}
		response = get(url, params=params, headers=headers, timeout=(3.05, 6))
		response.raise_for_status()
		htmldata = response.text
		return "", htmldata
	except exceptions.RequestException as errmsg:
		write_log(f"ERROR in module 'getHTMLdata': {errmsg}")
		return errmsg, {}


def callLibrary(libcall, title, **kwargs):
	if kwargs and kwargs.get("year", None) == "":  # in case 'year' is empty string
		kwargs.pop("year", None)
	try:  # mandatory because called library raises an error when no result
		response = libcall(title, **kwargs) if title else libcall(**kwargs)
	except Exception:
		if kwargs:
			kwargs.pop("language", None)
			kwargs.pop("year", None)
		try:  # fallback: try without language and/or without year
			response = libcall(title, **kwargs) if title else libcall(**kwargs)
		except Exception as errmsg:
			response = ""
			write_log(f"EXCEPTION in module 'callLibrary': {errmsg}")  # TODO: Errorlogging hier rausschmeißen!
	return response


def removeExtension(ext):
	return ext.replace(".wmv", "").replace(".mpeg2", "").replace(".ts", "").replace(".m2ts", "").replace(".mkv", "").replace(".avi", "").replace(".mpeg", "").replace(".mpg", "").replace(".iso", "").replace(".mp4", "")


def getMemInfo(value):
	result = [0, 0, 0, 0]  # (size, used, avail, use%)
	check = 0
	with open("/proc/meminfo") as fd:
		for line in fd:
			if f"{value}Total" in line:
				check += 1
				result[0] = int(line.split()[1]) * 1024  # size
			elif f"{value}Free" in line:
				check += 1
				result[2] = int(line.split()[1]) * 1024  # avail
			if check > 1:
				if result[0] > 0:
					result[1] = result[0] - result[2]  # used
					result[3] = int(result[1] * 100 / result[0])  # use%
				break
	return f"{getSizeStr(result[1])} ({result[3]}%)"


def getSizeStr(value, u=0):
	fractal = 0
	if value >= 1024:
		fmt = "%(size)u.%(frac)d %(unit)s"
		while (value >= 1024) and (u < len(aelGlobals.SIZE_UNITS)):
			(value, mod) = divmod(value, 1024)
			fractal = mod * 10 / 1024
			u += 1
	else:
		fmt = "%(size)u %(unit)s"
	return fmt % {"size": value, "frac": fractal, "unit": aelGlobals.SIZE_UNITS[u]}


def clearMem(screenName=""):
	write_log(f"{screenName} - Memory utilization before cleanup: {getMemInfo("Mem")}")
	system('sync')
	system('sh -c "echo 3 > /proc/sys/vm/drop_caches"')
	write_log(f"{screenName} - Memory utilization before cleanup: {getMemInfo("Mem")}")


def createBackup():
	backuppath = config.plugins.AdvancedEventLibrary.Backup.value
	aelGlobals.setStatus(f"{_('create backup in')} {backuppath}")
	write_log(f"create backup in {backuppath}")
	for currpath in [backuppath, f"{backuppath}poster/", f"{backuppath}cover/"]:
		if not exists(currpath):
			makedirs(currpath)
	dbpath = join(aelGlobals.CONFIGPATH, "eventLibrary.db") if config.plugins.AdvancedEventLibrary.dbFolder.value == 1 else join(aelGlobals.HDDPATH, "eventLibrary.db")
	if fileExists(dbpath):
		copy2(dbpath, join(backuppath, "eventLibrary.db"))
	files = glob(f"{aelGlobals.POSTERPATH}*.*")
	progress = 0
	pics = len(files)
	copied = 0
	for filename in files:
		progress += 1
		target = join(f"{backuppath}poster/", basename(filename))
		if not fileExists(target) or getmtime(filename) > (getmtime(target) + 7200):
			copy2(filename, target)
			aelGlobals.setStatus(f"({progress}/{pics} {_('save poster:')} {filename}")
			copied += 1
	write_log(f"have copied {copied} poster to {backuppath} poster/")
	del files
	files = glob(f"{aelGlobals.POSTERPATH}*.*")
	progress = 0
	pics = len(files)
	copied = 0
	for filename in files:
		progress += 1
		target = join(f"{backuppath}cover/", basename(filename))
		if not fileExists(target) or getmtime(filename) > getmtime(target):
			copy2(filename, target)
			aelGlobals.setStatus(f"({progress}/{pics}) {_('save cover')}: {filename}")
			copied += 1
	write_log(f"have copied {copied} cover to {backuppath}cover/")
	del files
	aelGlobals.setStatus()
	clearMem("createBackup")
	write_log("backup finished")


def checkUsedSpace(db=None):
	recordings = getRecordings()
	dbpath = join(aelGlobals.CONFIGPATH, "eventLibrary.db") if config.plugins.AdvancedEventLibrary.dbFolder.value == 1 else join(aelGlobals.HDDPATH, "eventLibrary.db")
	if fileExists(dbpath) and db:
		maxSize = 1 * 1024.0 * 1024.0 if "/etc" in aelGlobals.HDDPATH else config.plugins.AdvancedEventLibrary.MaxSize.value * 1024.0 * 1024.0
		posterSize = float(check_output(["du", "-sk", aelGlobals.POSTERPATH]).decode().split()[0])
		coverSize = float(check_output(["du", "-sk", aelGlobals.COVERPATH]).decode().split()[0])
		previewSize = float(check_output(["du", "-sk", aelGlobals.PREVIEWPATH]).decode().split()[0])
		inodes = check_output(["df", "-i", aelGlobals.HDDPATH]).decode().split()[-2]
		write_log(f"used Inodes: {inodes}")
		write_log(f"used memory space: {(posterSize + coverSize)} {_('KB of')} {maxSize} KB.")
		usedInodes = int(inodes[:-1])
		if (((round(posterSize) + round(coverSize) + round(previewSize)) > round(maxSize)) or usedInodes >= config.plugins.AdvancedEventLibrary.MaxUsedInodes.value):
			removeList = glob(join("{aelGlobals.PREVIEWPATH}*.*"))
			for f in removeList:
				remove(f)
			i = 0
			while i < 100:
				titles = db.getUnusedTitles()
				if titles:
					aelGlobals.setStatus(f"{_('Cleaning up the storage space')} #{(i + 1)}")
					write_log(f"Cleaning up the storage space #{(i + 1)}")
					for title in titles:
						if str(title[1]) not in recordings:
							for currdir in [f"{aelGlobals.POSTERPATH}{title[0]}", f"{aelGlobals.POSTERPATH}thumbnails/{title[0]}", f"{aelGlobals.COVERPATH}{title[0]}", f"{aelGlobals.COVERPATH}thumbnails/{title[0]}"]:
								for filename in glob(f"{currdir}*.*"):
									remove(filename)
								db.cleanDB(title[0])
					posterSize = float(check_output(["du", "-sk", aelGlobals.POSTERPATH]).decode().split()[0])
					coverSize = float(check_output(["du", "-sk", aelGlobals.COVERPATH]).decode().split()[0])
					write_log(f"used memory space: {(posterSize + coverSize)} {_('KB of')} {maxSize} KB.")
				if (posterSize + coverSize) < maxSize:
					break
				i += 1
			db.vacuumDB()
			write_log(f"finally used memory space: {posterSize + coverSize} {_('KB of')} {maxSize} KB.")


def removeLogs():
	if fileExists(aelGlobals.LOGFILE):
		remove(aelGlobals.LOGFILE)


def createMovieInfo(db):
	aelGlobals.setStatus(_("search for missing meta files..."))
	recordPaths = config.movielist.videodirs.value
	for recordPath in recordPaths:
		if isdir(recordPath):
			for root, directories, files in walk(recordPath):
				if isdir(root) and str(root) in aelGlobals.SPDICT and aelGlobals.SPDICT[root]:
					for filename in files:
						if not access(join(root, filename), W_OK):
							continue
						foundAsMovie = False
						foundOnTMDbTV = False
						foundOnTVDb = False
						if (filename.endswith(".ts") or filename.endswith(".mkv") or filename.endswith(".avi") or filename.endswith(".mpg") or filename.endswith(".mp4") or filename.endswith(".iso") or filename.endswith(".mpeg2")):
							if not db.getimageBlackList(removeExtension(filename)):
								if not fileExists(join(root, f"{filename}.meta")):
									title = convertSearchName(convertDateInFileName(((filename.split("/")[-1]).rsplit(".", 1)[0]).replace("__", " ").replace("_", " ")))
									mtitle = title
									titleNyear = convertYearInTitle(title)
									title = titleNyear[0]
									jahr = str(titleNyear[1])
									if title and title != " ":
										tmdb.API_KEY = get_keys("tmdb")
										titleinfo = {"title": mtitle, "genre": "", "year": "", "country": "", "overview": ""}
										aelGlobals.setStatus(f"{_("search meta information for")} {title}")
										search = tmdb.Search()
										response = callLibrary(search.movie, "", query=title, language="de", year=jahr) if jahr != "" else callLibrary(search.movie, "", query=title, language="de")  # TODO: hier die Boxsprache einsetzen
										if response and response.get("results", []):
											reslist = []
											for item in response.get("results", []):
												reslist.append(item.get("title", "").lower())
											bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
											if not bestmatch:
												bestmatch = [title.lower()]
											for item in response.get("results", []):
												if item.get("title", "").lower() == bestmatch[0]:
													foundAsMovie = True
													titleinfo["title"] = item.get("title", "")
													titleinfo["overview"] = item.get("overview", "")
													titleinfo["year"] = item.get("release_date", "")[:4]
													for genre in item.get("genre_ids", []):
														if aelGlobals.TMDB_GENRES[genre] not in titleinfo.get("genre", {}):
															titleinfo["genre"] = f"{titleinfo.get("genre", {})}{aelGlobals.TMDB_GENRES[genre]} "
														maxGenres = titleinfo.get("genre", []).split()
														if maxGenres:
															titleinfo["genre"] = maxGenres[0]
													details = tmdb.Movies(item.get("id", ""))
													for country in details.info(language="de").get("production_countries", ""):  # TODO: hier die Boxsprache einsetzen
														titleinfo["country"] = f"{titleinfo.get("country", {})}{country.get("iso_3166_1", "")} | "
													titleinfo["country"] = titleinfo.get("country", "")[:-3]
													break
										if not foundAsMovie:
											search = tmdb.Search()
											searchName = findEpisode(title)
											if searchName:
												response = callLibrary(search.tv, None, query=searchName[2], language="de", include_adult=True, search_type="ngram")  # TODO: hier die Boxsprache einsetzen
											else:
												response = callLibrary(search.tv, None, query=title, language="de", include_adult=True, search_type="ngram")  # TODO: hier die Boxsprache einsetzen
											if response:
												if response.get("results", []):
													reslist = []
													for item in response.get("results", []):
														reslist.append(item.get("name", "").lower())
													if searchName:
														bestmatch = get_close_matches(searchName[2].lower(), reslist, 1, 0.7)
														if not bestmatch:
															bestmatch = [searchName[2].lower()]
													else:
														bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
														if not bestmatch:
															bestmatch = [title.lower()]
													for item in response.get("results", []):
														if item.get("name", "").lower() == bestmatch[0]:
															foundOnTMDbTV = True
															if searchName:
																details = tmdb.TV_Episodes(item.get("id", ""), searchName[0], searchName[1])
																episode = details.info(language="de")  # TODO: hier die Boxsprache einsetzen
																titleinfo["title"] = f"{item.get("name", "")} - S{searchName[0]}E{searchName[1]} - {episode.get("name", "").lower()}"
																titleinfo["year"] = episode.get("air_date", "")[:4]
																titleinfo["overview"] = episode.get("overview", "")
																for country in item.get("origin_country", []):  # e.g. ['HR', 'FR', 'DE']
																	titleinfo["country"] = f"{titleinfo.get("country", {})}{country} | "
																titleinfo["country"] = titleinfo.get("country", "")[:-3]
																for genre in item.get("genre_ids", []):
																	if aelGlobals.TMDB_GENRES[genre] not in titleinfo.get("genre", {}):
																		titleinfo["genre"] = f"{titleinfo.get("genre", {})}{aelGlobals.TMDB_GENRES[genre]}-{_("series")}"
																	maxGenres = titleinfo.get("genre", []).split()
																	if maxGenres:
																		if len(maxGenres):
																			titleinfo["genre"] = maxGenres[0]
															else:
																titleinfo["title"] = item.get("name", "")
																titleinfo["overview"] = item.get("overview", "")
																for country in item.get("origin_country", []):  # e.g. ['HR', 'FR', 'DE']
																	titleinfo["country"] = f"{titleinfo.get("country", {})}{country} | "
																titleinfo["country"] = titleinfo.get("country", "")[:-3]
																titleinfo["year"] = item.get("first_air_date", "")[:4]
																for genre in item.get("genre_ids", []):
																	if aelGlobals.TMDB_GENRES[genre] not in titleinfo.get("genre", {}):
																		titleinfo["genre"] = f"{titleinfo.get("genre", {})}{aelGlobals.TMDB_GENRES[genre]}-{_("series")}"
																	maxGenres = titleinfo.get("genre", []).split()
																	if maxGenres:
																		titleinfo["genre"] = maxGenres[0]
															break
										if not foundAsMovie and not foundOnTMDbTV:
											tvdb.KEYS.API_KEY = get_keys("tvdb")
											search = tvdb.Search()
											seriesid = None
											title = convertTitle2(title)
											response = callLibrary(search.series, title, language="de")  # TODO: hier die Boxsprache einsetzen
											if response:
												reslist = []
												for result in response:
													reslist.append(result.get("seriesName", "").lower())
												bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
												if not bestmatch:
													bestmatch = [title.lower()]
												for result in response:
													if result.get("seriesName", "").lower() == bestmatch[0]:
														seriesid = result.get("id", "")
														break
											if seriesid:
												foundOnTVDb = True
												show = tvdb.Series(seriesid)
												response = show.info()
												epis = tvdb.Series_Episodes(seriesid)
												try:  # mandatory because the library raises an error when no result
													episoden = epis.all()
												except Exception:
													episoden = []
												if episoden:
													for episode in episoden:
														if episode.get("episodeName", "") in title:
															titleinfo["year"] = episode.get("firstAired", "")[:4]
															titleinfo["overview"] = episode.get("overview", "")
															if response:
																searchName = findEpisode(title)
																titleinfo["title"] = f"{response.get("seriesName", "")} - S{searchName[0]}E{searchName[1]} - {episode.get("episodeName", "")}" if searchName else f"{response.get("seriesName", "")} - {episode.get("episodeName", "")}"
																if not titleinfo.get("genre", {}):
																	for genre in response.get("genre", {}):
																		titleinfo["genre"] = f"{titleinfo.get("genre", {})}{genre}-{_("series")}"
																titleinfo["genre"] = titleinfo.get("genre", []).replace("Documentary", "Dokumentation").replace("Children", "Kinder")
																if not titleinfo.get("country", {}):
																	titleinfo["country"] = aelGlobals.NETWORKDICT.get(response.get("network", ""), "")
																break
												else:
													if response:
														titleinfo["title"] = response.get("seriesName", "")
														if titleinfo.get("year", "") == "":
															titleinfo["year"] = response.get("firstAired", "")[:4]
														if titleinfo.get("genre", {}) == "":
															for genre in response.get("genre", {}):
																titleinfo["genre"] = f"{titleinfo.get("genre", {})}{genre}-{_("series")}"
														titleinfo["genre"] = titleinfo.get("genre", []).replace("Documentary", "Dokumentation").replace("Children", "Kinder")
														titleinfo["country"] = aelGlobals.NETWORKDICT.get(response.get("network", ""), "")
														titleinfo["overview"] = response.get("overview", "")
										if titleinfo.get("overview", ""):
											txt = open(join(root, f"{removeExtension(filename)}.txt"), "w")
											txt.write(titleinfo.get("overview", ""))
											txt.close()
											write_log(f"createMovieInfo for '{filename}'")
										if foundAsMovie or foundOnTMDbTV or foundOnTVDb:
											if titleinfo.get("year", "") or titleinfo.get("genre", {}) or titleinfo.get("country", {}):
												filedt = int(stat(join(root, filename)).st_mtime)
												txt = open(join(root, f"{filename}.meta"), "w")
												minfo = f"'1:0:0:0:B:0:C00000:0:0:0:\n'{titleinfo.get("title", "")}\n"
												if titleinfo.get("genre", {}):
													minfo += f"{titleinfo.get("genre", {})}, "
												if titleinfo.get("country", {}):
													minfo += f"{titleinfo.get("country", {})}, "
												if titleinfo.get("year", ""):
													minfo += f"{titleinfo.get("year", "")}, "
												if minfo.endswith(", "):
													minfo = minfo[:-2]
												else:
													minfo += "\n"
												minfo += f"\n{filedt}\nAdvanced-Event-Library\n"
												txt.write(minfo)
												txt.close()
												write_log(f"create meta-Info for '{join(root, filename)}'")
											else:
												db.addimageBlackList(removeExtension(filename))
										else:
											db.addimageBlackList(removeExtension(filename))
											write_log(f"no meta files found for '{join(root, filename)}'")


def getAllRecords(db):
	names = set()
	aelGlobals.setStatus(_("search recording directories..."))
	recordPaths = config.movielist.videodirs.value
	doPics = True if "Pictures" not in aelGlobals.SPDICT or ("Pictures" in aelGlobals.SPDICT and aelGlobals.SPDICT["Pictures"]) else False
	for recordPath in recordPaths:
		if isdir(recordPath):
			for root, directories, files in walk(recordPath):
				if isdir(root):
					fileCount = 0
					if str(root) in aelGlobals.SPDICT and aelGlobals.SPDICT[root]:
						name = ""
						for filename in files:
							if (filename.endswith(".ts") or filename.endswith(".mkv") or filename.endswith(".avi") or filename.endswith(".mpg") or filename.endswith(".mp4") or filename.endswith(".iso") or filename.endswith(".mpeg2")) and doPics:
								if fileExists(join(root, f"{filename}.meta")):
									fname = convertDateInFileName(getline(join(root, f"{filename}.meta"), 2).replace("\n", ""))
								else:
									fname = convertDateInFileName(convertSearchName(convertTitle(((filename.split("/")[-1]).rsplit(".", 3)[0]).replace("_", " "))))
								searchName = filename
								if (fileExists(join(root, searchName)) and not fileExists(join(aelGlobals.POSTERPATH, fname))):
									write_log(f"copy poster {searchName} nach {fname}")
									copy2(join(root, searchName), join(aelGlobals.POSTERPATH, fname))
								searchName = removeExtension(filename)
								if (fileExists(join(root, searchName)) and not fileExists(join(aelGlobals.POSTERPATH, fname))):
									write_log(f"copy poster {searchName} nach {fname}")
									copy2(join(root, searchName), join(aelGlobals.POSTERPATH, fname))
								searchName = f"{filename}.bdp.jpg"  # TODO: was genau soll das? Gilt das auch für PNG und GIF?
								if (fileExists(join(root, searchName)) and not fileExists(join(aelGlobals.COVERPATH, fname))):
									write_log(f"copy cover {searchName} nach {fname}")
									copy2(join(root, searchName), join(aelGlobals.COVERPATH, fname))
								searchName = f"{removeExtension(filename)}.bdp.jpg"  # TODO: was genau soll das? Gilt das auch für PNG und GIF?
								if (fileExists(join(root, searchName)) and not fileExists(join(aelGlobals.COVERPATH, fname))):
									write_log(f"copy cover {searchName} nach {fname}")
									copy2(join(root, searchName), join(aelGlobals.COVERPATH, fname))
							if filename.endswith(".meta"):
								fileCount += 1
								foundInBl = False
								fname = convertDateInFileName(getline(join(root, filename), 2).replace("\n", ""))
								if db.getblackList(fname):
									fname = convertDateInFileName(convertTitle(getline(join(root, filename), 2).replace("\n", "")))
									if db.getblackList(fname):
										fname = convertDateInFileName(convertTitle2(getline(join(root, filename), 2).replace("\n", "")))
										if db.getblackList(fname):
											foundInBl = True
								if not db.checkTitle(fname) and not foundInBl and fname != "" and fname != " ":
									names.add(fname)
							if (filename.endswith(".ts") or filename.endswith(".mkv") or filename.endswith(".avi") or filename.endswith(".mpg") or filename.endswith(".mp4") or filename.endswith(".iso") or filename.endswith(".mpeg2")) and doPics:
								foundInBl = False
								service = eServiceReference("1:0:0:0:0:0:0:0:0:0:" + join(root, filename)) if filename.endswith(".ts") else eServiceReference("4097:0:0:0:0:0:0:0:0:0:" + join(root, filename))
								info = eServiceCenter.getInstance().info(service)
								if info:
									fname = removeExtension(info.getName(service))
									if not fname:
										fname = convertDateInFileName(((filename.split("/")[-1]).rsplit(".", 1)[0]).replace("__", " ").replace("_", " "))
								else:
									fname = convertDateInFileName(((filename.split("/")[-1]).rsplit(".", 1)[0]).replace("__", " ").replace("_", " "))
								if db.getblackList(fname):
									fname = convertDateInFileName(convertTitle(((filename.split("/")[-1]).rsplit(".", 1)[0]).replace("__", " ").replace("_", " ")))
									if db.getblackList(fname):
										fname = convertDateInFileName(convertTitle2(((filename.split("/")[-1]).rsplit(".", 1)[0]).replace("_", " ")))
										if db.getblackList(fname):
											foundInBl = True
								if not db.checkTitle(fname) and not foundInBl and fname != "" and fname != " ":
									names.add(fname)
						write_log(f"check {fileCount} meta Files in {root}")
				else:
					write_log(f"recordPath {root} is not exists")
		else:
			write_log(f"recordPath {recordPath} is not exists")
	write_log(f"found {len(names)} new Records in meta Files")
#		check vtidb
		#doIt = False
		#if "VTiDB" in aelGlobals.SPDICT:
		#	if aelGlobals.SPDICT["VTiDB"]:
		#		doIt = True
		#else:
		#	doIt = True
		#if (fileExists(vtidb_loc) and doIt):
		#	aelGlobals.setStatus("durchsuche VTI-DB...")
		#	vtidb_conn = connect(vtidb_loc, check_same_thread=False)
		#	cur = vtidb_conn.cursor()
		#	query = "SELECT title FROM moviedb_v0001"
		#	cur.execute(query)
		#	rows = cur.fetchall()
		#	if rows:
		#		write_log("check " + str(len(rows)) + " titles tidb")
		#		for row in rows:
		#			try:
		#				if row[0] and row[0] != "" and row[0] != " ":
		#					foundInBl = False
		#					name = convertTitle(row[0])
		#					if db.getblackList(convert2base64(name)):
		#						name = convertTitle2(row[0])
		#						if db.getblackList(convert2base64(name)):
		#							foundInBl = True
		#					if not db.checkTitle(convert2base64(name)) and not foundInBl:
		#						names.add(name)
		#			except Exception as ex:
		#				write_log("Error in getAllRecords vtidb: " + str(row[0]) + " - " + str(ex))
		#				continue
		#write_log("found " + str(len(names)) + " new Records")
	return names


def getRecordings():
	names = set()
	recordPaths = config.movielist.videodirs.value
	doPics = False
	for recordPath in recordPaths:
		if isdir(recordPath):
			for root, directories, files in walk(recordPath):
				if isdir(root) and str(root) in aelGlobals.SPDICT and aelGlobals.SPDICT[root]:
					fname = ""
					for filename in files:
						if filename.endswith(".meta"):
							fname = convertDateInFileName(getline(join(root, filename), 2).replace("\n", ""))
							names.add(fname)
							names.add(convertDateInFileName(convertTitle(fname)))
							names.add(convertDateInFileName(convertTitle2(fname)))
						if (filename.endswith(".ts") or filename.endswith(".mkv") or filename.endswith(".avi") or filename.endswith(".mpg") or filename.endswith(".mp4") or filename.endswith(".iso") or filename.endswith(".mpeg2")) and doPics:
							fname = convertDateInFileName(((filename.split("/")[-1]).rsplit(".", 1)[0]).replace("__", " ").replace("_", " "))
							names.add(fname)
							names.add(convertDateInFileName(convertTitle(fname)))
							names.add(convertDateInFileName(convertTitle2(fname)))
							service = eServiceReference("1:0:0:0:0:0:0:0:0:0:" + join(root, filename)) if filename.endswith(".ts") else eServiceReference("4097:0:0:0:0:0:0:0:0:0:" + join(root, filename))
							info = eServiceCenter.getInstance().info(service)
							fname = info.getName(service)
							names.add(fname)
							names.add(convertDateInFileName(convertTitle(fname)))
							names.add(convertDateInFileName(convertTitle2(fname)))
	return names


def cleanPreviewImages(db):
	recImages = getRecordings()
	prevImages = db.getUnusedPreviewImages(int(time() - 28800))
	ic = 0
	it = 0
	for image in prevImages:
		if image not in recImages:
			imgfile = join(aelGlobals.PREVIEWPATH, image)
			if fileExists(imgfile):
				remove(imgfile)
				ic += 1
			imgfile = join(f"{aelGlobals.PREVIEWPATH}thumbnails", image)
			if fileExists(imgfile):
				remove(imgfile)
				it += 1
		else:
			write_log(f"can't remove {image}, because it's a record")
	write_log(f"have removed {ic} preview images")
	write_log(f"have removed {it} preview thumbnails")
	del recImages
	del prevImages


def startUpdate():
	callInThread(getallEventsfromEPG)


def getallEventsfromEPG():
	aelGlobals.setStatus(_("verify directories..."))
	createDirs(aelGlobals.HDDPATH)
	aelGlobals.setStatus(_("remove logfile..."))
	removeLogs()
	write_log("### update start... ###")
	write_log(f"default image path is {aelGlobals.HDDPATH[:-1]}")
	write_log(f"load preview images is: {config.plugins.AdvancedEventLibrary.UsePreviewImages.value}")
	write_log(f"searchOptions {aelGlobals.SPDICT}")
	db = getDB()
	db.parameter(aelGlobals.PARAMETER_SET, "laststart", str(time()))
	cversion = db.parameter(aelGlobals.PARAMETER_GET, "currentVersion", None, 111)
	if cversion and int(cversion) < 113:
		db.parameter(aelGlobals.PARAMETER_SET, "currentVersion", "115")
		db.cleanliveTV(int(time() + (14 * 86400)))
	aelGlobals.setStatus(_("check reserved disk space..."))
	checkUsedSpace(db)
	names = getAllRecords(db)
	aelGlobals.setStatus(_("searching current EPG..."))
	lines = []
	mask = (eServiceReference.isMarker | eServiceReference.isDirectory)
	root = eServiceReference(f'{service_types_tv} FROM BOUQUET "bouquets.tv" ORDER BY bouquet')
	serviceHandler = eServiceCenter.getInstance()
	tvbouquets = serviceHandler.list(root).getContent("SN", True)
	for bouquet in tvbouquets:
		root = eServiceReference(str(bouquet[0]))
		serviceHandler = eServiceCenter.getInstance()
		ret = serviceHandler.list(root).getContent("SN", True)
		isInsPDict = bouquet[1] in aelGlobals.SPDICT
		if not isInsPDict or (isInsPDict and aelGlobals.SPDICT[bouquet[1]]):
			for (serviceref, servicename) in ret:
				playable = not (eServiceReference(serviceref).flags & mask)
				# =========== geaendert (#8) =====================
				if playable and "<n/a>" not in servicename and servicename != "." and serviceref:
					if serviceref not in aelGlobals.TVS_REFDICT and "%3a" not in serviceref:
#				if playable and "p%3a" not in serviceref and "<n/a>" not in servicename and servicename != "." and not serviceref.startswith("4097"):
#					if serviceref not in tvsref:
				# ===============================================
						write_log(f"'HINT: {servicename}' with reference '{serviceref}' could not be found in the TVS reference list!'")
					line = [serviceref, servicename]
					if line not in lines:
						lines.append(line)
	test = ["RITB", 0]
	for line in lines:
		test.append((line[0], 0, int(time() + 1000), -1))
	# write_log(f"debug test: {test}")
	epgcache = eEPGCache.getInstance()
	allevents = epgcache.lookupEvent(test) or []
	write_log(f"found {len(allevents)} Events in EPG")
	evt = 0
	liveTVRecords = []
	for serviceref, eid, name, begin in allevents:
		#==== hinzugefuegt (#8) =====
		if not serviceref:
			continue
		serviceref = serviceref.split("?", 1)[0]
		# =========================
		evt += 1
		aelGlobals.setStatus(f"{_('searching current EPG...')} ({evt}/{len(allevents)})")
		tvname = name
		# tvname = sub(r"\\(.*?\\)", "", tvname).strip()  # TODO: Ist dieser komische Regex wirklich nötig?
		# tvname = tvname.replace(" +", " ") # TODO: Ist replace wirklich nötig?
		#if not db.checkliveTV(eid, serviceref) and str(tvname) not in aelGlobals.EXCLUDENAMES and not "Invictus" in str(tvname):
		minEPGBeginTime = time() - 7200  # -2h
		maxEPGBeginTime = time() + 1036800  # 12Tage
		if begin > minEPGBeginTime and begin < maxEPGBeginTime:
			if not db.checkliveTV(eid, serviceref):
				if tvname not in aelGlobals.EXCLUDENAMES and "Invictus" not in str(tvname):
					record = (eid, "in progress", "", "", "", "", "", tvname, begin, "", "", "", "", "", "", "", "", serviceref)
					liveTVRecords.append(record)
		foundInBl = False
		name = convertTitle(name)
		if db.getblackList(convert2base64(name)):
			name = convertTitle2(name)
			if db.getblackList(convert2base64(name)):
				foundInBl = True
		if not db.checkTitle(convert2base64(name)) and not foundInBl:
			names.add(name)
	write_log(f"check {len(names)} new events")
	limgs = False if config.plugins.AdvancedEventLibrary.SearchFor.value == 1 else True  # "Extra data only"
	get_titleInfo(names, None, limgs, db, liveTVRecords)
	del names
	del lines
	del allevents
	del liveTVRecords


def get_titleInfo(titles, research=None, loadImages=True, db=None, liveTVRecords=[], lang="de"):  # purpose: try to find 'titleinfo' and fill up DICT via several servers
	tvdbV4 = get_TVDb()
	if not tvdbV4:
		write_log("TVDb API-V4 is not in use!")
	posters, covers, entrys, blentrys, position = 0, 0, 0, 0, 0
	for title in titles:
		if title and title != " " and "BL:" not in title:
			titleinfo = {"title": "", "genre": "", "poster_url": "", "backdrop_url": "", "year": "", "rating": "", "fsk": "", "country": ""}
			titleinfo["title"] = convertSearchName(title)
			titleNyear = convertYearInTitle(title)
			title = convertSearchName(titleNyear[0])
			jahr = titleNyear[1]
			position += 1
			original_name, imdbId = "", ""
			foundAsMovie, foundAsSeries = False, False
			# TMDBmovie dataserver
			if config.plugins.AdvancedEventLibrary.tmdbUsage.value & 1:
				tmdburl = b64decode(b"aHR0cDovL2ltYWdlLnRtZGIub3JnL3QvcC9vcmlnaW5hbA==l"[:-1]).decode()
				aelGlobals.setStatus(f"{position}/{len(titles)}: themoviedb movie - {title} ({posters}|{covers}|{entrys}|{blentrys})")
				write_log(f"looking for '{title}' on themoviedb movie")
				tmdb.API_KEY = get_keys("tmdb")
				search = tmdb.Search()
				response = callLibrary(search.movie, "", query=title, language=lang, year=jahr) if jahr else callLibrary(search.movie, "", query=title, language=lang)
				if response:
					reslist = []
					results = response.get("results", [])
					for item in results:
						reslist.append(item.get("title", "").lower())
					bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
					if not bestmatch:
						bestmatch = [title.lower()]
					for item in results:
						if item.get("title", "").lower() == bestmatch[0]:
							write_log(f"found '{bestmatch[0]}' for '{title.lower()}' on themoviedb movie")
							foundAsMovie = True
							# TODO: evtl. später einige ungenutzte wieder löschen
							# collect all available and useful data
							adult = item.get("adult", False)
							genre_ids = item.get("genre_ids", [])  #  e.g. [12, 10751, 9648]
							tmdbId = item.get("id", 0)
							original_title = item.get("original_title", "")  # e.g. 'Uzbuna na Zelenom Vrhu'
							release_date = item.get("release_date", "")[:4]
							title = item.get("title", "")
							vote_average = item.get("vote_average", 0)
							# prepare data for DB
							for genrecode in genre_ids:
								genre = aelGlobals.TMDB_GENRES.get(genrecode, "")
								if genre and genre not in titleinfo.get("genre", {}):
									titleinfo["genre"] = f"{titleinfo.get("genre", {})}{genre} "
							if loadImages:
								poster_path = item.get("poster_path", "")  # e.g. '/9pKuPigShOqh0MvkAKJEpP9iIXz.jpg'
								titleinfo["poster_url"] = f"{tmdburl}{poster_path}" if poster_path else ""
								backdrop_path = item.get("backdrop_path", "")  # e.g. '/pEuxDvQMBoiHbf1MsVQ8LWu0ERD.jpg'
								titleinfo["backdrop_url"] = f"{tmdburl}{backdrop_path}" if backdrop_path else ""
							titleinfo["year"] = release_date
							if vote_average:
								titleinfo["rating"] = vote_average
							if adult:
								titleinfo["fsk"] = "18"
							if tmdbId:
#								try:
								details = tmdb.Movies(tmdbId)
								for country in details.releases(language=lang)["countries"]:  # TODO: hier später die Boxsprache eintragen?
									if country.get("iso_3166_1", "") == lang.upper():
										titleinfo["fsk"] = country["certification"]
										break
								for country in details.info(language=lang)["production_countries"]:
									titleinfo["country"] = f"{titleinfo.get("country", {})}{country.get("iso_3166_1", "")} | "
								titleinfo["country"] = titleinfo.get("country", "")[:-3]
								imdbId = details.info(language=lang).get("imdbId", "")
#								except Exception as errmsg:
#									write_log(f"ERROR in module 'get_titleInfo': {errmsg}")
#									details = None
								if loadImages and details:
#									try:
									if not titleinfo.get("backdrop_url", ""):
										showimgs = details.images(language=lang)["backdrops"]
										if showimgs:
											titleinfo["backdrop_url"] = f"{tmdburl}{showimgs[0]["file_path"]}"
									if not titleinfo.get("poster_url", "").startswith("http"):
										showimgs = details.images(language=lang)["posters"]
										if showimgs:
											titleinfo["poster_url"] = f"{tmdburl}{showimgs[0]["file_path"]}"
#									except Exception as errmsg:
#										write_log(f"ERROR in module 'get_titleInfo': {errmsg}")
								original_name = original_title
							break
				if not foundAsMovie:
					# TMDBtv dataserver
					aelGlobals.setStatus(f"{position}/{len(titles)}: themoviedb tv - {title} ({posters}|{covers}|{entrys}|{blentrys})")
					write_log(f"looking for '{title}' on themoviedb tv")
					search = tmdb.Search()
					searchName = findEpisode(title)
					if searchName:
						response = callLibrary(search.tv, None, query=searchName[2], language=lang, year=jahr, include_adult=True, search_type="ngram")
					else:
						response = callLibrary(search.tv, None, query=title, language=lang, year=jahr)
					if response:
						reslist = []
						results = response.get("results", [])
						for item in results:
							reslist.append(item.get("name", "").lower())
						if searchName:
							bestmatch = get_close_matches(searchName[2].lower(), reslist, 1, 0.7)
							if not bestmatch:
								bestmatch = [searchName[2].lower()]
						else:
							bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
							if not bestmatch:
								bestmatch = [title.lower()]
						for item in results:
							if item.get("name", "").lower() == bestmatch[0]:
								foundAsSeries = True
								write_log(f"found '{bestmatch[0]}' for '{title.lower()}' on themoviedb tv")
								if searchName:
									details = tmdb.TV_Episodes(item.get("id", ""), searchName[0], searchName[1])
									if details:
										episode = details.info(language=lang)
										if not titleinfo.get("year", ""):
											titleinfo["year"] = episode.get("air_date", "")[:4]
										if not titleinfo.get("rating", ""):
											titleinfo["rating"] = episode.get("vote_average", 0)
										still_path = episode.get("still_path", "")
										if loadImages and not titleinfo.get("backdrop_url", ""):
											titleinfo["backdrop_url"] = f"{tmdburl}{still_path}" if still_path else ""
										for country in item.get("origin_country", []):  # e.g. ['HR', 'FR', 'DE']
											titleinfo["country"] = f"{titleinfo.get("country", {})}{country} | "
										titleinfo["country"] = titleinfo.get("country", "")[:-3]
										for genre in item.get("genre_ids", []):
											if aelGlobals.TMDB_GENRES[genre] not in titleinfo.get("genre", {}):
												titleinfo["genre"] = f"{titleinfo.get("genre", {})}{aelGlobals.TMDB_GENRES[genre]}-{_("series")}"
								else:
									# TODO: evtl. später einige ungenutzte wieder löschen
									# collect all available and useful data
									backdrop_path = item.get("backdrop_path", "")  # e.g. '/pEuxDvQMBoiHbf1MsVQ8LWu0ERD.jpg'
									genre_ids = item.get("genre_ids", [])  #  e.g. [12, 10751, 9648]
									tmdbId = item.get("id", 0)
									poster_path = item.get("poster_path", "")  # e.g. '/9pKuPigShOqh0MvkAKJEpP9iIXz.jpg'
									for genrecode in genre_ids:
										genre = aelGlobals.TMDB_GENRES.get(genrecode, "")
										if genre and genre not in titleinfo.get("genre", {}):
											titleinfo["genre"] = f"{titleinfo.get("genre", {})}{genre}-{_("series")}"
									if tmdbId:
										details = tmdb.TV(tmdbId)
										if loadImages and details:
#											try:
											for country in details.content_ratings(language=lang).get("results", []):
												if country.get("iso_3166_1", "") == lang.upper():
													titleinfo["fsk"] = country.get("rating", "")
													break
#											except Exception as errmsg:
#												write_log(f"ERROR in module 'get_titleInfo': {errmsg}")
#											try:
											if not titleinfo.get("poster_url", ""):
												showimgs = details.images(language=lang)["posters"]
												if showimgs:
													titleinfo["poster_url"] = f"{tmdburl}{showimgs[0]["file_path"]}"
											if not titleinfo.get("backdrop_url", ""):
												showimgs = details.images(language=lang)["backdrops"]
												if showimgs:
													titleinfo["backdrop_url"] = f"{tmdburl}{showimgs[0]["file_path"]}"
#											except Exception as errmsg:
#												write_log(f"ERROR in module 'get_titleInfo': {errmsg}")
									if not titleinfo.get("year", ""):
										titleinfo["year"] = item.get("first_air_date", "")[:4]
									if not titleinfo.get("rating", ""):
										titleinfo["rating"] = item.get("vote_average", 0)
									if not titleinfo.get("fsk", "") and item.get("adult", False):
										titleinfo["fsk"] = "18"
									for country in item.get("origin_country", []):  # e.g. ['HR', 'FR', 'DE']
										titleinfo["country"] = titleinfo.get("country", "") + country + " | "
									titleinfo["country"] = titleinfo.get("country", "")[:-3]
									original_name = item.get("original_name", "")  # e.g. 'Uzbuna na Zelenom Vrhu'
								break
			# TVDB dataserver
			if not foundAsMovie and not foundAsSeries and config.plugins.AdvancedEventLibrary.tvdbUsage.value & 1:
				aelGlobals.setStatus(f"{position}/{len(titles)}: thetvdb - {title} ({posters}|{covers}|{entrys}|{blentrys})")
				write_log(f"looking for '{title}' on thetvdb")
				tvdb.KEYS.API_KEY = get_keys("tvdb")
				search = tvdb.Search()
				searchTitle = convertTitle2(title)
				seriesId = 0
				poster, image, network = "", "", ""
				genres = []  # TODO: it seems to be that TVDB don't deliver a genre at all?
				response = callLibrary(search.series, searchTitle, language=lang)
				if response:
					reslist = []
					for result in response:
						reslist.append(result.get("seriesName", "").lower())
					bestmatch = get_close_matches(searchTitle.lower(), reslist, 1, 0.7)
					if not bestmatch:
						bestmatch = [searchTitle.lower()]
					for headitem in response:
						if headitem.get("seriesName", "").lower() == bestmatch[0]:
							write_log(f"found '{bestmatch[0]}' for '{title.lower()}' on thetvdb")
							# TODO: evtl. später einige ungenutzte wieder löschen
							# collect all available and useful data
							seriesId = headitem.get("id", "")
							image = headitem.get("image", "")  # e.g. '/banners/v4/series/424222/posters/65a85837132bf.jpg'
							network = headitem.get("network", "")  # e.g. 'National Geographic' or 'BBC One'
							poster = headitem.get("poster", "")  # e.g. '/banners/v4/series/424222/posters/65a85837132bf.jpg'
							genres = headitem.get("genre", [])  # TODO: it seems to be that TVDB don't deliver a genre at all?
							break
				if seriesId:
					foundEpisode = False
					show = tvdb.Series(seriesId)
					response = show.info()
					epis = tvdb.Series_Episodes(seriesId)
					try:  # mandatory because the library raises an error when no result
						episoden = epis.all()
					except Exception:
						episoden = []
					epilist = []
					tvdburl = b64decode(b"aHR0cHM6Ly93d3cudGhldHZkYi5jb20vYmFubmVycy8=J"[:-1]).decode()
					if episoden:
						for episode in episoden:
							episodeName = episode.get("episodeName")  # mandtory because 'episodeName' might be 'None'
							if episodeName:
								epilist.append(episodeName.lower())
						bestmatch = get_close_matches(title.lower(), epilist, 1, 0.7)
						for episode in episoden:
							episode = dict(filter(lambda item: item[1] is not None, episode.items()))  # remove all keys with value 'None'
							episodeName = episode.get("episodeName", "")
							if episodeName.lower() == bestmatch[0] if bestmatch else title.lower():
								foundEpisode = True
								imdbId = episode.get("imdbId", 0)
								if not titleinfo.get("title", ""):
									titleinfo["title"] = episodeName
								if response:
									for genre in response.get("genre", {}):
										titleinfo["genre"] = f"{titleinfo.get("genre", {})}{genre}-{_("series")} "
									titleinfo["genre"] = titleinfo.get("genre", "").replace("Documentary", "Dokumentation").replace("Children", "Kinder")
								if loadImages:
									if not titleinfo.get("poster_url", ""):
										poster = response.get("poster", "")
										titleinfo["poster_url"] = f"{tvdburl}{poster}" if poster else ""
									if not titleinfo.get("backdrop_url", ""):
										filename = episode.get("filename", "")
										titleinfo["backdrop_url"] = f"{tvdburl}{filename}" if filename else ""
								if not titleinfo.get("year", ""):
									titleinfo["year"] = episode.get("firstAired", "")[:4]
								if not titleinfo.get("rating", ""):
									titleinfo["rating"] = episode.get("siteRating", 0)
								if not titleinfo.get("fsk", ""):
									titleinfo["fsk"] = aelGlobals.FSKDICT.get(episode.get("contentRating", ""), "")
								if not titleinfo.get("country", {}):
									titleinfo["country"] = aelGlobals.NETWORKDICT.get(network, "")
								break
					if response and not foundEpisode:  # fallback and trying to piece together missing data
						if not titleinfo.get("title", ""):
							titleinfo["title"] = response.get("seriesName", "")
						if not titleinfo.get("genre", {}):
							for genre in response.get("genre", {}):
								titleinfo["genre"] = f"{titleinfo.get("genre", {})}{genre}-{_("series")}"
						if loadImages:
							if not titleinfo.get("poster_url", "") and not poster:
								poster = response.get("poster", "")
								titleinfo["poster_url"] = f"{tvdburl}{poster}" if poster else ""
							if not titleinfo.get("backdrop_url", ""):
								image = response.get("image", "")
								titleinfo["backdrop_url"] = f"{tvdburl}{image}" if image else ""
						if not titleinfo.get("year", ""):
							titleinfo["year"] = response.get("firstAired", "")[:4]
						if not titleinfo.get("rating", ""):
							titleinfo["rating"] = response.get("siteRating", "")
						if not titleinfo.get("fsk", ""):
							titleinfo["fsk"] = response.get("rating", "")
						if not titleinfo.get("country", {}):
							titleinfo["country"] = aelGlobals.NETWORKDICT.get(network, "")

			# TVMASZE dataserver
			if not foundAsMovie and config.plugins.AdvancedEventLibrary.tvmaszeUsage.value & 1:
				aelGlobals.setStatus(f"{position}/{len(titles)}: maze.tv - {title} ({posters}|{covers}|{entrys}|{blentrys})")
				write_log(f"looking for '{title}' on maze.tv")
				tvmazeurl = b64decode(b"aHR0cDovL2FwaS50dm1hemUuY29tL3NlYXJjaC9zaG93cw==5"[:-1]).decode()
				errmsg, response = getAPIdata(tvmazeurl, params={"q": f"{original_name or title}"})
#				print("#####TVMAZE_response:", response)
				if errmsg:
					write_log(f"API download error in module 'get_titleInfo: TVMAZE call': {errmsg}")
				if response:
					reslist = []
					for item in response:
						reslist.append(item.get("show", {}).get("name", "").lower())
					bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
					if not bestmatch:
						bestmatch = [title.lower()]
					for item in response:
						show = dict(filter(lambda item: item[1] is not None, item.get("show", {}).items()))  # remove all keys with value 'None'
						if titleinfo and show.get("name", "").lower() == bestmatch[0]:
							if not titleinfo.get("country", {}):
								titleinfo["country"] = show.get("network", {}).get("country", {}).get("code", "")
							if not titleinfo.get("year", ""):
								titleinfo["year"] = show.get("premiered", "")[:4]
							if not titleinfo.get("genre", {}):
								for genre in show.get("genres", []):
									if genre not in titleinfo.get("genre", {}):
										titleinfo["genre"] = f"{titleinfo.get("genre", {})}{genre}-{_("series")}"
								titleinfo["genre"] = titleinfo.get("genre", "").replace("Documentary", "Dokumentation").replace("Children", "Kinder")
							if loadImages:
								if not titleinfo.get("poster_url", ""):
									titleinfo["poster_url"] = show.get("image", {}).get("original", "")  # e.g. 'https://static.tvmaze.com/uploads/images/original_untouched/109/274423.jpg'
								if not titleinfo.get("rating", ""):
									titleinfo["rating"] = show.get("rating", {}).get("average", "")
							if imdbId:
								imdbId = show.get("externals", {}).get("imdb", "")
							break
			# OMDB dataserver
			if not foundAsMovie and not foundAsSeries and config.plugins.AdvancedEventLibrary.omdbUsage.value & 1:
				aelGlobals.setStatus(f"{position}/{len(titles)} : omdb - {title} ({posters}|{covers}|{entrys}|{blentrys})")
				write_log(f"looking for '{title}' on omdb")
				omdburl = b64decode(b"aHR0cDovL3d3dy5vbWRiYXBpLmNvbQ==b"[:-1]).decode()
				params = {"apikey": get_keys("omdb")}
				if imdbId:
					addparams = {"i": imdbId}
				else:
					addparams = {"s": original_name, "page": 1} if original_name else {"s": title, "page": 1}
					errmsg, response = getAPIdata(omdburl, params=params | addparams)
#					print("#####OMDB_res1:", response)
					if errmsg:
						write_log(f"API download error in module 'get_titleInfo OMDB call #1': {errmsg}")
					addparams = {"t": title, "page": 1}
					if response and response.get("Response", "False") == "True":
						reslist = []
						Search = response.get("Search", [])
						for result in Search:
							reslist.append(result["Title"].lower())
						bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
						if not bestmatch:
							bestmatch = [title.lower()]
						for result in Search:
							if result["Title"].lower() == bestmatch[0]:
								addparams = {"i": result["imdbID"]}
								break
				errmsg, response = getAPIdata(omdburl, params=params | addparams)
#				print("#####OMDB_res2:", response)
				if errmsg:
					write_log(f"API download error in module 'get_titleInfo: OMDB call #2': {errmsg}")
				if response and response.get("Response", "False") == "True":
					response = dict(filter(lambda item: item[1] != "N/A", response.items()))  # remove all keys with value 'N/A'
					if not titleinfo.get("year", ""):
						titleinfo["year"] = response.get("Year", "")[:4]
					if not titleinfo.get("genre", {}):
						stype = "-Serie" if response.get("Type", "") == "series" else " "
						genres = response.get("Genre", "").split(", ")
						for genre in genres:
							if genre not in titleinfo.get("genre", {}):
								titleinfo["genre"] = f"{titleinfo.get("genre", {})}{genre}{stype}".replace("Documentary", "Dokumentation").replace("Children", "Kinder")
					if loadImages and not titleinfo.get("poster_url", ""):
						titleinfo["poster_url"] = response.get("Poster", "")  # e.g. "https://m.media-amazon.com/images/M/MV5BZmEzMWYzN2QtMjNiNC00ODE2LWJkZmEtMDA0MjI1NjA4ZDc5XkEyXkFqcGc@._V1_SX300.jpg"
					if not titleinfo.get("rating", ""):
						titleinfo["rating"] = response.get("imdbRating", "")
					if response.get("Country", "") and not titleinfo.get("country", {}):
						countries = ""
						for country in response.get("Country", "").split(", "):
							countries = f"{countries}{country} | "
						titleinfo["country"] = countries[:-2].replace("West Germany", "DE").replace("East Germany", "DE").replace("Germany", "DE").replace("France", "FR").replace("Canada", "CA").replace("Austria", "AT").replace("Switzerland", "S").replace("Belgium", "B").replace("Spain", "ESP").replace("Poland", "PL").replace("Russia", "RU").replace("Czech Republic", "CZ").replace("Netherlands", "NL").replace("Italy", "IT")
#					imdb_ID = response.get("imdbID", "N/A")  # TODO: wofür wird das hier noch gebraucht?
#					if imdb_ID != "N/A" and not imdbId:
#						imdbId = imdb_ID
					titleinfo["fsk"] = aelGlobals.FSKDICT.get(response.get("Rated", ""), "")
			# Eintragung in Datenbank
			if db and title and title != " ":
				if not titleinfo.get("genre", {}) and not titleinfo.get("year", "") and not titleinfo.get("rating", "") and not titleinfo.get("fsk", "") and not titleinfo.get("country", {}) and not titleinfo.get("poster_url", "") and not titleinfo.get("backdrop_url", ""):
					blentrys += 1
					db.addblackList(title)
					write_log(f"no titles found for '{titleinfo.get("title", "")}'")
				if titleinfo.get("genre", {}) or titleinfo.get("year", "") or titleinfo.get("rating", "") or titleinfo.get("fsk", "") or titleinfo.get("country", {}):
					entrys += 1
					if research:
						if db.checkTitle(research):
							db.updateTitleInfo(titleinfo.get("title", ""), titleinfo.get("genre", {}), titleinfo.get("year", ""), titleinfo.get("rating", ""), titleinfo.get("fsk", ""), titleinfo.get("country", {}), research)
						else:
							db.addTitleInfo(title, titleinfo.get("title", ""), titleinfo.get("genre", {}), titleinfo.get("year", ""), titleinfo.get("rating", ""), titleinfo.get("fsk", ""), titleinfo.get("country", {}))
					else:
						db.addTitleInfo(title, titleinfo.get("title", ""), titleinfo.get("genre", {}), titleinfo.get("year", ""), titleinfo.get("rating", ""), titleinfo.get("fsk", ""), titleinfo.get("country", {}))
					write_log(f"found data for '{titleinfo.get("title", "")}'")
				if loadImages:
					if not titleinfo.get("poster_url", ""):
						year = titleinfo.get("year", "")
						titleinfo["poster_url"] = get_Picture(f"{title} ({year})", what="Poster", lang=lang) if year else get_Picture(title, what="Poster", lang=lang)
					if titleinfo.get("poster_url", ""):
						posters += 1
						filename = titleinfo.get("poster_url", "").split("/")[-1]
						print(f"#####download: {aelGlobals.POSTERPATH}{research if research else filename}")
						downloadImage(titleinfo.get("poster_url", ""), join(aelGlobals.POSTERPATH, f"{research if research else filename}"))
						if titleinfo.get("poster_url", ""):
							print(f"#####Imageopen: {aelGlobals.POSTERPATH}{filename}")
							img = Image.open(join(aelGlobals.POSTERPATH, filename))
							w, h = img.size
							if w > h:
								move(join(aelGlobals.POSTERPATH, filename), join(aelGlobals.COVERPATH, filename))
							img = None
					if not titleinfo.get("backdrop_url", ""):
						titleinfo["backdrop_url"] = get_Picture(f"{title} ({titleinfo.get("year", "")})", what="Cover", lang=lang) if titleinfo.get("year", "") else get_Picture(title, what="Cover", lang=lang)
					if titleinfo.get("backdrop_url", ""):
						covers += 1
						filename = titleinfo.get("backdrop_url", "").split("/")[-1]
						downloadImage(titleinfo.get("backdrop_url", ""), join(aelGlobals.COVERPATH, research if research else filename))
			write_log(titleinfo)
	write_log(f"set {entrys} on eventInfo")
	write_log(f"set {blentrys} on Blacklist")
	if db:
		db.parameter(aelGlobals.PARAMETER_SET, "lasteventInfoCount", str(int(entrys + blentrys)))
		db.parameter(aelGlobals.PARAMETER_SET, "lasteventInfoCountSuccsess", str(entrys))
	aelGlobals.setStatus(_("remove old extra data..."))
	if config.plugins.AdvancedEventLibrary.DelPreviewImages.value:
		cleanPreviewImages(db)
	if db:
		db.cleanliveTV(int(time() - 28800))
	if db and len(liveTVRecords) > 0:
		write_log(f"try to insert {len(liveTVRecords)} events into database")
		db.addliveTV(liveTVRecords)
		db.parameter(aelGlobals.PARAMETER_SET, "lastadditionalDataCount", str(db.getUpdateCount()))
		# TVSpielfilm dataserver
		if config.plugins.AdvancedEventLibrary.tvsUsage.value & 1:
			getTVSpielfilm(db)
		# TVmovie dataserver
		if config.plugins.AdvancedEventLibrary.tvmovieUsage.value & 1:
			getTVMovie(db)
		db.updateliveTVProgress()
	if loadImages:
		write_log("looking for missing pictures")
		get_MissingPictures(db, posters, covers)
	write_log("create thumbnails for cover")
	createThumbnails(aelGlobals.COVERPATH)
	write_log("create thumbnails for preview images")
	createThumbnails(aelGlobals.PREVIEWPATH)
	write_log("create thumbnails for poster")
	createThumbnails(aelGlobals.POSTERPATH)
	write_log("reduce large image-size")
	reduceImageSize(aelGlobals.COVERPATH, db)
	reduceImageSize(aelGlobals.PREVIEWPATH, db)
	reduceImageSize(aelGlobals.POSTERPATH, db)
	if config.plugins.AdvancedEventLibrary.CreateMetaData.value:
		write_log("looking for missing meta-Info")
		createMovieInfo(db)
	createStatistics(db)
	if config.plugins.AdvancedEventLibrary.UpdateAELMovieWall.value:
		write_log("create MovieWall data")
		try:
			itype = None
			filename = f"{aelGlobals.PLUGINPATH}imageType.data"
			if fileExists(filename):
				with open(filename, "r") as f:
					itype = f.read()
					f.close()
			if itype:
				from Plugins.Extensions.AdvancedEventLibrary.AdvancedEventLibrarySimpleMovieWall import saveList
				saveList(itype)
				write_log(f"MovieWall data saved with {itype}")
		except Exception as errmsg:
			write_log(f"ERROR in module 'get_titleInfo' - save moviewall data: {errmsg}")
	if config.plugins.AdvancedEventLibrary.Log.value:
		writeTVStatistic(db)
	if db:
		db.parameter(aelGlobals.PARAMETER_SET, "laststop", str(time()))
	write_log("### ...update done ###")
	aelGlobals.setStatus()
	clearMem("search: connected")


def getTVSpielfilm(db):
	evt, founded, imgcount, trailers = 0, 0, 0, 0
	refs = db.getSrefsforUpdate()
	tcount = db.getUpdateCount()
#	print("#####TVS ref:", refs)
	if refs:
		fulltext = {"U": _("Entertainment"), "SE": _("Series"), "SPO": _("Sport"), "SP": _("Movie"), "KIN": _("Children"), "RE": _("Reportage"), "AND": _("Other")}
		for sref in refs:
			if sref in aelGlobals.TVS_REFDICT:
				evt += 1
				maxDate = db.getMaxAirtimeforUpdate(sref)
				curDate = db.getMinAirtimeforUpdate(sref)
				while (int(curDate) - 86400) <= int(maxDate) + 86400:  # while int(curDate) <= int(maxDate) + 86400:
					curDatefmt = datetime.fromtimestamp(curDate).strftime("%Y-%m-%d")
					aelGlobals.setStatus(f"({evt}/{len(refs)}) {_("search")} {aelGlobals.TVS_REFDICT[sref][1]} {_("for the")} {curDatefmt} {_("on TV-Spielfilm")} ({founded}/{tcount} | {imgcount})")
					tvsurl = b64decode(b"aHR0cHM6Ly9saXZlLnR2c3BpZWxmaWxtLmRlL3N0YXRpYy9icm9hZGNhc3QvbGlzdC8=7"[:-1]).decode()
					errmsg, response = getAPIdata(f"{tvsurl}{aelGlobals.TVS_REFDICT[sref][0].upper()}/{curDatefmt}")
					if errmsg:
						write_log(f"API download error in module 'getTVSpielfilm': {errmsg}")
					if response:
						lastImage = ""
						for event in response:
							airtime = event.get("timestart", 0)
							eid = event.get("id", "")
							title = event.get("title", "")
							subtitle = event.get("episodeTitle", "")
							image = event.get("images", [{}])[0].get("size4")
							year = event.get("year", "")
							fsk = event.get("fsk", "")
							leadText = event.get("preview", "")
							conclusion = event.get("conclusion", "")
							categoryName = fulltext.get(event.get("sart_id", ""), "")
							season = event.get("seasonNumber", 0)
							episode = event.get("episodeNumber", "")
							episode = episode.split("/")[0] if "/" in episode else episode
							genre = event.get("genre", "")
							country = event.get("country", "").replace("/", " | ")
							ratingPoints, ratingAmount = 0, 0
							for ratingkey in ["ratingAction", "ratingDemanding", "ratingErotic", "ratingHumor", "ratingSuspense"]:
								currrating = event.get(ratingkey, 0)
								ratingPoints += int(currrating * 3.33)
								ratingAmount += 1
							rating = str(round(float(ratingPoints / ratingAmount), 1)) if ratingAmount else 0
							video = event.get("videos", [{}])[0].get("video", [{}])[0].get("url", [{}])
							if video and db.checkTitle(convert2base64(title)):
								db.updateTrailer(video, convert2base64(title))
							imdb = event.get("imdbId", "")  # imdb is no more supported by TVS
							if not db.checkTitle(convert2base64(title)) and categoryName == "Spielfilm":
								db.addTitleInfo(convert2base64(title), title, genre, year, rating, fsk, country, imdb)
							if db.checkTitle(convert2base64(title)):
								data = db.getTitleInfo(convert2base64(title))
								for item in [("genre", genre), ("year", year), ("rating", rating), ("fsk", fsk), ("country", country)]:
									if item[1] and not data[2]:
										db.updateSingleEventInfo(item[0], item[1], convert2base64(title[0]))
							if image and config.plugins.AdvancedEventLibrary.SearchFor.value != 1 and config.plugins.AdvancedEventLibrary.UsePreviewImages.value:
								bld = image
								imgname = f"{title} - "
								if season:
									imgname += f"S{season.zfill(2)}"
								if episode:
									imgname += f"E{episode.zfill(2)} - "
								if subtitle:
									imgname += f"{subtitle} - "
								image = imgname[:-3]
							else:
								bld = ""
							success = founded
							db.updateliveTVS(eid, subtitle, image, year, fsk, rating, leadText, conclusion, categoryName, season, episode, genre, country, imdb, sref, airtime, title)
							founded = tcount - db.getUpdateCount()
							if founded == success:
								write_log(f"no matches found for '{title}' on '{aelGlobals.TVS_REFDICT[sref][1]}' at '{datetime.fromtimestamp(airtime).strftime("%d.%m.%Y %H:%M:%S")}' with TV-Spielfilm")
							if founded > success and imdb:
								trailers += 1
							if founded > success and bld and config.plugins.AdvancedEventLibrary.SearchFor.value != 1 and config.plugins.AdvancedEventLibrary.UsePreviewImages.value and image != lastImage:
								if len(image) < 255:
									if downloadTVSImage(bld, join(aelGlobals.COVERPATH, image)):
										imgcount += 1
										lastImage = image
					curDate += 86400
	write_log(f"have updated {founded} events from TV-Spielfilm")
	write_log(f"have downloaded {imgcount} images from TV-Spielfilm")
	write_log(f"have found {trailers} trailers on TV-Spielfilm")
	db.parameter(aelGlobals.PARAMETER_SET, f"lastpreviewImageCount {imgcount}")


def getTVMovie(db, secondRun=False):
	evt = 0
	founded = 0
	imgcount = 0
	failedNames = []
	tcount = db.getUpdateCount()
	if not secondRun:
		tvnames = db.getTitlesforUpdate()
		write_log(f"check {len(tvnames)} titles on TV-Movie")
	else:
		tvnames = db.getTitlesforUpdate2()
		for name in failedNames:
			tvnames.append(name)
		write_log(f"recheck {len(tvnames)} titles on TV-Movie")
	for title in tvnames:
		evt += 1
		tvname = title[0] if not secondRun else convertTitle2(title[0])
		aelGlobals.setStatus(f"({evt}/{len(tvnames)}) {_('search on TV-Movie for')} {tvname} ({founded}/{tcount} | {imgcount})")
		tvmovieurl = b64decode(b"aHR0cDovL2NhcGkudHZtb3ZpZS5kZS92MS9icm9hZGNhc3RzL3NlYXJjaA==2"[:-1]).decode()
		errmsg, response = getAPIdata(tvmovieurl, params={"q": tvname, "page": 1, "rows": 400})
		if errmsg:
			write_log(f"API download error in module 'getTVMovie' {errmsg}")
		if response:
			reslist = set()
			for event in response.get("results", []):
				reslist.add(event.get("title", "").lower())
				if "originalTitle" in event:
					reslist.add(event.get("originalTitle", "").lower())
			bestmatch = get_close_matches(tvname.lower(), reslist, 2, 0.7)
			if not bestmatch:
				bestmatch = [tvname.lower()]
			nothingfound = True
			lastImage = ""
			for event in response.get("results", []):
				original_title = "abc123def456"
				if "originalTitle" in event:
					original_title = event.get("originalTitle", "").lower()
				if event.get("title", "").lower() in bestmatch or original_title in bestmatch:
					airtime = 0
					if "airTime" in event:
						airtime = int(mktime(datetime.strptime(str(event.get("airTime", "1900-01-01 00:00:00")), "%Y-%m-%d %H:%M:%S").timetuple()))
					if airtime <= db.getMaxAirtime(title[0]):
						nothingfound = False
						tid = event.get("id", "")
						image = event.get("previewImage", {}).get("id", "")
						genre = event.get("genreName", "")
						categoryName = event.get("categoryName", "")
						year = event.get("productionYear", "")
						country = event.get("countryOfProduction", "")
						ageRating = event.get("ageRating", "")
						fsk = {"OhneAlter": "0", "KeineJugend": "18", "Unbekannt": ""}.get(ageRating, "")
						fsk = ageRating if not fsk else fsk
						season = event.get("season", "")
						episode = event.get("episode", "")
						subtitle = event.get("subTitle", "").replace("None", "")
						leadText = event.get("leadText", "")
						conclusion = event.get("conclusion", "")
						rating = str(round(event.get("movieStarValue", 0) * 2))
						imdb = event.get("imdbId", "")  # imdb is no more supported by TVS
						if not db.checkTitle(convert2base64(title[0])) and categoryName == "Spielfilm":
							db.addTitleInfo(convert2base64(title[0]), title[0], genre, year, rating, fsk, country, imdb)
						if db.checkTitle(convert2base64(title[0])):
							data = db.getTitleInfo(convert2base64(title[0]))
							for item in [("genre", genre), ("year", year), ("rating", rating), ("fsk", fsk), ("country", country)]:
								if item[1] and not data[2]:
									db.updateSingleEventInfo(item[0], item[1], convert2base64(title[0]))
						if image and config.plugins.AdvancedEventLibrary.SearchFor.value != 1 and config.plugins.AdvancedEventLibrary.UsePreviewImages.value:
							bld = image
							imgname = f"{title[0]} - "
							if season:
								imgname += f"S{season.zfill(2)}"
							if episode:
								imgname += f"E{episode.zfill(2)} - "
							if subtitle:
								imgname += f"{subtitle} - "
							image = imgname[:-3]
						else:
							bld = ""
						success = founded
						db.updateliveTV(tid, subtitle, image, year, fsk, rating, leadText, conclusion, categoryName, season, episode, genre, country, imdb, title[0], airtime)
						founded = tcount - db.getUpdateCount()
						if founded > success and bld and config.plugins.AdvancedEventLibrary.SearchFor.value != 1 and config.plugins.AdvancedEventLibrary.UsePreviewImages.value and image != lastImage:
							if len(image) < 255:
								if downloadTVMovieImage(bld, join(aelGlobals.COVERPATH, image)):
									imgcount += 1
									lastImage = image
			if nothingfound:
				write_log(f"nothing found on TV-Movie for '{title[0]}'")
	write_log(f"have updated {founded} events from TV-Movie")
	write_log(f"have downloaded {imgcount} images from TV-Movie")
	if not secondRun:
		tvsImages = db.parameter(aelGlobals.PARAMETER_GET, "lastpreviewImageCount", None, 0)
		imgcount += int(tvsImages)
		db.parameter(aelGlobals.PARAMETER_SET, "lastpreviewImageCount", str(imgcount))
		getTVMovie(db, True)
	del tvnames
	del failedNames


def convertTitle(name):
	if name.find(" (") > 0:
		regexfinder = compile(r"\([12][90]\d{2}\)", IGNORECASE)
		ex = regexfinder.findall(name)
		if not ex:
			name = name[:name.find(" (")].strip()
	if name.find(" - S0") > 0:
		name = name[:name.find(" - S0")].strip()
	if name.find(" S0") > 0:
		name = name[:name.find(" S0")].strip()
	if name.find("Folge") > 0:
		name = name[:name.find("Folge")].strip()
	if name.find("Episode") > 0:
		name = name[:name.find("Episode")].strip()
	name = name.strip(" -+&#:_")
	return name


def convertTitle2(name):
	if name.find(" (") > 0:
		regexfinder = compile(r"\([12][90]\d{2}\)", IGNORECASE)
		ex = regexfinder.findall(name)
		if not ex:
			name = name[:name.find(" (")].strip()
	if name.find(":") > 0:
		name = name[:name.find(":")].strip()
	if name.find(" - S0") > 0:
		name = name[:name.find(" - S0")].strip()
	if name.find(" S0") > 0:
		name = name[:name.find(" S0")].strip()
	if name.find(" -") > 0:
		name = name[:name.find(" -")].strip()
	if name.find("Folge") > 0:
		name = name[:name.find("Folge")].strip()
	if name.find("Episode") > 0:
		name = name[:name.find("Episode")].strip()
	if name.find("!") > 0:
		name = name[:name.find("!") + 1].strip()
	name = name.strip(" -+&#:_")
	return name


def findEpisode(title):
	#======= geaendert (#10) ==================
	#regexfinder = re.compile("[Ss]\d{2}[Ee]\d{2}", re.MULTILINE|re.DOTALL)
	# regexfinder = re.compile("[Ss]\d{1,4}[Ee]\d{1,4}", re.MULTILINE|re.DOTALL)
	# ===========================================
	regexfinder = compile(r"[Ss]\d{1,4}[Ee]\d{1,4}", MULTILINE | DOTALL)
	ex = regexfinder.findall(title)
	if ex:
		removedEpisode = title
		if removedEpisode.find(str(ex[0])) > 0:
				removedEpisode = removedEpisode[:removedEpisode.find(str(ex[0]))]
		removedEpisode = convertTitle2(removedEpisode)
		#======= geandert (#3) ===============
		#SE = ex[0].replace("S","").replace("s","").split("E")
		SE = ex[0].lower().replace("s", "").split("e")
		# =======================================
		return (SE[0], SE[1], removedEpisode.strip())


def convertSearchName(eventName):
	eventName = removeExtension(eventName)
#	try:
	text = eventName.replace("\x86", "").replace("\x87", "")
#	except Exception:
#		text = eventName.replace(b"\x86", b"").replace(b"\x87", b"")
	return text


def convertDateInFileName(fileName):
	regexfinder = compile(r"\d{8} - ", IGNORECASE)
	ex = regexfinder.findall(fileName)
	return fileName.replace(ex[0], "") if ex else fileName


def convertYearInTitle(title):
	regexfinder = compile(r"\([12][90]\d{2}\)", IGNORECASE)
	ex = regexfinder.findall(title)
	return [title.replace(ex[0], "").strip(), ex[0].replace("(", "").replace(")", "")] if ex else [title, ""]


def downloadImage(url, filename, timeout=5):
#	try:
	if 1 == 1:
		if not fileExists(filename):
			response = get(url, stream=True, timeout=timeout)
			if response.status_code == 200:
				with open(filename, "wb") as file:
					file.write(response.content)
			else:
				write_log(f"Incorrect status code during download for '{filename}' on '{url}'")
		else:
			write_log(f"Picture {filename.split('/')[-1]} already exists.")
#	except Exception as errmsg:
#		write_log(f"Exception in module 'downloadImage': {errmsg}")


def downloadImage2(url, filename, timeout=5):
#	try:
	if 1 == 1:
		if not fileExists(filename):
			response = get(url, stream=True, timeout=timeout)
			if response.status_code != 200:
				with open(filename, "wb") as file:
					file.write(response.content)
				return True
			else:
				write_log(f"Incorrect status code during download for '{filename}' on '{url}'")
				return False
		else:
			return True
#	except Exception as errmsg:
#		write_log(f"Exception in module 'downloadImage2': {errmsg}")
#		return False


def checkAllImages():
	removeList = []
	dirs = [f"{aelGlobals.COVERPATH}", f"{aelGlobals.COVERPATH}thumbnails/", f"{aelGlobals.POSTERPATH}", f"{aelGlobals.POSTERPATH}thumbnails/"]
	for aelGlobals.HDDPATH in dirs:
		filelist = glob(f"{aelGlobals.HDDPATH}*.*")
		c = 0
		ln = len(filelist)
		for f in filelist:
			c += 1
			aelGlobals.setStatus(f"{c}/{ln} {_('verify')} {f}")
			img = Image.open(f)
			if img.format != "JPEG":
				write_log(f"invalid image : {f} {img.format}")
				removeList.append(f)
			img = None
		del filelist
	if removeList:
		for f in removeList:
			write_log(f"remove image : {f}")
			remove(f)
		del removeList
	aelGlobals.setStatus()
	clearMem("checkAllImages")


def reduceImageSize(path, db):
	imgsize = aelGlobals.COVERQUALITYDICT[config.plugins.AdvancedEventLibrary.coverQuality.value] if "cover" in str(path) else aelGlobals.POSTERQUALITYDICT[config.plugins.AdvancedEventLibrary.posterQuality.value]
	sizex, sizey = imgsize.split("x", 1)
	maxSize = config.plugins.AdvancedEventLibrary.MaxImageSize.value
	for file in glob(join(path, "*.*")):
		filename = ""
		try:
			q = 90
			if not db.getimageBlackList(file):
				oldSize = int(getsize(file) / 1024.0)
				if oldSize > maxSize:
					try:
						filename = b64decode((file.split("/")[-1]).rsplit(".", 1)[0]).decode()
					except Exception:
						filename = (file.split("/")[-1]).rsplit(".", 1)[0]
					try:
						img = Image.open(file)
					except Exception as errmsg:
						write_log(f"Exception in module 'reduceImageSize': {errmsg}")
						continue
					w, h = int(img.size[0]), int(img.size[1])
					aelGlobals.setStatus(f"{_('edit')} {filename} {_('with')} {bytes2human(getsize(file), 1)} {_('and')} {w})x{h}px")
					img_bytes = StringIO()
					img1 = img.convert("RGB", colors=256)
					img1.save(str(img_bytes), format="jpeg")
					if img_bytes.tell() / 1024 >= oldSize:
						if w > int(sizex):
							w, h = int(sizex), int(sizey)
							img1 = img.resize((w, h), Image.LANCZOS)
							img1.save(str(img_bytes), format="jpeg")
					else:
						if w > int(sizex):
							w, h = int(sizex), int(sizey)
							img1 = img1.resize((w, h), Image.LANCZOS)
							img1.save(str(img_bytes), format="jpeg")
					if img_bytes.tell() / 1024 > maxSize:
						while img_bytes.tell() / 1024 > maxSize:
							img1.save(str(img_bytes), format="jpeg", quality=q)
							q -= 8
							if q <= config.plugins.AdvancedEventLibrary.MaxCompression.value:
								break
					img1.save(file, format="jpeg", quality=q)
					write_log(f"file {filename} reduced from {bytes2human(int(oldSize * 1024), 1)} to {bytes2human(getsize(file), 1)} and {w}x{h}px")
					if getsize(file) / 1024.0 > maxSize:
						write_log("Image size cannot be further reduced with the current settings!")
						db.addimageBlackList(file)
		except Exception as errmsg:
			write_log(f"Error in module 'reduceImageSize': {filename} - {errmsg}")
			continue


def reduceSigleImageSize(src, dest):
	imgsize = aelGlobals.COVERQUALITYDICT[config.plugins.AdvancedEventLibrary.coverQuality.value] if "cover" in dest else aelGlobals.POSTERQUALITYDICT[config.plugins.AdvancedEventLibrary.posterQuality.value]
	sizex, sizey = imgsize.split("x", 1)
	maxSize = config.plugins.AdvancedEventLibrary.MaxImageSize.value
	q = 90
	oldSize = int(getsize(src) / 1024.0)
	if oldSize > maxSize:
		try:
			filename = b64decode((src.split("/")[-1]).rsplit(".", 1)[0]).decode()
		except Exception:
			filename = (src.split("/")[-1]).rsplit(".", 1)[0]
		try:
			img = Image.open(src)
			w, h = int(img.size[0]), int(img.size[1])
			write_log(f"convert image {filename} with {bytes2human(getsize(src), 1)} and {w}x{h}px")
			img_bytes = StringIO()
			img1 = img.convert("RGB", colors=256)
			img1.save(str(img_bytes), format="jpeg")
			if img_bytes.tell() / 1024 >= oldSize:
				if w > int(sizex):
					w, h = int(sizex), int(sizey)
					img1 = img.resize((w, h), Image.LANCZOS)
					img1.save(str(img_bytes), format="jpeg")
			else:
				if w > int(sizex):
					w, h = int(sizex), int(sizey)
					img1 = img1.resize((w, h), Image.LANCZOS)
					img1.save(str(img_bytes), format="jpeg")
			if img_bytes.tell() / 1024 > maxSize:
				while img_bytes.tell() / 1024 > maxSize:
					img1.save(str(img_bytes), format="jpeg", quality=q)
					q -= 8
					if q <= config.plugins.AdvancedEventLibrary.MaxCompression.value:
						break
			img1.save(dest, format="jpeg", quality=q)
			write_log(f"file {filename} reduced from {bytes2human(int(oldSize * 1024), 1)} to {bytes2human(getsize(dest), 1)} and {w}x{h}px")
			if getsize(dest) / 1024.0 > maxSize:
				write_log("Image size cannot be further reduced with the current settings!")
		except Exception as errmsg:
			write_log(f"Error in module 'reduceSingleImageSize': {filename} - {errmsg}")


def createThumbnails(path):
	wp, hp = parameters.get("EventLibraryThumbnailPosterSize", (60, 100))
	wc, hc = parameters.get("EventLibraryThumbnailCoverSize", (100, 60))
	for filename in glob(join(path, "*.*")):
		if filename:
			destfile = filename .replace("cover", "cover/thumbnails").replace("poster", "poster/thumbnails").replace("preview", "preview/thumbnails")
			if not fileExists(destfile):
				try:
					aelGlobals.setStatus(f"{_('create thumbnail for')} {filename}")
					img = Image.open(filename)
					imgnew = img.convert("RGBA", colors=256)
					imgnew = img.resize((wc, hc), Image.LANCZOS) if "cover" in filename or "preview" in filename else img.resize((wp, hp), Image.LANCZOS)
					imgnew.save(destfile)
				except Exception as errmsg:
					write_log(f"Error in module 'createThumbnails': {filename} - {errmsg}")
					remove(filename)
					continue


def createSingleThumbnail(src, dest):
	wp, hp = parameters.get("EventLibraryThumbnailPosterSize", (60, 100))
	wc, hc = parameters.get("EventLibraryThumbnailCoverSize", (100, 60))
	destfile = dest.replace("cover", "cover/thumbnails").replace("poster", "poster/thumbnails")
	write_log(f"create single thumbnail from source {src} to {destfile} with {wc}x{hc}px")
	img = Image.open(src)
#	imgnew = img.convert("RGBA", colors=256)
	imgnew = img.resize((wc, hc), Image.LANCZOS) if "cover" in dest or "preview" in dest else img.resize((wp, hp), Image.LANCZOS)
	imgnew.save(destfile)
	if fileExists(destfile):
		write_log("thumbnail created")
	img = None


def get_Picture(title, what="Cover", lang="de"):
	cq = str(config.plugins.AdvancedEventLibrary.coverQuality.value) if config.plugins.AdvancedEventLibrary.coverQuality.value != "w1920" else "original"
	posterquality = config.plugins.AdvancedEventLibrary.posterQuality.value
	tmdb.API_KEY = get_keys("tmdb")
	picture = None
	titleNyear = convertYearInTitle(title)
	title = convertSearchName(titleNyear[0])
	jahr = str(titleNyear[1])
	# TMDB image server
	if config.plugins.AdvancedEventLibrary.tmdbUsage.value & 2:
		tmdb.API_KEY = get_keys("tmdb")
		search = tmdb.Search()
		searchName = findEpisode(title)
		if searchName:
			response = callLibrary(search.tv, None, query=searchName[2], language=lang, year=jahr, include_adult=True, search_type="ngram")
		else:
			response = callLibrary(search.tv, None, query=title, language=lang, year=jahr)
		tmdburl = b64decode(b"aHR0cDovL2ltYWdlLnRtZGIub3JnL3QvcC8=x"[:-1]).decode()
		if response and response.get("results", []):
			reslist = []
			for item in response.get("results", []):
				reslist.append(item.get("name", "").lower())
			if searchName:
				bestmatch = get_close_matches(searchName[2].lower(), reslist, 1, 0.7)
				if not bestmatch:
					bestmatch = [searchName[2].lower()]
			else:
				bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
				if not bestmatch:
					bestmatch = [title.lower()]
			for item in response.get("results", []):
				if item.get("name", "").lower() in bestmatch:
					idx = tmdb.TV(item.get("id", ""))
					if searchName and what == "Cover":
						details = tmdb.TV_Episodes(item.get("id", ""), searchName[0], searchName[1])
						if details:
							episode = details.info(language=lang)
							if episode:
								imgs = details.images(language=lang)
								if imgs:
									picture = f"{tmdburl}{cq}{imgs.get("stills", [{}])[0].get("file_path", "")}"
					if what == "Cover" and not searchName:
						imgs = idx.images(language=lang)["backdrops"]
						if imgs:
							picture = f"{tmdburl}{cq}{imgs[0].get("file_path", "")}"
						if picture is None:
							imgs = idx.images()["backdrops"]
							if imgs:
								picture = f"{tmdburl}{cq}{imgs[0].get("file_path", "")}"
					if what == "Poster":
						imgs = idx.images(language=lang)["posters"]
						if imgs:
							picture = f"{tmdburl}{posterquality}{imgs[0].get("file_path", "")}"
						if picture is None:
							imgs = idx.images()["posters"]
							if imgs:
								picture = f"{tmdburl}{posterquality}{imgs[0].get("file_path", "")}"
		if picture is None:
			search = tmdb.Search()
			response = callLibrary(search.movie, None, query=title, language=lang, year=jahr)
			if response and response.get("results", []):
				reslist = []
				for item in response.get("results", []):
					reslist.append(item.get("title", "").lower())
				bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
				if not bestmatch:
					bestmatch = [title.lower()]
				for item in response.get("results", []):
					if item.get("title", "").lower() in bestmatch:
						idx = tmdb.Movies(item.get("id", ""))
						if what == "Cover":
							imgs = idx.images(language=lang)["backdrops"]
							if imgs:
								picture = f"{tmdburl}{cq}{imgs[0].get("file_path", "")}"
							if picture is None:
								imgs = idx.images()["backdrops"]
								if imgs:
									picture = f"{tmdburl}{cq}{imgs[0].get("file_path", "")}"
						if what == "Poster":
							imgs = idx.images(language=lang)["posters"]
							if imgs:
								picture = f"{tmdburl}{posterquality}{imgs[0].get("file_path", "")}"
							if picture is None:
								imgs = idx.images()["posters"]
								if imgs:
									picture = f"{tmdburl}{posterquality}{imgs[0].get("file_path", "")}"
	# TVDB image server
	if not picture and config.plugins.AdvancedEventLibrary.tvdbUsage.value & 2:
		tvdb.KEYS.API_KEY = get_keys("tvdb")
		search = tvdb.Search()
		searchTitle = convertTitle2(title)
		seriesid = None
		response = callLibrary(search.series, searchTitle, language=lang)
		if response:
			reslist = []
			for result in response:
				reslist.append(result.get("seriesName", "").lower())
			bestmatch = get_close_matches(searchTitle.lower(), reslist, 1, 0.7)
			if not bestmatch:
				bestmatch = [searchTitle.lower()]
			for result in response:
				if bestmatch[0] in result.get("seriesName", "").lower() or result.get("seriesName", "").lower() in bestmatch[0]:
					seriesid = result.get("id", "")
					break
		if seriesid:
			epis = tvdb.Series_Episodes(seriesid)
			try:  # mandatory because the library raises an error when no result
				episoden = epis.all()
			except Exception:
				episoden = []
			epilist = []
			if episoden:
				for episode in episoden:
					episodeName = episode.get("episodeName", "")
					if episodeName:
						epilist.append(episodeName.lower())
				bestmatch = get_close_matches(title.lower(), epilist, 1, 0.7)
				if not bestmatch:
					bestmatch = [title.lower()]
				for episode in episoden:
					episodeName = episode.get("episodeName", "")
					if episodeName and episodeName.lower() in bestmatch[0]:
						seriesid = episode.get("seriesId", "")
						break
			showimgs = tvdb.Series_Images(seriesid)
			if showimgs:
				tvdburl = b64decode(b"aHR0cHM6Ly93d3cudGhldHZkYi5jb20vYmFubmVycy8=J"[:-1]).decode()
				if what == "Cover":
					response = callLibrary(showimgs.fanart, None, language=lang)
					if response and len(response) > 0 and response != "None":
						picture = f"{tvdburl}{response[0].get("fileName", "")}"
				if what == "Poster":
					response = callLibrary(showimgs.poster, None, language=lang)
					if response and len(response) > 0 and response != "None":
						picture = f"{tvdburl}{response[0].get("fileName")}"
	if picture:
		write_log(f"researching picture result '{picture}' for '{title}'")
	return picture


def get_MissingPictures(db, poster, cover):
	pList = db.getMissingPictures()
	covers, posters = 0, 0
	if pList[0]:
		for picture in pList[0]:
			if db.getblackListCover(convert2base64(picture)):
				pList[0].remove(picture)
	if pList[1]:
		for picture in pList[1]:
			if db.getblackListPoster(convert2base64(picture)):
				pList[1].remove(picture)
	if pList[0]:
		write_log(f"found {len(pList[0])} missing covers")
		for idx, picture in enumerate(pList[0]):
			aelGlobals.setStatus(f"{_('looking for missing cover for')} {picture} ({idx}/{len(pList[0])} | {covers}) ")
			picurl = get_Picture(title=picture, what="Cover", lang="de")  # TODO: hier die Boxsprache einsetzen
			if picurl:
				covers += 1
				downloadImage(picurl, join(aelGlobals.COVERPATH, picture))
			else:
				db.addblackListCover(convert2base64(picture))
		write_log(f"have downloaded {covers} missing covers")
	if pList[1]:
		write_log(f"found {len(pList[1])} missing posters")
		for idx, picture in enumerate(pList[1]):
			aelGlobals.setStatus(f"{_('looking for missing poster for')} {picture} ({idx}/{len(pList[1])} | {posters}) ")
			picurl = get_Picture(title=picture, what="Poster", lang="de")  # TODO: hier die Boxsprache einsetzen
			if picurl:
				posters += 1
				downloadImage(picurl, join(aelGlobals.POSTERPATH, picture))
			else:
				db.addblackListPoster(convert2base64(picture))
		write_log(f"have downloaded {posters} missing posters")
	posters += poster
	covers += cover
	write_log(f"found {posters} posters")
	write_log(f"found {covers} covers")
	db.parameter(aelGlobals.PARAMETER_SET, "lastposterCount", posters)
	db.parameter(aelGlobals.PARAMETER_SET, "lastcoverCount", covers)


def writeTVStatistic(db):
	root = eServiceReference(f'{service_types_tv} FROM BOUQUET "bouquets.tv" ORDER BY bouquet')
	serviceHandler = eServiceCenter.getInstance()
	tvbouquets = serviceHandler.list(root).getContent("SN", True)
	for bouquet in tvbouquets:
		root = eServiceReference(str(bouquet[0]))
		serviceHandler = eServiceCenter.getInstance()
		ret = serviceHandler.list(root).getContent("SN", True)
		isInsPDict = bouquet[1] in aelGlobals.SPDICT
		if not isInsPDict or (isInsPDict and aelGlobals.SPDICT[bouquet[1]]):
			for (serviceref, servicename) in ret:
				#==== hinzugefuegt (#8) =====
				if not serviceref:
					continue
				serviceref = serviceref.split("?", 1)[0].decode("utf-8", "ignore")
				# =========================
				count = db.getEventCount(serviceref)
				write_log(f"There are {count} events for '{servicename}' in database'")


def get_size(path):
	total_size = 0
	for dirpath, dirnames, filenames in walk(path):
		for f in filenames:
			fp = join(dirpath, f)
			total_size += getsize(fp)
	return str(round(float(total_size / 1024.0 / 1024.0), 1)) + "M"


def createStatistics(db):
	DIR = f"{aelGlobals.POSTERPATH}"
	posterCount = len([name for name in listdir(DIR) if fileExists(join(DIR, name))])
	posterSize = check_output(["du", "-sh", DIR]).decode().split()[0]
	DIR = f"{aelGlobals.COVERPATH}"
	coverCount = len([name for name in listdir(DIR) if fileExists(join(DIR, name))])
	coverSize = check_output(["du", "-sh", DIR]).decode().split()[0]
	DIR = f"{aelGlobals.PREVIEWPATH}"
	previewCount = len([name for name in listdir(DIR) if fileExists(join(DIR, name))])
	previewSize = check_output(["du", "-sh", DIR]).decode().split()[0]
	inodes = check_output(["df", "-i", aelGlobals.HDDPATH]).decode().split()
	nodestr = f"{inodes[-4]} | {inodes[-5]} | {inodes[-2]}"
	db.parameter(aelGlobals.PARAMETER_SET, "posterCount", str(posterCount))
	db.parameter(aelGlobals.PARAMETER_SET, "coverCount", str(coverCount))
	db.parameter(aelGlobals.PARAMETER_SET, "previewCount", str(previewCount))
	db.parameter(aelGlobals.PARAMETER_SET, "posterSize", str(posterSize))
	db.parameter(aelGlobals.PARAMETER_SET, "coverSize", str(coverSize))
	db.parameter(aelGlobals.PARAMETER_SET, "previewSize", str(previewSize))
	db.parameter(aelGlobals.PARAMETER_SET, "usedInodes", str(nodestr))


def get_PictureList(title, what="Cover", count=20, b64title=None, lang="de", bingOption=""):
	cq = str(config.plugins.AdvancedEventLibrary.coverQuality.value) if config.plugins.AdvancedEventLibrary.coverQuality.value != "w1920" else "original"
	posterquality = config.plugins.AdvancedEventLibrary.posterQuality.value
	pictureList = []
	titleNyear = convertYearInTitle(title)
	title = convertSearchName(titleNyear[0])
	jahr = str(titleNyear[1])
	write_log(f"searching '{what}' for '{title}' with language = '{lang}'")
	if not b64title:
		b64title = convert2base64(title)
	# TVDB image server
	if config.plugins.AdvancedEventLibrary.tvdbUsage.value & 2:
		tvdb.KEYS.API_KEY = get_keys("tvdb")
		seriesid = None
		search = tvdb.Search()
		searchTitle = convertTitle2(title)
		result = {}
		response = callLibrary(search.series, searchTitle, language=lang)
		if response:
			reslist = []
			for result in response:
				reslist.append(result.get("seriesName", "").lower())
			bestmatch = get_close_matches(searchTitle.lower(), reslist, 1, 0.7)
			if not bestmatch:
				bestmatch = [searchTitle.lower()]
			for result in response:
				if bestmatch[0] in result.get("seriesName", "").lower() or result.get("seriesName", "").lower() in bestmatch[0]:
					seriesid = result.get("id", "")
					break
		if seriesid:
			epis = tvdb.Series_Episodes(seriesid)
			try:  # mandatory because the library raises an error when no result
				episoden = epis.all()
			except Exception:
				episoden = []
			epilist = []
			epiname = ""
			if episoden:
				for episode in episoden:
					epilist.append(episode.get("episodeName", "").lower())
				bestmatch = get_close_matches(title.lower(), epilist, 1, 0.7)
				if not bestmatch:
					bestmatch = [title.lower()]
				for episode in episoden:
					episodenName = episode.get("episodeName", "")
					if episodenName.lower() in bestmatch[0]:
						seriesid = episode.get("seriesId", "")
						epiname = f" - {episodenName}"
						break
			showimgs = tvdb.Series_Images(seriesid)
			if showimgs:
				tvdburl = b64decode(b"aHR0cHM6Ly93d3cudGhldHZkYi5jb20vYmFubmVycy8=J"[:-1]).decode()
				if what == "Cover":
					response = callLibrary(showimgs.fanart, None, language=lang)
					if response and str(response) != "None":
						for img in response:
							filename = img.get("fileName", "")
							itm = [f"{result.get("seriesName", "")}{epiname}", what, f"{img.get("resolution", "")} gefunden auf TVDb", f"{tvdburl}{filename}", join(aelGlobals.COVERPATH, b64title), filename]
							pictureList.append((itm,))
				if what == "Poster":
					response = callLibrary(showimgs.poster, None, language=lang)
					if response and str(response) != "None":
						for img in response:
							filename = img.get("fileName", "")
							itm = [f"{result.get("seriesName", "")}{epiname}", what, f"{img.get("resolution", "")} gefunden auf TVDb", f"{tvdburl}{filename}", join(aelGlobals.POSTERPATH, b64title), filename]
							pictureList.append((itm,))
	# TMDB image server
	if config.plugins.AdvancedEventLibrary.tvdbUsage.value & 2:
		tmdb.API_KEY = get_keys("tmdb")
		tmdburl = b64decode(b"aHR0cDovL2ltYWdlLnRtZGIub3JnL3QvcC9vcmlnaW5hbA==l"[:-1]).decode()
		search = tmdb.Search()
		searchName = findEpisode(title)
		if searchName:
			response = callLibrary(search.tv, None, query=searchName[2], language=lang, year=jahr, include_adult=True, search_type="ngram")
		else:
			response = callLibrary(search.tv, None, query=title, language=lang, year=jahr)
		if response and response.get("results", []):
			reslist = []
			for item in response.get("results", []):
				reslist.append(item.get("name", "").lower())
			if searchName:
				bestmatch = get_close_matches(searchName[2].lower(), reslist, 4, 0.7)
				if not bestmatch:
					bestmatch = [searchName[2].lower()]
			else:
				bestmatch = get_close_matches(title.lower(), reslist, 4, 0.7)
				if not bestmatch:
					bestmatch = [title.lower()]
			#========== geaendert (#7) ===============
			#for item in response.get("results", []):
			#	write_log('found on TMDb TV ' + str(item.get("name", "")))
			#	if item.get("name", "").lower() in bestmatch:
			appendTopHit = True
			itemList = []
			for index, item in enumerate(response.get("results", [])):
				if item.get("name", "").lower() in bestmatch:
					itemList.append(item)
					if index == 0:
						appendTopHit = False
			if appendTopHit:
				itemList.append(response.get("results", [])[0])
			for item in itemList:
				if item:
					write_log(f"found on TMDb TV {item.get("name", "")}")
			# ==================================================
			# for item in response.get("results", []):
			# write_log('found on TMDb TV ' + str(item.get("name", "")))
			# if item.get("name", "").lower() in bestmatch and 'id' in item:
					idx = tmdb.TV(item.get("id", ""))
					if searchName and what == "Cover":
						details = tmdb.TV_Episodes(item.get("id", ""), searchName[0], searchName[1])
						if details:
							episode = details.info(language=lang)
							if episode:
								imgs = details.images(language=lang)
								if imgs:
									for img in imgs.get("stills", [{}]):
											imgsize = f"{img["width"]}x{img["height"]}"
											file_path = img.get("file_path", "")
											itm = [f"{item.get("name", "")} - {episode.get("name", "").lower()}", what, f"{imgsize} {_("found on TMDb TV")}", f"{tmdburl}{cq}{file_path}", join(aelGlobals.COVERPATH, b64title), file_path]
											pictureList.append((itm,))
								#======== hinzugeugt (#6) =========
								still_path = episode.get("still_path", "")
								if still_path:
									tmdburl = b64decode(b"aHR0cDovL2ltYWdlLnRtZGIub3JnL3QvcC9vcmlnaW5hbA==l"[:-1]).decode()
									itm = [f"{item.get("name", "")} - {episode.get("name", "").lower()}", what, _("found on TMDb TV"), f"{tmdburl}{cq}{still_path}", join(aelGlobals.COVERPATH, b64title), still_path]
									pictureList.append((itm,))
								# ================================
					#==== geaendert (#6) =====
					#if what == "Cover" and not searchName:
					if what == "Cover":
					# ========================
						imgs = idx.images(language=lang)["backdrops"]
						if imgs:
							for img in imgs:
								imgsize = f"{img["width"]}x{img["height"]}"
								file_path = img.get("file_path", "")
								itm = [item.get("name", ""), what, f"{imgsize} {_("found on TMDb TV")}", f"{tmdburl}{cq}{file_path}", join(aelGlobals.COVERPATH, b64title), file_path]
								pictureList.append((itm,))
						if len(imgs) < 2:
							imgs = idx.images()["backdrops"]
							if imgs:
								for img in imgs:
									imgsize = f"{img["width"]}x{img["height"]}"
									file_path = img.get("file_path", "")
									itm = [item.get("name", ""), what, f"{imgsize} {_("found on TMDb TV")}", f"{tmdburl}{cq}{file_path}", join(aelGlobals.COVERPATH, b64title), file_path]
									pictureList.append((itm,))
					if what == "Poster":
						imgs = idx.images(language=lang)["posters"]
						if imgs:
							for img in imgs:
								imgsize = f"{img["width"]}x{img["height"]}"
								file_path = img.get("file_path", "")
								itm = [item.get("name", ""), what, f"{imgsize} {_("found on TMDb TV")}", f"{tmdburl}{posterquality}{file_path}", join(aelGlobals.POSTERPATH, b64title), file_path]
								pictureList.append((itm,))
						if len(imgs) < 2:
							imgs = idx.images()["posters"]
							if imgs:
								for img in imgs:
									imgsize = f"{img["width"]}x{img["height"]}"
									file_path = img.get("file_path", "")
									itm = [item.get("name", ""), what, f"{imgsize} {_("found on TMDb TV")}", f"{tmdburl}{posterquality}{file_path}", join(aelGlobals.POSTERPATH, b64title), file_path]
									pictureList.append((itm,))
		search = tmdb.Search()
		response = search.movie(query=title, language=lang, year=jahr) if jahr != "" else search.movie(query=title, language=lang)
		if response and response.get("results", []):
			reslist = []
			for item in response.get("results", []):
				reslist.append(item.get("title", "").lower())
			bestmatch = get_close_matches(title.lower(), reslist, 4, 0.7)
			if not bestmatch:
				bestmatch = [title.lower()]
			#========== geaendert (#7) ===============
			#for item in response.get("results", []):
			#	write_log("found on TMDb Movie " + str(item.get("title", "")))
			#	if item.get("title", "").lower() in bestmatch:
			appendTopHit = True
			itemList = []
			for index, item in enumerate(response.get("results", [])):
				if item.get("title", "").lower() in bestmatch:
					itemList.append(item)
					if index == 0:
						appendTopHit = False
			if appendTopHit:
				itemList.append(response.get("results", [])[0])
			for item in itemList:
				write_log(f"found on TMDb Movie {item.get("title", "")}")
			# ==================================================
			# for item in response.get("results", []):
			# write_log("found on TMDb Movie " + str(item.get("title", "")))
			# if item.get("title", "").lower() in bestmatch and "id" in item:
				idx = tmdb.Movies(item.get("id", ""))
				if what == "Cover":
					imgs = idx.images(language=lang)["backdrops"]
					if imgs:
						for img in imgs:
							imgsize = f"{img["width"]}x{img["height"]}"
							file_path = img.get("file_path", "")
							itm = [item.get("title", ""), what, f"{imgsize} {_("found on TMDb Movie")}", f"{tmdburl}{cq}{file_path}", join(aelGlobals.COVERPATH, b64title), file_path]
							pictureList.append((itm,))
					if len(imgs) < 2:
						imgs = idx.images()["backdrops"]
						if imgs:
							for img in imgs:
								imgsize = f"{img["width"]}x{img["height"]}"
								file_path = img.get("file_path", "")
								itm = [item.get("title", ""), what, f"{imgsize} {_("found on TMDb Movie")}", f"{tmdburl}{cq}{file_path}", join(aelGlobals.COVERPATH, b64title), file_path]
								pictureList.append((itm,))
				if what == "Poster":
					imgs = idx.images(language=lang)["posters"]
					if imgs:
						for img in imgs:
							imgsize = f"{img["width"]}x{img["height"]}"
							file_path = img.get("file_path", "")
							itm = [item.get("title", ""), what, f"{imgsize} {_("found on TMDb Movie")}", f"{tmdburl}{posterquality}{file_path}", join(aelGlobals.POSTERPATH, b64title), file_path]
							pictureList.append((itm,))
					if len(imgs) < 2:
						imgs = idx.images()["posters"]
						if imgs:
							for img in imgs:
								imgsize = f"{img["width"]}x{img["height"]}"
								file_path = img.get("file_path", "")
								itm = [item.get("title", ""), what, f"{imgsize} {_("found on TMDb Movie")}", f"{tmdburl}{posterquality}{file_path}", join(aelGlobals.POSTERPATH, b64title), file_path]
								pictureList.append((itm,))
	if not pictureList and what == "Poster":
		# OMDB image server
		if config.plugins.AdvancedEventLibrary.omdbUsage.value & 2:
			omdburl = b64decode(b"aHR0cDovL3d3dy5vbWRiYXBpLmNvbQ==J"[:-1]).decode()
			errmsg, response = getAPIdata(omdburl, params={"apikey": get_keys("omdb"), "t": title})
			if errmsg:
				write_log(f"API download error in module 'get_PictureList: OMDB call': {errmsg}")
			Poster = response.get("Poster", "")
			if response.get("Response", "False") == "True" and Poster:
				itm = [response.get("Title", ""), what, "OMDB", Poster, join(aelGlobals.POSTERPATH, b64title), "omdbPosterFile"]
				pictureList.append((itm,))
		# TVMAZE image server
		if config.plugins.AdvancedEventLibrary.tvmaszeUsage.value & 2:
			tvmazeurl = b64decode(b"aHR0cDovL2FwaS50dm1hemUuY29tL3NlYXJjaC9zaG93cw==5"[:-1]).decode()
			errmsg, response = getAPIdata(tvmazeurl, params={"q": title})
			if errmsg:
				write_log(f"API download error in module 'get_PictureList: TVMAZE call': {errmsg}")
			if response:
				reslist = []
				for item in response:
					if item.get("show", "") and item.get("show", {}).get("name", ""):
						reslist.append(item.get("show", {}).get("name", "").lower().lower())
				bestmatch = get_close_matches(title.lower(), reslist, 4, 0.7)
				if not bestmatch:
					bestmatch = [title.lower()]
				for item in response:
					if item.get("show", "") and item.get("show", {}).get("name", "") and item.get("show", {}).get("name", "").lower().lower() == bestmatch[0]:
						if item.get("show", {}).get("image", {}) and item.get("show", {}).get("image", {}).get("original", ""):
							itm = [item.get("show", {}).get("name", "").lower(), what, "maze.tv", item.get("show", {}).get("image", {}).get("original"), join(aelGlobals.POSTERPATH, b64title), "mazetvPosterFile"]
							pictureList.append((itm,))
	# BING image server
	if not pictureList and config.plugins.AdvancedEventLibrary.bingUsage.value & 2:
		BingSearch = BingImageSearch(f"{title}{bingOption}", count, what)
		response = BingSearch.search()
		for idx, image in enumerate(response):
			imgpath, name = (aelGlobals.POSTERPATH, "bingPoster_") if what == "Poster" else (aelGlobals.COVERPATH, "bingCover_")
			itm = [title, what, _("found on bing.com"), image, join(imgpath, b64title), f"{f'{name}{idx}'}"]
			pictureList.append((itm,))
	if pictureList:
		idx = 0
		write_log(f"found {len(pictureList)} images for '{title}'")
		failed = []
		while idx <= int(count) and idx < len(pictureList):
			write_log(f"Image: {pictureList[idx]}")
			if not downloadImage2(pictureList[idx][0][3], join("/tmp/", pictureList[idx][0][5])):
				failed.insert(0, idx)
			idx += 1
		for erroridx in failed:
			del pictureList[erroridx]
		return pictureList[:count]
	else:
		itm = [_("No results found"), f"_('Picture name'): '{b64title}'", None, None, None, None]
		pictureList.append((itm,))
		return pictureList


def get_searchResults(title, lang="de"):
	resultList = []
	titleNyear = convertYearInTitle(title)
	title = convertSearchName(titleNyear[0])
	jahr = str(titleNyear[1])
	write_log(f"searching results for '{title}' with language = '{lang}'")
	searchName = findEpisode(title)
	# TMDB data server
	if config.plugins.AdvancedEventLibrary.tmdbUsage.value & 1:
		tmdb.API_KEY = get_keys("tmdb")
		search = tmdb.Search()
		if searchName:
			response = callLibrary(search.tv, None, query=searchName[2], language=lang, year=jahr, include_adult=True, search_type="ngram")
		else:
			response = callLibrary(search.tv, None, query=title, language=lang, year=jahr)
		if response and response.get("results", []):
			reslist = []
			for item in response.get("results", []):
				reslist.append(item.get("name", "").lower())
			if searchName:
				bestmatch = get_close_matches(searchName[2].lower(), reslist, 10, 0.4)
				if not bestmatch:
					bestmatch = [searchName[2].lower()]
			else:
				bestmatch = get_close_matches(title.lower(), reslist, 10, 0.4)
				if not bestmatch:
					bestmatch = [title.lower()]
			for item in response.get("results", []):
				if item.get("name", "").lower() in bestmatch:
					countries, year, genres, rating, fsk, desc, epiname = "", "", "", "", "", "", ""
					if searchName:
						details = tmdb.TV_Episodes(item.get("id", ""), searchName[0], searchName[1])
						if details:
							episode = details.info(language=lang)
							epiname = f" - S{searchName[0]}E{searchName[1]} - {episode.get("name", "")}"
							year = episode.get("air_date", "")[:4]
							rating = episode.get("vote_average", "")
							desc = episode.get("overview", "")
							for country in item.get("origin_country", []):
								countries = f"{countries}{country} | "
							countries = countries[:-3]
							for genre in item.get("origin_country", []):
								genres = f"{genres}{aelGlobals.TMDB_GENRES[genre]}-{_("series")}"
							maxGenres = genres.split()
							if maxGenres:
								genres = maxGenres[0]
							details = tmdb.TV(item.get("id", ""))
							try:
								for country in details.content_ratings(language=lang).get("results", []):
									if str(country.get("iso_3166_1", "")) == lang.upper():
										fsk = str(country.get("rating", ""))
										break
							except Exception:
								pass
					else:
						desc = item.get("overview", "")
						for country in item.get("origin_country", []):
							countries = f"{countries}{country} | "
						countries = countries[:-3]
						year = item.get("first_air_date", "")[:4]
						for genre in item.get("origin_country", []):
							genres = f"{genres}{aelGlobals.TMDB_GENRES[genre]}-{_("series")}"
						vote_average = item.get("vote_average", "")
						if vote_average != "0":
							rating = vote_average
						details = tmdb.TV(item.get("id", ""))
						#===== hinzugefuegt try (#9) ========
						try:
							for country in details.content_ratings(language=lang).get("results", []):
								if str(country.get("iso_3166_1", "")) == lang.upper():
									fsk = str(country.get("rating", ""))
									break
						except Exception:
							pass
						# ====================================
					itm = [f"item.get('name', ''){epiname}", countries, year, genres, rating, fsk, "TMDb TV", desc]
					resultList.append((itm,))
			search = tmdb.Search()
		response = search.movie(query=title, language=lang, year=jahr) if jahr != "" else search.movie(query=title, language=lang)
		if response and response.get("results", []):
			reslist = []
			for item in response.get("results", []):
				reslist.append(item.get("title", "").lower())
			bestmatch = get_close_matches(title.lower(), reslist, 10, 0.4)
			if not bestmatch:
				bestmatch = [title.lower()]
			for item in response.get("results", []):
				if item.get("title", "").lower() in bestmatch:
					countries, year, genres, rating, fsk, desc = "", "", "", "", "", ""
					desc = item.get("overview", "")
					year = item.get("release_date", "")[:4]
					for genre in item.get("genre_ids", []):
						genres = f"{genres}{aelGlobals.TMDB_GENRES[genre]} "
					vote_average = item.get("vote_average", "")
					if vote_average != "0":
						rating = vote_average
					details = tmdb.Movies(item.get("id"), "")
					#===== hinzugefuegt try (#9) ========
					try:
						for country in details.releases(language=lang)["countries"]:
							if str(country.get("iso_3166_1", "")) == lang.upper():
								fsk = country["certification"]
								break
						for country in details.info(language=lang)["production_countries"]:
							countries = countries + country.get("iso_3166_1", "") + " | "
						countries = countries[:-3]
					except Exception:
						pass
					# ===================================*=
					itm = [str(item.get("title", "")), str(countries), str(year), str(genres), str(rating), str(fsk), "TMDb Movie", desc]
					resultList.append((itm,))
	# TVDB data server
	if config.plugins.AdvancedEventLibrary.tmdbUsage.value & 1:
		tvdb.KEYS.API_KEY = get_keys("tvdb")
		search = tvdb.Search()
		searchTitle = convertTitle2(title)
		searchName = findEpisode(title)
		response = callLibrary(search.series, searchTitle, language=lang)
		if response:
			reslist = []
			for result in response:
				reslist.append(result.get("seriesName", "").lower())
			bestmatch = get_close_matches(title.lower(), reslist, 10, 0.4)
			if not bestmatch:
				bestmatch = [title.lower()]
			for result in response:
				if result.get("seriesName", "").lower() in bestmatch:
					foundEpisode = False
					seriesid = None
					countries, year, genres, rating, fsk, desc, epiname = "", "", "", "", "", "", ""
					seriesid = result.get("id", "")
					if seriesid:
						foundEpisode = False
						show = tvdb.Series(seriesid)
						response = show.info()
						epis = tvdb.Series_Episodes(seriesid)
						try:  # mandatory because the library raises an error when no result
							episoden = epis.all()
						except Exception:
							episoden = []
						epilist = []
						if episoden:
							for episode in episoden:
								epilist.append(episode.get("episodeName", "").lower())
							bestmatch = get_close_matches(title.lower(), epilist, 1, 0.6)
							if not bestmatch:
								bestmatch = [title.lower()]
							for episode in episoden:
								if episode.get("episodeName", "").lower() == bestmatch[0]:
									episodenName = episode.get("episodeName", "")
									foundEpisode = True
									epiname = f" - S{searchName[0]}E{searchName[1]} - {episodenName}" if searchName else f" - {episodenName}"
									desc = episode.get("overview", "")
									year = episode.get("firstAired", "")[:4]
									siteRating = episode.get("siteRating", "")
									if siteRating != "0" and siteRating != "None":
										rating = siteRating
									fsk = aelGlobals.FSKDICT.get(episode.get("contentRating", ""), "")
									if response:
										for genre in response.get("genre", {}):
											genres = f"{genres}{genre}-{_("series")}"
										genres = genres.replace("Documentary", "Dokumentation").replace("Children", "Kinder")
										network = response.get("network", "")
										countries = aelGlobals.NETWORKDICT.get(network, "")
									seriesName = result.get("seriesName", "")
									itm = [f"{seriesName}{epiname}", countries, year, genres, rating, fsk, "The TVDB", desc]
									resultList.append((itm,))
									break
							if response and not foundEpisode:
								desc = response.get("overview", "")
							seriesName = result.get("seriesName", "")
							network = response.get("network", "")
							countries = aelGlobals.NETWORKDICT.get(network, "")
							year = response.get("firstAired", "")[:4]
							for genre in response.get("genre", {}):
								genres = f"{genres}{genre}-{_("series")}"
							genres = genres.replace("Documentary", "Dokumentation").replace("Children", "Kinder")
							rating = aelGlobals.FSKDICT.get(response.get("rating", ""), "")
							itm = [seriesName, countries, year, genres, rating, fsk, "The TVDB", desc]
							resultList.append((itm,))
	# TVMAZE data server
	if config.plugins.AdvancedEventLibrary.tvmaszeUsage.value & 1:
		tvmazeurl = b64decode(b"aHR0cDovL2FwaS50dm1hemUuY29tL3NlYXJjaC9zaG93cw==5"[:-1]).decode()
		errmsg, response = getAPIdata(tvmazeurl, params={"q": title})
		if errmsg:
			write_log(f"API download error in module 'get_searchResults: TVMAZE call #1': {errmsg}")
		if response:
			reslist = []
			for item in response:
				if item.get("show", "") and item.get("show", {}).get("name", ""):
					reslist.append(item.get("show", {}).get("name", "").lower())
			bestmatch = get_close_matches(title.lower(), reslist, 10, 0.4)
			if not bestmatch:
				bestmatch = [title.lower()]
			for item in response:
				if item.get("show", "") and item.get("show", {}).get("name", "") and item.get("show", {}).get("name", "").lower().lower() in bestmatch:
					countries, year, genres, rating, fsk, desc = "", "", "", "", "", ""
					if item.get("show", {}).get("summary", ""):
						desc = item.get("show", {}).get("summary", "")
					if item.get("show", {}).get("network", "") and item.get("show", {}).get("network", {}).get("country", "") and item.get("show", {}).get("network", {}).get("country", {}).get("code", ""):
						countries = item.get("show", {}).get("network", {}).get("country", {}).get("code", "")
					if item.get("show", {}).get("premiered", ""):
						year = item.get("show", {}).get("premiered", "")[:4]
					for genre in item.get("show", {}).get("genres", []):
						genres = f"{genres}{genre}-{_("series")}"
					genres = genres.replace("Documentary", "Dokumentation").replace("Children", "Kinder")
					rating = item.get("show", {}).get("rating", {}).get("average", "")
					itm = [str(item.get("show", {}).get("name", "").lower()), countries, year, genres, rating, fsk, "maze.tv", desc]
					resultList.append((itm,))
	# OMDB data server
	if config.plugins.AdvancedEventLibrary.omdbUsage.value & 1:
		omdburl = b64decode(b"aHR0cHM6Ly9saXZlLnR2c3BpZWxmaWxtLmRlL3N0YXRpYy9icm9hZGNhc3QvbGlzdA=='7"[:-1]).decode()
		omdbapi = get_keys("omdb")
		errmsg, response = getAPIdata(omdburl, params={"apikey": omdbapi, "s": title, "page": 1})
		if errmsg:
			write_log(f"API download error in module 'get_searchResults: TVMAZE call #2': {errmsg}")
		if response and response.get("Response", False):
			reslist = []
			for result in response.get("Search", []):
				reslist.append(result.get("Title", "").lower())
			bestmatch = get_close_matches(title.lower(), reslist, 10, 0.4)
			if not bestmatch:
				bestmatch = [title.lower()]
			for result in response.get("Search", []):
				if result.get("Title", "").lower() in bestmatch:
					errmsg, response = getAPIdata(omdburl, params={"apikey": omdbapi, "i": result.get("imdbID", "")})
					if errmsg:
						write_log(f"API download error in module 'get_searchResults: TVMAZE call #3': {errmsg}")
					if response:
						countries, year, genres, rating, fsk = "", "", "", "", ""
						desc = ""
						if response.get("Response", "False") == "True":
							desc = response.get("Plot", "")
							year = response.get("Year", "")[:4]
							if response.get("Genre", "N/A") != "N/A":
								types = " "
								if response.get("Type", "") == "series":
									types = "-{_('series')}"
								resgenres = response.get("Genre", "").split(", ")
								for genre in resgenres:
									genres = f"{genres}{genre}{types}"
								genres = genres.replace("Documentary", "Dokumentation").replace("Children", "Kinder")
							imdbRating = response.get("imdbRating", "N/A")
							if imdbRating != "N/A":
								rating = imdbRating
							Country = response.get("Country", "N/A")
							if Country != "N/A":
								rescountries = Country.split(", ")
								for country in rescountries:
									countries = f"{countries}{country} | "
								countries = countries[:-2].replace("West Germany", "DE").replace("East Germany", "DE").replace("Germany", "DE").replace("France", "FR").replace("Canada", "CA").replace("Austria", "AT").replace("Switzerland", "S").replace("Belgium", "B").replace("Spain", "ESP").replace("Poland", "PL").replace("Russia", "RU").replace("Czech Republic", "CZ").replace("Netherlands", "NL").replace("Italy", "IT")
							fsk = aelGlobals.FSKDICT.get(response.get("Rated", ""), "")
							itm = [response.get("Title", ""), countries, str(year), genres, str(rating), fsk, "omdb", desc]
							resultList.append((itm,))
	write_log(f"search results : {resultList}")
	if resultList:
		return (sorted(resultList, key=lambda x: x[0]))
	else:
		itm = [_("No results found"), None, None, None, None, None, None, None]
		resultList.append((itm,))
		return resultList


def downloadTVSImage(imgurl, imgname):
	if not fileExists(imgname):
		ir = get(imgurl, stream=True, timeout=4)
		if ir.status_code != 200:
			return False
		try:  # TODO: weg damit nachdem Dateinamen von b64encode auf HASH umgestellt wurden
			with open(imgname, "wb") as file:
				file.write(ir.raw)
		except Exception as errmsg:
			write_log(f"EXCEPTION in module 'downloadTVSImage: {errmsg}")
			return False
	return True


def downloadTVMovieImage(tvMovieImage, imgname):
	if not fileExists(imgname):
		tvmovieurl = b64decode(b"aHR0cDovL2ltYWdlcy50dm1vdmllLmRlR"[:-1]).decode()
		imgurl = f"{tvmovieurl}/{aelGlobals.COVERQUALITYDICT[config.plugins.AdvancedEventLibrary.coverQuality.value]}/Center/{tvMovieImage}"
		ir = get(imgurl, stream=True, timeout=4)
		if ir.status_code != 200:
			return False
		try:  # TODO: weg damit nachdem Dateinamen von b64encode auf HASH umgestellt wurden
			with open(imgname, "wb") as file:
				file.write(ir.raw)
		except Exception as errmsg:
			write_log(f"EXCEPTION in module 'downloadTVSImage: {errmsg}")
			return False
	return True


def getImageFile(path, eventName):
	pictureName = eventName
	imageFileName = join(path, pictureName)
	if (exists(imageFileName)):
		return imageFileName
	else:
		pictureName = convertTitle(eventName)
		imageFileName = join(path, pictureName)
		if (exists(imageFileName)):
			return imageFileName
		else:
			pictureName = convertTitle2(eventName)
			imageFileName = join(path, pictureName)
			if (exists(imageFileName)):
				return imageFileName
	if "cover" in path and config.plugins.AdvancedEventLibrary.UsePreviewImages.value:
		ppath = path.replace("cover", "preview")
		imageFileName = getPreviewImageFile(ppath, eventName)
		if imageFileName:
			return imageFileName


def getPreviewImageFile(path, eventName):
	imageFileName = join(path, eventName)
	if exists(imageFileName):
		return imageFileName
	else:
		imageFileName = join(path, convertTitle(eventName))
		if exists(imageFileName):
			return imageFileName
		else:
			imageFileName = join(path, convertTitle2(eventName))
			if exists(imageFileName):
				return imageFileName


class AELGlobals:
	CURRENTVERSION = 141
	AGENTS = [
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
			"Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
			"Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)",
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edge/87.0.664.75",
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363"
			]
	FSKDICT = {"R": "18", "TV-MA": "18", "TV-PG": "16", "TV-14": "12", "TV-Y7": "6", "PG-13": "12", "PG": "6", "G": "16"}
	SPDICT = {}
	if config.plugins.AdvancedEventLibrary.searchPlaces.value != "":
		SPDICT = eval(config.plugins.AdvancedEventLibrary.searchPlaces.value)
	PARAMETER_SET = 0
	PARAMETER_GET = 1
	SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
	COVERQUALITYDICT = {"w300": "300x169", "w780": "780x439", "w1280": "1280x720", "w1920": "1920x1080"}
	POSTERQUALITYDICT = {"w185": "185x280", "w342": "342x513", "w500": "500x750", "w780": "780x1170"}
	TMDB_GENRES = {10759: "Action-Abenteuer", 16: "Animation", 10762: "Kinder", 10763: "News", 10764: "Reality", 10765: "Sci-Fi-Fantasy", 10766: "Soap", 10767: "Talk", 10768: "War & Politics", 28: "Action", 12: "Abenteuer", 35: "Comedy", 80: "Crime", 99: "Dokumentation", 18: "Drama", 10751: "Familie", 14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Science-Fiction", 10770: "TV-Movie", 53: "Thriller", 10752: "War", 37: "Western"}
	EXCLUDENAMES = ["RTL UHD", "--", "Sendeschluss", "Dokumentation", "EaZzzy", "MediaShop", "Dauerwerbesendung", "Impressum"]
	APIKEYS = {"tmdb": ["ZTQ3YzNmYzJkYzRlMWMwN2UxNGE4OTc1YjI5MTE1NWI=", "MDA2ZTU5NGYzMzFiZDc1Nzk5NGQwOTRmM2E0ZmMyYWM=", "NTRkMzg1ZjBlYjczZDE0NWZhMjNkNTgyNGNiYWExYzM="],
		   	"tvdb": ["NTRLVFNFNzFZWUlYM1Q3WA==", "MzRkM2ZjOGZkNzQ0ODA5YjZjYzgwOTMyNjI3ZmE4MTM=", "Zjc0NWRiMDIxZDY3MDQ4OGU2MTFmNjY2NDZhMWY4MDQ="],
			"omdb": ["ZmQwYjkyMTY=", "YmY5MTFiZmM=", "OWZkNzFjMzI="]}  # ["fd0b9216", "bf911bfc", "9fd71c32"]
	DESKTOPSIZE = getDesktop(0).size()
	TEMPPATH = "/var/volatile/tmp"
	# TODO: später wieder auf TEMPPATH setzen
	# LOGFILE = join(TEMPPATH, "AdvancedEventLibrary.log")
	LOGPATH = "/home/root/logs/"
	LOGFILE = join(LOGPATH, "ael_debug.log")
	SKINPATH = resolveFilename(SCOPE_CURRENT_SKIN)  # /usr/share/enigma2/MetrixHD/
	SHAREPATH = resolveFilename(SCOPE_SKIN_IMAGE)  # /usr/share/enigma2/
	CONFIGPATH = resolveFilename(SCOPE_CONFIG, "AEL/")  # /etc/enigma2/AEL/
	PYTHONPATH = eEnv.resolve("${libdir}/enigma2/python/")  # /usr/lib/enigma2/python/
	PLUGINPATH = resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/AdvancedEventLibrary/")  # /usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/
	SKINPATH = f"{PLUGINPATH}skin/1080/" if DESKTOPSIZE.width() == 1920 else f"{PLUGINPATH}skin/720/"
	NETWORKDICT = {}
	NETWORKFILE = join(CONFIGPATH, "networks.json")
	TVS_MAPDICT = {}
	TVS_MAPFILE = join(CONFIGPATH, "tvs_mapping.txt")
	TVS_REFDICT = {}
	TVS_REFFILE = join(CONFIGPATH, "tvs_reflist.json")

	def __init__(self):
		self.saving = False
		self.STATUS = ""
		self.setPaths()
		config.plugins.AdvancedEventLibrary.Location.addNotifier(self.setPaths)

	def setStatus(self, text=None):
		self.STATUS = text or ""

	def setPaths(self, configItem=None):
		self.HDDPATH = config.plugins.AdvancedEventLibrary.Location.value
		if "AEL/" not in self.HDDPATH:
			self.HDDPATH = f"{self.HDDPATH}AEL/"
		createDirs(self.HDDPATH)
		self.POSTERPATH = f"{self.HDDPATH}poster/"
		self.COVERPATH = f"{self.HDDPATH}cover/"
		self.PREVIEWPATH = f"{self.HDDPATH}preview/"


aelGlobals = AELGlobals()


class DB_Functions(object):
	@staticmethod
	def dict_factory(cursor, row):
		d = {}
		for idx, col in enumerate(cursor.description):
			d[col[0]] = row[idx]
		return d

	def __init__(self, db_file):
		createDirs(aelGlobals.HDDPATH)
		self.conn = connect(db_file, check_same_thread=False)
		self.create_DB()

	def create_DB(self):
		cur = self.conn.cursor()
		# create table eventInfo
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='eventInfo';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE [eventInfo] ([base64title] TEXT NOT NULL,[title] TEXT NOT NULL,[genre] TEXT NULL,[year] TEXT NULL,[rating] TEXT NULL,[fsk] TEXT NULL,[country] TEXT NULL,[gDate] TEXT NOT NULL,[trailer] TEXT DEFAULT NULL,PRIMARY KEY ([base64title]))"
			cur.execute(query)
			self.conn.commit()
			write_log("Tabelle 'eventInfo' hinzugefügt")
		# create table blackList
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='blackList';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE [blackList] ([base64title] TEXT NOT NULL,PRIMARY KEY ([base64title]))"
			cur.execute(query)
			self.conn.commit()
			write_log("Tabelle 'blackList' hinzugefügt")
		# create table blackListCover
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='blackListCover';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE [blackListCover] ([filename] TEXT NOT NULL,PRIMARY KEY ([filename]))"
			cur.execute(query)
			self.conn.commit()
			write_log("Tabelle 'blackListCover' hinzugefügt")
		# create table blackListPoster
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='blackListPoster';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE [blackListPoster] ([filename] TEXT NOT NULL,PRIMARY KEY ([filename]))"
			cur.execute(query)
			self.conn.commit()
			write_log("Tabelle 'blackListPoster' hinzugefügt")
		# create table liveOnTV
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='liveOnTV';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE [liveOnTV] (eid INTEGER NOT NULL, id TEXT,subtitle TEXT,image TEXT,year TEXT,fsk TEXT,rating TEXT,title TEXT,airtime INTEGER NOT NULL,leadText TEXT,conclusion TEXT,categoryName TEXT,season TEXT,episode TEXT,genre TEXT,country TEXT,imdb TEXT,sref TEXT NOT NULL, PRIMARY KEY ([eid],[airtime],[sref]))"
			cur.execute(query)
			self.conn.commit()
			write_log("Tabelle 'liveOnTV' hinzugefügt")
		# delete table myliveTV
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='myliveTV';"
		cur.execute(query)
		if cur.fetchall():
			query = "DROP TABLE myliveTV"
			cur.execute(query)
			self.conn.commit()
		# delete table liveTV
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='liveTV';"
		cur.execute(query)
		if cur.fetchall():
			query = "DROP TABLE liveTV"
			cur.execute(query)
			self.conn.commit()
		# create table imageBlackList
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='imageBlackList';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE [imageBlackList] ([name] TEXT NOT NULL,PRIMARY KEY ([name]))"
			cur.execute(query)
			self.conn.commit()
			write_log("Tabelle 'imageBlackList' hinzugefügt")
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='parameters';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE `parameters` ( `name` TEXT NOT NULL UNIQUE, `value` TEXT, PRIMARY KEY(`name`) )"
			cur.execute(query)
			self.conn.commit()
			write_log("Tabelle 'parameters' hinzugefügt")
		#append columns eventInfo
		query = "PRAGMA table_info('eventInfo');"
		cur.execute(query)
		rows = cur.fetchall()
		found = False
		for row in rows:
			if "trailer" in row[1]:
				found = True
				break
		if found is False:
			query = "ALTER TABLE 'eventInfo' ADD COLUMN `trailer` TEXT DEFAULT NULL"
			cur.execute(query)
			self.conn.commit()

	def releaseDB(self):
		self.conn.close()

	def execute(self, query, args=()):
		cur = self.conn.cursor()
		cur.execute(query, args)

	def parameter(self, action, name, value=None, default=None):
		cur = self.conn.cursor()
		if action == aelGlobals.PARAMETER_GET:
			query = "SELECT value FROM parameters WHERE name = ?"
			cur.execute(query, (name,))
			rows = cur.fetchall()
			return {"False": False, "True": True}.get(rows[0][0], rows[0][0]) if rows else default
		elif action == aelGlobals.PARAMETER_SET and value or value is False:
			query = "REPLACE INTO parameters (name,value) VALUES (?,?)"
			cur.execute(query, (name, {False: "False", True: "True"}.get(value, value)))
			self.conn.commit()
			return value

	def addTitleInfo(self, base64title, title, genre, year, rating, fsk, country, trailer=None):
		now = str(time())
		cur = self.conn.cursor()
		query = "insert or ignore into eventInfo (base64title,title,genre,year,rating,fsk,country,gDate,trailer) values (?,?,?,?,?,?,?,?,?);"
		cur.execute(query, (base64title, title, genre, year, rating, fsk, country, now, trailer))
		self.conn.commit()

	def addliveTV(self, records):
		cur = self.conn.cursor()
		cur.executemany("insert or ignore into liveOnTV values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);", records)
		write_log(f"have inserted {cur.rowcount} events into database")
		self.conn.commit()
		# self.parameter(aelGlobals.PARAMETER_SET, "lastadditionalDataCount", str(cur.rowcount))f

	def updateTitleInfo(self, title, genre, year, rating, fsk, country, base64title):
		now = str(time())
		cur = self.conn.cursor()
		query = "update eventInfo set title = ?, genre = ?, year = ?, rating = ?, fsk = ?, country = ?, gDate = " + now + " where base64title = ?;"
		cur.execute(query, (title, genre, year, rating, fsk, country, base64title))
		self.conn.commit()

	def updateSingleEventInfo(self, col, val, base64title):
		cur = self.conn.cursor()
		query = "update eventInfo set " + str(col) + "= ? where base64title = ?;"
		cur.execute(query, (str(val), base64title))
		self.conn.commit()

	def updateTrailer(self, trailer, base64title):
		cur = self.conn.cursor()
		query = "update eventInfo set trailer = ? where base64title = ?;"
		cur.execute(query, (str(trailer), base64title))
		self.conn.commit()

	def updateliveTVInfo(self, image, genre, year, rating, fsk, country, eid):
		cur = self.conn.cursor()
		query = "update liveOnTV set image = ?, genre = ?, year = ?, rating = ?, fsk = ?, country = ? where eid = ?;"
		cur.execute(query, (image, genre, year, rating, fsk, country, eid))
		self.conn.commit()

	def updateliveTV(self, id, subtitle, image, year, fsk, rating, leadText, conclusion, categoryName, season, episode, genre, country, imdb, title, airtime):
		low = airtime - 360
		high = airtime + 360
		cur = self.conn.cursor()
		query = "update liveOnTV set id = ?, subtitle = ?, image = ?, year = ?, fsk = ?, rating = ?, leadText = ?, conclusion = ?, categoryName = ?, season = ?, episode = ?, genre = ?, country = ?, imdb = ? where title = ? AND airtime BETWEEN ? AND ? AND id = 'in progress';"
		cur.execute(query, (id, subtitle, image, year, fsk, rating, str(leadText), str(conclusion), str(categoryName), season, episode, genre, country, imdb, title, low, high))
		self.conn.commit()

#	def updateliveTVS(self, id,subtitle,image,year,fsk,rating,leadText,conclusion,categoryName,season,episode,genre,country, imdb, sref, airtime):
#		low = airtime - 150
#		high = airtime + 150
#		cur = self.conn.cursor()
#		query = "update liveOnTV set id = ?, subtitle = ?, image = ?, year = ?, fsk = ?, rating = ?, leadText = ?, conclusion = ?, categoryName = ?, season = ?, episode = ?, genre = ?, country = ?, imdb = ? where sref = ? AND airtime BETWEEN ? AND ? AND id = 'in progress';"
#		cur.execute(query,(id, subtitle.decode('utf8'), image.decode('utf8'), year, fsk, rating, str(leadText).decode('utf8'), str(conclusion).decode('utf8'), str(categoryName).decode('utf8'), season, episode, genre.decode('utf8'), country, str(imdb).decode('utf8'), str(sref).decode('utf8'), low, high))
#		self.conn.commit()

	def updateliveTVS(self, id, subtitle, image, year, fsk, rating, leadText, conclusion, categoryName, season, episode, genre, country, imdb, sref, airtime, title):
		updatetRows = 0
		low = airtime - 150
		high = airtime + 150
		cur = self.conn.cursor()
		query = "update liveOnTV set id = ?, subtitle = ?, image = ?, year = ?, fsk = ?, rating = ?, leadText = ?, conclusion = ?, categoryName = ?, season = ?, episode = ?, genre = ?, country = ?, imdb = ? where sref = ? AND airtime BETWEEN ? AND ? AND id = 'in progress';"
		cur.execute(query, (id, subtitle, image, year, fsk, rating, str(leadText), str(conclusion), str(categoryName), season, episode, genre, country, str(imdb), str(sref), low, high))
		updatetRows = cur.rowcount
		self.conn.commit()
		if updatetRows < 1:  # Suche mit titel
			low = airtime - 2700
			high = airtime + 2700
			query = "SELECT sref, airtime FROM liveOnTV WHERE title = ? AND sref = ? AND airtime BETWEEN ? AND ? AND id = 'in progress' ORDER BY airtime ASC LIMIT 1;"
			cur.execute(query, (title, str(sref), low, high))
			row = cur.fetchone()
			if row:
				query = "UPDATE liveOnTV set id = ?, subtitle = ?, image = ?, year = ?, fsk = ?, rating = ?, leadText = ?, conclusion = ?, categoryName = ?, season = ?, episode = ?, genre = ?, country = ?, imdb = ? where sref = ? AND airtime = ? AND  id = 'in progress';"
				cur.execute(query, (id, subtitle, image, year, fsk, rating, str(leadText), str(conclusion), str(categoryName), season, episode, genre, country, str(imdb), str(row[0]), row[1]))
				self.conn.commit()

	def updateliveTVProgress(self):
		cur = self.conn.cursor()
		query = "update liveOnTV set id = '' where id = 'in progress';"
		cur.execute(query)
		write_log(f"nothing found for '{cur.rowcount}' events in liveOnTV")
		self.conn.commit()
		self.parameter(aelGlobals.PARAMETER_SET, 'lastadditionalDataCountSuccess', str(cur.rowcount))

	def getTitleInfo(self, base64title):
		cur = self.conn.cursor()
		query = "SELECT base64title,title,genre,year,rating,fsk,country, trailer FROM eventInfo WHERE base64title = ?"
		cur.execute(query, (str(base64title),))
		row = cur.fetchall()
		return [row[0][0], row[0][1], row[0][2], row[0][3], row[0][4], row[0][5], row[0][6], str(row[0][7])] if row else []

	def getliveTV(self, eid, name=None, beginTime=None):
		tvname = ""
		cur = self.conn.cursor()
		if name:
			tvname = name
			# tvname = tvname.replace(" +", " ")  # TODO: wird das überhaupt gebraucht?
			# tvname = sub(r'\\(.*?\\)', '', tvname).strip() # TODO: wird der komische Regex überhaupt gebraucht?
			query = "SELECT * FROM liveOnTV WHERE eid = ? AND title = ?"
			cur.execute(query, (eid, tvname))
		else:
			query = "SELECT * FROM liveOnTV WHERE eid = ?"
			cur.execute(query, (eid,))
		row = cur.fetchall()
		if row:
			if row[0][1]:
				return [row[0]]
			else:
				if name and beginTime:
					query = "SELECT * FROM liveOnTV WHERE airtime = ? AND title = ?"
					cur.execute(query, (str(beginTime), tvname))
					row = cur.fetchall()
					return [row[0]] if row else []
		else:
			return []

	def getSrefsforUpdate(self):
		now = str(int(time() - 7200))
		refList = []
		cur = self.conn.cursor()
		query = f"SELECT DISTINCT sref FROM liveOnTV WHERE id = 'in progress' and airtime > {now}"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				refList.append(row[0])
		return refList

	def getMissingPictures(self):
		coverList = []
		posterList = []
		cur = self.conn.cursor()
		query = "SELECT DISTINCT title FROM liveOnTV WHERE categoryName = 'Spielfilm' or categoryName = 'Serie' ORDER BY title"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				if getImageFile(f"{aelGlobals.COVERPATH}", row[0]) is None:
					coverList.append(row[0])
				if getImageFile(f"{aelGlobals.HDDPATH}poster/", row[0]) is None:
					posterList.append(row[0])
		return [coverList, posterList]

	def getMinAirtimeforUpdate(self, sref):
		cur = self.conn.cursor()
		now = str(int(time() - 7200))
		query = f"SELECT Min(airtime) FROM liveOnTV WHERE id = 'in progress' and sref = ? and airtime > {now}"
		cur.execute(query, (str(sref),))
		row = cur.fetchall()
		return row[0][0] if row else 4000000000

	def getMaxAirtimeforUpdate(self, sref):
		cur = self.conn.cursor()
		now = str(int(time() - 7200))
		query = f"SELECT Max(airtime) FROM liveOnTV WHERE id = 'in progress' and sref = ? and airtime > {now}"
		cur.execute(query, (str(sref),))
		row = cur.fetchall()
		return row[0][0] if row else 1000000000

	def getUpdateCount(self):
		cur = self.conn.cursor()
		now = str(int(time() - 7200))
		query = f"SELECT COUNT(title) FROM liveOnTV WHERE id = 'in progress' and airtime > {now}"
		cur.execute(query)
		row = cur.fetchall()
		return row[0][0] if row else 0

	def getTrailerCount(self):
		trailercount = set()
		cur = self.conn.cursor()
		query = "SELECT DISTINCT imdb FROM liveOnTV WHERE imdb <> ''"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				trailercount.add(row[0])
		write_log(f"found {len(trailercount)} on liveTV")
		i = len(trailercount)
		query = "SELECT DISTINCT trailer FROM eventInfo WHERE trailer <> ''"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				trailercount.add(row[0])
		eI = len(trailercount) - i
		write_log(f"found {eI} on eventInfo")
		return len(trailercount)

	def getEventCount(self, sref):
		cur = self.conn.cursor()
		query = "SELECT COUNT(sref) FROM liveOnTV WHERE sref = ?"
		cur.execute(query, (str(sref),))
		row = cur.fetchall()
		return row[0][0] if row else 0

	def getTitlesforUpdate(self):
		now = str(int(time() - 7200))
		titleList = []
		cur = self.conn.cursor()
		query = f"SELECT DISTINCT title FROM liveOnTV WHERE id = 'in progress' and airtime > {now}"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				itm = [row[0]]
				titleList.append(itm)
		return titleList

	def getTitlesforUpdate2(self):
		now = str(int(time() - 7200))
		titleList = []
		cur = self.conn.cursor()
		query = f"SELECT DISTINCT title FROM liveOnTV WHERE id = 'in progress' and (title like '% - %' or title like '%: %') and airtime > {now}"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				itm = [row[0]]
				titleList.append(itm)
		return titleList

	def getUnusedTitles(self):
		titleList = []
		cur = self.conn.cursor()
		query = "SELECT base64title, title FROM eventInfo ORDER BY gDate ASC LIMIT 100;"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				itm = [row[0], row[1]]
				titleList.append(itm)
		return titleList

	def checkTitle(self, base64title):
		cur = self.conn.cursor()
		query = "SELECT base64title FROM eventInfo where base64title = ?;"
		cur.execute(query, (str(base64title),))
		rows = cur.fetchall()
		return True if rows else False

	def checkliveTV(self, eid, ref):
		cur = self.conn.cursor()
		query = "SELECT eid FROM liveOnTV where eid = ? AND sref = ?;"
		cur.execute(query, (eid, ref))
		rows = cur.fetchall()
		return True if rows else False

	def cleanDB(self, base64title):
		cur = self.conn.cursor()
		query = "delete from eventInfo where base64title = ?;"
		cur.execute(query, (str(base64title),))
		self.conn.commit()
		query = "delete from blackList where base64title = ?;"
		cur.execute(query, (str(base64title),))
		self.conn.commit()

	def cleanliveTV(self, airtime):
		cur = self.conn.cursor()
		query = "delete from liveOnTV where airtime < ?;"
		cur.execute(query, (str(airtime),))
		write_log(f"have removed {cur.rowcount} events from liveOnTV")
		self.conn.commit()
		self.vacuumDB()

	def cleanliveTVEntry(self, eid):
		cur = self.conn.cursor()
		query = "delete from liveOnTV where eid = ?;"
		cur.execute(query, (str(eid),))
		self.conn.commit()

	def getUnusedPreviewImages(self, airtime):
		titleList = []
		duplicates = []
		delList = []
		cur = self.conn.cursor()
		query = 'SELECT DISTINCT image from liveOnTV where airtime > ? AND image <> "";'
		cur.execute(query, (str(airtime),))
		rows = cur.fetchall()
		if rows:
			for row in rows:
				duplicates.append(row[0])
		query = 'SELECT DISTINCT image from liveOnTV where airtime < ? AND image <> "";'
		cur.execute(query, (str(airtime),))
		rows = cur.fetchall()
		write_log(f"found old preview images {len(rows)}")
		if rows:
			for row in rows:
				titleList.append(row[0])
		delList = [x for x in titleList if x not in duplicates]
		write_log(f"not used preview images {len(delList)}")
		del duplicates
		del titleList
		return delList

	def cleanblackList(self):
		cur = self.conn.cursor()
		query = "delete from blackList;"
		cur.execute(query)
		self.conn.commit()
		query = "delete from imageBlackList;"
		cur.execute(query)
		self.conn.commit()
		self.vacuumDB()

	def cleanNadd2BlackList(self, base64title):
		cur = self.conn.cursor()
		query = "delete from eventInfo where base64title = ?;"
		cur.execute(query, (str(base64title),))
		self.conn.commit()
		query = "insert or ignore into blackList (base64title) values (?);"
		cur.execute(query, (str(base64title),))
		self.conn.commit()

	def addblackList(self, base64title):
		cur = self.conn.cursor()
		query = "insert or ignore into blackList (base64title) values (?);"
		cur.execute(query, (str(base64title),))
		self.conn.commit()

	def addblackListCover(self, filename):
		cur = self.conn.cursor()
		query = "insert or ignore into blackListCover (filename) values (?);"
		cur.execute(query, (filename,))
		self.conn.commit()

	def addblackListPoster(self, filename):
		cur = self.conn.cursor()
		query = "insert or ignore into blackListPoster (filename) values (?);"
		cur.execute(query, (str(filename),))
		self.conn.commit()

	def addimageBlackList(self, name):
		cur = self.conn.cursor()
		query = "insert or ignore into imageBlackList (name) values (?);"
		cur.execute(query, (name,))
		self.conn.commit()

	def getimageBlackList(self, name):
		cur = self.conn.cursor()
		query = "SELECT name FROM imageBlackList WHERE name = ?"
		cur.execute(query, (name,))
		row = cur.fetchall()
		return True if row else False

	def getblackList(self, base64title):
		cur = self.conn.cursor()
		query = "SELECT base64title FROM blackList WHERE base64title = ?"
		cur.execute(query, (base64title,))
		row = cur.fetchall()
		return True if row else False

	def getblackListCover(self, filename):
		cur = self.conn.cursor()
		query = "SELECT filename FROM blackListCover WHERE filename = ?"
		cur.execute(query, (filename,))
		row = cur.fetchall()
		return True if row else False

	def getblackListPoster(self, filename):
		cur = self.conn.cursor()
		query = "SELECT filename FROM blackListPoster WHERE filename = ?"
		cur.execute(query, (filename,))
		row = cur.fetchall()
		return True if row else False

	def getblackListCount(self):
		cur = self.conn.cursor()
		query = "SELECT COUNT(base64title) FROM blackList"
		cur.execute(query)
		row = cur.fetchall()
		return row[0][0] if row else 0

	def getTitleInfoCount(self):
		cur = self.conn.cursor()
		query = "SELECT COUNT(base64title) FROM eventInfo"
		cur.execute(query)
		row = cur.fetchall()
		return row[0][0] if row else 0

	def getliveTVCount(self):
		cur = self.conn.cursor()
		query = "SELECT COUNT(eid) FROM liveOnTV"
		cur.execute(query)
		row = cur.fetchall()
		return row[0][0] if row else 0

	def getliveTVidCount(self):
		cur = self.conn.cursor()
		query = "SELECT COUNT(id) FROM liveOnTV WHERE id <> '' AND id <> 'in progress'"
		cur.execute(query)
		row = cur.fetchall()
		return row[0][0] if row else 0

	def getMaxAirtime(self, title):
		cur = self.conn.cursor()
		#========== geaendert (#8) =============
		#query = "SELECT Max(airtime) FROM liveOnTV WHERE title = ?"
		query = "SELECT Max(airtime),sRef FROM liveOnTV WHERE title = ?"
		# =======================================
		cur.execute(query, (title,))
		row = cur.fetchall()
		if row:
			#========== geaendert (#8) =============
			#return row[0][0]
			return 4000000000 if "http" in row[0][1] else row[0][0]
			# ===================================
		else:
			return 4000000000
#		return row[0][0] if row else 4000000000

	def getSeriesStarts(self):
		now = time()
		titleList = []
		cur = self.conn.cursor()
		if config.plugins.AdvancedEventLibrary.SeriesType.value == 'Staffelstart':
			query = f"SELECT sref, eid, categoryName FROM liveOnTV WHERE sref <> '' AND episode = '1' AND airtime > {now} ORDER BY categoryName, airtime"
		else:
			query = f"SELECT sref, eid, categoryName FROM liveOnTV WHERE sref <> '' AND season = '1' AND episode = '1' AND airtime > {now}  ORDER BY categoryName, airtime"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				itm = [row[0], row[1], row[2]]
				titleList.append(itm)
		return titleList

	def getSeriesStartsCategories(self):
		now = time()
		titleList = []
		cur = self.conn.cursor()
		if config.plugins.AdvancedEventLibrary.SeriesType.value == 'Staffelstart':
			query = f"SELECT Distinct categoryName from liveOnTV where airtime > {now} AND sref <> '' and episode = '1'"
		else:
			query = f"SELECT Distinct categoryName from liveOnTV where airtime > {now} AND sref <> '' and season = '1' and episode = '1'"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				itm = [row[0]]
				titleList.append(itm)
		return titleList

	def getFavourites(self, what="genre LIKE 'Krimi'", duration=86400):
		start = time()
		end = time() + duration
		titleList = []
		cur = self.conn.cursor()
		query = f"SELECT eid, sref from liveOnTV where airtime BETWEEN {start} AND {end} AND {what}"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				titleList.append(row)
		return titleList

	def getGenres(self):
		titleList = []
		cur = self.conn.cursor()
		query = "SELECT Distinct genre from liveOnTV WHERE genre <> '' ORDER BY genre"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				titleList.append(row[0])
		return titleList

	def vacuumDB(self):
		cur = self.conn.cursor()
		cur.execute("VACUUM")
		self.conn.commit()


def url_parse(url, defaultPort=None):
	parsed = urlparse(url)
	scheme = parsed[0]
	path = urlunparse(("", "") + parsed[2:])
	if defaultPort is None:
		defaultPort = 443 if scheme == "https" else 80
	host, port = parsed[1], defaultPort
	if ":" in host:
		host, port = host.split(":")
		port = int(port)
	return scheme, host, port, path


class BingImageSearch:
	def __init__(self, query, limit, what="Cover"):
		self.download_count = 0
		self.query = query
		self.filters = "+filterui:photo-photo+filterui:aspect-wide&form=IRFLTR" if what == "Cover" else "+filterui:photo-photo+filterui:aspect-tall&form=IRFLTR"
		self.limit = limit
		self.page_counter = 0

	def search(self):
		resultList = []
		while self.download_count < self.limit:
			bingurl = b64decode(b"aHR0cHM6Ly93d3cuYmluZy5jb20vaW1hZ2VzL2FzeW5j8"[:-1]).decode()
			params = {"q": self.query, "first": self.page_counter, "count": self.limit, "adlt": "off", "qft": self.filters}
			write_log(f"Bing-requests : {bingurl}")
			errmsg, htmldata = getHTMLdata(bingurl, params=params)
			if errmsg:
				write_log("HTML download error in module 'BingImageSearch:search'")
			if htmldata:
				links = findall(r"murl&quot;:&quot;(.*?)&quot;", str(htmldata))
				write_log(f"Bing-result : {links}")
				if len(links) <= self.limit:
					self.limit = len(links) - 1
				for link in links:
					link = link.replace(".jpeg", ".jpg")
					if link:
						if self.download_count < self.limit:
							resultList.append(link)
							self.download_count += 1
						else:
							break
				self.page_counter += 1
		return resultList


class PicLoader:
	def __init__(self, width, height):
		self.picload = ePicLoad()
		self.picload.setPara((width, height, 0, 0, False, 1, "#ff000000"))

	def load(self, filename):
		self.picload.startDecode(filename, 0, 0, False)
		data = self.picload.getData()
		return data

	def destroy(self):
		del self.picload
