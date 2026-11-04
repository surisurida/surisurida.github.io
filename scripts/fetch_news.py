# /// script
# requires-python = ">=3.12"
# dependencies = ["feedparser>=6.0.11", "httpx[http2]>=0.28"]
# ///
"""AI·로봇 분야 뉴스를 RSS 피드에서 모아 날짜별 VuePress 마크다운 페이지로 만든다.

실행: uv run scripts/fetch_news.py   (또는 pnpm news:update)

1. 피드에서 최근 7일 기사를 받아 data/news/<카테고리>.json에 쌓는다 (이미 있는 기사는 건너뜀).
2. 해외 기사 제목을 한국어로 번역하고, Google 뉴스 링크는 원문 주소로 바꾸고, 기사 대표 이미지를 찾아
   함께 저장한다 (한 번 처리한 기사는 다시 요청하지 않음).
3. 쌓인 기사 전체로 src/news/<카테고리>/YYYY-MM-DD.md(그날 한국 시간 기준 나온 기사)를 다시 만든다.
   카테고리 첫 페이지는 따로 없고, /news/<카테고리>/ 주소는 가장 최근 날짜 페이지로 이동한다.
   메뉴(src/.vuepress/navbar, sidebar)는 빌드할 때 이 폴더의 날짜 페이지 목록을 읽어 만든다.
4. 카테고리마다 가장 최근 날짜의 최신 기사를 모아 data/news/home.md를 만든다.
   메인 페이지(src/README.md)가 이 파일을 @include로 불러온다.

피드 하나가 실패해도 나머지로 진행한다. 다만 어느 카테고리에서든 기사를 하나도
받지 못하면(네트워크 장애 등) 아무 파일도 바꾸지 않고 종료 코드 1로 끝낸다.
"""

import html
import json
import re
import sys
import time
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import feedparser
import httpx

# 한국은 서머타임이 없으므로 고정 오프셋을 쓴다 (Windows에서도 tzdata 없이 동작).
KST = timezone(timedelta(hours=9), "KST")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "news"  # 수집한 기사 저장소 — 페이지는 이 데이터로 만든다
PAGES_DIR = ROOT / "src" / "news"
# src/ 밖에 두어야 별도 페이지가 되지 않고, src/README.md가 수집 때마다 바뀌지 않는다.
HOME_SECTIONS_PATH = DATA_DIR / "home.md"
HOME_ARTICLES = 5  # 메인 페이지에 보여 줄 카테고리별 기사 수

MAX_AGE = timedelta(days=7)  # 피드에서 이보다 오래된 기사는 받지 않는다
TIMEOUT = 20  # 요청 하나를 기다리는 최대 시간(초)
USER_AGENT = "Mozilla/5.0 (compatible; surisurida-news/1.0; +https://surisurida.github.io)"

# 키 없이 쓸 수 있는 비공식 Google 번역 주소. 공식 API가 아니어서 언제든 막힐 수 있으며,
# 막히면 원문 제목을 그대로 쓰고 다음 실행 때 다시 시도한다.
# HTTP/1.1 요청은 429(차단)로 거절되는 경우가 있어 HTTP/2(httpx)로 보낸다.
TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
TRANSLATE_REGION = "해외"  # 이 지역 기사의 제목만 번역한다
TRANSLATE_BATCH_CHARS = 1500  # 요청 하나에 줄바꿈으로 이어 보낼 제목들의 최대 글자 수

# 피드에 이미지가 없는 기사는 원문 페이지의 대표 이미지(og:image)를 쓴다.
# 한 사이트에 요청을 몰아 보내면 IP가 차단되므로(실제로 403을 받음) 사이트마다 하나씩, 간격을 두고 연다.
IMAGE_DELAY = 1.0  # 같은 사이트에 보내는 기사 페이지 요청 사이의 간격(초)
IMAGE_SITES_AT_ONCE = 8  # 동시에 처리할 사이트 수 (너무 많으면 DNS 조회가 실패한다)
HEAD_LIMIT = 300_000  # 기사 페이지에서 읽을 최대 바이트 (대표 이미지는 <head> 안에 있다)

