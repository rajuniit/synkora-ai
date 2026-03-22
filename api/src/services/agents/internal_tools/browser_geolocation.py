"""
Browser Geolocation and Country Simulation Tools.

Provides country simulation capabilities for browser automation including:
- Geolocation (latitude/longitude)
- Timezone
- Locale/Language settings
- User agent hints

Note: This provides browser-level simulation. For full country simulation,
you would also need proxy/VPN for IP-based geolocation.
"""

import logging
from dataclasses import dataclass
from typing import Any

from .browser_session import BrowserSession

logger = logging.getLogger(__name__)


@dataclass
class CountryConfig:
    """Configuration for simulating a specific country"""

    code: str  # ISO 3166-1 alpha-2
    name: str
    latitude: float
    longitude: float
    timezone: str
    locale: str
    languages: list[str]
    currency: str | None = None
    capital: str | None = None


# Country database with geolocation data
COUNTRY_DATA: dict[str, CountryConfig] = {
    # Europe
    "AM": CountryConfig(
        code="AM",
        name="Armenia",
        latitude=40.1792,
        longitude=44.4991,
        timezone="Asia/Yerevan",
        locale="hy-AM",
        languages=["hy", "ru", "en"],
        currency="AMD",
        capital="Yerevan",
    ),
    "DE": CountryConfig(
        code="DE",
        name="Germany",
        latitude=52.5200,
        longitude=13.4050,
        timezone="Europe/Berlin",
        locale="de-DE",
        languages=["de", "en"],
        currency="EUR",
        capital="Berlin",
    ),
    "FR": CountryConfig(
        code="FR",
        name="France",
        latitude=48.8566,
        longitude=2.3522,
        timezone="Europe/Paris",
        locale="fr-FR",
        languages=["fr", "en"],
        currency="EUR",
        capital="Paris",
    ),
    "GB": CountryConfig(
        code="GB",
        name="United Kingdom",
        latitude=51.5074,
        longitude=-0.1278,
        timezone="Europe/London",
        locale="en-GB",
        languages=["en"],
        currency="GBP",
        capital="London",
    ),
    "ES": CountryConfig(
        code="ES",
        name="Spain",
        latitude=40.4168,
        longitude=-3.7038,
        timezone="Europe/Madrid",
        locale="es-ES",
        languages=["es", "ca", "eu", "gl"],
        currency="EUR",
        capital="Madrid",
    ),
    "IT": CountryConfig(
        code="IT",
        name="Italy",
        latitude=41.9028,
        longitude=12.4964,
        timezone="Europe/Rome",
        locale="it-IT",
        languages=["it", "en"],
        currency="EUR",
        capital="Rome",
    ),
    "NL": CountryConfig(
        code="NL",
        name="Netherlands",
        latitude=52.3676,
        longitude=4.9041,
        timezone="Europe/Amsterdam",
        locale="nl-NL",
        languages=["nl", "en"],
        currency="EUR",
        capital="Amsterdam",
    ),
    "PL": CountryConfig(
        code="PL",
        name="Poland",
        latitude=52.2297,
        longitude=21.0122,
        timezone="Europe/Warsaw",
        locale="pl-PL",
        languages=["pl", "en"],
        currency="PLN",
        capital="Warsaw",
    ),
    "RU": CountryConfig(
        code="RU",
        name="Russia",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
        locale="ru-RU",
        languages=["ru", "en"],
        currency="RUB",
        capital="Moscow",
    ),
    "UA": CountryConfig(
        code="UA",
        name="Ukraine",
        latitude=50.4501,
        longitude=30.5234,
        timezone="Europe/Kyiv",
        locale="uk-UA",
        languages=["uk", "ru", "en"],
        currency="UAH",
        capital="Kyiv",
    ),
    "CH": CountryConfig(
        code="CH",
        name="Switzerland",
        latitude=46.9480,
        longitude=7.4474,
        timezone="Europe/Zurich",
        locale="de-CH",
        languages=["de", "fr", "it", "en"],
        currency="CHF",
        capital="Bern",
    ),
    "AT": CountryConfig(
        code="AT",
        name="Austria",
        latitude=48.2082,
        longitude=16.3738,
        timezone="Europe/Vienna",
        locale="de-AT",
        languages=["de", "en"],
        currency="EUR",
        capital="Vienna",
    ),
    "BE": CountryConfig(
        code="BE",
        name="Belgium",
        latitude=50.8503,
        longitude=4.3517,
        timezone="Europe/Brussels",
        locale="nl-BE",
        languages=["nl", "fr", "de", "en"],
        currency="EUR",
        capital="Brussels",
    ),
    "SE": CountryConfig(
        code="SE",
        name="Sweden",
        latitude=59.3293,
        longitude=18.0686,
        timezone="Europe/Stockholm",
        locale="sv-SE",
        languages=["sv", "en"],
        currency="SEK",
        capital="Stockholm",
    ),
    "NO": CountryConfig(
        code="NO",
        name="Norway",
        latitude=59.9139,
        longitude=10.7522,
        timezone="Europe/Oslo",
        locale="nb-NO",
        languages=["no", "nb", "nn", "en"],
        currency="NOK",
        capital="Oslo",
    ),
    "DK": CountryConfig(
        code="DK",
        name="Denmark",
        latitude=55.6761,
        longitude=12.5683,
        timezone="Europe/Copenhagen",
        locale="da-DK",
        languages=["da", "en"],
        currency="DKK",
        capital="Copenhagen",
    ),
    "FI": CountryConfig(
        code="FI",
        name="Finland",
        latitude=60.1699,
        longitude=24.9384,
        timezone="Europe/Helsinki",
        locale="fi-FI",
        languages=["fi", "sv", "en"],
        currency="EUR",
        capital="Helsinki",
    ),
    "PT": CountryConfig(
        code="PT",
        name="Portugal",
        latitude=38.7223,
        longitude=-9.1393,
        timezone="Europe/Lisbon",
        locale="pt-PT",
        languages=["pt", "en"],
        currency="EUR",
        capital="Lisbon",
    ),
    "GR": CountryConfig(
        code="GR",
        name="Greece",
        latitude=37.9838,
        longitude=23.7275,
        timezone="Europe/Athens",
        locale="el-GR",
        languages=["el", "en"],
        currency="EUR",
        capital="Athens",
    ),
    "CZ": CountryConfig(
        code="CZ",
        name="Czech Republic",
        latitude=50.0755,
        longitude=14.4378,
        timezone="Europe/Prague",
        locale="cs-CZ",
        languages=["cs", "en"],
        currency="CZK",
        capital="Prague",
    ),
    "RO": CountryConfig(
        code="RO",
        name="Romania",
        latitude=44.4268,
        longitude=26.1025,
        timezone="Europe/Bucharest",
        locale="ro-RO",
        languages=["ro", "en"],
        currency="RON",
        capital="Bucharest",
    ),
    "HU": CountryConfig(
        code="HU",
        name="Hungary",
        latitude=47.4979,
        longitude=19.0402,
        timezone="Europe/Budapest",
        locale="hu-HU",
        languages=["hu", "en"],
        currency="HUF",
        capital="Budapest",
    ),
    "IE": CountryConfig(
        code="IE",
        name="Ireland",
        latitude=53.3498,
        longitude=-6.2603,
        timezone="Europe/Dublin",
        locale="en-IE",
        languages=["en", "ga"],
        currency="EUR",
        capital="Dublin",
    ),
    # Americas
    "US": CountryConfig(
        code="US",
        name="United States",
        latitude=38.9072,
        longitude=-77.0369,
        timezone="America/New_York",
        locale="en-US",
        languages=["en", "es"],
        currency="USD",
        capital="Washington D.C.",
    ),
    "CA": CountryConfig(
        code="CA",
        name="Canada",
        latitude=45.4215,
        longitude=-75.6972,
        timezone="America/Toronto",
        locale="en-CA",
        languages=["en", "fr"],
        currency="CAD",
        capital="Ottawa",
    ),
    "MX": CountryConfig(
        code="MX",
        name="Mexico",
        latitude=19.4326,
        longitude=-99.1332,
        timezone="America/Mexico_City",
        locale="es-MX",
        languages=["es", "en"],
        currency="MXN",
        capital="Mexico City",
    ),
    "BR": CountryConfig(
        code="BR",
        name="Brazil",
        latitude=-15.7801,
        longitude=-47.9292,
        timezone="America/Sao_Paulo",
        locale="pt-BR",
        languages=["pt", "en"],
        currency="BRL",
        capital="Brasilia",
    ),
    "AR": CountryConfig(
        code="AR",
        name="Argentina",
        latitude=-34.6037,
        longitude=-58.3816,
        timezone="America/Argentina/Buenos_Aires",
        locale="es-AR",
        languages=["es", "en"],
        currency="ARS",
        capital="Buenos Aires",
    ),
    "CL": CountryConfig(
        code="CL",
        name="Chile",
        latitude=-33.4489,
        longitude=-70.6693,
        timezone="America/Santiago",
        locale="es-CL",
        languages=["es", "en"],
        currency="CLP",
        capital="Santiago",
    ),
    "CO": CountryConfig(
        code="CO",
        name="Colombia",
        latitude=4.7110,
        longitude=-74.0721,
        timezone="America/Bogota",
        locale="es-CO",
        languages=["es", "en"],
        currency="COP",
        capital="Bogota",
    ),
    # Asia Pacific
    "JP": CountryConfig(
        code="JP",
        name="Japan",
        latitude=35.6762,
        longitude=139.6503,
        timezone="Asia/Tokyo",
        locale="ja-JP",
        languages=["ja", "en"],
        currency="JPY",
        capital="Tokyo",
    ),
    "CN": CountryConfig(
        code="CN",
        name="China",
        latitude=39.9042,
        longitude=116.4074,
        timezone="Asia/Shanghai",
        locale="zh-CN",
        languages=["zh", "en"],
        currency="CNY",
        capital="Beijing",
    ),
    "KR": CountryConfig(
        code="KR",
        name="South Korea",
        latitude=37.5665,
        longitude=126.9780,
        timezone="Asia/Seoul",
        locale="ko-KR",
        languages=["ko", "en"],
        currency="KRW",
        capital="Seoul",
    ),
    "IN": CountryConfig(
        code="IN",
        name="India",
        latitude=28.6139,
        longitude=77.2090,
        timezone="Asia/Kolkata",
        locale="hi-IN",
        languages=["hi", "en", "ta", "te", "bn"],
        currency="INR",
        capital="New Delhi",
    ),
    "SG": CountryConfig(
        code="SG",
        name="Singapore",
        latitude=1.3521,
        longitude=103.8198,
        timezone="Asia/Singapore",
        locale="en-SG",
        languages=["en", "zh", "ms", "ta"],
        currency="SGD",
        capital="Singapore",
    ),
    "AU": CountryConfig(
        code="AU",
        name="Australia",
        latitude=-33.8688,
        longitude=151.2093,
        timezone="Australia/Sydney",
        locale="en-AU",
        languages=["en"],
        currency="AUD",
        capital="Canberra",
    ),
    "NZ": CountryConfig(
        code="NZ",
        name="New Zealand",
        latitude=-41.2865,
        longitude=174.7762,
        timezone="Pacific/Auckland",
        locale="en-NZ",
        languages=["en", "mi"],
        currency="NZD",
        capital="Wellington",
    ),
    "TH": CountryConfig(
        code="TH",
        name="Thailand",
        latitude=13.7563,
        longitude=100.5018,
        timezone="Asia/Bangkok",
        locale="th-TH",
        languages=["th", "en"],
        currency="THB",
        capital="Bangkok",
    ),
    "VN": CountryConfig(
        code="VN",
        name="Vietnam",
        latitude=21.0285,
        longitude=105.8542,
        timezone="Asia/Ho_Chi_Minh",
        locale="vi-VN",
        languages=["vi", "en"],
        currency="VND",
        capital="Hanoi",
    ),
    "MY": CountryConfig(
        code="MY",
        name="Malaysia",
        latitude=3.1390,
        longitude=101.6869,
        timezone="Asia/Kuala_Lumpur",
        locale="ms-MY",
        languages=["ms", "en", "zh", "ta"],
        currency="MYR",
        capital="Kuala Lumpur",
    ),
    "ID": CountryConfig(
        code="ID",
        name="Indonesia",
        latitude=-6.2088,
        longitude=106.8456,
        timezone="Asia/Jakarta",
        locale="id-ID",
        languages=["id", "en"],
        currency="IDR",
        capital="Jakarta",
    ),
    "PH": CountryConfig(
        code="PH",
        name="Philippines",
        latitude=14.5995,
        longitude=120.9842,
        timezone="Asia/Manila",
        locale="en-PH",
        languages=["en", "tl"],
        currency="PHP",
        capital="Manila",
    ),
    "PK": CountryConfig(
        code="PK",
        name="Pakistan",
        latitude=33.6844,
        longitude=73.0479,
        timezone="Asia/Karachi",
        locale="ur-PK",
        languages=["ur", "en"],
        currency="PKR",
        capital="Islamabad",
    ),
    "BD": CountryConfig(
        code="BD",
        name="Bangladesh",
        latitude=23.8103,
        longitude=90.4125,
        timezone="Asia/Dhaka",
        locale="bn-BD",
        languages=["bn", "en"],
        currency="BDT",
        capital="Dhaka",
    ),
    # Middle East
    "AE": CountryConfig(
        code="AE",
        name="United Arab Emirates",
        latitude=25.2048,
        longitude=55.2708,
        timezone="Asia/Dubai",
        locale="ar-AE",
        languages=["ar", "en"],
        currency="AED",
        capital="Abu Dhabi",
    ),
    "SA": CountryConfig(
        code="SA",
        name="Saudi Arabia",
        latitude=24.7136,
        longitude=46.6753,
        timezone="Asia/Riyadh",
        locale="ar-SA",
        languages=["ar", "en"],
        currency="SAR",
        capital="Riyadh",
    ),
    "IL": CountryConfig(
        code="IL",
        name="Israel",
        latitude=31.7683,
        longitude=35.2137,
        timezone="Asia/Jerusalem",
        locale="he-IL",
        languages=["he", "ar", "en"],
        currency="ILS",
        capital="Jerusalem",
    ),
    "TR": CountryConfig(
        code="TR",
        name="Turkey",
        latitude=39.9334,
        longitude=32.8597,
        timezone="Europe/Istanbul",
        locale="tr-TR",
        languages=["tr", "en"],
        currency="TRY",
        capital="Ankara",
    ),
    # Africa
    "ZA": CountryConfig(
        code="ZA",
        name="South Africa",
        latitude=-33.9249,
        longitude=18.4241,
        timezone="Africa/Johannesburg",
        locale="en-ZA",
        languages=["en", "af", "zu", "xh"],
        currency="ZAR",
        capital="Pretoria",
    ),
    "EG": CountryConfig(
        code="EG",
        name="Egypt",
        latitude=30.0444,
        longitude=31.2357,
        timezone="Africa/Cairo",
        locale="ar-EG",
        languages=["ar", "en"],
        currency="EGP",
        capital="Cairo",
    ),
    "NG": CountryConfig(
        code="NG",
        name="Nigeria",
        latitude=9.0765,
        longitude=7.3986,
        timezone="Africa/Lagos",
        locale="en-NG",
        languages=["en", "ha", "ig", "yo"],
        currency="NGN",
        capital="Abuja",
    ),
    "KE": CountryConfig(
        code="KE",
        name="Kenya",
        latitude=-1.2921,
        longitude=36.8219,
        timezone="Africa/Nairobi",
        locale="en-KE",
        languages=["en", "sw"],
        currency="KES",
        capital="Nairobi",
    ),
}

