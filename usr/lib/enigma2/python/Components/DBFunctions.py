from os.path import exists, join
from datetime import datetime
from sqlite3 import connect
from urllib.parse import urlparse, urlunparse

from Components.AELGlobals import aelGlobals
writeLog = print


class DB_Functions():
	PARAMETER_SET = 0
	PARAMETER_GET = 1

	@staticmethod
	def dict_factory(cursor, row):
		d = {}
		for idx, col in enumerate(cursor.description):
			d[col[0]] = row[idx]
		return d

	def __init__(self, db_file):
		aelGlobals.createDirs(aelGlobals.HDDPATH)
		self.conn = connect(db_file, check_same_thread=False)
		self.create_DB()

	def create_DB(self):
		cur = self.conn.cursor()
		# create table eventInfo
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='eventInfo';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE [eventInfo] ([creationdate] INTEGER NOT NULL, [title] TEXT NOT NULL, [genre] TEXT NULL, [year] TEXT NULL, [rating] TEXT NULL, [fsk] TEXT NULL, [country] TEXT NULL, [imdbId] TEXT NULL, [coverfile] TEXT NULL, [posterfile] TEXT NULL, [trailer_url] TEXT NULL, PRIMARY KEY ([title]))"
			cur.execute(query)
			self.conn.commit()
			writeLog("Tabelle 'eventInfo' hinzugefügt")
		# create table blackList
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='blackList';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE [blackList] ([title] TEXT NOT NULL,PRIMARY KEY ([title]))"
			cur.execute(query)
			self.conn.commit()
			writeLog("Tabelle 'blackList' hinzugefügt")
		# create table blackListImage
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='blackListImage';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE [blackListImage] ([filename] TEXT NOT NULL,PRIMARY KEY ([filename]))"
			cur.execute(query)
			self.conn.commit()
			writeLog("Tabelle 'blackListImage' hinzugefügt")
		# create table liveOnTV
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='liveOnTV';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE [liveOnTV] (e2eventId INTEGER NOT NULL, providerId TEXT, title TEXT, genre TEXT, year TEXT, rating TEXT, fsk TEXT, country TEXT, airtime INTEGER NOT NULL, imdbId TEXT, trailer_url TEXT, subtitle TEXT, leadText TEXT, conclusion TEXT, categoryName TEXT, season TEXT, episode TEXT, imagefile TEXT, sref TEXT NOT NULL, PRIMARY KEY ([e2eventId], [airtime], [sref]))"
			cur.execute(query)
			self.conn.commit()
			writeLog("Tabelle 'liveOnTV' hinzugefügt")
		# create table parameters
		query = "SELECT name FROM sqlite_master WHERE type='table' AND name='parameters';"
		cur.execute(query)
		if not cur.fetchall():
			query = "CREATE TABLE 'parameters' ( 'name' TEXT NOT NULL UNIQUE, 'value' TEXT, PRIMARY KEY('name') )"
			cur.execute(query)
			self.conn.commit()
			writeLog("Table 'parameters' added")

	def releaseDB(self):
		self.conn.close()

	def execute(self, query, args=()):
		cur = self.conn.cursor()
		cur.execute(query, args)

	def parameter(self, action, name, value=None, default=None):
		cur = self.conn.cursor()
		if action == self.PARAMETER_GET:
			query = "SELECT value FROM parameters WHERE name = ?"
			cur.execute(query, (name,))
			rows = cur.fetchall()
			return {"False": False, "True": True}.get(rows[0][0], rows[0][0]) if rows else default
		elif action == self.PARAMETER_SET and value:
			query = "REPLACE INTO parameters (name,value) VALUES (?,?)"
			cur.execute(query, (name, {False: "False", True: "True"}.get(value, value)))
			self.conn.commit()
			return value

	def addEventInfo(self, title, genre, year, rating, fsk, country, imdbId, coverfile, posterfile, trailer_url):
		creationdate = round(datetime.now().timestamp())
		cur = self.conn.cursor()
		query = "insert or ignore into eventInfo (creationdate, title, genre, year, rating, fsk, country, imdbId, coverfile, posterfile, trailer_url) values (?,?,?,?,?,?,?,?,?,?,?);"
		cur.execute(query, (creationdate, title, genre, year, rating, fsk, country, imdbId, coverfile, posterfile, trailer_url))
		self.conn.commit()

	def updateEventInfo(self, genre, year, rating, fsk, country, imdbId, coverfile, posterfile, trailer_url, title):
		creationdate = round(datetime.now().timestamp())
		cur = self.conn.cursor()
		query = "update eventInfo creationdate = ?, genre = ?, year = ?, rating = ?, fsk = ?, country = ?, imdbId = ?, coverfile= ?, posterfile = ?, trailer_url = ? where title = ?;"
		cur.execute(query, (creationdate, genre, year, rating, fsk, country, imdbId, coverfile, posterfile, trailer_url, title))
		self.conn.commit()

	def updateSingleEventInfo(self, col, val, title):
		cur = self.conn.cursor()
		query = f"update eventInfo set {col}= ? where title = ?;"
		cur.execute(query, (val, title))
		self.conn.commit()