# Google 뉴스 RSS는 원문 대신 news.google.com 링크만 준다. Google 뉴스 페이지의 서명 값으로
# 비공식 내부 API(batchexecute)에 물어 원문 주소를 알아낸다. 공식 API가 아니어서 언제든 막히거나
# 바뀔 수 있으며, 실패하면 Google 링크를 그대로 쓰고(이미지 없음) 다음 실행 때 다시 시도한다.
GOOGLE_NEWS_HOST = "news.google.com"
GOOGLE_DECODE_URL = "https://news.google.com/_/DotsSplashUi/data/batchexecute"
GOOGLE_DELAY = 1.0  # 기사 하나의 원문 주소를 찾은 뒤 다음 기사까지 쉬는 시간(초)
GOOGLE_MAX_PER_RUN = 150  # 한 번 실행에서 원문 주소를 찾을 최대 기사 수 (최신 기사부터)
GOOGLE_MAX_FAILURES = 3  # 연달아 이만큼 실패하면 이번 실행에서는 그만둔다
_GN_SIGNATURE = re.compile(r'data-n-a-sg="([^"]+)"')
_GN_TIMESTAMP = re.compile(r'data-n-a-ts="([^"]+)"')

GENERATED_NOTICE = (
    "<!-- 이 파일은 scripts/fetch_news.py가 자동으로 만듭니다. "
    "직접 고치지 말고 스크립트를 다시 실행하세요. -->"
)

REGIONS = ("국내", "해외")
WEEKDAYS = "월화수목금토일"
DATE_PAGE = re.compile(r"\d{4}-\d{2}-\d{2}\.md")


@dataclass(frozen=True)
class Feed:
    name: str  # 출처 이름. Google 뉴스는 기사마다 실제 언론사 이름으로 바뀐다.
    url: str
    region: str  # REGIONS 중 하나


@dataclass(frozen=True)
class Category:
    slug: str  # 폴더 이름 (src/news/<slug>/, data/news/<slug>.json)
    title: str
    short_title: str  # 페이지의 카테고리 표시에 쓸 짧은 이름
    feeds: tuple[Feed, ...]


@dataclass(frozen=True)
class Article:
    title: str
    link: str
    source: str
    region: str
    published: datetime  # 한국 시간
    title_ko: str | None = None  # 번역한 제목 (해외 기사만)
    # 대표 이미지 주소. ""는 찾아봤지만 없음, None은 아직 확인 전 (Google 뉴스 링크는 원문 주소를 찾기 전)
    image: str | None = None

    @property
    def display_title(self) -> str:
        return self.title_ko or self.title

    def to_json(self) -> dict:
        data = {**asdict(self), "published": self.published.isoformat()}
        return {key: value for key, value in data.items() if value is not None}  # 번역 없는 기사는 title_ko 생략

    @classmethod
    def from_json(cls, data: dict) -> "Article":
        return cls(**{**data, "published": datetime.fromisoformat(data["published"])})


def google_news(query: str) -> str:
    """최근 7일 동안의 한국어 Google 뉴스 검색 결과 RSS 주소."""
    params = {"q": f"{query} when:7d", "hl": "ko", "gl": "KR", "ceid": "KR:ko"}
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)


