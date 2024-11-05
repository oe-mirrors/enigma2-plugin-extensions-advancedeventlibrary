from base64 import b64decode
from urllib.parse import urlencode
from requests import post, exceptions


class Auth:
	def __init__(self, url, apikey="", pin=""):  # get token from server
		from .AdvancedEventLibrary import writeLog
		self.token = ""
		try:
			if not apikey:
				apikey = b64decode("ZmFmMzUxMzEtYTUxYy00NjZjLWJiZGEtNDVmYjZlOTE1NmU1h"[:-1]).decode()
			headers = {"accept": "application/json", "Authorization": f"Bearer {apikey}", "Content-Type": "application/json"}
			response = post(url, headers=headers, json={"apikey": apikey}, timeout=(3.05, 3))
			response.raise_for_status()
			status = response.status_code
			if status != 200:
				writeLog(f"API server access ERROR, response code: {status} - {response}")
				return
			jsondict = response.json()
			if jsondict and jsondict.get("status", "failure") == "success":
				self.token = jsondict.get("data", {}).get("token", "")
			else:
				self.token = ""
				writeLog(f"Response message from server: {jsondict.get('message', '')}")
		except exceptions.RequestException as errmsg:
			writeLog(f"ERROR in module 'getAPIdata': {errmsg}")

	def getToken(self):
		return self.token


class Request:
	def __init__(self, token):  # get data from server
		from .AdvancedEventLibrary import getAPIdata, writeLog
		self.getAPIdata = getAPIdata
		self.writeLog = writeLog
		self.token = token

	def makeRequest(self, url):
		errmsg, response = self.getAPIdata(url, headers={"Authorization": f"Bearer {self.token}"})
		if errmsg:
			self.writeLog(f"API download error in module 'TVDbApiV4: makeRequest': {errmsg}")
		if response:
			data = response.get("data", "")
			if data and response.get("status", "failure") == "success":
				return data


