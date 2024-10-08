#!/usr/bin/env python
# -*- coding: utf-8 -*-
#################################################################################
#																				#
#								AdvancedEventLibrary							#
#																				#
#																				#
#						License: this is closed source!							#
#	you are not allowed to use this or parts of it on any other image than VTi	#
#		you are not allowed to use this or parts of it on NON VU Hardware		#
#																				#
#							Copyright: tsiegel 2019								#
#																				#
#################################################################################

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
# ==================================================

__all__ = ['randbelow']

import urllib2
import json
import codecs
import os
import StringIO
import base64
import shutil
import requests
import re
import sqlite3
import linecache
import subprocess
import glob
import skin
from random import SystemRandom
from sqlite3 import Error
from time import time, localtime, strftime, mktime
from thread import start_new_thread
from enigma import eEPGCache, iServiceInformation, eServiceReference, eServiceCenter, eTimer, iPlayableServicePtr, iPlayableService
from Screens.ChannelSelection import service_types_tv
from operator import itemgetter
from Components.config import config, ConfigText, ConfigSubsection, ConfigInteger, ConfigYesNo, ConfigSelection, fileExists
from PIL import Image
from Tools.Alternatives import GetWithAlternative
from Tools.Bytes2Human import bytes2human
from Components.Sources.Event import Event
from Components.Sources.ExtEvent import ExtEvent
from Components.Sources.extEventInfo import extEventInfo
from Components.Sources.CurrentService import CurrentService
from Components.Sources.ServiceEvent import ServiceEvent
from Tools.Directories import defaultRecordingLocation
from ServiceReference import ServiceReference
from difflib import get_close_matches
from datetime import datetime
from twisted.web import client
from twisted.internet import reactor, defer, ssl
from twisted.python import failure
from twisted.internet._sslverify import ClientTLSOptions

isInstalled = False
try:
	from Plugins.Extensions.AdvancedEventLibrary import tmdbsimple as tmdb
	from Plugins.Extensions.AdvancedEventLibrary import tvdbsimple as tvdb
	from Plugins.Extensions.AdvancedEventLibrary import tvdb_api_v4
	isInstalled = True
except:
	pass

log = "/var/tmp/AdvancedEventLibrary.log"

bestmount = defaultRecordingLocation().replace('movie/','') + 'AdvancedEventLibrary/'
config.plugins.AdvancedEventLibrary = ConfigSubsection()
config.plugins.AdvancedEventLibrary.Location = ConfigText(default = bestmount)
dir = config.plugins.AdvancedEventLibrary.Location.value
if not "AdvancedEventLibrary/" in dir:
	dir = dir + "AdvancedEventLibrary/"
config.plugins.AdvancedEventLibrary.Backup = ConfigText(default = "/media/hdd/AdvancedEventLibraryBackup/")
backuppath = config.plugins.AdvancedEventLibrary.Backup.value
addlog = config.plugins.AdvancedEventLibrary.Log = ConfigYesNo(default = False)
createMetaData = config.plugins.AdvancedEventLibrary.CreateMetaData = ConfigYesNo(default = False)
usePreviewImages = config.plugins.AdvancedEventLibrary.UsePreviewImages = ConfigYesNo(default = True)
previewImages = usePreviewImages.value or usePreviewImages.value == 'true'
delPreviewImages = config.plugins.AdvancedEventLibrary.DelPreviewImages = ConfigYesNo(default = True)
delpreviewImages = delPreviewImages.value or delPreviewImages.value == 'true'
searchfor = config.plugins.AdvancedEventLibrary.SearchFor = ConfigSelection(default = "Extradaten und Bilder", choices = [ "Extradaten und Bilder", "nur Extradaten" ])
coverquality = config.plugins.AdvancedEventLibrary.coverQuality = ConfigSelection(default="w1280", choices = [("w300", "300x169"), ("w780", "780x439"), ("w1280", "1280x720"), ("w1920", "1920x1080")])
posterquality = config.plugins.AdvancedEventLibrary.posterQuality = ConfigSelection(default="w780", choices = [("w185", "185x280"),("w342", "342x513"), ("w500", "500x750"), ("w780", "780x1170")])
coverqualityDict = {"w300": "300x169", "w780": "780x439", "w1280": "1280x720", "w1920": "1920x1080"}
posterqualityDict = {"w185": "185x280","w342": "342x513", "w500": "500x750", "w780": "780x1170"}
searchPlaces = config.plugins.AdvancedEventLibrary.searchPlaces = ConfigText(default = '')
dbfolder = config.plugins.AdvancedEventLibrary.dbFolder = ConfigSelection(default="Datenverzeichnis", choices = ["Datenverzeichnis", "Flash"])
maxImageSize = config.plugins.AdvancedEventLibrary.MaxImageSize = ConfigSelection(default="200", choices = [("100", "100kB"), ("150", "150kB"), ("200", "200kB"), ("300", "300kB"), ("400", "400kB"), ("500", "500kB"), ("750", "750kB"), ("1024", "1024kB"), ("1000000", "unbegrenzt")])
maxCompression = config.plugins.AdvancedEventLibrary.MaxCompression = ConfigInteger(default=50, limits=(10, 90))
seriesStartType = config.plugins.AdvancedEventLibrary.SeriesType = ConfigSelection(default = "Staffelstart", choices = [ "Staffelstart", "Serienstart" ])
tmdbKey = config.plugins.AdvancedEventLibrary.tmdbKey = ConfigText(default = 'intern')
tvdbKey = config.plugins.AdvancedEventLibrary.tvdbKey = ConfigText(default = 'intern')
tvdbV4Key = config.plugins.AdvancedEventLibrary.tvdbV4Key = ConfigText(default = 'unbenutzt')
omdbKey = config.plugins.AdvancedEventLibrary.omdbKey = ConfigText(default = 'intern')
aelDISKey = config.plugins.AdvancedEventLibrary.aelKey = ConfigText(default = 'kein')
updateAELMovieWall = config.plugins.AdvancedEventLibrary.UpdateAELMovieWall = ConfigYesNo(default = True)

sPDict = {}
if searchPlaces.value != '':
	try:
		sPDict = eval(searchPlaces.value)
	except:
		pass

vtidb_loc = config.misc.db_path.value + '/vtidb.db'

STATUS = None
PARAMETER_SET = 0
PARAMETER_GET = 1
SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]

tmdb_genres = {10759 : "Action-Abenteuer", 16 : "Animation", 10762 : "Kinder", 10763 : "News", 10764 : "Reality", 10765 : "Sci-Fi-Fantasy", 10766 : "Soap", 10767 : "Talk", 10768 : "War & Politics", 28 : "Action", 12 : "Abenteuer", 16 : "Animation", 35 : "Comedy", 80 : "Crime", 99 : "Dokumentation", 18 : "Drama", 10751 : "Familie", 14 : "Fantasy", 36 : "History", 27 : "Horror", 10402 : "Music", 9648 : "Mystery", 10749 : "Romance", 878 : "Science-Fiction", 10770 : "TV-Movie", 53 : "Thriller", 10752 : "War", 37 : "Western"}
convNames = ['Polizeiruf','Tatort','Die Bergpolizei','Axte X','ANIXE auf Reisen','Close Up','Der Z�rich-Krimi','Buffy','Das Traumschiff','Die Land','Faszination Berge','Hyperraum','Kreuzfahrt ins Gl','Lost Places','Mit offenen Karten','Newton','Planet Schule','Punkt 12','Regular Show','News Reportage','News Spezial','S.W.A.T','Xenius','Der Barcelona-Krimi','Die ganze Wahrheit','Firmen am Abgrund','GEO Reportage','Kommissar Wallander','Rockpalast','SR Memories','Wildes Deutschland','Wilder Planet','Die rbb Reporter','Flugzeug-Katastrophen','Heute im Osten','Kalkofes Mattscheibe','Neue Nationalparks','Auf Entdeckungsreise']
excludeNames = ['RTL UHD', '--', 'Sendeschluss', 'Dokumentation', 'EaZzzy', 'MediaShop', 'Dauerwerbesendung', 'Impressum']
coverIDs = [3,8,11,15]
posterIDs = [2,7,14]

ApiKeys = {"tmdb": ["ZTQ3YzNmYzJkYzRlMWMwN2UxNGE4OTc1YjI5MTE1NWI=","MDA2ZTU5NGYzMzFiZDc1Nzk5NGQwOTRmM2E0ZmMyYWM=","NTRkMzg1ZjBlYjczZDE0NWZhMjNkNTgyNGNiYWExYzM="], "tvdb": ["NTRLVFNFNzFZWUlYM1Q3WA==","MzRkM2ZjOGZkNzQ0ODA5YjZjYzgwOTMyNjI3ZmE4MTM=","Zjc0NWRiMDIxZDY3MDQ4OGU2MTFmNjY2NDZhMWY4MDQ="], "omdb": ["ZmQwYjkyMTY=","YmY5MTFiZmM=","OWZkNzFjMzI="]}

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
	'France �': 'FRA',
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
	'KTN': 'PAK',
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
	'RT� One': 'IRL',
	'RT� Two': 'IRL',
	'RTL Television': 'DEU',
	'RTP A�ores': 'PRT',
	'RTP �frica': 'PRT',
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
	'SIC Com�dia': 'PRT',
	'SIC Mulher': 'PRT',
	'SIC Not�cias': 'PRT',
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
	'T�l�toon': 'FRA',
	'TVNZ': 'NZL',
	'Comedy Central (US)': 'USA',
	'TLC': 'USA',
	'Food Network': 'USA',
	'Global': 'CAN',
	'DuMont Television Network': 'USA',
	'History': 'USA',
	'Encore': 'USA',
	'Lifetime': 'USA',
	'��n': 'BEL',
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
	'TV 2': 'DNK',
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
	'S�ries+': 'CAN',
	'V': 'CAN',
	'Television Osaka': 'JPN',
	'SVT': 'SWE',
	'Zt�l�': 'CAN',
	'Vrak.TV': 'CAN',
	'Casa': 'CAN',
	'Logo': 'USA',
	'Disney XD': 'USA',
	'Prime (NZ)': 'NZL',
	'2�2': 'RUS',
	'TV Nova': 'CZE',
	'Cesk� televize': 'CZE',
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
	'Magyar Telev�zi�': 'HUN',
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
	'Tev�Ciudad': 'URY',
	'Encuentro': 'ARG',
	'TV P�blica': 'ARG',
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
	'Kanal 5': 'SWE',
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
	'T�l�-Qu�bec': 'CAN',
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
	'Channel 5': 'GBR',
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
	'H�r TV': 'HUN',
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
	'ATV T�rkiye': 'TUR',
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
	'AlloCin�': 'FRA',
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
	'Ch�rie 25': 'FRA',
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
	'Nou Televisi�': 'ESP',
	'Teletama': 'JPN',
	'Toei Channel': 'JPN',
	'CTV (JP)': 'JPN',
	'VOX': 'DEU',
	'El Rey Network': 'USA',
	'Sky Living': 'GBR',
	'Channel 3': 'THA',
	'Kamp�s TV': 'TUR',
	'Life OK': 'IND',
	'Canal Once': 'MEX',
	'Food Network Canada': 'CAN',
	'Al Jazeera America': 'USA',
	'HGTV Canada': 'CAN',
	'Discovery Shed': 'GBR',
	'Pivot': 'USA',
	'TVN': 'CHL',
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
	'FOX T�rkiye': 'TUR',
	'RTBF': 'BEL',
	'Ora TV': 'USA',
	'Discovery MAX': 'ESP',
	'DMAX (IT)': 'ITA',
	'ITV Wales': 'GBR',
	'OCS': 'FRA',
	'vtmKzoom': 'BEL',
	'TVO': 'CAN',
	'Televisi�n de Galicia': 'ESP',
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
	'TeleZ�ri': 'CHE',
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
	'TV S�o Carlos': 'BRA',
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
	'TRT Kurd�': 'TUR',
	'Kanal A (Turkey)': 'TUR',
	'TRT HD': 'TUR',
	'TRT Haber': 'TUR',
	'TRT Belgesel': 'TUR',
	'TRT World': 'TUR',
	'360': 'TUR',
	'TRT T�rk': 'TUR',
	'TRT �ocuk': 'TUR',
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
	'�lke TV': 'TUR',
	'TGRT Haber': 'TUR',
	'Beyaz TV': 'TUR',
	'L�leg�l TV': 'TUR',
	'HBO Nordic': 'SWE',
	'Bandai Channel': 'JPN',
	'Sixx': 'DEU',
	'element14': 'USA',
	'HBO Magyarorsz�g': 'HUN',
	'HBO Europe': 'HUN',
	'HBO Latin America': 'BRA',
	'Canal Off': 'BRA',
	'ETV': 'EST',
	'Super �cran': 'CAN',
	'Discovery Life': 'USA',
	'The Family Channel': 'USA',
	'Fox Family': 'USA',
	'Canal 9 (AR)': 'ARG',
	'B92': 'SRB',
	'Ceskoslovensk� televize': 'CZE',
	'CNNI': 'USA',
	'Channel 101': 'USA',
	'Canal 5': 'MEX',
	'MyNetworkTV': 'USA',
	'Blip': 'USA',
	'WPIX': 'USA',
	'Canal Famille': 'CAN',
	'Canal D': 'CAN',
	'�vasion': 'CAN',
	'DIY Network Canada': 'CAN',
	'Much (CA)': 'CAN',
	'MTV Brazil': 'BRA',
	'UKTV Yesterday': 'GBR',
	'Swearnet': 'CAN',
	'Dailymotion': 'USA',
	'RMC D�couverte': 'FRA',
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
	't�va': 'FRA',
	'MCM': 'FRA',
	'June': 'FRA',
	'Com�die !': 'FRA',
	'Com�die+': 'FRA',
	'Filles TV': 'FRA',
	'Discovery Channel (Australia)': 'AUS',
	'FOX (UK)': 'GBR',
	'Disney Junior (UK)': 'GBR',
	'n-tv': 'DEU',
	'OnStyle': 'KOR'
	}

def getDB():
	if dbfolder.value == "Flash":
		return DB_Functions('/etc/enigma2/eventLibrary.db')
	else:
		return DB_Functions(os.path.join(getPictureDir(), 'eventLibrary.db'))

def write_log(svalue, logging=True):
	if logging:
		t = localtime()
		logtime = '%02d:%02d:%02d' % (t.tm_hour, t.tm_min, t.tm_sec)
		AEL_log = open(log,"a")
		AEL_log.write(str(logtime) + " : [AdvancedEventLibrary] - " + str(svalue) + "\n")
		AEL_log.close()

def load_json(filename):
	f = open(filename,'r')
	data=f.read().replace('null', '""')
	f.close()
	return eval(data)

def randbelow(exclusive_upper_bound):
	if exclusive_upper_bound <= 0:
		return 0
	return SystemRandom()._randbelow(exclusive_upper_bound)

def get_keys(forwhat):
	if forwhat == 'tmdb' and tmdbKey.value != 'intern':
		return tmdbKey.value
	elif forwhat == 'tvdb' and tvdbKey.value != 'intern':
		return tvdbKey.value
	elif forwhat == 'omdb' and omdbKey.value != 'intern':
		return omdbKey.value
	else:
		return base64.b64decode(ApiKeys[forwhat][randbelow(3)])

def get_TVDb():
	if tvdbV4Key.value != "unbenutzt1":
		tvdbV4 = tvdb_api_v4.TVDB(tvdbV4Key.value)
		if tvdbV4.get_login_state():
			return tvdbV4
	return None

def convert2base64(title):
	if title.find('(') > 1:
		return base64.b64encode(title.decode('utf-8').lower().split('(')[0].strip()).replace('/','')
	return base64.b64encode(title.decode('utf-8').lower().strip()).replace('/','')

def convertSigns(text):
#	text = text.replace('\xc3\x84', '\xc4').replace('\xc3\x96', '\xd6').replace('\xc3\x9c', '\xdc').replace('\xc3\x9f', '\xdf').replace('\xc3\xa4', '\xe4').replace('\xc3\xb6', '\xf6').replace('\xc3\xbc', '\xfc').replace('&', '%26').replace('\xe2\x80\x90', '-').replace('\xe2\x80\x91', '-').replace('\xe2\x80\x92', '-').replace('\xe2\x80\x93', '-')
	text = text.replace('\xe2\x80\x90', '-').replace('\xe2\x80\x91', '-').replace('\xe2\x80\x92', '-').replace('\xe2\x80\x93', '-')
	return text

def createDirs(path):
	path = str(path).replace('poster/','').replace('cover/','')
	if not path.endswith('/'):
		path = path + '/'
	if not path.endswith('AdvancedEventLibrary/'):
		path = path + 'AdvancedEventLibrary/'
	if not os.path.exists(path):
		os.makedirs(path)
	if not os.path.exists(path+'poster/'):
		os.makedirs(path+'poster/')
	if not os.path.exists(path+'cover/'):
		os.makedirs(path+'cover/')
	if not os.path.exists(path+'preview/'):
		os.makedirs(path+'preview/')
	if not os.path.exists(path+'cover/thumbnails/'):
		os.makedirs(path+'cover/thumbnails/')
	if not os.path.exists(path+'preview/thumbnails/'):
		os.makedirs(path+'preview/thumbnails/')
	if not os.path.exists(path+'poster/thumbnails/'):
		os.makedirs(path+'poster/thumbnails/')

def getPictureDir():
	return dir

def removeExtension(ext):
	ext = ext.replace('.wmv','').replace('.mpeg2','').replace('.ts','').replace('.m2ts','').replace('.mkv','').replace('.avi','').replace('.mpeg','').replace('.mpg','').replace('.iso','').replace('.mp4','')
	return ext

def setStatus(text=None):
	global STATUS
	STATUS = text

def getMemInfo(value):
	result = [0,0,0,0]	# (size, used, avail, use%)
	try:
		check = 0
		fd = open("/proc/meminfo")
		for line in fd:
			if value + "Total" in line:
				check += 1
				result[0] = int(line.split()[1]) * 1024		# size
			elif value + "Free" in line:
				check += 1
				result[2] = int(line.split()[1]) * 1024		# avail
			if check > 1:
				if result[0] > 0:
					result[1] = result[0] - result[2]	# used
					result[3] = result[1] * 100 / result[0]	# use%
				break
		fd.close()
	except:
		pass
	return "%s (%s%%)" % (getSizeStr(result[1]), result[3])

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
	write_log(str(screenName) + ' - Speicherauslastung vor Bereinigung : ' + str(getMemInfo('Mem')))
	os.system('sync')
	os.system('sh -c "echo 3 > /proc/sys/vm/drop_caches"')
	write_log(str(screenName) + ' - Speicherauslastung nach Bereinigung : ' + str(getMemInfo('Mem')))

def createBackup():
	global STATUS
	STATUS = "erzeuge Backup in " + str(backuppath)
	write_log("create backup in " + str(backuppath))
	try:
		if not os.path.exists(backuppath):
			os.makedirs(backuppath)
		if not os.path.exists(backuppath+'poster/'):
			os.makedirs(backuppath+'poster/')
		if not os.path.exists(backuppath+'cover/'):
			os.makedirs(backuppath+'cover/')

		if dbfolder.value == "Flash":
			dbpath = '/etc/enigma2/eventLibrary.db'
		else:
			dbpath = os.path.join(getPictureDir(), 'eventLibrary.db')
		if fileExists(dbpath):
#			os.system('cp ' + str(dbpath) + str(os.path.join(backuppath, 'eventLibrary.db'))) 
			shutil.copy2(dbpath, os.path.join(backuppath, 'eventLibrary.db'))

		files = glob.glob(getPictureDir()+'poster/*.jpg')
		progress = 0
		pics = len(files)
		copied = 0
		for file in files:
			try:
				progress += 1
				target = os.path.join(backuppath+'poster/', os.path.basename(file))
				if not fileExists(target):
#					os.system('cp ' + str(file) + str(target)) 
					shutil.copy2(file,target)
					STATUS = "(" + str(progress) + "/" + str(pics) + ") sichere Poster : " + str(file)
					copied += 1
				else:
					if os.path.getmtime(file) > (os.path.getmtime(target) + 7200):
#						os.system('cp ' + str(file) + str(target)) 
						shutil.copy2(file,target)
						STATUS = "(" + str(progress) + "/" + str(pics) + ") sichere Poster : " + str(file)
						copied += 1
			except Exception as ex:
				write_log("Fehler beim kopieren : " + str(ex))
				continue
		write_log("have copied " + str(copied) + " poster to " + str(backuppath) + "poster/")
		del files

		files = glob.glob(getPictureDir()+'cover/*.jpg')
		progress = 0
		pics = len(files)
		copied = 0
		for file in files:
			try:
				progress += 1
				target = os.path.join(backuppath+'cover/', os.path.basename(file))
				if not fileExists(target):
#					os.system('cp ' + str(file) + str(target)) 
					shutil.copy2(file,target)
					STATUS = "(" + str(progress) + "/" + str(pics) + ") sichere Cover : " + str(file)
					copied += 1
				else:
					if os.path.getmtime(file) > os.path.getmtime(target):
#						os.system('cp ' + str(file) + str(target)) 
						shutil.copy2(file,target)
						STATUS = "(" + str(progress) + "/" + str(pics) + ") sichere Cover : " + str(file)
						copied += 1
			except Exception as ex:
				write_log("Fehler beim kopieren : " + str(ex))
				continue
		write_log("have copied " + str(copied) + " cover to " + str(backuppath) + "cover/")
		del files
	except Exception as ex:
		write_log("Fehler in createBackup : " + str(ex))
	STATUS = None
	clearMem("createBackup")
	write_log("backup finished")