# 같은 기사가 여러 피드에 있으면 앞에 적힌 피드의 것을 남긴다.
# 그래서 원문 링크를 주는 언론사 피드를 Google 뉴스보다 먼저 적는다.
CATEGORIES = (
    Category(
        slug="ai",
        title="AI 뉴스",
        short_title="AI",
        feeds=(
            Feed("AI타임스", "https://www.aitimes.com/rss/allArticle.xml", "국내"),
            Feed("인공지능신문", "https://www.aitimes.kr/rss/allArticle.xml", "국내"),
            Feed("Google 뉴스", google_news("인공지능"), "국내"),
            Feed("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/", "해외"),
            Feed("The Verge", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "해외"),
            Feed(
                "MIT Technology Review",
                "https://www.technologyreview.com/topic/artificial-intelligence/feed",
                "해외",
            ),
            Feed("Ars Technica", "https://arstechnica.com/ai/feed/", "해외"),
        ),
    ),
    Category(
        slug="robot",
        title="로봇 뉴스",
        short_title="로봇",
        feeds=(
            Feed("로봇신문", "https://www.irobotnews.com/rss/allArticle.xml", "국내"),
            Feed("Google 뉴스", google_news("로봇"), "국내"),
            Feed("The Robot Report", "https://www.therobotreport.com/feed/", "해외"),
            Feed("IEEE Spectrum", "https://spectrum.ieee.org/feeds/topic/robotics.rss", "해외"),
            Feed("Robohub", "https://robohub.org/feed/", "해외"),
        ),
    ),
)


# ---------------------------------------------------------------- 수집

_INVISIBLE = dict.fromkeys(map(ord, "﻿​"))  # BOM, 폭 없는 공백

# 시간대 표기가 없는 날짜 (예: "2026-11-03 13:03:52")
_NAIVE_DATE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?")

_IMG_SRC = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
_META_TAG = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_TAG_ATTR = re.compile(r"([\w:-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')")
_IMAGE_META = ("og:image", "og:image:url", "twitter:image")


def clean_text(text: str) -> str:
    """HTML 엔티티를 풀고(두 번 인코딩된 피드 대비) 보이지 않는 문자를 지운 뒤 공백을 하나로 합친다."""
    return " ".join(html.unescape(text).translate(_INVISIBLE).split())


def title_key(title: str) -> str:
    """중복 판별용 키. 대소문자·공백·문장부호 차이는 무시한다."""
    return re.sub(r"[\W_]+", "", title.casefold())


def entry_time(entry) -> datetime | None:
    for key in ("published", "updated"):
        parsed = entry.get(f"{key}_parsed")
        if parsed:
            # 국내 언론사 CMS(AI타임스, 로봇신문 등)는 시간대 없이 한국 시간을 적는데,
            # feedparser는 이를 UTC로 읽는다. 그래서 시간대 표기가 없으면 한국 시간으로 본다.
            tz = KST if _NAIVE_DATE.fullmatch(entry.get(key, "").strip()) else timezone.utc
            return datetime(*parsed[:6], tzinfo=tz).astimezone(KST)
    return None


def describe(error: Exception) -> str:
    """경고 메시지에 넣을 짧은 오류 설명."""
    if isinstance(error, httpx.HTTPStatusError):
        return f"HTTP {error.response.status_code}"
    return f"{type(error).__name__}: {error}"


def http_url(url: str | None) -> str | None:
    url = html.unescape(url or "").strip()
    return url if url.startswith(("https://", "http://")) else None


def feed_image(entry) -> str | None:
    """피드 항목에 들어 있는 이미지 주소. 썸네일 → 첨부 이미지 → 본문 첫 이미지 순으로 찾는다."""
    candidates = [m.get("url") for m in entry.get("media_thumbnail", [])]
    candidates += [
        m.get("url")
        for m in entry.get("media_content", [])
        if m.get("medium") == "image" or "image" in m.get("type", "image")
    ]
    candidates += [
        link.get("href")
        for link in entry.get("links", [])
        if link.get("rel") == "enclosure" and link.get("type", "").startswith("image/")
    ]
    bodies = [part.get("value", "") for part in entry.get("content", [])] + [entry.get("summary", "")]
    candidates += [match.group(1) for body in bodies for match in _IMG_SRC.finditer(body)]
    return next((url for url in map(http_url, candidates) if url), None)