class Url:
	def __init__(self):

		self.baseUrl = b64decode(b"aHR0cHM6Ly9hcGk0LnRoZXR2ZGIuY29tL3Y03"[:-1]).decode()

	def loginUrl(self):
		return f"{self.baseUrl}/login"

	def artworkStatusUrl(self):
		return f"{self.baseUrl}/artwork/statuses"

	def artworkTypesUrl(self):
		return f"{self.baseUrl}/artwork/types"

	def artworkUrl(self, id, extended=False):
		url = f"{self.baseUrl}/artwork/{id}"
		if extended:
			url = f"{url}/extended"
		return url

	def awardsUrl(self, page=1):
		page = max(page, 0)
		url = f"{self.baseUrl}/awards?page={page}"
		return url

	def awardUrl(self, id, extended=False):
		url = f"{self.baseUrl}/awards/{id}"
		if extended:
			url = f"{url}/extended"
		return url

	def awardsCategoriesUrl(self):
		url = f"{self.baseUrl}/awards/categories"
		return url

	def awardCategoryUrl(self, id, extended=False):
		url = f"{self.baseUrl}/awards/categories/{id}"
		if extended:
			url = f"{url}/extended"
		return url

	def contentRatingsUrl(self):
		url = f"{self.baseUrl}/content/ratings"
		return url

	def countriesUrl(self):
		url = f"{self.baseUrl}/countries"
		return url

	def companiesUrl(self, page=0):
		url = f"{self.baseUrl}/companies?page={page}"
		return url

	def companyUrl(self, id):
		url = f"{self.baseUrl}/companies/{id}"
		return url

	def allSeriesUrl(self, page=0):
		url = f"{self.baseUrl}/series?page={page}"
		return url

	def seriesUrl(self, id, extended=False):
		url = f"{self.baseUrl}/series/{id}"
		if extended:
			url = f"{url}/extended?meta=translations"
		return url

	def seriesEpisodesUrl(self, id, seasonType, page=0, lang=None):
		lang = f"/{lang}" if lang else ""
		url = f"{self.baseUrl}/series/{id}/episodes/{seasonType}{lang}?page={page}"
		return url

	def seriesTranslationUrl(self, id, lang):
		url = f"{self.baseUrl}/series/{id}/translations/{lang}"
		return url

	def movieTranslationUrl(self, id, lang):
		url = f"{self.baseUrl}/movies/{id}/translations/{lang}"
		return url

	def moviesUrl(self, page=0):
		url = f"{self.baseUrl}/movies?page={page}"
		return url

	def movieUrl(self, id, extended=False):
		url = f"{self.baseUrl}/movies/{id}"
		if extended:
			url = f"{url}/extended?meta=translations"
		return url

	def allSeasonsUrl(self, page=0):
		url = f"{self.baseUrl}/seasons?page={page}"
		return url

	def seasonUrl(self, id, extended=False):
		url = f"{self.baseUrl}/seasons/{id}"
		if extended:
			url = f"{url}/extended"
		return url

	def seasonTypesUrl(self):
		url = f"{self.baseUrl}/seasons/types"
		return url

	def seasonTranslationUrl(self, id, lang):
		url = f"{self.baseUrl}/seasons/{id}/translations/{lang}"
		return url

	def episodeUrl(self, id, extended=False):
		url = f"{self.baseUrl}/episodes/{id}"
		if extended:
			url = f"{url}/extended?meta=translations"
		return url

	def episodeTranslationUrl(self, id, lang):
		url = f"{self.baseUrl}/episodes/{id}/translations/{lang}"
		return url

	def gendersUrl(self):
		url = f"{self.baseUrl}/genders"
		return url

	def genresUrl(self):
		url = f"{self.baseUrl}/genres"
		return url

	def genreUrl(self, id):
		url = f"{self.baseUrl}/genres/{id}"
		return url

	def languagesUrl(self):
		url = f"{self.baseUrl}/languages"
		return url

	def personUrl(self, id, extended=False):
		url = f"{self.baseUrl}/people/{id}"
		if extended:
			url = f"{url}/extended"
		return url

	def characterUrl(self, id):
		url = f"{self.baseUrl}/characters/{id}"
		return url

	def peopleTypesUrl(self):
		url = f"{self.baseUrl}/people/types"
		return url

	def sourceTypesUrl(self):
		url = f"{self.baseUrl}/sources/types"
		return url

	def updatesUrl(self, since=0):  # https://api4.thetvdb.com/v4/updates?since=1631049140&type=series&action=update&page=0
		url = f"{self.baseUrl}/updates?since={since}"
		return url

	def tagOptionsUrl(self, page=0):
		url = f"{self.baseUrl}/tags/options?page={page}"
		return url

	def tagOptionUrl(self, id):
		url = f"{self.baseUrl}/tags/options/{id}"
		return url

	def listsUrl(self, page=0):
		url = f"{self.baseUrl}/lists?page={page}"
		return url

	def listUrl(self, id, extended=False):
		url = f"{self.baseUrl}/lists/{id}"
		if extended:
			url = f"{url}/extended"
		return url

	def searchUrl(self, query, filters):
		filters["query"] = query
		url = f"{self.baseUrl}/search?{urlencode(filters)}"
		return url


