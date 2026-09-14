"""ISO 3166-1 alpha-2 → English short name, for sources that report country codes (Lever,
SmartRecruiters, schema.org). Unknown codes are returned upper-cased rather than guessed."""

_NAMES = {
    "AE": "United Arab Emirates", "AO": "Angola", "AR": "Argentina", "AT": "Austria", "AU": "Australia",
    "BD": "Bangladesh", "BE": "Belgium", "BG": "Bulgaria", "BH": "Bahrain", "BJ": "Benin", "BR": "Brazil",
    "BW": "Botswana", "CA": "Canada", "CH": "Switzerland", "CI": "Côte d'Ivoire", "CL": "Chile", "CM": "Cameroon",
    "CN": "China", "CO": "Colombia", "CY": "Cyprus", "CZ": "Czechia", "DE": "Germany", "DK": "Denmark",
    "DZ": "Algeria", "EE": "Estonia", "EG": "Egypt", "ES": "Spain", "ET": "Ethiopia", "FI": "Finland",
    "FR": "France", "GB": "United Kingdom", "GH": "Ghana", "GR": "Greece", "HK": "Hong Kong", "HR": "Croatia",
    "HU": "Hungary", "ID": "Indonesia", "IE": "Ireland", "IL": "Israel", "IN": "India", "IQ": "Iraq",
    "IS": "Iceland", "IT": "Italy", "JO": "Jordan", "JP": "Japan", "KE": "Kenya", "KR": "South Korea",
    "KW": "Kuwait", "KZ": "Kazakhstan", "LB": "Lebanon", "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia",
    "MA": "Morocco", "MT": "Malta", "MU": "Mauritius", "MX": "Mexico", "MY": "Malaysia", "MZ": "Mozambique",
    "NA": "Namibia", "NG": "Nigeria", "NL": "Netherlands", "NO": "Norway", "NZ": "New Zealand", "OM": "Oman",
    "PE": "Peru", "PH": "Philippines", "PK": "Pakistan", "PL": "Poland", "PT": "Portugal", "QA": "Qatar",
    "RO": "Romania", "RS": "Serbia", "RW": "Rwanda", "SA": "Saudi Arabia", "SE": "Sweden", "SG": "Singapore",
    "SI": "Slovenia", "SK": "Slovakia", "SN": "Senegal", "TG": "Togo", "TH": "Thailand", "TN": "Tunisia",
    "TR": "Türkiye", "TW": "Taiwan", "TZ": "Tanzania", "UA": "Ukraine", "UG": "Uganda", "UK": "United Kingdom",
    "US": "United States", "UY": "Uruguay", "VN": "Vietnam", "ZA": "South Africa", "ZM": "Zambia", "ZW": "Zimbabwe",
}


def country_name(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if len(text) == 2 and text.isalpha():
        return _NAMES.get(text.upper(), text.upper())
    return text