def fetch_feed(client: httpx.Client, feed: Feed, now: datetime) -> list[Article]:
    """피드 하나를 내려받아 최근 MAX_AGE 안의 기사를 돌려준다."""
    response = client.get(feed.url)
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"RSS를 해석하지 못했습니다: {parsed.bozo_exception}")

    articles = []
    for entry in parsed.entries:
        published = entry_time(entry)
        title = clean_text(entry.get("title", ""))
        link = entry.get("link", "").strip()
        # javascript: 같은 주소가 섞여 들어오지 않도록 http(s) 링크만 받는다.
        if not (published and title and link.startswith(("https://", "http://"))):
            continue
        if now - published > MAX_AGE:
            continue
        # Google 뉴스는 entry.source에 실제 언론사가 있고, 제목 끝에 " - 언론사"가 붙어 있다.
        source = clean_text(entry.get("source", {}).get("title", "")) or feed.name
        title = title.removesuffix(f" - {source}")
        articles.append(Article(title, link, source, feed.region, published, image=feed_image(entry)))
    return articles


def fetch_category(client: httpx.Client, category: Category, now: datetime) -> list[Article]:
    """카테고리의 피드를 동시에 받아, 피드 순서대로 이은 기사 목록을 돌려준다."""

    def fetch(feed: Feed) -> list[Article]:
        try:
            return fetch_feed(client, feed, now)
        except Exception as error:  # 피드 하나가 실패해도 나머지는 계속 모은다
            print(f"  경고: {feed.name} 수집 실패 ({describe(error)})", file=sys.stderr)
            return []

    with ThreadPoolExecutor(max_workers=len(category.feeds)) as pool:
        return [article for result in pool.map(fetch, category.feeds) for article in result]


def merge(stored: list[Article], fetched: list[Article]) -> tuple[list[Article], int]:
    """저장된 기사에 새 기사를 더해 최신순으로 돌려준다. 링크나 제목이 같으면 먼저 있던 기사를 남긴다."""
    # 저장된 기사에 이미지 정보가 없고 이번 피드에 있으면 채워 넣는다.
    fetched_images = {article.link: article.image for article in fetched if article.image}
    merged = [
        replace(a, image=fetched_images[a.link]) if a.image is None and a.link in fetched_images else a
        for a in stored
    ]
    seen_links = {article.link for article in stored}
    seen_titles = {title_key(article.title) for article in stored}
    for article in fetched:
        key = title_key(article.title)
        if article.link in seen_links or (key and key in seen_titles):
            continue
        seen_links.add(article.link)
        seen_titles.add(key)
        merged.append(article)
    merged.sort(key=lambda article: article.published, reverse=True)
    return merged, len(merged) - len(stored)


def translate_batch(client: httpx.Client, titles: list[str]) -> list[str]:
    """영어 제목 여러 개를 줄바꿈으로 이어 한 번에 번역하고, 줄 단위로 다시 나눠 돌려준다."""
    response = client.post(
        TRANSLATE_URL,
        params={"client": "gtx", "sl": "en", "tl": "ko", "dt": "t"},
        data={"q": "\n".join(titles)},
    )
    response.raise_for_status()
    # 응답 형식: [[["번역문", "원문", ...], ...문장별 반복], ...]
    lines = "".join(segment[0] for segment in response.json()[0] if segment[0]).split("\n")
    if len(lines) != len(titles):
        raise ValueError(f"번역 결과의 줄 수가 다릅니다 (보낸 제목 {len(titles)}개, 받은 줄 {len(lines)}개)")
    results = []
    for title, line in zip(titles, lines):
        translated = clean_text(line)
        # 번역기가 제목 끝에 붙이는 마침표는 원문에 없으면 뗀다.
        results.append(translated if title.endswith(".") else translated.removesuffix("."))
    return results


def batches(titles: list[str]) -> list[list[str]]:
    """제목들을 TRANSLATE_BATCH_CHARS 글자를 넘지 않는 묶음으로 나눈다."""
    groups: list[list[str]] = [[]]
    size = 0
    for title in titles:
        if groups[-1] and size + len(title) > TRANSLATE_BATCH_CHARS:
            groups.append([])
            size = 0
        groups[-1].append(title)
        size += len(title) + 1
    return [group for group in groups if group]


