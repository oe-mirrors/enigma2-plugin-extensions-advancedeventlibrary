from json import loads
from html import unescape
from linecache import getline
from os.path import join, isfile
from re import findall, sub, search, compile, match, MULTILINE, DOTALL
from time import localtime
from enigma import iPlayableServicePtr, eServiceCenter, eServiceReference, eEPGCache
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Sources.CurrentService import CurrentService
from ServiceReference import ServiceReference
from Tools.AdvancedEventLibrary import aelGlobals, getPictureDir, convertDateInFileName, convertTitle, convertTitle2, convert2base64, convertSearchName, getDB, getImageFile

countrys = {
	'USA': ['United States', 'US', 'USA'],
	'DE': ['Deutschland', 'DE', 'BRD', 'Germany', 'DDR'],
	'GB': ['GB', 'Großbritanien', 'England', 'United Kingdom'],
	'IT': ['IT', 'Italien', 'Italy'],
	'AT': ['AT', 'Österreich', 'Austria'],
	'CH': ['CH', 'Schweiz', 'Switzerland', 'Swiss'],
	'FR': ['FR', 'Frankreich', 'France'],
	'AUS': ['AUS', 'Australien', 'Australia'],
	'CDN': ['CDN', 'CA', 'Kanada', 'Canada'],
	'SWD': ['SWD', 'SE', 'Schweden', 'Sweden'],
	'IRL': ['IRL', 'Irland', 'Ireland'],
	'AR': ['AR', 'Argentinien', 'Argentina'],
	'AU': ['AU', 'Australien', 'Australia'],
	'BE': ['BE', 'Belgien', 'Belgium'],
	'BR': ['BR', 'Brasilien', 'Brazil'],
	'BG': ['BG', 'Bulgarien', 'Bulgaria'],
	'CL': ['CL', 'Chile'],
	'CN': ['CN', 'China'],
	'CY': ['CY', 'Zypern', 'Cyprus'],
	'CZ': ['CZ', 'Tschechien', 'Czech Republic'],
	'DK': ['DK', 'Dänemark', 'Denmark'],
	'EG': ['EG', 'Ägypten', 'Egypt'],
	'FT': ['FT', 'Finnland', 'Finland'],
	'GR': ['GR', 'Griechenland', 'Greece'],
	'HK': ['HK', 'Hong Kong'],
	'HU': ['HU', 'Ungarn', 'Hungary'],
	'IS': ['IS', 'Island', 'Iceland'],
	'IN': ['IND', 'Indien', 'India'],
	'JP': ['JP', 'Japan'],
	'MX': ['MX', 'Mexico'],
	'NL': ['NL', 'Niederlande', 'Netherlands'],
	'NZ': ['NZ', 'Neuseeland', 'New Zealand'],
	'NO': ['NO', 'Norwegen', 'Norway'],
	'PL': ['PL', 'Polen', 'Poland'],
	'PT': ['PT', 'Portugal'],
	'RU': ['RU', 'Russland', 'Russia', 'Russian Federation', 'UdSSR'],
	'ES': ['ESP', 'Spanien', 'Spain']
	}


class AdvancedEventLibraryInfo(Converter, object):				# Input Parameter per Skin
	EPISODE_NUM = "EpisodeNum"									# optional formatierung angeben -> z.B. EpisodeNum(Staffel [s] Episode[ee])
	TITLE = "Title"												# optional mit Prefix angabe -> z.B. Titel oder Titel(Titel:)
	SUBTITLE = "Subtitle"										# mit MaxWord angabe -> z.B. Subtitle(10)
	SUBTITLE_CLEAN = "SubtitleClean"							# mit MaxWord angabe -> z.B. Subtitle(10), ohne Episode, Rating, etc. Infos
	PARENTAL_RATING = "ParentalRating"							# optional mit Prefix angabe -> z.B. ParentalRating oder ParentalRating(FSK)
	GENRE = "Genre"												# optional mit Prefix angabe -> z.B. Genre oder Genre(Genre:)
	YEAR = "Year"												# optional mit Prefix angabe -> z.B. Year oder Year(Jahr:)
	COUNTRY = "Country"											# optional mit Prefix angabe -> z.B. Country oder Country(Land:)
	RATING = "Rating"											# optional mit Prefix angabe -> z.B. Rating(Bewertung)
	RATING_STARS = "RatingStars"								# optional mit Prefix angabe -> z.B. RatingStars(star) -> Output: 65 -> kann für Images verwendet werden
	RATING_STARS_AS_TEXT = "RatingStarsAsText"					# optional mit Prefix angabe -> z.B. RatingStars(star) -> Output: 65 -> kann für Images verwendet werden
	CATEGORY = "Category"										# optional mit Prefix angabe -> z.B. Category(Kategorie:)
	LEADTEXT = "Leadtext"										# optional mit Prefix angabe -> z.B. Leadtext(Kurzbeschreibung:)
	CONCLUSION = "Conclusion"									# optional mit Prefix angabe -> z.B. Conclusion(Kritik:)
	EXTENDED_DESCRIPTION = "ExtendedDescription"				# optional mit Prefix angabe -> z.B. ExtendedDescription oder ExtendedDescription(Land:)
	EXTENDED_DESCRIPTION_CLEAN = "ExtendedDescriptionClean"		# optional mit Prefix angabe -> z.B. ExtendedDescriptionClean oder ExtendedDescriptionClean(Land:), ohne Episode, Rating, etc. Infos
	POWER_DESCRIPTION = "PowerDescription"
	ONE_LINE_DESCRIPTION = "OneLineDescription"
	SIMILAR_EVENTS = "SimilarEvents"
	WideInfo = "WideInfo"
	DolbyInfo = "DolbyInfo"
	HDInfo = "HDInfo"
	DolbyA = "DolbyA"
	DolbyB = "DolbyB"
	seriesNumParserList = [(r'(\d+)[.]\sStaffel[,]\sFolge\s(\d+)'),
							(r'(\d+)[.]\sStaffel[,]\sEpisode\s(\d+)'),
							(r'(\d+)[.]\sEpisode\sder\s(\d+)[.]\sStaffel'),
							(r'[(](\d+)[.](\d+)[)]')
							]  # Parser fuer Serien- und Episodennummer
	SPECIAL_FORMAT_PARSED_DESCRIPTION_SUBTITLE = 0
	SPECIAL_FORMAT_PARSED_DESCRIPTION_GENRE = 1
	SPECIAL_FORMAT_PARSED_DESCRIPTION_YEAR = 2
	SPECIAL_FORMAT_PARSED_DESCRIPTION_COUNTRY = 3

	def __init__(self, type):
		Converter.__init__(self, type)
		self.inputString = type
		self.types = str(type).split(",")
		self.coverPath = f"{getPictureDir()}cover/"
		self.posterPath = f"{getPictureDir()}poster/"
		self.eventName = ""
		self.db = getDB()
		self.sceenName = ""

	@cached
	def getBoolean(self):
		event = None
		if hasattr(self.source, 'getEvent'):
			event = self.source.getEvent()
		elif hasattr(self.source, 'event'):
			event = self.source.event
		if not event:
			return False
		if (isinstance(event, tuple) and event):
			event = event[0]
		data = str(event.getComponentData())
		for type in self.types:
			type.strip()
			if self.WideInfo in type:
				return True if "16:9" in data or "11" in data or "Breitwand" in data else False
			elif self.DolbyInfo in type:
				return True if "Dolby" in data else False
			elif self.HDInfo in type:
				return True if "11" in data or "HDTV" in data else False
			elif self.DolbyA in type:
				if "Dolby Digital 2.0" in data:
					return False
				if "Dolby Digital 5.1" in data or "11" in data:
					return True
				return False
			elif self.DolbyB in type:
				return True if "Dolby Digital 2.0" in data else False

	boolean = property(getBoolean)

	@cached
	def getText(self):
		isMovieFile = None
		event = None
		if hasattr(self.source, 'getEvent'):
			event = self.source.getEvent()
		else:
			event = self.source.event
			if hasattr(self.source, 'service'):
				spath = None
				service = self.source.service
				if service:
					if isinstance(service, eServiceReference):
						spath = service.getPath()
					elif isinstance(service, str):
						spath = service.rsplit(':', 1)[1].strip() if ':' in service else ServiceReference(service).ref.getPath()
					if spath:
						if spath.endswith(".ts") or spath.endswith(".mkv") or spath.endswith(".mpg") or spath.endswith(".avi") or spath.endswith(".mp4") or spath.endswith(".iso") or spath.endswith(".mpeg2") or spath.endswith(".wmv"):
							isMovieFile = spath
		if hasattr(self.source, 'service'):
			service = self.source.service
			if not isinstance(self.source, CurrentService):
				serviceHandler = eServiceCenter.getInstance()
				info = serviceHandler.info(service)
				spath = service.getPath()
				if spath.endswith(".ts") or spath.endswith(".mkv") or spath.endswith(".mpg") or spath.endswith(".avi") or spath.endswith(".mp4") or spath.endswith(".iso") or spath.endswith(".mpeg2") or spath.endswith(".wmv"):
					isMovieFile = spath
