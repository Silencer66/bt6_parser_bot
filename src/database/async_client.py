from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.engine import URL

def init_pools(conn_url:URL, write_pool_size, timeout=30, recycle=3600, max_overflow=0) -> async_sessionmaker:
    engine = create_async_engine(conn_url.set(drivername="postgresql+asyncpg"),
                                 pool_size=write_pool_size,
                                 pool_timeout=timeout,
                                 pool_recycle=recycle,
                                 max_overflow=max_overflow,
                                 future=True,
                                 query_cache_size=0)
    engine.execution_options(compiled_cache=None)

    # notice expire_on_commit=True mean that the object will be expired after commit, you can't get attribute from object after commit
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

def init_empty_pools(conn_url: URL):
    """Initialize database connection without pooling (NullPool)."""
    # This function useful for testing purpose
    engine_ = create_async_engine(conn_url.set(drivername="postgresql+asyncpg"), future=True, poolclass=NullPool, query_cache_size=0)
    engine_.execution_options(compiled_cache=None)

    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
