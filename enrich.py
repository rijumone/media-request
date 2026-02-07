import json
import random
import re
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import click
import requests
from bs4 import BeautifulSoup
from loguru import logger
from tqdm import tqdm


BASE_URL = "https://www.yts-official.top/movies/"
INPUT_FILE = Path("movies.json")
OUTPUT_FILE = Path("enriched-movies.json")
REQUEST_TIMEOUT = 20

QUALITY_PATTERN = re.compile(r"\b(2160p|1080p|720p|480p|3D)\b", re.IGNORECASE)
TYPE_PATTERN = re.compile(r"\b(WEB[\- ]?DL|WEBRIP|WEB|BLURAY|DVDRIP|HDRIP)\b", re.IGNORECASE)


def unique_preserve_order(items: Iterable[str]) -> list[str]:
	seen = set()
	ordered: list[str] = []
	for item in items:
		if item in seen:
			continue
		seen.add(item)
		ordered.append(item)
	return ordered


def normalize_quality(text: str | None) -> str | None:
	if not text:
		return None
	match = QUALITY_PATTERN.search(text)
	if not match:
		return None
	value = match.group(1).upper()
	return value.replace("P", "p") if value != "3D" else "3D"


def normalize_type(text: str | None) -> str | None:
	if not text:
		return None
	match = TYPE_PATTERN.search(text)
	if not match:
		return None
	value = match.group(1).upper().replace(" ", "").replace("-", "")
	if value.startswith("WEB"):
		return "WEB"
	if value == "BLURAY":
		return "BluRay"
	if value == "DVDRIP":
		return "DVDRip"
	if value == "HDRIP":
		return "HDRip"
	return None


def text_or_none(node) -> str | None:
	if not node:
		return None
	text = node.get_text(strip=True)
	return text if text else None


def fetch_html(url: str) -> str | None:
	headers = {"User-Agent": "Mozilla/5.0 (compatible; media-request/1.0)"}
	try:
		response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
		if response.status_code == 404:
			logger.warning("Page not found (404): {}", url)
			return None
		response.raise_for_status()
		return response.text
	except requests.RequestException as exc:
		logger.error("Failed to fetch {}: {}", url, exc)
		return None


def select_cast(soup: BeautifulSoup) -> list[str]:
	cast_container = soup.select_one("#crew > div:nth-of-type(2)")
	if not cast_container:
		return []

	cast_names = [text_or_none(span) for span in cast_container.select("a span span")]
	cast = [name for name in cast_names if name]
	if not cast:
		cast = [text_or_none(link) for link in cast_container.select("a") if text_or_none(link)]
	if not cast:
		cast = [text_or_none(span) for span in cast_container.select("span") if text_or_none(span)]

	return unique_preserve_order(cast)


def infer_quality_type(tag) -> tuple[str | None, str | None]:
	texts = []
	current = tag
	for _ in range(5):
		if not current:
			break
		texts.append(" ".join(current.stripped_strings))
		current = current.parent
	combined = " ".join(texts)
	quality = normalize_quality(combined)
	media_type = normalize_type(combined)
	return quality, media_type


def select_magnet_links(soup: BeautifulSoup) -> list[dict]:
	container = soup.select_one("#movie-content > div:nth-of-type(1) > div:nth-of-type(3) > div > div:nth-of-type(2)")
	if not container:
		container = soup

	magnets: list[dict] = []
	seen = set()
	for anchor in container.select("a[href^='magnet:']"):
		url = anchor.get("href")
		if not url or url in seen:
			continue
		seen.add(url)
		quality, media_type = infer_quality_type(anchor)
		magnets.append({
			"quality": quality,
			"type": media_type,
			"url": url,
		})
	return magnets


