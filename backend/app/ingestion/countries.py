"""Country names for discovered listings.

- `country_name`: ISO 3166-1 alpha-2 → English short name, for sources that report country codes
  (Lever, SmartRecruiters, schema.org). Unknown codes are returned upper-cased rather than guessed.
- `match_country`: recognizes a country named in free-text location strings ("Nigeria",
  "Kampala Uganda", "DRC"). Returns None for anything it doesn't recognize, so placeholders and
  free text ("City, Country", "or flexible") are never stored as a country.
"""

from __future__ import annotations

import re

_NAMES = {
    "AD": "Andorra", "AE": "United Arab Emirates", "AF": "Afghanistan", "AL": "Albania", "AM": "Armenia", "AO": "Angola",
    "AR": "Argentina", "AT": "Austria", "AU": "Australia", "AZ": "Azerbaijan", "BA": "Bosnia and Herzegovina",
    "BB": "Barbados", "BD": "Bangladesh", "BE": "Belgium", "BF": "Burkina Faso", "BG": "Bulgaria", "BH": "Bahrain",
    "BI": "Burundi", "BJ": "Benin", "BN": "Brunei", "BO": "Bolivia", "BR": "Brazil", "BS": "Bahamas", "BT": "Bhutan",
    "BW": "Botswana", "BY": "Belarus", "BZ": "Belize", "CA": "Canada", "CD": "Democratic Republic of the Congo",
    "CF": "Central African Republic", "CG": "Republic of the Congo", "CH": "Switzerland", "CI": "Côte d'Ivoire",
    "CL": "Chile", "CM": "Cameroon", "CN": "China", "CO": "Colombia", "CR": "Costa Rica", "CU": "Cuba", "CV": "Cabo Verde",
    "CY": "Cyprus", "CZ": "Czechia", "DE": "Germany", "DJ": "Djibouti", "DK": "Denmark", "DM": "Dominica",
    "DO": "Dominican Republic", "DZ": "Algeria", "EC": "Ecuador", "EE": "Estonia", "EG": "Egypt", "ER": "Eritrea",
    "ES": "Spain", "ET": "Ethiopia", "FI": "Finland", "FJ": "Fiji", "FR": "France", "GA": "Gabon", "GB": "United Kingdom",
    "GD": "Grenada", "GE": "Georgia", "GH": "Ghana", "GM": "Gambia", "GN": "Guinea", "GQ": "Equatorial Guinea",
    "GR": "Greece", "GT": "Guatemala", "GW": "Guinea-Bissau", "GY": "Guyana", "HK": "Hong Kong", "HN": "Honduras",
    "HR": "Croatia", "HT": "Haiti", "HU": "Hungary", "ID": "Indonesia", "IE": "Ireland", "IL": "Israel", "IN": "India",
    "IQ": "Iraq", "IR": "Iran", "IS": "Iceland", "IT": "Italy", "JM": "Jamaica", "JO": "Jordan", "JP": "Japan",
    "KE": "Kenya", "KG": "Kyrgyzstan", "KH": "Cambodia", "KM": "Comoros", "KR": "South Korea", "KW": "Kuwait",
    "KZ": "Kazakhstan", "LA": "Laos", "LB": "Lebanon", "LC": "Saint Lucia", "LK": "Sri Lanka", "LR": "Liberia",
    "LS": "Lesotho", "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "LY": "Libya", "MA": "Morocco",
    "MD": "Moldova", "ME": "Montenegro", "MG": "Madagascar", "MK": "North Macedonia", "ML": "Mali", "MM": "Myanmar",
    "MN": "Mongolia", "MO": "Macao", "MR": "Mauritania", "MT": "Malta", "MU": "Mauritius", "MV": "Maldives", "MW": "Malawi",
    "MX": "Mexico", "MY": "Malaysia", "MZ": "Mozambique", "NA": "Namibia", "NE": "Niger", "NG": "Nigeria",
    "NI": "Nicaragua", "NL": "Netherlands", "NO": "Norway", "NP": "Nepal", "NZ": "New Zealand", "OM": "Oman",
    "PA": "Panama", "PE": "Peru", "PG": "Papua New Guinea", "PH": "Philippines", "PK": "Pakistan", "PL": "Poland",
    "PR": "Puerto Rico", "PS": "Palestine", "PT": "Portugal", "PY": "Paraguay", "QA": "Qatar", "RO": "Romania",
    "RS": "Serbia", "RU": "Russia", "RW": "Rwanda", "SA": "Saudi Arabia", "SC": "Seychelles", "SD": "Sudan",
    "SE": "Sweden", "SG": "Singapore", "SI": "Slovenia", "SK": "Slovakia", "SL": "Sierra Leone", "SN": "Senegal",
    "SO": "Somalia", "SS": "South Sudan", "ST": "São Tomé and Príncipe", "SV": "El Salvador", "SY": "Syria",
    "SZ": "Eswatini", "TD": "Chad", "TG": "Togo", "TH": "Thailand", "TJ": "Tajikistan", "TL": "Timor-Leste",
    "TN": "Tunisia", "TR": "Türkiye", "TT": "Trinidad and Tobago", "TW": "Taiwan", "TZ": "Tanzania", "UA": "Ukraine",
    "UG": "Uganda", "UK": "United Kingdom", "US": "United States", "UY": "Uruguay", "UZ": "Uzbekistan",
    "VE": "Venezuela", "VN": "Vietnam", "YE": "Yemen", "ZA": "South Africa", "ZM": "Zambia", "ZW": "Zimbabwe",
}