def translate_titles(client: httpx.Client, articles: list[Article]) -> tuple[list[Article], int, int]:
    """아직 번역하지 않은 해외 기사 제목을 번역해 (기사 목록, 번역 성공 수, 실패 수)를 돌려준다.
    번역에 실패한 제목은 원문으로 두고 다음 실행 때 다시 시도한다."""
    titles = list(dict.fromkeys(a.title for a in articles if a.region == TRANSLATE_REGION and not a.title_ko))
    translations: dict[str, str] = {}
    for group in batches(titles):
        try:
            translations.update(zip(group, translate_batch(client, group)))
        except Exception as error:
            print(f"  경고: 제목 번역 실패 ({describe(error)})", file=sys.stderr)
            if isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 429:
                break  # 차단되었으면 남은 요청은 보내지 않는다

    translated = [
        replace(a, title_ko=translations[a.title]) if not a.title_ko and translations.get(a.title) else a
        for a in articles
    ]
    return translated, len(translations), len(titles) - len(translations)


def page_image(client: httpx.Client, url: str) -> str | None:
    """기사 페이지의 <head>만 읽어 대표 이미지(og:image 등) 주소를 돌려준다."""
    data = bytearray()
    with client.stream("GET", url) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            data += chunk
            if b"</head>" in data or len(data) > HEAD_LIMIT:
                break
        base = str(response.url)
    head = data.decode("utf-8", errors="replace")
    for tag in _META_TAG.findall(head):
        attrs = {key.lower(): double or single for key, double, single in _TAG_ATTR.findall(tag)}
        kind = (attrs.get("property") or attrs.get("name") or "").lower()
        if kind in _IMAGE_META and (image := http_url(urllib.parse.urljoin(base, attrs.get("content", "")))):
            return image
    return None


def checked_image(client: httpx.Client, url: str) -> str:
    """이미지가 브라우저에서 실제로 보이는지 확인해, 보이면 주소를, 아니면 ""를 돌려준다.
    사이트가 https라 브라우저는 http 이미지를 https로 바꿔 요청하므로 https로 확인한다.
    429나 서버 오류는 일시적인 문제로 보고 예외를 그대로 올린다 (다음 실행 때 다시 시도)."""
    if url.startswith("http://"):
        url = "https://" + url.removeprefix("http://")
    try:
        with client.stream("GET", url, headers={"Accept": "image/*"}) as response:
            if response.status_code == 429 or response.status_code >= 500:
                response.raise_for_status()
            ok = response.status_code == 200 and response.headers.get("content-type", "").startswith("image/")
    except httpx.HTTPStatusError:
        raise
    except httpx.HTTPError:  # 연결 실패·시간 초과 (https를 지원하지 않는 서버 포함)
        return ""
    return url if ok else ""


def google_original_url(client: httpx.Client, link: str) -> str | None:
    """Google 뉴스 링크(news.google.com/rss/articles/<id>)가 가리키는 원문 주소를 돌려준다."""
    article_id = urllib.parse.urlsplit(link).path.rstrip("/").rsplit("/", 1)[-1]
    page = client.get(f"https://{GOOGLE_NEWS_HOST}/rss/articles/{article_id}")
    page.raise_for_status()
    signature = _GN_SIGNATURE.search(page.text)
    timestamp = _GN_TIMESTAMP.search(page.text)
    if not (signature and timestamp):
        raise ValueError("Google 뉴스 페이지에서 서명 값을 찾지 못했습니다")

    options = [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None, None, None, 0, 1],
               "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0]  # fmt: skip
    query = ["garturlreq", options, article_id, int(timestamp.group(1)), signature.group(1)]
    request = [[["Fbv4je", json.dumps(query, separators=(",", ":"))]]]
    response = client.post(GOOGLE_DECODE_URL, data={"f.req": json.dumps(request, separators=(",", ":"))})
    response.raise_for_status()

    # 응답 형식: )]}'\n\n[["wrb.fr","Fbv4je","[\"garturlres\",\"https://원문 주소\",1]",...],...]
    body = response.text.split("\n\n", 1)[-1]
    for item in json.JSONDecoder().raw_decode(body)[0]:
        if isinstance(item, list) and len(item) > 2 and item[1] == "Fbv4je" and isinstance(item[2], str):
            result = json.loads(item[2])
            if result and result[0] == "garturlres":
                return http_url(result[1])
    return None