# US State timezones for more granular US simulation
US_STATES: dict[str, dict[str, Any]] = {
    "CA": {
        "name": "California",
        "timezone": "America/Los_Angeles",
        "latitude": 34.0522,
        "longitude": -118.2437,
        "city": "Los Angeles",
    },
    "NY": {
        "name": "New York",
        "timezone": "America/New_York",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "city": "New York City",
    },
    "TX": {
        "name": "Texas",
        "timezone": "America/Chicago",
        "latitude": 29.7604,
        "longitude": -95.3698,
        "city": "Houston",
    },
    "FL": {
        "name": "Florida",
        "timezone": "America/New_York",
        "latitude": 25.7617,
        "longitude": -80.1918,
        "city": "Miami",
    },
    "IL": {
        "name": "Illinois",
        "timezone": "America/Chicago",
        "latitude": 41.8781,
        "longitude": -87.6298,
        "city": "Chicago",
    },
    "WA": {
        "name": "Washington",
        "timezone": "America/Los_Angeles",
        "latitude": 47.6062,
        "longitude": -122.3321,
        "city": "Seattle",
    },
    "CO": {
        "name": "Colorado",
        "timezone": "America/Denver",
        "latitude": 39.7392,
        "longitude": -104.9903,
        "city": "Denver",
    },
    "AZ": {
        "name": "Arizona",
        "timezone": "America/Phoenix",
        "latitude": 33.4484,
        "longitude": -112.0740,
        "city": "Phoenix",
    },
}


