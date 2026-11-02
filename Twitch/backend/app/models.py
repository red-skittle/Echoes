import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    from sqlalchemy import JSON as Vector

from .db import Base


def new_id() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class User(Timestamped, Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    twitch_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(Text)


class Streamer(Timestamped, Base):
    __tablename__ = "streamers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    twitch_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    avatar_url: Mapped[str | None] = mapped_column(Text)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)


class StreamerMembership(Timestamped, Base):
    __tablename__ = "streamer_memberships"
    __table_args__ = (UniqueConstraint("streamer_id", "user_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    streamer_id: Mapped[str] = mapped_column(ForeignKey("streamers.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="owner")


class Video(Timestamped, Base):
    __tablename__ = "videos"
    __table_args__ = (UniqueConstraint("streamer_id", "twitch_video_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    streamer_id: Mapped[str] = mapped_column(ForeignKey("streamers.id", ondelete="CASCADE"), index=True)
    twitch_video_id: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="metadata_only")
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)


class VideoAsset(Timestamped, Base):
    __tablename__ = "video_assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    storage_key: Mapped[str] = mapped_column(Text)
    checksum_sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    authorized_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)


class Transcript(Timestamped, Base):
    __tablename__ = "transcripts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), unique=True)
    language: Mapped[str] = mapped_column(String(12), default="en")
    provider: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), default="pending")


class TranscriptSegment(Timestamped, Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (Index("ix_transcript_segment_time", "transcript_id", "start_seconds"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcripts.id", ondelete="CASCADE"), index=True)
    start_seconds: Mapped[int] = mapped_column(Integer)
    end_seconds: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)


class WikiEntry(Timestamped, Base):
    __tablename__ = "wiki_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    streamer_id: Mapped[str] = mapped_column(ForeignKey("streamers.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(240))
    summary: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(40), default="Event")
    status: Mapped[str] = mapped_column(String(30), default="verified")
    confidence: Mapped[float | None] = mapped_column(Float)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    sources: Mapped[list["WikiEntrySource"]] = relationship("WikiEntrySource", back_populates="entry", cascade="all, delete-orphan")


class WikiEntrySource(Timestamped, Base):
    __tablename__ = "wiki_entry_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    wiki_entry_id: Mapped[str] = mapped_column(ForeignKey("wiki_entries.id", ondelete="CASCADE"), index=True)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    start_seconds: Mapped[int] = mapped_column(Integer)
    end_seconds: Mapped[int] = mapped_column(Integer)
    citation_note: Mapped[str] = mapped_column(Text, default="")
    entry: Mapped["WikiEntry"] = relationship("WikiEntry", back_populates="sources")
    video: Mapped["Video"] = relationship("Video")


class Topic(Timestamped, Base):
    __tablename__ = "topics"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    streamer_id: Mapped[str] = mapped_column(ForeignKey("streamers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))


class WikiEntryTopic(Timestamped, Base):
    __tablename__ = "wiki_entry_topics"
    __table_args__ = (UniqueConstraint("wiki_entry_id", "topic_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    wiki_entry_id: Mapped[str] = mapped_column(ForeignKey("wiki_entries.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)


class Entity(Timestamped, Base):
    __tablename__ = "entities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    streamer_id: Mapped[str] = mapped_column(ForeignKey("streamers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(40), default="character")


class WikiEntryEntity(Timestamped, Base):
    __tablename__ = "wiki_entry_entities"
    __table_args__ = (UniqueConstraint("wiki_entry_id", "entity_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    wiki_entry_id: Mapped[str] = mapped_column(ForeignKey("wiki_entries.id", ondelete="CASCADE"), index=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)


class WikiRelationship(Timestamped, Base):
    __tablename__ = "wiki_relationships"
    __table_args__ = (UniqueConstraint("source_entry_id", "target_entry_id", "kind"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_entry_id: Mapped[str] = mapped_column(ForeignKey("wiki_entries.id", ondelete="CASCADE"), index=True)
    target_entry_id: Mapped[str] = mapped_column(ForeignKey("wiki_entries.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40), default="related")


class Contribution(Timestamped, Base):
    __tablename__ = "contributions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    streamer_id: Mapped[str] = mapped_column(ForeignKey("streamers.id", ondelete="CASCADE"), index=True)
    wiki_entry_id: Mapped[str | None] = mapped_column(ForeignKey("wiki_entries.id", ondelete="SET NULL"), index=True)
    contributor_name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(30), default="suggestion")
    title: Mapped[str] = mapped_column(String(240))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    review_note: Mapped[str | None] = mapped_column(Text)


class Embedding(Timestamped, Base):
    __tablename__ = "embeddings"
    __table_args__ = (Index("ix_embeddings_vector_cosine", "vector_json", postgresql_using="hnsw",
                            postgresql_ops={"vector_json": "vector_cosine_ops"}),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_type: Mapped[str] = mapped_column(String(30), index=True)
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    model: Mapped[str] = mapped_column(String(100))
    vector_json: Mapped[list] = mapped_column(JSON().with_variant(Vector(1536), "postgresql"))


class ProcessingJob(Timestamped, Base):
    __tablename__ = "processing_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    video_id: Mapped[str | None] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    job_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
