"""Which adapter handles a source. Deterministic adapters are always preferred; a source only
reaches AI research when its method says so (or its pages carry no structured data and research is
enabled — decided in the pipeline)."""

from __future__ import annotations

from app.core.config import Settings
from app.ingestion.adapters.ats import AshbyAdapter, GreenhouseAdapter, LeverAdapter, SmartRecruitersAdapter
from app.ingestion.adapters.base import SourceAdapter, SourceSnapshot
from app.ingestion.adapters.feeds import RssAdapter, StructuredPageAdapter
from app.ingestion.adapters.oracle import OracleRecruitingAdapter
from app.ingestion.adapters.workday import WorkdayAdapter

_BY_SOURCE_TYPE: dict[str, type[SourceAdapter]] = {
    "LEVER": LeverAdapter,
    "GREENHOUSE": GreenhouseAdapter,
    "ASHBY": AshbyAdapter,
    "SMARTRECRUITERS": SmartRecruitersAdapter,
    "WORKDAY": WorkdayAdapter,
    "ORACLE": OracleRecruitingAdapter,
    "RSS": RssAdapter,
}


class NoAdapterError(Exception):
    code = "NO_ADAPTER"


def adapter_for(source: SourceSnapshot) -> SourceAdapter | None:
    """None means "not fetched automatically" (MANUAL, or AI_RESEARCH which the pipeline handles)."""
    if source.discovery_method == "MANUAL":
        return None
    if source.source_type in _BY_SOURCE_TYPE:
        return _BY_SOURCE_TYPE[source.source_type]()
    if source.discovery_method == "RSS" or source.config("feed_url"):
        return RssAdapter()
    if source.discovery_method in ("STRUCTURED_DATA", "AI_RESEARCH"):
        # AI_RESEARCH sources still get the deterministic pass first; only pages with no
        # structured data are handed to a research provider (spec §75).
        return StructuredPageAdapter()
    return None


def adapter_enabled(adapter: SourceAdapter, settings: Settings) -> bool:
    return settings.web_discovery_enabled and adapter.is_enabled(settings)


# Default trust by source type (spec §7). Admins can raise/lower per source; trust is never
# publish permission on its own.
DEFAULT_TRUST_LEVEL = {
    "OFFICIAL_CAREER_PAGE": 5, "OFFICIAL_NEWSROOM": 5, "INVESTOR_RELATIONS": 5,
    "GREENHOUSE": 4, "LEVER": 4, "ASHBY": 4, "SMARTRECRUITERS": 4, "WORKDAY": 4, "SUCCESSFACTORS": 4, "ORACLE": 4,
    "GOVERNMENT": 3, "REGULATOR": 3, "UNIVERSITY": 3, "SCHOLARSHIP_PROVIDER": 3,
    "INDUSTRY_PUBLICATION": 2, "NEWS_MEDIA": 2, "RSS": 2,
    "AGGREGATOR": 1, "OTHER": 1,
}

DEFAULT_DISCOVERY_METHOD = {
    "GREENHOUSE": "STRUCTURED_API", "LEVER": "STRUCTURED_API", "ASHBY": "STRUCTURED_API",
    "SMARTRECRUITERS": "STRUCTURED_API", "WORKDAY": "STRUCTURED_API", "ORACLE": "STRUCTURED_API", "RSS": "RSS",
}

# Default polling intervals (spec §29): career sources 6-12h, scholarships 12-24h, newsrooms
# 6-24h, slow university sources 24-72h.
DEFAULT_CRAWL_INTERVAL_MINUTES = {
    # Official career sources: every 6 hours; very large boards are set to 12h per source in the seed.
    "GREENHOUSE": 360, "LEVER": 360, "ASHBY": 360, "SMARTRECRUITERS": 360, "WORKDAY": 360, "OFFICIAL_CAREER_PAGE": 360,
    "OFFICIAL_NEWSROOM": 720, "INVESTOR_RELATIONS": 1440, "RSS": 720, "INDUSTRY_PUBLICATION": 1440, "NEWS_MEDIA": 1440,
    "SCHOLARSHIP_PROVIDER": 1440, "GOVERNMENT": 1440, "REGULATOR": 1440, "UNIVERSITY": 2880,
    "SUCCESSFACTORS": 720, "ORACLE": 720, "AGGREGATOR": 1440, "OTHER": 1440,
}
