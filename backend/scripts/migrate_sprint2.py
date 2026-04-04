"""Apply Sprint 2 schema changes: tags, promotion, description."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

MIGRATIONS = [
    "ALTER TABLE ste ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}'",
    "ALTER TABLE ste ADD COLUMN IF NOT EXISTS description TEXT",
    "ALTER TABLE ste ADD COLUMN IF NOT EXISTS promoted_until TIMESTAMPTZ",
    "ALTER TABLE ste ADD COLUMN IF NOT EXISTS promotion_boost NUMERIC(5,3) DEFAULT 0.0",
    "ALTER TABLE ste ADD COLUMN IF NOT EXISTS creator_user_id TEXT",
    "ALTER TABLE ste ADD COLUMN IF NOT EXISTS order_count BIGINT DEFAULT 0",
    "CREATE INDEX IF NOT EXISTS ix_ste_tags ON ste USING GIN(tags)",
    "CREATE INDEX IF NOT EXISTS ix_ste_promoted ON ste(promoted_until) WHERE promoted_until IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS ix_ste_creator ON ste(creator_user_id)",
    """
    CREATE OR REPLACE FUNCTION ste_tsv_update() RETURNS trigger AS $$
    BEGIN
      NEW.name_tsv := to_tsvector('russian',
        COALESCE(NEW.name, '') || ' ' ||
        COALESCE(array_to_string(NEW.tags, ' '), '') || ' ' ||
        COALESCE(NEW.description, '')
      );
      RETURN NEW;
    END
    $$ LANGUAGE plpgsql;
    """,
    "DROP TRIGGER IF EXISTS ste_tsv_trigger ON ste",
    """
    CREATE TRIGGER ste_tsv_trigger BEFORE INSERT OR UPDATE ON ste
    FOR EACH ROW EXECUTE FUNCTION ste_tsv_update()
    """,
]


async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        for sql in MIGRATIONS:
            preview = sql.strip()[:60].replace("\n", " ")
            print(f"Running: {preview}...")
            await conn.execute(text(sql))
    await engine.dispose()
    print("Migration done!")


asyncio.run(main())