#	def updateTrailer(self, trailer_url, title):  # used by TVS
#		cur = self.conn.cursor()
#		query = "update eventInfo set trailer_url = ? where title = ?;"
#		cur.execute(query, (trailer_url, title))
#		self.conn.commit()

	def getEventInfo(self, title):
		cur = self.conn.cursor()
		query = "SELECT creationdate, genre, year, rating, fsk, country, imdbId, coverfile, posterfile, trailer_url FROM eventInfo WHERE title = ?"
		cur.execute(query, (title,))
		row = cur.fetchall()
		return row[0] if row else []

	def checkEventTitle(self, title):
		cur = self.conn.cursor()
		query = "SELECT title FROM eventInfo where title = ?;"
		cur.execute(query, (title,))
		rows = cur.fetchall()
		return True if rows else False

	def updateliveTVInfo(self, e2eventId, genre, year, rating, fsk, country):
		cur = self.conn.cursor()
		query = "update liveOnTV genre = ?, year = ?, rating = ?, fsk = ?, country = ? where e2eventId = ?;"
		cur.execute(query, (genre, year, rating, fsk, country, e2eventId))
		self.conn.commit()

	def addliveTV(self, records):  # records = (e2eventId, "in progress", tvname, "", "", "", "", "", round(begin), "", "", "", "", "", "", "", "", "", serviceref)
		cur = self.conn.cursor()
		cur.executemany("insert or ignore into liveOnTV values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);", records)
		writeLog(f"have inserted {cur.rowcount} events into database")
		self.conn.commit()
		self.parameter(self.PARAMETER_SET, "lastAdditionalDataCount", str(cur.rowcount))

	def updateliveTV(self, providerId, genre, year, rating, fsk, country, imdbId, trailer_url, subtitle, leadText, conclusion, categoryName, season, episode, imagefile, title, airtime):
		# e2eventId, title, airtime and sref is already available, providerId='in progress' has to be set, search for title and airtime and providerId='in progress'
		low = airtime - 360
		high = airtime + 360
		cur = self.conn.cursor()
		query = "update liveOnTV set providerId = ?, genre = ?, year = ?, rating = ?, fsk = ?, country = ?, imdbId = ?, trailer_url = ?, subtitle = ?, leadText = ?, conclusion = ?, categoryName = ?, season = ?, episode = ?, imagefile = ? where title = ? AND airtime BETWEEN ? AND ? AND providerId = 'in progress';"
		cur.execute(query, (providerId, genre, year, rating, fsk, country, imdbId, trailer_url, subtitle, leadText, conclusion, categoryName, season, episode, imagefile, title, low, high))
		self.conn.commit()

	def updateliveTVS(self, providerId, title, genre, year, rating, fsk, country, imdbId, trailer_url, subtitle, leadText, conclusion, categoryName, season, episode, imagefile, sref, airtime):
		# e2eventId, title, airtime and sref is already available, providerId='in progress' has to be set
		updatetRows = 0
		low = airtime - 150
		high = airtime + 150
		cur = self.conn.cursor()
		# search for: sref and airtime and providerId='in progress'
		query = "update liveOnTV set providerId = ?, genre = ?, year = ?, rating = ?, fsk = ?, country = ?, imdbId = ?, trailer_url = ?, subtitle = ?, leadText = ?, conclusion = ?, categoryName = ?, season = ?, episode = ?, imagefile = ? where sref = ? AND airtime BETWEEN ? AND ? AND providerId = 'in progress';"
		cur.execute(query, (providerId, genre, year, rating, fsk, country, imdbId, trailer_url, subtitle, leadText, conclusion, categoryName, season, episode, imagefile, sref, low, high))
		updatetRows = cur.rowcount
		self.conn.commit()
		if updatetRows < 1:  # Suche mit titel
			low = airtime - 2700
			high = airtime + 2700
			query = "SELECT sref, airtime FROM liveOnTV WHERE title = ? AND sref = ? AND airtime BETWEEN ? AND ? AND providerId = 'in progress' ORDER BY airtime ASC LIMIT 1;"
			cur.execute(query, (title, sref, low, high))
			row = cur.fetchone()
			if row:
				# search for: sref and airtime and providerId='in progress'
				query = "UPDATE liveOnTV set providerId = ?, genre = ?, year = ?, rating = ?, fsk = ?, country = ?, imdbId = ?, trailer_url = ?, subtitle = ?, leadText = ?, conclusion = ?, categoryName = ?, season = ?, episode = ?, imagefile = ? where sref = ? AND airtime = ? AND  providerId = 'in progress';"
				cur.execute(query, (providerId, genre, year, rating, fsk, country, imdbId, trailer_url, subtitle, leadText, conclusion, categoryName, season, episode, imagefile, row[0], row[1]))
				self.conn.commit()

	def updateliveTVProgress(self):
		cur = self.conn.cursor()
		query = "update liveOnTV set providerId = '' where providerId = 'in progress';"
		cur.execute(query)
		writeLog(f"nothing found for '{cur.rowcount}' events in liveOnTV")
		self.conn.commit()
		self.parameter(self.PARAMETER_SET, 'lastAdditionalDataCountSuccess', str(cur.rowcount))

	def getTitleInfo(self, base64title):  # TODO: wird wahrscheinlich gar nicht benötigt
		cur = self.conn.cursor()
		query = "SELECT title,title,genre,year,rating,fsk,country, trailer_url FROM eventInfo WHERE title = ?"
		cur.execute(query, (str(base64title),))
		row = cur.fetchall()
		return [row[0][0], row[0][1], row[0][2], row[0][3], row[0][4], row[0][5], row[0][6], str(row[0][7])] if row else []

	def getliveTV(self, e2eventId, name=None, beginTime=None):
		tvname = ""
		cur = self.conn.cursor()
		if name:
			tvname = name
			query = "SELECT * FROM liveOnTV WHERE e2eventId = ? AND title = ?"
			cur.execute(query, (e2eventId, tvname))
		else:
			query = "SELECT * FROM liveOnTV WHERE e2eventId = ?"
			cur.execute(query, (e2eventId,))
		row = cur.fetchall()
		if row:
			if row[0][1]:
				return [row[0]]
			else:
				if name and beginTime:
					query = "SELECT * FROM liveOnTV WHERE airtime = ? AND title = ?"
					cur.execute(query, (beginTime, tvname))
					row = cur.fetchall()
					return [row[0]] if row else []
		return []

	def getSrefsforUpdate(self):
		now = int(datetime.now().timestamp() - 7200)
		refList = []
		cur = self.conn.cursor()
		query = f"SELECT DISTINCT sref FROM liveOnTV WHERE providerId = 'in progress' and airtime > {now}"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				refList.append(row[0])
		return refList

	def getMissingliveTVImages(self):
		coverList = []
		posterList = []
		cur = self.conn.cursor()
		query = "SELECT DISTINCT imagefile FROM liveOnTV WHERE categoryName = 'Spielfilm' or categoryName = 'Serie' ORDER BY imagefile"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				if not exists(join(aelGlobals.COVERPATH, row[0])):
					coverList.append(row[0])
				if not exists(join(aelGlobals.POSTERPATH, row[0])):
					posterList.append(row[0])
		return [coverList, posterList]

	def getMinAirtimeforUpdate(self, sref):
		cur = self.conn.cursor()
		now = int(datetime.now().timestamp() - 7200)
		query = f"SELECT Min(airtime) FROM liveOnTV WHERE providerId = 'in progress' and sref = ? and airtime > {now}"
		cur.execute(query, (sref,))
		row = cur.fetchall()
		return row[0][0] if row else 4000000000

	def getMaxAirtimeforUpdate(self, sref):
		cur = self.conn.cursor()
		now = int(datetime.now().timestamp() - 7200)
		query = f"SELECT Max(airtime) FROM liveOnTV WHERE providerId = 'in progress' and sref = ? and airtime > {now}"
		cur.execute(query, (sref,))
		row = cur.fetchall()
		return row[0][0] if row else 1000000000

	def getUpdateCount(self):
		cur = self.conn.cursor()
		now = int(datetime.now().timestamp() - 7200)
		query = f"SELECT COUNT(title) FROM liveOnTV WHERE providerId = 'in progress' and airtime > {now}"
		cur.execute(query)
		row = cur.fetchall()
		return row[0][0] if row else 0

	def getTrailerCount(self, logging=False):
		livetrailers = set()
		cur = self.conn.cursor()
		query = "SELECT DISTINCT trailer_url FROM liveOnTV WHERE trailer_url <> ''"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				livetrailers.add(row[0])
		livecount = len(list(livetrailers))  # list(set()) removes dupes
		eventtrailers = set()
		query = "SELECT DISTINCT trailer_url FROM eventInfo WHERE trailer_url <> ''"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				eventtrailers.add(row[0])
		eventcount = len(list(eventtrailers))
		totalcount = len(list(livetrailers | eventtrailers))
		if logging:
			writeLog(f"found {livecount} different trailers on liveOnTV")
			writeLog(f"found {eventcount} different trailers on eventInfo")
			writeLog(f"found {totalcount} different trailers on liveOnTV and eventInfo")
		return totalcount

	def getEventCount(self, sref):
		cur = self.conn.cursor()
		query = "SELECT COUNT(sref) FROM liveOnTV WHERE sref = ?"
		cur.execute(query, (sref,))
		row = cur.fetchall()
		return row[0][0] if row else 0

	def getTitlesforUpdate(self):
		now = int(datetime.now().timestamp() - 7200)
		titleList = []
		cur = self.conn.cursor()
		query = f"SELECT DISTINCT title FROM liveOnTV WHERE providerId = 'in progress' and airtime > {now}"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				itm = [row[0]]
				titleList.append(itm)
		return titleList

	def getTitlesforUpdate2(self):
		now = int(datetime.now().timestamp() - 7200)
		titleList = []
		cur = self.conn.cursor()
		query = f"SELECT DISTINCT title FROM liveOnTV WHERE providerId = 'in progress' and (title like '% - %' or title like '%: %') and airtime > {now}"
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
		query = "SELECT title, coverfile, posterfile FROM eventInfo ORDER BY creationdate ASC LIMIT 100;"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				titleList.append((row[0], row[1], row[2]))
		return titleList

	def checkliveTV(self, e2eventId, ref):
		cur = self.conn.cursor()
		query = "SELECT e2eventId FROM liveOnTV where e2eventId = ? AND sref = ?;"
		cur.execute(query, (e2eventId, ref))
		rows = cur.fetchall()
		return True if rows else False

	def cleanDB(self, title):
		cur = self.conn.cursor()
		query = "delete from eventInfo where title = ?;"
		cur.execute(query, (title,))
		self.conn.commit()
		query = "delete from blackList where title = ?;"
		cur.execute(query, (title,))
		self.conn.commit()

	def cleanliveTV(self, airtime):
		cur = self.conn.cursor()
		query = "delete from liveOnTV where airtime < ?;"
		cur.execute(query, (airtime,))
		writeLog(f"have removed {cur.rowcount} events from liveOnTV")
		self.conn.commit()
		self.vacuumDB()

	def cleanliveTVEntry(self, e2eventId):
		cur = self.conn.cursor()
		query = "delete from liveOnTV where e2eventId = ?;"
		cur.execute(query, (e2eventId,))
		self.conn.commit()

	def getUnusedPreviewImages(self, airtime):
		titleList = []
		duplicates = []
		delList = []
		cur = self.conn.cursor()
		query = 'SELECT DISTINCT imagefile from liveOnTV where airtime > ? AND imagefile <> "";'
		cur.execute(query, (airtime,))
		rows = cur.fetchall()
		if rows:
			for row in rows:
				duplicates.append(row[0])
		query = 'SELECT DISTINCT imagefile from liveOnTV where airtime < ? AND imagefile <> "";'
		cur.execute(query, (airtime,))
		rows = cur.fetchall()
		writeLog(f"found old preview images {len(rows)}")
		if rows:
			for row in rows:
				titleList.append(row[0])
		delList = [x for x in titleList if x not in duplicates]
		writeLog(f"not used preview images {len(delList)}")
		del duplicates, titleList
		return delList

	def cleanblackList(self):
		cur = self.conn.cursor()
		query = "delete from blackList;"
		cur.execute(query)
		self.conn.commit()
		query = "delete from blackListImage;"
		cur.execute(query)
		self.conn.commit()
		self.vacuumDB()

	def cleanNadd2BlackList(self, title):
		cur = self.conn.cursor()
		query = "delete from eventInfo where title = ?;"
		cur.execute(query, (title,))
		self.conn.commit()
		query = "insert or ignore into blackList (title) values (?);"
		cur.execute(query, (title,))
		self.conn.commit()

	def addblackListTitle(self, title):  # TODO: macht die Blacklist für Titel überhaupt Sinn bei abschaltbaren Servern?
		cur = self.conn.cursor()
		query = "insert or ignore into blackList (title) values (?);"
		cur.execute(query, (title,))
		self.conn.commit()

	def addblackListImage(self, imgfile):
		imgname = imgfile.split("/")[-1]
		cur = self.conn.cursor()
		query = "insert or ignore into blackListImage (filename) values (?);"
		cur.execute(query, (imgname,))
		self.conn.commit()

	def getblackListTitle(self, title):  # TODO: macht die Blacklist für Titel überhaupt Sinn bei abschaltbaren Servern?
		cur = self.conn.cursor()
		query = "SELECT title FROM blackList WHERE title = ?"
		cur.execute(query, (title,))
		row = cur.fetchall()
		return True if row else False

	def getblackListImage(self, imgfile):
		imgname = imgfile.split("/")[-1]
		cur = self.conn.cursor()
		query = "SELECT filename FROM blackListImage WHERE filename = ?"
		cur.execute(query, (imgname,))
		row = cur.fetchall()
		return True if row else False

	def getblackListCount(self):
		cur = self.conn.cursor()
		query = "SELECT COUNT(title) FROM blackList"
		cur.execute(query)
		row = cur.fetchall()
		return row[0][0] if row else 0

	def getTitleInfoCount(self):
		cur = self.conn.cursor()
		query = "SELECT COUNT(title) FROM eventInfo"
		cur.execute(query)
		row = cur.fetchall()
		return row[0][0] if row else 0

	def getliveTVCount(self):
		cur = self.conn.cursor()
		query = "SELECT COUNT(e2eventId) FROM liveOnTV"
		cur.execute(query)
		row = cur.fetchall()
		return row[0][0] if row else 0

	def getliveTVidCount(self):
		cur = self.conn.cursor()
		query = "SELECT COUNT(providerId) FROM liveOnTV WHERE providerId <> '' AND providerId <> 'in progress'"
		cur.execute(query)
		row = cur.fetchall()
		return row[0][0] if row else 0

	def getMaxAirtime(self, title):
		cur = self.conn.cursor()
		#========== geaendert (#8) =============
		#query = "SELECT Max(airtime) FROM liveOnTV WHERE title = ?"
		query = "SELECT Max(airtime), sRef FROM liveOnTV WHERE title = ?"
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
		now = datetime.now().timestamp()
		titleList = []
		cur = self.conn.cursor()
		if config.plugins.AdvancedEventLibrary.SeriesType.value == 'Staffelstart':
			query = f"SELECT sref, e2eventId, categoryName FROM liveOnTV WHERE sref <> '' AND episode = '1' AND airtime > {now} ORDER BY categoryName, airtime"
		else:
			query = f"SELECT sref, e2eventId, categoryName FROM liveOnTV WHERE sref <> '' AND season = '1' AND episode = '1' AND airtime > {now}  ORDER BY categoryName, airtime"
		cur.execute(query)
		rows = cur.fetchall()
		if rows:
			for row in rows:
				itm = [row[0], row[1], row[2]]
				titleList.append(itm)
		return titleList

	def getSeriesStartsCategories(self):
		now = datetime.now().timestamp()
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
		start = datetime.now().timestamp()
		end = datetime.now().timestamp() + duration
		titleList = []
		cur = self.conn.cursor()
		query = f"SELECT e2eventId, sref from liveOnTV where airtime BETWEEN {start} AND {end} AND {what}"
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

	def url_parse(self, url, defaultPort=None):
		parsed = urlparse(url)
		scheme = parsed[0]
		path = urlunparse(("", "") + parsed[2:])
		if not defaultPort:
			defaultPort = 443 if scheme == "https" else 80
		host, port = parsed[1], defaultPort
		if ":" in host:
			host, port = host.split(":")
			port = int(port)
		return scheme, host, port, path
