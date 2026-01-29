import os
from config import Config
import logging
from sqlalchemy.engine import URL
import sqlalchemy
from database.migrations.migration_manager import run_migrations
from database.async_client import init_empty_pools, init_pools

logger = logging.getLogger(__name__)

if Config.USE_DEV_DB:
    from testcontainers.postgres import PostgresContainer

    import time
    import atexit


    def _wait_for_postgres(connection_url: URL, timeout: int = 30):
        """Wait for PostgreSQL to be ready.

        Args:
            timeout: Maximum time to wait in seconds
        """
        logger.info("Waiting for PostgreSQL to be ready...")
        connection_url = connection_url.set(drivername="postgresql+psycopg2")
        engine = sqlalchemy.create_engine(connection_url.render_as_string(False))

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with engine.connect() as conn:
                    result = conn.execute(sqlalchemy.text("SELECT 1"))
                    result.fetchone()
                    logger.info("PostgreSQL is ready!")
                    return
            except Exception as exc:
                time.sleep(1)

        raise TimeoutError(f"PostgreSQL not ready after {timeout} seconds")


    logger.info("Starting PostgreSQL test container...")

    connection_url = Config.database_url

    # Create and start container
    _container = PostgresContainer(
        image="postgres:16",
        name=connection_url.host,
        username=connection_url.username,
        password=connection_url.password,
        dbname=connection_url.database,
        port=connection_url.port
    )
    _container.with_bind_ports("5432/tcp", 5432)
    _container.with_command("postgres -c max_connections=200")
    _container.start()

    # Wait for readiness
    _wait_for_postgres(connection_url)

    # Run migrations
    logger.info("Running migrations...")


    # Clean up on exit
    def cleanup():
        logger.info("Stopping dev PostgreSQL container...")
        _container.stop()


    atexit.register(cleanup)

MIGRATION_URL = Config.database_url.set(drivername="postgresql+psycopg2").render_as_string(False)
ALEMBIC_INI_PATH = Config.ALEMBIC_INI_PATH
ALEMBIC_SCRIPT_PATH = Config.ALEMBIC_SCRIPT_PATH

run_migrations(MIGRATION_URL)

# Initialize pools after DB setup
if os.environ.get("USE_NULL_POOL"):
    get_db_session = init_empty_pools(Config.database_url.set(drivername="postgresql+asyncpg"))
else:
    get_db_session = init_pools(Config.database_url.set(drivername="postgresql+asyncpg"),
                           Config.WRITE_POOL_SIZE,
                           max_overflow=5)

async def get_db_session_dependency():
    async with get_db_session() as session:
        yield session

"""
usage example in fastapi routes:

from database.client import get_db_session_dependency

@private.get("/route")
async def some_route(session: Annotated[AsyncSession, Depends(get_db_session_dependency)]):
"""