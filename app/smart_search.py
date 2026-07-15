from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Iterable


GOSZAKUP_BASE_URL = "https://goszakup.gov.kz"
USER_AGENT = "Mozilla/5.0 (compatible; TenderSmartSearch/0.1)"

STOPWORDS = {
    "для",
    "или",
    "и",
    "на",
    "по",
    "с",
    "со",
    "в",
    "во",
    "от",
    "до",
    "при",
    "без",
    "за",
    "из",
    "это",
    "нужно",
    "нужен",
    "нужна",
    "купить",
    "закупить",
    "приобрести",
    "товар",
    "услуга",
    "услуги",
    "тендер",
    "лот",
}

SYNONYMS = {
    "сервер": ["сервер", "серверное оборудование", "vps", "виртуальный сервер", "хостинг"],
    "сайт": ["сайт", "веб-сайт", "портал", "интернет ресурс", "разработка сайта"],
    "лицензия": ["лицензия", "программное обеспечение", "по", "подписка", "license"],
    "компьютер": ["компьютер", "персональный компьютер", "пк", "рабочая станция"],
    "ноутбук": ["ноутбук", "портативный компьютер", "laptop"],
    "принтер": ["принтер", "мфу", "печатающее устройство"],
    "камера": ["камера", "видеонаблюдение", "ip камера"],
    "интернет": ["интернет", "канал связи", "услуги связи", "доступ к интернету"],
    "обслуживание": ["обслуживание", "сопровождение", "техническая поддержка"],
    "больница": ["больница", "больницы", "поликлиника", "медицинский", "здравоохранение"],
    "больницы": ["больница", "больницы", "поликлиника", "медицинский", "здравоохранение"],
}

ROW_RE = re.compile(r"<tr>\s*(?P<row>[\s\S]*?)</tr>", re.IGNORECASE)
STRONG_RE = re.compile(r"<strong>(?P<value>[\s\S]*?)</strong>", re.IGNORECASE)
CUSTOMER_RE = re.compile(r"<b>Заказчик:</b>\s*(?P<customer>[\s\S]*?)<br\s*/?>", re.IGNORECASE)
LOT_URL_RE = re.compile(r"href=[\"'](?P<href>[^\"']*subpriceoffer[^\"']*)[\"']", re.IGNORECASE)
METHOD_STATUS_RE = re.compile(
    r"<td nowrap=\"nowrap\"><strong>[\s\S]*?</strong></td>\s*"
    r"<td>(?P<method>[\s\S]*?)</td>\s*"
    r"<td>(?P<status>[\s\S]*?)</td>",
    re.IGNORECASE,
)


@dataclass
class Lot:
    lot_number: str
    announcement: str
    title: str
    customer: str
    amount: float | None
    method: str
    status: str
    url: str
    score: int
    matched_terms: list[str]
    source: str = "goszakup"

    def to_dict(self) -> dict:
        return asdict(self)


def smart_search(query: str, min_amount: float = 0, limit: int = 30) -> dict:
    profile = build_query_profile(query)
    raw_lots: dict[str, Lot] = {}

    for phrase in profile["search_phrases"]:
        for lot in fetch_lots(phrase, count=50):
            scored = score_lot(lot, profile["terms"], profile["required_terms"])
            if scored.score <= 0:
                continue
            if min_amount > 0 and (scored.amount is None or scored.amount < min_amount):
                continue

            current = raw_lots.get(scored.lot_number)
            if current is None or scored.score > current.score:
                raw_lots[scored.lot_number] = scored

    items = sorted(
        raw_lots.values(),
        key=lambda item: (item.score, item.amount or 0),
        reverse=True,
    )[:limit]

    return {
        "query": query,
        "terms": profile["terms"],
        "searchPhrases": profile["search_phrases"],
        "count": len(items),
        "items": [item.to_dict() for item in items],
    }


def build_query_profile(query: str) -> dict:
    normalized = normalize(query)
    words = [word for word in normalized.split() if len(word) > 1 and word not in STOPWORDS]
    terms = unique(words)

    expanded: list[str] = []
    for term in terms:
        expanded.append(term)
        expanded.extend(SYNONYMS.get(term, []))

    search_phrases = unique(
        [
            query.strip(),
            *terms,
            *expanded,
            " ".join(terms[:3]),
        ]
    )
    search_phrases = [phrase for phrase in search_phrases if phrase]

    return {
        "terms": unique(expanded),
        "required_terms": terms,
        "search_phrases": search_phrases[:12],
    }


