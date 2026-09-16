from dataclasses import asdict, dataclass
import logging
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from config import DEFAULT_CHANNELS

logger = logging.getLogger(__name__)
CHANNELS = DEFAULT_CHANNELS
VACANCY_PAGES = [f"https://t.me/s/{channel}" for channel in CHANNELS]
MAX_CHANNEL_POSTS = 200
CHANNEL_USERNAME_RE = re.compile(r"^(?:https://t\.me/)?@?([A-Za-z0-9_]{5,32})/?$", re.IGNORECASE)


@dataclass
class Vacancy:
    title: str
    text: str
    date: str
    url: str
    channel: str

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_channel_username(value: str) -> str:
    match = CHANNEL_USERNAME_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"Invalid Telegram channel username: {value!r}")
    username = match.group(1)
    logger.info("Custom channel username extracted: @%s", username)
    return username


async def fetch_channel(
    channel: str,
    client: httpx.AsyncClient,
    limit: int = MAX_CHANNEL_POSTS,
    before: int | None = None,
) -> list[Vacancy]:
    url = f"https://t.me/s/{channel}"
    if before is not None:
        url = f"{url}?before={before}"
    response = await client.get(url)
    response.raise_for_status()
    posts = _parse_public_posts(response.text, channel, limit)
    if not posts:
        raise ValueError(f"Channel @{channel} has no public posts or is unavailable")
    return posts


def _parse_public_posts(html: str, channel: str, limit: int) -> list[Vacancy]:
    soup = BeautifulSoup(html, "html.parser")
    vacancies = []
    for message in soup.select("div.tgme_widget_message[data-post]")[-limit:]:
        text_node = message.select_one("div.tgme_widget_message_text")
        date_link = message.select_one("a.tgme_widget_message_date")
        if text_node is None or date_link is None:
            continue
        text = text_node.get_text(" ", strip=True)
        if not text:
            continue
        post_id = message.get("data-post", "").split("/", 1)[-1]
        href = date_link.get("href") or ""
        url = href if href.startswith("http") else urljoin("https://t.me/", href.lstrip("/"))
        if not url and post_id:
            url = f"https://t.me/{channel}/{post_id}"
        title = text.split("\n", 1)[0].strip()[:120] or "IT-вакансия"
        date_node = date_link.select_one("time")
        date = date_node.get("datetime", "") if date_node else date_link.get_text(" ", strip=True)
        vacancies.append(Vacancy(title=title, text=text, date=date, url=url, channel=channel))
    return vacancies


def _is_public_profile(html: str, channel: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one("div.tgme_page_title")
    description = soup.select_one("div.tgme_page_description")
    extra = soup.select_one("div.tgme_page_extra")
    has_contact_page = "tgme_page_action" in html and "Telegram: Contact" in (soup.title.get_text(" ", strip=True) if soup.title else "")
    is_profile = bool(title and (description or extra))
    logger.debug("Public profile check for @%s: profile=%s contact_page=%s", channel, is_profile, has_contact_page)
    return is_profile and not has_contact_page


async def _fetch_custom_page(channel: str, client: httpx.AsyncClient, before: int | None = None) -> list[Vacancy]:
    suffix = f"?before={before}" if before is not None else ""
    short_url = f"https://t.me/s/{channel}{suffix}"
    response = await client.get(short_url)
    response.raise_for_status()
    redirected = bool(response.history)
    logger.info("Custom channel @%s: requested=%s final=%s redirected=%s", channel, short_url, response.url, redirected)
    posts = _parse_public_posts(response.text, channel, MAX_CHANNEL_POSTS)
    if posts:
        logger.info("Custom channel @%s: /s/ returned %d posts", channel, len(posts))
        return posts

    fallback_url = f"https://t.me/{channel}{suffix}"
    fallback = await client.get(fallback_url)
    fallback.raise_for_status()
    fallback_posts = _parse_public_posts(fallback.text, channel, MAX_CHANNEL_POSTS)
    logger.info("Custom channel @%s: fallback requested=%s final=%s redirected=%s posts=%d", channel, fallback_url, fallback.url, bool(fallback.history), len(fallback_posts))
    if fallback_posts:
        return fallback_posts
    if _is_public_profile(fallback.text, channel):
        logger.warning("Custom channel @%s is public, but Telegram exposes no posts in HTML", channel)
    else:
        logger.warning("Custom channel @%s is not an accessible public profile", channel)
    return []


async def fetch_channel_posts(channel: str) -> list[Vacancy]:
    """Fetch recent public posts for a user-selected channel."""
    channel = normalize_channel_username(channel)
    timeout = httpx.Timeout(20.0, connect=10.0)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        posts = []
        before = None
        while len(posts) < MAX_CHANNEL_POSTS:
            page = await _fetch_custom_page(channel, client, before)
            if not page:
                break
            posts.extend(page)
            post_ids = [int(post.url.rsplit("/", 1)[-1]) for post in page if post.url.rsplit("/", 1)[-1].isdigit()]
            if not post_ids:
                break
            next_before = min(post_ids)
            if before is not None and next_before >= before:
                break
            before = next_before
    unique = []
    seen_urls = set()
    for post in posts:
        if post.url in seen_urls:
            continue
        seen_urls.add(post.url)
        unique.append(post)
    return unique


async def fetch_all_vacancies() -> list[Vacancy]:
    vacancies: list[Vacancy] = []
    timeout = httpx.Timeout(20.0, connect=10.0)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        for channel in CHANNELS:
            try:
                vacancies.extend(await fetch_channel(channel, client))
                logger.info("Parsed channel %s", channel)
            except (httpx.HTTPError, ValueError) as error:
                logger.warning("Could not parse channel %s: %s", channel, error)
    unique: list[Vacancy] = []
    seen_urls: set[str] = set()
    seen_text: set[str] = set()
    for vacancy in vacancies:
        normalized = " ".join(vacancy.text.lower().split())
        if vacancy.url in seen_urls or normalized in seen_text:
            continue
        seen_urls.add(vacancy.url)
        seen_text.add(normalized)
        unique.append(vacancy)
    return unique