def resolve_google_links(client: httpx.Client, articles: list[Article]) -> tuple[list[Article], int]:
    """아직 처리하지 않은 Google 뉴스 링크를 원문 주소로 바꿔 (기사 목록, 바꾼 수)를 돌려준다.
    원문이 이미 가진 기사(다른 피드로 받은 기사)와 같으면 중복이므로 뺀다.
    Google이 오류를 주거나 연달아 실패하면 이번 실행에서는 그만두고 다음 실행 때 이어서 한다."""
    targets = [a for a in articles if a.image is None and urllib.parse.urlsplit(a.link).hostname == GOOGLE_NEWS_HOST]
    originals: dict[Article, str] = {}
    failures = 0
    for index, article in enumerate(targets[:GOOGLE_MAX_PER_RUN]):
        if index:
            time.sleep(GOOGLE_DELAY)
        try:
            original = google_original_url(client, article.link)
        except httpx.HTTPError as error:
            print(f"  경고: Google 뉴스 원문 주소 찾기를 멈춥니다 ({describe(error)})", file=sys.stderr)
            break
        except Exception:
            original = None
        if original:
            originals[article] = original
            failures = 0
            continue
        failures += 1
        if failures >= GOOGLE_MAX_FAILURES:
            print("  경고: Google 뉴스 원문 주소를 연달아 찾지 못해 이번에는 멈춥니다", file=sys.stderr)
            break

    known_links = {a.link for a in articles}
    updated = []
    for article in articles:
        original = originals.get(article)
        if original is None:
            updated.append(article)
        elif original not in known_links:
            known_links.add(original)
            updated.append(replace(article, link=original))
        # 원문이 이미 있는 기사면 이 기사는 버린다 (중복)
    return updated, len(originals)


def fill_images(client: httpx.Client, articles: list[Article]) -> tuple[list[Article], int]:
    """아직 확인하지 않은 기사의 대표 이미지를 원문 페이지에서 찾아 (기사 목록, 찾은 수)를 돌려준다.
    이미지가 없거나, 브라우저에서 보이지 않는 이미지(http 전용, 이미지가 아닌 응답, 404 등)거나,
    페이지가 없어졌으면 ""로 기록해 다시 찾지 않는다. 그 밖의 오류(차단, 서버 오류,
    네트워크 문제)가 나면 그 사이트에는 이번 실행에서 더 요청하지 않고, 다음 실행 때 다시 시도한다."""
    by_host: dict[str, list[Article]] = defaultdict(list)
    for article in articles:
        if article.image is None:
            by_host[urllib.parse.urlsplit(article.link).hostname or ""].append(article)

    def lookup_host(host: str, host_articles: list[Article]) -> dict[Article, str]:
        if host == GOOGLE_NEWS_HOST:
            return {}  # 원문 주소를 찾은 뒤에 이미지를 찾는다 (resolve_google_links)
        found: dict[Article, str] = {}
        for index, article in enumerate(host_articles):
            if index:
                time.sleep(IMAGE_DELAY)
            try:
                image = page_image(client, article.link)
                found[article] = checked_image(client, image) if image else ""
            except Exception as error:
                if isinstance(error, httpx.HTTPStatusError) and error.response.status_code in (404, 410):
                    found[article] = ""  # 없어진 페이지는 다시 찾지 않는다
                    continue
                print(f"  경고: {host} 이미지 확인을 멈춥니다 ({describe(error)})", file=sys.stderr)
                break
        return found

    results: dict[Article, str] = {}
    with ThreadPoolExecutor(max_workers=IMAGE_SITES_AT_ONCE) as pool:
        for found in pool.map(lookup_host, by_host.keys(), by_host.values()):
            results.update(found)

    updated = [replace(a, image=results[a]) if a in results else a for a in articles]
    return updated, sum(1 for image in results.values() if image)


