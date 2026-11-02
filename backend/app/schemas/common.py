from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field

# User Schemas
class UserBase(BaseModel):
    username: str
    display_name: str
    avatar_url: Optional[str] = None
    role: str = "viewer"

class UserResponse(UserBase):
    id: str
    twitch_id: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

# Topic & Entity Schemas
class TopicSchema(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    class Config:
        from_attributes = True

class EntitySchema(BaseModel):
    id: str
    name: str
    entity_type: str
    description: Optional[str] = None
    class Config:
        from_attributes = True

# Video Schemas
class VideoBase(BaseModel):
    title: str
    description: Optional[str] = None
    twitch_video_id: Optional[str] = None
    duration_seconds: int = 0
    thumbnail_url: Optional[str] = None
    view_count: int = 0
    stream_type: str = "archive"

class VideoResponse(VideoBase):
    id: str
    streamer_id: str
    published_at: Optional[datetime] = None
    is_indexed: bool
    processing_status: str
    created_at: datetime
    class Config:
        from_attributes = True

class TranscriptSegmentSchema(BaseModel):
    id: str
    start_time: float
    end_time: float
    text: str
    speaker: Optional[str] = None
    class Config:
        from_attributes = True

class TranscriptResponse(BaseModel):
    id: str
    video_id: str
    language: str
    full_text: str
    segments: List[TranscriptSegmentSchema] = []
    class Config:
        from_attributes = True

# Source Reference
class WikiSourceSchema(BaseModel):
    id: str
    video_id: str
    start_timestamp: int
    end_timestamp: int
    quote_text: Optional[str] = None
    context_note: Optional[str] = None
    video_title: Optional[str] = None
    video_thumbnail: Optional[str] = None
    twitch_video_id: Optional[str] = None
    class Config:
        from_attributes = True

# Wiki Entry Schemas
class WikiEntryBase(BaseModel):
    title: str
    summary: str
    content: str
    category: str = "Event"
    confidence: float = 1.0
    status: str = "verified"

class WikiEntryCreate(WikiEntryBase):
    streamer_id: str
    slug: Optional[str] = None
    topics: List[str] = []
    entities: List[str] = []
    sources: List[Dict[str, Any]] = []

class WikiEntryResponse(WikiEntryBase):
    id: str
    streamer_id: str
    slug: str
    revision: int
    created_at: datetime
    updated_at: datetime
    topics: List[TopicSchema] = []
    entities: List[EntitySchema] = []
    sources: List[WikiSourceSchema] = []
    related_entries: List[Dict[str, Any]] = []
    class Config:
        from_attributes = True

# Streamer Schemas
class StreamerBase(BaseModel):
    username: str
    display_name: str
    description: Optional[str] = None
    profile_image_url: Optional[str] = None
    offline_image_url: Optional[str] = None
    is_live: bool = False
    is_verified: bool = False
    follower_count: int = 0

class StreamerResponse(StreamerBase):
    id: str
    twitch_id: str
    created_at: datetime
    video_count: int = 0
    wiki_count: int = 0
    indexed_video_count: int = 0
    class Config:
        from_attributes = True

class StreamerDetailResponse(StreamerResponse):
    recent_videos: List[VideoResponse] = []
    featured_entries: List[WikiEntryResponse] = []
    top_topics: List[TopicSchema] = []
    top_entities: List[EntitySchema] = []

# Contribution Schemas
class ContributionCreate(BaseModel):
    streamer_id: str
    wiki_entry_id: Optional[str] = None
    contribution_type: str
    title: str
    description: Optional[str] = None
    content_diff: Optional[Dict[str, Any]] = None

class ContributionReview(BaseModel):
    status: str # approved, rejected
    review_comment: Optional[str] = None

class ContributionResponse(BaseModel):
    id: str
    streamer_id: str
    wiki_entry_id: Optional[str] = None
    user_id: str
    contribution_type: str
    title: str
    description: Optional[str] = None
    content_diff: Optional[Dict[str, Any]] = None
    status: str
    review_comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user_name: Optional[str] = None
    streamer_name: Optional[str] = None
    wiki_title: Optional[str] = None
    class Config:
        from_attributes = True

# Search & QA Schemas
class SearchQuery(BaseModel):
    query: str
    streamer_id: Optional[str] = None
    limit: int = 10

class SearchResultItem(BaseModel):
    id: str
    type: str # wiki_entry, video_moment, topic
    title: str
    summary: str
    stream_title: Optional[str] = None
    timestamp: Optional[int] = None
    end_timestamp: Optional[int] = None
    video_id: Optional[str] = None
    twitch_video_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    relevance_score: float = 0.0
    slug: Optional[str] = None
    category: Optional[str] = None
    streamer_username: Optional[str] = None

class AskResponse(BaseModel):
    question: str
    answer: str
    is_grounded: bool
    relevant_entries: List[WikiEntryResponse] = []
    citations: List[SearchResultItem] = []

# Job Schema
class ProcessingJobResponse(BaseModel):
    id: str
    video_id: str
    job_type: str
    status: str
    progress: int
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    video_title: Optional[str] = None
    class Config:
        from_attributes = True

