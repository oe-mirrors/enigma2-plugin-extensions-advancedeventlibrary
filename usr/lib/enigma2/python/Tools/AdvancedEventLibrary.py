__all__ = ['randbelow']   # TODO: Was das?
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
from random import SystemRandom, choice
from re import sub, compile, findall, IGNORECASE, MULTILINE, DOTALL
from requests import get, exceptions
from shutil import copy2, copyfileobj, move
from sqlite3 import connect
from subprocess import check_output
from time import time, localtime, mktime
from threading import Thread
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

DEFAULT_MODULE_NAME = __name__.split(".")[-1]

config.plugins.AdvancedEventLibrary = ConfigSubsection()
config.plugins.AdvancedEventLibrary.Location = ConfigText(default=f"{defaultRecordingLocation().replace('movie/', '')}AdvancedEventLibrary/")
config.plugins.AdvancedEventLibrary.Backup = ConfigText(default="/media/hdd/AdvancedEventLibraryBackup/")
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
config.plugins.AdvancedEventLibrary.searchPlaces = ConfigText(default='')
config.plugins.AdvancedEventLibrary.tmdbKey = ConfigText(default=_("internal"))
config.plugins.AdvancedEventLibrary.tvdbV4Key = ConfigText(default=_("unused"))
config.plugins.AdvancedEventLibrary.tvdbKey = ConfigText(default=_("internal"))
config.plugins.AdvancedEventLibrary.omdbKey = ConfigText(default=_("internal"))
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
config.plugins.AdvancedEventLibrary.StartBouquet = ConfigSelection(default=0, choices=[(0, _("Favorites")), (1, _("All Bouquets"))])
config.plugins.AdvancedEventLibrary.HDonly = ConfigYesNo(default=True)
config.plugins.AdvancedEventLibrary.StartTime = ConfigClock(default=69300)  # 20:15
config.plugins.AdvancedEventLibrary.Duration = ConfigInteger(default=60, limits=(20, 1440))

dir = config.plugins.AdvancedEventLibrary.Location.value
if "AdvancedEventLibrary/" not in dir:
	dir = f"{dir}AdvancedEventLibrary/"
sPDict = {}
if config.plugins.AdvancedEventLibrary.searchPlaces.value != '':
	sPDict = eval(config.plugins.AdvancedEventLibrary.searchPlaces.value)
