from datetime import datetime, timezone

from sqlalchemy import DateTime, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class GoogleIdentity(Base):
    """Per-user zkLogin salt, keyed by Google's stable `sub` claim.

    Deliberately stores no email/profile data here (privacy-by-default,
    brief §0) — only what's needed to deterministically re-derive the same
    zkLogin Sui address across logins.
    """

    __tablename__ = "google_identities"

    google_sub: Mapped[str] = mapped_column(String, primary_key=True)
    salt: Mapped[str] = mapped_column(String, nullable=False)
    sui_address: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