class TVDB:
	def __init__(self, apikey="", pin=""):
		self.url = Url()
		self.auth = Auth(self.url.loginUrl(), apikey, pin)
		self.token = self.auth.getToken()
		self.request = Request(self.token)

	def getLoginState(self):
		return True if self.token else False

	def getArtworkStatuses(self):  # -> list:
		"""Returns a list of artwork statuses"""
		url = self.url.artworkStatusUrl()
		return self.request.makeRequest(url)

	def getArtworkTypes(self):  # -> list:
		"""Returns a list of artwork types"""
		url = self.url.artworkTypesUrl()
		return self.request.makeRequest(url)

	def getArtwork(self, id=0):  # -> dict:
		"""Returns an artwork dictionary"""
		url = self.url.artworkUrl(id)
		return self.request.makeRequest(url)

	def getArtworkExtended(self, id=0):  # -> dict:
		"""Returns an artwork extended dictionary"""
		url = self.url.artworkUrl(id, True)
		return self.request.makeRequest(url)

	def getAllAwards(self):  # -> list:
		"""Returns a list of awards"""
		url = self.url.awardsUrl()
		return self.request.makeRequest(url)

	def getAward(self, id=0):  # -> dict:
		"""Returns an award dictionary"""
		url = self.url.awardUrl(id, False)
		return self.request.makeRequest(url)

	def getAwardExtended(self, id=0):  # -> dict:
		"""Returns an award extended dictionary"""
		url = self.url.awardUrl(id, True)
		return self.request.makeRequest(url)

	def getAllAwardCategories(self):  # -> list:
		"""Returns a list of award categories"""
		url = self.url.awardsCategoriesUrl()
		return self.request.makeRequest(url)

	def getAwardCategory(self, id=0):  # -> dict:
		"""Returns an award category dictionary"""
		url = self.url.awardCategoryUrl(id, False)
		return self.request.makeRequest(url)

	def getAwardCategoryExtended(self, id=0):  # -> dict:
		"""Returns an award category extended dictionary"""
		url = self.url.awardCategoryUrl(id, True)
		return self.request.makeRequest(url)

	def getContentRatings(self):  # -> list:
		"""Returns a list of content ratings"""
		url = self.url.contentRatingsUrl()
		return self.request.makeRequest(url)

	def getCountries(self):  # -> list:
		"""Returns a list of countries"""
		url = self.url.countriesUrl()
		return self.request.makeRequest(url)

	def getAllCompanies(self, page=0):  # -> list:
		"""Returns a list of companies"""
		url = self.url.companiesUrl(page)
		return self.request.makeRequest(url)

	def getCompany(self, id=0):  # -> dict:
		"""Returns a company dictionary"""
		url = self.url.companyUrl(id)
		return self.request.makeRequest(url)

	def getAllSeries(self, page=0):  # -> list:
		"""Returns a list of series"""
		url = self.url.allSeriesUrl(page)
		return self.request.makeRequest(url)

	def getSeries(self, id=0):  # -> dict:
		"""Returns a series dictionary"""
		url = self.url.seriesUrl(id, False)
		return self.request.makeRequest(url)

	def getSeriesExtended(self, id=0):  # -> dict:
		"""Returns a series extended dictionary"""
		url = self.url.seriesUrl(id, True)
		return self.request.makeRequest(url)

	def getSeriesEpisodes(self, id, seasonType="official", page=0, lang="deu"):  # -> dict:
		"""Returns a series episodes dictionary"""
		url = self.url.seriesEpisodesUrl(id, seasonType, page, lang)
		return self.request.makeRequest(url)

	def getSeriesTranslation(self, id, lang="deu"):  # -> dict:
		"""Returns a series translation dictionary"""
		url = self.url.seriesTranslationUrl(id, lang)
		return self.request.makeRequest(url)

	def getAllMovies(self, page=0):  # -> list:
		"""Returns a list of movies"""
		url = self.url.moviesUrl(page)
		return self.request.makeRequest(url)

	def getMovie(self, id=0):  # -> dict:
		"""Returns a movie dictionary"""
		url = self.url.movieUrl(id, False)
		return self.request.makeRequest(url)

	def getMovieExtended(self, id=0):  # -> dict:
		"""Returns a movie extended dictionary"""
		url = self.url.movieUrl(id, True)
		return self.request.makeRequest(url)

	def getMovieTranslation(self, id=0, lang="deu"):  # -> dict:
		"""Returns a movie translation dictionary"""
		url = self.url.movieTranslationUrl(id, lang)
		return self.request.makeRequest(url)

	def getAllSeasons(self, page=0):  # -> list:
		"""Returns a list of seasons"""
		url = self.url.allSeasonsUrl(page)
		return self.request.makeRequest(url)

	def getSeason(self, id=0):  # -> dict:
		"""Returns a season dictionary"""
		url = self.url.seasonUrl(id, False)
		return self.request.makeRequest(url)

	def getSeasonExtended(self, id=0):  # -> dict:
		"""Returns a season extended dictionary"""
		url = self.url.seasonUrl(id, True)
		return self.request.makeRequest(url)

	def getseasonTypes(self):  # -> list:
		"""Returns a list of season types"""
		url = self.url.seasonTypesUrl()
		return self.request.makeRequest(url)

	def getSeasonTranslation(self, id=0, lang="deu"):  # -> dict:
		"""Returns a seasons translation dictionary"""
		url = self.url.seasonTranslationUrl(id, lang)
		return self.request.makeRequest(url)

	def getEpisode(self, id=0):  # -> dict:
		"""Returns an episode dictionary"""
		url = self.url.episodeUrl(id, False)
		return self.request.makeRequest(url)

	def getEpisodesTranslation(self, id=0, lang="deu"):  # -> dict:
		"""Returns an episode translation dictionary"""
		url = self.url.episodeTranslationUrl(id, lang)
		return self.request.makeRequest(url)

	def getEpisodeTxtended(self, id=0):  # -> dict:
		"""Returns an episode extended dictionary"""
		url = self.url.episodeUrl(id, True)
		return self.request.makeRequest(url)

	def getAllGenders(self):  # -> list:
		"""Returns a list of genders"""
		url = self.url.gendersUrl()
		return self.request.makeRequest(url)

	def getAllGenres(self):  # -> list:
		"""Returns a list of genres"""
		url = self.url.genresUrl()
		return self.request.makeRequest(url)

	def getGenre(self, id=0):  # -> dict:
		"""Returns a genres dictionary"""
		url = self.url.genreUrl(id)
		return self.request.makeRequest(url)

	def getAllLanguages(self):  # -> list:
		"""Returns a list of languages"""
		url = self.url.languagesUrl()
		return self.request.makeRequest(url)

	def getPerson(self, id=0):  # -> dict:
		"""Returns a person dictionary"""
		url = self.url.personUrl(id, False)
		return self.request.makeRequest(url)

	def getPersonExtended(self, id=0):  # -> dict:
		"""Returns a person extended dictionary"""
		url = self.url.personUrl(id, True)
		return self.request.makeRequest(url)

	def getCharacter(self, id=0):  # -> dict:
		"""Returns a character dictionary"""
		url = self.url.characterUrl(id)
		return self.request.makeRequest(url)

	def getAllPeopleTypes(self):  # -> list:
		"""Returns a list of people types"""
		url = self.url.peopleTypesUrl()
		return self.request.makeRequest(url)

	def getAllSourcetypes(self):  # -> list:
		"""Returns a list of sourcetypes"""
		url = self.url.sourceTypesUrl()
		return self.request.makeRequest(url)

	def getUpdates(self, since=0):  # -> list:
		"""Returns a list of updates"""
		url = self.url.updatesUrl(since)
		return self.request.makeRequest(url)

	def getAllTagOptions(self, page=0):  # -> list:
		"""Returns a list of tag options"""
		url = self.url.tagOptionsUrl(page)
		return self.request.makeRequest(url)

	def getTagOption(self, id=0):  # -> dict:
		"""Returns a tag option dictionary"""
		url = self.url.tagOptionUrl(id)
		return self.request.makeRequest(url)

	def getAllLists(self, page=0):  # -> dict:
		url = self.url.listsUrl(page)
		return self.request.makeRequest(url)

	def getList(self, id):  # -> dict:
		url = self.url.listUrl(id)
		return self.request.makeRequest(url)

	def getlistExtended(self, id):  # -> dict:
		url = self.url.listUrl(id, True)
		return self.request.makeRequest(url)

	def search(self, query, **kwargs):  # -> list:
		"""Returns a list of search results"""
		url = self.url.searchUrl(query, kwargs)
		return self.request.makeRequest(url)