_ALIASES = {
    "usa": "United States", "u.s.": "United States", "u.s.a.": "United States", "united states of america": "United States",
    "uk": "United Kingdom", "u.k.": "United Kingdom", "great britain": "United Kingdom", "england": "United Kingdom",
    "scotland": "United Kingdom", "wales": "United Kingdom", "northern ireland": "United Kingdom",
    "uae": "United Arab Emirates", "drc": "Democratic Republic of the Congo", "dr congo": "Democratic Republic of the Congo",
    "democratic republic of congo": "Democratic Republic of the Congo", "congo-kinshasa": "Democratic Republic of the Congo",
    "congo-brazzaville": "Republic of the Congo", "ivory coast": "Côte d'Ivoire", "cote d'ivoire": "Côte d'Ivoire",
    "côte d’ivoire": "Côte d'Ivoire", "cote d'lvoire": "Côte d'Ivoire", "cape verde": "Cabo Verde",
    "swaziland": "Eswatini", "the gambia": "Gambia", "turkey": "Türkiye", "czech republic": "Czechia",
    "korea": "South Korea", "republic of korea": "South Korea", "viet nam": "Vietnam", "south-africa": "South Africa",
}

_BY_NAME = {name.lower(): name for name in _NAMES.values()} | _ALIASES
# Longest names first so "South Sudan" wins over "Sudan" and "Guinea-Bissau" over "Guinea".
_TRAILING = sorted(_BY_NAME, key=len, reverse=True)


# Regions used for filtering ("jobs in Africa"). Membership is by the canonical country names above,
# so a new country only needs adding here — no fixed per-country logic elsewhere.
REGIONS: dict[str, frozenset[str]] = {
    "AFRICA": frozenset({
        "Algeria", "Angola", "Benin", "Botswana", "Burkina Faso", "Burundi", "Cabo Verde", "Cameroon", "Central African Republic",
        "Chad", "Comoros", "Côte d'Ivoire", "Democratic Republic of the Congo", "Djibouti", "Egypt", "Equatorial Guinea", "Eritrea",
        "Eswatini", "Ethiopia", "Gabon", "Gambia", "Ghana", "Guinea", "Guinea-Bissau", "Kenya", "Lesotho", "Liberia", "Libya",
        "Madagascar", "Malawi", "Mali", "Mauritania", "Mauritius", "Morocco", "Mozambique", "Namibia", "Niger", "Nigeria",
        "Republic of the Congo", "Rwanda", "São Tomé and Príncipe", "Senegal", "Seychelles", "Sierra Leone", "Somalia",
        "South Africa", "South Sudan", "Sudan", "Tanzania", "Togo", "Tunisia", "Uganda", "Zambia", "Zimbabwe",
    }),
    "EUROPE": frozenset({
        "Albania", "Andorra", "Austria", "Belarus", "Belgium", "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Cyprus", "Czechia",
        "Denmark", "Estonia", "Finland", "France", "Georgia", "Germany", "Greece", "Hungary", "Iceland", "Ireland", "Italy", "Latvia",
        "Lithuania", "Luxembourg", "Malta", "Moldova", "Montenegro", "Netherlands", "North Macedonia", "Norway", "Poland", "Portugal",
        "Romania", "Serbia", "Slovakia", "Slovenia", "Spain", "Sweden", "Switzerland", "Türkiye", "Ukraine", "United Kingdom",
    }),
    "MIDDLE_EAST": frozenset({
        "Bahrain", "Iraq", "Israel", "Jordan", "Kuwait", "Lebanon", "Oman", "Palestine", "Qatar", "Saudi Arabia", "Syria",
        "United Arab Emirates", "Yemen",
    }),
    "NORTH_AMERICA": frozenset({"Canada", "Mexico", "United States"}),
}


def _canonical(value: str) -> str | None:
    text = value.strip()
    return _NAMES.get(text.upper()) if len(text) == 2 and text.isalpha() else match_country(text)


def region_countries(region: str | None) -> frozenset[str] | None:
    return REGIONS.get((region or "").strip().upper().replace(" ", "_").replace("-", "_"))


def location_matches(filters: list[str] | tuple[str, ...], *, country: str | None, location: str | None) -> bool:
    """Whether a listing belongs to a source's configured country/region scope. Filters are country
    names (any spelling `match_country` knows) or region keys such as AFRICA. A listing whose
    country is unknown matches only if its location text names a filtered country."""
    wanted: set[str] = set()
    for value in filters:
        members = region_countries(str(value))
        if members:
            wanted |= members
        elif _canonical(str(value)):
            wanted.add(_canonical(str(value)))
    if not wanted:
        return True
    resolved = _canonical(country) if country else None
    if resolved:
        return resolved in wanted
    text = f" {(location or '').lower()} "
    return any(f" {name.lower()}" in text or f",{name.lower()}" in text for name in wanted)


def country_name(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if len(text) == 2 and text.isalpha():
        return _NAMES.get(text.upper(), text.upper())
    return text


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("’", "'")).strip(" .;:-").lower()


def match_country(text: str | None) -> str | None:
    """The country a location segment names, if any: an exact name or alias ("Nigeria", "DRC"),
    or a name ending the segment ("Kampala Uganda"). Two-letter segments are not treated as
    countries here — in free text they are usually regions ("Austin, TX")."""
    if not text:
        return None
    key = _clean(text)
    if not key or len(key) <= 2:
        return None
    if key in _BY_NAME:
        return _BY_NAME[key]
    for name in _TRAILING:
        if len(name) > 3 and key.endswith(" " + name):
            return _BY_NAME[name]
    return None
