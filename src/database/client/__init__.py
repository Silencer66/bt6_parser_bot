import os
from sqlalchemy.ext.asyncio import AsyncSession
from alembic import command
from alembic.config import Config as AlembicConfig

from database.async_client import init_empty_pools, init_pools
from src.config import Config, logger

def run_migrations():
    """Run database migrations using Alembic."""
    migration_url = Config.database_url.set(drivername="postgresql+asyncpg").render_as_string(False)
    
    if not os.path.exists(Config.ALEMBIC_INI_PATH):
        logger.warning(f"Alembic config not found at {Config.ALEMBIC_INI_PATH}")
        return

    try:
        logger.info("Running database migrations...")
        alembic_cfg = AlembicConfig(Config.ALEMBIC_INI_PATH)
        alembic_cfg.set_main_option("sqlalchemy.url", migration_url)
        alembic_cfg.set_main_option("script_location", Config.ALEMBIC_SCRIPT_PATH)
        
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations completed successfully")
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")

# УБРАЛИ АВТОЗАПУСК МИГРАЦИЙ ОТСЮДА

# Initialize session maker
if os.environ.get("USE_NULL_POOL"):
    get_db_session = init_empty_pools(Config.database_url.set(drivername="postgresql+asyncpg"))
else:
    get_db_session = init_pools(
        Config.database_url.set(drivername="postgresql+asyncpg"),
        Config.WRITE_POOL_SIZE,
        max_overflow=5
    )
