from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import urljoin
import json
import re
from enum import Enum

from bs4 import BeautifulSoup
from pydantic import BaseModel


MOVIES_ROOT = Path("/home/riju/websites/yts/www.yts-official.cc/movies")
TORRENT_ROOT = Path("/home/riju/websites/yts/www.yts-official.cc/torrent")
POSTER_ROOT = Path("/home/riju/websites/yts/www.yts-official.cc/movies/poster")


class Quality(str, Enum):
	P2160 = "2160p"
	P1080 = "1080p"
	P720 = "720p"
	P480 = "480p"
	P3D = "3D"


class ReleaseType(str, Enum):
	WEB = "WEB"
	BLURAY = "BluRay"
	DVDRIP = "DVDRip"
	HDRIP = "HDRip"
	WEBDL = "WEB-DL"
	WEBRIP = "WEBRip"
	UNKNOWN = "Unknown"


class Genre(str, Enum):
	ACTION = "Action"
	ADVENTURE = "Adventure"
	ANIMATION = "Animation"
	BIOGRAPHY = "Biography"
	COMEDY = "Comedy"
	CRIME = "Crime"
	DOCUMENTARY = "Documentary"
	DRAMA = "Drama"
	FAMILY = "Family"
	FANTASY = "Fantasy"
	FILM_NOIR = "Film-Noir"
	HISTORY = "History"
	HORROR = "Horror"
	MUSICAL = "Musical"
	MYSTERY = "Mystery"
	ROMATIC = "Romance"
	SCI_FI = "Sci-Fi"
	SPORT = "Sport"
	THRILLER = "Thriller"
	VAR = "Var"
	WAR = "War"
	WESTERN = "Western"
	UNKNOWN = "Unknown"


class Poster(BaseModel):
	url: str
	path: Optional[Path]


class MagnetLink(BaseModel):
	quality: Optional[Quality]
	type: Optional[ReleaseType]
	url: str


class TorrentFile(BaseModel):
	quality: Optional[Quality]
	type: Optional[ReleaseType]
	url: str
	path: Optional[Path]


class Media(BaseModel):
	slug: str
	title: Optional[str]
	year: Optional[int]
	genres: List[Genre]
	imdb_link: Optional[str]
	imdb_rating: Optional[float]
	synopsis: Optional[str]
	director: Optional[str]
	cast: List[str]
	poster: Optional[Poster]
	magnet_links: List[MagnetLink]
	torrent_files: List[TorrentFile]


def unique_preserve_order(items: Iterable[str]) -> List[str]:
	seen = set()
	ordered: List[str] = []
	for item in items:
		if item in seen:
			continue
		seen.add(item)
		ordered.append(item)
	return ordered


def unique_by_url(items: Iterable[BaseModel]) -> List[BaseModel]:
	seen = set()
	ordered: List[BaseModel] = []
	for item in items:
		url = getattr(item, "url", None)
		if not url or url in seen:
			continue
		seen.add(url)
		ordered.append(item)
	return ordered


def parse_year(text: Optional[str]) -> Optional[int]:
	if not text:
		return None
	match = re.search(r"\b(\d{4})\b", text)
	if not match:
		return None
	try:
		return int(match.group(1))
	except ValueError:
		return None


QUALITY_PATTERN = re.compile(r"(\d{3,4}p|3D)", re.IGNORECASE)


def normalize_quality(text: Optional[str]) -> Optional[Quality]:
	if not text:
		return None
	match = QUALITY_PATTERN.search(text)
	if not match:
		return None
	value = match.group(1).upper()
	value = value.replace("P", "p") if value != "3D" else "3D"
	mapping = {q.value: q for q in Quality}
	return mapping.get(value)


TYPE_CLEAN_PATTERN = re.compile(r"[^A-Za-z]")


def normalize_type(text: Optional[str]) -> Optional[ReleaseType]:
	if not text:
		return None
	clean = TYPE_CLEAN_PATTERN.sub("", text).upper()
	mapping = {
		"WEB": ReleaseType.WEB,
		"BLURAY": ReleaseType.BLURAY,
		"DVDRIP": ReleaseType.DVDRIP,
		"HDRIP": ReleaseType.HDRIP,
		"WEBDL": ReleaseType.WEBDL,
		"WEBRIP": ReleaseType.WEBRIP,
	}
	return mapping.get(clean, ReleaseType.UNKNOWN)


def normalize_genre(text: Optional[str]) -> Optional[Genre]:
	if not text:
		return None
	clean = text.strip().upper()
	mapping = {g.value.upper(): g for g in Genre}
	return mapping.get(clean, Genre.UNKNOWN)


def resolve_torrent_path(torrent_href: str) -> Optional[Path]:
	"""Check if torrent file exists on disk and return its path."""
	from urllib.parse import unquote
	filename = torrent_href.split("/")[-1]
	filename = unquote(filename)
	torrent_path = TORRENT_ROOT / filename
	return torrent_path if torrent_path.is_file() else None


def resolve_poster_path(poster_href: str) -> Optional[Path]:
	"""Check if poster file exists on disk and return its path."""
	from urllib.parse import unquote
	filename = poster_href.split("/")[-1]
	filename = unquote(filename)
	poster_path = POSTER_ROOT / filename
	return poster_path if poster_path.is_file() else None