def checkUsedSpace(db=None):
	try:
		recordings = getRecordings()
		if dbfolder.value == "Flash":
			dbpath = '/etc/enigma2/eventLibrary.db'
		else:
			dbpath = os.path.join(getPictureDir(), 'eventLibrary.db')
		if fileExists(dbpath) and db:
			config.plugins.AdvancedEventLibrary.MaxSize = ConfigInteger(default=1, limits=(1, 100))
			config.plugins.AdvancedEventLibrary.MaxUsedInodes = ConfigInteger(default=90, limits=(20, 95))
			maxUsedInodes = config.plugins.AdvancedEventLibrary.MaxUsedInodes.value
			if "/etc" in dir:
				maxSize = 1 * 1024.0 * 1024.0
			else:
				maxSize = config.plugins.AdvancedEventLibrary.MaxSize.value * 1024.0 * 1024.0
			PDIR = dir + 'poster/'
			CDIR = dir + 'cover/'
			PRDIR = dir + 'preview/'
			posterSize = float(subprocess.check_output(['du','-sk', PDIR]).split()[0])
			coverSize = float(subprocess.check_output(['du','-sk', CDIR]).split()[0])
			previewSize = float(subprocess.check_output(['du','-sk', PRDIR]).split()[0])
			inodes = subprocess.check_output(['df','-i', dir]).split()[-2]
			write_log('benutzte Inodes = ' + str(inodes))
			write_log('benutzter Speicherplatz = ' + str(float(posterSize) + float(coverSize)) + ' kB von ' + str(maxSize) + ' kB.')
			usedInodes = int(inodes[:-1])
			if (((int(posterSize) + int(coverSize) + int(previewSize)) > int(maxSize)) or usedInodes >= maxUsedInodes):
				removeList = glob.glob(os.path.join(PRDIR, "*.jpg"))
				for f in removeList:
					os.remove(f)
				i = 0
				while i < 100:
					titles = db.getUnusedTitles()
					if titles:
						write_log(str(i+1) + '. Bereinigung des Speicherplatzes.')
						for title in titles:
							try:
								if not str(title[1]) in recordings:
									removeList = glob.glob(PDIR + title[0] + '*.jpg')
									for file in removeList:
										os.remove(file)
									removeList = glob.glob(PDIR + 'thumbnails/' + title[0] + '*.jpg')
									for file in removeList:
										os.remove(file)
									removeList = glob.glob(CDIR + title[0] + '*.jpg')
									for file in removeList:
										os.remove(file)
									removeList = glob.glob(CDIR + 'thumbnails/' + title[0] + '*.jpg')
									for file in removeList:
										os.remove(file)
									db.cleanDB(title[0])
									del removeList
							except:
								continue
						posterSize = float(subprocess.check_output(['du','-sk', PDIR]).split()[0])
						coverSize = float(subprocess.check_output(['du','-sk', CDIR]).split()[0])
						write_log('benutzter Speicherplatz = ' + str(float(posterSize) + float(coverSize)) + ' kB von ' + str(maxSize) + ' kB.')
					if (posterSize + coverSize) < maxSize:
						break
					i +=1
				db.vacuumDB()
				write_log('benutzter Speicherplatz = ' + str(float(posterSize) + float(coverSize)) + ' kB von ' + str(maxSize) + ' kB.')
	except Exception as ex:
		write_log("Fehler in getUsedSpace : " + str(ex))

def removeLogs():
	if fileExists(log):
		os.remove(log)

def startUpdate():
	if isInstalled:
		start_new_thread(getallEventsfromEPG, ())
	else:
		write_log("AdvancedEventLibrary not installed")

def isconnected():
	try:
		return os.system("ping -c 2 -W 2 -w 4 8.8.8.8")
	except Exception as ex:
		write_log("no internet connection! " + str(ex))
		return False

def createMovieInfo(db):
	global STATUS
	try:
		STATUS = 'suche nach fehlenden meta-Dateien...'
		recordPaths = config.movielist.videodirs.value
		for recordPath in recordPaths:
			if os.path.isdir(recordPath):
				for root, directories, files in os.walk(recordPath):
					if os.path.isdir(root):
						doIt = False
						if str(root) in sPDict:
							if sPDict[root]:
								doIt = True
						if doIt:
							for filename in files:
								try:
									#== # Hinzugefuegt (#2): Check ReadOnly ==
									if not os.access(os.path.join(root, filename), os.W_OK):
										continue
									# =================================
									foundAsMovie = False
									foundOnTMDbTV = False
									foundOnTVDb = False
									if (filename.endswith('.ts') or filename.endswith('.mkv') or filename.endswith('.avi') or filename.endswith('.mpg') or filename.endswith('.mp4') or filename.endswith('.iso') or filename.endswith('.mpeg2')):
										if not db.getimageBlackList(removeExtension(str(filename).decode('utf8'))):
											if not fileExists(os.path.join(root, filename + '.meta')):
												title = convertSearchName(convertDateInFileName(((filename.split('/')[-1]).rsplit('.', 1)[0]).replace('__',' ').replace('_',' ')))
												mtitle = title
												titleNyear = convertYearInTitle(title)
												title = titleNyear[0]
												jahr = str(titleNyear[1])
												if title and title != '' and title != ' ':
													tmdb.API_KEY = get_keys('tmdb')
													titleinfo = {
														"title" : mtitle,
														"genre" : "",
														"year" : "",
														"country" : "",
														"overview" : ""
														}
													try:
														STATUS = 'suche meta-Informationen f�r ' + str(title)
														write_log('suche meta-Informationen f�r ' + str(title), addlog.value)
														search = tmdb.Search()
														if jahr != '':
															res = search.movie(query=title, language='de', year=jahr)
														else:
															res = search.movie(query=title, language='de')
														if res:
															if res['results']:
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
																		#===== geaendert (#9) ========
																		#if item['genre_ids']:
																		if item.get('genre_ids',""):
																		# =============================
																			for genre in item['genre_ids']:
																				if not tmdb_genres[genre] in titleinfo['genre']:
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
													except Exception as ex:
														write_log('Fehler in createMovieInfo themoviedb movie : ' + str(ex))

													try:
														if not foundAsMovie:
															search = tmdb.Search()
															searchName = findEpisode(title)
															if searchName: 
																res = search.tv(query=searchName[2], language='de', include_adult=True, search_type='ngram')
															else:
																res = search.tv(query=title, language='de', include_adult=True, search_type='ngram')
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
																				try:
																					details = tmdb.TV_Episodes(item['id'],searchName[0],searchName[1])
																					epi = details.info(language='de')
																					#imgs = details.images(language='de')
																					if 'name' in epi:
																						titleinfo['title'] = item['name'] + ' - S' + searchName[0] + 'E' + searchName[1] + ' - ' + epi['name']
																					if 'air_date' in epi:
																						titleinfo['year'] = epi['air_date'][:4]
																					if 'overview' in epi:
																						titleinfo['overview'] = epi['overview']
																					#===== geaendert (#9) ========
																					#if item['origin_country']:
																					if item.get('origin_country',""):
																					# =============================
																						for country in item['origin_country']:
																							titleinfo['country'] = titleinfo['country'] + country + ' | '
																						titleinfo['country'] = titleinfo['country'][:-3]
																					#===== geaendert (#9) ========
																					#if item['genre_ids']:
																					if item.get('genre_ids',""):
																					# =============================
																						for genre in item['genre_ids']:
																							if not tmdb_genres[genre] in titleinfo['genre']:
																								titleinfo['genre'] = titleinfo['genre'] + tmdb_genres[genre] + '-Serie '
																						maxGenres = titleinfo['genre'].split()
																						if maxGenres:
																							if len(maxGenres) >= 1:
																								titleinfo['genre'] = maxGenres[0]
																				except:
																					pass
																			else:
																				titleinfo['title'] = item['name']
																				if 'overview' in item:
																					titleinfo['overview'] = item['overview']
																				#===== geaendert (#9) ========
																				#if item['origin_country']:
																				if item.get('origin_country',""):
																				# =============================
																					for country in item['origin_country']:
																						titleinfo['country'] = titleinfo['country'] + country + ' | '
																					titleinfo['country'] = titleinfo['country'][:-3]
																				if 'first_air_date' in item:
																					titleinfo['year'] = item['first_air_date'][:4]
																				#===== geaendert (#9) ========
																				#if item['genre_ids']:
																				if item.get('genre_ids',""):
																				# =============================
																					for genre in item['genre_ids']:
																						if not tmdb_genres[genre] in titleinfo['genre']:
																							titleinfo['genre'] = titleinfo['genre'] + tmdb_genres[genre] + '-Serie '
																					maxGenres = titleinfo['genre'].split()
																					if maxGenres:
																						if len(maxGenres) >= 1:
																							titleinfo['genre'] = maxGenres[0]
																			break
													except Exception as ex:
														write_log('Fehler in createMovieInfo themoviedb tv : ' + str(ex))

													try:
														if not foundAsMovie and not foundOnTMDbTV:
															tvdb.KEYS.API_KEY = get_keys('tvdb')
															search = tvdb.Search()
															seriesid = None
															ctitle = title
															title = convertTitle2(title)
															try:
																response = search.series(title, language="de")
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
															except Exception as ex:
																try:
																	response = search.series(title)
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
																except Exception as ex:
																	pass
															if seriesid:
																foundOnTVDb = True
																show = tvdb.Series(seriesid)
																response = show.info()
																epis = tvdb.Series_Episodes(seriesid)
																episoden = None
																try:
																	episoden = epis.all()
																except:
																	pass
																if episoden:
																	if episoden != 'None':
																		for episode in episoden:
																			try:
																				if str(episode['episodeName']) in str(ctitle):
																					if 'firstAired' in episode:
																						titleinfo['year'] = episode['firstAired'][:4]
																					if 'overview' in episode:
																						titleinfo['overview'] = episode['overview']
																					if response:
																						searchName = findEpisode(title)
																						if searchName:
																							titleinfo['title'] = response['seriesName'] + ' - S' + searchName[0] + 'E' + searchName[1] + ' - ' + episode['episodeName']
																						else:
																							titleinfo['title'] = response['seriesName'] + ' - ' + episode['episodeName']
																						if titleinfo['genre'] == "":
																							for genre in response['genre']:
																								titleinfo['genre'] = titleinfo['genre'] + genre + '-Serie '
																						titleinfo['genre'] = titleinfo['genre'].replace("Documentary", "Dokumentation").replace("Children", "Kinder")
																						if titleinfo['country'] == "":
																							if response['network'] in networks:
																								titleinfo['country'] = networks[response['network']]
																					break
																			except:
																				continue
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
													except Exception as ex:
														write_log('Fehler in createMovieInfo TVDb : ' + str(ex))

													if titleinfo['overview'] != "":
														txt = open(os.path.join(root, removeExtension(filename) + ".txt"),"w")
														txt.write(titleinfo['overview'])
														txt.close()
														write_log('createMovieInfo for : ' + str(filename))

													if foundAsMovie or foundOnTMDbTV or foundOnTVDb:
														if titleinfo['year'] != "" or titleinfo['genre'] != "" or titleinfo['country'] != "":
															filedt = int(os.stat(os.path.join(root, filename)).st_mtime)
															txt = open(os.path.join(root, filename + ".meta"),"w")
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
															write_log('create meta-Info for ' + str(os.path.join(root, filename)))
														else:
															db.addimageBlackList(removeExtension(str(filename).decode('utf8')))
													else:
														db.addimageBlackList(removeExtension(str(filename).decode('utf8')))
														write_log('nothing found for ' + str(os.path.join(root, filename)))
								except Exception as ex:
									write_log('Fehler in createMovieInfo : ' + str(ex))
									continue
	except Exception as ex:
		write_log('Fehler in createMovieInfo : ' + str(ex))


def getAllRecords(db):
	global STATUS
	try:
		STATUS = 'durchsuche Aufnahmeverzeichnisse...'
		PDIR = dir + 'poster/'
		CDIR = dir + 'cover/'
		names = set()
		recordPaths = config.movielist.videodirs.value
		doPics = False
		if "Pictures" in sPDict:
			if sPDict["Pictures"]:
				doPics = True
		else:
			doPics = True
		for recordPath in recordPaths:
			if os.path.isdir(recordPath):
				for root, directories, files in os.walk(recordPath):
					if os.path.isdir(root):
						doIt = False
						if str(root) in sPDict:
							if sPDict[root]:
								doIt = True
						fileCount = 0
						if doIt:
							for filename in files:
								try:
									if (filename.endswith('.ts') or filename.endswith('.mkv') or filename.endswith('.avi') or filename.endswith('.mpg') or filename.endswith('.mp4') or filename.endswith('.iso') or filename.endswith('.mpeg2')) and doPics:
										if fileExists(os.path.join(root,filename + '.meta')):
											fname = convertDateInFileName(linecache.getline(os.path.join(root,filename + '.meta'), 2).replace("\n",""))
										else:
											fname = convertDateInFileName(convertSearchName(convertTitle(((filename.split('/')[-1]).rsplit('.', 3)[0]).replace('_',' '))))
										searchName = filename + '.jpg'
										if (fileExists(os.path.join(root,searchName)) and not fileExists(PDIR + convert2base64(fname) + '.jpg')):
											write_log('copy poster ' + str(searchName) + ' nach ' + str(fname) + ".jpg")
											shutil.copy2(os.path.join(root,searchName), PDIR + convert2base64(fname) + ".jpg")
										searchName = removeExtension(filename) + '.jpg'
										if (fileExists(os.path.join(root,searchName)) and not fileExists(PDIR + convert2base64(fname) + '.jpg')):
											write_log('copy poster ' + str(searchName) + ' nach ' + str(fname) + ".jpg")
											shutil.copy2(os.path.join(root,searchName), PDIR + convert2base64(fname) + ".jpg")
										searchName = filename + '.bdp.jpg'
										if (fileExists(os.path.join(root,searchName)) and not fileExists(CDIR + convert2base64(fname) + '.jpg')):
											write_log('copy cover ' + str(searchName) + ' nach ' + str(fname) + ".jpg")
											shutil.copy2(os.path.join(root,searchName), CDIR + convert2base64(fname) + ".jpg")
										searchName = removeExtension(filename) + '.bdp.jpg'
										if (fileExists(os.path.join(root,searchName)) and not fileExists(CDIR + convert2base64(fname) + '.jpg')):
											write_log('copy cover ' + str(searchName) + ' nach ' + str(fname) + ".jpg")
											shutil.copy2(os.path.join(root,searchName), CDIR + convert2base64(fname) + ".jpg")
									if filename.endswith('.meta'):
										fileCount += 1
										foundInBl = False
										name = convertDateInFileName(linecache.getline(os.path.join(root,filename), 2).replace("\n",""))
										if db.getblackList(convert2base64(name)):
											name = convertDateInFileName(convertTitle(linecache.getline(os.path.join(root,filename), 2).replace("\n","")))
											if db.getblackList(convert2base64(name)):
												name = convertDateInFileName(convertTitle2(linecache.getline(os.path.join(root,filename), 2).replace("\n","")))
												if db.getblackList(convert2base64(name)):
													foundInBl = True
										if not db.checkTitle(convert2base64(name)) and not foundInBl and name != '' and name != ' ':
											names.add(name)
									if (filename.endswith('.ts') or filename.endswith('.mkv') or filename.endswith('.avi') or filename.endswith('.mpg') or filename.endswith('.mp4') or filename.endswith('.iso') or filename.endswith('.mpeg2')) and doPics:
										foundInBl = False
										name = convertDateInFileName(((filename.split('/')[-1]).rsplit('.', 1)[0]).replace('__',' ').replace('_',' '))
										if filename.endswith('.ts'):
											s_service = '1:0:0:0:0:0:0:0:0:0:' + os.path.join(root, filename)
											service = eServiceReference('1:0:0:0:0:0:0:0:0:0:' + os.path.join(root, filename))
										else:
											s_service = '4097:0:0:0:0:0:0:0:0:0:' + os.path.join(root, filename)
											service = eServiceReference('4097:0:0:0:0:0:0:0:0:0:' + os.path.join(root, filename))
										try:
											info = eServiceCenter.getInstance().info(service)
											if info:
												name = removeExtension(info.getName(service))
												if name is None:
													name = convertDateInFileName(((filename.split('/')[-1]).rsplit('.', 1)[0]).replace('__',' ').replace('_',' '))
											else:
												name = convertDateInFileName(((filename.split('/')[-1]).rsplit('.', 1)[0]).replace('__',' ').replace('_',' '))
										except:
											pass
										if db.getblackList(convert2base64(name)):
											name = convertDateInFileName(convertTitle(((filename.split('/')[-1]).rsplit('.', 1)[0]).replace('__',' ').replace('_',' ')))
											if db.getblackList(convert2base64(name)):
												name = convertDateInFileName(convertTitle2(((filename.split('/')[-1]).rsplit('.', 1)[0]).replace('_',' ')))
												if db.getblackList(convert2base64(name)):
													foundInBl = True
										if not db.checkTitle(convert2base64(name)) and not foundInBl and name != '' and name != ' ':
											names.add(name)
								except Exception as ex:
									write_log("Fehler in getAllRecords : " + ' - ' + str(name) + ' - ' + str(ex))
									continue
							write_log('check ' + str(fileCount) + ' meta Files in ' + str(root))
					else:
						write_log('recordPath ' + str(root) + ' is not exists')
			else:
				write_log('recordPath ' + str(recordPath) + ' is not exists')
		write_log('found ' + str(len(names)) + ' new Records in meta Files')
#		check vtidb
		doIt = False
		if "VTiDB" in sPDict:
			if sPDict["VTiDB"]:
				doIt = True
		else:
			doIt = True
		if (fileExists(vtidb_loc) and doIt):
			STATUS = 'durchsuche VTI-DB...'
			vtidb_conn = sqlite3.connect(vtidb_loc,check_same_thread=False)
			cur = vtidb_conn.cursor()
			query = "SELECT title FROM moviedb_v0001"
			cur.execute(query)
			rows = cur.fetchall()
			if rows:
				write_log('check ' + str(len(rows)) + ' titles in vtidb')
				for row in rows:
					try:
						if row[0] and row[0] != '' and row[0] != ' ':
							foundInBl = False
							name = convertTitle(row[0])
							if db.getblackList(convert2base64(name)):
								name = convertTitle2(row[0])
								if db.getblackList(convert2base64(name)):
									foundInBl = True
							if not db.checkTitle(convert2base64(name)) and not foundInBl:
								names.add(name)
					except Exception as ex:
						write_log("Fehler in getAllRecords vtidb: " + str(row[0]) + ' - ' + str(ex))
						continue
		write_log('found ' + str(len(names)) + ' new Records')
		return names
	except Exception as ex:
		write_log("Fehler in getAllRecords : " + str(ex))
		return names

def getRecordings():
	try:
		names = set()
		recordPaths = config.movielist.videodirs.value
		doPics = False
		for recordPath in recordPaths:
			if os.path.isdir(recordPath):
				for root, directories, files in os.walk(recordPath):
					if os.path.isdir(root):
						doIt = False
						if str(root) in sPDict:
							if sPDict[root]:
								doIt = True
						if doIt:
							for filename in files:
								try:
									if filename.endswith('.meta'):
										name = convertDateInFileName(linecache.getline(os.path.join(root,filename), 2).replace("\n",""))
										names.add(convert2base64(name))
										names.add(convert2base64(convertDateInFileName(convertTitle(name))))
										names.add(convert2base64(convertDateInFileName(convertTitle2(name))))
									if (filename.endswith('.ts') or filename.endswith('.mkv') or filename.endswith('.avi') or filename.endswith('.mpg') or filename.endswith('.mp4') or filename.endswith('.iso') or filename.endswith('.mpeg2')) and doPics:
										name = convertDateInFileName(((filename.split('/')[-1]).rsplit('.', 1)[0]).replace('__',' ').replace('_',' '))
										names.add(convert2base64(name))
										names.add(convert2base64(convertDateInFileName(convertTitle(name))))
										names.add(convert2base64(convertDateInFileName(convertTitle2(name))))
										if filename.endswith('.ts'):
											s_service = '1:0:0:0:0:0:0:0:0:0:' + os.path.join(root, filename)
											service = eServiceReference('1:0:0:0:0:0:0:0:0:0:' + os.path.join(root, filename))
										else:
											s_service = '4097:0:0:0:0:0:0:0:0:0:' + os.path.join(root, filename)
											service = eServiceReference('4097:0:0:0:0:0:0:0:0:0:' + os.path.join(root, filename))
										try:
											info = eServiceCenter.getInstance().info(service)
											name = info.getName(service)
											names.add(convert2base64(name))
											names.add(convert2base64(convertDateInFileName(convertTitle(name))))
											names.add(convert2base64(convertDateInFileName(convertTitle2(name))))
										except:
											pass
								except Exception as ex:
									write_log("getRecordings : " + ' - ' + str(name) + ' - ' + str(ex))
									continue
		return names
	except Exception as ex:
		write_log("Fehler in getRecordings : " + str(ex))
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
				os.remove(img)
				ic += 1
			img = dir + 'preview/thumbnails/' + convert2base64(image) + '.jpg'
			if fileExists(img):
				os.remove(img)
				it += 1
		else:
			write_log("can't remove " + str(image) + ", because it's a record")
	write_log('have removed ' + str(ic) + ' preview images')
	write_log('have removed ' + str(it) + ' preview thumbnails')
	del recImages
	del prevImages