#not used
#vtidb_loc = config.misc.db_path.value + '/vtidb.db'
STATUS = ""
PARAMETER_SET = 0
PARAMETER_GET = 1
SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
ADDLOG = config.plugins.AdvancedEventLibrary.Log.value
coverqualityDict = {"w300": "300x169", "w780": "780x439", "w1280": "1280x720", "w1920": "1920x1080"}
posterqualityDict = {"w185": "185x280", "w342": "342x513", "w500": "500x750", "w780": "780x1170"}
tmdb_genres = {10759: "Action-Abenteuer", 16: "Animation", 10762: "Kinder", 10763: "News", 10764: "Reality", 10765: "Sci-Fi-Fantasy", 10766: "Soap", 10767: "Talk", 10768: "War & Politics", 28: "Action", 12: "Abenteuer", 35: "Comedy", 80: "Crime", 99: "Dokumentation", 18: "Drama", 10751: "Familie", 14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Science-Fiction", 10770: "TV-Movie", 53: "Thriller", 10752: "War", 37: "Western"}
convNames = ['Polizeiruf', 'Tatort', 'Die Bergpolizei', 'Axte X', 'ANIXE auf Reisen', 'Close Up', 'Der Zürich-Krimi', 'Buffy', 'Das Traumschiff', 'Die Land', 'Faszination Berge', 'Hyperraum', 'Kreuzfahrt ins Gl', 'Lost Places', 'Mit offenen Karten', 'Newton', 'Planet Schule', 'Punkt 12', 'Regular Show', 'News Reportage', 'News Spezial', 'S.W.A.T', 'Xenius', 'Der Barcelona-Krimi', 'Die ganze Wahrheit', 'Firmen am Abgrund', 'GEO Reportage', 'Kommissar Wallander', 'Rockpalast', 'SR Memories', 'Wildes Deutschland', 'Wilder Planet', 'Die rbb Reporter', 'Flugzeug-Katastrophen', 'Heute im Osten', 'Kalkofes Mattscheibe', 'Neue Nationalparks', 'Auf Entdeckungsreise']
excludeNames = ['RTL UHD', '--', 'Sendeschluss', 'Dokumentation', 'EaZzzy', 'MediaShop', 'Dauerwerbesendung', 'Impressum']
coverIDs = [3, 8, 11, 15]
posterIDs = [2, 7, 14]
ApiKeys = {"tmdb": ["ZTQ3YzNmYzJkYzRlMWMwN2UxNGE4OTc1YjI5MTE1NWI=", "MDA2ZTU5NGYzMzFiZDc1Nzk5NGQwOTRmM2E0ZmMyYWM=", "NTRkMzg1ZjBlYjczZDE0NWZhMjNkNTgyNGNiYWExYzM="],
		   	"tvdb": ["NTRLVFNFNzFZWUlYM1Q3WA==", "MzRkM2ZjOGZkNzQ0ODA5YjZjYzgwOTMyNjI3ZmE4MTM=", "Zjc0NWRiMDIxZDY3MDQ4OGU2MTFmNjY2NDZhMWY4MDQ="],
			"omdb": ["ZmQwYjkyMTY=", "YmY5MTFiZmM=", "OWZkNzFjMzI="]
			}
networks = {
	'3sat': 'DEU',
	'A&E': 'USA',
	'AAG TV': 'PAK',
	'Aaj TV': 'PAK',
	'ABC (US)': 'USA',
	'ABC (AU)': 'AUS',
	'ABC (JA)': 'JPN',
	'ABC (PH)': 'PHL',
	'ABC Family': 'USA',
	'ABS-CBN Broadcasting Company': 'PHL',
	'Abu Dhabi TV': 'ARE',
	'Adult Channel': 'GBR',
	'Al Alam': 'IRN',
	'Al Arabiyya': 'ARE',
	'Al Jazeera': 'QAT',
	'Alpha TV GUJARATI': 'IND',
	'Alpha TV PUNJABI': 'IND',
	'America One Television Network': 'USA',
	'Animal Planet': 'USA',
	'Anime Network': 'USA',
	'ANT1': 'GRC',
	'Antena 3': 'ESP',
	'ARY Digital': 'PAK',
	'ARY One World': 'PAK',
	'ARY Shopping Channel': 'PAK',
	'ARY Zouq': 'PAK',
	'ATN Aastha Channel': 'IND',
	'AXN': 'USA',
	'B4U Movies': 'GBR',
	'B4U Music': 'GBR',
	'BabyFirstTV': 'USA',
	'BBC America': 'USA',
	'BBC Canada': 'CAN',
	'BBC Four': 'GBR',
	'BBC Kids': 'CAN',
	'BBC News': 'GBR',
	'BBC One': 'GBR',
	'BBC Parliament': 'GBR',
	'BBC Prime': 'GBR',
	'BBC Three': 'GBR',
	'BBC Two': 'GBR',
	'BBC World News': 'GBR',
	'FYI': 'USA',
	'Boomerang': 'USA',
	'BR': 'DEU',
	'BR-alpha': 'DEU',
	'Bravo (US)': 'USA',
	'Bravo (UK)': 'GBR',
	'Bravo (CA)': 'CAN',
	'Bubble Hits': 'IRL',
	'Canal+': 'FRA',
	'Canvas/Ketnet': 'BEL',
	'Carlton Television': 'GBR',
	'Cartoon Network': 'USA',
	'CBBC': 'GBR',
	'CBC (CA)': 'CAN',
	'CBeebies': 'GBR',
	'CBS': 'USA',
	'CCTV': 'CHN',
	'Challenge': 'GBR',
	'Channel [V]': 'CHN',
	'Channel 4': 'GBR',
	'Channel 5': 'SGP',
	'Channel 6': 'IRL',
	'Channel 8': 'SGP',
	'Channel U': 'SGP',
	'Chart Show TV': 'GBR',
	'Chorus Sports': 'IRL',
	'City Channel': 'IRL',
	'Classic Arts Showcase': 'USA',
	'Classic FM TV': 'GBR',
	'CN8': 'USA',
	'CNBC TV18': 'IND',
	'CNN': 'USA',
	'Comedy Channel': 'USA',
	'CPAC': 'CAN',
	'C-Span': 'USA',
	'CTV': 'CAN',
	'DR1': 'DNK',
	'Das Erste': 'DEU',
	'Dawn News': 'PAK',
	'Deutsche Welle TV': 'DEU',
	'Discovery': 'USA',
	'Discovery Kids': 'USA',
	'Dish TV': 'USA',
	'Disney Channel (US)': 'USA',
	'WOWOW': 'JPN',
	'Disney Cinemagic': 'GBR',
	'Doordarshan National': 'IND',
	'DD-Gujarati': 'IND',
	'Doordarshan News': 'IND',
	'Doordarshan Sports': 'IND',
	'E!': 'USA',
	'E! (CA)': 'CAN',
	'E4': 'GBR',
	'EBS': 'KOR',
	'ERT': 'GRC',
	'ESPN': 'USA',
	'ESPN Asia': 'HKG',
	'ESPN Hong Kong': 'HKG',
	'ESPN India': 'IND',
	'ESPN Philippines': 'PHL',
	'ESPN Taiwan': 'TWN',
	'ETV Gujarati': 'IND',
	'Eurosport': 'GBR',
	'Family (CA)': 'CAN',
	'Fashion TV': 'FRA',
	'Five': 'GBR',
	'Five Life': 'GBR',
	'Five US': 'GBR',
	'Fox Reality': 'USA',
	'France 2': 'FRA',
	'France 3': 'FRA',
	'France 4': 'FRA',
	'France 5': 'FRA',
	'France Ô': 'FRA',
	'Fred TV': 'USA',
	'Fuji TV': 'JPN',
	'FUNimation Channel': 'USA',
	'FX': 'USA',
	'GEO Super': 'PAK',
	'Geo TV': 'PAK',
	'GMA': 'PHL',
	'GSN': 'USA',
	'Guardian Television Network': 'USA',
	'Hallmark Channel': 'USA',
	'Indus Music': 'PAK',
	'Indus News': 'PAK',
	'Indus Vision': 'PAK',
	'Ion Television': 'USA',
	'KanaalTwee': 'BEL',
	'Kashish TV': 'PAK',
	'KBS': 'KOR',
	'Kerrang! TV': 'GBR',
	'Kids and Teens TV': 'USA',
	'KIKA': 'DEU',
	'Kiss': 'GBR',
	'KTN': 'KEN',
#	'KTN': 'PAK',
	'LCI': 'FRA',
	'Liberty Channel': 'USA',
	'Liberty TV': 'GBR',
	'Living': 'GBR',
	'M6': 'FRA',
	'Magic': 'GBR',
	'MATV': 'GBR',
	'MBS': 'JPN',
	'MDR': 'DEU',
	'Mega Channel': 'GRC',
	'MTV (US)': 'USA',
	'MTV Base': 'GBR',
	'MTV Dance': 'GBR',
	'MTV Hits': 'USA',
	'MTV2': 'USA',
	'MBC': 'KOR',
	'MUTV': 'GBR',
	'National Geographic (US)': 'USA',
	'NBC': 'USA',
	'NDR': 'DEU',
	'NDTV 24x7': 'IND',
	'NDTV India': 'IND',
	'New Tang Dynasty TV': 'USA',
	'News One': 'PAK',
	'NHK': 'JPN',
	'Nick at Nite': 'USA',
	'Nick GAS': 'USA',
	'Nickelodeon': 'USA',
	'NickToons': 'USA',
	'Nine Network': 'AUS',
	'Noggin': 'USA',
	'NTA': 'NGA',
	'NTV (JP)': 'JPN',
	'Ovation TV': 'USA',
	'Paramount Comedy': 'GBR',
	'PBS': 'USA',
	'PBS Kids Sprout': 'USA',
	'Phoenix': 'DEU',
	'Phoenix TV': 'CHN',
	'Playboy TV': 'USA',
	'Playhouse Disney': 'USA',
	'PlayJam': 'GBR',
	'Press TV': 'IRN',
	'PRO TV': 'ROU',
	'PTV Bolan': 'PAK',
	'PTV Global': 'USA',
	'PTV Home': 'PAK',
	'PTV News': 'PAK',
	'Pub Channel': 'GBR',
	'Q TV': 'GBR',
	'QTV': 'PAK',
	'QVC': 'USA',
	'Radio Bremen': 'DEU',
	'Radio Canada': 'CAN',
	'RAI': 'ITA',
	'RBB': 'DEU',
	'RCTI': 'IDN',
	'Record': 'BRA',
	'Red Hot TV': 'GBR',
	'Rede Globo': 'BRA',
	'Revelation TV': 'GBR',
	'rmusic TV': 'GBR',
	'Royal News': 'PAK',
	'RTÉ One': 'IRL',
	'RTÉ Two': 'IRL',
	'RTL Television': 'DEU',
	'RTP Açores': 'PRT',
	'RTP África': 'PRT',
	'RTP Internacional': 'PRT',
	'RTP Madeira': 'PRT',
	'RTP N': 'PRT',
	'RTP1': 'PRT',
	'S4/C': 'GBR',
	'S4C2': 'GBR',
	'Sab TV': 'IND',
	'Sahara ONE': 'IND',
	'Sanskar': 'IND',
	'SBS': 'KOR',
	'SBS (AU)': 'AUS',
	'Scuzz': 'GBR',
	'SET MAX': 'IND',
	'Setanta Ireland': 'IRL',
	'Seven Network': 'AUS',
	'Showtime': 'USA',
	'SIC': 'PRT',
	'SIC Comédia': 'PRT',
	'SIC Mulher': 'PRT',
	'SIC Notícias': 'PRT',
	'SIC Radical': 'PRT',
	'SIC Sempre Gold': 'PRT',
	'Sirasa': 'LKA',
	'Sky Box Office': 'GBR',
	'Sky Cinema (UK)': 'GBR',
	'Sky Movies': 'GBR',
	'Sky News': 'GBR',
	'Sky News Ireland': 'IRL',
	'Sky Sports': 'GBR',
	'Sky Travel': 'GBR',
	'Sky1': 'GBR',
	'Sky2': 'GBR',
	'Sky3': 'GBR',
	'Sleuth': 'USA',
	'Smash Hits': 'GBR',
	'SOAPnet': 'USA',
	'Sony Entertainment Television': 'USA',
	'Sony TV': 'IND',
	'Spike TV': 'USA',
	'STAR Gold': 'IND',
	'STAR Movies': 'HKG',
	'STAR News': 'IND',
	'STAR Plus': 'IND',
	'STAR Sports Asia': 'HKG',
	'STAR Sports Hong Kong': 'HKG',
	'STAR Sports India': 'IND',
	'STAR Sports Southeast Asia': 'HKG',
	'STAR Sports Malaysia': 'MYS',
	'STAR Sports Taiwan': 'TWN',
	'STAR Vijay': 'IND',
	'Star World': 'HKG',
	'Starz!': 'USA',
	'Studio 23': 'PHL',
	'STV (UK)': 'GBR',
	'Style': 'USA',
	'SUN music': 'IND',
	'SUN news': 'IND',
	'SUN TV': 'IND',
	'Superstation WGN': 'USA',
	'Swarnawahini': 'LKA',
	'SWR': 'DEU',
	'Tokyo Broadcasting System': 'JPN',
	'TBS': 'USA',
	'TCM': 'GBR',
	'TeleG': 'GBR',
	'Telemundo': 'USA',
	'Televisa': 'MEX',
	'TEN Sports': 'IND',
	'TF1': 'FRA',
	'The Amp': 'GBR',
	'The Box': 'GBR',
	'The CW': 'USA',
	'The Den': 'IRL',
	'TeenNick': 'USA',
	'The WB': 'USA',
	'The Weather Channel': 'USA',
	'TMC': 'MCO',
	'TMF': 'NLD',
	'TNT': 'USA',
	'Toon Disney': 'USA',
	'TQS': 'CAN',
	'Travel Channel (UK)': 'GBR',
	'Treehouse TV': 'CAN',
	'truTV': 'USA',
	'Turner South': 'USA',
	'TV Asahi': 'JPN',
	'TV Cabo': 'PRT',
	'TV Chile': 'CHL',
	'TV Guide Channel': 'USA',
	'TV Land': 'USA',
	'TVOne Global': 'PAK',
	'TV Tokyo': 'JPN',
	'TV5 Monde': 'FRA',
	'TVB': 'CHN',
	'TVBS': 'CHN',
	'TVE': 'ESP',
	'TVG Network': 'USA',
	'TVI': 'PRT',
	'TVM': 'MLT',
	'TVRI': 'IDN',
	'TVS Sydney': 'AUS',
	'UK Entertainment Channel': 'GBR',
	'Eden': 'GBR',
	'UKTV Drama': 'GBR',
	'UKTV Food': 'GBR',
	'Dave': 'GBR',
	'UKTV Gold': 'GBR',
	'UKTV History': 'GBR',
	'UKTV Style': 'GBR',
	'Univision': 'USA',
	'UNTV 37': 'PHL',
	'UPN': 'USA',
	'USA Network': 'USA',
	'UTV': 'IRL',
	'Varsity TV': 'USA',
	'VH1': 'USA',
	'VH1 Classics': 'USA',
	'VijfTV': 'BEL',
	'Volksmusik TV': 'DEU',
	'VT4': 'BEL',
	'VTM': 'BEL',
	'Warner Channel': 'USA',
	'WDR': 'DEU',
	'WE tv': 'USA',
	'XY TV': 'USA',
	'YLE': 'FIN',
	'YTV (CA)': 'CAN',
	'ZDF': 'DEU',
	'Zee Gujarati': 'IND',
	'Zee Cinema': 'IND',
	'Zee Muzic': 'IND',
	'Zee TV': 'IND',
	'ZOOM': 'IND',
	'ITV': 'GBR',
	'BBC HD': 'GBR',
	'ITV1': 'GBR',
	'ITV2': 'GBR',
	'ITV3': 'GBR',
	'ITV4': 'GBR',
	'FOX (US)': 'USA',
	'Space': 'CAN',
	'HBO': 'USA',
	'SciFi': 'USA',
	'Syndicated': '',
	'Showcase (CA)': 'CAN',
	'Teletoon': 'CAN',
	'Télétoon': 'FRA',
	'TVNZ': 'NZL',
	'Comedy Central (US)': 'USA',
	'TLC': 'USA',
	'Food Network': 'USA',
	'Global': 'CAN',
	'DuMont Television Network': 'USA',
	'History': 'USA',
	'Encore': 'USA',
	'Lifetime': 'USA',
	'één': 'BEL',
	'G4': 'USA',
	'Revision3': 'USA',
	'Network Ten': 'AUS',
	'Cinemax': 'USA',
	'Canale 5': 'ITA',
	'Oxygen': 'USA',
	'Court TV': 'USA',
	'HGTV': 'USA',
	'CTC': 'JPN',
	'NRK1': 'NOR',
	'NRK2': 'NOR',
	'NRK3': 'NOR',
	'NRK Super': 'NOR',
	'TV 2': 'NOR',
	'TV 2 Zebra': 'NOR',
	'TV 2 Filmkanalen': 'NOR',
	'TV 2 Nyhetskanalen': 'NOR',
	'TV 2 Sport': 'NOR',
	'TV 2 Science Fiction': 'NOR',
	'TVNorge': 'NOR',
	'Viasat 4': 'NOR',
	'FEM': 'GBR',
	'Syfy': 'USA',
	'IFC': 'USA',
	'SundanceTV': 'USA',
#	'TV 2': 'DNK',
	'TV 3': 'DNK',
	'Speed': 'USA',
	'TV 4': 'POL',
	'TVN': 'POL',
	'TVN Turbo': 'POL',
	'TVP SA': 'POL',
	'TVP1': 'POL',
	'TVP2': 'POL',
	'Tokyo MX': 'JPN',
	'SAT.1': 'DEU',
	'ProSieben': 'DEU',
	'TV4': 'SWE',
	'History (CA)': 'CAN',
	'BS11': 'JPN',
	'Arte': 'FRA',
	'Planet Green': 'USA',
	'Schweizer Fernsehen': 'CHE',
	'CBC (JP)': 'JPN',
	'HBO Canada': 'CAN',
	'The Movie Network': 'CAN',
	'Movie Central': 'CAN',
	'Travel Channel': 'USA',
	'AMC': 'USA',
	'ORF 1': 'AUT',
	'ORF 2': 'AUT',
	'Animax': 'JPN',
	'Telecinco': 'ESP',
	'La Siete': 'ESP',
	'TVA (JP)': 'JPN',
	'Investigation Discovery': 'USA',
	'TV Azteca': 'MEX',
	'Séries+': 'CAN',
	'V': 'CAN',
	'Television Osaka': 'JPN',
	'SVT': 'SWE',
	'Ztélé': 'CAN',
	'Vrak.TV': 'CAN',
	'Casa': 'CAN',
	'Logo': 'USA',
	'Disney XD': 'USA',
	'Prime (NZ)': 'NZL',
	'2×2': 'RUS',
	'TV Nova': 'CZE',
	'Ceská televize': 'CZE',
	'Prima televize': 'CZE',
	'Science Channel': 'USA',
	'DIY Network': 'USA',
	'AVRO': 'NLD',
	'NCRV': 'NLD',
	'KRO': 'NLD',
	'VPRO': 'NLD',
	'VARA': 'NLD',
	'BNN (NL)': 'NLD',
	'EO': 'NLD',
	'TROS': 'NLD',
	'Veronica': 'NLD',
	'SBS 6': 'NLD',
	'NET 5': 'NLD',
	'BET': 'USA',
	'ORTF': 'FRA',
	'Fox Business': 'USA',
	'AT-X': 'JPN',
	'OWN': 'USA',
	'CMT': 'USA',
	'Cooking Channel': 'USA',
	'HOT': 'ISR',
	'yes': 'ISR',
	'Current TV': 'USA',
	'The Hub': 'USA',
	'1+1': 'UKR',
	'ICTV': 'UKR',
	'Military Channel': 'USA',
	'WealthTV': 'USA',
	'MTV3': 'FIN',
	'Nelonen': 'FIN',
	'TV3 (NZ)': 'NZL',
	'TV 2 Zulu': 'DNK',
	'TV 2 Charlie': 'DNK',
	'TV3+': 'DNK',
	'TV3 Puls': 'DNK',
	'DR2': 'DNK',
	'DR K': 'DNK',
	'DR Ramasjang': 'DNK',
	'Kanal 4': 'DNK',
	'Kanal 5': 'DNK',
	'dk4': 'DNK',
	'Magyar Televízió': 'HUN',
	'Outdoor Channel': 'USA',
	'The Sportsman Channel': 'USA',
	'ATV': 'AUT',
	'Puls 4': 'AUT',
	'Servus TV': 'AUT',
	'LifeStyle': 'AUS',
	'SVT1': 'SWE',
	'SVT2': 'SWE',
	'Kunskapskanalen': 'SWE',
	'SVT24': 'SWE',
	'SVTB': 'SWE',
	'TV11': 'SWE',
	'TV4 Plus': 'SWE',
	'TV4 Guld': 'SWE',
	'TV4 Fakta': 'SWE',
	'TV4 Komedi': 'SWE',
	'TV4 Science Fiction': 'SWE',
	'TV3 (SE)': 'SWE',
	'TV6': 'SWE',
	'TV7 (SE)': 'SWE',
	'TV8': 'SWE',
	'HDNet': 'USA',
	'JIM': 'FIN',
	'SuoimiTV': 'FIN',
	'Sub': 'FIN',
	'MoonTV': 'FIN',
	'ReelzChannel': 'USA',
	'BYU Television': 'USA',
	'DMAX (DE)': 'DEU',
	'OLN': 'CAN',
	'Action': 'CAN',
	'Rai 1': 'ITA',
	'Rai 2': 'ITA',
	'Rai 3': 'ITA',
	'Rete 4': 'ITA',
	'Italia 1': 'ITA',
	'Joi': 'ITA',
	'Mya': 'ITA',
	'Steel': 'ITA',
	'Fox (IT)': 'ITA',
	'Fox Life': 'ITA',
	'Fox Crime': 'ITA',
	'RTL 4': 'NLD',
	'RTL 5': 'NLD',
	'RTL 7': 'NLD',
	'RTL 8': 'NLD',
	'CNBC': 'USA',
	'ZDF.Kultur': 'DEU',
	'ZDFneo': 'DEU',
	'Kids Station': 'JPN',
	'Watch': 'GBR',
	'YTV (JP)': 'JPN',
	'TNU': 'URY',
	'Canal 10 Saeta': 'URY',
	'Teledoce': 'URY',
	'Canal 4 Montecarlo': 'URY',
	'TevéCiudad': 'URY',
	'Encuentro': 'ARG',
	'TV Pública': 'ARG',
	'Einsfestival': 'DEU',
	'SR': 'DEU',
	'Kyoto Broadcasting System': 'JPN',
	'YTV (UK)': 'GBR',
	'Velocity': 'USA',
	'ITV Granada': 'GBR',
	'Netflix': 'USA',
	'NTR': 'NLD',
	'TV3 (ES)': 'ESP',
	'BNT1': 'BGR',
	'bTV': 'BGR',
	'NovaTV': 'BGR',
	'TV7 (BG)': 'BGR',
	'MNN': 'USA',
	'Voyage': 'FRA',
	'Fox8': 'AUS',
	'CI': 'AUS',
	'LifeStyle FOOD': 'AUS',
	'LifeStyle HOME': 'AUS',
	'MSNBC': 'USA',
	'NHNZ': 'NZL',
#	'Kanal 5': 'SWE',
	'RVU': 'NLD',
	'Jupiter Broadcasting ': 'USA',
	'TWiT': 'USA',
	'Smithsonian Channel': 'USA',
	'Discovery HD World': 'SGP',
	'Discovery Turbo UK': 'GBR',
	'Discovery Turbo': 'USA',
	'Discovery Science': 'USA',
	'FOX Traveller': 'IND',
	'DDR1': 'DEU',
	'G4 Canada': 'CAN',
	'H2': 'USA',
	'TV3 (NO)': 'NOR',
	'TG4': 'IRL',
	'Sky Arts': 'GBR',
	'ABC1': 'AUS',
	'ABC2': 'AUS',
	'ABC3': 'AUS',
	'ABC4Kids': 'AUS',
	'ABC News 24': 'AUS',
	'Fuel TV': 'USA',
	'RT': 'RUS',
	'Russia Today': 'RUS',
	'Télé-Québec': 'CAN',
	'FOX (FI)': 'FIN',
	'C31': 'AUS',
	'La7': 'ITA',
	'LaSexta': 'ITA',
	'Cuatro': 'ESP',
	'YouTube': 'USA',
	'TNT Serie': 'DEU',
	'TFO': 'CAN',
	'TVA': 'CAN',
	'Slice': 'CAN',
	'IKON': 'NLD',
	'KBS TV1': 'KOR',
	'KBS TV2': 'KOR',
	'KBS World': 'KOR',
	'FOX SPORTS': 'AUS',
	'City': 'CAN',
	'tvN': 'KOR',
	'Sky Atlantic': 'GBR',
	'Pick TV': 'GBR',
	'Niconico': 'JPN',
	'W9': 'FRA',
	'Antenne 2': 'FRA',
	'SET TV': 'TWN',
#	'Channel 5': 'GBR',
	'Oasis HD': 'CAN',
	'eqhd': 'CAN',
	'radX': 'CAN',
	'HIFI': 'CAN',
	'La Une': 'BEL',
	'La Deux': 'BEL',
	'La Trois': 'BEL',
	'RTL TVI': 'BEL',
	'Club RTL': 'BEL',
	'Plug RTL': 'BEL',
	'SBT': 'BRA',
	'Multishow': 'BRA',
	'Audience Network': 'USA',
	'Sky Uno': 'ITA',
	'Cielo': 'ITA',
	'VIER': 'BEL',
	'2BE': 'BEL',
	'Tele 5': 'DEU',
	'Hulu': 'USA',
	'Star TV': 'TUR',
	'Show TV': 'TUR',
	'Kanal D': 'TUR',
	'Rooster Teeth': 'USA',
	'here!': 'USA',
	'Prime (BE)': 'BEL',
	'laSexta': 'ESP',
	'GNT': 'BRA',
	'NT1': 'FRA',
	'NBCSN': 'USA',
	'Destination America': 'USA',
	'ARTV': 'CAN',
	'Yahoo! Screen': 'USA',
	'Duna TV': 'HUN',
	'Hír TV': 'HUN',
	'National Geographic Adventure': 'USA',
	'Nat Geo Wild': 'USA',
	'More4': 'GBR',
	'National Geographic (UK)': 'GBR',
	'TV Aichi': 'JPN',
	'FTV': 'TWN',
	'CTV (CN)': 'CHN',
	'DR3': 'DNK',
	'Sky Cinema (IT)': 'ITA',
	'TV Cultura': 'BRA',
	'MTV Italia': 'ITA',
	'TV3 (IE)': 'IRL',
	'EinsPlus': 'DEU',
	'TRT 1': 'TUR',
	'RTL': 'LUX',
	'ATV Türkiye': 'TUR',
	'RCN TV': 'COL',
	'Caracol TV': 'COL',
	'Venevision': 'VEN',
	'Televen': 'VEN',
	'RCTV': 'VEN',
	'Hrvatska radiotelevizija': 'HRV',
	'tvk': 'JPN',
	'Amazon': 'USA',
	'MBC Plus Media': 'KOR',
	'MBN': 'KOR',
	'CGV': 'KOR',
	'OCN': 'KOR',
	'Fox Channel': 'DEU',
	'Ustream': 'USA',
	'BTV': 'CHN',
	'Mnet': 'KOR',
	'Australian Christian Channel': 'AUS',
	'The Africa Channel': 'GBR',
	'Esquire Network': 'USA',
	'ORF III': 'AUT',
	'Nolife': 'FRA',
	'TestTube': 'USA',
	'jTBC': 'KOR',
	'Hunan TV': 'CHN',
	'La Cinq': 'FRA',
	'AlloCiné': 'FRA',
	'FXX': 'USA',
	'BBC ALBA': 'GBR',
	'TVGN': 'USA',
	'SABC1': 'ZAF',
	'SABC2': 'ZAF',
	'SABC3': 'ZAF',
	'SoHo': 'AUS',
	'TheBlaze': 'USA',
	'Comedy (CA)': 'CAN',
	'MTV (UK)': 'GBR',
	'TV One (US)': 'USA',
	'Crackle': 'USA',
	'Nick Jr.': 'USA',
	'Gulli': 'FRA',
	'Canal J': 'FRA',
	'Syndication': 'USA',
	'FOX Sports 1': 'USA',
	'FOX Sports 2': 'USA',
	'Chérie 25': 'FRA',
	'NOS': 'NLD',
	'Colors': 'IND',
	'Omroep MAX': 'NLD',
	'PowNed': 'NLD',
	'WNL': 'NLD',
	'The Verge': 'USA',
	'WGN America': 'USA',
	'Adult Swim': 'USA',
	'Super Channel': 'CAN',
	'RLTV': 'USA',
	'W Network': 'CAN',
	'PTS': 'TWN',
	'PTS HD': 'TWN',
	'Hakka TV': 'TWN',
	'TITV': 'TWN',
	'CTS': 'TWN',
	'CTi TV': 'TWN',
	'ETTV': 'TWN',
	'ETTV Yoyo': 'TWN',
	'GTV': 'TWN',
	'MTV Mandarin': 'TWN',
	'NTV (TW)': 'TWN',
	'SET Metro': 'TWN',
	'STAR Chinese Channel': 'TWN',
	'TTV': 'TWN',
	'TVBS Entertainment Channel': 'TWN',
	'Videoland Television Network': 'TWN',
	'DaAi TV': 'TWN',
	'Much TV': 'TWN',
	'Aizo TV': 'TWN',
	'STV (TW)': 'TWN',
	'Nou 24': 'ESP',
	'Nou Televisió': 'ESP',
	'Teletama': 'JPN',
	'Toei Channel': 'JPN',
	'CTV (JP)': 'JPN',
	'VOX': 'DEU',
	'El Rey Network': 'USA',
	'Sky Living': 'GBR',
	'Channel 3': 'THA',
	'Kampüs TV': 'TUR',
	'Life OK': 'IND',
	'Canal Once': 'MEX',
	'Food Network Canada': 'CAN',
	'Al Jazeera America': 'USA',
	'HGTV Canada': 'CAN',
	'Discovery Shed': 'GBR',
	'Pivot': 'USA',
#	'TVN': 'CHL',
	'Canal 13': 'CHL',
	'MavTV': 'USA',
	'Great American Country': 'USA',
	'D8': 'FRA',
	'BNN': 'CAN',
	'Crime & Investigation Network': 'USA',
	'CSTV': 'KOR',
	'TrueVisions': 'THA',
	'LMN': 'USA',
	'Jeuxvideo.com': 'FRA',
	'Thames Television': 'GBR',
	'Polsat': 'POL',
	'TVN Style': 'POL',
	'Arena': 'AUS',
	'AXS TV': 'USA',
	'TV One (NZ)': 'NZL',
	'TV2': 'NZL',
	'KCET': 'USA',
	'Omroep Brabant': 'NLD',
	'fuse': 'USA',
	'TSN': 'CAN',
	'El Trece': 'ARG',
	'Vimeo': 'USA',
	'Xbox Video': 'USA',
	'FEARnet': 'USA',
	'Channel 7': 'THA',
	'AHC': 'USA',
	'FOX Türkiye': 'TUR',
	'RTBF': 'BEL',
	'Ora TV': 'USA',
	'Discovery MAX': 'ESP',
	'DMAX (IT)': 'ITA',
	'ITV Wales': 'GBR',
	'OCS': 'FRA',
	'vtmKzoom': 'BEL',
	'TVO': 'CAN',
	'Televisión de Galicia': 'ESP',
	'RTL Klub': 'HUN',
	'Showcase (AU)': 'AUS',
	'Canal Sur': 'ESP',
	'RTL Televizija': 'HRV',
	'Discovery Channel (Asia)': 'SGP',
	'Lifetime UK': 'GBR',
	'TSR': 'CHE',
	'RTS Un': 'CHE',
	'SRF 1': 'CHE',
	'Maori Television': 'NZL',
	'MusiquePlus': 'CAN',
	'Spektrum': 'HUN',
	'Disney Channel (Germany)': 'DEU',
	'TeleZüri': 'CHE',
	'3+': 'CHE',
	'MBC Every1': 'KOR',
	'Sportsman Channel': 'USA',
	'Anhui TV': 'CHN',
	'Dragon TV': 'CHN',
	'Jiangsu TV': 'CHN',
	'Zhejiang TV': 'CHN',
	'TVS China': 'CHN',
	'NECO': 'JPN',
	'ART TV': 'GRC',
	'Epsilon TV': 'GRC',
	'Skai': 'GRC',
	'TV São Carlos': 'BRA',
	'TBN (Trinity Broadcasting Network)': 'USA',
	'Bounce TV': 'USA',
	'HLN': 'USA',
	'APTN': 'CAN',
	'Omni': 'CAN',
	'addikTV': 'CAN',
	'Centric': 'USA',
	'ICI Tou.tv': 'CAN',
	'RDI': 'CAN',
	'TV Osaka': 'JPN',
	'PlayStation Network': 'USA',
	'ICI Explora': 'CAN',
	'MBC Drama': 'KOR',
	'Sky Deutschland': 'DEU',
	'AOL': 'USA',
	'Channel 2': 'ISR',
	'DRAMAcube': 'KOR',
	'Community Channel': 'GBR',
	'This TV': 'USA',
	'Nagoya Broadcasting Network': 'JPN',
	'M-Net': 'ZAF',
	'NFL Network': 'USA',
	'Pop': 'USA',
	'Super!': 'ITA',
	'Cartoon Network Australia': 'AUS',
	'Canadian Learning Television': 'CAN',
	'Oprah Winfrey Network': 'USA',
	'Alpha TV': 'GRC',
	'TV Net': 'TUR',
	'TRT Kurdî': 'TUR',
	'Kanal A (Turkey)': 'TUR',
	'TRT HD': 'TUR',
	'TRT Haber': 'TUR',
	'TRT Belgesel': 'TUR',
	'TRT World': 'TUR',
	'360': 'TUR',
	'TRT Türk': 'TUR',
	'TRT Çocuk': 'TUR',
	'TRT Avaz': 'TUR',
	'TRT Arabic': 'TUR',
	'TRT Diyanet': 'TUR',
	'TRT Okul': 'TUR',
	'Cine 5': 'TUR',
	'Dost TV': 'TUR',
	'24': 'TUR',
	'Semerkand TV': 'TUR',
	'A Haber': 'TUR',
	'Kanal 7': 'TUR',
	'Ülke TV': 'TUR',
	'TGRT Haber': 'TUR',
	'Beyaz TV': 'TUR',
	'Lâlegül TV': 'TUR',
	'HBO Nordic': 'SWE',
	'Bandai Channel': 'JPN',
	'Sixx': 'DEU',
	'element14': 'USA',
	'HBO Magyarország': 'HUN',
	'HBO Europe': 'HUN',
	'HBO Latin America': 'BRA',
	'Canal Off': 'BRA',
	'ETV': 'EST',
	'Super Écran': 'CAN',
	'Discovery Life': 'USA',
	'The Family Channel': 'USA',
	'Fox Family': 'USA',
	'Canal 9 (AR)': 'ARG',
	'B92': 'SRB',
	'Ceskoslovenská televize': 'CZE',
	'CNNI': 'USA',
	'Channel 101': 'USA',
	'Canal 5': 'MEX',
	'MyNetworkTV': 'USA',
	'Blip': 'USA',
	'WPIX': 'USA',
	'Canal Famille': 'CAN',
	'Canal D': 'CAN',
	'Évasion': 'CAN',
	'DIY Network Canada': 'CAN',
	'Much (CA)': 'CAN',
	'MTV Brazil': 'BRA',
	'UKTV Yesterday': 'GBR',
	'Swearnet': 'CAN',
	'Dailymotion': 'USA',
	'RMC Découverte': 'FRA',
	'Discovery Family': 'USA',
	'SBS Plus': 'KOR',
	'Olive': 'KOR',
	'NAVER tvcast': 'KOR',
	'BBC iPlayer': 'GBR',
	'E-Channel': 'KOR',
	'Pakapaka': 'ARG',
	'Trend E': 'KOR',
	'MBC Queen': 'KOR',
	'iQiyi': 'CHN',
	'CW Seed': 'USA',
	'Rede Bandeirantes': 'BRA',
	'NBA TV': 'USA',
	'ITVBe': 'GBR',
	'Comedy Central (UK)': 'GBR',
	'NRJ 12': 'FRA',
	'Gaiam TV ': 'USA',
	'STAR One': 'IND',
	'Canal de las Estrellas': 'MEX',
	'TVQ (Japan)': 'JPN',
	'TVQ (Australia)': 'AUS',
	'UP TV': 'USA',
	'Universal Channel': 'BRA',
	'Golf Channel': 'USA',
	'CITV': 'GBR',
	'SKY PerfecTV!': 'JPN',
	'Disney Junior': 'USA',
	'Mondo TV': 'ITA',
	'téva': 'FRA',
	'MCM': 'FRA',
	'June': 'FRA',
	'Comédie !': 'FRA',
	'Comédie+': 'FRA',
	'Filles TV': 'FRA',
	'Discovery Channel (Australia)': 'AUS',
	'FOX (UK)': 'GBR',
	'Disney Junior (UK)': 'GBR',
	'n-tv': 'DEU',
	'OnStyle': 'KOR'
	}


def getDB():
	return DB_Functions(join(aelGlobals.CONFIGPATH, "eventLibrary.db")) if config.plugins.AdvancedEventLibrary.dbFolder.value == 1 else DB_Functions(join(getPictureDir(), "eventLibrary.db"))


def load_json(filename):
	with open(filename, 'r') as f:
		data = f.read().replace('null', '""')
	return eval(data)


def randbelow(exclusive_upper_bound):
	if exclusive_upper_bound <= 0:
		return 0
	return SystemRandom()._randbelow(exclusive_upper_bound)


def get_keys(forwhat):
	tmdbkey = config.plugins.AdvancedEventLibrary.tmdbKey.value
	tvdbkey = config.plugins.AdvancedEventLibrary.tvdbKey.value
	omdbKey = config.plugins.AdvancedEventLibrary.omdbKey.value
	if forwhat == 'tmdb' and tmdbkey != _("internal"):
		return tmdbkey
	elif forwhat == 'tvdb' and tvdbkey != _("internal"):
		return tvdbkey
	elif forwhat == 'omdb' and omdbKey != _("internal"):
		return omdbKey
	else:
		return b64decode(ApiKeys[forwhat][randbelow(3)]).decode()


def get_TVDb():
	tvdbV4Key = config.plugins.AdvancedEventLibrary.tvdbV4Key.value
	if tvdbV4Key != _("unused"):
		tvdbV4 = tvdb_api_v4.TVDB(tvdbV4Key)
		if tvdbV4.get_login_state():
			return tvdbV4


def convert2base64(title):
#	TODO: Kann nach den Tests weg
#	if title.find('(') > 1:
#		return b64encode(title.lower().encode().split(b'(')[0].strip()).replace(b'/', b'').decode('utf-8')
#	return b64encode(title.lower().strip().encode()).replace(b'/', b'').decode('utf-8')
	if title.find('(') > 1:
		return b64encode(title.lower().split("(")[0].strip().replace("/", "").encode()).decode()
	return b64encode(title.lower().strip().replace("/", "").encode()).decode()


def convertSigns(text):
#	TODO: Kann nach den Tests weg
#	text = text.replace('\xc3\x84', '\xc4').replace('\xc3\x96', '\xd6').replace('\xc3\x9c', '\xdc').replace('\xc3\x9f', '\xdf').replace('\xc3\xa4', '\xe4').replace('\xc3\xb6', '\xf6').replace('\xc3\xbc', '\xfc').replace('&', '%26').replace('\xe2\x80\x90', '-').replace('\xe2\x80\x91', '-').replace('\xe2\x80\x92', '-').replace('\xe2\x80\x93', '-')
	text = text.replace('\xe2\x80\x90', '-').replace('\xe2\x80\x91', '-').replace('\xe2\x80\x92', '-').replace('\xe2\x80\x93', '-')
	return text


def createDirs(path):
	path = str(path).replace('poster/', '').replace('cover/', '')
	if not path.endswith('/'):
		path = path + '/'
	if not path.endswith('AdvancedEventLibrary/'):
		path = path + 'AdvancedEventLibrary/'
	if not exists(path):
		makedirs(path)
	if not exists(path + 'poster/'):
		makedirs(path + 'poster/')
	if not exists(path + 'cover/'):
		makedirs(path + 'cover/')
	if not exists(path + 'preview/'):
		makedirs(path + 'preview/')
	if not exists(path + 'cover/thumbnails/'):
		makedirs(path + 'cover/thumbnails/')
	if not exists(path + 'preview/thumbnails/'):
		makedirs(path + 'preview/thumbnails/')
	if not exists(path + 'poster/thumbnails/'):
		makedirs(path + 'poster/thumbnails/')


def getPictureDir():
	return dir


def removeExtension(ext):
	return ext.replace('.wmv', '').replace('.mpeg2', '').replace('.ts', '').replace('.m2ts', '').replace('.mkv', '').replace('.avi', '').replace('.mpeg', '').replace('.mpg', '').replace('.iso', '').replace('.mp4', '')


def getMemInfo(value):
	result = [0, 0, 0, 0]  # (size, used, avail, use%)
	check = 0
	with open("/proc/meminfo") as fd:
		for line in fd:
			if value + "Total" in line:
				check += 1
				result[0] = int(line.split()[1]) * 1024		# size
			elif value + "Free" in line:
				check += 1
				result[2] = int(line.split()[1]) * 1024		# avail
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
		while (value >= 1024) and (u < len(SIZE_UNITS)):
			(value, mod) = divmod(value, 1024)
			fractal = mod * 10 / 1024
			u += 1
	else:
		fmt = "%(size)u %(unit)s"
	return fmt % {"size": value, "frac": fractal, "unit": SIZE_UNITS[u]}


def clearMem(screenName=""):
	aelGlobals.write_log(str(screenName) + ' - Speicherauslastung vor Bereinigung : ' + str(getMemInfo('Mem')))
	system('sync')
	system('sh -c "echo 3 > /proc/sys/vm/drop_caches"')
	aelGlobals.write_log(str(screenName) + ' - Speicherauslastung nach Bereinigung : ' + str(getMemInfo('Mem')))


def createBackup():
	global STATUS
	backuppath = config.plugins.AdvancedEventLibrary.Backup.value
	STATUS = f"erzeuge Backup in {backuppath}"
	aelGlobals.write_log(f"create backup in {backuppath}")
	for currpath in [backuppath, f"{backuppath}poster/", f"{backuppath}cover/"]:
		if not exists(currpath):
			makedirs(currpath)
	dbpath = join(aelGlobals.CONFIGPATH, "eventLibrary.db") if config.plugins.AdvancedEventLibrary.dbFolder.value == 1 else join(getPictureDir(), 'eventLibrary.db')
	if fileExists(dbpath):
		copy2(dbpath, join(backuppath, 'eventLibrary.db'))
	files = glob(getPictureDir() + 'poster/*.jpg')
	progress = 0
	pics = len(files)
	copied = 0
	for file in files:
		progress += 1
		target = join(f"{backuppath}poster/", basename(file))
		if not fileExists(target) or getmtime(file) > (getmtime(target) + 7200):
			copy2(file, target)
			STATUS = f"({progress}/{pics} sichere Poster : {file}"
			copied += 1
	aelGlobals.write_log(f"have copied {copied} poster to {backuppath} poster/")
	del files
	files = glob(getPictureDir() + 'poster/*.jpg')
	progress = 0
	pics = len(files)
	copied = 0
	for file in files:
		progress += 1
		target = join(f"{backuppath}cover/", basename(file))
		if not fileExists(target) or getmtime(file) > getmtime(target):
			copy2(file, target)
			STATUS = f"({progress}/{pics}) sichere Cover : {file}"
			copied += 1
	aelGlobals.write_log(f"have copied {copied} cover to {backuppath}cover/")
	del files
	STATUS = None
	clearMem("createBackup")
	aelGlobals.write_log("backup finished")


def checkUsedSpace(db=None):
	recordings = getRecordings()
	dbpath = join(aelGlobals.CONFIGPATH, "eventLibrary.db") if config.plugins.AdvancedEventLibrary.dbFolder.value == 1 else join(getPictureDir(), "eventLibrary.db")
	if fileExists(dbpath) and db:
		maxSize = 1 * 1024.0 * 1024.0 if "/etc" in dir else config.plugins.AdvancedEventLibrary.MaxSize.value * 1024.0 * 1024.0
		PDIR = f"{dir}poster/"
		CDIR = f"{dir}cover/"
		PRDIR = f"{dir}preview/"
		posterSize = float(check_output(['du', '-sk', PDIR]).split()[0])
		coverSize = float(check_output(['du', '-sk', CDIR]).split()[0])
		previewSize = float(check_output(['du', '-sk', PRDIR]).split()[0])
		inodes = check_output(['df', '-i', dir]).split()[-2].decode()
		aelGlobals.write_log(f"benutzte Inodes = {inodes}")
		aelGlobals.write_log(f"benutzter Speicherplatz = {(posterSize + coverSize)} kB von {maxSize} kB.")
		usedInodes = int(inodes[:-1])
		if (((int(posterSize) + int(coverSize) + int(previewSize)) > int(maxSize)) or usedInodes >= config.plugins.AdvancedEventLibrary.MaxUsedInodes.value):
			removeList = glob(join(PRDIR, "*.jpg"))
			for f in removeList:
				remove(f)
			i = 0
			while i < 100:
				titles = db.getUnusedTitles()
				if titles:
					aelGlobals.write_log(str(i + 1) + '. Bereinigung des Speicherplatzes.')
					for title in titles:
						if str(title[1]) not in recordings:
							for currdir in [f"{PDIR}{title[0]}", f"{PDIR}thumbnails/{title[0]}", f"{CDIR}{title[0]}", f"{CDIR}thumbnails/{title[0]}"]:
								for file in glob(f"{currdir}*.jpg"):
									remove(file)
								db.cleanDB(title[0])
					posterSize = float(check_output(['du', '-sk', PDIR]).split()[0])
					coverSize = float(check_output(['du', '-sk', CDIR]).split()[0])
					aelGlobals.write_log('benutzter Speicherplatz = ' + str(float(posterSize) + float(coverSize)) + ' kB von ' + str(maxSize) + ' kB.')
				if (posterSize + coverSize) < maxSize:
					break
				i += 1
			db.vacuumDB()
			aelGlobals.write_log(f"Used memory space = {float(posterSize) + float(coverSize)} kB of {maxSize} kB.")


def removeLogs():
	if fileExists(aelGlobals.LOGFILE):
		remove(aelGlobals.LOGFILE)


def startUpdate():
	thread = Thread(target=getallEventsfromEPG, args=())
	thread.start()


def createMovieInfo(db):
	global STATUS
	STATUS = _("search for missing meta files...")
	recordPaths = config.movielist.videodirs.value
	for recordPath in recordPaths:
		if isdir(recordPath):
			for root, directories, files in walk(recordPath):
				if isdir(root) and str(root) in sPDict and sPDict[root]:
					for filename in files:
						if not access(join(root, filename), W_OK):
							continue
						foundAsMovie = False
						foundOnTMDbTV = False
						foundOnTVDb = False
						if (filename.endswith('.ts') or filename.endswith('.mkv') or filename.endswith('.avi') or filename.endswith('.mpg') or filename.endswith('.mp4') or filename.endswith('.iso') or filename.endswith('.mpeg2')):
							if not db.getimageBlackList(removeExtension(str(filename))):
								if not fileExists(join(root, f"{filename}.meta")):
									title = convertSearchName(convertDateInFileName(((filename.split('/')[-1]).rsplit('.', 1)[0]).replace('__', ' ').replace('_', ' ')))
									mtitle = title
									titleNyear = convertYearInTitle(title)
									title = titleNyear[0]
									jahr = str(titleNyear[1])
									if title and title != '' and title != ' ':
										tmdb.API_KEY = get_keys('tmdb')
										titleinfo = {"title": mtitle, "genre": "", "year": "", "country": "", "overview": ""}
										STATUS = _("search meta information for %s") % title
										aelGlobals.write_log(STATUS, ADDLOG)
										search = tmdb.Search()
										res = search.movie(query=title, language='de', year=jahr) if jahr != '' else search.movie(query=title, language='de')
										if res and res['results']:
											reslist = []
											for item in res['results']:
												reslist.append(item['title'].lower())
											bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
											if not bestmatch:
												bestmatch = [title.lower()]
											for item in res['results']:
												if item['title'].lower() == bestmatch[0]:
													foundAsMovie = True
													titleinfo['title'] = item['title']
													if 'overview' in item:
														titleinfo['overview'] = item['overview']
													if 'release_date' in item:
														titleinfo['year'] = item['release_date'][:4]
													if item['genre_ids']:
														for genre in item['genre_ids']:
															if tmdb_genres[genre] not in titleinfo['genre']:
																titleinfo['genre'] = titleinfo['genre'] + tmdb_genres[genre] + ' '
														maxGenres = titleinfo['genre'].split()
														if maxGenres:
															if len(maxGenres) >= 1:
																titleinfo['genre'] = maxGenres[0]
													if 'id' in item:
														details = tmdb.Movies(item['id'])
														for country in details.info(language='de')['production_countries']:
															titleinfo['country'] = titleinfo['country'] + country['iso_3166_1'] + " | "
														titleinfo['country'] = titleinfo['country'][:-3]
													break
										if not foundAsMovie:
											search = tmdb.Search()
											searchName = findEpisode(title)
											if searchName:
												res = aelGlobals.callLibrary(search.tv, query=searchName[2], language='de', include_adult=True, search_type='ngram')
											else:
												res = aelGlobals.callLibrary(search.tv, query=title, language='de', include_adult=True, search_type='ngram')
											if res:
												if res['results']:
													reslist = []
													for item in res['results']:
														reslist.append(item['name'].lower())
													if searchName:
														bestmatch = get_close_matches(searchName[2].lower(), reslist, 1, 0.7)
														if not bestmatch:
															bestmatch = [searchName[2].lower()]
													else:
														bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
														if not bestmatch:
															bestmatch = [title.lower()]
													for item in res['results']:
														if item['name'].lower() == bestmatch[0]:
															foundOnTMDbTV = True
															if searchName:
																details = tmdb.TV_Episodes(item['id'], searchName[0], searchName[1])
																epi = details.info(language='de')
																#imgs = details.images(language='de')
																if 'name' in epi:
																	titleinfo['title'] = item['name'] + ' - S' + searchName[0] + 'E' + searchName[1] + ' - ' + epi['name']
																if 'air_date' in epi:
																	titleinfo['year'] = epi['air_date'][:4]
																if 'overview' in epi:
																	titleinfo['overview'] = epi['overview']
																if item['origin_country']:
																	for country in item['origin_country']:
																		titleinfo['country'] = titleinfo['country'] + country + ' | '
																	titleinfo['country'] = titleinfo['country'][:-3]
																if item['genre_ids']:
																	for genre in item['genre_ids']:
																		if tmdb_genres[genre] not in titleinfo['genre']:
																			titleinfo['genre'] = titleinfo['genre'] + tmdb_genres[genre] + '-Serie '
																	maxGenres = titleinfo['genre'].split()
																	if maxGenres:
																		if len(maxGenres) >= 1:
																			titleinfo['genre'] = maxGenres[0]
															else:
																titleinfo['title'] = item['name']
																if 'overview' in item:
																	titleinfo['overview'] = item['overview']
																if item['origin_country']:
																	for country in item['origin_country']:
																		titleinfo['country'] = titleinfo['country'] + country + ' | '
																	titleinfo['country'] = titleinfo['country'][:-3]
																if 'first_air_date' in item:
																	titleinfo['year'] = item['first_air_date'][:4]
																if item['genre_ids']:
																	for genre in item['genre_ids']:
																		if tmdb_genres[genre] not in titleinfo['genre']:
																			titleinfo['genre'] = titleinfo['genre'] + tmdb_genres[genre] + '-Serie '
																	maxGenres = titleinfo['genre'].split()
																	if maxGenres:
																		if len(maxGenres) >= 1:
																			titleinfo['genre'] = maxGenres[0]
															break
										if not foundAsMovie and not foundOnTMDbTV:
											tvdb.KEYS.API_KEY = get_keys('tvdb')
											search = tvdb.Search()
											seriesid = None
											ctitle = title
											title = convertTitle2(title)
											response = aelGlobals.callLibrary(search.series, title=title, language="de")
											if response:
												reslist = []
												for result in response:
													reslist.append(result['seriesName'].lower())
												bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
												if not bestmatch:
													bestmatch = [title.lower()]
												for result in response:
													if result['seriesName'].lower() == bestmatch[0]:
														seriesid = result['id']
														break
											if seriesid:
												foundOnTVDb = True
												show = tvdb.Series(seriesid)
												response = show.info()
												epis = tvdb.Series_Episodes(seriesid)
												episoden = None
												try:  # mandatory because the library raises an error when no result
													episoden = epis.all()
												except Exception:
													episoden = []
												if episoden:
													for episode in episoden:
														if str(episode['episodeName']) in str(ctitle):
															if 'firstAired' in episode:
																titleinfo['year'] = episode['firstAired'][:4]
																if 'overview' in episode:
																	titleinfo['overview'] = episode['overview']
															if response:
																searchName = findEpisode(title)
																titleinfo['title'] = response['seriesName'] + ' - S' + searchName[0] + 'E' + searchName[1] + ' - ' + episode['episodeName'] if searchName else response['seriesName'] + ' - ' + episode['episodeName']
																if titleinfo['genre'] == "":
																	for genre in response['genre']:
																		titleinfo['genre'] = titleinfo['genre'] + genre + '-Serie '
																titleinfo['genre'] = titleinfo['genre'].replace("Documentary", "Dokumentation").replace("Children", "Kinder")
																if titleinfo['country'] == "" and response['network'] in networks:
																	titleinfo['country'] = networks[response['network']]
																break
												else:
													if response:
														titleinfo['title'] = response['seriesName']
														if titleinfo['year'] == "":
															titleinfo['year'] = response['firstAired'][:4]
														if titleinfo['genre'] == "":
															for genre in response['genre']:
																titleinfo['genre'] = titleinfo['genre'] + genre + '-Serie '
														titleinfo['genre'] = titleinfo['genre'].replace("Documentary", "Dokumentation").replace("Children", "Kinder")
														if titleinfo['country'] == "":
															if response['network'] in networks:
																titleinfo['country'] = networks[response['network']]
														if 'overview' in response:
															titleinfo['overview'] = response['overview']
										if titleinfo['overview'] != "":
											txt = open(join(root, removeExtension(filename) + ".txt"), "w")
											txt.write(titleinfo['overview'])
											txt.close()
											aelGlobals.write_log('createMovieInfo for : ' + str(filename))
										if foundAsMovie or foundOnTMDbTV or foundOnTVDb:
											if titleinfo['year'] != "" or titleinfo['genre'] != "" or titleinfo['country'] != "":
												filedt = int(stat(join(root, filename)).st_mtime)
												txt = open(join(root, filename + ".meta"), "w")
												minfo = "1:0:0:0:B:0:C00000:0:0:0:\n" + str(titleinfo['title']) + "\n"
												if str(titleinfo['genre']) != "":
													minfo += str(titleinfo['genre']) + ", "
												if str(titleinfo['country']) != "":
													minfo += str(titleinfo['country']) + ", "
												if str(titleinfo['year']) != "":
													minfo += str(titleinfo['year']) + ", "
												if minfo.endswith(', '):
													minfo = minfo[:-2]
												else:
													minfo += "\n"
												minfo += "\n" + str(filedt) + "\nAdvanced-Event-Library\n"
												txt.write(minfo)
												txt.close()
												aelGlobals.write_log('create meta-Info for ' + str(join(root, filename)))
											else:
												db.addimageBlackList(removeExtension(str(filename)))
										else:
											db.addimageBlackList(removeExtension(str(filename)))
											aelGlobals.write_log('nothing found for ' + str(join(root, filename)))


def getAllRecords(db):
	global STATUS
	names = set()
	STATUS = "search recording directories..."
	PDIR = dir + 'poster/'
	CDIR = dir + 'cover/'
	recordPaths = config.movielist.videodirs.value
	doPics = False
	if "Pictures" in sPDict:
		if sPDict["Pictures"]:
			doPics = True
	else:
		doPics = True
	for recordPath in recordPaths:
		if isdir(recordPath):
			for root, directories, files in walk(recordPath):
				if isdir(root):
					fileCount = 0
					if str(root) in sPDict and sPDict[root]:
						name = ""
						for filename in files:
							if (filename.endswith('.ts') or filename.endswith('.mkv') or filename.endswith('.avi') or filename.endswith('.mpg') or filename.endswith('.mp4') or filename.endswith('.iso') or filename.endswith('.mpeg2')) and doPics:
								if fileExists(join(root, filename + '.meta')):
									fname = convertDateInFileName(getline(join(root, filename + '.meta'), 2).replace("\n", ""))
								else:
									fname = convertDateInFileName(convertSearchName(convertTitle(((filename.split('/')[-1]).rsplit('.', 3)[0]).replace('_', ' '))))
								searchName = filename + '.jpg'
								if (fileExists(join(root, searchName)) and not fileExists(PDIR + convert2base64(fname) + '.jpg')):
									aelGlobals.write_log('copy poster ' + str(searchName) + ' nach ' + str(fname) + ".jpg")
									copy2(join(root, searchName), PDIR + convert2base64(fname) + ".jpg")
								searchName = removeExtension(filename) + '.jpg'
								if (fileExists(join(root, searchName)) and not fileExists(PDIR + convert2base64(fname) + '.jpg')):
									aelGlobals.write_log('copy poster ' + str(searchName) + ' nach ' + str(fname) + ".jpg")
									copy2(join(root, searchName), PDIR + convert2base64(fname) + ".jpg")
								searchName = filename + '.bdp.jpg'
								if (fileExists(join(root, searchName)) and not fileExists(CDIR + convert2base64(fname) + '.jpg')):
									aelGlobals.write_log('copy cover ' + str(searchName) + ' nach ' + str(fname) + ".jpg")
									copy2(join(root, searchName), CDIR + convert2base64(fname) + ".jpg")
								searchName = removeExtension(filename) + '.bdp.jpg'
								if (fileExists(join(root, searchName)) and not fileExists(CDIR + convert2base64(fname) + '.jpg')):
									aelGlobals.write_log('copy cover ' + str(searchName) + ' nach ' + str(fname) + ".jpg")
									copy2(join(root, searchName), CDIR + convert2base64(fname) + ".jpg")
							if filename.endswith('.meta'):
								fileCount += 1
								foundInBl = False
								name = convertDateInFileName(getline(join(root, filename), 2).replace("\n", ""))
								if db.getblackList(convert2base64(name)):
									name = convertDateInFileName(convertTitle(getline(join(root, filename), 2).replace("\n", "")))
									if db.getblackList(convert2base64(name)):
										name = convertDateInFileName(convertTitle2(getline(join(root, filename), 2).replace("\n", "")))
										if db.getblackList(convert2base64(name)):
											foundInBl = True
								if not db.checkTitle(convert2base64(name)) and not foundInBl and name != '' and name != ' ':
									names.add(name)
							if (filename.endswith('.ts') or filename.endswith('.mkv') or filename.endswith('.avi') or filename.endswith('.mpg') or filename.endswith('.mp4') or filename.endswith('.iso') or filename.endswith('.mpeg2')) and doPics:
								foundInBl = False
								service = eServiceReference('1:0:0:0:0:0:0:0:0:0:' + join(root, filename)) if filename.endswith('.ts') else eServiceReference('4097:0:0:0:0:0:0:0:0:0:' + join(root, filename))
								info = eServiceCenter.getInstance().info(service)
								if info:
									name = removeExtension(info.getName(service))
									if name is None:
										name = convertDateInFileName(((filename.split('/')[-1]).rsplit('.', 1)[0]).replace('__', ' ').replace('_', ' '))
								else:
									name = convertDateInFileName(((filename.split('/')[-1]).rsplit('.', 1)[0]).replace('__', ' ').replace('_', ' '))
								if db.getblackList(convert2base64(name)):
									name = convertDateInFileName(convertTitle(((filename.split('/')[-1]).rsplit('.', 1)[0]).replace('__', ' ').replace('_', ' ')))
									if db.getblackList(convert2base64(name)):
										name = convertDateInFileName(convertTitle2(((filename.split('/')[-1]).rsplit('.', 1)[0]).replace('_', ' ')))
										if db.getblackList(convert2base64(name)):
											foundInBl = True
								if not db.checkTitle(convert2base64(name)) and not foundInBl and name != '' and name != ' ':
									names.add(name)
						aelGlobals.write_log('check ' + str(fileCount) + ' meta Files in ' + str(root))
				else:
					aelGlobals.write_log('recordPath ' + str(root) + ' is not exists')
		else:
			aelGlobals.write_log('recordPath ' + str(recordPath) + ' is not exists')
	aelGlobals.write_log('found ' + str(len(names)) + ' new Records in meta Files')
#		check vtidb
		#doIt = False
		#if "VTiDB" in sPDict:
		#	if sPDict["VTiDB"]:
		#		doIt = True
		#else:
		#	doIt = True
		#if (fileExists(vtidb_loc) and doIt):
		#	STATUS = 'durchsuche VTI-DB...'
		#	vtidb_conn = connect(vtidb_loc, check_same_thread=False)
		#	cur = vtidb_conn.cursor()
		#	query = "SELECT title FROM moviedb_v0001"
		#	cur.execute(query)
		#	rows = cur.fetchall()
		#	if rows:
		#		aelGlobals.write_log('check ' + str(len(rows)) + ' titles in vtidb')
		#		for row in rows:
		#			try:
		#				if row[0] and row[0] != '' and row[0] != ' ':
		#					foundInBl = False
		#					name = convertTitle(row[0])
		#					if db.getblackList(convert2base64(name)):
		#						name = convertTitle2(row[0])
		#						if db.getblackList(convert2base64(name)):
		#							foundInBl = True
		#					if not db.checkTitle(convert2base64(name)) and not foundInBl:
		#						names.add(name)
		#			except Exception as ex:
		#				aelGlobals.write_log("Error in getAllRecords vtidb: " + str(row[0]) + ' - ' + str(ex))
		#				continue
		#aelGlobals.write_log('found ' + str(len(names)) + ' new Records')
	return names


def getRecordings():
	names = set()
	recordPaths = config.movielist.videodirs.value
	doPics = False
	for recordPath in recordPaths:
		if isdir(recordPath):
			for root, directories, files in walk(recordPath):
				if isdir(root) and str(root) in sPDict and sPDict[root]:
					name = ""
					for filename in files:
						if filename.endswith('.meta'):
							name = convertDateInFileName(getline(join(root, filename), 2).replace("\n", ""))
							names.add(convert2base64(name))
							names.add(convert2base64(convertDateInFileName(convertTitle(name))))
							names.add(convert2base64(convertDateInFileName(convertTitle2(name))))
						if (filename.endswith('.ts') or filename.endswith('.mkv') or filename.endswith('.avi') or filename.endswith('.mpg') or filename.endswith('.mp4') or filename.endswith('.iso') or filename.endswith('.mpeg2')) and doPics:
							name = convertDateInFileName(((filename.split('/')[-1]).rsplit('.', 1)[0]).replace('__', ' ').replace('_', ' '))
							names.add(convert2base64(name))
							names.add(convert2base64(convertDateInFileName(convertTitle(name))))
							names.add(convert2base64(convertDateInFileName(convertTitle2(name))))
							service = eServiceReference('1:0:0:0:0:0:0:0:0:0:' + join(root, filename)) if filename.endswith('.ts') else eServiceReference('4097:0:0:0:0:0:0:0:0:0:' + join(root, filename))
							info = eServiceCenter.getInstance().info(service)
							name = info.getName(service)
							names.add(convert2base64(name))
							names.add(convert2base64(convertDateInFileName(convertTitle(name))))
							names.add(convert2base64(convertDateInFileName(convertTitle2(name))))
	return names


def cleanPreviewImages(db):
	recImages = getRecordings()
	prevImages = db.getUnusedPreviewImages(int(time() - 28800))
	ic = 0
	it = 0
	for image in prevImages:
		if convert2base64(image) not in recImages:
			img = dir + 'preview/' + convert2base64(image) + '.jpg'
			if fileExists(img):
				remove(img)
				ic += 1
			img = dir + 'preview/thumbnails/' + convert2base64(image) + '.jpg'
			if fileExists(img):
				remove(img)
				it += 1
		else:
			aelGlobals.write_log("can't remove " + str(image) + ", because it's a record")
	aelGlobals.write_log('have removed ' + str(ic) + ' preview images')
	aelGlobals.write_log('have removed ' + str(it) + ' preview thumbnails')
	del recImages
	del prevImages


def getallEventsfromEPG():
	global STATUS
	STATUS = "überprüfe Verzeichnisse..."
	createDirs(dir)
	STATUS = "entferne Logfile..."
	removeLogs()
	aelGlobals.write_log("Update start...")
	aelGlobals.write_log("default image path is " + str(dir)[:-1])
#	aelGlobals.write_log("load preview images is: " + str(config.plugins.AdvancedEventLibrary.UsePreviewImages.value))
	aelGlobals.write_log("searchOptions " + str(sPDict))
	db = getDB()
	db.parameter(PARAMETER_SET, 'laststart', str(time()))
	cversion = db.parameter(PARAMETER_GET, 'currentVersion', None, 111)
	if cversion and int(cversion) < 113:
		db.parameter(PARAMETER_SET, 'currentVersion', '115')
		db.cleanliveTV(int(time() + (14 * 86400)))
	STATUS = "überprüfe reservierten Speicherplatz..."
	checkUsedSpace(db)
	names = getAllRecords(db)
	STATUS = "search current EPG..."
	lines = []
	mask = (eServiceReference.isMarker | eServiceReference.isDirectory)
	root = eServiceReference(str(service_types_tv + ' FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
	serviceHandler = eServiceCenter.getInstance()
	tvbouquets = serviceHandler.list(root).getContent("SN", True)
	jsonfile = join(aelGlobals.CONFIGPATH, "tvs_reflist.json")
	tvsref = load_json(jsonfile) if fileExists(jsonfile) else {}
	aelGlobals.write_log(f"TV Spielfilm mapping file '{jsonfile}' successfully loaded" if jsonfile else f"WARNING: could not find TV Spielfilm mapping file '{jsonfile}'")
	for bouquet in tvbouquets:
		root = eServiceReference(str(bouquet[0]))
		serviceHandler = eServiceCenter.getInstance()
		ret = serviceHandler.list(root).getContent("SN", True)
		isInsPDict = bouquet[1] in sPDict
		if not isInsPDict or (isInsPDict and sPDict[bouquet[1]]):
			for (serviceref, servicename) in ret:
				playable = not (eServiceReference(serviceref).flags & mask)
				if playable and "p%3a" not in serviceref and "<n/a>" not in servicename and servicename != "." and not serviceref.startswith('4097'):
					if serviceref not in tvsref:
						aelGlobals.write_log(f"'{servicename}' with reference '{serviceref}' could not be found in the TVS reference list!'")
					line = [serviceref, servicename]
					if line not in lines:
						lines.append(line)
	test = ["RITB", 0]
	for line in lines:
		test.append((line[0], 0, int(time() + 1000), -1))
	aelGlobals.write_log(f"debug test: {test}")
	epgcache = eEPGCache.getInstance()
	allevents = epgcache.lookupEvent(test) or []
	aelGlobals.write_log(f"found {len(allevents)} Events in EPG")
	evt = 0
	liveTVRecords = []
	for serviceref, eid, name, begin in allevents:
		evt += 1
		STATUS = f"search current EPG... ({evt}/{len(allevents)})"
		tvname = name
		tvname = sub(r'\\(.*?\\)', '', tvname).strip()
		tvname = sub(r' +', ' ', tvname)
		#if not db.checkliveTV(eid, serviceref) and str(tvname) not in excludeNames and not 'Invictus' in str(tvname):
		minEPGBeginTime = time() - 7200  # -2h
		maxEPGBeginTime = time() + 1036800  # 12Tage
		if begin > minEPGBeginTime and begin < maxEPGBeginTime:
			if not db.checkliveTV(eid, serviceref):
				if str(tvname) not in excludeNames and 'Invictus' not in str(tvname):
					record = (eid, 'in progress', '', '', '', '', '', tvname, begin, '', '', '', '', '', '', '', '', serviceref)
					liveTVRecords.append(record)
		foundInBl = False
		name = convertTitle(name)
		if db.getblackList(convert2base64(name)):
			name = convertTitle2(name)
			if db.getblackList(convert2base64(name)):
				foundInBl = True
		if not db.checkTitle(convert2base64(name)) and not foundInBl:
			names.add(name)
	aelGlobals.write_log(f"check {len(names)} new events")
	limgs = False if config.plugins.AdvancedEventLibrary.SearchFor.value == 1 else True  # "Extra data only"
	get_titleInfo(names, None, limgs, db, liveTVRecords, tvsref)
	del names
	del lines
	del allevents
	del liveTVRecords


def getTVSpielfilm(db, tvsref):
	global STATUS
	evt = 0
	founded = 0
	imgcount = 0
	trailers = 0
	coverDir = f"{getPictureDir()}preview/"
	refs = db.getSrefsforUpdate()
	tcount = db.getUpdateCount()
	if refs and tvsref:
		for sref in refs:
			if sref in tvsref:
				evt += 1
				maxDate = db.getMaxAirtimeforUpdate(sref)
				curDate = db.getMinAirtimeforUpdate(sref)
				while (int(curDate) - 86400) <= int(maxDate) + 86400:  # while int(curDate) <= int(maxDate) + 86400:
					curDatefmt = datetime.fromtimestamp(curDate).strftime("%Y-%m-%d")
					STATUS = f"({evt}/{len(refs)}) durchsuche {tvsref[sref]} für den {curDatefmt} auf TV-Spielfilm ({founded}/{tcount} | {imgcount})"
#					Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
#					Beispiel: https://live.tvspielfilm.de/static/broadcast/list/ARD/2020-06-11
#					unkodierte URL: https://live.tvspielfilm.de/static/broadcast/list/
					url = b64decode(b"aHR0cHM6Ly9saXZlLnR2c3BpZWxmaWxtLmRlL3N0YXRpYy9icm9hZGNhc3QvbGlzdC8=7"[:-1]).decode()
					errmsg, res = aelGlobals.getAPIdata(f"{url}{tvsref[sref].upper()}/{curDatefmt}")
					if errmsg:
						aelGlobals.write_log("[{DEFAULT_MODULE_NAME}] API download error in module 'getTVSpielfilm'")
					if res:
						lastImage = ""
						fulltext = {"U": _("Entertainment"), "SE": _("Series"), "SPO": _("Sport"), "SP": _("Movie"), "KIN": _("Children"), "RE": _("Reportage"), "AND": _("Other")}
						for event in res:
							airtime = event.get("timestart", 0)
							eid = event.get("id", "")
							title = event.get("title", "")
							subtitle = event.get("episodeTitle", "")
							image = event.get("images", [{}]).get(0, {}).get("size4")[0]
							year = event.get("year", "")
							fsk = event.get("fsk", "")
							leadText = event.get("preview", "")
							conclusion = event.get("conclusion", "")
							categoryName = fulltext.get(event.get("sart_id", ""), "")
							season = event.get("seasonNumber", 0)
							episode = event.get("episodeNumber", "")
							episode = episode.split('/')[0] if '/' in episode else episode
							genre = event.get("genre", "")
							country = event.get("country", "").replace('/', ' | ')
							ratingPoints, ratingAmount = 0, 0
							for ratingkey in ["ratingAction", "ratingDemanding", "ratingErotic", "ratingHumor", "ratingSuspense"]:
								currrating = event.get(ratingkey, 0)
								ratingPoints += int(currrating * 3.33)
								ratingAmount += 1
							rating = str(round(float(ratingPoints / ratingAmount), 1)) if ratingAmount else 0
							imdb = event.get("videos", [{}]).get(0, {}).get("video", [{}]).get(0, {}).get("url", [{}])
							if imdb and db.checkTitle(convert2base64(title)):
								db.updateTrailer(imdb, convert2base64(title))
							if not db.checkTitle(convert2base64(title)) and categoryName == "Spielfilm":
								db.addTitleInfo(convert2base64(title), title, genre, year, rating, fsk, country, imdb)
							if db.checkTitle(convert2base64(title)):
								data = db.getTitleInfo(convert2base64(title))
								if genre and data[2]:
									db.updateSingleEventInfo('genre', genre, convert2base64(title))
								if year and data[3]:
									db.updateSingleEventInfo('year', year, convert2base64(title))
								if rating and data[4]:
									db.updateSingleEventInfo('rating', rating, convert2base64(title))
								if fsk and data[5]:
									db.updateSingleEventInfo('fsk', fsk, convert2base64(title))
								if country and data[5]:
									db.updateSingleEventInfo('country', country, convert2base64(title))
							bld = ""
							if image and config.plugins.AdvancedEventLibrary.SearchFor.value != 1 and config.plugins.AdvancedEventLibrary.UsePreviewImages.value:
								bld = image
								imgname = title + ' - '
								if season:
									imgname += f"S{season.zfill(2)}"
								if episode:
									imgname += f"E{episode.zfill(2)} - "
								if subtitle != "":
									imgname += f"{subtitle} - "
								image = imgname[:-3]
							success = founded
							db.updateliveTVS(eid, subtitle, image, year, fsk, rating, leadText, conclusion, categoryName, season, episode, genre, country, imdb, sref, airtime, title)
							founded = tcount - db.getUpdateCount()
							if founded == success:
								aelGlobals.write_log('no matches found for ' + str(title) + ' on ' + tvsref[sref] + ' at ' + str(datetime.fromtimestamp(airtime).strftime("%d.%m.%Y %H:%M:%S")) + ' with TV-Spielfilm ', ADDLOG)
							if founded > success and imdb != "":
								trailers += 1
							if founded > success and bld != "" and config.plugins.AdvancedEventLibrary.SearchFor.value != 1 and config.plugins.AdvancedEventLibrary.UsePreviewImages.value and str(image) != str(lastImage):
								if len(convert2base64(image)) < 255:
									imgpath = f"{coverDir}{convert2base64(image)}.jpg"
									if downloadTVSImage(bld, imgpath):
										imgcount += 1
										lastImage = image
					curDate = curDate + 86400
	aelGlobals.write_log(f"have updated {founded} events from TV-Spielfilm")
	aelGlobals.write_log(f"have downloaded {imgcount} images from TV-Spielfilm")
	aelGlobals.write_log(f"have found {trailers} trailers on TV-Spielfilm")
	db.parameter(PARAMETER_SET, f"lastpreviewImageCount {imgcount}")


def getTVMovie(db, secondRun=False):
	global STATUS
	evt = 0
	founded = 0
	imgcount = 0
	coverDir = f"{getPictureDir()}preview/"
	failedNames = []
	tcount = db.getUpdateCount()
	if not secondRun:
		tvnames = db.getTitlesforUpdate()
		aelGlobals.write_log('check ' + str(len(tvnames)) + ' titles on TV-Movie')
	else:
		tvnames = db.getTitlesforUpdate2()
		for name in failedNames:
			tvnames.append(name)
		aelGlobals.write_log('recheck ' + str(len(tvnames)) + ' titles on TV-Movie')
	url = 0
	for title in tvnames:
		evt += 1
		if not secondRun:
			tvname = correctTitleName(title[0])
			for convName in convNames:
				if str(tvname).startswith(str(convName)):
					if str(tvname).startswith('Die Bergpolizei'):
						tvname = convertTitle2(tvname) + ' - Ganz nah am Himmel'
					else:
						tvname = convertTitle2(tvname)
		else:
			tvname = convertTitle2(title[0])
		results = None
		STATUS = f"({evt}/{len(tvnames)}) suche auf TV-Movie nach {tvname} ({founded}/{tcount} | {imgcount})"
#		Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
#		searchurl = 'http://capi.tvmovie.de/v1/broadcasts/search?q=%s&page=1&rows=400'
#		url = searchurl % quote(sub(r'[^0-9a-zA-Z-:!., ]+', '*', str(tvname)))#.lower())
#		url = searchurl % quote(str(tvname))  # .lower())
#		unkodierte URL: http://capi.tvmovie.de/v1/broadcasts/search
		url = b64decode(b"aHR0cDovL2NhcGkudHZtb3ZpZS5kZS92MS9icm9hZGNhc3RzL3NlYXJjaA==2"[:-1]).decode
		errmsg, res = aelGlobals.getAPIdata(url, params={"q": tvname, "page": 1, "rows": 400})
		if errmsg:
			aelGlobals.write_log("[{DEFAULT_MODULE_NAME}] API download error in module 'getTVMovie'")
		if results and 'results' in res:
			reslist = set()
			for event in res['results']:
				reslist.add(event['title'].lower())
				if 'originalTitle' in event:
					reslist.add(event['originalTitle'].lower())
			bestmatch = get_close_matches(tvname.lower(), reslist, 2, 0.7)
			if not bestmatch:
				bestmatch = [tvname.lower()]
			nothingfound = True
			lastImage = ""
			for event in res['results']:
				original_title = 'abc123def456'
				if 'originalTitle' in event:
					original_title = event['originalTitle'].lower()
				if event['title'].lower() in bestmatch or original_title in bestmatch:
					airtime = 0
					if 'airTime' in event:
						airtime = int(mktime(datetime.strptime(str(event['airTime']), '%Y-%m-%d %H:%M:%S').timetuple()))
					if airtime <= db.getMaxAirtime(title[0]):
						nothingfound = False
						tid = ""
						subtitle = ""
						image = ""
						year = ""
						fsk = ""
						rating = ""
						leadText = ""
						conclusion = ""
						categoryName = ""
						season = ""
						episode = ""
						genre = ""
						country = ""
						imdb = ""
						if 'id' in event:
							tid = str(event['id'])
						if 'previewImage' in event:
							image = event['previewImage']['id']
						if 'genreName' in event:
							genre = event['genreName']
						if 'categoryName' in event:
							categoryName = event['categoryName']
						if 'productionYear' in event:
							year = event['productionYear']
						if 'countryOfProduction' in event:
							country = event['countryOfProduction']
						if 'ageRating' in event and 'Unbekannt' not in str(event['ageRating']):
							if 'OhneAlter' in str(event['ageRating']):
								fsk = '0'
							elif 'KeineJugend' in str(event['ageRating']):
								fsk = '18'
							else:
								fsk = event['ageRating']
						if 'season' in event:
							season = event['season']
						if 'episode' in event:
							episode = event['episode']
						if 'subTitle' in event and 'None' not in str(event['subTitle']):
							subtitle = event['subTitle']
						if 'leadText' in event:
							leadText = event['leadText']
						if 'conclusion' in event:
							conclusion = event['conclusion']
						if 'movieStarValue' in event:
							rating = str(int(event['movieStarValue'] * 2))
						rating = ""
#						if 'imdbId' in event:
#							imdb = event['imdbId']
						if not db.checkTitle(convert2base64(title[0])) and categoryName == "Spielfilm":
							db.addTitleInfo(convert2base64(title[0]), title[0], genre, year, rating, fsk, country, imdb)
						if db.checkTitle(convert2base64(title[0])):
							data = db.getTitleInfo(convert2base64(title[0]))
							if genre != "" and data[2] == "":
								db.updateSingleEventInfo('genre', genre, convert2base64(title[0]))
							if year != "" and data[3] == "":
								db.updateSingleEventInfo('year', year, convert2base64(title[0]))
							if rating != "" and data[4] == "":
								db.updateSingleEventInfo('rating', rating, convert2base64(title[0]))
							if fsk != "" and data[5] == "":
								db.updateSingleEventInfo('fsk', fsk, convert2base64(title[0]))
							if country != "" and data[5] == "":
								db.updateSingleEventInfo('country', country, convert2base64(title[0]))
						bld = ""
						if image != "" and config.plugins.AdvancedEventLibrary.SearchFor.value != 1 and config.plugins.AdvancedEventLibrary.UsePreviewImages.value:
							bld = image
							imgname = title[0] + ' - '
							if season != "":
								imgname += 'S' + str(season).zfill(2)
							if episode != "":
								imgname += 'E' + str(episode).zfill(2) + ' - '
							if subtitle != "":
								imgname += subtitle + ' - '
							image = imgname[:-3]
						else:
							image = ""
						success = founded
						db.updateliveTV(tid, subtitle, image, year, fsk, rating, leadText, conclusion, categoryName, season, episode, genre, country, imdb, title[0], airtime)
						founded = tcount - db.getUpdateCount()
						if founded > success and bld != "" and config.plugins.AdvancedEventLibrary.SearchFor.value != 1 and config.plugins.AdvancedEventLibrary.UsePreviewImages.value and str(image) != str(lastImage):
							if len(convert2base64(image)) < 255:
								imgpath = coverDir + convert2base64(image) + '.jpg'
								if downloadTVMovieImage(bld, imgpath):
									imgcount += 1
									lastImage = image
			if nothingfound:
				aelGlobals.write_log('nothing found on TV-Movie for ' + str(title[0]) + ' url ' + str(url), ADDLOG)
	aelGlobals.write_log('have updated ' + str(founded) + ' events from TV-Movie')
	aelGlobals.write_log('have downloaded ' + str(imgcount) + ' images from TV-Movie')
	if not secondRun:
		tvsImages = db.parameter(PARAMETER_GET, 'lastpreviewImageCount', None, 0)
		imgcount += int(tvsImages)
		db.parameter(PARAMETER_SET, 'lastpreviewImageCount', str(imgcount))
		getTVMovie(db, True)
	del tvnames
	del failedNames


def correctTitleName(tvname):
	if 'CSI: New York' in tvname:
		tvname = 'CSI: NY'
	elif 'CSI: Vegas' in tvname:
		tvname = 'CSI: Den Tätern auf der Spur'
	elif 'Star Trek - Das n' in tvname:
		tvname = 'Raumschiff Enterprise - Das nächste Jahrhundert'
	elif 'SAT.1-Fr' in tvname:
		tvname = 'Sat.1-Frühstücksfernsehen'
	elif 'Gefragt - Gejagt' in tvname:
		tvname = 'Gefragt Gejagt'
	elif 'nder - Menschen - Abenteuer' in tvname:
		tvname = 'Länder Menschen Abenteuer'
	elif 'Land - Liebe - Luft' in tvname:
		tvname = 'Land Liebe Luft'
	elif 'Stadt - Land - Quiz' in tvname:
		tvname = 'Stadt Land Quiz'
	elif 'Peppa Pig' in tvname:
		tvname = 'Peppa'
	elif 'Scooby-Doo!' in tvname:
		tvname = 'Scooby-Doo'
	elif 'ZDF SPORTreportage' in tvname:
		tvname = 'Sportreportage'
	elif 'The Garfield ShowT' in tvname:
		tvname = 'The Garfield Show'
	elif 'ProSieben S' in tvname:
		tvname = 'Spätnachrichten'
	elif 'Explosiv - Weekend' in tvname:
		tvname = 'Explosiv Weekend'
	elif 'Exclusiv - Weekend' in tvname:
		tvname = 'Exclusiv Weekend'
	elif 'Exclusiv - Das Starmagazin' in tvname:
		tvname = 'Exclusiv - Das Star-Magazin'
	elif 'Krass Schule - Die jungen Lehrer - Wie alles begann' in tvname:
		tvname = 'Krass Schule - Die jungen Lehrer'
	elif 'Die Megaschiff-Bauer' in tvname:
		tvname = 'Die Megaschiffbauer'
	elif 'Stargate: Atlantis' in tvname:
		tvname = 'Stargate Atlantis'
	elif 'Mega-Bauwerke' in tvname:
		tvname = 'Megastructures'
	elif 'Das Universum' in tvname:
		tvname = 'Das Universum - Eine Reise durch Raum und Zeit'
	elif 'Die wilden Siebziger' in tvname or 'Die Wilden Siebziger' in tvname:
		tvname = 'Die wilden 70er'
	elif 'MDR um 2' in tvname:
		tvname = 'MDR um zwei'
	elif 'MDR um 4' in tvname:
		tvname = 'MDR um vier'
	elif 'MDR um 11' in tvname:
		tvname = 'MDR um elf'
	elif 'MDR SACHSEN-ANHALT HEUTE' in tvname:
		tvname = 'MDR Regional'
	elif 'MDR SACHSENSPIEGEL' in tvname:
		tvname = 'MDR Regional'
	elif 'RINGEN JOURNAL' in tvname:
		tvname = 'MDR Regional'
	elif 'Geo Reportage' in tvname or 'GEO Reportage' in tvname:
		tvname = '360 Geo-Reportage'
	elif '7 Tage' in tvname:
		tvname = '7 Tage'
	elif 'Die Brot-Piloten' in tvname:
		tvname = 'Die Brotpiloten'
	elif 'Die UFO-Akten' in tvname:
		tvname = 'Die geheimen UFO-Akten - Besuch aus dem All'
	elif 'Dragons - Die W' in tvname:
		tvname = 'DreamWorks: Die Drachenreiter von Berk'
	elif 'Jim Hensons: Doozers' in tvname:
		tvname = 'Doozers'
	elif 'Lecker aufs Land' in tvname:
		tvname = 'Lecker aufs Land - eine kulinarische Reise'
	elif 'Schloss Einstein' in tvname:
		tvname = 'Schloss Einstein'
	elif 'Heiter bis t' in tvname:
		if tvname.find(': ') > 0:
			tvname = tvname[tvname.find(': ') + 2:].strip()
		elif tvname.find(' - ') > 0:
			tvname = tvname[tvname.find(' - ') + 3:].strip()
	return tvname.replace(' & ', ' ')


def convertTitle(name):
	if name.find(' (') > 0:
		regexfinder = compile(r"\([12][90]\d{2}\)", IGNORECASE)
		ex = regexfinder.findall(name)
		if not ex:
			name = name[:name.find(' (')].strip()
	if name.find(' - S0') > 0:
		name = name[:name.find(' - S0')].strip()
	if name.find(' S0') > 0:
		name = name[:name.find(' S0')].strip()
	if name.find('Folge') > 0:
		name = name[:name.find('Folge')].strip()
	if name.find('Episode') > 0:
		name = name[:name.find('Episode')].strip()
	name = name.strip(" -+&#:_")
	return name


def convertTitle2(name):
	if name.find(' (') > 0:
		regexfinder = compile(r"\([12][90]\d{2}\)", IGNORECASE)
		ex = regexfinder.findall(name)
		if not ex:
			name = name[:name.find(' (')].strip()
	if name.find(':') > 0:
		name = name[:name.find(':')].strip()
	if name.find(' - S0') > 0:
		name = name[:name.find(' - S0')].strip()
	if name.find(' S0') > 0:
		name = name[:name.find(' S0')].strip()
	if name.find(' -') > 0:
		name = name[:name.find(' -')].strip()
	if name.find('Folge') > 0:
		name = name[:name.find('Folge')].strip()
	if name.find('Episode') > 0:
		name = name[:name.find('Episode')].strip()
	if name.find('!') > 0:
		name = name[:name.find('!') + 1].strip()
	name = name.strip(" -+&#:_")
	return name


def findEpisode(title):
	regexfinder = compile(r'[Ss]\d{2}[Ee]\d{2}', MULTILINE | DOTALL)
	ex = regexfinder.findall(str(title))
	if ex:
		removedEpisode = title
		if removedEpisode.find(str(ex[0])) > 0:
				removedEpisode = removedEpisode[:removedEpisode.find(str(ex[0]))]
		removedEpisode = convertTitle2(removedEpisode)
		SE = ex[0].lower().replace('s', '').split('e')
		return (SE[0], SE[1], removedEpisode.strip())


def convertSearchName(eventName):
	eventName = removeExtension(eventName)
	try:
		text = eventName.replace('\x86', '').replace('\x87', '')
	except Exception:
		text = eventName.replace(b'\x86', b'').replace(b'\x87', b'')
	return text


def convertDateInFileName(fileName):
	regexfinder = compile(r'\d{8} - ', IGNORECASE)
	ex = regexfinder.findall(fileName)
	return fileName.replace(ex[0], '') if ex else fileName


def convertYearInTitle(title):
	regexfinder = compile(r"\([12][90]\d{2}\)", IGNORECASE)
	ex = regexfinder.findall(title)
	return [title.replace(ex[0], '').strip(), ex[0].replace('(', '').replace(')', '')] if ex else [title, '']


def downloadImage(url, filename, timeout=5):
	try:
		if not fileExists(filename):
			r = get(url, stream=True, timeout=timeout)
			if r.status_code == 200:
				with open(filename, 'wb') as f:
					r.raw.decode_content = True
					copyfileobj(r.raw, f)
					f.close()
				r = None
			else:
				aelGlobals.write_log("Fehlerhafter Statuscode beim Download für : " + str(filename) + ' auf ' + str(url))
		else:
			aelGlobals.write_log("Picture : " + str(b64decode(filename.split('/')[-1].replace('.jpg', ''))) + ' exists already ', ADDLOG)
	except Exception as ex:
		aelGlobals.write_log("Error in download image: " + str(ex))


def downloadImage2(url, filename, timeout=5):
	try:
		if not fileExists(filename):
			r = get(url, stream=True, timeout=timeout)
			if r.status_code != 200:
				with open(filename, 'wb') as f:
					r.raw.decode_content = True
					copyfileobj(r.raw, f)
					f.close()
				r = None
				return True
			else:
				return False
		else:
			return True
	except Exception:
		return False


def checkAllImages():
	global STATUS
	removeList = []
	dirs = [f"{getPictureDir()}cover/", getPictureDir() + 'cover/thumbnails/', f"{getPictureDir()}poster/", getPictureDir() + 'poster/thumbnails/']
	for dir in dirs:
		filelist = glob(dir + "*.*")
		c = 0
		ln = len(filelist)
		for f in filelist:
			c += 1
			STATUS = f"{c}/{ln} überprüfe {f}"
			img = Image.open(f)
			if img.format != 'JPEG':
				aelGlobals.write_log('invalid image : ' + str(f) + ' ' + str(img.format))
				removeList.append(f)
			img = None
		del filelist
	if removeList:
		for f in removeList:
			aelGlobals.write_log('remove image : ' + str(f))
			remove(f)
		del removeList
	STATUS = None
	clearMem("checkAllImages")


def reduceImageSize(path, db):
	global STATUS
	imgsize = coverqualityDict[config.plugins.AdvancedEventLibrary.coverQuality.value] if 'cover' in str(path) else posterqualityDict[config.plugins.AdvancedEventLibrary.posterQuality.value]
	sizex, sizey = imgsize.split("x", 1)
	filelist = glob(join(path, "*.jpg"))
	maxSize = config.plugins.AdvancedEventLibrary.MaxImageSize.value
	for f in filelist:
		try:
			q = 90
			if not db.getimageBlackList(f):
				oldSize = int(getsize(f) / 1024.0)
				if oldSize > maxSize:
					try:
						fn = b64decode((f.split('/')[-1]).rsplit('.', 1)[0])
					except Exception:
						fn = (f.split('/')[-1]).rsplit('.', 1)[0]
						fn = fn.replace('.jpg', '')
					try:
						img = Image.open(f)
					except Exception:
						continue
					w = int(img.size[0])
					h = int(img.size[1])
					STATUS = f"Bearbeite {fn}.jpg mit {bytes2human(getsize(f), 1)} und {w})x{h}px"
					img_bytes = StringIO()
					img1 = img.convert('RGB', colors=256)
					img1.save(str(img_bytes), format='jpeg')
					if img_bytes.tell() / 1024 >= oldSize:
						if w > int(sizex):
							w = int(sizex)
							h = int(sizey)
							img1 = img.resize((w, h), Image.LANCZOS)
							img1.save(str(img_bytes), format='jpeg')
					else:
						if w > int(sizex):
							w = int(sizex)
							h = int(sizey)
							img1 = img1.resize((w, h), Image.LANCZOS)
							img1.save(str(img_bytes), format='jpeg')
					if img_bytes.tell() / 1024 > maxSize:
						while img_bytes.tell() / 1024 > maxSize:
							img1.save(str(img_bytes), format='jpeg', quality=q)
							q -= 8
							if q <= config.plugins.AdvancedEventLibrary.MaxCompression.value:
								break
					img1.save(f, format='jpeg', quality=q)
					aelGlobals.write_log('file ' + str(fn) + '.jpg reduced from ' + str(bytes2human(int(oldSize * 1024), 1)) + ' to ' + str(bytes2human(getsize(f), 1)) + ' and ' + str(w) + 'x' + str(h) + 'px')
					if getsize(f) / 1024.0 > maxSize:
						aelGlobals.write_log('Image size cannot be further reduced with the current settings!')
						db.addimageBlackList(str(f))
					img_bytes = None
					img = None
		except Exception as ex:
			aelGlobals.write_log("Error in reduceImageSize: " + str(ex))
			continue
	del filelist


def reduceSigleImageSize(src, dest):
	imgsize = coverqualityDict[config.plugins.AdvancedEventLibrary.coverQuality.value] if 'cover' in str(dest) else posterqualityDict[config.plugins.AdvancedEventLibrary.posterQuality.value]
	sizex, sizey = imgsize.split("x", 1)
	maxSize = config.plugins.AdvancedEventLibrary.MaxImageSize.value
	q = 90
	oldSize = int(getsize(src) / 1024.0)
	if oldSize > maxSize:
		try:
			fn = b64decode((src.split('/')[-1]).rsplit('.', 1)[0])
		except Exception:
			fn = (src.split('/')[-1]).rsplit('.', 1)[0]
			fn = fn.replace('.jpg', '')
		try:
			img = Image.open(src)
			w = int(img.size[0])
			h = int(img.size[1])
			aelGlobals.write_log('convert image ' + str(fn) + '.jpg with ' + str(bytes2human(getsize(src), 1)) + ' and ' + str(w) + 'x' + str(h) + 'px')
			img_bytes = StringIO()
			img1 = img.convert('RGB', colors=256)
			img1.save(str(img_bytes), format='jpeg')
			if img_bytes.tell() / 1024 >= oldSize:
				if w > int(sizex):
					w = int(sizex)
					h = int(sizey)
					img1 = img.resize((w, h), Image.LANCZOS)
					img1.save(str(img_bytes), format='jpeg')
			else:
				if w > int(sizex):
					w = int(sizex)
					h = int(sizey)
					img1 = img1.resize((w, h), Image.LANCZOS)
					img1.save(str(img_bytes), format='jpeg')
			if img_bytes.tell() / 1024 > maxSize:
				while img_bytes.tell() / 1024 > maxSize:
					img1.save(str(img_bytes), format='jpeg', quality=q)
					q -= 8
					if q <= config.plugins.AdvancedEventLibrary.MaxCompression.value:
						break
			img1.save(dest, format='jpeg', quality=q)
			aelGlobals.write_log('file ' + str(fn) + '.jpg reduced from ' + str(bytes2human(int(oldSize * 1024), 1)) + ' to ' + str(bytes2human(getsize(dest), 1)) + ' and ' + str(w) + 'x' + str(h) + 'px')
			if getsize(dest) / 1024.0 > maxSize:
				aelGlobals.write_log('Image size cannot be further reduced with the current settings!')
			img_bytes = None
			img = None
		except Exception as ex:
			aelGlobals.write_log("Error in reduceSingleImageSize: " + str(ex))


def createThumbnails(path):
	global STATUS
	wp, hp = parameters.get("EventLibraryThumbnailPosterSize", (60, 100))
	wc, hc = parameters.get("EventLibraryThumbnailCoverSize", (100, 60))
	filelist = glob(join(path, "*.jpg"))
	for f in filelist:
		try:
			if f.endswith('.jpg'):
				if 'bGl2ZSBibDog' in str(f):
					remove(f)
				else:
					destfile = f.replace('cover', 'cover/thumbnails').replace('poster', 'poster/thumbnails').replace('preview', 'preview/thumbnails')
					if not fileExists(destfile):
						STATUS = f"erzeuge Thumbnail für {f}"
						img = Image.open(f)
						imgnew = img.convert('RGBA', colors=256)
						imgnew = img.resize((wc, hc), Image.LANCZOS) if 'cover' in str(f) or 'preview' in str(f) else img.resize((wp, hp), Image.LANCZOS)
						imgnew.save(destfile)
						img = None
		except Exception as ex:
			aelGlobals.write_log("Error in createThumbnails: " + str(f) + ' - ' + str(ex))
			remove(f)
			continue
	del filelist


def createSingleThumbnail(src, dest):
	wp, hp = parameters.get("EventLibraryThumbnailPosterSize", (60, 100))
	wc, hc = parameters.get("EventLibraryThumbnailCoverSize", (100, 60))
	destfile = dest.replace('cover', 'cover/thumbnails').replace('poster', 'poster/thumbnails')
	aelGlobals.write_log('create single thumbnail from source ' + str(src) + ' to ' + str(destfile) + ' with ' + str(wc) + 'x' + str(hc) + 'px')
	img = Image.open(src)
	imgnew = img.convert('RGBA', colors=256)
	imgnew = img.resize((wc, hc), Image.LANCZOS) if 'cover' in str(dest) or 'preview' in str(dest) else img.resize((wp, hp), Image.LANCZOS)
	imgnew.save(destfile)
	if fileExists(destfile):
		aelGlobals.write_log('thumbnail created')
	img = None


def get_titleInfo(titles, research=None, loadImages=True, db=None, liveTVRecords=[], tvsref=None, lang="de"):
	global STATUS
	tvdbV4 = get_TVDb()
	if not tvdbV4:
		aelGlobals.write_log('TVDb API-V4 is not in use!')
	posterDir = f"{getPictureDir()}poster/"
	coverDir = f"{getPictureDir()}cover/"
	previewDir = f"{getPictureDir()}preview/"
	posters = 0
	covers = 0
	entrys = 0
	blentrys = 0
	position = 0
#	TODO: Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
#	unkodierte URL: http://image.tmdb.org/t/p/original
	tmdburl = b64decode(b"aHR0cDovL2ltYWdlLnRtZGIub3JnL3QvcC9vcmlnaW5hbA==l"[:-1]).decode()
	for title in titles:
		if title and title != '' and title != ' ' and 'BL:' not in title:
			tmdb.API_KEY = get_keys('tmdb')
			tvdb.KEYS.API_KEY = get_keys('tvdb')
			titleinfo = {"title": "", "genre": "", "poster_url": "", "backdrop_url": "", "year": "", "rating": "", "fsk": "", "country": ""}
			titleinfo['title'] = convertSearchName(title)
			titleNyear = convertYearInTitle(title)
			title = convertSearchName(titleNyear[0])
			jahr = str(titleNyear[1])
			position += 1
			org_name = None
			imdb_id = None
			omdb_image = None
			foundAsMovie = False
			foundAsSeries = False
			aelGlobals.write_log('################################################### themoviedb movie ##############################################')
			STATUS = f"{position}/{len(titles)} : themoviedb movie -{title} ({posters}|{covers}|{entrys}|{blentrys})"
			aelGlobals.write_log('looking for ' + str(title) + ' on themoviedb movie', aelGlobals.addlog)
			search = tmdb.Search()
			res = search.movie(query=title, language='de', year=jahr) if jahr != '' else search.movie(query=title, language='de')
			if res and res['results']:
				reslist = []
				for item in res['results']:
					if 'love blows' not in str(item['title'].lower()):
						reslist.append(item['title'].lower())
				bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
				if not bestmatch:
					bestmatch = [title.lower()]
				for item in res['results']:
					if item['title'].lower() == bestmatch[0]:
						foundAsMovie = True
						aelGlobals.write_log('found ' + str(bestmatch[0]) + ' for ' + str(title.lower()) + ' on themoviedb movie', aelGlobals.addlog)
						if item['original_title']:
							org_name = item['original_title']
						if item['poster_path'] and loadImages:
							if item['poster_path'].endswith('.jpg'):
								titleinfo['poster_url'] = f"{tmdburl}{item['poster_path']}"
						if item['backdrop_path'] and loadImages:
							if item['backdrop_path'].endswith('.jpg'):
								titleinfo['backdrop_url'] = f"{tmdburl}{item['backdrop_path']}"
						if 'release_date' in item:
							titleinfo['year'] = item['release_date'][:4]
						if item['genre_ids']:
							for genre in item['genre_ids']:
								if tmdb_genres[genre] not in titleinfo['genre']:
									titleinfo['genre'] = titleinfo['genre'] + tmdb_genres[genre] + ' '
						if 'vote_average' in item and item['vote_average'] != "0":
							titleinfo['rating'] = str(item['vote_average'])
						if 'id' in item:
							details = tmdb.Movies(item['id'])
							for country in details.releases(language='de')['countries']:
								if str(country['iso_3166_1']) == "DE":
									titleinfo['fsk'] = str(country['certification'])
									break
							for country in details.info(language='de')['production_countries']:
								titleinfo['country'] = titleinfo['country'] + country['iso_3166_1'] + " | "
							titleinfo['country'] = titleinfo['country'][:-3]
							imdb_id = details.info(language='de')['imdb_id']
							if not titleinfo['poster_url'].startswith('http') or not titleinfo['backdrop_url'].startswith('http') and loadImages:
								if not titleinfo['backdrop_url'].startswith('http'):
									showimgs = details.images(language='de')['backdrops']
									if showimgs:
										titleinfo['backdrop_url'] = f"{tmdburl}{showimgs[0]['file_path']}"
								if not titleinfo['poster_url'].startswith('http'):
									showimgs = details.images(language='de')['posters']
									if showimgs:
										titleinfo['poster_url'] = f"{tmdburl}{showimgs[0]['file_path']}"
						break
			aelGlobals.write_log('################################################### themoviedb tv ##############################################')
			if not foundAsMovie:
				STATUS = f"{position}/{len(titles)} : themoviedb tv -{title} ({posters}|{covers}|{entrys}|{blentrys})"
				aelGlobals.write_log('looking for ' + str(title) + ' on themoviedb tv', aelGlobals.addlog)
				search = tmdb.Search()
				searchName = findEpisode(title)
				if searchName:
					res = aelGlobals.callLibrary(search.tv, query=searchName[2], language='de', year=jahr, include_adult=True, search_type='ngram')
				else:
					res = aelGlobals.callLibrary(search.tv, query=title, language='de', year=jahr)
				if res and res['results']:
					reslist = []
					for item in res['results']:
						if 'love blows' not in str(item['name'].lower()):
							reslist.append(item['name'].lower())
					if searchName:
						bestmatch = get_close_matches(searchName[2].lower(), reslist, 1, 0.7)
						if not bestmatch:
							bestmatch = [searchName[2].lower()]
					else:
						bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
						if not bestmatch:
							bestmatch = [title.lower()]
					for item in res['results']:
						if item['name'].lower() == bestmatch[0]:
							foundAsSeries = True
							aelGlobals.write_log('found ' + str(bestmatch[0]) + ' for ' + str(title.lower()) + ' on themoviedb tv', aelGlobals.addlog)
							if searchName:
								details = tmdb.TV_Episodes(item['id'], searchName[0], searchName[1])
								if details:
									epi = details.info(language='de')
									#imgs = details.images(language='de')
									if 'air_date' in epi:
										titleinfo['year'] = epi['air_date'][:4]
									if 'vote_average' in epi:
										titleinfo['rating'] = epi['vote_average']
									if epi['still_path'] and loadImages:
										if epi['still_path'].endswith('.jpg'):
											titleinfo['backdrop_url'] = f"{tmdburl}{epi['still_path']}"
									if item['origin_country']:
										for country in item['origin_country']:
											titleinfo['country'] = titleinfo['country'] + country + ' | '
										titleinfo['country'] = titleinfo['country'][:-3]
									if item['genre_ids']:
										for genre in item['genre_ids']:
											if tmdb_genres[genre] not in titleinfo['genre']:
												titleinfo['genre'] = titleinfo['genre'] + tmdb_genres[genre] + '-Serie '
							else:
								if item['original_name']:
									org_name = item['original_name']
								if item['origin_country']:
									for country in item['origin_country']:
										titleinfo['country'] = titleinfo['country'] + country + ' | '
									titleinfo['country'] = titleinfo['country'][:-3]
								if item['poster_path'] and loadImages:
									if item['poster_path'].endswith('.jpg'):
										titleinfo['poster_url'] = f"{tmdburl}{item['poster_path']}"
								if item['backdrop_path'] and loadImages:
									if item['backdrop_path'].endswith('.jpg'):
										titleinfo['backdrop_url'] = f"{tmdburl}{item['backdrop_path']}"
								if 'first_air_date' in item:
									titleinfo['year'] = item['first_air_date'][:4]
								if item['genre_ids']:
									for genre in item['genre_ids']:
										if tmdb_genres[genre] not in titleinfo['genre']:
											titleinfo['genre'] = titleinfo['genre'] + tmdb_genres[genre] + '-Serie '
								if 'vote_average' in item and item['vote_average'] != "0":
									titleinfo['rating'] = str(item['vote_average'])
								if 'id' in item:
									details = tmdb.TV(item['id'])
									for country in details.content_ratings(language='de')['results']:
										if str(country['iso_3166_1']) == "DE":
											titleinfo['fsk'] = str(country['rating'])
											break
									if not titleinfo['poster_url'].startswith('http') or not titleinfo['backdrop_url'].startswith('http') and loadImages:
										if not titleinfo['backdrop_url'].startswith('http'):
											showimgs = details.images(language='de')['backdrops']
											if showimgs:
												titleinfo['backdrop_url'] = f"{tmdburl}{showimgs[0]['file_path']}"
										if not titleinfo['poster_url'].startswith('http'):
											showimgs = details.images(language='de')['posters']
											if showimgs:
												titleinfo['poster_url'] = f"{tmdburl}{showimgs[0]['file_path']}"
							break
			aelGlobals.write_log('################################################### thetvdb ##############################################')
			if not foundAsMovie and not foundAsSeries:
				STATUS = f"{position}/{len(titles)} : thetvdb -{title} ({posters}|{covers}|{entrys}|{blentrys})"
				aelGlobals.write_log('looking for ' + str(title) + ' on thetvdb', aelGlobals.addlog)
				seriesid = None
				search = tvdb.Search()
				searchTitle = convertTitle2(title)
				response = aelGlobals.callLibrary(search.series, title=searchTitle, language="de")
				if response:
					reslist = []
					for result in response:
						if 'love blows' not in str(result['seriesName'].lower()):
							reslist.append(result['seriesName'].lower())
					bestmatch = get_close_matches(searchTitle.lower(), reslist, 1, 0.7)
					if not bestmatch:
						bestmatch = [searchTitle.lower()]
					for result in response:
						if result['seriesName'].lower() == bestmatch[0]:
							aelGlobals.write_log('found ' + str(bestmatch[0]) + ' for ' + str(title.lower()) + ' on thetvdb', aelGlobals.addlog)
							seriesid = result['id']
							break
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
					if episoden and episoden:
						for episode in episoden:
							epilist.append(str(episode['episodeName']).lower())
						bestmatch = get_close_matches(title.lower(), epilist, 1, 0.7)
						if not bestmatch:
							bestmatch = [title.lower()]
						for episode in episoden:
							if str(episode['episodeName']).lower() == str(bestmatch[0]):
								foundEpisode = True
								if 'firstAired' in episode and episode['firstAired'] is not None:
									titleinfo['year'] = episode['firstAired'][:4]
								if 'siteRating' in episode:
									if episode['siteRating'] != '0' and episode['siteRating'] != 'None':
										titleinfo['rating'] = episode['siteRating']
								if 'contentRating' in episode:
									if "TV-MA" in str(episode['contentRating']):
										titleinfo['fsk'] = "18"
									elif "TV-PG" in str(episode['contentRating']):
										titleinfo['fsk'] = "16"
									elif "TV-14" in str(episode['contentRating']):
										titleinfo['fsk'] = "12"
									elif "TV-Y7" in str(episode['contentRating']):
										titleinfo['fsk'] = "6"
								if 'filename' in episode and loadImages:
									if str(episode['filename']).endswith('.jpg') and not titleinfo['backdrop_url'].startswith('http'):
										titleinfo['backdrop_url'] = 'https://www.thetvdb.com/banners/' + episode['filename']
								if 'imdbId' in episode and episode['imdbId'] is not None:
									imdb_id = episode['imdbId']
								if response:
									if titleinfo['genre'] == "" and 'genre' in response:
										if response['genre'] and str(response['genre']) != 'None':
											for genre in response['genre']:
												titleinfo['genre'] = titleinfo['genre'] + genre + '-Serie '
									titleinfo['genre'] = titleinfo['genre'].replace("Documentary", "Dokumentation").replace("Children", "Kinder")
									if titleinfo['country'] == "" and response['network'] is not None:
										if response['network'] in networks:
											titleinfo['country'] = networks[response['network']]
									if response['poster'] and loadImages:
										if str(response['poster']).endswith('.jpg') and not titleinfo['poster_url'].startswith('http'):
											titleinfo['poster_url'] = 'https://www.thetvdb.com/banners/' + response['poster']
								break
					if response and not foundEpisode:
						if titleinfo['year'] == "":
							titleinfo['year'] = response['firstAired'][:4]
						if titleinfo['genre'] == "" and response['genre']:
							for genre in response['genre']:
								titleinfo['genre'] = titleinfo['genre'] + genre + '-Serie '
						titleinfo['genre'] = titleinfo['genre'].replace("Documentary", "Dokumentation").replace("Children", "Kinder")
						if titleinfo['country'] == "" and response['network'] in networks:
							titleinfo['country'] = networks[response['network']]
						imdb_id = response['imdbId']
						if titleinfo['rating'] == "" and response['siteRating'] != "0":
							titleinfo['rating'] = response['siteRating']
						if titleinfo['fsk'] == "":
							if "TV-MA" in str(response['rating']):
								titleinfo['fsk'] = "18"
							elif "TV-PG" in str(response['rating']):
									titleinfo['fsk'] = "16"
							elif "TV-14" in str(response['rating']):
								titleinfo['fsk'] = "12"
							elif "TV-Y7" in str(response['rating']):
								titleinfo['fsk'] = "6"
						if response['poster'] and loadImages:
							if response['poster'].endswith('.jpg') and not titleinfo['poster_url'].startswith('http'):
								titleinfo['poster_url'] = 'https://www.thetvdb.com/banners/' + response['poster']
						if response['fanart'] and loadImages:
							if response['fanart'].endswith('.jpg') and not titleinfo['backdrop_url'].startswith('http'):
								titleinfo['backdrop_url'] = 'https://www.thetvdb.com/banners/' + response['fanart']
						if not titleinfo['poster_url'].startswith('http') or not titleinfo['backdrop_url'].startswith('http') and loadImages:
							showimgs = tvdb.Series_Images(seriesid)
							if not titleinfo['backdrop_url'].startswith('http'):
								response = aelGlobals.callLibrary(showimgs.fanart, language=str(lang))
								if response and str(response) != 'None':
									titleinfo['backdrop_url'] = 'https://www.thetvdb.com/banners/' + response[0]['fileName']
							if not titleinfo['poster_url'].startswith('http'):
								response = aelGlobals.callLibrary(showimgs.poster, language=str(lang))
								if response and str(response) != 'None':
									titleinfo['poster_url'] = 'https://www.thetvdb.com/banners/' + response[0]['fileName']
			aelGlobals.write_log('################################################### maze.tv ##############################################')
			if not foundAsMovie:
				if titleinfo['genre'] == "" or titleinfo['country'] == "" or titleinfo['year'] == "" or titleinfo['rating'] == "" or titleinfo['poster_url'] == "":
					STATUS = f"{position}/{len(titles)} : maze.tv -{title} ({posters}|{covers}|{entrys}|{blentrys})"
					aelGlobals.write_log('looking for ' + str(title) + ' on maze.tv', aelGlobals.addlog)
					# TODO: Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
					# url = f"http://api.tvmaze.com/search/shows?q={org_name}" if org_name else f"http://api.tvmaze.com/search/shows?q={title}"
					# unkodierte URL: http://api.tvmaze.com/search/shows
					tvmazeurl = b64decode(b"aHR0cDovL2FwaS50dm1hemUuY29tL3NlYXJjaC9zaG93cw==5")[:-1].decode()
					errmsg, res = aelGlobals.getAPIdata(tvmazeurl, params={"q": f"{org_name if org_name else title}"})
					if errmsg:
						aelGlobals.write_log("[{DEFAULT_MODULE_NAME}] API download error in module 'get_titleInfo: TVMAZE call'")
					if res:
						reslist = []
						for item in res:
							if 'love blows' not in str(item['show']['name'].lower()):
								reslist.append(item['show']['name'].lower())
						bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
						if not bestmatch:
							bestmatch = [title.lower()]
						for item in res:
							if item['show']['name'].lower() == bestmatch[0]:
								if item['show']['network']['country'] and titleinfo['country'] == "":
									titleinfo['country'] = item['show']['network']['country']['code']
								if item['show']['premiered'] and titleinfo['year'] == "":
									titleinfo['year'] = item['show']['premiered'][:4]
								if item['show']['genres'] and titleinfo['genre'] == "":
									for genre in item['show']['genres']:
										if genre not in titleinfo['genre']:
											titleinfo['genre'] = titleinfo['genre'] + genre + '-Serie '
									titleinfo['genre'] = titleinfo['genre'].replace("Documentary", "Dokumentation").replace("Children", "Kinder")
								if item['show']['image'] and not titleinfo['poster_url'].startswith('http') and loadImages:
									titleinfo['poster_url'] = item['show']['image']['original']
								if item['show']['rating']['average'] and titleinfo['rating'] == "":
									titleinfo['rating'] = item['show']['rating']['average']
								if item['show']['externals']['imdb'] and not imdb_id:
									imdb_id = item['show']['externals']['imdb']
								break
			aelGlobals.write_log('################################################### omdb ##############################################')
			if not foundAsMovie and not foundAsSeries:
				STATUS = f"{position}/{len(titles)} : omdb -{title} ({posters}|{covers}|{entrys}|{blentrys})"
				aelGlobals.write_log('looking for ' + str(title) + ' on omdb', aelGlobals.addlog)
				# TODO: Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
				# unkodierte URL: http://www.omdbapi.com
				omdburl = b64decode(b"aHR0cDovL3d3dy5vbWRiYXBpLmNvbQ==b"[:-1]).decode()
				if imdb_id:
					# TODO: Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
					# url = f"http://www.omdbapi.com/?apikey={get_keys('omdb')}&i={imdb_id}"
					params = {"apikey": get_keys('omdb'), "i": imdb_id}
				else:
					# TODO: Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
					# url = f"http://www.omdbapi.com/?apikey={get_keys('omdb')}&s={org_name}&page=1" if org_name else f"http://www.omdbapi.com/?apikey={get_keys('omdb')}&s={title}&page=1"
					params = {"apikey": get_keys('omdb'), "s": org_name, "page": 1}
					errmsg, res = aelGlobals.getAPIdata(omdburl, params=params)
					if errmsg:
						aelGlobals.write_log("[{DEFAULT_MODULE_NAME}] API download error in module 'get_titleInfo: OMDB call #1'")
					# TODO: Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
					# url = f"http://www.omdbapi.com/?apikey={get_keys('omdb')}&t={title}"
					params = {"apikey": get_keys('omdb'), "t": title, "page": 1}
					if res and res['Response'] == "True":
						reslist = []
						for result in res['Search']:
							reslist.append(result['Title'].lower())
						bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
						if not bestmatch:
							bestmatch = [title.lower()]
						for result in res['Search']:
							if result['Title'].lower() == bestmatch[0]:
								# TODO: Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
								# url = f"http://www.omdbapi.com/?apikey={get_keys('omdb')}&i={result['imdbID']}"
								params = {"apikey": get_keys('omdb'), "i": result['imdbID']}
								break
				errmsg, res = aelGlobals.getAPIdata(omdburl, params=params)
				if errmsg:
					aelGlobals.write_log("[{DEFAULT_MODULE_NAME}] API download error in module 'get_searchResults: OMDB call #2'")
				if res and res['Response'] == "True":
					if res['Year'] and titleinfo['year'] == "":
						titleinfo['year'] = res['Year'][:4]
					if res['Genre'] != "N/A" and titleinfo['genre'] == "":
						stype = "-Serie" if res['Type'] and res['Type'] == 'series' else " "
						genres = res['Genre'].split(', ')
						for genre in genres:
							if genre not in titleinfo['genre']:
								titleinfo['genre'] = titleinfo['genre'] + genre + stype
						titleinfo['genre'] = titleinfo['genre'].replace("Documentary", "Dokumentation").replace("Children", "Kinder")
					if res['Poster'].startswith('http') and not titleinfo['poster_url'].startswith('http') and loadImages:
						titleinfo['poster_url'] = res['Poster']
						omdb_image = True
					if res['imdbRating'] != "N/A" and titleinfo['rating'] == "":
						titleinfo['rating'] = res['imdbRating']
					if res['Country'] != "N/A" and titleinfo['country'] == "":
						rescountries = res['Country'].split(', ')
						countries = ""
						for country in rescountries:
							countries = countries + country + ' | '
						titleinfo['country'] = countries[:-2].replace('West Germany', 'DE').replace('East Germany', 'DE').replace('Germany', 'DE').replace('France', 'FR').replace('Canada', 'CA').replace('Austria', 'AT').replace('Switzerland', 'S').replace('Belgium', 'B').replace('Spain', 'ESP').replace('Poland', 'PL').replace('Russia', 'RU').replace('Czech Republic', 'CZ').replace('Netherlands', 'NL').replace('Italy', 'IT')
					if res['imdbID'] != "N/A" and not imdb_id:
						imdb_id = res['imdbID']
					if titleinfo['fsk'] == "" and res['Rated'] != "N/A":
						if "R" in str(res['Rated']):
							titleinfo['fsk'] = "18"
						elif "TV-MA" in str(res['Rated']):
							titleinfo['fsk'] = "18"
						elif "TV-PG" in str(res['Rated']):
							titleinfo['fsk'] = "16"
						elif "TV-14" in str(res['Rated']):
							titleinfo['fsk'] = "12"
						elif "TV-Y7" in str(res['Rated']):
							titleinfo['fsk'] = "6"
						elif "PG-13" in str(res['Rated']):
							titleinfo['fsk'] = "12"
						elif "PG" in str(res['Rated']):
							titleinfo['fsk'] = "6"
						elif "G" in str(res['Rated']):
							titleinfo['fsk'] = "16"
			filename = convert2base64(title)
			if db and filename and filename != '' and filename != ' ':
				if titleinfo['genre'] == "" and titleinfo['year'] == "" and titleinfo['rating'] == "" and titleinfo['fsk'] == "" and titleinfo['country'] == "" and titleinfo['poster_url'] == "" and titleinfo['backdrop_url'] == "":
					blentrys += 1
					db.addblackList(filename)
					aelGlobals.write_log('nothing found for : ' + str(titleinfo['title']), aelGlobals.addlog)
				if titleinfo['genre'] != "" or titleinfo['year'] != "" or titleinfo['rating'] != "" or titleinfo['fsk'] != "" or titleinfo['country'] != "":
					entrys += 1
					if research:
						if db.checkTitle(research):
							db.updateTitleInfo(titleinfo['title'], titleinfo['genre'], titleinfo['year'], titleinfo['rating'], titleinfo['fsk'], titleinfo['country'], research)
						else:
							db.addTitleInfo(filename, titleinfo['title'], titleinfo['genre'], titleinfo['year'], titleinfo['rating'], titleinfo['fsk'], titleinfo['country'])
					else:
						db.addTitleInfo(filename, titleinfo['title'], titleinfo['genre'], titleinfo['year'], titleinfo['rating'], titleinfo['fsk'], titleinfo['country'])
					aelGlobals.write_log('found data for : ' + str(titleinfo['title']), aelGlobals.addlog)
				if not titleinfo['poster_url'] and loadImages:
					titleinfo['poster_url'] = get_Picture(f"{title} ({titleinfo['year']})", what='Poster', lang='de') if titleinfo['year'] != "" else get_Picture(title, what='Poster', lang='de')
				if titleinfo['poster_url'] and loadImages:
					if titleinfo['poster_url'].startswith('http'):
						posters += 1
						if research:
							downloadImage(titleinfo['poster_url'], join(posterDir, f"{research}.jpg"))
						else:
							downloadImage(titleinfo['poster_url'], join(posterDir, f"{filename}.jpg"))
						if omdb_image:
							img = Image.open(join(posterDir, f"{filename}.jpg"))
							w, h = img.size
							if w > h:
								move(join(posterDir, filename + '.jpg'), join(coverDir, f"{filename}.jpg"))
							img = None
				if not titleinfo['backdrop_url'] and loadImages:
					titleinfo['backdrop_url'] = get_Picture(f"{title} ({titleinfo['year']})", what='Cover', lang='de') if titleinfo['year'] != "" else get_Picture(title, what='Cover', lang='de')
				if titleinfo['backdrop_url'] and loadImages:
					if titleinfo['backdrop_url'].startswith('http'):
						covers += 1
						if research:
							downloadImage(titleinfo['backdrop_url'], join(coverDir, f"{research}.jpg"))
						else:
							downloadImage(titleinfo['backdrop_url'], join(coverDir, f"{filename}.jpg"))
			aelGlobals.write_log(titleinfo, aelGlobals.addlog)
	aelGlobals.write_log(f"set {entrys} on eventInfo")
	aelGlobals.write_log(f"set {blentrys} on Blacklist")
	if db:
		db.parameter(PARAMETER_SET, 'lasteventInfoCount', str(int(entrys + blentrys)))
		db.parameter(PARAMETER_SET, 'lasteventInfoCountSuccsess', str(entrys))
	STATUS = "entferne alte Extradaten..."
	if config.plugins.AdvancedEventLibrary.DelPreviewImages.value:
		cleanPreviewImages(db)
	if db:
		db.cleanliveTV(int(time() - 28800))
	if db and len(liveTVRecords) > 0:
		aelGlobals.write_log('try to insert ' + str(len(liveTVRecords)) + ' events into database')
		db.addliveTV(liveTVRecords)
		db.parameter(PARAMETER_SET, 'lastadditionalDataCount', str(db.getUpdateCount()))
		getTVSpielfilm(db, tvsref)
		getTVMovie(db)
		db.updateliveTVProgress()
	if loadImages:
		aelGlobals.write_log("looking for missing pictures")
		get_MissingPictures(db, posters, covers)
	aelGlobals.write_log("create thumbnails for cover")
	createThumbnails(coverDir)
	aelGlobals.write_log("create thumbnails for preview images")
	createThumbnails(previewDir)
	aelGlobals.write_log("create thumbnails for poster")
	createThumbnails(posterDir)
	aelGlobals.write_log("reduce large image-size")
	reduceImageSize(coverDir, db)
	reduceImageSize(previewDir, db)
	reduceImageSize(posterDir, db)
	if config.plugins.AdvancedEventLibrary.CreateMetaData.value:
		aelGlobals.write_log("looking for missing meta-Info")
		createMovieInfo(db)
	createStatistics(db)
	if config.plugins.AdvancedEventLibrary.UpdateAELMovieWall.value:
		aelGlobals.write_log("create MovieWall data")
		try:
			itype = None
			if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/imageType.data'):
				with open('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/imageType.data', 'r') as f:
					itype = f.read()
					f.close()
			if itype:
				from Plugins.Extensions.AdvancedEventLibrary.AdvancedEventLibrarySimpleMovieWall import saveList
				saveList(itype)
				aelGlobals.write_log("MovieWall data saved with " + str(itype))
		except Exception as ex:
			aelGlobals.write_log('save moviewall data : ' + str(ex))
	if aelGlobals.addlog:
		writeTVStatistic(db)
	if db:
		db.parameter(PARAMETER_SET, 'laststop', str(time()))
	aelGlobals.write_log("Update done")
	STATUS = None
	clearMem("search: connected")


def get_Picture(title, what='Cover', lang='de'):
	cq = str(config.plugins.AdvancedEventLibrary.coverQuality.value) if config.plugins.AdvancedEventLibrary.coverQuality.value != "w1920" else 'original'
	posterquality = config.plugins.AdvancedEventLibrary.posterQuality.value
	posterDir = f"{getPictureDir()}poster/"
	coverDir = f"{getPictureDir()}cover/"
	tmdb.API_KEY = get_keys('tmdb')
	picture = None
	titleNyear = convertYearInTitle(title)
	title = convertSearchName(titleNyear[0])
	jahr = str(titleNyear[1])
	aelGlobals.write_log('################################################### themoviedb tv ##############################################')
	search = tmdb.Search()
	searchName = findEpisode(title)
	#	TODO: Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
	#	unkodierte URL: http://image.tmdb.org/t/p/
	tmdburl = b64decode(b"aHR0cDovL2ltYWdlLnRtZGIub3JnL3QvcC8=x"[:-1]).decode()
	if searchName:
		res = aelGlobals.callLibrary(search.tv, query=searchName[2], language=str(lang), year=jahr, include_adult=True, search_type='ngram')
	else:
		res = aelGlobals.callLibrary(search.tv, query=title, language=str(lang), year=jahr)
	if res and res['results']:
		reslist = []
		for item in res['results']:
			reslist.append(item['name'].lower())
		if searchName:
			bestmatch = get_close_matches(searchName[2].lower(), reslist, 1, 0.7)
			if not bestmatch:
				bestmatch = [searchName[2].lower()]
		else:
			bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
			if not bestmatch:
				bestmatch = [title.lower()]
		for item in res['results']:
			if item['name'].lower() in bestmatch and 'id' in item:
				idx = tmdb.TV(item['id'])
				if searchName and what == 'Cover':
					details = tmdb.TV_Episodes(item['id'], searchName[0], searchName[1])
					if details:
						epi = details.info(language=str(lang))
						if epi:
							imgs = details.images(language=str(lang))
							if imgs and 'stills' in imgs:
								picture = f"{tmdburl}{cq}{imgs['stills'][0]['file_path']}"
				if what == 'Cover' and not searchName:
					imgs = idx.images(language=str(lang))['backdrops']
					if imgs:
						picture = f"{tmdburl}{cq}{imgs[0]['file_path']}"
					if picture is None:
						imgs = idx.images()['backdrops']
						if imgs:
							picture = f"{tmdburl}{cq}{imgs[0]['file_path']}"
				if what == 'Poster':
					imgs = idx.images(language=str(lang))['posters']
					if imgs:
						picture = f"{tmdburl}{posterquality}{imgs[0]['file_path']}"
					if picture is None:
						imgs = idx.images()['posters']
						if imgs:
							picture = f"{tmdburl}{posterquality}{imgs[0]['file_path']}"
	aelGlobals.write_log('################################################### themoviedb movie ##############################################')
	if picture is None:
		search = tmdb.Search()
		res = aelGlobals.callLibrary(search.movie(query=title, language=str(lang), year=jahr))
		if res and res['results']:
			reslist = []
			for item in res['results']:
				reslist.append(item['title'].lower())
			bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
			if not bestmatch:
				bestmatch = [title.lower()]
			for item in res['results']:
				if item['title'].lower() in bestmatch and 'id' in item:
					idx = tmdb.Movies(item['id'])
					if what == 'Cover':
						imgs = idx.images(language=str(lang))['backdrops']
						if imgs:
							picture = f"{tmdburl}{cq}{imgs[0]['file_path']}"
						if picture is None:
							imgs = idx.images()['backdrops']
							if imgs:
								picture = f"{tmdburl}{cq}{imgs[0]['file_path']}"
					if what == 'Poster':
						imgs = idx.images(language=str(lang))['posters']
						if imgs:
							picture = f"{tmdburl}{posterquality}{imgs[0]['file_path']}"
						if picture is None:
							imgs = idx.images()['posters']
							if imgs:
								picture = f"{tmdburl}{posterquality}{imgs[0]['file_path']}"
	if picture is None:
		tvdb.KEYS.API_KEY = get_keys('tvdb')
		seriesid = None
		search = tvdb.Search()
		searchTitle = convertTitle2(title)
		response = aelGlobals.callLibrary(search.series, title=searchTitle, language=str(lang))
		if response:
			reslist = []
			for result in response:
				reslist.append(result['seriesName'].lower())
			bestmatch = get_close_matches(searchTitle.lower(), reslist, 1, 0.7)
			if not bestmatch:
				bestmatch = [searchTitle.lower()]
			for result in response:
				if bestmatch[0] in result['seriesName'].lower() or result['seriesName'].lower() in bestmatch[0]:
					seriesid = result['id']
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
					epilist.append(str(episode['episodeName']).lower())
				bestmatch = get_close_matches(title.lower(), epilist, 1, 0.7)
				if not bestmatch:
					bestmatch = [title.lower()]
				for episode in episoden:
					if str(episode['episodeName']).lower() in bestmatch[0]:
						if 'seriesId' in episode:
							seriesid = episode['seriesId']
						break
			showimgs = tvdb.Series_Images(seriesid)
			if showimgs:
				if what == 'Cover':
					response = aelGlobals.callLibrary(showimgs.fanart, language=str(lang))
					if response and str(response) != 'None':
						picture = 'https://www.thetvdb.com/banners/' + response[0]['fileName']
				if what == 'Poster':
					response = aelGlobals.callLibrary(showimgs.poster, language=str(lang))
					if response and str(response) != 'None':
						picture = 'https://www.thetvdb.com/banners/' + response[0]['fileName']
	if picture:
		aelGlobals.write_log('researching picture result ' + str(picture) + ' for ' + str(title))
	return picture


def get_MissingPictures(db, poster, cover):
	global STATUS
	posterDir = f"{getPictureDir()}poster/"
	coverDir = f"{getPictureDir()}cover/"
	pList = db.getMissingPictures()
	covers = 0
	posters = 0
	i = 0
	if pList[0]:
		for picture in pList[0]:
			if db.getblackListCover(convert2base64(picture)):
				pList[0].remove(picture)
	if pList[1]:
		for picture in pList[1]:
			if db.getblackListPoster(convert2base64(picture)):
				pList[1].remove(picture)
	if pList[0]:
		aelGlobals.write_log('found ' + str(len(pList[0])) + ' missing covers')
		for picture in pList[0]:
			i += 1
			STATUS = f"suche fehlendes Cover für {picture} ({i}/{len(pList[0])} | {covers}) "
			url = get_Picture(title=picture, what='Cover', lang='de')
			if url:
				covers += 1
				downloadImage(url, join(coverDir, convert2base64(picture) + '.jpg'))
			else:
				db.addblackListCover(convert2base64(picture))
		aelGlobals.write_log('have downloaded ' + str(covers) + ' missing covers')
	if pList[1]:
		aelGlobals.write_log('found ' + str(len(pList[1])) + ' missing posters')
		i = 0
		for picture in pList[1]:
			i += 1
			STATUS = f"suche fehlendes Poster für {picture} ({i}/{len(pList[1])} | {posters}) "
			url = get_Picture(title=picture, what='Poster', lang='de')
			if url:
				posters += 1
				downloadImage(url, join(posterDir, convert2base64(picture) + '.jpg'))
			else:
				db.addblackListPoster(convert2base64(picture))
		aelGlobals.write_log('have downloaded ' + str(posters) + ' missing posters')
	posters += poster
	covers += cover
	aelGlobals.write_log("found " + str(posters) + " posters")
	aelGlobals.write_log("found " + str(covers) + " covers")
	db.parameter(PARAMETER_SET, 'lastposterCount', str(posters))
	db.parameter(PARAMETER_SET, 'lastcoverCount', str(covers))


def writeTVStatistic(db):
	root = eServiceReference(str(service_types_tv + ' FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
	serviceHandler = eServiceCenter.getInstance()
	tvbouquets = serviceHandler.list(root).getContent("SN", True)
	for bouquet in tvbouquets:
		root = eServiceReference(str(bouquet[0]))
		serviceHandler = eServiceCenter.getInstance()
		ret = serviceHandler.list(root).getContent("SN", True)
		isInsPDict = bouquet[1] in sPDict
		if not isInsPDict or (isInsPDict and sPDict[bouquet[1]]):
			for (serviceref, servicename) in ret:
				count = db.getEventCount(serviceref)
				aelGlobals.write_log('There are ' + str(count) + ' events for ' + str(servicename) + ' in database')


def get_size(path):
	total_size = 0
	for dirpath, dirnames, filenames in walk(path):
		for f in filenames:
			fp = join(dirpath, f)
			total_size += getsize(fp)
	return str(round(float(total_size / 1024.0 / 1024.0), 1)) + 'M'


def createStatistics(db):
	DIR = f"{getPictureDir()}poster/"
	posterCount = len([name for name in listdir(DIR) if fileExists(join(DIR, name))])
	posterSize = check_output(['du', '-sh', DIR]).split()[0]
	DIR = f"{getPictureDir()}cover/"
	coverCount = len([name for name in listdir(DIR) if fileExists(join(DIR, name))])
	DIR = f"{getPictureDir()}preview/"
	previewCount = len([name for name in listdir(DIR) if fileExists(join(DIR, name))])
	DIR = f"{getPictureDir()}cover/"
	coverSize = check_output(['du', '-sh', DIR]).split()[0]
	DIR = f"{getPictureDir()}preview/"
	previewSize = check_output(['du', '-sh', DIR]).split()[0]
	inodes = check_output(['df', '-i', dir]).split()
	nodestr = f"{inodes[-4]} | {inodes[-5]} | {inodes[-2]}"
	db.parameter(PARAMETER_SET, 'posterCount', str(posterCount))
	db.parameter(PARAMETER_SET, 'coverCount', str(coverCount))
	db.parameter(PARAMETER_SET, 'previewCount', str(previewCount))
	db.parameter(PARAMETER_SET, 'posterSize', str(posterSize))
	db.parameter(PARAMETER_SET, 'coverSize', str(coverSize))
	db.parameter(PARAMETER_SET, 'previewSize', str(previewSize))
	db.parameter(PARAMETER_SET, 'usedInodes', str(nodestr))


def get_PictureList(title, what='Cover', count=20, b64title=None, lang='de', bingOption=''):
	cq = str(config.plugins.AdvancedEventLibrary.coverQuality.value) if config.plugins.AdvancedEventLibrary.coverQuality.value != "w1920" else 'original'
	posterquality = config.plugins.AdvancedEventLibrary.posterQuality.value
	posterDir = f"{getPictureDir()}poster/"
	coverDir = f"{getPictureDir()}cover/"
	tmdb.API_KEY = get_keys('tmdb')
	# TODO: Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
	# unkodierte URL: http://image.tmdb.org/t/p/
	tmdburl = b64decode(b"aHR0cDovL2ltYWdlLnRtZGIub3JnL3QvcC9vcmlnaW5hbA==l"[:-1]).decode()
	pictureList = []
	titleNyear = convertYearInTitle(title)
	title = convertSearchName(titleNyear[0])
	jahr = str(titleNyear[1])
	aelGlobals.write_log('searching ' + str(what) + ' for ' + str(title) + ' with language = ' + str(lang))
	if not b64title:
		b64title = convert2base64(title)
	tvdb.KEYS.API_KEY = get_keys('tvdb')
	seriesid = None
	search = tvdb.Search()
	searchTitle = convertTitle2(title)
	result = {}
	response = aelGlobals.callLibrary(search.series, title=searchTitle, language=str(lang))
	if response:
		reslist = []
		for result in response:
			reslist.append(result['seriesName'].lower())
		bestmatch = get_close_matches(searchTitle.lower(), reslist, 1, 0.7)
		if not bestmatch:
			bestmatch = [searchTitle.lower()]
		for result in response:
			if bestmatch[0] in result['seriesName'].lower() or result['seriesName'].lower() in bestmatch[0]:
				seriesid = result['id']
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
				epilist.append(str(episode['episodeName']).lower())
			bestmatch = get_close_matches(title.lower(), epilist, 1, 0.7)
			if not bestmatch:
				bestmatch = [title.lower()]
			for episode in episoden:
				if str(episode['episodeName']).lower() in bestmatch[0]:
					if 'seriesId' in episode:
						seriesid = episode['seriesId']
						epiname = ' - ' + str(episode['episodeName'])
					break
		showimgs = tvdb.Series_Images(seriesid)
		if showimgs:
			if what == 'Cover':
				response = aelGlobals.callLibrary(showimgs.fanart, language=str(lang))
				if response and str(response) != 'None':
					for img in response:
						itm = [result['seriesName'] + epiname, what, str(img['resolution']) + ' gefunden auf TVDb', 'https://www.thetvdb.com/banners/' + img['fileName'], join(coverDir, b64title + '.jpg'), convert2base64(img['fileName']) + '.jpg']
						pictureList.append((itm,))
			if what == 'Poster':
				response = aelGlobals.callLibrary(showimgs.poster, language=str(lang))
				if response and str(response) != 'None':
					for img in response:
						itm = [result['seriesName'] + epiname, what, str(img['resolution']) + ' gefunden auf TVDb', 'https://www.thetvdb.com/banners/' + img['fileName'], join(posterDir, b64title + '.jpg'), convert2base64(img['fileName']) + '.jpg']
						pictureList.append((itm,))
	search = tmdb.Search()
	searchName = findEpisode(title)
	if searchName:
		res = aelGlobals.callLibrary(search.tv, query=searchName[2], language=str(lang), year=jahr, include_adult=True, search_type='ngram')
	else:
		res = aelGlobals.callLibrary(search.tv, query=title, language=str(lang), year=jahr)
	if res and res['results']:
		reslist = []
		for item in res['results']:
			reslist.append(item['name'].lower())
		if searchName:
			bestmatch = get_close_matches(searchName[2].lower(), reslist, 4, 0.7)
			if not bestmatch:
				bestmatch = [searchName[2].lower()]
		else:
			bestmatch = get_close_matches(title.lower(), reslist, 4, 0.7)
			if not bestmatch:
				bestmatch = [title.lower()]
		for item in res['results']:
			aelGlobals.write_log('found on TMDb TV ' + str(item['name']))
			if item['name'].lower() in bestmatch and 'id' in item:
				idx = tmdb.TV(item['id'])
				if searchName and what == 'Cover':
					details = tmdb.TV_Episodes(item['id'], searchName[0], searchName[1])
					if details:
						epi = details.info(language=str(lang))
						if epi:
							imgs = details.images(language=str(lang))
							if imgs and 'stills' in imgs:
								for img in imgs['stills']:
										imgsize = str(img['width']) + 'x' + str(img['height'])
										itm = [item['name'] + ' - ' + epi['name'], what, str(imgsize) + ' gefunden auf TMDb TV', f"{tmdburl}{cq}{img['file_path']}", join(coverDir, b64title + '.jpg'), convert2base64(img['file_path']) + '.jpg']
										pictureList.append((itm,))
				if what == 'Cover' and not searchName:
					imgs = idx.images(language=str(lang))['backdrops']
					if imgs:
						for img in imgs:
							imgsize = str(img['width']) + 'x' + str(img['height'])
							itm = [item['name'], what, str(imgsize) + ' gefunden auf TMDb TV', f"{tmdburl}{cq}{img['file_path']}", join(coverDir, b64title + '.jpg'), convert2base64(img['file_path']) + '.jpg']
							pictureList.append((itm,))
					if len(imgs) < 2:
						imgs = idx.images()['backdrops']
						if imgs:
							for img in imgs:
								imgsize = str(img['width']) + 'x' + str(img['height'])
								itm = [item['name'], what, str(imgsize) + ' gefunden auf TMDb TV', f"{tmdburl}{cq}{img['file_path']}", join(coverDir, b64title + '.jpg'), convert2base64(img['file_path']) + '.jpg']
								pictureList.append((itm,))
				if what == 'Poster':
					imgs = idx.images(language=str(lang))['posters']
					if imgs:
						for img in imgs:
							imgsize = str(img['width']) + 'x' + str(img['height'])
							itm = [item['name'], what, str(imgsize) + ' gefunden auf TMDb TV', f"{tmdburl}{posterquality}{img['file_path']}", join(posterDir, b64title + '.jpg'), convert2base64(img['file_path']) + '.jpg']
							pictureList.append((itm,))
					if len(imgs) < 2:
						imgs = idx.images()['posters']
						if imgs:
							for img in imgs:
								imgsize = str(img['width']) + 'x' + str(img['height'])
								itm = [item['name'], what, str(imgsize) + ' gefunden auf TMDb TV', f"{tmdburl}{posterquality}{img['file_path']}", join(posterDir, b64title + '.jpg'), convert2base64(img['file_path']) + '.jpg']
								pictureList.append((itm,))
	search = tmdb.Search()
	res = search.movie(query=title, language=str(lang), year=jahr) if jahr != '' else search.movie(query=title, language=str(lang))
	if res and res['results']:
		reslist = []
		for item in res['results']:
			reslist.append(item['title'].lower())
		bestmatch = get_close_matches(title.lower(), reslist, 4, 0.7)
		if not bestmatch:
			bestmatch = [title.lower()]
		for item in res['results']:
			aelGlobals.write_log('found on TMDb Movie ' + str(item['title']))
			if item['title'].lower() in bestmatch and 'id' in item:
				idx = tmdb.Movies(item['id'])
				if what == 'Cover':
					imgs = idx.images(language=str(lang))['backdrops']
					if imgs:
						for img in imgs:
							imgsize = str(img['width']) + 'x' + str(img['height'])
							itm = [item['title'], what, str(imgsize) + ' gefunden auf TMDb Movie', f"{tmdburl}{cq}{img['file_path']}", join(coverDir, b64title + '.jpg'), convert2base64(img['file_path']) + '.jpg']
							pictureList.append((itm,))
					if len(imgs) < 2:
						imgs = idx.images()['backdrops']
						if imgs:
							for img in imgs:
								imgsize = str(img['width']) + 'x' + str(img['height'])
								itm = [item['title'], what, str(imgsize) + ' gefunden auf TMDb Movie', f"{tmdburl}{cq}{img['file_path']}", join(coverDir, b64title + '.jpg'), convert2base64(img['file_path']) + '.jpg']
								pictureList.append((itm,))
				if what == 'Poster':
					imgs = idx.images(language=str(lang))['posters']
					if imgs:
						for img in imgs:
							imgsize = str(img['width']) + 'x' + str(img['height'])
							itm = [item['title'], what, str(imgsize) + ' gefunden auf TMDb Movie', f"{tmdburl}{posterquality}{img['file_path']}", join(posterDir, b64title + '.jpg'), convert2base64(img['file_path']) + '.jpg']
							pictureList.append((itm,))
					if len(imgs) < 2:
						imgs = idx.images()['posters']
						if imgs:
							for img in imgs:
								imgsize = str(img['width']) + 'x' + str(img['height'])
								itm = [item['title'], what, str(imgsize) + ' gefunden auf TMDb Movie', f"{tmdburl}{posterquality}{img['file_path']}", join(posterDir, b64title + '.jpg'), convert2base64(img['file_path']) + '.jpg']
								pictureList.append((itm,))
	if not pictureList and what == 'Poster':
		# TODO: Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
		# url = f"http://www.omdbapi.com/?apikey={get_keys('omdb')}&t={title}"
		# unkodierte URL: "http://www.omdbapi.com"
		url = b64decode(b"aHR0cDovL3d3dy5vbWRiYXBpLmNvbQ==J"[:-1]).decode()
		errmsg, res = aelGlobals.getAPIdata(url, params={"apikey": get_keys("omdb"), "t": title})
		if errmsg:
			aelGlobals.write_log("[{DEFAULT_MODULE_NAME}] API download error in module 'get_PictureList: OMDB call'")
		if res['Response'] == "True" and res['Poster'].startswith('http'):
			itm = [res['Title'], what, 'OMDB', res['Poster'], join(posterDir, b64title + '.jpg'), convert2base64('omdbPosterFile') + '.jpg']
			pictureList.append((itm,))
		# TODO: Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
		# tvmazeurl = f"http://api.tvmaze.com/search/shows?q={title}"
		# unkodierte URL: "http://api.tvmaze.com/search/shows"
		tvmazeurl = b64decode(b"aHR0cDovL2FwaS50dm1hemUuY29tL3NlYXJjaC9zaG93cw==F"[:-1]).decode()
		errmsg, res = aelGlobals.getAPIdata(tvmazeurl, params={"q": title})
		if errmsg:
			aelGlobals.write_log("[{DEFAULT_MODULE_NAME}] API download error in module 'get_PictureList: TVMAZE call'")
		if res:
			reslist = []
			for item in res:
				reslist.append(item['show']['name'].lower())
			bestmatch = get_close_matches(title.lower(), reslist, 4, 0.7)
			if not bestmatch:
				bestmatch = [title.lower()]
			for item in res:
				if item['show']['name'].lower() == bestmatch[0] and item['show']['image']:
					itm = [item['show']['name'], what, 'maze.tv', item['show']['image']['original'], join(posterDir, b64title + '.jpg'), convert2base64('mazetvPosterFile') + '.jpg']
					pictureList.append((itm,))
	if not pictureList:
		BingSearch = BingImageSearch(f"{title}{bingOption}", count, what)
		res = BingSearch.search()
		i = 0
		for image in res:
			if what == 'Poster':
				itm = [title, what, 'gefunden auf bing.com', image, join(posterDir, b64title + '.jpg'), convert2base64('bingPoster_' + str(i)) + '.jpg']
			else:
				itm = [title, what, 'gefunden auf bing.com', image, join(coverDir, b64title + '.jpg'), convert2base64('bingCover_' + str(i)) + '.jpg']
			pictureList.append((itm,))
			i += 1
	if pictureList:
		idx = 0
		aelGlobals.write_log('found ' + str(len(pictureList)) + ' images for ' + str(title), aelGlobals.addlog)
		failed = []
		while idx <= int(count) and idx < len(pictureList):
			aelGlobals.write_log('Image : ' + str(pictureList[idx]), aelGlobals.addlog)
			if not downloadImage2(pictureList[idx][0][3], join('/tmp/', pictureList[idx][0][5])):
				failed.insert(0, idx)
			idx += 1
		for erroridx in failed:
			del pictureList[erroridx]
		return pictureList[:count]
	else:
		itm = ["Keine Ergebnisse gefunden", "Bildname '" + str(b64title) + ".jpg'", None, None, None, None]
		pictureList.append((itm,))
		return pictureList


def get_searchResults(title, lang='de'):
	tmdb.API_KEY = get_keys('tmdb')
	resultList = []
	titleNyear = convertYearInTitle(title)
	title = convertSearchName(titleNyear[0])
	jahr = str(titleNyear[1])
	aelGlobals.write_log('searching results for ' + str(title) + ' with language = ' + str(lang))
	searchName = findEpisode(title)
	search = tmdb.Search()
	if searchName:
		res = aelGlobals.callLibrary(search.tv, query=searchName[2], language=lang, year=jahr, include_adult=True, search_type='ngram')
	else:
		res = aelGlobals.callLibrary(search.tv, query=title, language=lang, year=jahr)
	if res and res['results']:
		reslist = []
		for item in res['results']:
			reslist.append(item['name'].lower())
		if searchName:
			bestmatch = get_close_matches(searchName[2].lower(), reslist, 10, 0.4)
			if not bestmatch:
				bestmatch = [searchName[2].lower()]
		else:
			bestmatch = get_close_matches(title.lower(), reslist, 10, 0.4)
			if not bestmatch:
				bestmatch = [title.lower()]
		for item in res['results']:
			if item['name'].lower() in bestmatch:
				countries = ""
				year = ""
				genres = ""
				rating = ""
				fsk = ""
				desc = ""
				epiname = ''
				if searchName:
					details = tmdb.TV_Episodes(item['id'], searchName[0], searchName[1])
					if details:
						epi = details.info(language=str(lang))
						if 'name' in epi:
							epiname = ' - S' + searchName[0] + 'E' + searchName[1] + ' - ' + epi['name']
						if 'air_date' in epi:
							year = epi['air_date'][:4]
						if 'vote_average' in epi:
							rating = epi['vote_average']
						if 'overview' in epi:
							desc = epi['overview']
						if item['origin_country']:
							for country in item['origin_country']:
								countries = countries + country + ' | '
							countries = countries[:-3]
						if item['genre_ids']:
							for genre in item['genre_ids']:
								genres = genres + tmdb_genres[genre] + '-Serie '
							maxGenres = genres.split()
							if maxGenres and len(maxGenres) >= 1:
								genres = maxGenres[0]
						if 'id' in item:
							details = tmdb.TV(item['id'])
							for country in details.content_ratings(language='de')['results']:
								if str(country['iso_3166_1']) == "DE":
									fsk = str(country['rating'])
									break
				else:
					if 'overview' in item:
						desc = item['overview']
					if item['origin_country']:
						for country in item['origin_country']:
							countries = countries + country + ' | '
						countries = countries[:-3]
					if 'first_air_date' in item:
						year = item['first_air_date'][:4]
					if item['genre_ids']:
						for genre in item['genre_ids']:
							genres = genres + tmdb_genres[genre] + '-Serie '
					if 'vote_average' in item and item['vote_average'] != "0":
						rating = str(item['vote_average'])
					if 'id' in item:
						details = tmdb.TV(item['id'])
						for country in details.content_ratings(language='de')['results']:
							if str(country['iso_3166_1']) == "DE":
								fsk = str(country['rating'])
								break
				itm = [str(item['name']) + epiname, str(countries), str(year), str(genres), str(rating), str(fsk), "TMDb TV", desc]
				resultList.append((itm,))
		search = tmdb.Search()
	res = search.movie(query=title, language=lang, year=jahr) if jahr != '' else search.movie(query=title, language=lang)
	if res and res['results']:
		reslist = []
		for item in res['results']:
			reslist.append(item['title'].lower())
		bestmatch = get_close_matches(title.lower(), reslist, 10, 0.4)
		if not bestmatch:
			bestmatch = [title.lower()]
		for item in res['results']:
			if item['title'].lower() in bestmatch:
				countries = ""
				year = ""
				genres = ""
				rating = ""
				fsk = ""
				desc = ""
				if 'overview' in item:
					desc = item['overview']
				if 'release_date' in item:
					year = item['release_date'][:4]
				if item['genre_ids']:
					for genre in item['genre_ids']:
						genres = genres + tmdb_genres[genre] + ' '
				if 'vote_average' in item and item['vote_average'] != "0":
					rating = str(item['vote_average'])
				if 'id' in item:
					details = tmdb.Movies(item['id'])
					for country in details.releases(language='de')['countries']:
						if str(country['iso_3166_1']) == "DE":
							fsk = str(country['certification'])
							break
					for country in details.info(language='de')['production_countries']:
						countries = countries + country['iso_3166_1'] + " | "
					countries = countries[:-3]
				itm = [str(item['title']), str(countries), str(year), str(genres), str(rating), str(fsk), "TMDb Movie", desc]
				resultList.append((itm,))
	tvdb.KEYS.API_KEY = get_keys('tvdb')
	search = tvdb.Search()
	searchTitle = convertTitle2(title)
	searchName = findEpisode(title)
	response = aelGlobals.callLibrary(search.series, title=searchTitle, language="de")
	if response:
		reslist = []
		for result in response:
			reslist.append(result['seriesName'].lower())
		bestmatch = get_close_matches(title.lower(), reslist, 10, 0.4)
		if not bestmatch:
			bestmatch = [title.lower()]
		for result in response:
			if result['seriesName'].lower() in bestmatch:
				foundEpisode = False
				seriesid = None
				countries = ""
				year = ""
				genres = ""
				rating = ""
				fsk = ""
				desc = ""
				epiname = ""
				seriesid = result['id']
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
							epilist.append(episode['episodeName'].lower())
						bestmatch = get_close_matches(title.lower(), epilist, 1, 0.6)
						if not bestmatch:
							bestmatch = [title.lower()]
						for episode in episoden:
							if episode['episodeName'].lower() == bestmatch[0]:
								foundEpisode = True
								if 'episodeName' in episode:
									epiname = ' - S' + searchName[0] + 'E' + searchName[1] + ' - ' + episode['episodeName'] if searchName else ' - ' + episode['episodeName']
								if 'overview' in episode:
									desc = episode['overview']
								if 'firstAired' in episode:
									year = episode['firstAired'][:4]
								if 'siteRating' in episode and episode['siteRating'] != '0' and episode['siteRating'] != 'None':
									rating = episode['siteRating']
								rateddict = {"R": "18", "TV-MA": "18", "TV-PG": "16", "TV-14": "12", "TV-Y7": "6", "PG-13": "12", "PG": "6", "G": "16"}
								fsk = rateddict.get(episode.get("contentRating", ""), "")
								if 'contentRating' in episode:
									if "TV-MA" in str(episode['contentRating']):
										fsk = "18"
									elif "TV-PG" in str(episode['contentRating']):
										fsk = "16"
									elif "TV-14" in str(episode['contentRating']):
										fsk = "12"
									elif "TV-Y7" in str(episode['contentRating']):
										fsk = "6"
								if response:
									if 'genre' in response and response['genre']:
										for genre in response['genre']:
											genres = genres + genre + '-Serie '
									genres = genres.replace("Documentary", "Dokumentation").replace("Children", "Kinder")
									if response['network'] in networks:
										countries = networks[response['network']]
								itm = [str(result['seriesName'] + epiname), str(countries), str(year), str(genres), str(rating), str(fsk), "The TVDB", desc]
								resultList.append((itm,))
								break
						if response and not foundEpisode and 'overview' in response:
							desc = response['overview']
						if response['network'] in networks:
							countries = networks[response['network']]
						year = response['firstAired'][:4]
						for genre in response['genre']:
							genres = genres + genre + '-Serie '
						genres = genres.replace("Documentary", "Dokumentation").replace("Children", "Kinder")
						if response['siteRating'] != "0":
							rating = response['siteRating']
						if "TV-MA" in str(response['rating']):
							fsk = "18"
						elif "TV-PG" in str(response['rating']):
							fsk = "16"
						elif "TV-14" in str(response['rating']):
							fsk = "12"
						elif "TV-Y7" in str(response['rating']):
							fsk = "6"
						itm = [str(result['seriesName']), str(countries), str(year), str(genres), str(rating), str(fsk), "The TVDB", desc]
						resultList.append((itm,))
	# TODO: Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
	# tvmazeurl = f"http://api.tvmaze.com/search/shows?q={title}"
	# unkodierte URL: "http://api.tvmaze.com/search/shows"
	tvmazeurl = b64decode(b"aHR0cDovL2FwaS50dm1hemUuY29tL3NlYXJjaC9zaG93cw==L"[:-1]).decode()
	errmsg, res = aelGlobals.getAPIdata(tvmazeurl, params={"q": title})
	if errmsg:
		aelGlobals.write_log("[{DEFAULT_MODULE_NAME}] API download error in module 'get_searchResults: TVMAZE call #1'")
	if res:
		reslist = []
		for item in res:
			reslist.append(item['show']['name'].lower())
		bestmatch = get_close_matches(title.lower(), reslist, 10, 0.4)
		if not bestmatch:
			bestmatch = [title.lower()]
		for item in res:
			if item['show']['name'].lower() in bestmatch:
				countries = ""
				year = ""
				genres = ""
				rating = ""
				fsk = ""
				desc = ""
				if item['show']['summary']:
					desc = item['show']['summary']
				if item['show']['network']['country']:
					countries = item['show']['network']['country']['code']
				if item['show']['premiered']:
					year = item['show']['premiered'][:4]
				if item['show']['genres']:
					for genre in item['show']['genres']:
						genres = genres + genre + '-Serie '
					genres = genres.replace("Documentary", "Dokumentation").replace("Children", "Kinder")
				if item['show']['rating']['average']:
					rating = item['show']['rating']['average']
				itm = [str(item['show']['name']), str(countries), str(year), str(genres), str(rating), str(fsk), "maze.tv", desc]
				resultList.append((itm,))
	# TODO: Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
	# url = f"http://www.omdbapi.com/?apikey={get_keys('omdb')}&s={title}&page=1"
	# unkodierte URL: "http://www.omdbapi.com"
	omdburl = b64decode(b"aHR0cHM6Ly9saXZlLnR2c3BpZWxmaWxtLmRlL3N0YXRpYy9icm9hZGNhc3QvbGlzdC8=7"[:-1]).decode()
	omdbapi = get_keys('omdb')
	errmsg, res = aelGlobals.getAPIdata(omdburl, params={"apikey": omdbapi, "s": title, "page": 1})
	if errmsg:
		aelGlobals.write_log("[{DEFAULT_MODULE_NAME}] API download error in module 'get_searchResults: TVMAZE call #2'")
	if res and res.get("Response", False):
		reslist = []
		for result in res.get("Search", []):
			reslist.append(result['Title'].lower())
		bestmatch = get_close_matches(title.lower(), reslist, 10, 0.4)
		if not bestmatch:
			bestmatch = [title.lower()]
		for result in res.get("Search", []):
			if result['Title'].lower() in bestmatch:
				# TODO: Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
				# url = f"http://www.omdbapi.com/?apikey={get_keys('omdb')}&i={result['imdbID']}"
				errmsg, res = aelGlobals.getAPIdata(omdburl, params={"apikey": omdbapi, "i": result.get("imdbID", "")})
				if errmsg:
					aelGlobals.write_log("[{DEFAULT_MODULE_NAME}] API download error in module 'get_searchResults: TVMAZE call #3'")
				if res:
					countries = ""
					year = ""
					genres = ""
					rating = ""
					fsk = ""
					desc = ""
					if res['Response'] == "True":
						if res['Plot']:
							desc = res['Plot']
						if res['Year']:
							year = res['Year'][:4]
						if res['Genre'] != "N/A":
							types = ' '
							if res['Type'] and res['Type'] == 'series':
								types = '-Serie '
							resgenres = res['Genre'].split(', ')
							for genre in resgenres:
								genres = genres + genre + types
							genres = genres.replace("Documentary", "Dokumentation").replace("Children", "Kinder")
						if res['imdbRating'] != "N/A":
							rating = res['imdbRating']
						if res['Country'] != "N/A":
							rescountries = res['Country'].split(', ')
							for country in rescountries:
								countries = countries + country + ' | '
							countries = countries[:-2].replace('West Germany', 'DE').replace('East Germany', 'DE').replace('Germany', 'DE').replace('France', 'FR').replace('Canada', 'CA').replace('Austria', 'AT').replace('Switzerland', 'S').replace('Belgium', 'B').replace('Spain', 'ESP').replace('Poland', 'PL').replace('Russia', 'RU').replace('Czech Republic', 'CZ').replace('Netherlands', 'NL').replace('Italy', 'IT')
						rateddict = {"R": "18", "TV-MA": "18", "TV-PG": "16", "TV-14": "12", "TV-Y7": "6", "PG-13": "12", "PG": "6", "G": "16"}
						fsk = rateddict.get(res.get("Rated", ""), "")
						itm = [res['Title'], countries, str(year), genres, str(rating), fsk, "omdb", desc]
						resultList.append((itm,))
	aelGlobals.write_log('search results : ' + str(resultList))
	if resultList:
		return (sorted(resultList, key=lambda x: x[0]))
	else:
		itm = ["Keine Ergebnisse gefunden", None, None, None, None, None, None, None]
		resultList.append((itm,))
		return resultList


def downloadTVSImage(tvsImage, imgname):
	if not fileExists(imgname):
		ir = get(tvsImage, stream=True, timeout=4)
		if ir.status_code == 200:
			with open(imgname, 'wb') as f:
				ir.raw.decode_content = True
				copyfileobj(ir.raw, f)
				f.close()
			ir = None
			return True


def downloadTVMovieImage(tvMovieImage, imgname):
	if not fileExists(imgname):
#		TODO: Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
#		imgurl = 'http://images.tvmovie.de/' + str(coverqualityDict[config.plugins.AdvancedEventLibrary.coverQuality.value]) + '/Center/' + tvMovieImage
#		unkodierte url: http://images.tvmovie.de
		tvmovieurl = b64decode(b"aHR0cDovL2ltYWdlcy50dm1vdmllLmRlR"[:-1]).decode()
		imgurl = f"{tvmovieurl}/{coverqualityDict[config.plugins.AdvancedEventLibrary.coverQuality.value]}/Center/{tvMovieImage}"
		ir = get(imgurl, stream=True, timeout=4)
		if ir.status_code == 200:
			with open(imgname, 'wb') as f:
				ir.raw.decode_content = True
				copyfileobj(ir.raw, f)
				f.close()
			ir = None
			return True
		else:
			return False
	else:
		return True


def getImageFile(path, eventName):
	name = eventName
	pictureName = convert2base64(name) + '.jpg'
	imageFileName = join(path, pictureName)
	if (exists(imageFileName)):
		return imageFileName
	else:
		name = convertTitle(eventName)
		pictureName = convert2base64(name) + '.jpg'
		imageFileName = join(path, pictureName)
		if (exists(imageFileName)):
			return imageFileName
		else:
			name = convertTitle2(eventName)
			pictureName = convert2base64(name) + '.jpg'
			imageFileName = join(path, pictureName)
			if (exists(imageFileName)):
				return imageFileName
	if 'cover' in path and config.plugins.AdvancedEventLibrary.UsePreviewImages.value:
		ppath = path.replace('cover', 'preview')
		imageFileName = getPreviewImageFile(ppath, eventName)
		if imageFileName:
			return imageFileName


def getPreviewImageFile(path, eventName):
	name = eventName
	pictureName = convert2base64(name) + '.jpg'
	imageFileName = join(path, pictureName)
	if (exists(imageFileName)):
		return imageFileName
	else:
		name = convertTitle(eventName)
		pictureName = convert2base64(name) + '.jpg'
		imageFileName = join(path, pictureName)
		if (exists(imageFileName)):
			return imageFileName
		else:
			name = convertTitle2(eventName)
			pictureName = convert2base64(name) + '.jpg'
			imageFileName = join(path, pictureName)
			if (exists(imageFileName)):
				return imageFileName


class AELGlobals:
	CURRENTVERSION = 132
	AGENTS = [
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
			"Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
			"Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)",
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edge/87.0.664.75",
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363"
			]
	DESKTOPSIZE = getDesktop(0).size()
	TEMPPATH = "/var/volatile/tmp"
# TODO: später wieder auf TEMPPATH setzen
#	LOGFILE = join(TEMPPATH, "AdvancedEventLibrary.log")
	LOGPATH = "/home/root/logs/"
	LOGFILE = join(LOGPATH, "ael_logfile.log")
	SKINPATH = resolveFilename(SCOPE_CURRENT_SKIN)  # /usr/share/enigma2/MetrixHD/
	SHAREPATH = resolveFilename(SCOPE_SKIN_IMAGE)  # /usr/share/enigma2/
	CONFIGPATH = resolveFilename(SCOPE_CONFIG, "AEL/")  # /etc/enigma2/AEL/
	PYTHONPATH = eEnv.resolve("${libdir}/enigma2/python/")  # /usr/lib/enigma2/python/
	PLUGINPATH = resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/AdvancedEventLibrary/")  # /usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary
	SKINPATH = f"{PLUGINPATH}skin/1080/" if DESKTOPSIZE.width() == 1920 else f"{PLUGINPATH}skin/720/"
	MAPFILE = join(CONFIGPATH, "tvs_mapping.txt")

	def __init__(self):
		self.saving = False
		self.STATUS = None
		self.addlog = config.plugins.AdvancedEventLibrary.Log.value

	def setStatus(self, text=None):
		self.STATUS = text

	def write_log(self, svalue, module=DEFAULT_MODULE_NAME):
		t = localtime()
		logtime = '%02d:%02d:%02d' % (t.tm_hour, t.tm_min, t.tm_sec)
		with open(self.LOGFILE, "a") as f:
			f.write(f"{logtime} : [{module}] - {svalue}\n")

	def getAPIdata(self, url, params=None):
		headers = {"User-Agent": choice(self.AGENTS)}
		jsondict = {}
		try:
			response = get(url, params=params, headers=headers, timeout=(3.05, 6))
			response.raise_for_status()
			status = response.status_code
			if status == 200:
				jsondict = loads(response.content)
			else:
				errmsg = f"[{DEFAULT_MODULE_NAME}] API server access ERROR, response code: {status}"
			return "", jsondict
		except exceptions.RequestException as errmsg:
			aelGlobals.write_log(f"[{DEFAULT_MODULE_NAME}] ERROR in module 'getAPIdata': {errmsg}")
			return errmsg, {}

	def getHTMLdata(self, url, params=None):
		headers = {"User-Agent": choice(self.AGENTS)}
		try:
			response = get(url, params=params, headers=headers, timeout=(3.05, 6))
			response.raise_for_status()
			htmldata = response.text
			return "", htmldata
		except exceptions.RequestException as errmsg:
			aelGlobals.write_log(f"[{DEFAULT_MODULE_NAME}] ERROR in module 'getHTMLdata': {errmsg}")
			return errmsg, {}

	def callLibrary(self, libcall, **kwargs):
		try:  # mandatory because called library raises an error when no result
			if not kwargs.get("year", ""):  # in case 'year' is empty string
				kwargs.pop("year", "x")
			response = libcall(**kwargs)
		except Exception:
			try:  # 2nd try without language and/or without year
				response = libcall(**kwargs.pop("language", None).pop("year", None))
			except Exception:
				response = ""
		return response


aelGlobals = AELGlobals()

########################################### DB Helper Class #######################################################


class DB_Functions(object):
	@staticmethod
	def dict_factory(cursor, row):
		d = {}
		for idx, col in enumerate(cursor.description):
			d[col[0]] = row[idx]
		return d

	def __init__(self, db_file):
		createDirs(dir)
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
			aelGlobals.write_log("Tabelle 'eventInfo' hinzugefügt")
		# create table blackList
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='blackList';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE [blackList] ([base64title] TEXT NOT NULL,PRIMARY KEY ([base64title]))"
			cur.execute(query)
			self.conn.commit()
			aelGlobals.write_log("Tabelle 'blackList' hinzugefügt")
		# create table blackListCover
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='blackListCover';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE [blackListCover] ([base64title] TEXT NOT NULL,PRIMARY KEY ([base64title]))"
			cur.execute(query)
			self.conn.commit()
			aelGlobals.write_log("Tabelle 'blackListCover' hinzugefügt")
		# create table blackListPoster
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='blackListPoster';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE [blackListPoster] ([base64title] TEXT NOT NULL,PRIMARY KEY ([base64title]))"
			cur.execute(query)
			self.conn.commit()
			aelGlobals.write_log("Tabelle 'blackListPoster' hinzugefügt")
		# create table liveOnTV
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='liveOnTV';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE [liveOnTV] (eid INTEGER NOT NULL, id TEXT,subtitle TEXT,image TEXT,year TEXT,fsk TEXT,rating TEXT,title TEXT,airtime INTEGER NOT NULL,leadText TEXT,conclusion TEXT,categoryName TEXT,season TEXT,episode TEXT,genre TEXT,country TEXT,imdb TEXT,sref TEXT NOT NULL, PRIMARY KEY ([eid],[airtime],[sref]))"
			cur.execute(query)
			self.conn.commit()
			aelGlobals.write_log("Tabelle 'liveOnTV' hinzugefügt")
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
			aelGlobals.write_log("Tabelle 'imageBlackList' hinzugefügt")
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='parameters';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE `parameters` ( `name` TEXT NOT NULL UNIQUE, `value` TEXT, PRIMARY KEY(`name`) )"
			cur.execute(query)
			self.conn.commit()
			aelGlobals.write_log("Tabelle 'parameters' hinzugefügt")
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
		if action == PARAMETER_GET:
			query = "SELECT value FROM parameters WHERE name = ?"
			cur.execute(query, (name,))
			rows = cur.fetchall()
			if rows:
				if rows[0][0] == "False":
					ret = False
				elif rows[0][0] == "True":
					ret = True
				else:
					ret = rows[0][0]
				return ret
			else:
				return default
		elif action == PARAMETER_SET and value or value is False:
			if value is False:
				val = "False"
			elif value is True:
				val = "True"
			else:
				val = value
			query = "REPLACE INTO parameters (name,value) VALUES (?,?)"
			cur.execute(query, (name, val))
			self.conn.commit()
			return value

	def addTitleInfo(self, base64title, title, genre, year, rating, fsk, country, trailer=None):
		now = str(time())
		cur = self.conn.cursor()
		query = "insert or ignore into eventInfo (base64title,title,genre,year,rating,fsk,country,gDate,trailer) values (?,?,?,?,?,?,?,?,?);"
		cur.execute(query, (base64title, str(title), str(genre), year, rating, fsk, str(country), now, trailer))
		self.conn.commit()

	def addliveTV(self, records):
		cur = self.conn.cursor()
		cur.executemany('insert or ignore into liveOnTV values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);', records)
		aelGlobals.write_log("have inserted " + str(cur.rowcount) + " events into database")
		self.conn.commit()
		# self.parameter(PARAMETER_SET, 'lastadditionalDataCount', str(cur.rowcount))

	def updateTitleInfo(self, title, genre, year, rating, fsk, country, base64title):
		now = str(time())
		cur = self.conn.cursor()
		query = "update eventInfo set title = ?, genre = ?, year = ?, rating = ?, fsk = ?, country = ?, gDate = " + now + " where base64title = ?;"
		cur.execute(query, (str(title), str(genre), year, rating, fsk, str(country), base64title))
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
		cur.execute(query, (str(image), str(genre), year, rating, fsk, str(country), eid))
		self.conn.commit()

	def updateliveTV(self, id, subtitle, image, year, fsk, rating, leadText, conclusion, categoryName, season, episode, genre, country, imdb, title, airtime):
		low = airtime - 360
		high = airtime + 360
		cur = self.conn.cursor()
		query = "update liveOnTV set id = ?, subtitle = ?, image = ?, year = ?, fsk = ?, rating = ?, leadText = ?, conclusion = ?, categoryName = ?, season = ?, episode = ?, genre = ?, country = ?, imdb = ? where title = ? AND airtime BETWEEN ? AND ? AND id = 'in progress';"
		cur.execute(query, (id, str(subtitle), image, year, fsk, rating, str(leadText), str(conclusion), str(categoryName), season, episode, str(genre), country, imdb, str(title), low, high))
		self.conn.commit()

#	def updateliveTVS(self, id,subtitle,image,year,fsk,rating,leadText,conclusion,categoryName,season,episode,genre,country, imdb, sref, airtime):
#		low = airtime - 150
#		high = airtime + 150
#		cur = self.conn.cursor()
#		query = "update liveOnTV set id = ?, subtitle = ?, image = ?, year = ?, fsk = ?, rating = ?, leadText = ?, conclusion = ?, categoryName = ?, season = ?, episode = ?, genre = ?, country = ?, imdb = ? where sref = ? AND airtime BETWEEN ? AND ? AND id = 'in progress';"
#		cur.execute(query,(id, str(subtitle).decode('utf8'), str(image).decode('utf8'), year, fsk, rating, str(leadText).decode('utf8'), str(conclusion).decode('utf8'), str(categoryName).decode('utf8'), season, episode, str(genre).decode('utf8'), country, str(imdb).decode('utf8'), str(sref).decode('utf8'), low, high))
#		self.conn.commit()

	def updateliveTVS(self, id, subtitle, image, year, fsk, rating, leadText, conclusion, categoryName, season, episode, genre, country, imdb, sref, airtime, title):
		updatetRows = 0
		low = airtime - 150
		high = airtime + 150
		cur = self.conn.cursor()
		query = "update liveOnTV set id = ?, subtitle = ?, image = ?, year = ?, fsk = ?, rating = ?, leadText = ?, conclusion = ?, categoryName = ?, season = ?, episode = ?, genre = ?, country = ?, imdb = ? where sref = ? AND airtime BETWEEN ? AND ? AND id = 'in progress';"
		cur.execute(query, (id, str(subtitle), str(image), year, fsk, rating, str(leadText), str(conclusion), str(categoryName), season, episode, str(genre), country, str(imdb), str(sref), low, high))
		updatetRows = cur.rowcount
		self.conn.commit()
		if updatetRows < 1:  # Suche mit titel
			low = airtime - 2700
			high = airtime + 2700
			query = "SELECT sref, airtime FROM liveOnTV WHERE title = ? AND sref = ? AND airtime BETWEEN ? AND ? AND id = 'in progress' ORDER BY airtime ASC LIMIT 1;"
			cur.execute(query, (str(title), str(sref), low, high))
			row = cur.fetchone()
			if row:
				query = "UPDATE liveOnTV set id = ?, subtitle = ?, image = ?, year = ?, fsk = ?, rating = ?, leadText = ?, conclusion = ?, categoryName = ?, season = ?, episode = ?, genre = ?, country = ?, imdb = ? where sref = ? AND airtime = ? AND  id = 'in progress';"
				cur.execute(query, (id, str(subtitle), str(image), year, fsk, rating, str(leadText), str(conclusion), str(categoryName), season, episode, str(genre), country, str(imdb), str(row[0]), row[1]))
				self.conn.commit()

	def updateliveTVProgress(self):
		cur = self.conn.cursor()
		query = "update liveOnTV set id = '' where id = 'in progress';"
		cur.execute(query)
		aelGlobals.write_log("nothing found for " + str(cur.rowcount) + " events in liveOnTV")
		self.conn.commit()
		self.parameter(PARAMETER_SET, 'lastadditionalDataCountSuccess', str(cur.rowcount))

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
			tvname = sub(r'\\(.*?\\)', '', tvname).strip()
			tvname = sub(r' +', ' ', tvname)
			query = "SELECT * FROM liveOnTV WHERE eid = ? AND title = ?"
			cur.execute(query, (eid, tvname))
		else:
			query = "SELECT * FROM liveOnTV WHERE eid = ?"
			cur.execute(query, (eid,))
		row = cur.fetchall()
		if row:
			if row[0][1] != "":
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
		query = "SELECT DISTINCT sref FROM liveOnTV WHERE id = 'in progress' and airtime > " + now
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
				if getImageFile(f"{getPictureDir()}cover/", row[0]) is None:
					coverList.append(row[0])
				if getImageFile(f"{getPictureDir()}poster/", row[0]) is None:
					posterList.append(row[0])
		return [coverList, posterList]

	def getMinAirtimeforUpdate(self, sref):
		cur = self.conn.cursor()
		now = str(int(time() - 7200))
		query = "SELECT Min(airtime) FROM liveOnTV WHERE id = 'in progress' and sref = ? and airtime > " + now
		cur.execute(query, (str(sref),))
		row = cur.fetchall()
		return row[0][0] if row else 4000000000

	def getMaxAirtimeforUpdate(self, sref):
		cur = self.conn.cursor()
		now = str(int(time() - 7200))
		query = "SELECT Max(airtime) FROM liveOnTV WHERE id = 'in progress' and sref = ? and airtime > " + now
		cur.execute(query, (str(sref),))
		row = cur.fetchall()
		return row[0][0] if row else 1000000000

	def getUpdateCount(self):
		cur = self.conn.cursor()
		now = str(int(time() - 7200))
		query = "SELECT COUNT(title) FROM liveOnTV WHERE id = 'in progress' and airtime > " + now
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
		aelGlobals.write_log("found " + str(len(trailercount)) + ' on liveTV')
		i = len(trailercount)
		query = "SELECT DISTINCT trailer FROM eventInfo WHERE trailer <> ''"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				trailercount.add(row[0])
		eI = len(trailercount) - i
		aelGlobals.write_log("found " + str(eI) + ' on eventInfo')
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
		query = "SELECT DISTINCT title FROM liveOnTV WHERE id = 'in progress' and airtime > " + now
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
		query = "SELECT DISTINCT title FROM liveOnTV WHERE id = 'in progress' and (title like '% - %' or title like '%: %') and airtime > " + now
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
		aelGlobals.write_log("have removed " + str(cur.rowcount) + " events from liveOnTV")
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
		aelGlobals.write_log("found old preview images " + str(len(rows)))
		if rows:
			for row in rows:
				titleList.append(row[0])
		delList = [x for x in titleList if x not in duplicates]
		aelGlobals.write_log("not used preview images " + str(len(delList)))
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

	def addblackListCover(self, base64title):
		cur = self.conn.cursor()
		query = "insert or ignore into blackListCover (base64title) values (?);"
		cur.execute(query, (str(base64title),))
		self.conn.commit()

	def addblackListPoster(self, base64title):
		cur = self.conn.cursor()
		query = "insert or ignore into blackListPoster (base64title) values (?);"
		cur.execute(query, (str(base64title),))
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
		cur.execute(query, (str(base64title),))
		row = cur.fetchall()
		return True if row else False

	def getblackListCover(self, base64title):
		cur = self.conn.cursor()
		query = "SELECT base64title FROM blackListCover WHERE base64title = ?"
		cur.execute(query, (str(base64title),))
		row = cur.fetchall()
		return True if row else False

	def getblackListPoster(self, base64title):
		cur = self.conn.cursor()
		query = "SELECT base64title FROM blackListPoster WHERE base64title = ?"
		cur.execute(query, (str(base64title),))
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
		query = "SELECT Max(airtime) FROM liveOnTV WHERE title = ?"
		cur.execute(query, (str(title),))
		row = cur.fetchall()
		return row[0][0] if row else 4000000000

	def getSeriesStarts(self):
		now = time()
		titleList = []
		cur = self.conn.cursor()
		if config.plugins.AdvancedEventLibrary.SeriesType.value == 'Staffelstart':
			query = "SELECT sref, eid, categoryName FROM liveOnTV WHERE sref <> '' AND episode = '1' AND airtime > " + str(now) + " ORDER BY categoryName, airtime"
		else:
			query = "SELECT sref, eid, categoryName FROM liveOnTV WHERE sref <> '' AND season = '1' AND episode = '1' AND airtime > " + str(now) + "  ORDER BY categoryName, airtime"
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
			query = "SELECT Distinct categoryName from liveOnTV where airtime > " + str(now) + " AND sref <> '' and episode = '1'"
		else:
			query = "SELECT Distinct categoryName from liveOnTV where airtime > " + str(now) + " AND sref <> '' and season = '1' and episode = '1'"
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
		query = "SELECT eid, sref from liveOnTV where airtime BETWEEN " + str(start) + " AND " + str(end) + " AND " + str(what)
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

########################################### Download Helper Class #######################################################


def url_parse(url, defaultPort=None):
	parsed = urlparse(url)
	scheme = parsed[0]
	path = urlunparse(('', '') + parsed[2:])
	if defaultPort is None:
		defaultPort = 443 if scheme == 'https' else 80
	host, port = parsed[1], defaultPort
	if ':' in host:
		host, port = host.split(':')
		port = int(port)
	return scheme, host, port, path


class BingImageSearch:
	def __init__(self, query, limit, what='Cover'):
		self.download_count = 0
		self.query = query
		self.filters = '+filterui:photo-photo+filterui:aspect-wide&form=IRFLTR' if what == 'Cover' else '+filterui:photo-photo+filterui:aspect-tall&form=IRFLTR'
		self.limit = limit
#		Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
#		self.headers = {'User-Agent': 'Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'}
		self.page_counter = 0

	def search(self):
		resultList = []
		while self.download_count < self.limit:
#			Kommentare sind nur aus Dokugründen noch da, kann später dann weg...
#			request_url = 'https://www.bing.com/images/async?q=' + quote(self.query) + '&first=' + self.page_counter + '&count=' + str(self.limit) + '&adlt=off' + '&qft=' + self.filters
#			html = get(request_url, timeout=5, headers=self.headers).content
#			unkodierte URL: https://www.bing.com/images/async
			bingurl = b64decode(b"aHR0cHM6Ly93d3cuYmluZy5jb20vaW1hZ2VzL2FzeW5j8"[:-1]).decode()
			params = {"q": self.query, "first": self.page_counter, "count": self.limit, "adlt": "off", "qft": self.filters}
			aelGlobals.write_log(f"Bing-requests : {bingurl}")
			errmsg, htmldata = aelGlobals.getHTMLdata(bingurl, params=params)
			if errmsg:
				aelGlobals.write_log("[{DEFAULT_MODULE_NAME}] HTML download error in module 'BingImageSearch:search'")
			if htmldata:
				links = findall(r"murl&quot;:&quot;(.*?)&quot;", str(htmldata))
				aelGlobals.write_log(f"Bing-result : {links}")
				if len(links) <= self.limit:
					self.limit = len(links) - 1
				for link in links:
					link = link.replace(".jpeg", ".jpg")
					if link.endswith('.jpg'):
						if self.download_count < self.limit:
							resultList.append(link)
							self.download_count += 1
						else:
							break
				self.page_counter += 1
		return resultList


####################################################################################################################################################################
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
