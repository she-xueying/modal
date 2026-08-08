"""Database connection, models, and session management."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from app.config import settings


# --------------------------------------------------------------------------- #
#  Engine & Session
# --------------------------------------------------------------------------- #

db_path = settings.data_dir / "app.db"
engine = create_engine(
    f"sqlite:///{db_path}",
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    """FastAPI dependency: yields a database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------------------------------- #
#  ORM Models
# --------------------------------------------------------------------------- #

class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


class Conversation(Base):
    """A chat conversation (can have many messages)."""

    __tablename__ = "conversations"

    id = Column(String(32), primary_key=True, default=_uuid)
    title = Column(String(255), nullable=False, default="新对话")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    """A single message inside a conversation."""

    __tablename__ = "messages"

    id = Column(String(32), primary_key=True, default=_uuid)
    conversation_id = Column(
        String(32), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(20), nullable=False)  # "user" | "assistant" | "system"
    content = Column(Text, nullable=False, default="")
    map_data = Column(Text, nullable=True)  # JSON-encoded MapData (assistant)
    weather_data = Column(Text, nullable=True)  # JSON-encoded weather (assistant)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    conversation = relationship("Conversation", back_populates="messages")


def _ensure_columns() -> None:
    """Add missing columns to existing tables (lightweight dev migration)."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "messages" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("messages")}
        for col in ("map_data", "weather_data"):
            if col not in cols:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE messages ADD COLUMN {col} TEXT"))
                print(f"[database] added column messages.{col}")


# Create tables on import
Base.metadata.create_all(engine)
_ensure_columns()