def getallEventsfromEPG():
	global STATUS
	try:
		STATUS = '�berpr�fe Verzeichnisse...'
		createDirs(dir)
		STATUS = 'entferne Logfile...'
		removeLogs()
		write_log("Update start...")
		write_log("default image path is " + str(dir)[:-1])
		write_log("load preview images is: " + str(previewImages) + ' - ' + str(usePreviewImages.value))
		write_log("searchOptions " + str(sPDict))
		db = getDB()
		db.parameter(PARAMETER_SET, 'laststart', str(time()))
		cVersion = db.parameter(PARAMETER_GET, 'currentVersion', None, 111)
		if int(cVersion) < 113:
			db.parameter(PARAMETER_SET, 'currentVersion', '115')
			db.cleanliveTV(int(time() + (14*86400)))
		STATUS = '�berpr�fe reservierten Speicherplatz...'
		checkUsedSpace(db)
		names = getAllRecords(db)
		STATUS = 'durchsuche aktuelles EPG...'
		lines = []
		mask = (eServiceReference.isMarker | eServiceReference.isDirectory)
		root = eServiceReference(str(service_types_tv + ' FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
		serviceHandler = eServiceCenter.getInstance()
		tvbouquets = serviceHandler.list(root).getContent("SN", True)
		tvsref = {}
		if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/tvsreflist.data'):
			tvsref = load_json('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/tvsreflist.data')

		for bouquet in tvbouquets:
			root = eServiceReference(str(bouquet[0]))
			serviceHandler = eServiceCenter.getInstance()
			ret = serviceHandler.list(root).getContent("SN", True)
			doIt = False
			if str(bouquet[1]) in sPDict:
				if sPDict[str(bouquet[1])]:
					doIt = True
			else:
				doIt = True
			if doIt:
				for (serviceref, servicename) in ret:
					playable = not (eServiceReference(serviceref).flags & mask)
					# =========== geaendert (#8) =====================
					#if playable and "p%3a" not in serviceref and "<n/a>" not in servicename and servicename != "." and not serviceref.startswith('4097'):
						#if serviceref not in tvsref:
							#write_log(servicename +  ' mit der Referenz ' + serviceref + ' konnte nicht in der TVS Referenzliste gefunden werden!')
					if playable and "<n/a>" not in servicename and servicename != "." and serviceref:
						if serviceref not in tvsref and not "%3a" in serviceref:
							write_log(servicename +  ' mit der Referenz ' + serviceref + ' konnte nicht in der TVS Referenzliste gefunden werden!')
					# ===============================================
						line = [serviceref,servicename]
						if line not in lines:
							lines.append(line)

		acttime = time() + 1000
		test = ['RITB']
		for line in lines:
			test.append((line[0], 0, acttime, -1))

		epgcache = eEPGCache.getInstance()
		allevents = epgcache.lookupEvent(test) or []
		write_log('found ' + str(len(allevents)) + ' Events in EPG')
		evt = 0

		liveTVRecords = []
		for serviceref, eid, name, begin in allevents:
			try:
				#==== hinzugefuegt (#8) =====
				if not serviceref:
					continue
				serviceref = serviceref.split("?",1)[0].decode('utf-8','ignore')
				# =========================
				evt += 1
				STATUS = 'durchsuche aktuelles EPG... (' + str(evt) + '/' + str(len(allevents)) + ')'
				tvname = name
				tvname = re.sub('\\(.*?\\)', '', tvname).strip()
				tvname = re.sub(' +', ' ', tvname)
				#================== geaendert (#4) ====================
				#if not db.checkliveTV(eid, serviceref) and str(tvname) not in excludeNames and not 'Invictus' in str(tvname):
				#		record = (eid,'in progress','','','','','',tvname.decode('utf8'),begin,'','','','','','','','',serviceref)
				#		liveTVRecords.append(record)
				minEPGBeginTime = time() - 7200 #-2h
				maxEPGBeginTime = time() + 1036800 #12Tage
				if begin > minEPGBeginTime and begin < maxEPGBeginTime:
					if not db.checkliveTV(eid, serviceref):
						if str(tvname) not in excludeNames and not 'Invictus' in str(tvname):
							record = (eid,'in progress','','','','','',tvname.decode('utf8'),begin,'','','','','','','','',serviceref)
							liveTVRecords.append(record)
				# =========================
				foundInBl = False
				name = convertTitle(name)
				if db.getblackList(convert2base64(name)):
					name = convertTitle2(name)
					if db.getblackList(convert2base64(name)):
						foundInBl = True
				if not db.checkTitle(convert2base64(name)) and not foundInBl:
					names.add(name)
			except Exception as ex:
				write_log('Fehler in get_allEventsfromEPG : ' + str(ex))
				continue
		write_log('check ' + str(len(names)) + ' new events')
		limgs = True
		if str(searchfor.value) == "nur Extradaten":
			limgs = False
		get_titleInfo(names, None, limgs, db, liveTVRecords, tvsref)
		del names
		del lines
		del allevents
		del liveTVRecords
	except Exception as ex:
		write_log("Fehler in get_allEventsfromEPG : " + str(ex))

def getTVSpielfilm(db,tvsref):
	global STATUS
	try:
		evt = 0
		founded = 0
		imgcount = 0
		trailers = 0
		coverDir = getPictureDir() + 'preview/'
		refs = db.getSrefsforUpdate()
		tcount = db.getUpdateCount()
		if refs and tvsref:
			for sRef in refs:
				try:
					if sRef in tvsref:
						evt += 1
						maxDate = db.getMaxAirtimeforUpdate(sRef)
						curDate = db.getMinAirtimeforUpdate(sRef)
						#======= geaendert (#4) ==================
						#while int(curDate) <= int(maxDate)+86400:
						while (int(curDate)-86400) <= int(maxDate)+86400:
						# ========================================
							try:
								url = 'https://live.tvspielfilm.de/static/broadcast/list/' + str(tvsref[sRef]).upper() + '/' + str(datetime.fromtimestamp(curDate).strftime("%Y-%m-%d"))
								STATUS = '(' + str(evt) + '/' + str(len(refs)) + ') durchsuche ' + tvsref[sRef] + ' f�r den ' + str(datetime.fromtimestamp(curDate).strftime("%Y-%m-%d")) + ' auf TV-Spielfilm ' + " (" + str(founded) + "/" + str(tcount) + " | " + str(imgcount) + ")"
								results = json.loads(requests.get(url, timeout=4).text)
								if results:
									lastImage = ""
									for event in results:
										try:
											airtime = 0
											if 'timestart' in event:
												airtime = int(event['timestart'])
											id = ""
											title = ""
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
											if 'title' in event:
												title = convertSigns(str(event['title']))
											if 'id' in event:
												id = str(event['id'])
											if 'images' in event:
												image = event['images'][0]['size4']
											if 'genre' in event:
												genre = event['genre']
											if 'sart_id' in event:
												categoryName = event['sart_id'].replace('U', 'Unterhaltung').replace('SE', 'Serien').replace('SPO', 'Sport').replace('SP', 'Spielfilm').replace('KIN', 'Kinder').replace('RE', 'Reportage').replace('AND', 'Sonstiges')
											if 'year' in event:
												year = event['year']
											if 'country' in event:
												country = event['country'].replace('/',' | ')
											if 'fsk' in event:
												fsk = event['fsk']
											if 'seasonNumber' in event:
												season = event['seasonNumber']
											if 'episodeNumber' in event:
												if '/' in event['episodeNumber']:
													episode = event['episodeNumber'].split('/')[0]
												else:
													episode = event['episodeNumber']
											if 'episodeTitle' in event:
												subtitle = event['episodeTitle']
											if 'preview' in event:
												leadText = event['preview']
											if 'conclusion' in event:
												conclusion = event['conclusion']

											ratingCount = 0
											ratings = 0
											if 'ratingAction' in event:
												if int(event['ratingAction']) > 0:
													ratingCount += int(event['ratingAction'] * 3.33)
													ratings += 1
											if 'ratingDemanding' in event:
												if int(event['ratingDemanding']) > 0:
													ratingCount += int(event['ratingDemanding'] * 3.33)
													ratings += 1
											if 'ratingErotic' in event:
												if int(event['ratingErotic']) > 0:
													ratingCount += int(event['ratingErotic'] * 3.33)
													ratings += 1
											if 'ratingHumor' in event:
												if int(event['ratingHumor']) > 0:
													ratingCount += int(event['ratingHumor'] * 3.33)
													ratings += 1
											if 'ratingSuspense' in event:
												if int(event['ratingSuspense']) > 0:
													ratingCount += int(event['ratingSuspense'] * 3.33)
													ratings += 1
											if ratings > 0:
												rating = str(round(float(ratingCount / ratings),1))
											#======== hinzugefuegt (#5) ====
											rating = ""
											# ==============================

											if 'videos' in event:
												imdb = event['videos'][0]['video'][0]['url']
												if db.checkTitle(convert2base64(title)):
													db.updateTrailer(imdb, convert2base64(title))

											if not db.checkTitle(convert2base64(title)) and categoryName == "Spielfilm":
												db.addTitleInfo(convert2base64(title),title,genre,year,rating,fsk,country,imdb)
											if db.checkTitle(convert2base64(title)):
												data = db.getTitleInfo(convert2base64(title))
												if genre != "" and data[2] == "":
													db.updateSingleEventInfo('genre', genre, convert2base64(title)) 
												if year != "" and data[3] == "":
													db.updateSingleEventInfo('year', year, convert2base64(title)) 
												if rating != "" and data[4] == "":
													db.updateSingleEventInfo('rating', rating, convert2base64(title)) 
												if fsk != "" and data[5] == "":
													db.updateSingleEventInfo('fsk', fsk, convert2base64(title)) 
												if country != "" and data[5] == "":
													db.updateSingleEventInfo('country', country, convert2base64(title)) 

											bld = ""
											if image != "" and str(searchfor.value) != "nur Extradaten" and previewImages:
												bld = image
												imgname = title + ' - '
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
											#=== geandert (#4) title hinz. ===

											db.updateliveTVS(id,subtitle,image,year,fsk,rating,leadText,conclusion,categoryName,season,episode,genre,country,imdb,sRef,airtime,title)
											# ===========================
											founded = tcount - db.getUpdateCount()
											if founded == success:
												write_log('no matches found for ' + str(title) + ' on ' + tvsref[sRef] + ' at ' + str(datetime.fromtimestamp(airtime).strftime("%d.%m.%Y %H:%M:%S")) + ' with TV-Spielfilm ', addlog.value)
											if founded > success and imdb != "":
												trailers += 1
											if founded > success and bld != "" and str(searchfor.value) != "nur Extradaten" and previewImages and str(image) != str(lastImage):
												if len(convert2base64(image)) < 255:
													imgpath = coverDir + convert2base64(image) + '.jpg'
													if downloadTVSImage(bld, imgpath):
														imgcount += 1
														lastImage = image
										except Exception as ex:
											write_log('Fehler in TV-Spielfilm : ' + str(ex) + ' - url ' + str(url),addlog.value)
											continue

								curDate = curDate + 86400
							except Exception as ex:
								write_log('Fehler in getTVSpielfilm: ' + str(ex) + ' - ' + str(url), addlog.value)
								curDate = curDate + 86400
								continue
				except Exception as ex:
					write_log('Fehler in getTVSpielfilm: ' + str(ex))
					continue
		write_log('have updated ' + str(founded) + ' events from TV-Spielfilm')
		write_log('have downloaded ' + str(imgcount) + ' images from TV-Spielfilm')
		write_log('have found ' + str(trailers) + ' trailers on TV-Spielfilm')
		db.parameter(PARAMETER_SET, 'lastpreviewImageCount', str(imgcount))
	except Exception as ex:
		write_log('Fehler in getTVSpielfilm: ' + str(ex))


def getTVMovie(db, secondRun = False):
	global STATUS
	try:
		evt = 0
		founded = 0
		imgcount = 0
		tvnames = set()
		coverDir = getPictureDir() + 'preview/'
		failedNames = []
		tcount = db.getUpdateCount()
		if not secondRun:
			tvnames = db.getTitlesforUpdate()
			write_log('check ' + str(len(tvnames)) + ' titles on TV-Movie')
		else:
			tvnames = db.getTitlesforUpdate2()
			for name in failedNames:
				tvnames.append(name)
			write_log('recheck ' + str(len(tvnames)) + ' titles on TV-Movie')
		for title in tvnames:
			try:
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
				searchurl = 'http://capi.tvmovie.de/v1/broadcasts/search?q=%s&page=1&rows=400'
#				url = searchurl % urllib2.quote(re.sub('[^0-9a-zA-Z-:!., ]+', '*', str(tvname)))#.lower())
				url = searchurl % urllib2.quote(str(tvname))#.lower())
				STATUS = '(' + str(evt) + '/' + str(len(tvnames)) + ') suche auf TV-Movie nach ' + str(tvname) + " (" + str(founded) + "/" + str(tcount) + " | " + str(imgcount) + ")"
				results = json.loads(requests.get(url, timeout=4).text)
				if results:
					if 'results' in results:
						reslist = set()
						for event in results['results']:
							reslist.add(event['title'].lower())
							if 'originalTitle' in event:
								reslist.add(event['originalTitle'].lower())
						bestmatch = get_close_matches(tvname.lower(), reslist, 2, 0.7)
						if not bestmatch:
							bestmatch = [tvname.lower()]
						nothingfound = True
						lastImage = ""
						for event in results['results']:
							try:
								original_title = 'abc123def456'
								if 'originalTitle' in event:
									original_title = event['originalTitle'].lower()
								if event['title'].lower() in bestmatch or original_title in bestmatch:
									airtime = 0
									if 'airTime' in event:
										airtime = int(mktime(datetime.strptime(str(event['airTime']), '%Y-%m-%d %H:%M:%S').timetuple()))
									if airtime <= db.getMaxAirtime(title[0]): 
										nothingfound = False
										id = ""
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
											id = str(event['id'])
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
										if 'ageRating' in event:
											if not 'Unbekannt' in str(event['ageRating']):
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
										if 'subTitle' in event:
											if not 'None' in str(event['subTitle']):
												subtitle = event['subTitle']
										if 'leadText' in event:
											leadText = event['leadText']
										if 'conclusion' in event:
											conclusion = event['conclusion']
										if 'movieStarValue' in event:
											rating = str(int(event['movieStarValue'] * 2))
										#======== hinzugefuegt (#5) ====
										rating = ""
										# ==============================
#										if 'imdbId' in event:
#											imdb = event['imdbId']

										if not db.checkTitle(convert2base64(title[0])) and categoryName == "Spielfilm":
											db.addTitleInfo(convert2base64(title[0]),title[0],genre,year,rating,fsk,country,imdb)
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
										if image != "" and str(searchfor.value) != "nur Extradaten" and previewImages:
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

										db.updateliveTV(id,subtitle,image,year,fsk,rating,leadText,conclusion,categoryName,season,episode,genre,country,imdb,title[0],airtime)
										founded = tcount - db.getUpdateCount()
										if founded > success and bld != "" and str(searchfor.value) != "nur Extradaten" and previewImages and str(image) != str(lastImage):
											if len(convert2base64(image)) < 255:
												imgpath = coverDir + convert2base64(image) + '.jpg'
												if downloadTVMovieImage(bld, imgpath):
													imgcount += 1
													lastImage = image
							except Exception as ex:
								write_log('Fehler in TV-Movie : ' + str(ex) + ' - ' + str(title[0]) + ' url ' + str(url))
								failedNames.append(title)
								continue
						if nothingfound:
							write_log('nothing found on TV-Movie for ' + str(title[0]) + ' url ' + str(url), addlog.value)
			except Exception as ex:
				write_log('Fehler in TV-Movie : ' + str(ex) + ' - ' + str(title[0]) + ' url ' + str(url))
				continue
		write_log('have updated ' + str(founded) + ' events from TV-Movie')
		write_log('have downloaded ' + str(imgcount) + ' images from TV-Movie')
		if not secondRun:
			tvsImages = db.parameter(PARAMETER_GET, 'lastpreviewImageCount', None, 0)
			imgcount += int(tvsImages)
			db.parameter(PARAMETER_SET, 'lastpreviewImageCount', str(imgcount))
			getTVMovie(db, True)
		del tvnames
		del failedNames
	except Exception as ex:
		write_log('Fehler in getTVMovie : ' + str(ex))

def correctTitleName(tvname):
	if 'CSI: New York' in tvname:
		tvname = 'CSI: NY'
	elif 'CSI: Vegas' in tvname:
		tvname = 'CSI: Den T�tern auf der Spur'
	elif 'Star Trek - Das n' in tvname:
		tvname = 'Raumschiff Enterprise - Das n�chste Jahrhundert'
	elif 'SAT.1-Fr' in tvname:
		tvname = 'Sat.1-Fr�hst�cksfernsehen'
	elif 'Gefragt - Gejagt' in tvname:
		tvname = 'Gefragt Gejagt'
	elif 'nder - Menschen - Abenteuer' in tvname:
		tvname = 'L�nder Menschen Abenteuer'
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
		tvname = 'Sp�tnachrichten'
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
			tvname = tvname[tvname.find(': ')+2:].strip()
		elif tvname.find(' - ') > 0:
			tvname = tvname[tvname.find(' - ')+3:].strip()
	return tvname.replace(' & ',' ')


def convertTitle(name):
	if name.find(' (') > 0:
		regexfinder = re.compile(r"\([12][90]\d{2}\)", re.IGNORECASE)
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
	#=========hinzugefuegt {#3) ==============
	name = name.strip(" -+&#:_")
	# ========================================
	return name

def convertTitle2(name):
	if name.find(' (') > 0:
		regexfinder = re.compile(r"\([12][90]\d{2}\)", re.IGNORECASE)
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
		name = name[:name.find('!')+1].strip()
	#=========hinzugefuegt {#3) ==============
	name = name.strip(" -+&#:_")
	# ========================================
	return name

def findEpisode(title):
	try:
		#======= geaendert (#10) ==================
		#regexfinder = re.compile('[Ss]\d{2}[Ee]\d{2}', re.MULTILINE|re.DOTALL)
		regexfinder = re.compile('[Ss]\d{1,4}[Ee]\d{1,4}', re.MULTILINE|re.DOTALL)
		# ===========================================
		ex = regexfinder.findall(str(title))
		if ex:
			removedEpisode = title
			if removedEpisode.find(str(ex[0])) > 0:
					removedEpisode = removedEpisode[:removedEpisode.find(str(ex[0]))]
			removedEpisode = convertTitle2(removedEpisode)
			#======= geandert (#3) ===============
			#SE = ex[0].replace('S','').replace('s','').split('E')
			SE = ex[0].lower().replace('s','').split('e')
			# =======================================
			return (SE[0],SE[1], removedEpisode.strip())
		return None
	except:
		return None

def convertSearchName(eventName):
	#==== Aenderung (#1): Fix-mp4 ==============r
	try:
		eventName = removeExtension(eventName)
		text = eventName.decode('utf-8', 'ignore').replace(u'\x86', u'').replace(u'\x87', u'').encode('utf-8', 'ignore')
	except:
		eventName = removeExtension(eventName)
		text = eventName.decode('utf-8', 'ignore').replace(u'\x86', u'').replace(u'\x87', u'')
	return text
	# ======================================================

def convertDateInFileName(fileName):
	regexfinder = re.compile('\d{8} - ', re.IGNORECASE)
	ex = regexfinder.findall(fileName)
	if ex:
		return fileName.replace(ex[0], '')
	return fileName

def convertYearInTitle(title):
	regexfinder = re.compile(r"\([12][90]\d{2}\)", re.IGNORECASE)
	ex = regexfinder.findall(title)
	if ex:
		return [title.replace(ex[0], '').strip(), ex[0].replace('(','').replace(')','')]
	return [title, '']

def downloadImage(url, filename, timeout=5):
	try:
		if not fileExists(filename):
			r = requests.get(url, stream=True, timeout=timeout)
			if r.status_code == 200:
				with open(filename, 'wb') as f:
					r.raw.decode_content = True
					shutil.copyfileobj(r.raw, f)
					f.close()
				r = None
			else:
				write_log("Fehlerhafter Statuscode beim Download f�r : " + str(filename) + ' auf ' + str(url))
		else:
			write_log("Picture : " + str(base64.b64decode(filename.split('/')[-1].replace('.jpg',''))) + ' exists already ', addlog.value)
	except Exception as ex:
		write_log("Fehler in download image: " + str(ex))

def downloadImage2(url, filename, timeout=5):
	try:
		if not fileExists(filename):
			r = requests.get(url, stream=True, timeout=timeout)
			if r.status_code == 200:
				with open(filename, 'wb') as f:
					r.raw.decode_content = True
					shutil.copyfileobj(r.raw, f)
					f.close()
				r = None
				return True
			else:
				return False
		else:
			return True
	except:
		return False


def checkAllImages():
	try:
		global STATUS
		removeList = []
		dirs = [getPictureDir()+'cover/',getPictureDir()+'cover/thumbnails/',getPictureDir()+'poster/',getPictureDir()+'poster/thumbnails/']
		for dir in dirs:
			filelist = glob.glob(dir + "*.*")
			c = 0
			l = len(filelist)
			for f in filelist:
				try:
					c += 1
					STATUS = str(c) + '/' + str(l) + ' �berpr�fe ' + str(f)
					img = Image.open(f)
					if img.format != 'JPEG':
						write_log('invalid image : ' + str(f) + ' ' + str(img.format))
						removeList.append(f)
					img = None
				except Exception as ex:
					write_log('invalid image : ' + str(f) + ' ' + str(ex))
					removeList.append(f)
					continue
			del filelist
		if removeList:
			for f in removeList:
				write_log('remove image : ' + str(f))
				os.remove(f)
			del removeList
		STATUS = None
		clearMem("checkAllImages")
	except Exception as ex:
		STATUS = None
		write_log("Fehler in checkAllImages: " + str(ex))

def reduceImageSize(path, db):
	try:
		global STATUS
		if 'cover' in str(path):
			imgsize = coverqualityDict[coverquality.value]
		else:
			imgsize = posterqualityDict[posterquality.value]
		sizex, sizey = imgsize.split("x",1)
		filelist = glob.glob(os.path.join(path, "*.jpg"))
		maxSize = int(maxImageSize.value)
		maxcompression = int(maxCompression.value)
		for f in filelist:
			try:
				q = 90
				if not db.getimageBlackList(f):
					oldSize = int(os.path.getsize(f)/1024.0)
					if oldSize > maxSize:
						try:
							fn= base64.b64decode((f.split('/')[-1]).rsplit('.', 1)[0])
						except:
							fn = (f.split('/')[-1]).rsplit('.', 1)[0]
							fn = fn.replace('.jpg','')
						try:
							img = Image.open(f)
						except:
							continue
						w = int(img.size[0])
						h = int(img.size[1])
						STATUS = 'Bearbeite ' + str(fn) + '.jpg mit ' + str(bytes2human(os.path.getsize(f),1)) + ' und ' + str(w) + 'x' + str(h) + 'px'
						img_bytes = StringIO.StringIO()
						img1 = img.convert('RGB', colors=256)
						img1.save(img_bytes, format='jpeg')
						if img_bytes.tell()/1024 >= oldSize:
							if w > int(sizex):
								w = int(sizex)
								h = int(sizey)
								img1 = img.resize((w,h), Image.ANTIALIAS)
								img1.save(img_bytes, format='jpeg')
						else:
							if w > int(sizex):
								w = int(sizex)
								h = int(sizey)
								img1 = img1.resize((w,h), Image.ANTIALIAS)
								img1.save(img_bytes, format='jpeg')
						if img_bytes.tell()/1024 > maxSize:
							while img_bytes.tell()/1024 > maxSize:
								img1.save(img_bytes, format='jpeg', quality=q)
								q -= 8
								if q <= maxcompression:
									break
						img1.save(f, format='jpeg', quality=q)
						write_log('file ' + str(fn) + '.jpg reduced from ' + str(bytes2human(int(oldSize*1024),1)) + ' to '+ str(bytes2human(os.path.getsize(f),1)) + ' and ' + str(w) + 'x' + str(h) + 'px')
						if os.path.getsize(f)/1024.0 > maxSize:
							write_log('Image size cannot be further reduced with the current settings!')
							db.addimageBlackList(str(f))
						img_bytes = None
						img = None
			except Exception as ex:
				write_log("Fehler in reduceImageSize: " + str(ex))
				continue
		del filelist
	except Exception as ex:
		write_log("Fehler in reduceImageSize: " + str(ex))

def reduceSigleImageSize(src, dest):
	try:
		if 'cover' in str(dest):
			imgsize = coverqualityDict[coverquality.value]
		else:
			imgsize = posterqualityDict[posterquality.value]
		sizex, sizey = imgsize.split("x",1)
		maxSize = int(maxImageSize.value)
		maxcompression = int(maxCompression.value)
		q = 90
		try:
			oldSize = int(os.path.getsize(src)/1024.0)
			if oldSize > maxSize:
				try:
					fn= base64.b64decode((src.split('/')[-1]).rsplit('.', 1)[0])
				except:
					fn = (src.split('/')[-1]).rsplit('.', 1)[0]
					fn = fn.replace('.jpg','')
				try:
					img = Image.open(src)
					w = int(img.size[0])
					h = int(img.size[1])
					write_log('convert image ' + str(fn) + '.jpg with ' + str(bytes2human(os.path.getsize(src),1)) + ' and ' + str(w) + 'x' + str(h) + 'px')
					img_bytes = StringIO.StringIO()
					img1 = img.convert('RGB', colors=256)
					img1.save(img_bytes, format='jpeg')
					if img_bytes.tell()/1024 >= oldSize:
						if w > int(sizex):
							w = int(sizex)
							h = int(sizey)
							img1 = img.resize((w,h), Image.ANTIALIAS)
							img1.save(img_bytes, format='jpeg')
					else:
						if w > int(sizex):
							w = int(sizex)
							h = int(sizey)
							img1 = img1.resize((w,h), Image.ANTIALIAS)
							img1.save(img_bytes, format='jpeg')
					if img_bytes.tell()/1024 > maxSize:
						while img_bytes.tell()/1024 > maxSize:
							img1.save(img_bytes, format='jpeg', quality=q)
							q -= 8
							if q <= maxcompression:
								break
					img1.save(dest, format='jpeg', quality=q)
					write_log('file ' + str(fn) + '.jpg reduced from ' + str(bytes2human(int(oldSize*1024),1)) + ' to '+ str(bytes2human(os.path.getsize(dest),1)) + ' and ' + str(w) + 'x' + str(h) + 'px')
					if os.path.getsize(dest)/1024.0 > maxSize:
						write_log('Image size cannot be further reduced with the current settings!')
					img_bytes = None
					img = None
				except Exception as ex:
					write_log("Fehler in reduceSingleImageSize: " + str(ex))
		except Exception as ex:
			write_log("Fehler in reduceSingleImageSize: " + str(ex))
	except Exception as ex:
		write_log("Fehler in reduceSingleImageSize: " + str(ex))

def createThumbnails(path):
	try:
		global STATUS
		wp, hp = skin.parameters.get("EventLibraryThumbnailPosterSize", (60, 100))
		wc, hc = skin.parameters.get("EventLibraryThumbnailCoverSize", (100, 60))
		filelist = glob.glob(os.path.join(path, "*.jpg"))
		for f in filelist:
			try:
				if f.endswith('.jpg'):
					if 'bGl2ZSBibDog' in str(f):
						os.remove(f)
					else:
						destfile = f.replace('cover', 'cover/thumbnails').replace('poster', 'poster/thumbnails').replace('preview', 'preview/thumbnails')
						if not fileExists(destfile):
							STATUS = 'erzeuge Thumbnail f�r ' + str(f)
							img = Image.open(f)
							imgnew = img.convert('RGBA', colors=256)
							if 'cover' in str(f) or 'preview' in str(f):
								imgnew = img.resize((wc,hc), Image.ANTIALIAS)
							else:
								imgnew = img.resize((wp,hp), Image.ANTIALIAS)
							imgnew.save(destfile)
							img = None
			except Exception as ex:
				write_log("Fehler in createThumbnails: " + str(f) + ' - ' + str(ex))
				os.remove(f)
				continue
		del filelist
	except Exception as ex:
		write_log("Fehler in createThumbnails: " + str(ex))

def createSingleThumbnail(src, dest):
	try:
		wp, hp = skin.parameters.get("EventLibraryThumbnailPosterSize", (60, 100))
		wc, hc = skin.parameters.get("EventLibraryThumbnailCoverSize", (100, 60))
		destfile = dest.replace('cover', 'cover/thumbnails').replace('poster', 'poster/thumbnails')
		write_log('create single thumbnail from source ' + str(src) + ' to ' + str(destfile) + ' with ' + str(wc) + 'x' + str(hc) + 'px')
		img = Image.open(src)
		imgnew = img.convert('RGBA', colors=256)
		if 'cover' in str(dest) or 'preview' in str(dest):
			imgnew = img.resize((wc,hc), Image.ANTIALIAS)
		else:
			imgnew = img.resize((wp,hp), Image.ANTIALIAS)
		imgnew.save(destfile)
		if fileExists(destfile):
			write_log('thumbnail created')
		img = None
	except Exception as ex:
		os.remove(src)
		write_log("Fehler in createSingleThumbnail: " + str(src) + ' - ' + str(ex))

def get_titleInfo(titles, research=None, loadImages=True, db=None, liveTVRecords=[],tvsref=None):
	global STATUS
	if isconnected() == 0 and isInstalled:
		tvdbV4 = get_TVDb()
		if not tvdbV4:
			write_log('TVDb API-V4 is not in use!')
		posterDir = getPictureDir()+'poster/'
		coverDir = getPictureDir()+'cover/'
		previewDir = getPictureDir()+'preview/'
		posters = 0
		covers = 0
		entrys = 0
		blentrys = 0
		position = 0
		for title in titles:
			try:
				if title and title != '' and title != ' ' and not 'BL:' in title:
					tmdb.API_KEY = get_keys('tmdb')
					tvdb.KEYS.API_KEY = get_keys('tvdb')
					titleinfo = {
						"title" : "",
						"genre" : "",
						"poster_url" : "",
						"backdrop_url" : "",
						"year" : "",
						"rating" : "",
						"fsk" : "",
						"country" : ""
						}
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
		#			write_log('################################################### themoviedb movie ##############################################')
					try:
						STATUS = str(position) + '/' + str(len(titles)) + ' : themoviedb movie -' + str(title)  + '  (' + str(posters)  + '|' + str(covers)  + '|' + str(entrys)  + '|' + str(blentrys)  + ')'
						write_log('looking for ' + str(title) + ' on themoviedb movie', addlog.value)
						search = tmdb.Search()
						if jahr != '':
							res = search.movie(query=title, language='de', year=jahr)
						else:
							res = search.movie(query=title, language='de')
						if res:
							#===== geaendert (#9) ========
							#if res['results']:
							if res.get('results',""):
							# =============================
								reslist = []
								for item in res['results']:
									if not 'love blows' in str(item['title'].lower()):
										reslist.append(item['title'].lower())
								bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
								if not bestmatch:
									bestmatch = [title.lower()]
								for item in res['results']:
									if item['title'].lower() == bestmatch[0]:
										foundAsMovie = True
										write_log('found ' + str(bestmatch[0]) + ' for ' + str(title.lower()) + ' on themoviedb movie', addlog.value)
										#===== geaendert (#9) ========
										#if item['original_title']:
										if item.get('original_title',""):
										# =============================
											org_name = item['original_title']
										#===== geaendert (#9) ========
										#if item['poster_path'] and loadImages:
										if item.get('poster_path',"") and loadImages:
										# =============================
											if item['poster_path'].endswith('.jpg'):
												titleinfo['poster_url'] = 'http://image.tmdb.org/t/p/original' +  item['poster_path']
										#===== geaendert (#9) ========
										#if item['backdrop_path'] and loadImages:
										if item.get('backdrop_path',"") and loadImages:
										# =============================
											if item['backdrop_path'].endswith('.jpg'):
												titleinfo['backdrop_url'] = 'http://image.tmdb.org/t/p/original' +  item['backdrop_path']
										if 'release_date' in item:
											titleinfo['year'] = item['release_date'][:4]
										#===== geaendert (#9) ========
										#if item['genre_ids']
										if item.get('genre_ids',""):
										# =============================
											for genre in item['genre_ids']:
												if not tmdb_genres[genre] in titleinfo['genre']:
													titleinfo['genre'] = titleinfo['genre'] + tmdb_genres[genre] + ' '
										if 'vote_average' in item and item['vote_average'] != "0":
											titleinfo['rating'] = str(item['vote_average'])
										if 'id' in item:
											details = tmdb.Movies(item['id'])
											#===== hinzugefuegt try (#9) ========
											try:
												for country in details.releases(language='de')['countries']:
													if str(country['iso_3166_1']) == "DE":
														titleinfo['fsk'] = str(country['certification'])
														break
												for country in details.info(language='de')['production_countries']:
													titleinfo['country'] = titleinfo['country'] + country['iso_3166_1'] + " | "
												titleinfo['country'] = titleinfo['country'][:-3]
												imdb_id = details.info(language='de')['imdb_id']
											except Exception as ex:
												pass
											# =====================
											if not titleinfo['poster_url'].startswith('http') or not titleinfo['backdrop_url'].startswith('http') and loadImages:
												try:
													if not titleinfo['backdrop_url'].startswith('http'):
														showimgs = details.images(language='de')['backdrops']
														if showimgs:
															titleinfo['backdrop_url'] = 'http://image.tmdb.org/t/p/original' +  showimgs[0]['file_path']
												except Exception as ex:
													pass
												try:
													if not titleinfo['poster_url'].startswith('http'):
														showimgs = details.images(language='de')['posters']
														if showimgs:
															titleinfo['poster_url'] = 'http://image.tmdb.org/t/p/original' +  showimgs[0]['file_path']
												except Exception as ex:
													pass
										break
					except Exception as ex:
						write_log('Fehler in get_titleInfo themoviedb movie : ' + str(ex))

		#			write_log('################################################### themoviedb tv ##############################################')
					try:
						if not foundAsMovie:
							STATUS = str(position) + '/' + str(len(titles)) + ' : themoviedb tv -' + str(title)  + '  (' + str(posters)  + '|' + str(covers)  + '|' + str(entrys)  + '|' + str(blentrys)  + ')'
							write_log('looking for ' + str(title) + ' on themoviedb tv', addlog.value)
							search = tmdb.Search()
							searchName = findEpisode(title)
							if searchName: 
								if jahr != '':
									res = search.tv(query=searchName[2], language='de', year=jahr, include_adult=True, search_type='ngram')
								else:
									res = search.tv(query=searchName[2], language='de', include_adult=True, search_type='ngram')
							else:
								if jahr != '':
									res = search.tv(query=title, language='de', year=jahr) 
								else:
									res = search.tv(query=title, language='de') 
							if res:
								if res['results']:
									reslist = []
									for item in res['results']:
										if not 'love blows' in str(item['name'].lower()):
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
											write_log('found ' + str(bestmatch[0]) + ' for ' + str(title.lower()) + ' on themoviedb tv', addlog.value)
											if searchName:
												try:
													details = tmdb.TV_Episodes(item['id'],searchName[0],searchName[1])
													if details:
														epi = details.info(language='de')
														#imgs = details.images(language='de')
														if 'air_date' in epi:
															titleinfo['year'] = epi['air_date'][:4]
														if 'vote_average' in epi:
															titleinfo['rating'] = epi['vote_average']
														if epi['still_path'] and loadImages:
															if epi['still_path'].endswith('.jpg'):
																titleinfo['backdrop_url'] = 'http://image.tmdb.org/t/p/original' +  epi['still_path']
														#===== geaendert (#9) ========
														#if item['origin_country']
														if item.get('origin_country',""):
														# =============================
															for country in item['origin_country']:
																titleinfo['country'] = titleinfo['country'] + country + ' | '
															titleinfo['country'] = titleinfo['country'][:-3]
														#===== geaendert (#9) ========
														#if item['genre_ids']
														if item.get('genre_ids',""):
														# =============================
															for genre in item['genre_ids']:
																if not tmdb_genres[genre] in titleinfo['genre']:
																	titleinfo['genre'] = titleinfo['genre'] + tmdb_genres[genre] + '-Serie '
												except:
													pass
											else:
												#===== geaendert (#9) ========
												#if item['original_name']
												if item.get('original_name',""):
												# =============================
													org_name = item['original_name']
												#===== geaendert (#9) ========
												#if item['origin_country']
												if item.get('origin_country',""):
												# =============================
													for country in item['origin_country']:
														titleinfo['country'] = titleinfo['country'] + country + ' | '
													titleinfo['country'] = titleinfo['country'][:-3]
												#===== geaendert (#9) ========
												#if item['poster_path'] and loadImages:
												if item.get('poster_path',"") and loadImages:
												# =============================
													if item['poster_path'].endswith('.jpg'):
														titleinfo['poster_url'] = 'http://image.tmdb.org/t/p/original' +  item['poster_path']
												#===== geaendert (#9) ========
												#if item['backdrop_path'] and loadImages:
												if item.get('backdrop_path',"") and loadImages:
												# =============================
													if item['backdrop_path'].endswith('.jpg'):
														titleinfo['backdrop_url'] = 'http://image.tmdb.org/t/p/original' +  item['backdrop_path']
												if 'first_air_date' in item:
													titleinfo['year'] = item['first_air_date'][:4]
												#===== geaendert (#9) ========
												#if item['genre_ids']
												if item.get('genre_ids',""):
												# =============================
													for genre in item['genre_ids']:
														if not tmdb_genres[genre] in titleinfo['genre']:
															titleinfo['genre'] = titleinfo['genre'] + tmdb_genres[genre] + '-Serie '
												if 'vote_average' in item and item['vote_average'] != "0":
													titleinfo['rating'] = str(item['vote_average'])
												if 'id' in item:
													details = tmdb.TV(item['id'])
													#===== hinzugefuegt try (#9) ========
													try:
														for country in details.content_ratings(language='de')['results']:
															if str(country['iso_3166_1']) == "DE":
																titleinfo['fsk'] = str(country['rating'])
																break
													except Exception as ex:
															pass
													# ==================================
													if not titleinfo['poster_url'].startswith('http') or not titleinfo['backdrop_url'].startswith('http') and loadImages:
														try:
															if not titleinfo['backdrop_url'].startswith('http'):
																showimgs = details.images(language='de')['backdrops']
																if showimgs:
																	titleinfo['backdrop_url'] = 'http://image.tmdb.org/t/p/original' +  showimgs[0]['file_path']
														except Exception as ex:
															pass
														try:
															if not titleinfo['poster_url'].startswith('http'):
																showimgs = details.images(language='de')['posters']
																if showimgs:
																	titleinfo['poster_url'] = 'http://image.tmdb.org/t/p/original' +  showimgs[0]['file_path']
														except Exception as ex:
															pass
											break
					except Exception as ex:
						write_log('Fehler in get_titleInfo themoviedb tv : ' + str(ex))

		#			write_log('################################################### thetvdb ##############################################')
					if not foundAsMovie and not foundAsSeries:
						if True:
							STATUS = str(position) + '/' + str(len(titles)) + ' : thetvdb -' + str(title)  + '  (' + str(posters)  + '|' + str(covers)  + '|' + str(entrys)  + '|' + str(blentrys)  + ')'
							write_log('looking for ' + str(title) + ' on thetvdb', addlog.value)
							seriesid = None
							search = tvdb.Search()
							searchTitle = convertTitle2(title)
							try:
								try:
									response = search.series(searchTitle, language="de")
									if response:
										reslist = []
										for result in response:
											if not 'love blows' in str(result['seriesName'].lower()):
												reslist.append(result['seriesName'].lower())
										bestmatch = get_close_matches(searchTitle.lower(), reslist, 1, 0.7)
										if not bestmatch:
											bestmatch = [searchTitle.lower()]
										for result in response:
											if result['seriesName'].lower() == bestmatch[0]:
												write_log('found ' + str(bestmatch[0]) + ' for ' + str(title.lower()) + ' on thetvdb', addlog.value)
												seriesid = result['id']
												break
								except Exception as ex:
									try:
										response = search.series(searchTitle)
										if response:
											reslist = []
											for result in response:
												if not 'love blows' in str(result['seriesName'].lower()):
													reslist.append(result['seriesName'].lower())
											bestmatch = get_close_matches(searchTitle.lower(), reslist, 1, 0.7)
											if not bestmatch:
												bestmatch = [searchTitle.lower()]
											for result in response:
												if result['seriesName'].lower() == bestmatch[0]:
													write_log('found ' + str(bestmatch[0]) + ' for ' + str(title.lower()) + ' on thetvdb', addlog.value)
													seriesid = result['id']
													break
									except Exception as ex:
										pass

								if seriesid:
									foundEpisode = False
									show = tvdb.Series(seriesid)
									response = show.info()
									epis = tvdb.Series_Episodes(seriesid)
									episoden = None
									try:
										episoden = epis.all()
									except:
										pass
									epilist = []
									if episoden:
										if episoden != 'None':
											for episode in episoden:
												epilist.append(str(episode['episodeName']).lower())
											bestmatch = get_close_matches(title.lower(), epilist, 1, 0.7)
											if not bestmatch:
												bestmatch = [title.lower()]
											for episode in episoden:
												try:
													if str(episode['episodeName']).lower() == str(bestmatch[0]):
														foundEpisode = True
														if 'firstAired' in episode and episode['firstAired'] != None:
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
														if 'imdbId' in episode and episode['imdbId'] != None:
															imdb_id = episode['imdbId']
														if response:
															if titleinfo['genre'] == "" and 'genre' in response:
																if response['genre'] and str(response['genre']) != 'None':
																	for genre in response['genre']:
																		titleinfo['genre'] = titleinfo['genre'] + genre + '-Serie '
															titleinfo['genre'] = titleinfo['genre'].replace("Documentary", "Dokumentation").replace("Children", "Kinder")
															if titleinfo['country'] == "" and response['network'] != None:
																if response['network'] in networks:
																	titleinfo['country'] = networks[response['network']]
															#===== geaendert (#9) ========
															#if response['poster'] and loadImages:
															if response.get('poster',"") and loadImages:
															# =============================
																if str(response['poster']).endswith('.jpg') and not titleinfo['poster_url'].startswith('http'):
																	titleinfo['poster_url'] = 'https://www.thetvdb.com/banners/' + response['poster']
														break
												except:
													write_log('Fehler in get_titleInfo thetvdb Episoden : ' + str(ex) + ' ' + str(episode))
													continue

									if response and not foundEpisode:
										if titleinfo['year'] == "":
											titleinfo['year'] = response['firstAired'][:4]
										if titleinfo['genre'] == "":
											if response['genre']:
												for genre in response['genre']:
													titleinfo['genre'] = titleinfo['genre'] + genre + '-Serie '
										titleinfo['genre'] = titleinfo['genre'].replace("Documentary", "Dokumentation").replace("Children", "Kinder")
										if titleinfo['country'] == "":
											if response['network'] in networks:
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
										#===== geaendert (#9) ========
										#if response['poster'] and loadImages:
										if response.get('poster',"") and loadImages:
										# =============================
											if response['poster'].endswith('.jpg') and not titleinfo['poster_url'].startswith('http'):
												titleinfo['poster_url'] = 'https://www.thetvdb.com/banners/' + response['poster']
										#===== geaendert (#9) ========
										#if response['fanart'] and loadImages:
										if response.get('fanart',"") and loadImages:
										# =============================
											if response['fanart'].endswith('.jpg') and not titleinfo['backdrop_url'].startswith('http'):
												titleinfo['backdrop_url'] = 'https://www.thetvdb.com/banners/' + response['fanart']
										if not titleinfo['poster_url'].startswith('http') or not titleinfo['backdrop_url'].startswith('http') and loadImages:
											showimgs = tvdb.Series_Images(seriesid)
											try:
												if not titleinfo['backdrop_url'].startswith('http'):
													try:
														response = showimgs.fanart(language=lang)
													except:
														response = showimgs.fanart()
													if response and str(response) != 'None':
														titleinfo['backdrop_url'] = 'https://www.thetvdb.com/banners/' + response[0]['fileName']
											except Exception as ex:
												pass
											try:
												if not titleinfo['poster_url'].startswith('http'):
													try:
														response = showimgs.poster(language=lang)
													except:
														response = showimgs.poster()
													if response and str(response) != 'None':
														titleinfo['poster_url'] = 'https://www.thetvdb.com/banners/' + response[0]['fileName']
											except Exception as ex:
												pass
							except Exception as ex:
								write_log('Fehler in get_titleInfo thetvdb : ' + str(ex) + ' ' + str(title))

		#			write_log('################################################### maze.tv ##############################################')
					if not foundAsMovie:
						if titleinfo['genre'] == "" or titleinfo['country'] == "" or titleinfo['year'] == "" or titleinfo['rating'] == "" or titleinfo['poster_url'] == "":
							STATUS = str(position) + '/' + str(len(titles)) + ' : maze.tv -' + str(title)  + '  (' + str(posters)  + '|' + str(covers)  + '|' + str(entrys)  + '|' + str(blentrys)  + ')'
							write_log('looking for ' + str(title) + ' on maze.tv', addlog.value)
							try:
								if org_name:
									url = "http://api.tvmaze.com/search/shows?q=%s" % (org_name)
								else:
									url = "http://api.tvmaze.com/search/shows?q=%s" % (title)
								r = requests.get(url, timeout=5)
								if r.status_code == 200:
									res = json.loads(r.content)
									if res:
										reslist = []
										
										
										for item in res:
											#===== geaendert (#9) ========
											#if not 'love blows' in str(item['show']['name'].lower()):
											if item.get('show',"") and item['show'].get('name',"") and not 'love blows' in str(item['show']['name'].lower()):
											# =============================
												reslist.append(item['show']['name'].lower())
										bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
										if not bestmatch:
											bestmatch = [title.lower()]
										for item in res:
											#===== geaendert (#9) ========
											#if item['show']['name']:
											if item.get('show',"") and item['show'].get('name',"") and item['show']['name'].lower() == bestmatch[0]:
											# =============================
												#===== geaendert (#9) ========
												#if item['show']['network']['country'] and titleinfo['country'] == "":
												if item['show'].get('network',"") and item['show']['network'].get('country',"") and item['show']['network']['country'].get('code',"") and titleinfo['country'] == "":
												# =============================
													titleinfo['country'] = item['show']['network']['country']['code']
												#===== geaendert (#9) ========
												#if item['show']['premiered'] and titleinfo['year'] == "":
												if item['show'].get('premiered',"") and titleinfo['year'] == "":
													titleinfo['year'] = item['show']['premiered'][:4]
												# =============================
												#===== geaendert (#9) ========
												#if item['show']['genres'] and titleinfo['genre'] == "":
												if item['show'].get('genres',"") and titleinfo['genre'] == "":
												# =============================
													for genre in item['show']['genres']:
														if not genre in titleinfo['genre']:
															titleinfo['genre'] = titleinfo['genre'] + genre + '-Serie '
													titleinfo['genre'] = titleinfo['genre'].replace("Documentary", "Dokumentation").replace("Children", "Kinder")
												#===== geaendert (#9) ========
												#if item['show']['image'] and not titleinfo['poster_url'].startswith('http') and loadImages:
												if item['show'].get('image',"") and not titleinfo['poster_url'].startswith('http') and loadImages:
												# =============================
													titleinfo['poster_url'] = item['show']['image']['original']
												#===== geaendert (#9) ========
												#if item['show']['rating']['average'] and titleinfo['rating'] == "":
												if item['show'].get('rating',"") and item['show']['rating'].get('average',"") and titleinfo['rating'] == "":
												# =============================
													titleinfo['rating'] = item['show']['rating']['average']
												#===== geaendert (#9) ========
												#if item['show']['externals']['imdb'] and not imdb_id:
												if item['show'].get('externals',"") and item['show']['externals'].get('imdb',"") and not imdb_id:
												# =============================
													imdb_id = item['show']['externals']['imdb']
												
												break
							except Exception as ex:
								write_log('Fehler in get_titleInfo maze.tv : ' + str(ex))

		#			write_log('################################################### omdb ##############################################')
					if not foundAsMovie and not foundAsSeries:
						try:
							STATUS = str(position) + '/' + str(len(titles)) + ' : omdb -' + str(title)  + '  (' + str(posters)  + '|' + str(covers)  + '|' + str(entrys)  + '|' + str(blentrys)  + ')'
							write_log('looking for ' + str(title) + ' on omdb', addlog.value)
							if imdb_id:
								url = "http://www.omdbapi.com/?apikey=%s&i=%s" % (get_keys('omdb'), imdb_id)
							else:
								if org_name:
									url = "http://www.omdbapi.com/?apikey=%s&s=%s&page=1" % (get_keys('omdb'), org_name)
								else:
									url = "http://www.omdbapi.com/?apikey=%s&s=%s&page=1" % (get_keys('omdb'), title)
								r = requests.get(url, timeout=5)
								url = "http://www.omdbapi.com/?apikey=%s&t=%s" % (get_keys('omdb'), title)
								if r.status_code == 200:
									res = json.loads(r.content)
									if res['Response'] == "True":
										reslist = []
										for result in res['Search']:
											reslist.append(result['Title'].lower())
										bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
										if not bestmatch:
											bestmatch = [title.lower()]
										for result in res['Search']:
											if result['Title'].lower() == bestmatch[0]:
												url = "http://www.omdbapi.com/?apikey=%s&i=%s" % (get_keys('omdb'), result['imdbID'])
												break

							r = requests.get(url, timeout=5)
							if r.status_code == 200:
								res = json.loads(r.content)
								if res['Response'] == "True":
									if res['Year'] and titleinfo['year'] == "":
										titleinfo['year'] = res['Year'][:4]
									if res['Genre'] != "N/A" and titleinfo['genre'] == "":
										type = ' '
										if res['Type']:
											if res['Type'] == 'series':
												type = '-Serie'
										genres = res['Genre'].split(', ')
										for genre in genres:
											if not genre in titleinfo['genre']:
												titleinfo['genre'] = titleinfo['genre'] + genre + type
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
										titleinfo['country'] = countries[:-2].replace('West Germany','DE').replace('East Germany','DE').replace('Germany','DE').replace('France','FR').replace('Canada','CA').replace('Austria','AT').replace('Switzerland','S').replace('Belgium','B').replace('Spain','ESP').replace('Poland','PL').replace('Russia','RU').replace('Czech Republic','CZ').replace('Netherlands','NL').replace('Italy','IT')
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
						except Exception as ex:
							write_log('Fehler in get_titleInfo omdb : ' + str(ex))

					filename = convert2base64(title)
					if filename and filename != '' and filename != ' ':
						if titleinfo['genre'] == "" and titleinfo['year'] == "" and titleinfo['rating'] == "" and titleinfo['fsk'] == "" and titleinfo['country'] == "" and titleinfo['poster_url'] == "" and titleinfo['backdrop_url'] == "":
							blentrys += 1
							db.addblackList(filename)
							write_log('nothing found for : ' + str(titleinfo['title']), addlog.value)

						if titleinfo['genre'] != "" or titleinfo['year'] != "" or titleinfo['rating'] != "" or titleinfo['fsk'] != "" or titleinfo['country'] != "":
							entrys += 1
							if research:
								if db.checkTitle(research):
									db.updateTitleInfo(titleinfo['title'],titleinfo['genre'],titleinfo['year'],titleinfo['rating'],titleinfo['fsk'],titleinfo['country'],research)
								else:
									db.addTitleInfo(filename,titleinfo['title'],titleinfo['genre'],titleinfo['year'],titleinfo['rating'],titleinfo['fsk'],titleinfo['country'])
							else:
								db.addTitleInfo(filename,titleinfo['title'],titleinfo['genre'],titleinfo['year'],titleinfo['rating'],titleinfo['fsk'],titleinfo['country'])
							write_log('found data for : ' + str(titleinfo['title']), addlog.value)

						if not titleinfo['poster_url'] and loadImages:
							if titleinfo['year'] != "":
								titleinfo['poster_url'] = get_Picture(title + ' (' + titleinfo['year'] + ')', what='Poster', lang='de')
							else:
								titleinfo['poster_url'] = get_Picture(title, what='Poster', lang='de')
						if titleinfo['poster_url'] and loadImages:
							if titleinfo['poster_url'].startswith('http'):
								posters += 1
								if research:
									downloadImage(titleinfo['poster_url'], os.path.join(posterDir, research +'.jpg'))
								else:
									downloadImage(titleinfo['poster_url'], os.path.join(posterDir, filename +'.jpg'))
								if omdb_image:
									img = Image.open(os.path.join(posterDir, filename +'.jpg'))
									w, h = img.size
									if w > h:
										shutil.move(os.path.join(posterDir, filename +'.jpg'), os.path.join(coverDir, filename +'.jpg'))
									img = None
						if not titleinfo['backdrop_url'] and loadImages:
							if titleinfo['year'] != "":
								titleinfo['backdrop_url'] = get_Picture(title + ' (' + titleinfo['year'] + ')', what='Cover', lang='de')
							else:
								titleinfo['backdrop_url'] = get_Picture(title, what='Cover', lang='de')
						if titleinfo['backdrop_url'] and loadImages:
							if titleinfo['backdrop_url'].startswith('http'):
								covers += 1
								if research:
									downloadImage(titleinfo['backdrop_url'], os.path.join(coverDir, research +'.jpg'))
								else:
									downloadImage(titleinfo['backdrop_url'], os.path.join(coverDir, filename +'.jpg'))
					write_log(titleinfo, addlog.value)
			except Exception as ex:
				write_log("Fehler in get_titleInfo for : " + str(title) + ' infos = ' + str(titleinfo) + ' : ' + str(ex))
				continue
		write_log("set " + str(entrys) + " on eventInfo")
		write_log("set " + str(blentrys) + " on Blacklist")

		db.parameter(PARAMETER_SET, 'lasteventInfoCount', str(int(entrys+blentrys)))
		db.parameter(PARAMETER_SET, 'lasteventInfoCountSuccsess', str(entrys))

		STATUS = 'entferne alte Extradaten...'
		if delpreviewImages:
			cleanPreviewImages(db)
		db.cleanliveTV(int(time() - 28800))
		if len(liveTVRecords) > 0:
			write_log('try to insert ' + str(len(liveTVRecords)) + ' events into database')
			db.addliveTV(liveTVRecords)
			#======= hinzugeuegt (#4) ========
			db.parameter(PARAMETER_SET, 'lastadditionalDataCount', str(db.getUpdateCount()))
			# ================================
			getTVSpielfilm(db,tvsref)
			getTVMovie(db)
			db.updateliveTVProgress()
		if loadImages:
			write_log("looking for missing pictures")
			get_MissingPictures(db, posters, covers)
		write_log("create thumbnails for cover")
		createThumbnails(coverDir)
		write_log("create thumbnails for preview images")
		createThumbnails(previewDir)
		write_log("create thumbnails for poster")
		createThumbnails(posterDir)
		write_log("reduce large image-size")
		reduceImageSize(coverDir, db)
		reduceImageSize(previewDir, db)
		reduceImageSize(posterDir, db)
		if createMetaData.value:
			write_log("looking for missing meta-Info")
			createMovieInfo(db)
		createStatistics(db)
		if updateAELMovieWall.value:
			write_log("create MovieWall data")
			try:
				itype = None
				if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/imageType.data'):
					with open('/usr/lib/enigma2/python/Plugins/Extensions/AdvancedEventLibrary/imageType.data', 'r') as f:
						itype = f.read()
						f.close()
				if itype:
					from Plugins.Extensions.AdvancedEventLibrary.AdvancedEventLibrarySimpleMovieWall import saveList
					saveList(itype)
					write_log("MovieWall data saved with " + str(itype))
			except Exception as ex:
				write_log('save moviewall data : ' + str(ex))
		if addlog.value:
			writeTVStatistic(db)
		db.parameter(PARAMETER_SET, 'laststop', str(time()))
		write_log("Update done")
		STATUS = None
		clearMem("search")
		if research:
			return True
	else:
		STATUS = None
		clearMem("search")
		if research:
			return False

def get_Picture(title, what='Cover', lang='de'):
	if isconnected() == 0 and isInstalled:
		if coverquality.value != "w1920":
			cq = str(coverquality.value)
		else:
			cq = 'original'
		posterDir = getPictureDir()+'poster/'
		coverDir = getPictureDir()+'cover/'
		tmdb.API_KEY = get_keys('tmdb')
		picture = None
		try:
			titleNyear = convertYearInTitle(title)
			title = convertSearchName(titleNyear[0])
			jahr = str(titleNyear[1])

#			write_log('################################################### themoviedb tv ##############################################')
			try:
				search = tmdb.Search()
				searchName = findEpisode(title)
				if searchName: 
					if jahr != '':
						res = search.tv(query=searchName[2], language=str(lang), year=jahr, include_adult=True, search_type='ngram')
					else:
						res = search.tv(query=searchName[2], language=str(lang), include_adult=True, search_type='ngram')
				else:
					if jahr != '':
						res = search.tv(query=title, language=str(lang), year=jahr) 
					else:
						res = search.tv(query=title, language=str(lang)) 
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
							if item['name'].lower() in bestmatch:
								if 'id' in item:
									idx = tmdb.TV(item['id'])
									if searchName and what == 'Cover':
										try:
											details = tmdb.TV_Episodes(item['id'],searchName[0],searchName[1])
											if details:
												epi = details.info(language=str(lang))
												if epi:
													imgs = details.images(language=str(lang))
													if imgs:
														if 'stills' in imgs:
															picture = 'http://image.tmdb.org/t/p/' + cq + imgs['stills'][0]['file_path']
										except Exception as ex:
											write_log('get ' + str(what) + ' : ' + str(ex))
									try:
										if what == 'Cover' and not searchName:
											imgs = idx.images(language=str(lang))['backdrops']
											if imgs:
												picture = 'http://image.tmdb.org/t/p/' + cq + imgs[0]['file_path']
											if picture is None:
												imgs = idx.images()['backdrops']
												if imgs:
													picture = 'http://image.tmdb.org/t/p/' + cq + imgs[0]['file_path']
									except Exception as ex:
										write_log('get ' + str(what) + ' : ' + str(ex))
									try:
										if what == 'Poster':
											imgs = idx.images(language=str(lang))['posters']
											if imgs:
												picture = 'http://image.tmdb.org/t/p/' + str(posterquality.value) + imgs[0]['file_path']
											if picture is None:
												imgs = idx.images()['posters']
												if imgs:
													picture = 'http://image.tmdb.org/t/p/' + str(posterquality.value) + imgs[0]['file_path']
									except Exception as ex:
										write_log('get ' + str(what) + ' : ' + str(ex))
			except Exception as ex:
				write_log('get ' + str(what) + ' : ' + str(ex))

#			write_log('################################################### themoviedb movie ##############################################')
			if picture is None:
				try:
					search = tmdb.Search()
					if jahr != '':
						res = search.movie(query=title, language=str(lang), year=jahr)
					else:
						res = search.movie(query=title, language=str(lang))
					if res:
						if res['results']:
							reslist = []
							for item in res['results']:
								reslist.append(item['title'].lower())
							bestmatch = get_close_matches(title.lower(), reslist, 1, 0.7)
							if not bestmatch:
								bestmatch = [title.lower()]
							for item in res['results']:
								if item['title'].lower() in bestmatch:
									if 'id' in item:
										idx = tmdb.Movies(item['id'])
										try:
											if what == 'Cover':
												imgs = idx.images(language=str(lang))['backdrops']
												if imgs:
													picture = 'http://image.tmdb.org/t/p/' + cq + imgs[0]['file_path']
												if picture is None:
													imgs = idx.images()['backdrops']
													if imgs:
														picture = 'http://image.tmdb.org/t/p/' + cq + imgs[0]['file_path']
										except Exception as ex:
											write_log('get ' + str(what) + ' : ' + str(ex))
										try:
											if what == 'Poster':
												imgs = idx.images(language=str(lang))['posters']
												if imgs:
													picture = 'http://image.tmdb.org/t/p/' + str(posterquality.value) + imgs[0]['file_path']
												if picture is None:
													imgs = idx.images()['posters']
													if imgs:
														picture = 'http://image.tmdb.org/t/p/' + str(posterquality.value) + imgs[0]['file_path']
										except Exception as ex:
											write_log('get ' + str(what) + ' : ' + str(ex))
				except Exception as ex:
					write_log('get ' + str(what) + ' : ' + str(ex))

#			write_log('################################################### thetvdb ##############################################')
			if picture is None:
				tvdb.KEYS.API_KEY = get_keys('tvdb')
				seriesid = None
				search = tvdb.Search()
				searchTitle = convertTitle2(title)
				try:
					try:
						response = search.series(searchTitle, language=str(lang)) 
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
					except Exception as ex:
						try:
							response = search.series(searchTitle)
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
						except:
							pass

					if seriesid:
						epis = tvdb.Series_Episodes(seriesid)
						episoden = None
						try:
							episoden = epis.all()
						except:
							pass
						epilist = []
						if episoden:
							if episoden != 'None':
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
							try:
								if what == 'Cover':
									try:
										response = showimgs.fanart(language=str(lang))
									except:
										response = showimgs.fanart()
									if response and str(response) != 'None':
										picture = 'https://www.thetvdb.com/banners/' + response[0]['fileName'] 
							except Exception as ex:
								write_log('Fehler in get Cover : ' + str(ex))
							try:
								if what == 'Poster':
									try:
										response = showimgs.poster(language=str(lang))
									except:
										response = showimgs.poster()
									if response and str(response) != 'None':
										picture = 'https://www.thetvdb.com/banners/' + response[0]['fileName']
							except Exception as ex:
								write_log('Fehler in get Poster : ' + str(ex))
				except Exception as ex:
					write_log('Fehler in get tvdb images : ' + str(ex))

			if picture:
				write_log('researching picture result ' + str(picture) + ' for ' + str(title))
			return picture
		except Exception as ex:
			write_log('get_Picture : ' + str(ex))
			return None

def get_MissingPictures(db, poster, cover):
	try:
		global STATUS
		posterDir = getPictureDir()+'poster/'
		coverDir = getPictureDir()+'cover/'
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
			write_log('found ' + str(len(pList[0])) + ' missing covers')
			for picture in pList[0]:
				i += 1
				STATUS = 'suche fehlendes Cover f�r ' + str(picture) + ' (' + str(i) + '/' + str(len(pList[0])) + ' | ' + str(covers) + ') '
				url = get_Picture(title=picture, what='Cover', lang='de')
				if url:
					covers += 1
					downloadImage(url, os.path.join(coverDir, convert2base64(picture) +'.jpg'))
				else:
					db.addblackListCover(convert2base64(picture))
			write_log('have downloaded ' + str(covers) + ' missing covers')
		if pList[1]:
			write_log('found ' + str(len(pList[1])) + ' missing posters')
			i = 0
			for picture in pList[1]:
				i += 1
				STATUS = 'suche fehlendes Poster f�r ' + str(picture) + ' (' + str(i) + '/' + str(len(pList[1])) + ' | ' + str(posters) + ') '
				url = get_Picture(title=picture, what='Poster', lang='de')
				if url:
					posters += 1
					downloadImage(url, os.path.join(posterDir, convert2base64(picture) +'.jpg'))
				else:
					db.addblackListPoster(convert2base64(picture))
			write_log('have downloaded ' + str(posters) + ' missing posters')

		posters += poster
		covers += cover
		write_log("found " + str(posters) + " posters")
		write_log("found " + str(covers) + " covers")

		db.parameter(PARAMETER_SET, 'lastposterCount', str(posters))
		db.parameter(PARAMETER_SET, 'lastcoverCount', str(covers))
	except Exception as ex:
		write_log('get_MissingPictures : ' + str(ex))

def writeTVStatistic(db):
	root = eServiceReference(str(service_types_tv + ' FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
	serviceHandler = eServiceCenter.getInstance()
	tvbouquets = serviceHandler.list(root).getContent("SN", True)
	for bouquet in tvbouquets:
		root = eServiceReference(str(bouquet[0]))
		serviceHandler = eServiceCenter.getInstance()
		ret = serviceHandler.list(root).getContent("SN", True)
		doIt = False
		if str(bouquet[1]) in sPDict:
			if sPDict[str(bouquet[1])]:
				doIt = True
		else:
			doIt = True
		if doIt:
			for (serviceref, servicename) in ret:
				#==== hinzugefuegt (#8) =====
				if not serviceref:
					continue
				serviceref = serviceref.split("?",1)[0].decode('utf-8','ignore')
				# =========================
				count = db.getEventCount(serviceref)
				write_log('There are ' + str(count) + ' events for ' + str(servicename) + ' in database')


def get_size(path):
	total_size = 0
	for dirpath, dirnames, filenames in os.walk(path):
		for f in filenames:
			fp = os.path.join(dirpath, f)
			total_size += os.path.getsize(fp)
	return str(round(float(total_size / 1024.0 / 1024.0),1)) + 'M'

def createStatistics(db):
	try:
		DIR = getPictureDir() + 'poster/'
		posterCount = len([name for name in os.listdir(DIR) if fileExists(os.path.join(DIR, name))])
		try:
			posterSize = subprocess.check_output(['du','-sh', DIR]).split()[0].decode('utf-8')
		except subprocess.CalledProcessError as e:
			write_log("Fehler in createStatistics getposterSize : " + str(e.returncode))
			posterSize = get_size(DIR)

		DIR = getPictureDir() + 'cover/'
		coverCount = len([name for name in os.listdir(DIR) if fileExists(os.path.join(DIR, name))])
		DIR = getPictureDir() + 'preview/'
		previewCount = len([name for name in os.listdir(DIR) if fileExists(os.path.join(DIR, name))])

		DIR = getPictureDir() + 'cover/'
		try:
			coverSize = subprocess.check_output(['du','-sh', DIR]).split()[0].decode('utf-8')
		except subprocess.CalledProcessError as e:
			write_log("Fehler in createStatistics getcoverSize : " + str(e.returncode))
			coverSize = get_size(DIR)
		DIR = getPictureDir() + 'preview/'
		try:
			previewSize = subprocess.check_output(['du','-sh', DIR]).split()[0].decode('utf-8')
		except subprocess.CalledProcessError as e:
			write_log("Fehler in createStatistics getcoverSize : " + str(e.returncode))
			previewSize = get_size(DIR)

		try:
			inodes = subprocess.check_output(['df','-i', dir]).split()
			nodestr = inodes[-4] + ' | ' + inodes[-5] + ' | ' + inodes[-2]
		except:
			nodestr = "0"

		db.parameter(PARAMETER_SET, 'posterCount', str(posterCount))
		db.parameter(PARAMETER_SET, 'coverCount', str(coverCount))
		db.parameter(PARAMETER_SET, 'previewCount', str(previewCount))
		db.parameter(PARAMETER_SET, 'posterSize', str(posterSize))
		db.parameter(PARAMETER_SET, 'coverSize', str(coverSize))
		db.parameter(PARAMETER_SET, 'previewSize', str(previewSize))
		db.parameter(PARAMETER_SET, 'usedInodes', str(nodestr))
	except Exception as ex:
		write_log('createStatistics : ' + str(ex))

def get_PictureList(title, what='Cover', count=20, b64title=None, lang='de', bingOption=''):
	if isconnected() == 0 and isInstalled:
		if coverquality.value != "w1920":
			cq = str(coverquality.value)
		else:
			cq = 'original'
		posterDir = getPictureDir()+'poster/'
		coverDir = getPictureDir()+'cover/'
		tmdb.API_KEY = get_keys('tmdb')
		pictureList = []
		try:
			titleNyear = convertYearInTitle(title)
			title = convertSearchName(titleNyear[0])
			jahr = str(titleNyear[1])
			write_log('searching ' + str(what) + ' for ' + str(title) + ' with language = ' + str(lang))
			if not b64title:
				b64title = convert2base64(title)

				
			if True:
				tvdb.KEYS.API_KEY = get_keys('tvdb')
				seriesid = None
				search = tvdb.Search()
				searchTitle = convertTitle2(title)
				try:
					try:
						response = search.series(searchTitle, language=str(lang)) 
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
					except Exception as ex:
						try:
							response = search.series(searchTitle)
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
						except:
							pass

					if seriesid:
						epis = tvdb.Series_Episodes(seriesid)
						episoden = None
						try:
							episoden = epis.all()
						except:
							pass
						epiname = ''
						epilist = []
						if episoden:
							if episoden != 'None':
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
							try:
								if what == 'Cover':
									try:
										response = showimgs.fanart(language=str(lang))
									except:
										response = showimgs.fanart()
									if response and str(response) != 'None':
										for img in response:
											itm = [result['seriesName'] + epiname, what, str(img['resolution']) + ' gefunden auf TVDb', 'https://www.thetvdb.com/banners/' + img['fileName'], os.path.join(coverDir, b64title +'.jpg'), convert2base64(img['fileName']) +'.jpg']
											pictureList.append((itm,))
							except Exception as ex:
								write_log('Fehler in get Cover : ' + str(ex))
							try:
								if what == 'Poster':
									try:
										response = showimgs.poster(language=str(lang))
									except:
										response = showimgs.poster()
									if response and str(response) != 'None':
										for img in response:
											itm = [result['seriesName'] + epiname, what, str(img['resolution']) + ' gefunden auf TVDb', 'https://www.thetvdb.com/banners/' + img['fileName'], os.path.join(posterDir, b64title +'.jpg'), convert2base64(img['fileName']) +'.jpg']
											pictureList.append((itm,))
							except Exception as ex:
								write_log('Fehler in get Poster : ' + str(ex))
				except Exception as ex:
					write_log('Fehler in get tvdb images : ' + str(ex))

#			write_log('################################################### themoviedb tv ##############################################')
			try:
				search = tmdb.Search()
				searchName = findEpisode(title)
				if searchName: 
					if jahr != '':
						res = search.tv(query=searchName[2], language=str(lang), year=jahr, include_adult=True, search_type='ngram')
					else:
						res = search.tv(query=searchName[2], language=str(lang), include_adult=True, search_type='ngram')
				else:
					if jahr != '':
						res = search.tv(query=title, language=str(lang), year=jahr) 
					else:
						res = search.tv(query=title, language=str(lang)) 
				if res:
					if res['results']:
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
						
						#========== geaendert (#7) ===============
						#for item in res['results']:
						#	write_log('found on TMDb TV ' + str(item['name']))
						#	if item['name'].lower() in bestmatch:
						appendTopHit = True
						itemList = []
						for index,item in enumerate(res['results']):
							if item['name'].lower() in bestmatch:
								itemList.append(item)
								if index == 0:
									appendTopHit = False
						if appendTopHit:
							itemList.append(res['results'][0])
						for item in itemList:
							if item: #AlwaysTrue
								write_log('found on TMDb TV ' + str(item['name']))
						# ==================================================
								if 'id' in item:
									idx = tmdb.TV(item['id'])
									if searchName and what == 'Cover':
										try:
											details = tmdb.TV_Episodes(item['id'],searchName[0],searchName[1])
											if details:
												epi = details.info(language=str(lang))
												if epi:
													imgs = details.images(language=str(lang))
													if imgs:
														if 'stills' in imgs:
															for img in imgs['stills']:
																	imgsize = str(img['width']) + 'x' + str(img['height'])
																	itm = [item['name'] + ' - ' + epi['name'], what, str(imgsize) + ' gefunden auf TMDb TV', 'http://image.tmdb.org/t/p/' + cq + img['file_path'], os.path.join(coverDir, b64title +'.jpg'), convert2base64(img['file_path']) +'.jpg']
																	pictureList.append((itm,))
													#======== hinzugeugt (#6) =========
													if epi.get("still_path","") and epi['still_path'].endswith('.jpg'):
														itm = [item['name'] + ' - ' + epi['name'], what, 'gefunden auf TMDb TV', 'http://image.tmdb.org/t/p/' + cq + epi['still_path'], os.path.join(coverDir, b64title +'.jpg'), convert2base64(epi['still_path']) +'.jpg']
														pictureList.append((itm,))
													# ================================
										except:
											pass
									try:
										#==== geaendert (#6) =====
										#if what == 'Cover' and not searchName:
										if what == 'Cover':
										# ========================
											imgs = idx.images(language=str(lang))['backdrops']
											if imgs:
												for img in imgs:
													imgsize = str(img['width']) + 'x' + str(img['height'])
													itm = [item['name'], what, str(imgsize) + ' gefunden auf TMDb TV', 'http://image.tmdb.org/t/p/' + cq + img['file_path'], os.path.join(coverDir, b64title +'.jpg'), convert2base64(img['file_path']) +'.jpg']
													pictureList.append((itm,))
											if len(imgs) < 2:
												imgs = idx.images()['backdrops']
												if imgs:
													for img in imgs:
														imgsize = str(img['width']) + 'x' + str(img['height'])
														itm = [item['name'], what, str(imgsize) + ' gefunden auf TMDb TV', 'http://image.tmdb.org/t/p/' + cq + img['file_path'], os.path.join(coverDir, b64title +'.jpg'), convert2base64(img['file_path']) +'.jpg']
														pictureList.append((itm,))
									except:
										pass
									try:
										if what == 'Poster':
											imgs = idx.images(language=str(lang))['posters']
											if imgs:
												for img in imgs:
													imgsize = str(img['width']) + 'x' + str(img['height'])
													itm = [item['name'], what, str(imgsize) + ' gefunden auf TMDb TV', 'http://image.tmdb.org/t/p/' + str(posterquality.value) + img['file_path'], os.path.join(posterDir, b64title +'.jpg'), convert2base64(img['file_path']) +'.jpg']
													pictureList.append((itm,))
											if len(imgs) < 2:
												imgs = idx.images()['posters']
												if imgs:
													for img in imgs:
														imgsize = str(img['width']) + 'x' + str(img['height'])
														itm = [item['name'], what, str(imgsize) + ' gefunden auf TMDb TV', 'http://image.tmdb.org/t/p/' + str(posterquality.value) + img['file_path'], os.path.join(posterDir, b64title +'.jpg'), convert2base64(img['file_path']) +'.jpg']
														pictureList.append((itm,))
									except:
										pass
			except:
				pass

#			write_log('################################################### themoviedb movie ##############################################')
			try:
				search = tmdb.Search()
				if jahr != '':
					res = search.movie(query=title, language=str(lang), year=jahr)
				else:
					res = search.movie(query=title, language=str(lang))
				if res:
					if res['results']:
						reslist = []
						for item in res['results']:
							reslist.append(item['title'].lower())
						bestmatch = get_close_matches(title.lower(), reslist, 4, 0.7)
						if not bestmatch:
							bestmatch = [title.lower()]
							
						#========== geaendert (#7) ===============
						#for item in res['results']:
						#	write_log('found on TMDb Movie ' + str(item['title']))
						#	if item['title'].lower() in bestmatch:
						appendTopHit = True
						itemList = []
						for index,item in enumerate(res['results']):
							if item['title'].lower() in bestmatch:
								itemList.append(item)
								if index == 0:
									appendTopHit = False
						if appendTopHit:
							itemList.append(res['results'][0])
						for item in itemList:
							if item: #AlwaysTrue
								write_log('found on TMDb Movie ' + str(item['title']))
						# ==================================================
								if 'id' in item:
									idx = tmdb.Movies(item['id'])
									try:
										if what == 'Cover':
											imgs = idx.images(language=str(lang))['backdrops']
											if imgs:
												for img in imgs:
													imgsize = str(img['width']) + 'x' + str(img['height'])
													itm = [item['title'], what, str(imgsize) + ' gefunden auf TMDb Movie', 'http://image.tmdb.org/t/p/' + cq + img['file_path'], os.path.join(coverDir, b64title +'.jpg'), convert2base64(img['file_path']) +'.jpg']
													pictureList.append((itm,))
											if len(imgs) < 2:
												imgs = idx.images()['backdrops']
												if imgs:
													for img in imgs:
														imgsize = str(img['width']) + 'x' + str(img['height'])
														itm = [item['title'], what, str(imgsize) + ' gefunden auf TMDb Movie', 'http://image.tmdb.org/t/p/' + cq + img['file_path'], os.path.join(coverDir, b64title +'.jpg'), convert2base64(img['file_path']) +'.jpg']
														pictureList.append((itm,))
									except:
										pass
									try:
										if what == 'Poster':
											imgs = idx.images(language=str(lang))['posters']
											if imgs:
												for img in imgs:
													imgsize = str(img['width']) + 'x' + str(img['height'])
													itm = [item['title'], what, str(imgsize) + ' gefunden auf TMDb Movie', 'http://image.tmdb.org/t/p/' + str(posterquality.value) + img['file_path'], os.path.join(posterDir, b64title +'.jpg'), convert2base64(img['file_path']) +'.jpg']
													pictureList.append((itm,))
											if len(imgs) < 2:
												imgs = idx.images()['posters']
												if imgs:
													for img in imgs:
														imgsize = str(img['width']) + 'x' + str(img['height'])
														itm = [item['title'], what, str(imgsize) + ' gefunden auf TMDb Movie', 'http://image.tmdb.org/t/p/' + str(posterquality.value) + img['file_path'], os.path.join(posterDir, b64title +'.jpg'), convert2base64(img['file_path']) +'.jpg']
														pictureList.append((itm,))
									except:
										pass
			except:
				pass

			if not pictureList and what == 'Poster':
				try:
					url = "http://www.omdbapi.com/?apikey=%s&t=%s" % (get_keys('omdb'), title)
					r = requests.get(url, timeout=5)
					if r.status_code == 200:
						res = json.loads(r.content)
						if res['Response'] == "True":
							if res['Poster'].startswith('http'):
								itm = [res['Title'], what, 'OMDB', res['Poster'], os.path.join(posterDir, b64title +'.jpg'), convert2base64('omdbPosterFile') + '.jpg']
								pictureList.append((itm,))

					url = "http://api.tvmaze.com/search/shows?q=%s" % (title)
					r = requests.get(url, timeout=5)
					if r.status_code == 200:
						res = json.loads(r.content)
						if res:
							reslist = []
							for item in res:
								#===== geaendert (#9) ========
								#reslist.append(item['show']['name'].lower())
								if item.get('show',"") and item['show'].get('name',""):
									reslist.append(item['show']['name'].lower())
								# =============================
								
							bestmatch = get_close_matches(title.lower(), reslist, 4, 0.7)
							if not bestmatch:
								bestmatch = [title.lower()]
							for item in res:
								#===== geaendert (#9) ========
								#if item['show']['name'].lower() == bestmatch[0]:
								if item.get('show',"") and item['show'].get('name',"") and item['show']['name'].lower() == bestmatch[0]:
								# =============================
									#===== geaendert (#9) ========
									#if item['show']['image']:
									if item['show'].get('image',"") and item['show']['image'].get('original',""):
									# =============================
										itm = [item['show']['name'], what, 'maze.tv', item['show']['image']['original'], os.path.join(posterDir, b64title +'.jpg'), convert2base64('mazetvPosterFile') + '.jpg']
										pictureList.append((itm,))
				except:
					pass

			if not pictureList:
				BingSearch = BingImageSearch(title+bingOption, int(count), what)
				res = BingSearch.search()
				i = 0
				for image in res:
					if what == 'Poster':
						itm = [title, what, 'gefunden auf bing.com', image, os.path.join(posterDir, b64title +'.jpg'), convert2base64('bingPoster_'+str(i)) + '.jpg']
					else:
						itm = [title, what, 'gefunden auf bing.com', image, os.path.join(coverDir, b64title +'.jpg'), convert2base64('bingCover_'+str(i)) + '.jpg']
					pictureList.append((itm,))
					i += 1


			if pictureList:
				idx = 0
				write_log('found ' + str(len(pictureList)) + ' images for ' + str(title), addlog.value)
				failed = []
				while idx <= int(count) and idx < len(pictureList):
					write_log('Image : ' + str(pictureList[idx]), addlog.value)
					if not downloadImage2(pictureList[idx][0][3], os.path.join('/tmp/', pictureList[idx][0][5])):
						failed.insert(0,idx)
					idx += 1
				for erroridx in failed:
					del pictureList[erroridx]
				return pictureList[:count]
			else:
				itm = ["Keine Ergebnisse gefunden", "Bildname '" + str(b64title) + ".jpg'", None, None, None, None]
				pictureList.append((itm,))
				return pictureList
		except Exception as ex:
			write_log('get_PictureList : ' + str(ex))
			return []

def get_searchResults(title, lang='de'):
	if isconnected() == 0 and isInstalled:
		tmdb.API_KEY = get_keys('tmdb')
		resultList = []
		try:
			titleNyear = convertYearInTitle(title)
			title = convertSearchName(titleNyear[0])
			jahr = str(titleNyear[1])
			write_log('searching results for ' + str(title) + ' with language = ' + str(lang))
			try:
				searchName = findEpisode(title)
				search = tmdb.Search()
				if searchName: 
					if jahr != '':
						res = search.tv(query=searchName[2], language=lang, year=jahr, include_adult=True, search_type='ngram')
					else:
						res = search.tv(query=searchName[2], language=lang, include_adult=True, search_type='ngram')
				else:
					if jahr != '':
						res = search.tv(query=title, language=lang, year=jahr) 
					else:
						res = search.tv(query=title, language=lang) 
				if res:
					if res['results']:
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
									try:
										details = tmdb.TV_Episodes(item['id'],searchName[0],searchName[1])
										if details:
											epi = details.info(language=lang)
											if 'name' in epi:
												epiname = ' - S' + searchName[0] + 'E' + searchName[1] + ' - ' + epi['name']
											if 'air_date' in epi:
												year = epi['air_date'][:4]
											if 'vote_average' in epi:
												rating = epi['vote_average']
											if 'overview' in epi:
												desc = epi['overview']
											#===== geaendert (#9) ========
											#if item['origin_country']
											if item.get('origin_country',""):
											# =============================
												for country in item['origin_country']:
													countries = countries + country + ' | '
												countries = countries[:-3]
											#===== geaendert (#9) ========
											#if item['genre_ids']
											if item.get('genre_ids',""):
											# =============================
												for genre in item['genre_ids']:
													genres = genres + tmdb_genres[genre] + '-Serie '
												maxGenres = genres.split()
												if maxGenres:
													if len(maxGenres) >= 1:
														genres = maxGenres[0]
											if 'id' in item:
												details = tmdb.TV(item['id'])
												#===== hinzugefuegt try (#9) ========
												try:
													for country in details.content_ratings(language='de')['results']:
														if str(country['iso_3166_1']) == "DE":
															fsk = str(country['rating'])
															break
												except:
													pass
												# =================================
									except:
										pass
								else:
									if 'overview' in item:
										desc = item['overview']
									#===== geaendert (#9) ========
									#if item['origin_country']
									if item.get('origin_country',""):
									# =============================
										for country in item['origin_country']:
											countries = countries + country + ' | '
										countries = countries[:-3]
									if 'first_air_date' in item:
										year = item['first_air_date'][:4]
									#===== geaendert (#9) ========
									#if item['genre_ids']
									if item.get('genre_ids',""):
									# =============================
										for genre in item['genre_ids']:
											genres = genres + tmdb_genres[genre] + '-Serie '
									if 'vote_average' in item and item['vote_average'] != "0":
										rating = str(item['vote_average'])
									if 'id' in item:
										details = tmdb.TV(item['id'])
										#===== hinzugefuegt try (#9) ========
										try:
											for country in details.content_ratings(language='de')['results']:
												if str(country['iso_3166_1']) == "DE":
													fsk = str(country['rating'])
													break
										except:
											pass
										# ====================================
								itm = [str(item['name'])+epiname, str(countries), str(year), str(genres), str(rating), str(fsk), "TMDb TV", desc]
								resultList.append((itm,))
			except:
				pass

			try:
				search = tmdb.Search()
				if jahr != '':
					res = search.movie(query=title, language=lang, year=jahr)
				else:
					res = search.movie(query=title, language=lang)
				if res:
					if res['results']:
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
								#===== geaendert (#9) ========
								#if item['genre_ids']
								if item.get('genre_ids',""):
								# =============================
									for genre in item['genre_ids']:
										genres = genres + tmdb_genres[genre] + ' '
								if 'vote_average' in item and item['vote_average'] != "0":
									rating = str(item['vote_average'])
								if 'id' in item:
									details = tmdb.Movies(item['id'])
									#===== hinzugefuegt try (#9) ========
									try:
										for country in details.releases(language='de')['countries']:
											if str(country['iso_3166_1']) == "DE":
												fsk = str(country['certification'])
												break
										for country in details.info(language='de')['production_countries']:
											countries = countries + country['iso_3166_1'] + " | "
										countries = countries[:-3]
									except:
										pass
									# ===================================*=
								itm = [str(item['title']), str(countries), str(year), str(genres), str(rating), str(fsk), "TMDb Movie", desc]
								resultList.append((itm,))
			except:
				pass

			if True:
				tvdb.KEYS.API_KEY = get_keys('tvdb')
				search = tvdb.Search()
				searchTitle = convertTitle2(title)
				searchName = findEpisode(title)
				try:
					try:
						response = search.series(searchTitle, language=lang)
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
										episoden = None
										try:
											episoden = epis.all()
										except:
											pass
										epilist = []
										if episoden:
											if episoden != 'None':
												for episode in episoden:
													epilist.append(episode['episodeName'].lower())
												bestmatch = get_close_matches(title.lower(), epilist, 1, 0.6)
												if not bestmatch:
													bestmatch = [title.lower()]
												for episode in episoden:
													try:
														if episode['episodeName'].lower() == bestmatch[0]:
															foundEpisode = True
															if 'episodeName' in episode:
																if searchName:
																	epiname = ' - S' + searchName[0] + 'E' + searchName[1] + ' - ' + episode['episodeName']
																else:
																	epiname = ' - ' + episode['episodeName']
															if 'overview' in episode:
																desc = episode['overview']
															if 'firstAired' in episode:
																year = episode['firstAired'][:4]
															if 'siteRating' in episode:
																if episode['siteRating'] != '0' and episode['siteRating'] != 'None':
																	rating = episode['siteRating']
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
																if 'genre' in response:
																	if response['genre']:
																		for genre in response['genre']:
																			genres = genres + genre + '-Serie '
																genres = genres.replace("Documentary", "Dokumentation").replace("Children", "Kinder")
																if response['network'] in networks:
																	countries = networks[response['network']]
															itm = [str(result['seriesName']+epiname), str(countries), str(year), str(genres), str(rating), str(fsk), "The TVDB", desc]
															resultList.append((itm,))
															break
													except Exception as ex:
														continue

										if response and not foundEpisode:
											if 'overview' in response:
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
					except Exception as ex:
						try:
							response = search.series(title) 
							if response:
								reslist = []
								for result in response:
									reslist.append(result['seriesName'].lower())
								bestmatch = get_close_matches(title.lower(), reslist, 10, 0.4)
								if not bestmatch:
									bestmatch = [title.lower()]
								for result in response:
									if result['seriesName'].lower() in bestmatch:
										seriesid = None
										countries = ""
										year = ""
										genres = ""
										rating = ""
										fsk = ""
										desc = ""
										seriesid = result['id']
										if seriesid:
											show = tvdb.Series(seriesid)
											response = show.info()
											if response:
												if 'overview' in response:
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
						except:
							pass
				except:
					pass



			try:
				url = "http://api.tvmaze.com/search/shows?q=%s" % (title)
				r = requests.get(url, timeout=5)
				if r.status_code == 200:
					res = json.loads(r.content)
					reslist = []
					for item in res:
						#===== geaendert (#9) ========
						#reslist.append(item['show']['name'].lower())
						if item.get('show',"") and item['show'].get('name',""):
							reslist.append(item['show']['name'].lower())
						# =============================
					bestmatch = get_close_matches(title.lower(), reslist, 10, 0.4)
					if not bestmatch:
						bestmatch = [title.lower()]
					for item in res:
						#===== geaendert (#9) ========
						#if item['show']['name'].lower() in bestmatch:
						if item.get('show',"") and item['show'].get('name',"") and item['show']['name'].lower() in bestmatch:
						# =============================
							countries = ""
							year = ""
							genres = ""
							rating = ""
							fsk = ""
							desc = ""
							#===== geaendert (#9) ========
							#if item['show']['summary']:
							if item['show'].get('summary',""):
							# =============================
								desc = item['show']['summary']
							#===== geaendert (#9) ========
							#if item['show']['network']['country']:
							if item['show'].get('network',"") and item['show']['network'].get('country',"") and item['show']['network']['country'].get('code',""):
							# =============================
								countries = item['show']['network']['country']['code']
							#===== geaendert (#9) ========
							#if item['show']['premiered']:
							if item['show'].get('premiered',""):
							# =============================
								year = item['show']['premiered'][:4]
							#===== geaendert (#9) ========
							#if item['show']['genres']:
							if item['show'].get('genres',""):
							# =============================
								for genre in item['show']['genres']:
									genres = genres + genre + '-Serie '
								genres = genres.replace("Documentary", "Dokumentation").replace("Children", "Kinder")
							#===== geaendert (#9) ========
							#if item['show']['rating']['average'] and str(item['show']['rating']['average']) != None:
							if item['show'].get('rating',"") and item['show']['rating'].get('average',"") and str(item['show']['rating']['average']) != None:
							# =============================
								rating = item['show']['rating']['average']
							itm = [str(item['show']['name']), str(countries), str(year), str(genres), str(rating), str(fsk), "maze.tv", desc]
							resultList.append((itm,))
			except: 
				pass

			try:
				url = "http://www.omdbapi.com/?apikey=%s&s=%s&page=1" % (get_keys('omdb'), title)
				r = requests.get(url, timeout=5)
				if r.status_code == 200:
					res = json.loads(r.content)
					if res['Response'] == "True":
						reslist = []
						for result in res['Search']:
							reslist.append(result['Title'].lower())
						bestmatch = get_close_matches(title.lower(), reslist, 10, 0.4)
						if not bestmatch:
							bestmatch = [title.lower()]
						for result in res['Search']:
							if result['Title'].lower() in bestmatch:
								url = "http://www.omdbapi.com/?apikey=%s&i=%s" % (get_keys('omdb'), result['imdbID'])
								r = requests.get(url, timeout=5)
								if r.status_code == 200:
									countries = ""
									year = ""
									genres = ""
									rating = ""
									fsk = ""
									desc = ""
									res = json.loads(r.content)
									if res['Response'] == "True":
										if res['Plot']:
											desc = res['Plot']
										if res['Year']:
											year = res['Year'][:4]
										if res['Genre'] != "N/A":
											type = ' '
											if res['Type']:
												if res['Type'] == 'series':
													type = '-Serie '
											resgenres = res['Genre'].split(', ')
											for genre in resgenres:
												genres = genres + genre + type
											genres = genres.replace("Documentary", "Dokumentation").replace("Children", "Kinder")
										if res['imdbRating'] != "N/A":
											rating = res['imdbRating']
										if res['Country'] != "N/A":
											rescountries = res['Country'].split(', ')
											for country in rescountries:
												countries = countries + country + ' | '
											countries = countries[:-2].replace('West Germany','DE').replace('East Germany','DE').replace('Germany','DE').replace('France','FR').replace('Canada','CA').replace('Austria','AT').replace('Switzerland','S').replace('Belgium','B').replace('Spain','ESP').replace('Poland','PL').replace('Russia','RU').replace('Czech Republic','CZ').replace('Netherlands','NL').replace('Italy','IT')
										if res['Rated'] != "N/A":
											if "R" in str(res['Rated']):
												fsk = "18"
											elif "TV-MA" in str(res['Rated']):
												fsk = "18"
											elif "TV-PG" in str(res['Rated']):
												fsk = "16"
											elif "TV-14" in str(res['Rated']):
												fsk = "12"
											elif "TV-Y7" in str(res['Rated']):
												fsk = "6"
											elif "PG-13" in str(res['Rated']):
												fsk = "12"
											elif "PG" in str(res['Rated']):
												fsk = "6"
											elif "G" in str(res['Rated']):
												fsk = "16"
										itm = [str(res['Title']), str(countries), str(year), str(genres), str(rating), str(fsk), "omdb", desc]
										resultList.append((itm,))
			except Exception as ex:
				write_log('get_searchResults omdb: ' + str(ex))

			write_log('search results : ' + str(resultList))
			if resultList:
				return(sorted(resultList, key = lambda x: x[0]))
			else:
				itm = ["Keine Ergebnisse gefunden", None, None, None, None, None, None, None]
				resultList.append((itm,))
				return resultList
		except Exception as ex:
			write_log('get_searchResults : ' + str(ex))
			return []

def downloadTVSImage(tvsImage, imgname):
	try:
		if not fileExists(imgname):
			ir = requests.get(tvsImage, stream=True, timeout=4)
			if ir.status_code == 200:
				with open(imgname, 'wb') as f:
					ir.raw.decode_content = True
					shutil.copyfileobj(ir.raw, f)
					f.close()
				ir = None
				return True
			else:
				return False
		else:
			return False
	except Exception as ex:
		write_log("Fehler beim laden des Previewbildes von TVS: " + str(ex))
		return False

def downloadTVMovieImage(tvMovieImage, imgname):
	try:
		if not fileExists(imgname):
			imgurl = 'http://images.tvmovie.de/' + str(coverqualityDict[coverquality.value]) + '/Center/' + tvMovieImage
			ir = requests.get(imgurl, stream=True, timeout=4)
			if ir.status_code == 200:
				with open(imgname, 'wb') as f:
					ir.raw.decode_content = True
					shutil.copyfileobj(ir.raw, f)
					f.close()
				ir = None
				return True
			else:
				return False
		else:
			return True
	except Exception as ex:
		write_log("Fehler beim laden des Previewbildes : " + str(ex))
		return False

def getImageFile(path, eventName):
	name = eventName
	pictureName = convert2base64(name) + '.jpg'
	imageFileName = os.path.join(path, pictureName)
	if (os.path.exists(imageFileName)):
		return imageFileName
	else:
		name = convertTitle(eventName)
		pictureName = convert2base64(name) + '.jpg'
		imageFileName = os.path.join(path, pictureName)
		if (os.path.exists(imageFileName)):
			return imageFileName
		else:
			name = convertTitle2(eventName)
			pictureName = convert2base64(name) + '.jpg'
			imageFileName = os.path.join(path, pictureName)
			if (os.path.exists(imageFileName)):
				return imageFileName
	if 'cover' in path and previewImages:
		ppath = path.replace('cover', 'preview')
		imageFileName = getPreviewImageFile(ppath, eventName)
		if imageFileName:
			return imageFileName
	return None

def getPreviewImageFile(path, eventName):
	name = eventName
	pictureName = convert2base64(name) + '.jpg'
	imageFileName = os.path.join(path, pictureName)
	if (os.path.exists(imageFileName)):
		return imageFileName
	else:
		name = convertTitle(eventName)
		pictureName = convert2base64(name) + '.jpg'
		imageFileName = os.path.join(path, pictureName)
		if (os.path.exists(imageFileName)):
			return imageFileName
		else:
			name = convertTitle2(eventName)
			pictureName = convert2base64(name) + '.jpg'
			imageFileName = os.path.join(path, pictureName)
			if (os.path.exists(imageFileName)):
				return imageFileName
	return None

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
		self.conn = sqlite3.connect(db_file,check_same_thread=False)
		self.create_DB()

	def create_DB(self):
		try:
			cur = self.conn.cursor()
			# create table eventInfo
			query = "SELECT name FROM sqlite_master WHERE type='table' AND name='eventInfo';"
			cur.execute(query)
			if not cur.fetchall():
				query = "CREATE TABLE [eventInfo] ([base64title] TEXT NOT NULL,[title] TEXT NOT NULL,[genre] TEXT NULL,[year] TEXT NULL,[rating] TEXT NULL,[fsk] TEXT NULL,[country] TEXT NULL,[gDate] TEXT NOT NULL,[trailer] TEXT DEFAULT NULL,PRIMARY KEY ([base64title]))"
				cur.execute(query)
				self.conn.commit()
				write_log("Tabelle 'eventInfo' hinzugef�gt")

			# create table blackList
			query = "SELECT name FROM sqlite_master WHERE type='table' AND name='blackList';"
			cur.execute(query)
			if not cur.fetchall():
				query = "CREATE TABLE [blackList] ([base64title] TEXT NOT NULL,PRIMARY KEY ([base64title]))"
				cur.execute(query)
				self.conn.commit()
				write_log("Tabelle 'blackList' hinzugef�gt")

			# create table blackListCover
			query = "SELECT name FROM sqlite_master WHERE type='table' AND name='blackListCover';"
			cur.execute(query)
			if not cur.fetchall():
				query = "CREATE TABLE [blackListCover] ([base64title] TEXT NOT NULL,PRIMARY KEY ([base64title]))"
				cur.execute(query)
				self.conn.commit()
				write_log("Tabelle 'blackListCover' hinzugef�gt")

			# create table blackListPoster
			query = "SELECT name FROM sqlite_master WHERE type='table' AND name='blackListPoster';"
			cur.execute(query)
			if not cur.fetchall():
				query = "CREATE TABLE [blackListPoster] ([base64title] TEXT NOT NULL,PRIMARY KEY ([base64title]))"
				cur.execute(query)
				self.conn.commit()
				write_log("Tabelle 'blackListPoster' hinzugef�gt")

			# create table liveOnTV
			query = "SELECT name FROM sqlite_master WHERE type='table' AND name='liveOnTV';"
			cur.execute(query)
			if not cur.fetchall():
				query = "CREATE TABLE [liveOnTV] (eid INTEGER NOT NULL, id TEXT,subtitle TEXT,image TEXT,year TEXT,fsk TEXT,rating TEXT,title TEXT,airtime INTEGER NOT NULL,leadText TEXT,conclusion TEXT,categoryName TEXT,season TEXT,episode TEXT,genre TEXT,country TEXT,imdb TEXT,sref TEXT NOT NULL, PRIMARY KEY ([eid],[airtime],[sref]))"
				cur.execute(query)
				self.conn.commit()
				write_log("Tabelle 'liveOnTV' hinzugef�gt")

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
				write_log("Tabelle 'imageBlackList' hinzugef�gt")

			query = "SELECT name FROM sqlite_master WHERE type='table' AND name='parameters';"
			cur.execute(query)
			if not cur.fetchall():
				query = "CREATE TABLE `parameters` ( `name` TEXT NOT NULL UNIQUE, `value` TEXT, PRIMARY KEY(`name`) )"
				cur.execute(query)
				self.conn.commit()
				write_log("Tabelle 'parameters' hinzugef�gt")

			#append columns eventInfo
			query = "PRAGMA table_info('eventInfo');"
			cur.execute(query)
			rows = cur.fetchall()
			found = False
			for row in rows:
				if "trailer" in row[1]:
					found = True
					break
			if found == False:
				query ="ALTER TABLE 'eventInfo' ADD COLUMN `trailer` TEXT DEFAULT NULL"
				cur.execute(query)
				self.conn.commit()

		except Error as ex:
			write_log("Fehler in DB Create: " + str(ex))

	def releaseDB(self):
		self.conn.close()

	def execute(self,query,args=()):
		cur = self.conn.cursor()
		cur.execute(query,args)

	def parameter(self,action,name,value=None,default=None):
		cur = self.conn.cursor()
		if action == PARAMETER_GET:
			ret = None
			query = "SELECT value FROM parameters WHERE name = ?"
			cur.execute(query,(name,))
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

		elif action == PARAMETER_SET:
			if value or value == False:
				if value == False:
					val = "False"
				elif value == True:
					val = "True"
				else:
					val = value

				query = "REPLACE INTO parameters (name,value) VALUES (?,?)"
				cur.execute(query,(name,val))
				self.conn.commit()
				return value
			else:
				return None
		else:
			return None

	def addTitleInfo(self, base64title,title,genre,year,rating,fsk,country,trailer=None):
		try:
			now = str(time())
			cur = self.conn.cursor()
			query = "insert or ignore into eventInfo (base64title,title,genre,year,rating,fsk,country,gDate,trailer) values (?,?,?,?,?,?,?,?,?);"
			cur.execute(query,(base64title, str(title).decode('utf8'), str(genre).decode('utf8'), year, rating, fsk, str(country).decode('utf8'),now,trailer))
			self.conn.commit()
		except Error as ex:
			write_log("Fehler in addTitleInfo : " + str(ex))

	def addliveTV(self, records):
		try:
			cur = self.conn.cursor()
			cur.executemany('insert or ignore into liveOnTV values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);',records)
			write_log("have inserted " + str(cur.rowcount) + " events into database")
			self.conn.commit()
			#======= entfernt (#4) nun ueber updateConut ========
			#self.parameter(PARAMETER_SET, 'lastadditionalDataCount', str(cur.rowcount))
			# ===================================================== 
		except Error as ex:
			write_log("Fehler in addliveTV : " + str(ex))

	def updateTitleInfo(self, title, genre,year,rating,fsk,country,base64title):
		try:
			now = str(time())
			cur = self.conn.cursor()
			query = "update eventInfo set title = ?, genre = ?, year = ?, rating = ?, fsk = ?, country = ?, gDate = "+now+" where base64title = ?;"
			cur.execute(query,(str(title).decode('utf8'), str(genre).decode('utf8'), year, rating, fsk, str(country).decode('utf8'), base64title))
			self.conn.commit()
		except Error as ex:
			write_log("Fehler in updateTitleInfo : " + str(ex))

	def updateSingleEventInfo(self, col, val,base64title):
		try:
			cur = self.conn.cursor()
			query = "update eventInfo set " + str(col) + "= ? where base64title = ?;"
			cur.execute(query,(str(val).decode('utf8'), base64title))
			self.conn.commit()
		except Error as ex:
			write_log("Fehler in updateSingleEventInfo : " + str(ex))

	def updateTrailer(self, trailer,base64title):
		try:
			cur = self.conn.cursor()
			query = "update eventInfo set trailer = ? where base64title = ?;"
			cur.execute(query,(str(trailer).decode('utf8'), base64title))
			self.conn.commit()
		except Error as ex:
			write_log("Fehler in updateTrailer : " + str(ex))

	def updateliveTVInfo(self, image,genre,year,rating,fsk,country,eid):
		try:
			cur = self.conn.cursor()
			query = "update liveOnTV set image = ?, genre = ?, year = ?, rating = ?, fsk = ?, country = ? where eid = ?;"
			cur.execute(query,(str(image).decode('utf8'), str(genre).decode('utf8'), year, rating, fsk, str(country).decode('utf8'), eid))
			self.conn.commit()
		except Error as ex:
			write_log("Fehler in updateliveTVInfo : " + str(ex))

	def updateliveTV(self, id,subtitle,image,year,fsk,rating,leadText,conclusion,categoryName,season,episode,genre,country, imdb, title, airtime):
		try:
			low = airtime - 360
			high = airtime + 360
			cur = self.conn.cursor()
			query = "update liveOnTV set id = ?, subtitle = ?, image = ?, year = ?, fsk = ?, rating = ?, leadText = ?, conclusion = ?, categoryName = ?, season = ?, episode = ?, genre = ?, country = ?, imdb = ? where title = ? AND airtime BETWEEN ? AND ? AND id = 'in progress';"
			cur.execute(query,(id, str(subtitle).decode('utf8'), image.decode('utf8'), year, fsk, rating, str(leadText).decode('utf8'), str(conclusion).decode('utf8'), str(categoryName).decode('utf8'), season, episode, str(genre).decode('utf8'), country, imdb, str(title).decode('utf8'), low, high))
			self.conn.commit()
		except Error as ex:
			write_log("Fehler in updateliveTV : " + str(ex))

	#=========== geandert (#4) ======================
	'''
	def updateliveTVS(self, id,subtitle,image,year,fsk,rating,leadText,conclusion,categoryName,season,episode,genre,country, imdb, sref, airtime):
		try:
			low = airtime - 150
			high = airtime + 150
			cur = self.conn.cursor()
			query = "update liveOnTV set id = ?, subtitle = ?, image = ?, year = ?, fsk = ?, rating = ?, leadText = ?, conclusion = ?, categoryName = ?, season = ?, episode = ?, genre = ?, country = ?, imdb = ? where sref = ? AND airtime BETWEEN ? AND ? AND id = 'in progress';"
			cur.execute(query,(id, str(subtitle).decode('utf8'), str(image).decode('utf8'), year, fsk, rating, str(leadText).decode('utf8'), str(conclusion).decode('utf8'), str(categoryName).decode('utf8'), season, episode, str(genre).decode('utf8'), country, str(imdb).decode('utf8'), str(sref).decode('utf8'), low, high))
			self.conn.commit()
		except Error as ex:
			write_log("Fehler in updateliveTVS : " + str(ex))
	'''		
	def updateliveTVS(self, id,subtitle,image,year,fsk,rating,leadText,conclusion,categoryName,season,episode,genre,country, imdb, sref, airtime,title):
		try:
			updatetRows = 0
			low = airtime - 150
			high = airtime + 150
			cur = self.conn.cursor()
			query = "update liveOnTV set id = ?, subtitle = ?, image = ?, year = ?, fsk = ?, rating = ?, leadText = ?, conclusion = ?, categoryName = ?, season = ?, episode = ?, genre = ?, country = ?, imdb = ? where sref = ? AND airtime BETWEEN ? AND ? AND id = 'in progress';"
			cur.execute(query,(id, str(subtitle).decode('utf8'), str(image).decode('utf8'), year, fsk, rating, str(leadText).decode('utf8'), str(conclusion).decode('utf8'), str(categoryName).decode('utf8'), season, episode, str(genre).decode('utf8'), country, str(imdb).decode('utf8'), str(sref).decode('utf8'), low, high))
			updatetRows = cur.rowcount
			self.conn.commit()
			
			if updatetRows < 1:
				#Suche mit titel
				low = airtime - 2700
				high = airtime + 2700
				query = "SELECT sref, airtime FROM liveOnTV WHERE title = ? AND sref = ? AND airtime BETWEEN ? AND ? AND id = 'in progress' ORDER BY airtime ASC LIMIT 1;"
				cur.execute(query,(str(title).decode('utf8'),str(sref).decode('utf8'),low,high))
				row = cur.fetchone()
				if row:
					query = "UPDATE liveOnTV set id = ?, subtitle = ?, image = ?, year = ?, fsk = ?, rating = ?, leadText = ?, conclusion = ?, categoryName = ?, season = ?, episode = ?, genre = ?, country = ?, imdb = ? where sref = ? AND airtime = ? AND  id = 'in progress';"
					cur.execute(query,(id, str(subtitle).decode('utf8'), str(image).decode('utf8'), year, fsk, rating, str(leadText).decode('utf8'), str(conclusion).decode('utf8'), str(categoryName).decode('utf8'), season, episode, str(genre).decode('utf8'), country, str(imdb).decode('utf8'), str(row[0]).decode('utf8'), row[1]))
					self.conn.commit()
			
		except Error as ex:
			write_log("Fehler in updateliveTVS : " + str(ex))
	# ==============================================================

	def updateliveTVProgress(self):
		try:
			cur = self.conn.cursor()
			query = "update liveOnTV set id = '' where id = 'in progress';"
			cur.execute(query)
			write_log("nothing found for " + str(cur.rowcount) + " events in liveOnTV")
			self.conn.commit()
			self.parameter(PARAMETER_SET, 'lastadditionalDataCountSuccess', str(cur.rowcount))
		except Error as ex:
			write_log("Fehler in updateliveTVProgress : " + str(ex))

	def getTitleInfo(self, base64title):
		try:
			cur = self.conn.cursor()
			query = "SELECT base64title,title,genre,year,rating,fsk,country, trailer FROM eventInfo WHERE base64title = ?"
			cur.execute(query,(str(base64title),))
			row = cur.fetchall()
			if row:
				return [row[0][0],row[0][1].decode('utf8'),row[0][2].decode('utf8'),row[0][3],row[0][4],row[0][5],row[0][6].decode('utf8'),str(row[0][7]).decode('utf8')]
			else:
				return []
		except Error as ex:
			write_log("Fehler in getTitleInfo : " + str(ex) + ' - ' + str(base64title))
			return []
			
	def getliveTV(self, eid, name=None, beginTime=None):
		try:
			cur = self.conn.cursor()
			if name:
				tvname = name.decode('utf8')
				tvname = re.sub('\\(.*?\\)', '', tvname).strip()
				tvname = re.sub(' +', ' ', tvname)
				query = "SELECT * FROM liveOnTV WHERE eid = ? AND title = ?"
				cur.execute(query,(eid, tvname))
			else:
				query = "SELECT * FROM liveOnTV WHERE eid = ?"
				cur.execute(query,(eid,))
			row = cur.fetchall()
			if row:
				if row[0][1] != "":
					return [row[0]]
				else:
					if name and beginTime:
						query = "SELECT * FROM liveOnTV WHERE airtime = ? AND title = ?"
						cur.execute(query,(str(beginTime), tvname))
						row = cur.fetchall()
						if row:
							return [row[0]]
						else:
							return []
			else:
				return []
		except Error as ex:
			write_log("Fehler in getliveTV : " + str(ex) + ' - ' + str(eid) + ' : ' + str(name))
			return []

	def getSrefsforUpdate(self):
		try:
			now = str(int(time()-7200))
			refList = []
			cur = self.conn.cursor()
			query = "SELECT DISTINCT sref FROM liveOnTV WHERE id = 'in progress' and airtime > " + now
			cur.execute(query)
			rows = cur.fetchall()
			if rows:
				for row in rows:
					refList.append(row[0])
			return refList
		except Error as ex:
			write_log("Fehler in getSrefsforUpdate : " + str(ex))
			return []

	def getMissingPictures(self):
		try:
			coverList = []
			posterList = []
			cur = self.conn.cursor()
			query = "SELECT DISTINCT title FROM liveOnTV WHERE categoryName = 'Spielfilm' or categoryName = 'Serie' ORDER BY title"
			cur.execute(query)
			rows = cur.fetchall()
			if rows:
				for row in rows:
					if getImageFile(getPictureDir() + 'cover/', row[0]) is None:
						coverList.append(row[0])
					if getImageFile(getPictureDir() + 'poster/', row[0]) is None:
						posterList.append(row[0])
			return [coverList, posterList]
		except Error as ex:
			write_log("Fehler in getMissingPictures : " + str(ex))
			return [None,None]

	def getMinAirtimeforUpdate(self, sref):
		try:
			cur = self.conn.cursor()
			#===== geaendert (#4) =======
			#query = "SELECT Min(airtime) FROM liveOnTV WHERE id = 'in progress' and sref = ?"
			now = str(int(time()-7200))
			query = "SELECT Min(airtime) FROM liveOnTV WHERE id = 'in progress' and sref = ? and airtime > " + now
			# ================================
			cur.execute(query,(str(sref),))
			row = cur.fetchall()
			if row:
				return row[0][0]
			else:
				return 4000000000
		except Error as ex:
			write_log("Fehler in getMinAirtimeforUpdate : " + str(ex))
			return 4000000000

	def getMaxAirtimeforUpdate(self, sref):
		try:
			cur = self.conn.cursor()
			#===== geaendert (#4) =======
			#query = "SELECT Max(airtime) FROM liveOnTV WHERE id = 'in progress' and sref = ?"
			now = str(int(time()-7200))
			query = "SELECT Max(airtime) FROM liveOnTV WHERE id = 'in progress' and sref = ? and airtime > " + now
			# ============================
			cur.execute(query,(str(sref),))
			row = cur.fetchall()
			if row:
				return row[0][0]
			else:
				return 1000000000
		except Error as ex:
			write_log("Fehler in getMaxAirtimeforUpdate : " + str(ex))
			return 1000000000

	def getUpdateCount(self):
		try:
			cur = self.conn.cursor()
			#===== geaendert (#4) =======
			#query = "SELECT COUNT(title) FROM liveOnTV WHERE id = 'in progress'"
			now = str(int(time()-7200))
			query = "SELECT COUNT(title) FROM liveOnTV WHERE id = 'in progress' and airtime > " + now
			# ============================
			cur.execute(query)
			row = cur.fetchall()
			if row:
				return row[0][0]
			else:
				return 0
		except Error as ex:
			write_log("Fehler in getUpdateCount : " + str(ex))
			return 0

	def getTrailerCount(self):
		try:
			trailercount = set()
			cur = self.conn.cursor()
			query = "SELECT DISTINCT imdb FROM liveOnTV WHERE imdb <> ''"
			cur.execute(query)
			rows = cur.fetchall()
			if rows:
				for row in rows:
					trailercount.add(row[0])
			write_log("found " + str(len(trailercount)) + ' on liveTV')
			i = len(trailercount)
			query = "SELECT DISTINCT trailer FROM eventInfo WHERE trailer <> ''"
			cur.execute(query)
			rows = cur.fetchall()
			if rows:
				for row in rows:
					trailercount.add(row[0])
			eI = len(trailercount) - i
			write_log("found " + str(eI) + ' on eventInfo')
			return len(trailercount)
		except Error as ex:
			write_log("Fehler in getUpdateCount : " + str(ex))
			return 0

	def getEventCount(self, sref):
		try:
			cur = self.conn.cursor()
			query = "SELECT COUNT(sref) FROM liveOnTV WHERE sref = ?"
			#==== geaendert (#8) ======
			#cur.execute(query,(str(sref),))
			cur.execute(query,(str(sref).decode('utf-8','ignore'),))
			# =========================
			row = cur.fetchall()
			if row:
				return row[0][0]
			else:
				return 0
		except Error as ex:
			write_log("Fehler in getEventCount : " + str(ex))
			return 0

	def getTitlesforUpdate(self):
		try:
			now = str(int(time()-7200))
			titleList = []
			cur = self.conn.cursor()
			query = "SELECT DISTINCT title FROM liveOnTV WHERE id = 'in progress' and airtime > " + now
			cur.execute(query)
			rows = cur.fetchall()
			if rows:
				for row in rows:
					itm = [row[0].decode('utf8')]
					titleList.append(itm)
			return titleList
		except Error as ex:
			write_log("Fehler in getTitlesforUpdate : " + str(ex))
			return []

	def getTitlesforUpdate2(self):
		try:
			now = str(int(time()-7200))
			titleList = []
			cur = self.conn.cursor()
			query = "SELECT DISTINCT title FROM liveOnTV WHERE id = 'in progress' and (title like '% - %' or title like '%: %') and airtime > " + now
			cur.execute(query)
			rows = cur.fetchall()
			if rows:
				for row in rows:
					itm = [row[0].decode('utf8')]
					titleList.append(itm)
			return titleList
		except Error as ex:
			write_log("Fehler in getTitlesforUpdate2 : " + str(ex))
			return []

	def getUnusedTitles(self):
		try:
			cur = self.conn.cursor()
			titleList = []
			cur = self.conn.cursor()
			query = "SELECT base64title, title FROM eventInfo ORDER BY gDate ASC LIMIT 100;"
			cur.execute(query)
			rows = cur.fetchall()
			if rows:
				for row in rows:
					itm = [row[0],row[1]]
					titleList.append(itm)
			return titleList
		except Error as ex:
			write_log("Fehler in getUnusedTitles : " + str(ex))
			return []

	def checkTitle(self, base64title):
		try:
			cur = self.conn.cursor()
			query = "SELECT base64title FROM eventInfo where base64title = ?;"
			cur.execute(query,(str(base64title),))
			rows = cur.fetchall()
			if rows:
				return True
			else:
				return False
		except Error as ex:
			write_log("Fehler in checkTitle: " + str(ex))
			return False
			
	
	def checkliveTV(self, eid, ref):
		try:
			cur = self.conn.cursor()
			query = "SELECT eid FROM liveOnTV where eid = ? AND sref = ?;"
			cur.execute(query,(eid,ref))
			rows = cur.fetchall()
			if rows:
				return True
			else:
				return False
		except Error as ex:
			write_log("Fehler in checkliveTV: " + str(ex))
			return False

	def cleanDB(self, base64title):
		try:
			cur = self.conn.cursor()
			query = "delete from eventInfo where base64title = ?;"
			cur.execute(query,(str(base64title),))
			self.conn.commit()
			query = "delete from blackList where base64title = ?;"
			cur.execute(query,(str(base64title),))
			self.conn.commit()
		except Error as ex:
			write_log("Fehler in cleanDB : " + str(ex))

	def cleanliveTV(self, airtime):
		try:
			cur = self.conn.cursor()
			query = "delete from liveOnTV where airtime < ?;"
			cur.execute(query,(str(airtime),))
			write_log("have removed " + str(cur.rowcount) + " events from liveOnTV")
			self.conn.commit()
			self.vacuumDB()
		except Error as ex:
			write_log("Fehler in cleanliveTV : " + str(ex))

	def cleanliveTVEntry(self, eid):
		try:
			cur = self.conn.cursor()
			query = "delete from liveOnTV where eid = ?;"
			cur.execute(query,(str(eid),))
			self.conn.commit()
		except Error as ex:
			write_log("Fehler in cleanliveTVEntry : " + str(ex))

	def getUnusedPreviewImages(self, airtime):
		try:
			cur = self.conn.cursor()
			titleList = []
			duplicates = []
			delList = []
			cur = self.conn.cursor()
			query = 'SELECT DISTINCT image from liveOnTV where airtime > ? AND image <> "";'
			cur.execute(query,(str(airtime),))
			rows = cur.fetchall()
			if rows:
				for row in rows:
					duplicates.append(row[0])
			query = 'SELECT DISTINCT image from liveOnTV where airtime < ? AND image <> "";'
			cur.execute(query,(str(airtime),))
			rows = cur.fetchall()
			write_log("found old preview images " + str(len(rows)))
			if rows:
				for row in rows:
					titleList.append(row[0])
			delList = [x for x in titleList if x not in duplicates]
			write_log("not used preview images " + str(len(delList)))
			del duplicates
			del titleList
			return delList
		except Error as ex:
			write_log("Fehler in getUnusedPreviewImages : " + str(ex))
			return []

	def cleanblackList(self):
		try:
			cur = self.conn.cursor()
			query = "delete from blackList;"
			cur.execute(query)
			self.conn.commit()
			query = "delete from imageBlackList;"
			cur.execute(query)
			self.conn.commit()
			self.vacuumDB()
		except Error as ex:
			write_log("Fehler in cleanblackList : " + str(ex))


	def cleanNadd2BlackList(self, base64title):
		try:
			cur = self.conn.cursor()
			query = "delete from eventInfo where base64title = ?;"
			cur.execute(query,(str(base64title),))
			self.conn.commit()
			query = "insert or ignore into blackList (base64title) values (?);"
			cur.execute(query,(str(base64title),))
			self.conn.commit()
		except Error as ex:
			write_log("Fehler in cleanNadd2BlackList : " + str(ex))

	def addblackList(self, base64title):
		try:
			cur = self.conn.cursor()
			query = "insert or ignore into blackList (base64title) values (?);"
			cur.execute(query,(str(base64title),))
			self.conn.commit()
		except Error as ex:
			write_log("Fehler in addblackList : " + str(ex))

	def addblackListCover(self, base64title):
		try:
			cur = self.conn.cursor()
			query = "insert or ignore into blackListCover (base64title) values (?);"
			cur.execute(query,(str(base64title),))
			self.conn.commit()
		except Error as ex:
			write_log("Fehler in addblackListCover : " + str(ex))

	def addblackListPoster(self, base64title):
		try:
			cur = self.conn.cursor()
			query = "insert or ignore into blackListPoster (base64title) values (?);"
			cur.execute(query,(str(base64title),))
			self.conn.commit()
		except Error as ex:
			write_log("Fehler in addblackListPoster : " + str(ex))

	def addimageBlackList(self, name):
		try:
			cur = self.conn.cursor()
			query = "insert or ignore into imageBlackList (name) values (?);"
			cur.execute(query,(name,))
			self.conn.commit()
		except Error as ex:
			write_log("Fehler in addimageBlackList : " + str(ex))


	def getimageBlackList(self, name):
		try:
			cur = self.conn.cursor()
			query = "SELECT name FROM imageBlackList WHERE name = ?"
			cur.execute(query,(name,))
			row = cur.fetchall()
			if row:
				return True
			else:
				return False
		except Error as ex:
			write_log("Fehler in getimageBlackList : " + str(ex))
			return False

	def getblackList(self, base64title):
		try:
			cur = self.conn.cursor()
			query = "SELECT base64title FROM blackList WHERE base64title = ?"
			cur.execute(query,(str(base64title),))
			row = cur.fetchall()
			if row:
				return True
			else:
				return False
		except Error as ex:
			write_log("Fehler in getblackList : " + str(ex))
			return False

	def getblackListCover(self, base64title):
		try:
			cur = self.conn.cursor()
			query = "SELECT base64title FROM blackListCover WHERE base64title = ?"
			cur.execute(query,(str(base64title),))
			row = cur.fetchall()
			if row:
				return True
			else:
				return False
		except Error as ex:
			write_log("Fehler in getblackListCover : " + str(ex))
			return False

	def getblackListPoster(self, base64title):
		try:
			cur = self.conn.cursor()
			query = "SELECT base64title FROM blackListPoster WHERE base64title = ?"
			cur.execute(query,(str(base64title),))
			row = cur.fetchall()
			if row:
				return True
			else:
				return False
		except Error as ex:
			write_log("Fehler in getblackListPoster : " + str(ex))
			return False

	def getblackListCount(self):
		try:
			cur = self.conn.cursor()
			query = "SELECT COUNT(base64title) FROM blackList"
			cur.execute(query)
			row = cur.fetchall()
			if row:
				return row[0][0]
			else:
				return 0
		except Error as ex:
			write_log("Fehler in getblackListCount : " + str(ex))
			return 0

	def getTitleInfoCount(self):
		try:
			cur = self.conn.cursor()
			query = "SELECT COUNT(base64title) FROM eventInfo"
			cur.execute(query)
			row = cur.fetchall()
			if row:
				return row[0][0]
			else:
				return 0
		except Error as ex:
			write_log("Fehler in getTitleInfoCount : " + str(ex))
			return 0

	def getliveTVCount(self):
		try:
			cur = self.conn.cursor()
			query = "SELECT COUNT(eid) FROM liveOnTV"
			cur.execute(query)
			row = cur.fetchall()
			if row:
				return row[0][0]
			else:
				return 0
		except Error as ex:
			write_log("Fehler in getliveTVCount : " + str(ex))
			return 0

	def getliveTVidCount(self):
		try:
			cur = self.conn.cursor()
			query = "SELECT COUNT(id) FROM liveOnTV WHERE id <> '' AND id <> 'in progress'"
			cur.execute(query)
			row = cur.fetchall()
			if row:
				return row[0][0]
			else:
				return 0
		except Error as ex:
			write_log("Fehler in getliveTVidCount : " + str(ex))
			return 0

	def getMaxAirtime(self, title):
		try:
			cur = self.conn.cursor()
			#========== geaendert (#8) =============
			#query = "SELECT Max(airtime) FROM liveOnTV WHERE title = ?"
			query = "SELECT Max(airtime),sRef FROM liveOnTV WHERE title = ?"
			# =======================================
			cur.execute(query,(str(title).decode('utf8'),))
			row = cur.fetchall()
			if row:
				#========== geaendert (#8) =============
				#return row[0][0]
				if "http" in row[0][1]:
					return 4000000000
				else:
					return row[0][0]
				# ===================================
				return row[0][0]
			else:
				return 4000000000
		except Error as ex:
			write_log("Fehler in getMaxAirtime : " + str(ex))
			return 4000000000

	def getSeriesStarts(self):
		try:
			now = time()
			titleList = []
			cur = self.conn.cursor()
			if str(seriesStartType.value) == 'Staffelstart':
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
		except Error as ex:
			write_log("Fehler in getSeriesStarts : " + str(ex))
			return []

	def getSeriesStartsCategories(self):
		try:
			now = time()
			titleList = []
			cur = self.conn.cursor()
			if str(seriesStartType.value) == 'Staffelstart':
				query = "SELECT Distinct categoryName from liveOnTV where airtime > " + str(now) + " AND sref <> '' and episode = '1'"
			else:
				query = "SELECT Distinct categoryName from liveOnTV where airtime > " + str(now) + " AND sref <> '' and season = '1' and episode = '1'"
			cur.execute(query)
			rows = cur.fetchall()
			if rows:
				for row in rows:
					itm = [row[0].decode('utf8')]
					titleList.append(itm)
			return titleList
		except Error as ex:
			write_log("Fehler in getSeriesStartsCategories : " + str(ex))
			return []

	def getFavourites(self, what="genre LIKE 'Krimi'", duration = 86400):
		try:
			start = time()
			end = time() + duration
			titleList = []
			cur = self.conn.cursor()
			query = "SELECT eid, sref from liveOnTV where airtime BETWEEN " + str(start) + " AND " +  str(end) + " AND " + str(what)
			cur.execute(query)
			rows = cur.fetchall()
			if rows:
				for row in rows:
					titleList.append(row)
			return titleList
		except Error as ex:
			write_log("Fehler in getFavourites : " + str(ex))
			return []

	def getGenres(self):
		try:
			titleList = []
			cur = self.conn.cursor()
			query = "SELECT Distinct genre from liveOnTV WHERE genre <> '' ORDER BY genre"
			cur.execute(query)
			rows = cur.fetchall()
			if rows:
				for row in rows:
					titleList.append(row[0].decode('utf8'))
			return titleList
		except Error as ex:
			write_log("Fehler in getGenres : " + str(ex))
			return []

	def vacuumDB(self):
		cur = self.conn.cursor()
		cur.execute("VACUUM")
		self.conn.commit()

########################################### Download Helper Class #######################################################
class HTTPProgressDownloader(client.HTTPDownloader):
	def __init__(self, url, outfile, headers=None):
		client.HTTPDownloader.__init__(self, url, outfile, headers=headers, agent="AEL-Image-Server Downloader")
		self.status = None
		self.progress_callback = None
		self.deferred = defer.Deferred()

	def noPage(self, reason):
		if self.status == "304":
			client.HTTPDownloader.page(self, "")
		else:
			client.HTTPDownloader.noPage(self, reason)

	def gotHeaders(self, headers):
		if self.status == "200":
			if headers.has_key("content-length"):
				self.totalbytes = int(headers["content-length"][0])
			else:
				self.totalbytes = 0
			self.currentbytes = 0.0
		return client.HTTPDownloader.gotHeaders(self, headers)

	def pagePart(self, packet):
		if self.status == "200":
			self.currentbytes += len(packet)
		if self.progress_callback:
			self.progress_callback(self.currentbytes, self.totalbytes)
		return client.HTTPDownloader.pagePart(self, packet)

	def pageEnd(self):
		return client.HTTPDownloader.pageEnd(self)

import urlparse
def url_parse(url, defaultPort=None):
	parsed = urlparse.urlparse(url)
	scheme = parsed[0]
	path = urlparse.urlunparse(('', '') + parsed[2:])
	if defaultPort is None:
		if scheme == 'https':
			defaultPort = 443
		else:
			defaultPort = 80
	host, port = parsed[1], defaultPort
	if ':' in host:
		host, port = host.split(':')
		port = int(port)
	return scheme, host, port, path

class downloadWithProgress:
	def __init__(self, url, outputfile, contextFactory=None, *args, **kwargs):
		scheme, host, port, path = url_parse(url)
		self.factory = HTTPProgressDownloader(url, outputfile, *args, **kwargs)
		if scheme == 'https':
			if contextFactory is None:
				class TLSSNIContextFactory(ssl.ClientContextFactory): 
					def getContext(self, hostname=None, port=None): 
						ctx = ssl.ClientContextFactory.getContext(self) 
						ClientTLSOptions(host, ctx) 
						return ctx
				contextFactory = TLSSNIContextFactory()
				self.connection = reactor.connectSSL(host, port, self.factory, contextFactory)
		else:
			self.connection = reactor.connectTCP(host, port, self.factory)

	def start(self):
		return self.factory.deferred

	def stop(self):
		if hasattr(self, "connection") and self.connection:
			self.connection.disconnect()

	def addProgress(self, progress_callback):
		self.factory.progress_callback = progress_callback

class BingImageSearch:
	def __init__(self, query, limit, what = 'Cover'):
		self.download_count = 0
		self.query = query
		if what == 'Cover':
			self.filters = '+filterui:photo-photo+filterui:aspect-wide&form=IRFLTR'
		else:
			self.filters = '+filterui:photo-photo+filterui:aspect-tall&form=IRFLTR'

		self.limit = limit

		self.headers = {'User-Agent': 'Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'}
		self.page_counter = 0

	def search(self):
		resultList = []
		try:
			while self.download_count < self.limit:
				request_url = 'https://www.bing.com/images/async?q=' + urllib2.quote(self.query) \
							  + '&first=' + str(self.page_counter) + '&count=' + str(self.limit) \
							  + '&adlt=off' + '&qft=' + self.filters
				write_log('Bing-requests ' + str(request_url))
				html = requests.get(request_url, timeout=5, headers=self.headers).content
				links = re.findall('murl&quot;:&quot;(.*?)&quot;', html)
				write_log('Bing-result ' + str(links))
				if len(links) <= self.limit:
					self.limit = len(links) - 1

				for link in links:
					if link.endswith('.jpg'):
						if self.download_count < self.limit:
							resultList.append(link)
							self.download_count += 1
						else:
							break
				self.page_counter += 1
			return resultList
		except:
			return resultList

#https://live.tvspielfilm.de/static/broadcast/list/ARD/2020-06-11
#https://live.tvspielfilm.de/static/content/channel-list/livetv