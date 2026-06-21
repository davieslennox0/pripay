from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, create_engine
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


class PinCredential(Base):
    """One transaction PIN per Sui address (brief §6) — entirely separate
    from zkLogin auth. Only the Argon2id hash is ever stored."""

    __tablename__ = "pin_credentials"

    sui_address: Mapped[str] = mapped_column(String, primary_key=True)
    pin_hash: Mapped[str] = mapped_column(String, nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class BoundHandle(Base):
    """A verified platform-handle -> Sui address binding (brief §1B).

    This is the off-chain, searchable side of binding. The on-chain anchor
    (handle_registry::bind_handle) requires a tx signed by the user's
    zkLogin address, which needs the ZK proof/TEE signing path the build
    order defers to a later phase — so for now a bind only lands here, not
    on-chain yet.
    """

    __tablename__ = "bound_handles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sui_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    handle_normalized: Mapped[str] = mapped_column(String, nullable=False)
    handle_display: Mapped[str] = mapped_column(String, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (UniqueConstraint("platform", "handle_normalized", name="uq_platform_handle"),)


class EmailVerificationToken(Base):
    """Short-lived magic-link token proving ownership of an email address
    before it can be bound (brief §1B: "OAuth-verify ownership... email
    magic link")."""

    __tablename__ = "email_verification_tokens"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    sui_address: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