#				else:
#					isMovieFile = info.getName(service)
			elif not '<Components.Sources.ServiceEvent.ServiceEvent' in str(self.source):
				if isinstance(service, iPlayableServicePtr):
					info = service and service.info()
					ref = None
				else:  # reference
					info = service and self.source.info
					ref = service
				if info != None:
					name = ref and info.getName(ref)
					if name is None:
						if ref is None:
							if isinstance(self.source, CurrentService):
								ref = self.source.getCurrentServiceReference()
						if ref:
							if ref.getPath():
								isMovieFile = str(ref.getPath())
								serviceHandler = eServiceCenter.getInstance()
								info_tmp = serviceHandler.info(ref)
								if info_tmp:
									event = info_tmp.getEvent(ref)
		if (isinstance(event, tuple) and event):  # Prüfen ob event tuple ist
			event = event[0]
		if event and self.types != '':
			result = []
			if not isMovieFile:
				self.eventName = self.removeExtension(event.getEventName())
			else:
				if isfile(f"{isMovieFile}.meta"):
					self.eventName = self.removeExtension(getline(f"{isMovieFile}.meta", 2).replace("\n", "").strip())
				else:
					self.eventName = self.removeExtension(((str(isMovieFile).split('/')[-1]).rsplit('.', 1)[0]).replace('_', ' '))
			self.eventName = convertDateInFileName(convertSearchName(self.eventName))
			values = None
			if not isMovieFile and event != None:
				eventid = None
				ename = None
				val = None
				ename = event.getEventName()
				eventid = event.getEventId()
				eventTime = event.getBeginTime()
				if eventid and ename:
					val = self.db.getliveTV(eventid, ename, eventTime)
					if val:
						values = {
							'subtitle': str(val[0][2]),
							'vote': str(val[0][6]),
							'year': str(val[0][4]),
							'ageRating': str(val[0][5]),
							'title': str(val[0][7]),
							'leadText': str(val[0][9]),
							'conclusion': str(val[0][10]),
							'categoryName': str(val[0][11]),
							'season': str(val[0][12]),
							'genre': str(val[0][14]),
							'episode': str(val[0][13]),
							'country': str(val[0][15])
							}
			dbData = None
			try:
				dbData = self.db.getTitleInfo(convert2base64(self.eventName))
				if not dbData:
					dbData = self.db.getTitleInfo(convert2base64(convertTitle(self.eventName)))
					if not dbData:
						dbData = self.db.getTitleInfo(convert2base64(convertTitle2(self.eventName)))
			except Exception:
				if values:
					dbData = self.db.getTitleInfo(convert2base64(str(values['title']).strip()))
					if not dbData:
						dbData = self.db.getTitleInfo(convert2base64(convertTitle(str(values['title']).strip())))
						if not dbData:
							dbData = self.db.getTitleInfo(convert2base64(convertTitle2(str(values['title']).strip())))
			for type in self.types:
				type.strip()
				if self.POWER_DESCRIPTION in type:
					powerDescription = self.getPowerDescription(self.inputString, event, values, dbData, isMovieFile)
					return powerDescription if (powerDescription != None) else ''
				elif self.EPISODE_NUM in type:
					episodeNum = self.getEpisodeNum(type, event, values, isMovieFile)
					if (episodeNum != None):
						result.append(episodeNum)
				elif self.SIMILAR_EVENTS in type:
					similarEvents = self.getSimilarEvents(type, self.eventName)
					if (similarEvents != None and len(similarEvents) > 0 and similarEvents != ' '):
						result.append(similarEvents)
				elif self.TITLE in type:
					title = self.getTitleWithPrefix(type, event, values)
					if (title != None and len(title) > 0 and title != ' '):
						result.append(title)
				elif self.SUBTITLE in type:
					subtitle = self.getSubtitle(type, event, values, dbData, True) if (self.SUBTITLE_CLEAN in type) else self.getSubtitle(type, event, values, dbData, False)
					if (subtitle != None and len(subtitle) > 0 and subtitle != ' '):
						result.append(subtitle)
				elif self.PARENTAL_RATING in type:
					parentialRating = self.getParentalRating(type, event, values, dbData, isMovieFile)
					if (parentialRating != None):
						result.append(parentialRating)
				elif self.RATING in type:
					rating = None
					if (self.RATING_STARS_AS_TEXT in type):
						rating = self.getRating(type, values, event, False, dbData, isMovieFile, True)
					elif (self.RATING_STARS in type):
						#gerundetes Rating, kann z.B. für Rating Images verwendet werden
						rating = self.getRating(type, values, event, True, dbData, isMovieFile)
					else:
						#Rating als Kommazahl
						rating = self.getRating(type, values, event, False, dbData, isMovieFile)
					if (rating != None):
						result.append(rating)
				elif self.CATEGORY in type:
					category = self.getCategory(type, values)
					if (category != None):
						result.append(category)
				elif self.GENRE in type:
					genre = self.getGenre(type, values, event, dbData, isMovieFile)
					if (genre != None):
						result.append(genre)
				elif self.YEAR in type:
					year = self.getYear(type, values, event, dbData, isMovieFile)
					if (year != None):
						result.append(year)
				elif self.COUNTRY in type:
					country = self.getCountry(type, values, event, dbData, isMovieFile)
					if (country != None):
						result.append(country)
				elif self.LEADTEXT in type:
					leadtext = self.getLeadText(type, values)
					if (leadtext != None):
						result.append(leadtext)
				elif self.CONCLUSION in type:
					conclusion = self.getConclusion(type, values)
					if (conclusion != None):
						result.append(conclusion)
				elif self.EXTENDED_DESCRIPTION in type:
					extendedDescription = self.getExtendedDescription(type, values, event, True, dbData, isMovieFile) if (self.EXTENDED_DESCRIPTION_CLEAN in type) else self.getExtendedDescription(type, values, event, False, dbData, isMovieFile)
					if (extendedDescription != None):
						result.append(extendedDescription)
				elif self.ONE_LINE_DESCRIPTION in type:
					oneLineDescription = self.getOneLineDescription(type, event, isMovieFile)
					if (oneLineDescription != None):
						result.append(oneLineDescription)
				else:
					result.append("!!! invalid parameter '%s' !!!" % (type))
			sep = ' %s ' % str(unescape('&#xB7;'))
			return sep.join(result)
		return ""

	text = property(getText)

	def getPowerDescription(self, input, event, values, dbData, isMovie):
		condition = None
		inputParser = match(r'^PowerDescription[[](.*)[]$]', input, MULTILINE | DOTALL)  # InputParser ohne Condition
		inputParserWithCondition = match(r'^PowerDescription[[](True|False|true|false|isImageAvailable|isPosterAvailable|isNoImageAvailable|isNoPosterAvailable)[]][[](.*)[]$]', input, MULTILINE | DOTALL)  # InputParser mit Condition
		if (inputParserWithCondition != None):
			condition = inputParserWithCondition.group(1)
			input = inputParserWithCondition.group(2)
		elif (inputParser != None):
			input = inputParser.group(1)
		else:
			input = None
		if (input != None):
			if (condition != None and condition == 'isImageAvailable' and not self.isImageAvailable(event, values)):
				return
			elif (condition != None and condition == 'isPosterAvailable' and not self.isPosterAvailable(event, values)):
				return
			elif (condition != None and condition == 'isNoImageAvailable' and self.isImageAvailable(event, values)):
				return
			elif (condition != None and condition == 'isNoPosterAvailable' and self.isPosterAvailable(event, values)):
				return
			if (self.TITLE in input):
				type = self.getParsedTyp(self.TITLE, input)
				title = self.getTitleWithPrefix(type, event, values)
				input = input.replace(type, title) if (title != None and len(title) > 0 and title != ' ') else str(input).replace(type, "")
			if (self.SUBTITLE in input):
				if (self.SUBTITLE_CLEAN in input):
					type = self.getParsedTyp(self.SUBTITLE_CLEAN, input)
					subtitle = self.getSubtitle(type, event, values, dbData, True)
				else:
					type = self.getParsedTyp(self.SUBTITLE, input)
					subtitle = self.getSubtitle(type, event, values, dbData, False)
				input = input.replace(type, subtitle) if (subtitle != None and len(subtitle) > 0 and subtitle != ' ') else str(input).replace(type, "")
			if (self.GENRE in input):
				type = self.getParsedTyp(self.GENRE, input)
				genre = self.getGenre(type, values, event, dbData, isMovie)
				input = input.replace(type, genre) if (genre != None) else str(input).replace(type, "")
			if (self.EPISODE_NUM in input):
				type = self.getParsedTyp(self.EPISODE_NUM, input)
				episodeNum = self.getEpisodeNum(type, event, values, isMovie)
				input = input.replace(type, episodeNum) if (episodeNum != None) else str(input).replace(type, "")
			if (self.CATEGORY in input):
				type = self.getParsedTyp(self.CATEGORY, input)
				category = self.getCategory(type, values)
				input = input.replace(type, category) if (category != None) else str(input).replace(type, "")
			if (self.SIMILAR_EVENTS in input):
				type = self.getParsedTyp(self.SIMILAR_EVENTS, input)
				similarEvents = self.getSimilarEvents(type, self.eventName)
				input = input.replace(type, similarEvents) if (similarEvents != None) else str(input).replace(type, "")
			if (self.PARENTAL_RATING in input):
				type = self.getParsedTyp(self.PARENTAL_RATING, input)
				parentialRating = self.getParentalRating(type, event, values, dbData, isMovie)
				input = input.replace(type, parentialRating) if (parentialRating != None) else str(input).replace(type, "")
			if (self.RATING in input):
				type = self.getParsedTyp(self.RATING, input)
				rating = self.getRating(type, values, event, False, dbData, isMovie)
				input = input.replace(type, rating) if (rating != None) else str(input).replace(type, "")
			if (self.RATING_STARS_AS_TEXT in input):
				type = self.getParsedTyp(self.RATING, input)
				rating = self.getRating(type, values, event, False, dbData, isMovieFile, True)
				input = input.replace(type, rating) if (rating != None) else str(input).replace(type, "")
			if (self.YEAR in input):
				type = self.getParsedTyp(self.YEAR, input)
				year = self.getYear(type, values, event, dbData, isMovie)
				input = input.replace(type, year) if (year != None) else str(input).replace(type, "")
			if (self.COUNTRY in input):
				type = self.getParsedTyp(self.COUNTRY, input)
				country = self.getCountry(type, values, event, dbData, isMovie)
				input = input.replace(type, country) if (country != None) else str(input).replace(type, "")
			if (self.LEADTEXT in input):
				type = self.getParsedTyp(self.LEADTEXT, input)
				leadtext = self.getLeadText(type, values)
				input = input.replace(type, leadtext) if (leadtext != None) else str(input).replace(type, "")
			if (self.CONCLUSION in input):
				type = self.getParsedTyp(self.CONCLUSION, input)
				conclusion = self.getConclusion(type, values)
				input = input.replace(type, conclusion) if (conclusion != None) else str(input).replace(type, "")
			if self.ONE_LINE_DESCRIPTION in input:
				oneLineDescription = self.getOneLineDescription(type, event, isMovie)
				input = input.replace(type, oneLineDescription) if (oneLineDescription != None) else str(input).replace(type, "")
			if (self.EXTENDED_DESCRIPTION in input):
				if (self.EXTENDED_DESCRIPTION_CLEAN in input):
					type = self.getParsedTyp(self.EXTENDED_DESCRIPTION_CLEAN, input)
					extendedDescription = self.getExtendedDescription(type, values, event, True, dbData, isMovie)
				else:
					type = self.getParsedTyp(self.EXTENDED_DESCRIPTION, input)
					extendedDescription = self.getExtendedDescription(type, values, event, False, dbData, isMovie)
				input = input.replace(type, extendedDescription) if (extendedDescription != None) else str(input).replace(type, "")
			middleDot = str(unescape('&#xB7;'))  # '\,' in MiddleDot umwandeln
			sep = ' %s ' % middleDot
			input = input.replace('\\,', sep)
			input = input.replace('%s  %s' % (middleDot, middleDot), middleDot)  # Doppelte MiddleDot in einen umwandeln
			input = input.replace('%s \\n' % middleDot, "\\n")
			if (input.startswith('\\n\\n\\n')):  # falls input mit newline beginnt -> entfernen
				return input[6:]
			elif (input.startswith('\\n\\n')):
				return input[4:]
			elif (input.startswith('\\n')):
				return input[2:]
			elif (input.startswith(sep)):
				return input[4:]
			else:
				return input
		else:
			return "Wrong format: %s" % (input)

	def getParsedTyp(self, type, input):
		parseString = r'(%s[(].*?[)])' % (type)
		parser = search(parseString, input)
		return parser.group(1) if parser else type

	def getSimilarEvents(self, type, name):
		text = ''
		epgcache = eEPGCache.getInstance()
		ret = epgcache.search(('NB', 100, eEPGCache.EXAKT_TITLE_SEARCH, str(name), eEPGCache.NO_CASE_CHECK))
		if ret is not None:
			ret.sort(self.sort_func)
			del ret[0]
			for x in ret:
				if not x[0].startswith('.'):
					t = localtime(x[1])
					text += '\n%d.%d.%d - %02d:%02d  -  %s' % (t[2], t[1], t[0], t[3], t[4], x[0])
			prefix = self.getPrefixParser(type)
			if (text != None and prefix != None):
				text = '%s%s' % (prefix, text)
		return text

	def sort_func(self, x, y):
		if x[1] < y[1]:
			return -1
		elif x[1] == y[1]:
			return 0
		else:
			return 1

	def getCountry(self, type, values, event, dbData, isMovie):
		country = None
		if (values != None and len(values) > 0 and country == None) and 'country' in values and len(str(values['country']).strip()) > 0:
			country = str(values['country']).strip()

		if (country == None and isMovie != None) and isfile(isMovie + '.meta'):
			desc = getline(isMovie + '.meta', 3)
			parsedDesc = self.getSpecialFormatDescription(desc, self.SPECIAL_FORMAT_PARSED_DESCRIPTION_COUNTRY)
			country = parsedDesc if (parsedDesc != None) else self.findCountry(desc)[0]
		if dbData and country == None:
			if len(dbData[6]) > 0:
				country = str(dbData[6])
		if (country == None and event != None):
			desc = event.getShortDescription()
			if (desc == ''):  # Rückfalllösung über FullDescription
				desc = self.getFullDescription(event)
			if desc != "":
				country = self.findCountry(self.getFullDescription(event))[0]
				if country == None:  # Spezielle EPG Formate parsen
					parsedDesc = self.getSpecialFormatDescription(desc, self.SPECIAL_FORMAT_PARSED_DESCRIPTION_COUNTRY)
					if (parsedDesc != None):
						country = parsedDesc
			if (country == None):  # country aus FullDescription parsen -> Foromat ' xx Min.\n Land Jahr'
				country = self.getParsedCountryOrYear(self.SPECIAL_FORMAT_PARSED_DESCRIPTION_COUNTRY, event.getExtendedDescription(), event)
		prefix = self.getPrefixParser(type)
		if (country != None and prefix != None):
			country = '%s%s' % (prefix, country)
		return country

	def getExtendedDescription(self, type, values, event, clean, dbData, isMovie):
		desc = None
		if isMovie:
			if isfile(isMovie + '.txt'):
				with open(isMovie + '.txt', "r") as f:
					desc = f.read()
			elif isfile(self.removeExtension(isMovie) + '.txt'):
				with open(self.removeExtension(isMovie) + '.txt', "r") as f:
					desc = f.read()
		if event != None:
			if desc:
				ext = event.getExtendedDescription()
				if ext and ext != "":
					ext += '\n\n'
				else:
					ext = ""
				ext += desc
				desc = ext
			else:
				desc = event.getExtendedDescription()
			if (desc != "" and desc != None):
				prefix = self.getPrefixParser(type)
				if (desc != None and prefix != None):
					desc = '%s%s' % (prefix, desc)
			if (clean):
				if (desc != None and ". Staffel, Folge" in desc):  # Episoden Nummer entfernen
					episodeNum = self.getEpisodeNum("EpisodeNum([s]. Staffel, Folge [e]: )", event, values, isMovie)
					if (episodeNum != None):
						desc = desc.replace(episodeNum, "")
				if (desc != None):  # ParentalRating entfernen
					desc = desc.replace("Ab 0 Jahren", "").replace("Ab 6 Jahren", "").replace("Ab 12 Jahren", "").replace("Ab 16 Jahren", "").replace("Ab 18 Jahren", "")
					desc = desc.replace("Ab 0 Jahre", "").replace("Ab 6 Jahre", "").replace("Ab 12 Jahre", "").replace("Ab 16 Jahre", "").replace("Ab 18 Jahre", "")
					desc = desc.replace("Altersfreigabe: ab 6", "").replace("Altersfreigabe: ab 12", "").replace("Altersfreigabe: ab 16", "").replace("Altersfreigabe: ab 18", "").replace("Altersfreigabe: ab 0", "")
					desc = desc.replace("FSK0", "").replace("FSK6", "").replace("FSK12", "").replace("FSK16", "").replace("FSK18", "").replace("FSK 0", "").replace("FSK 6", "").replace("FSK 12", "").replace("FSK 16", "").replace("FSK 18", "")
				if (desc != None):  # Country und Year entfernen
					country = self.getCountry("Country", values, event, dbData, isMovie)
					year = self.getYear("Year", values, event, dbData, isMovie)
					if (country != None and year != None):
						desc = desc.replace("%s %s. " % (country, year), "")
						desc = desc.replace("%s %s." % (country, year), "")
						desc = desc.replace("%s %s, " % (country, year), "")
						desc = desc.replace("%s %s" % (country, year), "")
				if (desc != None and 'IMDb rating:' in desc):  # Rating entfernen
					rating = self.getRating(self.RATING, values, event, False, dbData, isMovie)
					if (rating != None):
						rating = rating.replace(",", ".")
						desc = desc.replace(" IMDb rating: %s/10." % (rating), "")
		return desc

	def getOneLineDescription(self, type, event, isMovie=None):
		desc = None
		if (event != None):
			desc = event.getShortDescription()

		if (desc == None and isMovie):
			if isfile(isMovie + '.meta'):
				desc = getline(isMovie + '.meta', 3)

		if (desc != "" and desc != None):
			if '\n' in desc:
				desc = desc.replace('\n', ' ' + str(unescape('&#xB7;')) + ' ')
			else:
				tdesc = desc.split("\n")
				desc = tdesc[0].replace('\\n', ' ' + str(unescape('&#xB7;')) + ' ')
			prefix = self.getPrefixParser(type)
			if (desc != None and prefix != None):
				desc = '%s%s' % (prefix, desc)
			if desc.find(' Altersfreigabe: Ohne Altersbe') > 0:
				desc = desc[:desc.find(' Altersfreigabe: Ohne Altersbe')] + ' FSK: 0'
			desc = (" ".join(findall(r"[A-Za-z0-9üäöÜÄÖß:.,!?()]*", desc))).replace("  ", " ").replace('Altersfreigabe: ab', 'FSK:')
			return desc
		return

	def getYear(self, type, values, event, dbData, isMovie):
		year = None
		if (values != None and len(values) > 0 and year == None) and 'year' in values and len(str(values['year']).strip()) > 0:
			year = str(values['year']).strip()
		if (year == None and event != None):
			desc = event.getShortDescription()
			if (desc == ''):  # Rückfalllösung über FullDescription
				desc = self.getFullDescription(event)
			else:  # Spezielle EPG Formate parsen
				parsedDesc = self.getSpecialFormatDescription(desc, self.SPECIAL_FORMAT_PARSED_DESCRIPTION_YEAR)
				if (parsedDesc != None):
					year = parsedDesc
			if (year == None):  # Year aus FullDescription parsen -> Foromat ' xx Min.\n Land Jahr'
				year = self.getParsedCountryOrYear(self.SPECIAL_FORMAT_PARSED_DESCRIPTION_YEAR, event.getExtendedDescription(), event)
		if (year == None and isMovie != None):
			if isfile(isMovie + '.meta'):
				desc = getline(isMovie + '.meta', 3)
				parsedDesc = self.getSpecialFormatDescription(desc, self.SPECIAL_FORMAT_PARSED_DESCRIPTION_YEAR)
				year = parsedDesc if (parsedDesc != None) else self.findYear(desc)
		if (year == None and event != None):
			year = self.findYear(self.getFullDescription(event))
		if dbData and year == None and len(dbData[3]) > 0:
			if len(dbData[2]) > 0:
				if "Serie" in str(dbData[2]) or "Soap" in str(dbData[2]):
					year = "(EA) " + str(dbData[3])
				else:
					year = str(dbData[3])
			else:
				year = str(dbData[3])
		prefix = self.getPrefixParser(type)
		if (year != None and prefix != None):
			year = '%s%s' % (prefix, year)
		return year

	def getGenre(self, type, values, event, dbData, isMovie):
		genre = None
		if (values != None and len(values) > 0 and genre == None) and 'genre' in values and len(str(values['genre']).strip()) > 0:
			genre = str(values['genre']).strip()
		if dbData and genre == None and len(dbData[2]) > 0:
			genre = str(dbData[2])
		if (genre == None and isMovie != None) and isfile(isMovie + '.meta'):
			name = getline(isMovie + '.meta', 2).replace('\n', '')
			desc = getline(isMovie + '.meta', 3).replace(name, '').replace('Altersfreigabe', ' Altersfreigabe').replace('\n', '')
			genre = self.getCompareGenreWithGenreList(desc, None)
			if not genre:
				parsedDesc = self.getSpecialFormatDescription(desc, self.SPECIAL_FORMAT_PARSED_DESCRIPTION_GENRE)
				if (parsedDesc != None):
					genre = parsedDesc
		if (genre == None and event != None):
			desc = event.getShortDescription().replace('\n', ' ')
			if (desc == ''):  # Rückfalllösung über FullDescription
				desc = self.getFullDescription(event)
			if desc != "":
				genre = self.getCompareGenreWithGenreList(desc, None)
				if (genre == None):  # Spezielle EPG Formate parsen
					parsedDesc = self.getSpecialFormatDescription(desc, self.SPECIAL_FORMAT_PARSED_DESCRIPTION_GENRE)
					if (parsedDesc != None):
						genre = parsedDesc
		if genre != None:
			maxGenres = genre.split()
			if maxGenres and len(maxGenres) >= 1:
				genre = maxGenres[0]  # + ' ' + str(unescape('&#xB7;')) + ' ' + maxGenres[1]
		prefix = self.getPrefixParser(type)
		if (genre != None and prefix != None):
			genre = '%s%s' % (prefix, genre)
		return genre

	def getCategory(self, type, values):
		category = None
		if (values != None and len(values) > 0) and 'categoryName' in values and len(str(values['categoryName']).strip()) > 0:
			category = str(values['categoryName']).strip()
		prefix = self.getPrefixParser(type)
		if (category != None and prefix != None):
			category = '%s%s' % (prefix, category)
		return category

	def getLeadText(self, type, values):
		leadtext = None
		if (values != None and len(values) > 0) and 'leadText' in values and len(str(values['leadText']).strip()) > 0:
			leadtext = str(values['leadText']).strip()
		prefix = self.getPrefixParser(type)
		if (leadtext != None and prefix != None):
			leadtext = '%s%s' % (prefix, leadtext)
		return leadtext

	def getConclusion(self, type, values):
		conclusion = None
		if (values != None and len(values) > 0) and 'conclusion' in values and len(str(values['conclusion']).strip()) > 0:
			conclusion = str(values['conclusion']).strip()
		prefix = self.getPrefixParser(type)
		if (conclusion != None and prefix != None):
			conclusion = '%s%s' % (prefix, conclusion)
		return conclusion

	def getRating(self, type, values, event, isStars, dbData, isMovie, starsAsText=False):
		rating = None
		if dbData and len(dbData[4]) > 0:
			tmp = str(dbData[4]).strip()
			rating = self.getRatingAsNumber(tmp, isStars, starsAsText)
		if (values != None and len(values) > 0 and rating == None) and 'vote' in values and len(str(values['vote']).strip()) > 0:
			tmp = str(values['vote']).strip()
			rating = self.getRatingAsNumber(tmp, isStars, starsAsText)
		if (rating == None and event != None) or (rating == str(0) and event != None):
			desc = self.getFullDescription(event)  # Rating aus Description extrahieren
			parser = search(r'IMDb rating:\s(\d+\.\d+)[/]', desc)
			if (parser):
				tmp = str(parser.group(1))
				rating = self.getRatingAsNumber(tmp, isStars, starsAsText)
		prefix = self.getPrefixParser(type)
		if (rating != None and prefix != None):
			rating = '%s%s' % (prefix, rating)
		return rating

	def getRatingAsNumber(self, strRating, isStars, starsAsText=False):
		if (self.isNumber(strRating)):
			if (float(strRating) > 0):  # Nur anzeigen wenn Rating > 0
				if (isStars):
					return str(round(float(strRating) * 2) / 2).replace(".", "")
				elif (starsAsText):
					return str(unescape('&#9733;')) * int(round(float(strRating) * 2) / 2)
				else:
					return str(round(float(strRating), 1)).replace(".", ",")
			else:
				if (isStars or starsAsText):
					return
		else:
			if (isStars or starsAsText):
				return

	def getParentalRating(self, type, event, values, dbData, isMovie):
		parentialRating = None
		if (parentialRating == None and event != None):
			desc = self.getFullDescription(event)
			parser = search(r'Ab\s(\d+)\s[Jahren|Jahre]', desc)
			if not parser:
				if desc.find('Altersfreigabe: Ohne Altersbe') > 0:
					parentialRating = str(0)
				elif 'Altersfreigabe: ab 0' in desc:
					parentialRating = str(0)
				elif 'Altersfreigabe: ab 6' in desc:
					parentialRating = str(6)
				elif 'Altersfreigabe: ab 12' in desc:
					parentialRating = str(12)
				elif 'Altersfreigabe: ab 16' in desc:
					parentialRating = str(16)
				elif 'Altersfreigabe: ab 18' in desc:
					parentialRating = str(18)
				elif 'FSK0' in desc:
					parentialRating = str(0)
				elif 'FSK6' in desc:
					parentialRating = str(6)
				elif 'FSK12' in desc:
					parentialRating = str(12)
				elif 'FSK16' in desc:
					parentialRating = str(16)
				elif 'FSK18' in desc:
					parentialRating = str(18)
				elif 'FSK 0' in desc:
					parentialRating = str(0)
				elif 'FSK 6' in desc:
					parentialRating = str(6)
				elif 'FSK 12' in desc:
					parentialRating = str(12)
				elif 'FSK 16' in desc:
					parentialRating = str(16)
				elif 'FSK 18' in desc:
					parentialRating = str(18)
			if (parser):
				parentialRating = parser.group(1)

		if (parentialRating == None and isMovie != None) and isfile(isMovie + '.meta'):
			desc = getline(isMovie + '.meta', 3)
			parser = search(r'Ab\s(\d+)\s[Jahren|Jahre]', desc)
			if not parser:
				if desc.find('Altersfreigabe: Ohne Altersbe') > 0:
					parentialRating = str(0)
				elif 'Altersfreigabe: ab 0' in desc:
					parentialRating = str(0)
				elif 'Altersfreigabe: ab 6' in desc:
					parentialRating = str(6)
				elif 'Altersfreigabe: ab 12' in desc:
					parentialRating = str(12)
				elif 'Altersfreigabe: ab 16' in desc:
					parentialRating = str(16)
				elif 'Altersfreigabe: ab 18' in desc:
					parentialRating = str(18)
				elif 'FSK0' in desc:
					parentialRating = str(0)
				elif 'FSK6' in desc:
					parentialRating = str(6)
				elif 'FSK12' in desc:
					parentialRating = str(12)
				elif 'FSK16' in desc:
					parentialRating = str(16)
				elif 'FSK18' in desc:
					parentialRating = str(18)
				elif 'FSK 0' in desc:
					parentialRating = str(0)
				elif 'FSK 6' in desc:
					parentialRating = str(6)
				elif 'FSK 12' in desc:
					parentialRating = str(12)
				elif 'FSK 16' in desc:
					parentialRating = str(16)
				elif 'FSK 18' in desc:
					parentialRating = str(18)
			if (parser):
				parentialRating = parser.group(1)
		if (values != None and len(values) > 0 and parentialRating == None) and 'ageRating' in values:
			if len(str(values['ageRating']).strip()) > 0:
				tmp = str(values['ageRating']).strip()
				try:
					tmp = int(tmp)
					if tmp in range(0, 6):
						parentialRating = str(0)
					elif tmp in range(6, 12):
						parentialRating = str(6)
					elif tmp in range(12, 16):
						parentialRating = str(12)
					elif tmp in range(16, 18):
						parentialRating = str(16)
					elif tmp >= 18:
						parentialRating = str(18)
				except Exception:
					if tmp.find('Ohne Altersbe') > 0:
						parentialRating = str(0)
					elif (tmp == 'KeineJugendfreigabe' or tmp == 'KeineJugendfreige'):
						parentialRating = str(18)
					elif (tmp != 'Unbekannt'):
						parentialRating = tmp
		if dbData and parentialRating == None and len(dbData[5]) > 0:
			parentialRating = str(dbData[5])
		prefix = self.getPrefixParser(type)
		if (parentialRating != None and prefix != None):
			parentialRating = '%s%s' % (prefix, parentialRating)
		return parentialRating

	def getTitle(self, event, values):  # Nur Title ohne Prefix, wird zum vergleichen benötigt
		title = None
		if (values != None and len(values) > 0):
			if len(str(values['title']).strip()) > 0:
				title = str(values['title']).strip()
		if (title == None):
			title = self.eventName
		return title

	def getTitleWithPrefix(self, type, event, values):
		title = self.getTitle(event, values)
		prefix = self.getPrefixParser(type)
		if (title != None and prefix != None):
			title = '%s%s' % (prefix, title)
		return title

	def getSubtitle(self, type, event, values, dbData, clean):
		subtitle = None
		if (values != None and len(values) > 0):
			if len(str(values['subtitle']).strip()) > 0:
				subtitle = str(values['subtitle']).strip()
		if (subtitle == None and event != None):
			maxWords = int(self.getMaxSubtitleWords(type))
			result = self.getSubtitleFromDescription(event, maxWords, clean)
			if (result != None):
				subtitle = result
		if (subtitle != None and subtitle.rstrip('.') == self.getTitle(event, values)):  # Falls Subtitle = Title -> dann nichts zurück geben
			subtitle = None
		if (subtitle != "" and subtitle != None):
			if '\n' in subtitle:
				if clean:
					pos = subtitle.find('\n')
					subtitle = subtitle[:pos].strip()
				subtitle = subtitle.replace('\n', ' ' + str(unescape('&#xB7;')) + ' ')
			else:
				tdesc = subtitle.split("\n")
				if clean:
					if subtitle.find('\\n') > 0:
						pos = subtitle.find('\\n')
					else:
						pos = len(tdesc[0])
					subtitle = tdesc[0][:pos].strip()
				subtitle = tdesc[0].replace('\\n', ' ' + str(unescape('&#xB7;')) + ' ')
			if subtitle.find(' Altersfreigabe: Ohne Altersbe') > 0:
				subtitle = subtitle[:subtitle.find(' Altersfreigabe: Ohne Altersbe')] + ' FSK: 0'
			subtitle = (" ".join(findall(r"[A-Za-z0-9üäöÜÄÖß:.,!?()]*", subtitle))).replace("  ", " ").replace('Altersfreigabe: ab', 'FSK:')
			if (clean):  # Episoden Nummer entfernen
				if (subtitle != None and ". Staffel, Folge" in subtitle):
					episodeNum = self.getEpisodeNum("EpisodeNum([s]. Staffel, Folge [e]: )", event, values, None)
					if (episodeNum != None):
						subtitle = subtitle.replace(episodeNum, "")
				if (subtitle != None):  # ParentalRating entfernen
					se = self.findEpisode(subtitle)
					if se:
						subtitle = subtitle.replace(str(se[0]), '').replace(str(se[1]), '')
					extractEpisode = search(r'\sFolge\s(\d+)', subtitle)
					if not extractEpisode:
						extractEpisode = search(r'Folge\s(\d+)', subtitle)
					if (extractEpisode):
						subtitle = subtitle.replace(str(extractEpisode.group(0).strip()), '').replace(str(extractEpisode.group(1).strip()), '')
					subtitle = subtitle.replace("Ab 0 Jahren", "").replace("Ab 6 Jahren", "").replace("Ab 12 Jahren", "").replace("Ab 16 Jahren", "").replace("Ab 18 Jahren", "")
					subtitle = subtitle.replace("Ab 0 Jahre", "").replace("Ab 6 Jahre", "").replace("Ab 12 Jahre", "").replace("Ab 16 Jahre", "").replace("Ab 18 Jahre", "")
					subtitle = subtitle.replace("Altersfreigabe: ab 6", "").replace("Altersfreigabe: ab 12", "").replace("Altersfreigabe: ab 16", "").replace("Altersfreigabe: ab 18", "").replace("Altersfreigabe: ab 0", "")
					subtitle = subtitle.replace("FSK0", "").replace("FSK6", "").replace("FSK12", "").replace("FSK16", "").replace("FSK18", "").replace("FSK 0", "").replace("FSK 6", "").replace("FSK 12", "").replace("FSK 16", "").replace("FSK 18", "")
					subtitle = subtitle.replace("FSK: 0", "").replace("FSK: 6", "").replace("FSK: 12", "").replace("FSK: 16", "").replace("FSK: 18", "")
					country = self.getCountry("Country", values, event, dbData, None)
					year = self.getYear("Year", values, event, dbData, None)
					if (country != None and year != None):
						subtitle = subtitle.replace("%s %s. " % (country, year), "")
						subtitle = subtitle.replace("%s %s." % (country, year), "")
						subtitle = subtitle.replace("%s %s, " % (country, year), "")
						subtitle = subtitle.replace("%s %s" % (country, year), "")
						subtitle = subtitle.replace("%s %s" % ("D", year), "")
					country = self.findCountry(subtitle)
					if country:
						subtitle = subtitle.replace(str(country[1]), '')
					year = self.findYear(subtitle)
					if year:
						subtitle = subtitle.replace(str(year), '')
					if (values != None and len(values) > 0):
						if 'genre' in values and len(str(values['genre']).strip()) > 0:
							subtitle = subtitle.replace(' ' + str(values['genre']) + ' ', '')
					fileName = join(aelGlobals.PYTHONPATH, "Components/Converter/AdvancedEventLibrary_Genre.json")
					if (isfile(fileName)):
						with open(fileName) as file:
							jsonString = str(file.read())
							genreData = loads(jsonString)
							for genre in genreData:
								genre = genre.encode('utf-8')
								subtitle = subtitle.replace(' ' + str(genre) + ' ', '')
					if (values != None and len(values) > 0):
						if len(str(values['title']).strip()) > 0:
							subtitle = subtitle.replace(str(values['title']), '')
					subtitle = subtitle.replace(str(self.eventName), '').strip()
					if subtitle.startswith(','):
						subtitle = subtitle[1:]
				return subtitle.strip()
			return subtitle
		return subtitle

	def getSubtitleFromDescription(self, event, maxWords, clean=False):
		desc = None
		desc = event.getShortDescription()
		if not desc and not clean:  # Rückfalllösung über FullDescription
			desc = self.getFullDescription(event)
		if desc:  # Spezielle EPG Formate parsen
			parsedDesc = self.getSpecialFormatDescription(desc, self.SPECIAL_FORMAT_PARSED_DESCRIPTION_SUBTITLE)
			if (parsedDesc != None):
				return parsedDesc
			result = self.getMaxWords(desc, maxWords)  # maxWords verwenden
			if (result != None):
				genre = self.getCompareGenreWithGenreList(result, None)
				if (genre != None) and (genre == result):  # Prüfen Subtitle = Genre, dann nichts zurück geben
					return
				return result
			else:  # Wenn Wörter in shortDescription > maxWords, dann nach Zeichen suchen und bis dahin zurück geben und prüfen ob < maxWord EXPERIMENTAL
				return self.getSubtitleFromDescriptionUntilChar(event, desc, maxWords)

	def getSpecialFormatDescription(self, desc, resultTyp):  # Spezielle Formate raus werfen
		desc = desc.replace("Thema u. a.: ", "")
		wordList = desc.split(", ")
		if len(wordList) == 3:  # Format: 'Subtitle, Genre, Land Jahr'
			parser = match(r'^[^.:?;]+[,]\s[^.:?;]+[,]\s[^.:?;]+\s\d+$', desc)
			if (desc.count(", ") == 2 and parser):  # Pruefen 2x ', ' vorhanden ist und ob letzter Eintrag im Format 'Land Jahr', return desc.replace(", ", " %s " % str(unescape('&#xB7;')))
				if (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_SUBTITLE):
					return wordList[0]
				elif (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_GENRE):
					return wordList[1]
				elif (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_YEAR):
					year = self.getParsedCountryOrYear(resultTyp, wordList[2], None)
					if (year != None):
						return year
				elif (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_COUNTRY):
					country = self.getParsedCountryOrYear(resultTyp, wordList[2], None)
					if (country != None):
						return country
		#TODO: Abgleich mit Genre einfügen
		elif len(wordList) == 2:  # Format: 'Subtitle/Genre, Land Jahr' | 'Genre, Land Jahr' | 'Subtitle Genre, Land Jahr'
			parser = match(r'^[^.:?!;]+[,]\s[^.:?!;]+\s\d+$', desc)
			if (desc.count(", ") == 1 and parser):
				genre = self.getCompareGenreWithGenreList(wordList[0], ', ')
				if (genre != None):  # Format 'Genre, Land Jahr, Prüfen ob Wort vor Koma in Genre List ist -> Genre
					if (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_SUBTITLE):
						return ''
					elif (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_GENRE):
						return wordList[0]
					elif (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_YEAR):
						year = self.getParsedCountryOrYear(resultTyp, wordList[1], None)
						if (year != None):
							return year
					elif (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_COUNTRY):
						country = self.getParsedCountryOrYear(resultTyp, wordList[1], None)
						if (country != None):
							return country
				genre = self.getCompareGenreWithGenreList(wordList[0], None)  # Format 'Subtitle Genre, Land Jahr', Genre herausfiltern
				if (genre != None):
					subtitle = wordList[0].replace(genre + ". ", "").replace(genre, "").strip()
					if (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_SUBTITLE):
						return subtitle
					elif (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_GENRE):
						return genre
					elif (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_YEAR):
						year = self.getParsedCountryOrYear(resultTyp, wordList[1], None)
						if (year != None):
							return year
					elif (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_COUNTRY):
						country = self.getParsedCountryOrYear(resultTyp, wordList[1], None)
						if (country != None):
							return country
				if (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_SUBTITLE):

					return wordList[0]  # Format 'Subtitle, Land Jahr'
		if (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_GENRE):  # Wird nur für Genre angewendet
			genre = self.getCompareGenreWithGenreList(desc, None)
			if (genre != None):
				return genre

	def getSubtitleFromDescriptionUntilChar(self, event, desc, maxWords):
		firstChar = findall(r'[.]\s|[?]\s|[:]\s|$', desc)[0]
		if (firstChar != "" and len(firstChar) > 0):
			firstCharPos = desc.find(firstChar)
			result = desc[0:firstCharPos]
			genre = self.getCompareGenreWithGenreList(result, ". ")  # Kann ggf. Genre sein, dann raus filtern
			if (genre != None):
				if (genre == result):
					desc = desc.replace(f"{genre}. ", "")  # genre = genre + "."
					firstCharPos = desc.find(firstChar)
					result = desc[0:firstCharPos]
					result = self.getMaxWords(result, maxWords)  # maxWords verwenden
					if (result != None):
						return result
			if (result != None):  # maxWords verwenden
				result = self.getMaxWords(result, maxWords)
				if (result != None):
					return result

	def getMaxWords(self, desc, maxWords):
		wordList = desc.split(" ")
		if (len(wordList) >= maxWords):
			del wordList[maxWords:len(wordList)]
			sep = ' '
			res = sep.join(wordList)
			return res + '...'
		return desc

	def getMaxSubtitleWords(self, type):  # max Anzahl an erlaubten Wörten aus Parameter von Skin lesen
		maxSubtitleWordsParser = r'Subtitle[(](\d+)[)]'
		maxSubtitleWords = search(maxSubtitleWordsParser, type)
		if (maxSubtitleWords):
			return maxSubtitleWords.group(1)
		else:
			maxSubtitleWordsParser = r'SubtitleClean[(](\d+)[)]'
			maxSubtitleWords = search(maxSubtitleWordsParser, type)
			if (maxSubtitleWords):
				return maxSubtitleWords.group(1)
		return "!!! invalid type '%s' !!!" % (type)

	def getEpisodeNum(self, type, event, values, isMovie=None):
		episodeNum = None
		sNum = None
		eNum = None
		if (values != None and len(values) > 0):
			if 'season' in values and 'episode' in values:
				if len(str(values['season']).strip()) > 0 and len(str(values['episode']).strip()) > 0:
					sNum = str(values['season'])
					eNum = str(values['episode'])
				elif len(str(values['episode']).strip()) > 0:
					sNum = '99'
					eNum = str(values['episode'])
		if (sNum == None and eNum == None and event != None):
			desc = self.getFullDescription(event)
			for parser in self.seriesNumParserList:
				extractSeriesNums = search(parser, str(desc))
				if (extractSeriesNums):
					sNum = extractSeriesNums.group(1)
					eNum = extractSeriesNums.group(2)
					break
			if (sNum == None and eNum == None):
				extractEpisode = search(r'\sFolge\s(\d+)', str(desc))
				if (extractEpisode):
					sNum = '99'
					eNum = extractEpisode.group(1).strip()
		if (sNum == None and eNum == None and self.eventName):
			SE = self.findEpisode(self.eventName)
			if SE:
				sNum = SE[0]
				eNum = SE[1]
		if (sNum == None and eNum == None and isMovie):
			SE = self.findEpisode(isMovie)
			if SE:
				sNum = SE[0]
				eNum = SE[1]
		episodeFormat = self.getPrefixParser(type)  # individuelle Formatierung extrahieren
		if (sNum != None and eNum != None):
			if (episodeFormat != None):
				sFormatParser = search(r"[[]([s]+|[s])[]]", episodeFormat)  # Staffel Format parsen
				if (sFormatParser != None):
					sFormat = sFormatParser.group(1)
					sDigits = len(sFormat)
					episodeNum = episodeFormat.replace('[%s]' % (sFormat), sNum.zfill(sDigits)) if str(sNum) != '99' else episodeFormat.replace('[%s]' % (sFormat), '').replace('Staffel', '').replace('S', '').replace(', ', '')
				eFormatParser = search(r"[[]([e]+|[e])[]]", episodeFormat)  # Episoden Format parsen
				if (eFormatParser != None):
					eFormat = eFormatParser.group(1)
					eDigits = len(eFormat)
					episodeNum = episodeNum.replace('[%s]' % (eFormat), eNum.zfill(eDigits)) if str(sNum) != '99' else episodeNum.replace('[%s]' % (eFormat), eNum.zfill(eDigits)).replace('Episode', 'Folge ').replace('E', 'Folge ')
			else:  # Standard falls kein individuelles Format angeben ist
				episodeNum = 'Folge %s' % (eNum.zfill(2)) if str(sNum) == '99' else 'S%sE%s' % (sNum.zfill(2), eNum.zfill(2))
				return episodeNum

	def getFullDescription(self, event):
		if event != None:
			ext_desc = event.getExtendedDescription()
			short_desc = event.getShortDescription()
		if short_desc == "":
			return ext_desc
		elif ext_desc == "":
			return short_desc
		else:
			return "%s\n\n%s" % (short_desc, ext_desc)

	def getPrefixParser(self, type):  # Prefix aus Parameter von Skin lesen
		prefixParser = '.*[(](.*)[)]'
		prefix = search(prefixParser, type)
		if (prefix):
			return prefix.group(1)

	def isNumber(self, inp):
		try:
			val = int(inp)
			return True
		except ValueError:
			try:
				val = float(inp)
				return True
			except ValueError:
				return False

	def getCompareGenreWithGenreList(self, desc, splitChar):
		if (splitChar == None):
			desc = sub('[.,]', '', desc)  # Hinter Genre kann direkt ein Zeichen folgen
			descWordList = desc.split(' ')
		else:
			descWordList = desc.split(splitChar)  # WortList zum Vergleichen erzeugen
		setWordList = set(descWordList)
		fileName = join(aelGlobals.PYTHONPATH, "Components/Converter/AdvancedEventLibrary_Genre.json")
		if 'Folge' in setWordList or 'Staffel' in setWordList or 'Episode' in setWordList:
			return 'Serie'
		if (isfile(fileName)):
			with open(fileName) as file:
				jsonString = str(file.read())
