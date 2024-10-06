from base64 import b64decode
from urllib.request import Request as uRequest, urlopen
from urllib.parse import urlencode
from json import dumps, load


class Auth:
	def __init__(self, url, pin=""):
		loginInfo = {"apikey": b64decode("N2UwYTVjN2EtNTQ0NS00YWU2LTg4OTItOGZlYWQyYzc2ZTI3Z"[:-1]).decode()}
		if pin != "":
			loginInfo["pin"] = pin
		self.token = None
		loginInfoBytes = dumps(loginInfo, indent=2).encode('utf-8')
		req = uRequest(url, data=loginInfoBytes)
		req.add_header("Content-Type", "application/json")
		response = urlopen(req, data=loginInfoBytes, timeout=5)
		if response:
			res = load(response)
			if "data" in res:
				if "token" in res["data"] and res["data"]["token"] is not None:
					self.token = res["data"]["token"]

	def get_token(self):
		return self.token


class Request:
	def __init__(self, auth_token):
		self.auth_token = auth_token

	def make_request(self, url):
		req = uRequest(url)
		req.add_header("Authorization", f"Bearer {self.auth_token}")
		response = urlopen(req, timeout=5)
		if response:
			res = load(response)
			data = res.get("data", None)
			if data and res.get('status', 'failure') != 'failure':
				return data


class Url:
	def __init__(self):
		self.base_url = "https://api4.thetvdb.com/v4"

	def login_url(self):
		return f"{self.base_url}/login"

	def artwork_status_url(self):
		return f"{self.base_url}/artwork/statuses"

	def artwork_types_url(self):
		return f"{self.base_url}/artwork/types"

	def artwork_url(self, id, extended=False):
		url = f"{self.base_url}/artwork/{id}"
		if extended:
			url = f"{url}/extended"
		return url

	def awards_url(self, page):
		if page < 0:
			page = 0
		url = f"{self.base_url}/awards?page={page}"
		return url

	def award_url(self, id, extended=False):
		url = f"{self.base_url}/awards/{id}"
		if extended:
			url = f"{url}/extended"
		return url

	def awards_categories_url(self):
		url = f"{self.base_url}/awards/categories"
		return url

	def award_category_url(self, id, extended=False):
		url = f"{self.base_url}/awards/categories/{id}"
		if extended:
			url = f"{url}/extended"
		return url

	def content_ratings_url(self):
		url = f"{self.base_url}/content/ratings"
		return url

	def countries_url(self):
		url = f"{self.base_url}/countries"
		return url

	def companies_url(self, page=0):
		url = f"{self.base_url}/companies?page={page}"
		return url

	def company_url(self, id):
		url = f"{self.base_url}/companies/{id}"
		return url

	def all_series_url(self, page=0):
		url = f"{self.base_url}/series?page={page}"
		return url

	def series_url(self, id, extended=False):
		url = f"{self.base_url}/series/{id}"
		if extended:
			url = f"{url}/extended?meta=translations"
		return url

	def series_episodes_url(self, id, season_type, page=0, lang=None):
		lang = '/' + lang if lang else ''
		url = f"{self.base_url}/series/{id}/episodes/{season_type}{lang}?page={page}"
		return url

	def series_translation_url(self, id, lang):
		url = f"{self.base_url}/series/{id}/translations/{lang}"
		return url

	def movie_translation_url(self, id, lang):
		url = f"{self.base_url}/movies/{id}/translations/{lang}"
		return url

	def movies_url(self, page=0):
		url = f"{self.base_url}/movies?page={page}"
		return url

	def movie_url(self, id, extended=False):
		url = f"{self.base_url}/movies/{id}"
		if extended:
			url = f"{url}/extended?meta=translations"
		return url

	def all_seasons_url(self, page=0):
		url = f"{self.base_url}/seasons?page={page}"
		return url

	def season_url(self, id, extended=False):
		url = f"{self.base_url}/seasons/{id}"
		if extended:
			url = f"{url}/extended"
		return url

	def season_types_url(self):
		url = f"{self.base_url}/seasons/types"
		return url

	def season_translation_url(self, id, lang):
		url = f"{self.base_url}/seasons/{id}/translations/{lang}"
		return url

	def episode_url(self, id, extended=False):
		url = f"{self.base_url}/episodes/{id}"
		if extended:
			url = f"{url}/extended?meta=translations"
		return url

	def genders_url(self):
		url = f"{self.base_url}/genders"
		return url

	def genres_url(self):
		url = f"{self.base_url}/genres"
		return url

	def genre_url(self, id):
		url = f"{self.base_url}/genres/{id}"
		return url

	def languages_url(self):
		url = f"{self.base_url}/languages"
		return url

	def person_url(self, id, extended=False):
		url = f"{self.base_url}/people/{id}"
		if extended:
			url = f"{url}/extended"
		return url

	def character_url(self, id):
		url = f"{self.base_url}/characters/{id}"
		return url

	def people_types_url(self):
		url = f"{self.base_url}/people/types"
		return url

	def source_types_url(self):
		url = f"{self.base_url}/sources/types"
		return url

	def updates_url(self, since=0, typ="series"):  # https://api4.thetvdb.com/v4/updates?since=1631049140&type=series&action=update&page=0
		url = f"{self.base_url}/updates?since={since}"
		return url

	def tag_options_url(self, page=0):
		url = f"{self.base_url}/tags/options?page={page}"
		return url

	def tag_option_url(self, id):
		url = f"{self.base_url}/tags/options/{id}"
		return url

	def lists_url(self, page=0):
		url = f"{self.base_url}/lists?page={page}"
		return url

	def list_url(self, id, extended=False):
		url = f"{self.base_url}/lists/{id}"
		if extended:
			url = f"{url}/extended"
		return url

	def search_url(self, query, filters):
		filters["query"] = query
		url = f"{self.base_url}/search?{urlencode(filters)}"
		return url


