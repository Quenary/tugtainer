from app.config import Config
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession


def _get_async_url() -> str:
    url = Config.DB_URL
    if url.startswith("sqlite:"):
        url = url.replace("sqlite:", "sqlite+aiosqlite:")
    elif url.startswith("postgresql+psycopg2:"):
        url = url.replace("postgresql+psycopg2:", "postgresql+asyncpg:")
    elif url.startswith("mysql+pymysql:"):
        url = url.replace("mysql+pymysql:", "mysql+asyncmy:")
    elif url.startswith("mysql:"):
        url = url.replace("mysql:", "mysql+asyncmy:")
    return url


def _get_connect_args(
    url: str,
) -> dict:
    if "sqlite+aiosqlite:" in url:
        return {"timeout": 15}
    return {}


async_url = _get_async_url()
async_engine = create_async_engine(
    async_url,
    connect_args=_get_connect_args(async_url),
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=False,
)
async_session_maker = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