def enrich_movie(movie: dict, base_url: str) -> dict:
	slug = movie.get("slug")
	if not slug:
		logger.warning("Movie missing slug: {}", movie.get("title", "<no title>"))
		return movie

	url = urljoin(base_url, f"{slug}/")
	logger.debug("Fetching movie page: {}", url)
	html = fetch_html(url)
	if not html:
		logger.warning("Could not fetch HTML for slug: {}", slug)
		movie.update({
			"imdb_link": None,
			"synopsis": None,
			"director": None,
			"cast": [],
			"magnet_links": [],
		})
		return movie

	soup = BeautifulSoup(html, "html.parser")

	imdb_link = None
	imdb_anchor = soup.select_one("#movie-info > div:nth-of-type(2) > div:nth-of-type(2) > a")
	if imdb_anchor and imdb_anchor.get("href"):
		imdb_link = imdb_anchor.get("href")

	synopsis = text_or_none(soup.select_one("#synopsis > p:nth-of-type(2)"))

	director = text_or_none(
		soup.select_one("#crew > div:nth-of-type(1) > div > div:nth-of-type(2) > a > span > span")
	)

	cast = select_cast(soup)
	magnet_links = select_magnet_links(soup)

	logger.success("Enriched movie: {} ({})", movie.get("title"), slug)
	movie.update({
		"imdb_link": imdb_link,
		"synopsis": synopsis,
		"director": director,
		"cast": cast,
		"magnet_links": magnet_links,
	})
	return movie


def write_output(items: list[dict], output_path: Path) -> None:
	with output_path.open("w", encoding="utf-8") as handle:
		json.dump(items, handle, indent=2, ensure_ascii=True)


def load_existing_output(output_path: Path) -> dict[str, dict]:
	if not output_path.exists():
		return {}
	try:
		with output_path.open("r", encoding="utf-8") as handle:
			movies = json.load(handle)
			if not isinstance(movies, list):
				return {}
			return {movie.get("slug"): movie for movie in movies if movie.get("slug")}
	except (json.JSONDecodeError, IOError):
		return {}


@click.command()
@click.option("--input-file", "input_file", default=str(INPUT_FILE), show_default=True)
@click.option("--output-file", "output_file", default=str(OUTPUT_FILE), show_default=True)
@click.option("--base-url", "base_url", default=BASE_URL, show_default=True)
@click.option("--sleep-min", default=0.1, show_default=True)
@click.option("--sleep-max", default=0.6, show_default=True)
@click.option("--limit", default=0, show_default=True, help="Limit number of movies to process")
@click.option("--start", "start", default=1, show_default=True, help="1-based movie number to start from")
def enrich_movies(
	input_file: str,
	output_file: str,
	base_url: str,
	sleep_min: float,
	sleep_max: float,
	limit: int,
	start: int,
) -> None:
	logger.remove()
	logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)

	input_path = Path(input_file)
	output_path = Path(output_file)
	if not input_path.exists():
		logger.error("Input file not found: {}", input_path)
		raise SystemExit(f"Input file not found: {input_path}")

	logger.info("Loading movies from: {}", input_path)

	with input_path.open("r", encoding="utf-8") as handle:
		movies = json.load(handle)
		if not isinstance(movies, list):
			logger.error("Input file must be a JSON array, got: {}", type(movies))
			raise SystemExit("Input file must be a JSON array of movies")

	logger.info("Loaded {} movies from input file", len(movies))

	# Load existing enriched movies
	enriched_map = load_existing_output(output_path)
	if enriched_map:
		logger.info("Found {} already enriched movies in output file", len(enriched_map))

	start_index = max(0, start - 1)
	items = movies[start_index:]
	if limit and limit > 0:
		items = items[:limit]
	
	# Build output list: use enriched versions if available, otherwise original
	output_list = []
	to_process = []
	for movie in items:
		slug = movie.get("slug")
		if slug and slug in enriched_map:
			output_list.append(enriched_map[slug])
		else:
			output_list.append(movie)
			to_process.append(len(output_list) - 1)  # Track index to update
	
	logger.info("Processing {} movies ({} already enriched, {} to enrich)", 
		len(items), len(items) - len(to_process), len(to_process))
	
	for idx, list_index in enumerate(
		tqdm(to_process, total=len(to_process), desc="Enriching movies", unit="movie"),
		start=1,
	):
		movie = output_list[list_index]
		logger.info("[{}/{}] Processing: {}", idx, len(to_process), movie.get("title", movie.get("slug")))
		enriched = enrich_movie(movie, base_url)
		output_list[list_index] = enriched
		
		# Write after each enrichment
		write_output(output_list, output_path)
		
		if sleep_max > 0:
			pause = random.uniform(max(0.0, sleep_min), max(sleep_min, sleep_max))
			logger.debug("Sleeping {:.2f} seconds", pause)
			time.sleep(pause)

	logger.success("Successfully wrote {} enriched movies to: {}", len(output_list), output_path)


if __name__ == "__main__":
	enrich_movies()