class TVDB:
	def __init__(self, pin=""):
		self.url = Url()
		login_url = self.url.login_url()
		self.auth = Auth(login_url, pin)
		self.auth_token = self.auth.get_token()
		self.request = Request(self.auth_token)

	def get_login_state(self):
		return True if self.auth_token else False

	def get_artwork_statuses(self):  # -> list:
		"""Returns a list of artwork statuses"""
		url = self.url.artwork_status_url()
		return self.request.make_request(url)

	def get_artwork_types(self):  # -> list:
		"""Returns a list of artwork types"""
		url = self.url.artwork_types_url()
		return self.request.make_request(url)

	def get_artwork(self, id=0):  # -> dict:
		"""Returns an artwork dictionary"""
		url = self.url.artwork_url(id)
		return self.request.make_request(url)

	def get_artwork_extended(self, id=0):  # -> dict:
		"""Returns an artwork extended dictionary"""
		url = self.url.artwork_url(id, True)
		return self.request.make_request(url)

	def get_all_awards(self):  # -> list:
		"""Returns a list of awards"""
		url = self.url.awards_url()
		return self.request.make_request(url)

	def get_award(self, id=0):  # -> dict:
		"""Returns an award dictionary"""
		url = self.url.award_url(id, False)
		return self.request.make_request(url)

	def get_award_extended(self, id=0):  # -> dict:
		"""Returns an award extended dictionary"""
		url = self.url.award_url(id, True)
		return self.request.make_request(url)

	def get_all_award_categories(self):  # -> list:
		"""Returns a list of award categories"""
		url = self.url.awards_categories_url()
		return self.request.make_request(url)

	def get_award_category(self, id=0):  # -> dict:
		"""Returns an award category dictionary"""
		url = self.url.award_category_url(id, False)
		return self.request.make_request(url)

	def get_award_category_extended(self, id=0):  # -> dict:
		"""Returns an award category extended dictionary"""
		url = self.url.award_category_url(id, True)
		return self.request.make_request(url)

	def get_content_ratings(self):  # -> list:
		"""Returns a list of content ratings"""
		url = self.url.content_ratings_url()
		return self.request.make_request(url)

	def get_countries(self):  # -> list:
		"""Returns a list of countries"""
		url = self.url.countries_url()
		return self.request.make_request(url)

	def get_all_companies(self, page=0):  # -> list:
		"""Returns a list of companies"""
		url = self.url.companies_url(page)
		return self.request.make_request(url)

	def get_company(self, id=0):  # -> dict:
		"""Returns a company dictionary"""
		url = self.url.company_url(id)
		return self.request.make_request(url)

	def get_all_series(self, page=0):  # -> list:
		"""Returns a list of series"""
		url = self.url.all_series_url(page)
		return self.request.make_request(url)

	def get_series(self, id=0):  # -> dict:
		"""Returns a series dictionary"""
		url = self.url.series_url(id, False)
		return self.request.make_request(url)

	def get_series_extended(self, id=0):  # -> dict:
		"""Returns a series extended dictionary"""
		url = self.url.series_url(id, True)
		return self.request.make_request(url)

	def get_series_episodes(self, id, season_type="official", page=0, lang='deu'):  # -> dict:
		"""Returns a series episodes dictionary"""
		url = self.url.series_episodes_url(id, season_type, page, lang)
		return self.request.make_request(url)

	def get_series_translation(self, id, lang='deu'):  # -> dict:
		"""Returns a series translation dictionary"""
		url = self.url.series_translation_url(id, lang)
		return self.request.make_request(url)

	def get_all_movies(self, page=0):  # -> list:
		"""Returns a list of movies"""
		url = self.url.movies_url(page)
		return self.request.make_request(url)

	def get_movie(self, id=0):  # -> dict:
		"""Returns a movie dictionary"""
		url = self.url.movie_url(id, False)
		return self.request.make_request(url)

	def get_movie_extended(self, id=0):  # -> dict:
		"""Returns a movie extended dictionary"""
		url = self.url.movie_url(id, True)
		return self.request.make_request(url)

	def get_movie_translation(self, id=0, lang="deu"):  # -> dict:
		"""Returns a movie translation dictionary"""
		url = self.url.movie_translation_url(id, lang)
		return self.request.make_request(url)

	def get_all_seasons(self, page=0):  # -> list:
		"""Returns a list of seasons"""
		url = self.url.all_seasons_url(page)
		return self.request.make_request(url)

	def get_season(self, id=0):  # -> dict:
		"""Returns a season dictionary"""
		url = self.url.season_url(id, False)
		return self.request.make_request(url)

	def get_season_extended(self, id=0):  # -> dict:
		"""Returns a season extended dictionary"""
		url = self.url.season_url(id, True)
		return self.request.make_request(url)

	def get_season_types(self):  # -> list:
		"""Returns a list of season types"""
		url = self.url.season_types_url()
		return self.request.make_request(url)

	def get_season_translation(self, id=0, lang="deu"):  # -> dict:
		"""Returns a seasons translation dictionary"""
		url = self.url.season_translation_url(id, lang)
		return self.request.make_request(url)

	def get_episode(self, id=0):  # -> dict:
		"""Returns an episode dictionary"""
		url = self.url.episode_url(id, False)
		return self.request.make_request(url)

	def get_episodes_translation(self, id=0, lang="deu"):  # -> dict:
		"""Returns an episode translation dictionary"""
		url = self.url.episode_translation_url(id, lang)
		return self.request.make_request(url)

	def get_episode_extended(self, id=0):  # -> dict:
		"""Returns an episode extended dictionary"""
		url = self.url.episode_url(id, True)
		return self.request.make_request(url)

	def get_all_genders(self):  # -> list:
		"""Returns a list of genders"""
		url = self.url.genders_url()
		return self.request.make_request(url)

	def get_all_genres(self):  # -> list:
		"""Returns a list of genres"""
		url = self.url.genres_url()
		return self.request.make_request(url)

	def get_genre(self, id=0):  # -> dict:
		"""Returns a genres dictionary"""
		url = self.url.genre_url(id, False)
		return self.request.make_request(url)

	def get_all_languages(self):  # -> list:
		"""Returns a list of languages"""
		url = self.url.languages_url()
		return self.request.make_request(url)

	def get_person(self, id=0):  # -> dict:
		"""Returns a person dictionary"""
		url = self.url.person_url(id, False)
		return self.request.make_request(url)

	def get_person_extended(self, id=0):  # -> dict:
		"""Returns a person extended dictionary"""
		url = self.url.person_url(id, True)
		return self.request.make_request(url)

	def get_character(self, id=0):  # -> dict:
		"""Returns a character dictionary"""
		url = self.url.character_url(id)
		return self.request.make_request(url)

	def get_all_people_types(self):  # -> list:
		"""Returns a list of people types"""
		url = self.url.people_types_url()
		return self.request.make_request(url)

	def get_all_sourcetypes(self):  # -> list:
		"""Returns a list of sourcetypes"""
		url = self.url.source_types_url()
		return self.request.make_request(url)

	def get_updates(self, since=0, typ="series"):  # -> list:
		"""Returns a list of updates"""
		url = self.url.updates_url(since, typ)
		return self.request.make_request(url)

	def get_all_tag_options(self, page=0):  # -> list:
		"""Returns a list of tag options"""
		url = self.url.tag_options_url(page)
		return self.request.make_request(url)

	def get_tag_option(self, id=0):  # -> dict:
		"""Returns a tag option dictionary"""
		url = self.url.tag_option_url(id)
		return self.request.make_request(url)

	def get_all_lists(self, page=0):  # -> dict:
		url = self.url.lists_url(page)
		return self.request.make_request(url)

	def get_list(self, id):  # -> dict:
		url = self.url.list_url(id)
		return self.request.make_request(url)

	def get_list_extended(self, id):  # -> dict:
		url = self.url.list_url(id, True)
		return self.request.make_request(url)

	def search(self, query, **kwargs):  # -> list:
		"""Returns a list of search results"""
		url = self.url.search_url(query, kwargs)
		return self.request.make_request(url)