#				jsonString = jsonString.decode("iso-8859-1")  # in Uncode umwandeln, da sonst json parsing nicht möglich
				genreData = loads(jsonString)
				for genre in genreData:  # exakten Treffer suchen
					genre = genre.encode('utf-8')  # in utf-8 zurück wandeln
					setGenre = set([genre])
					for words in setWordList:
						if words == genre:
							return str(genre)
					if setGenre & setWordList:
						return genre

	def getParsedCountryOrYear(self, resultTyp, desc, event):
		if (event == None and desc):
			parser = match(r'^([^.:?; ]+)\s(\d+)$', desc)  # verwendet von getSpecialFormatDescription
			if (parser):
				if (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_COUNTRY):
					return parser.group(1)
				elif (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_YEAR):
					return parser.group(2)
		else:
			if (desc != ""):
				parser = search(r'\s\d+\s[Min.]+\n([^.:?;]+)\s(\d+)', desc)
				if (parser):
					if (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_COUNTRY):
						return parser.group(1)
					elif (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_YEAR):
						return parser.group(2)

				parser = search(r'\s\d+\s[Min.]+\n(\d+)', desc)
				if (parser) and (resultTyp == self.SPECIAL_FORMAT_PARSED_DESCRIPTION_YEAR):
					return parser.group(1)

	def isImageAvailable(self, event, values):
		if getImageFile(self.coverPath, self.eventName):
			return True
		return False

	def isPosterAvailable(self, event, values):
		if getImageFile(self.posterPath, self.eventName):
			return True
		return False

	def findYear(self, desc):
		regexfinder = compile('\d{4}.', MULTILINE | DOTALL)
		ex = regexfinder.findall(desc)
		if ex:
			year = str(ex[0].replace('.', '').replace('\n', '').replace('\xc2', ''))
			if int(year) in range(1950, 2030):
				return year
		regexfinder = compile('\d{4}', MULTILINE | DOTALL)
		ex = regexfinder.findall(desc)
		if ex:
			year = str(ex[0].replace('\n', '').replace('\xc2', ''))
			if int(year) in range(1950, 2030):
				return year

	def findEpisode(self, desc):
		regexfinder = compile('[Ss]\d{2}[Ee]\d{2}', MULTILINE | DOTALL)
		ex = regexfinder.findall(str(desc))
		if ex:
			SE = ex[0].lower().replace('s', '').split('e')
			return (SE[0], SE[1])

	def findCountry(self, desc):
		desc = sub('[.,]', '', str(desc))
		descWordList = desc.replace('\n', ' ').split(' ')
		setWordList = set(descWordList)
		for words in setWordList:
			for k, v in countrys.items():
				for country in v:
					if str(country) == str(words):
						return (str(k), country)
		return (None, None)

	def removeExtension(self, ext):
		ext = ext.replace('.wmv', '').replace('.mpeg2', '').replace('.ts', '').replace('.m2ts', '').replace('.mkv', '').replace('.avi', '').replace('.mpeg', '').replace('.mpg', '').replace('.iso', '').replace('.mp4', '')
		return ext