def store_path(category: Category) -> Path:
    return DATA_DIR / f"{category.slug}.json"


def load_store(category: Category) -> list[Article]:
    path = store_path(category)
    if not path.exists():
        return []
    return [Article.from_json(item) for item in json.loads(path.read_text(encoding="utf-8"))]


def save_store(category: Category, articles: list[Article]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps([article.to_json() for article in articles], ensure_ascii=False, indent=2)
    write(store_path(category), text + "\n")


# ---------------------------------------------------------------- 마크다운 생성

# 기사 제목이 마크다운이나 테마 확장 문법(강조, 링크, HTML 태그, ==표시==, ~아래첨자~,
# ^위첨자^, !!스포일러!!, {속성}, $수식$ 등)으로 해석되지 않도록 앞에 \를 붙일 문자들.
_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]<>!|~^=$&])")


def md_text(text: str) -> str:
    return _MD_SPECIAL.sub(r"\\\1", text)


def md_title(text: str) -> str:
    """링크 제목 속성("...") 안에 넣을 문자열. 마우스를 올리면 보인다."""
    return md_text(text).replace('"', '\\"')


def md_url(url: str) -> str:
    """마크다운 링크 주소를 끊어 버리는 문자를 퍼센트 인코딩한다."""
    return url.translate(
        {ord(" "): "%20", ord("("): "%28", ord(")"): "%29", ord("<"): "%3C", ord(">"): "%3E", ord("\\"): "%5C"}
    )


def korean_date(day: date) -> str:
    return f"{day.year}년 {day.month}월 {day.day}일({WEEKDAYS[day.weekday()]})"


def region_counts(articles: list[Article]) -> str:
    return " · ".join(f"{region} {sum(a.region == region for a in articles)}건" for region in REGIONS)


def group_by_date(articles: list[Article]) -> dict[date, list[Article]]:
    """최신순 기사 목록을 한국 시간 날짜별로 나눈다 (최신 날짜부터)."""
    days: dict[date, list[Article]] = defaultdict(list)
    for article in articles:
        days[article.published.astimezone(KST).date()].append(article)
    return dict(sorted(days.items(), reverse=True))


def article_list(articles: list[Article]) -> str:
    """기사 목록. 제목에 {{ }}가 있어도 Vue가 템플릿으로 해석하지 않도록 v-pre 컨테이너로 감싼다."""
    if not articles:
        return "이 날 수집된 기사가 없습니다."
    lines = []
    for article in articles:
        link = md_url(article.link)
        # 대표 이미지는 기사 링크로 감싸 제목 왼쪽에 둔다 (배치는 styles/index.scss의 .news-page).
        # 이미지 서버가 다른 사이트에서의 사용을 막는 경우가 있어 referrer를 보내지 않고,
        # 이미지 링크에는 테마의 외부 링크 아이콘(↗)을 붙이지 않는다.
        image = md_url(article.image) if article.image else ""
        thumb = f'[![]({image}){{referrerpolicy="no-referrer"}}]({link}){{.no-external-link-icon}} ' if image else ""
        # 번역한 제목은 원문을 링크의 title 속성에 넣어, 마우스를 올리면 원문이 보이게 한다.
        hover = f' "{md_title(article.title)}"' if article.title_ko else ""
        lines.append(
            f"- {thumb}[{md_text(article.display_title)}]({link}{hover})\n"
            f"  <small>{md_text(article.source)} · {article.published.astimezone(KST):%H:%M}</small>"
        )
    return "::: v-pre\n\n" + "\n".join(lines) + "\n\n:::"


