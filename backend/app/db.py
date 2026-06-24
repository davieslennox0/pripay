from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
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


class PinResetToken(Base):
    """A pending PIN reset (brief §6: "only resettable via zkLogin re-auth +
    cooldown period"). Only issued after re-verifying a *fresh* Google ID
    token against the session's own google_sub (not just the existing
    session cookie), so a hijacked session alone can't reset the PIN. The
    new PIN can't take effect until `available_at`, giving the real owner a
    window to notice and react (e.g. via an alert email, once that exists)
    if this wasn't them."""

    __tablename__ = "pin_reset_tokens"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    sui_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
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


class SendRecord(Base):
    """A send, plaintext for now (brief §12 step 4: happy path before
    Seal/TEE/Walrus are layered in). `status` tracks the stubbed on-chain
    settlement until real contract calls replace it. As of phase 6 the
    settlement itself is produced by the TEE executor (app/tee), and the
    attestation it returns is recorded here as an audit anchor (brief §5:
    "a hash for audit/dispute purposes").
    """

    __tablename__ = "send_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_sui_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    recipient_platform: Mapped[str] = mapped_column(String, nullable=False)
    recipient_handle: Mapped[str] = mapped_column(String, nullable=False)
    recipient_sui_address: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    fee: Mapped[float] = mapped_column(Float, nullable=False)
    receiver_gets: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    claim_token: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    tx_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    # Which enclave signed/relayed this, and the attestation digest binding
    # that enclave to the settled outcome (see app/tee/schemas.TeeAttestation).
    tee_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    tee_attestation: Mapped[str | None] = mapped_column(String, nullable=True)
    # Encrypted record in Walrus (brief §5/§12 step 7) — amount/token/memo are
    # only ever read back through app.storage.read_record, never stored
    # plaintext here beyond the `amount` column above (kept for the existing
    # quote/list UI; the Walrus blob is the source of truth once Seal lands).
    walrus_backend: Mapped[str | None] = mapped_column(String, nullable=True)
    walrus_blob_id: Mapped[str | None] = mapped_column(String, nullable=True)
    record_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    seal_identity: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ReceiveRecord(Base):
    """An inbound cross-chain bridge into the user's own Sui address (brief
    §8 + §12 step 8). Umbra never custodies these funds — the aggregator's
    quoted route lands USDC directly at `to_sui_address`; this row just
    tracks the quote -> submit -> settle lifecycle (for the dashboard, and so
    `/receive/{id}/status` knows what to poll)."""

    __tablename__ = "receive_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    to_sui_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    from_chain: Mapped[str] = mapped_column(String, nullable=False)
    from_token: Mapped[str] = mapped_column(String, nullable=False)
    from_amount: Mapped[str] = mapped_column(String, nullable=False)
    to_amount_min: Mapped[str] = mapped_column(String, nullable=False)
    tool: Mapped[str] = mapped_column(String, nullable=False)
    quote_id: Mapped[str] = mapped_column(String, nullable=False)
    from_tx_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    receiving_tx_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    # quoted -> pending (source tx submitted) -> settled | failed
    status: Mapped[str] = mapped_column(String, nullable=False, default="quoted")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class SwapQuote(Base):
    """A quoted swap route (brief §10), held server-side between `/swap/quote`
    and `/swap/execute` since the route object must be passed back to the
    swap venue verbatim to build the transaction. `used` prevents replaying
    the same quote into two transactions."""

    __tablename__ = "swap_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sui_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    coin_in_type: Mapped[str] = mapped_column(String, nullable=False)
    coin_out_type: Mapped[str] = mapped_column(String, nullable=False)
    amount_in: Mapped[str] = mapped_column(String, nullable=False)
    amount_out_min: Mapped[str] = mapped_column(String, nullable=False)
    route_json: Mapped[str] = mapped_column(Text, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class SwapRecord(Base):
    """A settled (stubbed) swap (brief §10 + §12 step 9). As with SendRecord,
    settlement is produced by the TEE executor and the attestation it
    returns is recorded here as an audit anchor."""

    __tablename__ = "swap_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sui_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    coin_in_type: Mapped[str] = mapped_column(String, nullable=False)
    coin_out_type: Mapped[str] = mapped_column(String, nullable=False)
    amount_in: Mapped[str] = mapped_column(String, nullable=False)
    amount_out_min: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    tx_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    tee_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    tee_attestation: Mapped[str | None] = mapped_column(String, nullable=True)
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