def get_country_config(country_code: str) -> CountryConfig | None:
    """Get country configuration by ISO 3166-1 alpha-2 code"""
    return COUNTRY_DATA.get(country_code.upper())


def list_supported_countries() -> list[dict[str, str]]:
    """List all supported countries"""
    return [{"code": c.code, "name": c.name, "timezone": c.timezone} for c in COUNTRY_DATA.values()]


def build_accept_language_header(languages: list[str]) -> str:
    """Build Accept-Language header from language list"""
    if not languages:
        return "en-US,en;q=0.9"

    parts = []
    for i, lang in enumerate(languages):
        if i == 0:
            parts.append(lang)
        else:
            # Decrease quality factor for each subsequent language
            quality = max(0.1, 1.0 - (i * 0.1))
            parts.append(f"{lang};q={quality:.1f}")

    return ",".join(parts)


def get_country_user_agent(country_code: str, base_user_agent: str | None = None) -> str:
    """Generate a user agent appropriate for the country"""
    # Base Chrome user agent - most common globally
    ua = (
        base_user_agent
        or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Could customize based on country if needed
    # For now, return standard Chrome UA
    return ua


# =============================================================================
# BROWSER SESSION CONFIGURATION
# =============================================================================


def parse_proxy_url(proxy_url: str) -> dict[str, Any]:
    """
    Parse proxy URL into Playwright proxy config.

    Supports formats:
    - http://host:port
    - http://user:pass@host:port
    - socks5://host:port
    - socks5://user:pass@host:port
    """
    from urllib.parse import urlparse

    parsed = urlparse(proxy_url)

    proxy_config: dict[str, Any] = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}

    if parsed.username:
        proxy_config["username"] = parsed.username
    if parsed.password:
        proxy_config["password"] = parsed.password

    return proxy_config