def render_date_page(category: Category, day: date, articles: list[Article], latest: bool) -> str:
    sections = "\n\n".join(
        f"## {region}\n\n{article_list([a for a in articles if a.region == region])}" for region in REGIONS
    )
    sources = ", ".join(feed.name for feed in category.feeds)
    # 가장 최근 날짜 페이지는 카테고리 주소(/news/<slug>/)로 들어온 방문자를 받는다 (redirect 플러그인).
    redirect = f"redirectFrom: /news/{category.slug}/\n" if latest else ""
    return f"""---
title: "{day} {category.title}"
shortTitle: "{day}"
date: {day}
{redirect}category:
  - {category.short_title}
tag:
  - 뉴스
editLink: false
lastUpdated: false
contributors: false
pageInfo: [Category, Tag]
toc: false
containerClass: news-page
---

{GENERATED_NOTICE}

{korean_date(day)}에 나온 {category.title} {len(articles)}건입니다 ({region_counts(articles)}).
제목을 누르면 원문 기사로 이동합니다.

::: info 출처

{sources}. {TRANSLATE_REGION} 기사 제목은 Google 번역으로 옮겼으며, 제목에 마우스를 올리면 원문이 보입니다.

:::

{sections}
"""


def render_home_sections(results: list[tuple[Category, list[Article]]]) -> str:
    """메인 페이지에 넣을 구획. 카테고리마다 가장 최근 날짜의 기사를 최신순으로 HOME_ARTICLES건까지 담는다."""
    sections = []
    for category, articles in results:
        day, day_articles = next(iter(group_by_date(articles).items()))
        shown = day_articles[:HOME_ARTICLES]
        sections.append(
            f"## {category.title}\n\n"
            f"{korean_date(day)}에 나온 기사 {len(day_articles)}건 중 최근 {len(shown)}건입니다. "
            f"[전체 보기](/news/{category.slug}/{day}.md)\n\n"
            f"{article_list(shown)}"
        )
    return GENERATED_NOTICE + "\n\n" + "\n\n".join(sections) + "\n"


def write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def write_pages(category: Category, articles: list[Article]) -> None:
    page_dir = PAGES_DIR / category.slug
    page_dir.mkdir(parents=True, exist_ok=True)
    days = group_by_date(articles)
    # 저장소(data/news)에 없는 날짜의 페이지는 지워서 데이터와 페이지를 항상 맞춘다.
    for path in page_dir.glob("*.md"):
        if DATE_PAGE.fullmatch(path.name) and date.fromisoformat(path.stem) not in days:
            path.unlink()
    latest = next(iter(days))
    for day, day_articles in days.items():
        write(page_dir / f"{day}.md", render_date_page(category, day, day_articles, latest=day == latest))


def main() -> int:
    now = datetime.now(KST).replace(second=0, microsecond=0)
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(http2=True, headers=headers, timeout=TIMEOUT, follow_redirects=True) as client:
        results = []
        for category in CATEGORIES:
            print(f"{category.title} 수집 중...")
            results.append((category, fetch_category(client, category, now)))

        empty = [category.title for category, fetched in results if not fetched]
        if empty:
            print(f"오류: {', '.join(empty)}에서 기사를 하나도 받지 못해 아무 파일도 바꾸지 않습니다.", file=sys.stderr)
            return 1

        stored = []
        for category, fetched in results:
            articles, added = merge(load_store(category), fetched)
            articles, translated, untranslated = translate_titles(client, articles)
            articles, resolved = resolve_google_links(client, articles)
            articles, images = fill_images(client, articles)
            save_store(category, articles)
            write_pages(category, articles)
            stored.append((category, articles))
            print(
                f"  {category.title}: 새 기사 {added}건, 누적 {len(articles)}건, 제목 번역 {translated}건, "
                f"Google 원문 주소 {resolved}건, 이미지 찾기 {images}건"
            )
            if untranslated:
                print(f"  경고: 제목 {untranslated}건은 원문으로 둡니다 (다음 실행 때 다시 번역 시도).", file=sys.stderr)
        write(HOME_SECTIONS_PATH, render_home_sections(stored))
    print(f"완료: {PAGES_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