def fetch_lots(keyword: str, count: int = 50) -> list[Lot]:
    params = urllib.parse.urlencode(
        {
            "count_record": min(max(count, 1), 50),
            "filter[name]": keyword,
            "page": 1,
        }
    )
    url = f"{GOSZAKUP_BASE_URL}/ru/search/lots?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=25) as response:
        document = response.read().decode("utf-8", errors="ignore")

    table = extract_search_table(document)
    lots: list[Lot] = []
    for match in ROW_RE.finditer(table):
        row = match.group("row")
        strong_values = [clean(value) for value in STRONG_RE.findall(row)]
        if len(strong_values) < 4:
            continue

        lot_number = strong_values[0]
        announcement = strong_values[1]
        title = strong_values[2]
        amount = parse_amount(strong_values[-1])
        customer_match = CUSTOMER_RE.search(row)
        url_match = LOT_URL_RE.search(row)
        method_status_match = METHOD_STATUS_RE.search(row)

        if not lot_number or not title:
            continue

        lot_url = urllib.parse.urljoin(
            GOSZAKUP_BASE_URL,
            html.unescape(url_match.group("href")) if url_match else "/ru/search/lots",
        )
        lots.append(
            Lot(
                lot_number=lot_number,
                announcement=announcement,
                title=title,
                customer=clean(customer_match.group("customer")) if customer_match else "",
                amount=amount,
                method=clean(method_status_match.group("method")) if method_status_match else "",
                status=clean(method_status_match.group("status")) if method_status_match else "",
                url=lot_url,
                score=0,
                matched_terms=[],
            )
        )
    return lots


def extract_search_table(document: str) -> str:
    table_start = document.find('id="search-result"')
    if table_start == -1:
        return document
    tbody_start = document.find("<tbody", table_start)
    tbody_end = document.find("</tbody>", tbody_start)
    if tbody_start == -1 or tbody_end == -1:
        return document[table_start:]
    return document[tbody_start:tbody_end]


def score_lot(lot: Lot, terms: list[str], required_terms: list[str]) -> Lot:
    title_text = normalize(f"{lot.title} {lot.announcement}")
    customer_text = normalize(lot.customer)
    metadata_text = normalize(f"{lot.method} {lot.status}")
    full_text = normalize(f"{title_text} {customer_text} {metadata_text}")

    matched = [term for term in terms if normalize(term) in full_text]
    required_matches: list[str] = []
    synonym_terms = [term for term in terms if term not in required_terms]

    score = 0
    for required_term in required_terms:
        concept_terms = unique([required_term, *SYNONYMS.get(required_term, [])])
        concept_matched = False
        concept_score = 0

        for term in concept_terms:
            if term in title_text:
                concept_matched = True
                concept_score = max(concept_score, 28)
            if term in customer_text:
                concept_matched = True
                concept_score = max(concept_score, 24)
            if term in metadata_text:
                concept_matched = True
                concept_score = max(concept_score, 8)

        if concept_matched:
            required_matches.append(required_term)
            score += concept_score

    for term in required_matches:
        if term in title_text:
            score += 28
        if term in customer_text:
            score += 24
        if term in metadata_text:
            score += 8

    for term in synonym_terms:
        normalized_term = normalize(term)
        if normalized_term in title_text:
            score += 9
        elif normalized_term in customer_text:
            score += 7
        elif normalized_term in metadata_text:
            score += 2

    score += len(required_matches) * 12

    if "опубликован" in normalize(lot.status):
        score += 6
    if lot.amount and lot.amount >= 1_000_000:
        score += 2

    if required_terms and not required_matches:
        score -= 15
    elif len(required_terms) > 1 and len(required_matches) == 1:
        score -= 12

    return Lot(
        lot_number=lot.lot_number,
        announcement=lot.announcement,
        title=lot.title,
        customer=lot.customer,
        amount=lot.amount,
        method=lot.method,
        status=lot.status,
        url=lot.url,
        score=max(score, 0),
        matched_terms=unique(matched),
        source=lot.source,
    )


def normalize(value: str) -> str:
    cleaned = value.lower().replace("ё", "е")
    cleaned = re.sub(r"[^0-9a-zа-яәіңғүұқөһ\- ]+", " ", cleaned)
    return " ".join(cleaned.split())


def clean(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(without_tags).split())


def parse_amount(value: str) -> float | None:
    normalized = value.replace(" ", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = normalize(item)
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
