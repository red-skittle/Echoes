from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Streamer, Video, WikiEntry, WikiEntrySource

SAMPLE_STREAMER = "mossybytes"
SAMPLE_VIDEOS = [
    {"key": "sample-stream-1", "title": "A very normal Minecraft Monday", "date": datetime(2025, 10, 24, tzinfo=timezone.utc), "duration": 10800},
    {"key": "sample-stream-2", "title": "Building a home (for real this time)", "date": datetime(2025, 10, 17, tzinfo=timezone.utc), "duration": 9000},
    {"key": "sample-stream-3", "title": "Chat takes the wheel", "date": datetime(2025, 10, 10, tzinfo=timezone.utc), "duration": 7200},
]
SAMPLE_ARTICLES = [
    ("The Underneath", "The server’s underground village began as an unexpected discovery beneath spawn.", "Community Lore", "the-underneath", 2538, 3300, "Minecraft"),
    ("The door problem", "Every build session brings a new debate about how many doors a house really needs.", "Running Joke", "the-door-problem", 1450, 1770, "Community builds"),
    ("The first community build", "A tiny spawn house became a shared project and a permanent meeting spot.", "Milestone", "first-community-build", 820, 1240, "Community builds"),
    ("The Underneath expedition", "The community returned with supplies to explore the caves below the village.", "Event", "underneath-expedition", 3970, 4520, "Minecraft"),
    ("Moss the axolotl", "An axolotl discovered during the first expedition became the chat’s unofficial mascot.", "Character", "moss-the-axolotl", 4710, 4900, "Characters"),
    ("The missing staircase", "A staircase build caused more confusion than the cave it was meant to reach.", "Running Joke", "missing-staircase", 5640, 6050, "Community builds"),
    ("Spawn town begins", "Viewers started building homes around the shared spawn house.", "Milestone", "spawn-town-begins", 6680, 7190, "Community builds"),
    ("The great lantern debate", "Chat voted between lantern styles to light the route underground.", "Community Lore", "lantern-debate", 7330, 7610, "Community lore"),
    ("First trip to the Nether", "The group prepared a portal and made its first trip to the Nether together.", "Event", "first-nether-trip", 8100, 8720, "Minecraft"),
    ("The emergency cake", "A cake was placed at spawn as a running joke about emergency supplies.", "Running Joke", "emergency-cake", 1900, 2050, "Community lore"),
    ("A bridge over the ravine", "The group built a safer crossing between spawn and the mine entrance.", "Milestone", "ravine-bridge", 5200, 5780, "Community builds"),
    ("The first group screenshot", "The community gathered at spawn for a screenshot after finishing the bridge.", "Event", "group-screenshot", 7010, 7130, "Community lore"),
]


def seed_demo(db: Session) -> None:
    streamer = db.scalar(select(Streamer).where(Streamer.username == SAMPLE_STREAMER))
    if streamer is None:
        streamer = Streamer(
            username=SAMPLE_STREAMER, display_name="mossybytes",
            description="Cozy games, questionable builds, and a chat that remembers absolutely everything.",
            is_sample=True,
        )
        db.add(streamer)
        db.flush()
    videos: dict[str, Video] = {}
    for item in SAMPLE_VIDEOS:
        video = db.scalar(select(Video).where(Video.streamer_id == streamer.id, Video.title == item["title"]))
        if video is None:
            video = Video(streamer_id=streamer.id, title=item["title"], published_at=item["date"],
                          duration_seconds=item["duration"], status="sample_content", is_sample=True)
            db.add(video)
            db.flush()
        videos[item["key"]] = video
    for i, (title, summary, category, slug, start, end, topic) in enumerate(SAMPLE_ARTICLES):
        entry = db.scalar(select(WikiEntry).where(WikiEntry.slug == slug))
        if entry is None:
            entry = WikiEntry(streamer_id=streamer.id, slug=slug, title=title, summary=summary,
                              body=f"{summary} This is synthetic sample content created to demonstrate Afterlife's source-linked wiki format. It is not derived from a real Twitch broadcast.",
                              category=category, status="sample", is_sample=True)
            db.add(entry)
            db.flush()
            video_key = "sample-stream-1" if i < 10 else "sample-stream-2"
            db.add(WikiEntrySource(wiki_entry_id=entry.id, video_id=videos[video_key].id,
                                   start_seconds=start, end_seconds=end,
                                   citation_note=f"Synthetic demo source reference · {topic}"))
    db.commit()
