import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs, urlunparse 

logger = logging.getLogger(__name__)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.critical("DATABASE_URL environment variable not set.")
    raise ValueError("DATABASE_URL environment variable not set.")

parsed_url = urlparse(DATABASE_URL)
query_params = parse_qs(parsed_url.query)

connect_args = {}

if 'sslmode' in query_params:
    sslmode = query_params['sslmode'][0] 
    if sslmode in ['prefer', 'require', 'allow', 'verify-ca', 'verify-full']:
        connect_args['ssl'] = sslmode
        logger.info(f"Parsed sslmode='{sslmode}' and adding to connect_args as ssl='{sslmode}'.")
    else:
        logger.warning(f"Unsupported sslmode '{sslmode}' found in DATABASE_URL query parameters.")

adapted_scheme = 'postgresql+asyncpg'
if parsed_url.scheme == 'postgres':
    logger.info("Adapting scheme from 'postgres' to 'postgresql+asyncpg'")
elif parsed_url.scheme == 'postgresql':
    logger.info("Adapting scheme from 'postgresql' to 'postgresql+asyncpg'")
elif parsed_url.scheme != 'postgresql+asyncpg':
     logger.error(f"Unsupported database scheme: {parsed_url.scheme}")
     raise ValueError(f"DATABASE_URL scheme '{parsed_url.scheme}' is not compatible with asyncpg driver.")

adapted_components = (adapted_scheme, parsed_url.netloc, parsed_url.path, '', '', '')
adapted_db_url = urlunparse(adapted_components)
logger.info(f"Adapted DATABASE_URL for engine: {adapted_db_url}")

try:
    async_engine = create_async_engine(
        adapted_db_url, 
        connect_args=connect_args, 
        echo=False, 
        pool_pre_ping=True
    )
    
    AsyncSessionFactory = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    logger.info("Async database engine and session factory configured successfully.")

except Exception as e:
    logger.critical(f"Failed to create async database engine: {e}")
    raise

async def get_async_session() -> AsyncSession:
    """FastAPI dependency to provide an async database session."""
    async_session = AsyncSessionFactory()
    try:
        yield async_session
    except Exception as e:
        logger.error(f"Error during database session: {e}")
        await async_session.rollback()
        raise 
    finally:
        await async_session.close()
        logger.debug("Async database session closed.")

async def test_connection():
    async with AsyncSessionFactory() as session:
        try:
            await session.execute(text("SELECT 1"))
            logger.info("Database connection successful.")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False 