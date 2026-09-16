"""Exports published content from the local development database into a portable pack that the
production deployment imports at startup.

    cd backend && python -m scripts.export_content

Writes `backend/data/content_pack/` (JSON + referenced media files). Commit it: the deployment reads
it from the repository, which also means media files survive a host with an ephemeral filesystem.

No user, application, CV, recording or admin data is included — see app/services/content_pack.py.
"""

from pathlib import Path

from app.core.config import get_settings
from app.services.content_pack import export_pack

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUT = BACKEND_DIR / "data" / "content_pack"


def main() -> None:
    settings = get_settings()
    url = settings.database_url
    if not url.startswith("sqlite"):
        raise SystemExit(f"export_content reads the local SQLite database; DATABASE_URL is {url.split('://')[0]}://…")
    sqlite_path = BACKEND_DIR / url.split("///")[-1].lstrip("./")
    if not sqlite_path.is_file():
        raise SystemExit(f"Database file not found: {sqlite_path}")

    counts = export_pack(
        sqlite_path=sqlite_path,
        upload_dir=BACKEND_DIR / settings.upload_dir,
        base_url=settings.public_base_url,
        out_dir=DEFAULT_OUT,
    )
    print(f"Wrote {DEFAULT_OUT}")
    for key, value in counts.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