def parse_downloads(soup: BeautifulSoup, base_url: str) -> tuple[List[MagnetLink], List[TorrentFile]]:
	magnet_objects: List[MagnetLink] = []
	torrent_objects: List[TorrentFile] = []

	for modal in soup.select(".modal-torrent"):
		quality_span = modal.select_one(".modal-quality span") or modal.select_one(".modal-quality")
		quality = normalize_quality(quality_span.get_text(strip=True) if quality_span else None)
		type_text = modal.select_one("p.quality-size")
		type_value = normalize_type(type_text.get_text(strip=True) if type_text else None) or ReleaseType.UNKNOWN

		magnet_anchor = modal.select_one("a[href^='magnet:']")
		if magnet_anchor and magnet_anchor.get("href"):
			magnet_objects.append(MagnetLink(quality=quality, type=type_value, url=magnet_anchor.get("href")))

		torrent_anchor = modal.select_one("a.download-torrent[href]")
		if torrent_anchor and torrent_anchor.get("href"):
			torrent_href = torrent_anchor.get("href")
			torrent_url = urljoin(base_url, torrent_href)
			torrent_path = resolve_torrent_path(torrent_href)
			torrent_objects.append(TorrentFile(quality=quality, type=type_value, url=torrent_url, path=torrent_path))

	if not magnet_objects:
		fallback_magnets = [a.get("href") for a in soup.select("a[href^='magnet:']") if a.get("href")]
		magnet_objects = [MagnetLink(quality=None, type=ReleaseType.UNKNOWN, url=url) for url in unique_preserve_order(fallback_magnets)]

	if not torrent_objects:
		fallback_torrents = [a.get("href") for a in soup.select("a.download-torrent[href]") if a.get("href")]
		torrent_objects = [TorrentFile(quality=None, type=ReleaseType.UNKNOWN, url=urljoin(base_url, href), path=resolve_torrent_path(href)) for href in unique_preserve_order(fallback_torrents)]

	return unique_by_url(magnet_objects), unique_by_url(torrent_objects)


def parse_media(index_path: Path) -> Media:
	html = index_path.read_text(encoding="utf-8", errors="ignore")
	soup = BeautifulSoup(html, "html.parser")

	slug = index_path.parent.name
	base_url = f"https://www.yts-official.cc/movies/{slug}/"

	title_tag = soup.select_one("#movie-content h1") or soup.find("h1", attrs={"itemprop": "name"})
	title = title_tag.get_text(strip=True) if title_tag else None

	year_tag = None
	if title_tag and title_tag.find_next_sibling("h2"):
		year_tag = title_tag.find_next_sibling("h2")
	if not year_tag:
		year_tag = soup.find("h2")
	year = parse_year(year_tag.get_text(strip=True) if year_tag else None)

	# Extract genres from second h2 (after year)
	genres: List[Genre] = []
	genre_tag = title_tag.find_next_sibling("h2").find_next_sibling("h2") if title_tag else None
	if genre_tag:
		genre_text = genre_tag.get_text(strip=True)
		genres = [normalize_genre(g.strip()) or Genre.UNKNOWN for g in genre_text.split("/") if g.strip()]

	imdb_anchor = soup.find("a", href=re.compile(r"imdb\.com/title"))
	imdb_link = imdb_anchor.get("href") if imdb_anchor else None

	# Extract IMDb rating
	imdb_rating = None
	rating_span = soup.find("span", attrs={"itemprop": "ratingValue"})
	if rating_span:
		try:
			imdb_rating = float(rating_span.get_text(strip=True))
		except (ValueError, AttributeError):
			pass

	# Extract synopsis
	synopsis = None
	synopsis_div = soup.find("div", id="synopsis")
	if synopsis_div:
		synopsis_p = synopsis_div.find("p", class_="hidden-xs")
		if not synopsis_p:
			synopsis_p = synopsis_div.find("p")
		if synopsis_p:
			synopsis = synopsis_p.get_text(strip=True)

	# Extract director
	director = None
	director_div = soup.find("div", class_="directors")
	if director_div:
		director_span = director_div.find("span", attrs={"itemprop": "name"})
		if director_span:
			director = director_span.get_text(strip=True)

	# Extract cast
	cast = []
	cast_div = soup.find("div", class_="actors")
	if cast_div:
		cast_spans = cast_div.find_all("span", attrs={"itemprop": "name"})
		cast = [span.get_text(strip=True) for span in cast_spans if span.get_text(strip=True)]

	poster_img = soup.select_one("#movie-poster img[itemprop='image']") or soup.select_one("#movie-poster img")
	poster_src = poster_img.get("src") if poster_img else None
	poster = None
	if poster_src:
		poster_url = urljoin(base_url, poster_src)
		poster_path = resolve_poster_path(poster_src)
		poster = Poster(url=poster_url, path=poster_path)

	magnet_links, torrent_files = parse_downloads(soup, base_url)

	return Media(
		slug=slug,
		title=title,
		year=year,
		genres=genres,
		imdb_link=imdb_link,
		imdb_rating=imdb_rating,
		synopsis=synopsis,
		director=director,
		cast=cast,
		poster=poster,
		magnet_links=magnet_links,
		torrent_files=torrent_files,
	)


def main() -> None:
	media_entries: List[Media] = []
	for movie_dir in sorted(MOVIES_ROOT.iterdir()):
		if not movie_dir.is_dir():
			continue
		index_file = movie_dir / "index.html"
		if not index_file.is_file():
			continue
		media_entries.append(parse_media(index_file))

	qualities_seen = sorted({entry.quality.value for media in media_entries for entry in (media.magnet_links + media.torrent_files) if entry.quality})
	types_seen = sorted({entry.type.value for media in media_entries for entry in (media.magnet_links + media.torrent_files) if entry.type})

	output = {
		"supported_qualities": [q.value for q in Quality],
		"supported_types": [t.value for t in ReleaseType],
		"seen_qualities": qualities_seen,
		"seen_types": types_seen,
		"media": [media.model_dump(mode='json') for media in media_entries],
	}

	print(json.dumps(output, indent=2))


if __name__ == "__main__":
	main()
