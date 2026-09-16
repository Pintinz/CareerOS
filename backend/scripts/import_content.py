"""Imports the committed content pack into this deployment's database.

    cd backend && python -m scripts.import_content

Idempotent: rows are upserted by primary key, so re-running updates content instead of duplicating
it. Deployments without shell access run the same import at startup — set `BOOTSTRAP_CONTENT=true`
(see app/main.py).
"""

import asyncio
from pathlib import Path

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.services.content_pack import import_pack

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PACK = BACKEND_DIR / "data" / "content_pack"


async def main() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        counts = await import_pack(
            session,
            pack_dir=DEFAULT_PACK,
            public_base_url=settings.public_base_url,
            upload_dir=BACKEND_DIR / settings.upload_dir,
        )
    for key, value in counts.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
