import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Table, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base, generate_uuid

# Association Table: wiki_entry_topics
wiki_entry_topics = Table(
    "wiki_entry_topics",
    Base.metadata,
    Column("wiki_entry_id", String(36), ForeignKey("wiki_entries.id", ondelete="CASCADE"), primary_key=True),
    Column("topic_id", String(36), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
)

# Association Table: wiki_entry_entities
wiki_entry_entities = Table(
    "wiki_entry_entities",
    Base.metadata,
    Column("wiki_entry_id", String(36), ForeignKey("wiki_entries.id", ondelete="CASCADE"), primary_key=True),
    Column("entity_id", String(36), ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    twitch_id = Column(String(64), unique=True, index=True, nullable=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    display_name = Column(String(128), nullable=False)
    email = Column(String(255), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    role = Column(String(32), default="viewer") # viewer, contributor, moderator, streamer, admin
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    memberships = relationship("StreamerMembership", back_populates="user", cascade="all, delete-orphan")
    contributions = relationship("Contribution", back_populates="user", foreign_keys="Contribution.user_id")

class Streamer(Base):
    __tablename__ = "streamers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    twitch_id = Column(String(64), unique=True, index=True, nullable=False)
    username = Column(String(64), unique=True, index=True, nullable=False)
    display_name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    profile_image_url = Column(String(512), nullable=True)
    offline_image_url = Column(String(512), nullable=True)
    is_live = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    follower_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    memberships = relationship("StreamerMembership", back_populates="streamer", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="streamer", cascade="all, delete-orphan")
    wiki_entries = relationship("WikiEntry", back_populates="streamer", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="streamer", cascade="all, delete-orphan")

class StreamerMembership(Base):
    __tablename__ = "streamer_memberships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    streamer_id = Column(String(36), ForeignKey("streamers.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(32), default="contributor") # owner, moderator, contributor
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="memberships")
    streamer = relationship("Streamer", back_populates="memberships")

class Video(Base):
    __tablename__ = "videos"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    streamer_id = Column(String(36), ForeignKey("streamers.id", ondelete="CASCADE"), nullable=False, index=True)
    twitch_video_id = Column(String(64), index=True, nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0)
    thumbnail_url = Column(String(512), nullable=True)
    view_count = Column(Integer, default=0)
    stream_type = Column(String(32), default="archive") # archive, highlight, upload, clip
    is_indexed = Column(Boolean, default=False)
    processing_status = Column(String(32), default="unprocessed") # unprocessed, pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    streamer = relationship("Streamer", back_populates="videos")
    assets = relationship("VideoAsset", back_populates="video", cascade="all, delete-orphan")
    transcripts = relationship("Transcript", back_populates="video", cascade="all, delete-orphan")
    sources = relationship("WikiEntrySource", back_populates="video")
    jobs = relationship("ProcessingJob", back_populates="video", cascade="all, delete-orphan")

class VideoAsset(Base):
    __tablename__ = "video_assets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_type = Column(String(32), nullable=False) # raw_video, audio_extracted, chunk_audio
    file_path = Column(String(512), nullable=False)
    mime_type = Column(String(64), nullable=True)
    file_size_bytes = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    video = relationship("Video", back_populates="assets")

class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    language = Column(String(16), default="en")
    full_text = Column(Text, nullable=False)
    duration_seconds = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    video = relationship("Video", back_populates="transcripts")
    segments = relationship("TranscriptSegment", back_populates="transcript", cascade="all, delete-orphan")

class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transcript_id = Column(String(36), ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(Float, nullable=False) # seconds with decimal accuracy
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    speaker = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    transcript = relationship("Transcript", back_populates="segments")
    sources = relationship("WikiEntrySource", back_populates="segment")

class WikiEntry(Base):
    __tablename__ = "wiki_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    streamer_id = Column(String(36), ForeignKey("streamers.id", ondelete="CASCADE"), nullable=False, index=True)
    slug = Column(String(128), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    content = Column(Text, nullable=False) # Markdown article
    category = Column(String(64), default="Event") # Event, Lore, Inside Joke, Character, Tutorial, Discussion
    confidence = Column(Float, default=1.0)
    status = Column(String(32), default="verified") # verified, ai_draft, pending_review, archived
    revision = Column(Integer, default=1)
    author_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    streamer = relationship("Streamer", back_populates="wiki_entries")
    sources = relationship("WikiEntrySource", back_populates="wiki_entry", cascade="all, delete-orphan")
    topics = relationship("Topic", secondary=wiki_entry_topics, back_populates="wiki_entries")
    entities = relationship("Entity", secondary=wiki_entry_entities, back_populates="wiki_entries")
    contributions = relationship("Contribution", back_populates="wiki_entry")

    outbound_relationships = relationship(
        "WikiRelationship",
        foreign_keys="WikiRelationship.source_entry_id",
        back_populates="source_entry",
        cascade="all, delete-orphan"
    )
    inbound_relationships = relationship(
        "WikiRelationship",
        foreign_keys="WikiRelationship.target_entry_id",
        back_populates="target_entry",
        cascade="all, delete-orphan"
    )

class WikiEntrySource(Base):
    __tablename__ = "wiki_entry_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    wiki_entry_id = Column(String(36), ForeignKey("wiki_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_id = Column(String(36), ForeignKey("transcript_segments.id", ondelete="SET NULL"), nullable=True)
    start_timestamp = Column(Integer, nullable=False) # seconds for video player seek
    end_timestamp = Column(Integer, nullable=False)
    quote_text = Column(Text, nullable=True)
    context_note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    wiki_entry = relationship("WikiEntry", back_populates="sources")
    video = relationship("Video", back_populates="sources")
    segment = relationship("TranscriptSegment", back_populates="sources")

class Topic(Base):
    __tablename__ = "topics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(64), unique=True, index=True, nullable=False)
    slug = Column(String(64), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    wiki_entries = relationship("WikiEntry", secondary=wiki_entry_topics, back_populates="topics")

class Entity(Base):
    __tablename__ = "entities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    streamer_id = Column(String(36), ForeignKey("streamers.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), index=True, nullable=False)
    entity_type = Column(String(64), nullable=False) # Person, Character, Location, Game, Meme, Item, Group
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    streamer = relationship("Streamer", back_populates="entities")
    wiki_entries = relationship("WikiEntry", secondary=wiki_entry_entities, back_populates="entities")

class WikiRelationship(Base):
    __tablename__ = "wiki_relationships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_entry_id = Column(String(36), ForeignKey("wiki_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    target_entry_id = Column(String(36), ForeignKey("wiki_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(64), default="relates_to") # leads_to, part_of, references, opposes, spun_off
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    source_entry = relationship("WikiEntry", foreign_keys=[source_entry_id], back_populates="outbound_relationships")
    target_entry = relationship("WikiEntry", foreign_keys=[target_entry_id], back_populates="inbound_relationships")

class Contribution(Base):
    __tablename__ = "contributions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    wiki_entry_id = Column(String(36), ForeignKey("wiki_entries.id", ondelete="SET NULL"), nullable=True, index=True)
    streamer_id = Column(String(36), ForeignKey("streamers.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    contribution_type = Column(String(32), nullable=False) # new_article, correction, add_timestamp, add_relation
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    content_diff = Column(JSON, nullable=True) # structured suggested diff/fields
    status = Column(String(32), default="pending") # pending, approved, rejected
    reviewed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id], back_populates="contributions")
    wiki_entry = relationship("WikiEntry", back_populates="contributions")

class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_type = Column(String(32), nullable=False) # wiki_entry, transcript_segment, topic, entity
    entity_id = Column(String(36), nullable=False, index=True)
    text_content = Column(Text, nullable=False)
    vector = Column(JSON, nullable=False) # List of floats [0.012, -0.045, ...] compatible with both SQLite and Postgres
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = Column(String(32), nullable=False) # ingestion, transcription, wiki_extraction, indexing
    status = Column(String(32), default="queued") # queued, in_progress, completed, failed
    progress = Column(Integer, default=0) # 0 to 100
    current_step = Column(String(128), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    video = relationship("Video", back_populates="jobs")