async def internal_browser_set_country(
    country_code: str,
    session_id: str = "default",
    apply_to_existing: bool = True,
    proxy_url: str | None = None,
    custom_latitude: float | None = None,
    custom_longitude: float | None = None,
    custom_timezone: str | None = None,
    custom_locale: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Configure browser session to simulate browsing from a specific country.

    This sets:
    - Geolocation (latitude/longitude)
    - Timezone
    - Locale/Language
    - Accept-Language headers
    - Proxy (optional) - for IP-based geolocation

    Args:
        country_code: ISO 3166-1 alpha-2 country code (e.g., "US", "DE", "JP", "AM")
        session_id: Browser session ID (default: "default")
        apply_to_existing: If True, recreates the context with new settings.
                          If False, only affects new pages/sessions.
        proxy_url: Proxy server URL for IP-based geolocation. Formats:
                   - http://host:port
                   - http://user:pass@host:port
                   - socks5://user:pass@host:port
                   For country-specific proxies (e.g., Bright Data):
                   - http://user-country-am:pass@proxy.brightdata.com:22225
        custom_latitude: Override the default latitude for the country
        custom_longitude: Override the default longitude for the country
        custom_timezone: Override the default timezone
        custom_locale: Override the default locale

    Returns:
        Dict with configuration result including applied settings

    Example:
        # Simulate browsing from Armenia (browser-level only)
        result = await internal_browser_set_country(country_code="AM")

        # Full simulation with proxy (browser + IP)
        result = await internal_browser_set_country(
            country_code="AM",
            proxy_url="http://user-country-am:pass@proxy.brightdata.com:22225"
        )

        # Simulate from Germany with custom location
        result = await internal_browser_set_country(
            country_code="DE",
            custom_latitude=48.1351,  # Munich
            custom_longitude=11.5820,
            proxy_url="http://user:pass@de-proxy.example.com:8080"
        )
    """
    try:
        country = get_country_config(country_code)
        if not country:
            return {
                "success": False,
                "error": f"Country code '{country_code}' not found. Use internal_browser_list_countries to see supported countries.",
                "supported_countries": len(COUNTRY_DATA),
            }

        # Determine settings
        latitude = custom_latitude if custom_latitude is not None else country.latitude
        longitude = custom_longitude if custom_longitude is not None else country.longitude
        timezone = custom_timezone or country.timezone
        locale = custom_locale or country.locale
        languages = country.languages

        # Get or create session
        session = await BrowserSession.get_or_create(session_id)

        # Parse proxy config if provided
        proxy_config = None
        if proxy_url:
            try:
                proxy_config = parse_proxy_url(proxy_url)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Invalid proxy URL: {e}. Expected format: http://user:pass@host:port",
                }

        # Build context options for country simulation
        geolocation_config = {
            "geolocation": {"latitude": latitude, "longitude": longitude, "accuracy": 100},
            "timezone_id": timezone,
            "locale": locale,
            "permissions": ["geolocation"],  # Grant geolocation permission
            "extra_http_headers": {"Accept-Language": build_accept_language_header(languages)},
        }

        # Apply to existing session by recreating context
        if apply_to_existing and session.context:
            # Store current pages' URLs
            current_urls = {}
            for page_id, page in session.pages.items():
                try:
                    current_urls[page_id] = page.url
                except Exception:
                    pass

            # Close existing context and browser (proxy requires browser-level config)
            await session.context.close()

            if proxy_config:
                # Proxy is set at browser launch level in Playwright
                # Need to relaunch browser with proxy
                if session.browser:
                    await session.browser.close()
                session.browser = await session.playwright.chromium.launch(
                    headless=True,
                    proxy=proxy_config,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-accelerated-2d-canvas",
                        "--disable-gpu",
                    ],
                )

            # Create new context with country settings
            session.context = await session.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=get_country_user_agent(country_code),
                geolocation=geolocation_config["geolocation"],
                timezone_id=geolocation_config["timezone_id"],
                locale=geolocation_config["locale"],
                permissions=geolocation_config["permissions"],
                extra_http_headers=geolocation_config["extra_http_headers"],
            )

            # Clear old pages
            session.pages.clear()
            session._page_state_store.clear()
            session.current_page_id = None

            # Restore pages at their URLs
            for page_id, url in current_urls.items():
                try:
                    _, page = await session.new_page(page_id)
                    if url and url != "about:blank":
                        await page.goto(url)
                except Exception as e:
                    logger.warning(f"Failed to restore page {page_id}: {e}")

        # Store config in session for future reference
        session._country_config = geolocation_config
        session._country_code = country_code
        session._proxy_config = proxy_config

        using_proxy = proxy_config is not None
        note = f"Browser geolocation, timezone, and locale are now simulating {country.name}."
        if using_proxy:
            note += " Proxy is active - IP-based geolocation will also show the target country."
        else:
            note += (
                " Note: IP-based geolocation will still show your actual location."
                " Pass proxy_url for full country simulation."
            )

        return {
            "success": True,
            "country_code": country_code,
            "country_name": country.name,
            "proxy_active": using_proxy,
            "applied_settings": {
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone,
                "locale": locale,
                "languages": languages,
                "accept_language": build_accept_language_header(languages),
                "proxy": proxy_config["server"] if proxy_config else None,
            },
            "session_id": session_id,
            "note": note,
        }

    except Exception as e:
        logger.error(f"Error setting country simulation: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_set_geolocation(
    latitude: float,
    longitude: float,
    accuracy: float = 100,
    session_id: str = "default",
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Set custom geolocation coordinates for the browser session.

    Args:
        latitude: Latitude coordinate (-90 to 90)
        longitude: Longitude coordinate (-180 to 180)
        accuracy: Accuracy in meters (default: 100)
        session_id: Browser session ID

    Returns:
        Dict with result

    Example:
        # Set to Yerevan, Armenia
        result = await internal_browser_set_geolocation(
            latitude=40.1792,
            longitude=44.4991
        )
    """
    try:
        if not -90 <= latitude <= 90:
            return {"success": False, "error": "Latitude must be between -90 and 90"}
        if not -180 <= longitude <= 180:
            return {"success": False, "error": "Longitude must be between -180 and 180"}

        session = await BrowserSession.get_or_create(session_id)

        if not session.context:
            return {"success": False, "error": "No browser context available"}

        # Set geolocation on context
        await session.context.set_geolocation({"latitude": latitude, "longitude": longitude, "accuracy": accuracy})

        # Grant permission
        await session.context.grant_permissions(["geolocation"])

        return {
            "success": True,
            "geolocation": {"latitude": latitude, "longitude": longitude, "accuracy": accuracy},
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Error setting geolocation: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_list_countries(
    region: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    List all supported countries for browser simulation.

    Args:
        region: Filter by region - "europe", "americas", "asia", "middle_east", "africa"

    Returns:
        Dict with list of supported countries

    Example:
        result = await internal_browser_list_countries(region="europe")
    """
    countries = list_supported_countries()

    if region:
        region_lower = region.lower().replace(" ", "_")
        region_map = {
            "europe": [
                "AM",
                "DE",
                "FR",
                "GB",
                "ES",
                "IT",
                "NL",
                "PL",
                "RU",
                "UA",
                "CH",
                "AT",
                "BE",
                "SE",
                "NO",
                "DK",
                "FI",
                "PT",
                "GR",
                "CZ",
                "RO",
                "HU",
                "IE",
            ],
            "americas": ["US", "CA", "MX", "BR", "AR", "CL", "CO"],
            "asia": ["JP", "CN", "KR", "IN", "SG", "AU", "NZ", "TH", "VN", "MY", "ID", "PH", "PK", "BD"],
            "middle_east": ["AE", "SA", "IL", "TR"],
            "africa": ["ZA", "EG", "NG", "KE"],
        }
        filter_codes = region_map.get(region_lower, [])
        if filter_codes:
            countries = [c for c in countries if c["code"] in filter_codes]

    return {
        "success": True,
        "countries": countries,
        "count": len(countries),
        "total_supported": len(COUNTRY_DATA),
    }


async def internal_browser_get_country_info(
    country_code: str,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Get detailed information about a country's simulation settings.

    Args:
        country_code: ISO 3166-1 alpha-2 country code (e.g., "AM", "US", "DE")

    Returns:
        Dict with country details including coordinates, timezone, locale

    Example:
        result = await internal_browser_get_country_info(country_code="AM")
    """
    country = get_country_config(country_code)
    if not country:
        return {"success": False, "error": f"Country code '{country_code}' not found"}

    return {
        "success": True,
        "country": {
            "code": country.code,
            "name": country.name,
            "capital": country.capital,
            "coordinates": {"latitude": country.latitude, "longitude": country.longitude},
            "timezone": country.timezone,
            "locale": country.locale,
            "languages": country.languages,
            "currency": country.currency,
            "accept_language_header": build_accept_language_header(country.languages),
        },
    }


async def internal_browser_get_current_location(
    session_id: str = "default",
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Get the current geolocation settings for a browser session.

    Args:
        session_id: Browser session ID

    Returns:
        Dict with current location settings

    Example:
        result = await internal_browser_get_current_location()
    """
    try:
        session = await BrowserSession.get_or_create(session_id)

        # Get stored country config if set
        country_code = getattr(session, "_country_code", None)
        country_config = getattr(session, "_country_config", None)
        proxy_config = getattr(session, "_proxy_config", None)

        if country_code and country_config:
            return {
                "success": True,
                "simulating_country": country_code,
                "settings": country_config,
                "proxy_active": proxy_config is not None,
                "proxy_server": proxy_config.get("server") if proxy_config else None,
                "session_id": session_id,
            }

        return {
            "success": True,
            "simulating_country": None,
            "proxy_active": proxy_config is not None,
            "proxy_server": proxy_config.get("server") if proxy_config else None,
            "message": "No country simulation configured. Browser using default settings.",
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Error getting current location: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_set_proxy(
    proxy_url: str,
    session_id: str = "default",
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Set a proxy for the browser session without changing geolocation settings.

    All browser traffic will be routed through the proxy server.

    Args:
        proxy_url: Proxy server URL. Supported formats:
                   - http://host:port
                   - http://user:pass@host:port
                   - socks5://host:port
                   - socks5://user:pass@host:port

                   For country-specific residential proxies:
                   - Bright Data: http://user-country-am:pass@brd.superproxy.io:22225
                   - Oxylabs: http://user:pass@pr.oxylabs.io:7777
                   - SmartProxy: http://user:pass@gate.smartproxy.com:7000
        session_id: Browser session ID (default: "default")

    Returns:
        Dict with proxy configuration result

    Example:
        # Basic proxy
        result = await internal_browser_set_proxy(
            proxy_url="http://proxy.example.com:8080"
        )

        # Authenticated proxy
        result = await internal_browser_set_proxy(
            proxy_url="http://username:password@proxy.example.com:8080"
        )

        # SOCKS5 proxy
        result = await internal_browser_set_proxy(
            proxy_url="socks5://user:pass@proxy.example.com:1080"
        )
    """
    try:
        # Parse proxy URL
        try:
            proxy_config = parse_proxy_url(proxy_url)
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid proxy URL: {e}. Expected format: http://user:pass@host:port",
            }

        session = await BrowserSession.get_or_create(session_id)

        # Store current pages' URLs
        current_urls = {}
        if session.context:
            for page_id, page in session.pages.items():
                try:
                    current_urls[page_id] = page.url
                except Exception:
                    pass
            await session.context.close()

        # Close browser and relaunch with proxy
        if session.browser:
            await session.browser.close()

        session.browser = await session.playwright.chromium.launch(
            headless=True,
            proxy=proxy_config,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
            ],
        )

        # Create new context
        session.context = await session.browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        # Clear old pages
        session.pages.clear()
        session._page_state_store.clear()
        session.current_page_id = None

        # Store proxy config
        session._proxy_config = proxy_config

        # Restore pages at their URLs
        for page_id, url in current_urls.items():
            try:
                _, page = await session.new_page(page_id)
                if url and url != "about:blank":
                    await page.goto(url)
            except Exception as e:
                logger.warning(f"Failed to restore page {page_id}: {e}")

        return {
            "success": True,
            "proxy_server": proxy_config["server"],
            "authenticated": "username" in proxy_config,
            "session_id": session_id,
            "note": "Proxy is now active. All browser traffic will route through the proxy server.",
        }

    except Exception as e:
        logger.error(f"Error setting proxy: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_clear_proxy(
    session_id: str = "default",
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Remove proxy from browser session and use direct connection.

    Args:
        session_id: Browser session ID

    Returns:
        Dict with result

    Example:
        result = await internal_browser_clear_proxy()
    """
    try:
        session = await BrowserSession.get_or_create(session_id)

        # Check if proxy is set
        proxy_config = getattr(session, "_proxy_config", None)
        if not proxy_config:
            return {
                "success": True,
                "message": "No proxy was configured.",
                "session_id": session_id,
            }

        # Store current pages' URLs
        current_urls = {}
        if session.context:
            for page_id, page in session.pages.items():
                try:
                    current_urls[page_id] = page.url
                except Exception:
                    pass
            await session.context.close()

        # Close browser and relaunch without proxy
        if session.browser:
            await session.browser.close()

        session.browser = await session.playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
            ],
        )

        # Create new context
        session.context = await session.browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        # Clear old pages and proxy config
        session.pages.clear()
        session._page_state_store.clear()
        session.current_page_id = None
        session._proxy_config = None

        # Restore pages at their URLs
        for page_id, url in current_urls.items():
            try:
                _, page = await session.new_page(page_id)
                if url and url != "about:blank":
                    await page.goto(url)
            except Exception as e:
                logger.warning(f"Failed to restore page {page_id}: {e}")

        return {
            "success": True,
            "message": "Proxy removed. Browser now using direct connection.",
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Error clearing proxy: {e}")
        return {"success": False, "error": str(e)}
