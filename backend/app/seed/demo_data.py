import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import (
    User, Streamer, StreamerMembership, Video, VideoAsset,
    Transcript, TranscriptSegment, WikiEntry, WikiEntrySource,
    Topic, Entity, WikiRelationship, Contribution, Embedding
)

def seed_demo_data(db: Session) -> None:
    # Check if streamer already exists
    existing = db.query(Streamer).filter_by(username="aria_valkyrie").first()
    if existing:
        return

    print("Seeding Afterlife Demo Data...")

    # 1. Users
    streamer_user = User(
        id=str(uuid.uuid4()),
        twitch_id="tw_user_98765",
        username="aria_valkyrie",
        display_name="Aria Valkyrie",
        email="aria@afterlife.wiki",
        avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=256&auto=format&fit=crop&q=80",
        role="streamer"
    )
    mod_user = User(
        id=str(uuid.uuid4()),
        twitch_id="tw_user_54321",
        username="lore_master_kai",
        display_name="Kai | Lore Archivist",
        email="kai@afterlife.wiki",
        avatar_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=256&auto=format&fit=crop&q=80",
        role="moderator"
    )
    viewer_user = User(
        id=str(uuid.uuid4()),
        twitch_id="tw_user_11223",
        username="pixel_wanderer",
        display_name="PixelWanderer99",
        email="pixel@afterlife.wiki",
        avatar_url="https://images.unsplash.com/photo-1517841905240-472988babdf9?w=256&auto=format&fit=crop&q=80",
        role="contributor"
    )
    db.add_all([streamer_user, mod_user, viewer_user])
    db.flush()

    # 2. Streamer Profile
    streamer = Streamer(
        id=str(uuid.uuid4()),
        twitch_id="tw_aria_valkyrie",
        username="aria_valkyrie",
        display_name="Aria Valkyrie",
        description="Full-time explorer, sandbox storyteller, and architecture enthusiast. Building civilizations, uncovering ancient underground lore, and laughing through accidental disasters with chat.",
        profile_image_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=512&auto=format&fit=crop&q=80",
        offline_image_url="https://images.unsplash.com/photo-1511512578047-dfb367046420?w=1280&auto=format&fit=crop&q=80",
        is_live=False,
        is_verified=True,
        follower_count=248500
    )
    db.add(streamer)
    db.flush()

    # Streamer Membership
    membership = StreamerMembership(
        id=str(uuid.uuid4()),
        user_id=streamer_user.id,
        streamer_id=streamer.id,
        role="owner"
    )
    mod_membership = StreamerMembership(
        id=str(uuid.uuid4()),
        user_id=mod_user.id,
        streamer_id=streamer.id,
        role="moderator"
    )
    db.add_all([membership, mod_membership])

    # 3. Topics
    topics_data = [
        ("Minecraft", "minecraft", "Open-world survival sandbox gameplay and creative projects."),
        ("Underground Lore", "underground-lore", "Historical expeditions into DeepHaven and subterranean ruins."),
        ("Speedrunning", "speedrunning", "Nether fortress routing and Ender Dragon timing challenges."),
        ("Community Builds", "community-builds", "Massive viewer-participatory structures and megabases."),
        ("Inside Jokes", "inside-jokes", "Memorable stream gags, running chat memes, and slip-ups."),
        ("Redstone Engineering", "redstone-engineering", "Complex automated contraptions and accidental explosions."),
        ("Collaborations", "collaborations", "Guest appearances, server wars, and crossover episodes.")
    ]
    topics_map = {}
    for name, slug, desc in topics_data:
        topic = Topic(id=str(uuid.uuid4()), name=name, slug=slug, description=desc)
        db.add(topic)
        topics_map[slug] = topic
    db.flush()

    # 4. Entities
    entities_data = [
        ("The Underground Village (DeepHaven)", "Location", "A sprawling subterranean settlement first discovered at Y=-42 during Season 2."),
        ("Professor Beaks", "Character", "A blue parrot adopted in Episode 14 who repeatedly sat on redstone pressure plates."),
        ("The Molten Forge", "Location", "A lava-powered community blacksmith station built above the central magma crater."),
        ("The Obsidian Monolith", "Location", "A mysterious 64-block tall monument erected overnight to commemorate the Season 1 finale."),
        ("The Clutch Water Bucket Incident", "Meme", "A legendary failed water bucket drop from world height that ended a 70-hour hardcore streak."),
        ("Ironclad Golem 'Bartholomew'", "Character", "An oversized Iron Golem spawned to defend the town square who refused to fight zombies.")
    ]
    entities_map = {}
    for name, etype, desc in entities_data:
        ent = Entity(id=str(uuid.uuid4()), streamer_id=streamer.id, name=name, entity_type=etype, description=desc)
        db.add(ent)
        entities_map[name] = ent
    db.flush()

    # 5. Videos
    now = datetime.utcnow()
    v1 = Video(
        id=str(uuid.uuid4()),
        streamer_id=streamer.id,
        twitch_video_id="v218940121",
        title="Expedition DeepHaven: Down to Y=-58 | S2 Finale Prep",
        description="The monumental stream where we broke through the bedrock ceiling cave and made contact with the ancient underground village.",
        published_at=now - timedelta(days=28),
        duration_seconds=14280, # ~3h 58m
        thumbnail_url="https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=640&auto=format&fit=crop&q=80",
        view_count=84200,
        stream_type="archive",
        is_indexed=True,
        processing_status="completed"
    )
    v2 = Video(
        id=str(uuid.uuid4()),
        streamer_id=streamer.id,
        twitch_video_id="v219488302",
        title="Building The Molten Forge & Adopting Professor Beaks",
        description="Constructing our multi-tier automated industrial smelter and meeting the bird that almost wiped the entire redstone grid.",
        published_at=now - timedelta(days=21),
        duration_seconds=12640, # ~3h 30m
        thumbnail_url="https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=640&auto=format&fit=crop&q=80",
        view_count=62100,
        stream_type="archive",
        is_indexed=True,
        processing_status="completed"
    )
    v3 = Video(
        id=str(uuid.uuid4()),
        streamer_id=streamer.id,
        twitch_video_id="v220199411",
        title="The Great Flooding of DeepHaven + Hardcore World Record Attempt",
        description="An accidental water valve breakthrough triggers a cascading water emergency across the lower districts.",
        published_at=now - timedelta(days=12),
        duration_seconds=15600, # ~4h 20m
        thumbnail_url="https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=640&auto=format&fit=crop&q=80",
        view_count=98500,
        stream_type="archive",
        is_indexed=True,
        processing_status="completed"
    )
    v4 = Video(
        id=str(uuid.uuid4()),
        streamer_id=streamer.id,
        twitch_video_id="v221054923",
        title="Community Build Day: Restoring the Obsidian Monolith",
        description="Chat voted on architectural plans to renovate the sacred monument with amethyst crystals and glow lichen.",
        published_at=now - timedelta(days=4),
        duration_seconds=10800, # 3 hours
        thumbnail_url="https://images.unsplash.com/photo-1542751371-adc38448a05e?w=640&auto=format&fit=crop&q=80",
        view_count=45300,
        stream_type="archive",
        is_indexed=True,
        processing_status="completed"
    )
    db.add_all([v1, v2, v3, v4])
    db.flush()

    # 6. Transcripts & Segments for Video 1 (Discovery)
    t1 = Transcript(
        id=str(uuid.uuid4()),
        video_id=v1.id,
        language="en",
        full_text="Welcome back everyone! Today we are heading down past Y=-40 to investigate the sound of church bells coming through solid deepslate.",
        duration_seconds=14280.0
    )
    db.add(t1)
    db.flush()

    seg1_1 = TranscriptSegment(
        id=str(uuid.uuid4()),
        transcript_id=t1.id,
        start_time=312.0,
        end_time=348.0,
        text="Wait... chat, do you hear that? That's not an ambient cave hum. That's a bell! Dig through here, careful with the gravel!",
        speaker="Aria"
    )
    seg1_2 = TranscriptSegment(
        id=str(uuid.uuid4()),
        transcript_id=t1.id,
        start_time=350.0,
        end_time=415.0,
        text="Look at this cavern! There's an entire wooden settlement completely enclosed in dripstone. Look at those street lamps! We found it!",
        speaker="Aria"
    )
    seg1_3 = TranscriptSegment(
        id=str(uuid.uuid4()),
        transcript_id=t1.id,
        start_time=1420.0,
        end_time=1495.0,
        text="Let's officially name this place DeepHaven. We will build our base around this natural vault.",
        speaker="Aria"
    )
    db.add_all([seg1_1, seg1_2, seg1_3])

    # Transcripts for Video 2 (Beaks & Forge)
    t2 = Transcript(
        id=str(uuid.uuid4()),
        video_id=v2.id,
        language="en",
        full_text="Today we're building the Molten Forge to power all our tools.",
        duration_seconds=12640.0
    )
    db.add(t2)
    db.flush()

    seg2_1 = TranscriptSegment(
        id=str(uuid.uuid4()),
        transcript_id=t2.id,
        start_time=820.0,
        end_time=890.0,
        text="He just flew onto my shoulder! Meet Professor Beaks. He is our chief inspector from now on.",
        speaker="Aria"
    )
    seg2_2 = TranscriptSegment(
        id=str(uuid.uuid4()),
        transcript_id=t2.id,
        start_time=2150.0,
        end_time=2230.0,
        text="NO BEAKS DON'T STEP ON THAT! *alarm sounds* The lava dispenser just triggered! Grab the buckets!",
        speaker="Aria"
    )
    db.add_all([seg2_1, seg2_2])

    # Transcripts for Video 3 (Flooding & Clutch fail)
    t3 = Transcript(
        id=str(uuid.uuid4()),
        video_id=v3.id,
        language="en",
        full_text="Hardcore speedrun and town expansion stream.",
        duration_seconds=15600.0
    )
    db.add(t3)
    db.flush()

    seg3_1 = TranscriptSegment(
        id=str(uuid.uuid4()),
        transcript_id=t3.id,
        start_time=450.0,
        end_time=512.0,
        text="The aqueduct wall gave way! Water is rushing down into the residential quarter! Seal the bulkheads!",
        speaker="Aria"
    )
    seg3_2 = TranscriptSegment(
        id=str(uuid.uuid4()),
        transcript_id=t3.id,
        start_time=4210.0,
        end_time=4280.0,
        text="Watch this MLG water bucket from 150 blocks up. Easy. *splat sound* ...Wait. You have got to be kidding me.",
        speaker="Aria"
    )
    db.add_all([seg3_1, seg3_2])
    db.flush()

    # 7. Wiki Entries (12 rich entries with categories, verified status, and exact timestamps)
    wiki_articles = [
        {
            "slug": "discovery-of-deephaven",
            "title": "The Discovery of DeepHaven (Underground Village)",
            "summary": "The momentous breakthrough at Y=-42 where Aria uncovered a forgotten underground village nestled within a massive dripstone cavern.",
            "category": "Event",
            "confidence": 0.98,
            "status": "verified",
            "content": """## Overview
On stream broadcast **Expedition DeepHaven: Down to Y=-58**, Aria breached the limestone cavern walls at elevation Y=-42 following faint sound cues of a village bell. 

Behind the deepslate formation lay an extraordinarily intact subterranean biome featuring automated lanterns, moss-covered pathways, and five surviving villager librarians.

## Historical Impact
The discovery marked the end of the nomadic wandering era of Season 2 and established the permanent capital of the community. Within two weeks of discovery, chat voted to designate the site **DeepHaven**.

### Key Milestones
- **Elevation:** Y=-42.5
- **Coordinates:** X: -1402, Z: 890
- **First Response:** Immediate fortification of the cavern mouth against phantom spawns.
- **Subsequent Projects:** Creation of the Molten Forge and central library.
""",
            "topics": ["minecraft", "underground-lore"],
            "entities": ["The Underground Village (DeepHaven)"],
            "sources": [
                {"video": v1, "segment": seg1_2, "start": 350, "end": 415, "quote": "Look at this cavern! There's an entire wooden settlement completely enclosed in dripstone.", "note": "Moment of initial cave breakthrough"}
            ]
        },
        {
            "slug": "professor-beaks",
            "title": "Professor Beaks (The Chaotic Familiar)",
            "summary": "A stray cyan parrot adopted during Episode 14 that gained cult status for repeatedly triggering unshielded redstone circuits.",
            "category": "Character",
            "confidence": 0.95,
            "status": "verified",
            "content": """## Biography
**Professor Beaks** was discovered perched atop a solitary jungle wood support beam near the upper cavern entrance during the construction of The Molten Forge.

Despite being tamed with pumpkin seeds, Professor Beaks displayed an uncanny behavioral habit of landing exclusively on calibrated stone pressure plates.

## Notable Incidents
1. **The Smelter Meltdown (Minute 35:50):** Beaks walked across the primary logic gate, toggling all four lava dispensers into continuous dump mode.
2. **The Armor Stand Cascade:** Knocked Aria's backup enchanted Netherite set into an active hopper line.
3. **Official Pardon:** Following the Great Flooding, Beaks was awarded the honorary title of *Grand Inspector of Circuitry*.
""",
            "topics": ["inside-jokes", "minecraft"],
            "entities": ["Professor Beaks", "The Molten Forge"],
            "sources": [
                {"video": v2, "segment": seg2_1, "start": 820, "end": 890, "quote": "He just flew onto my shoulder! Meet Professor Beaks.", "note": "Adoption ceremony"},
                {"video": v2, "segment": seg2_2, "start": 2150, "end": 2230, "quote": "NO BEAKS DON'T STEP ON THAT! The lava dispenser just triggered!", "note": "The famous redstone meltdown incident"}
            ]
        },
        {
            "slug": "the-molten-forge",
            "title": "The Molten Forge",
            "summary": "A mega-scale subterranean smelting factory harnessing natural lava cascades to process 4,000 ores per hour.",
            "category": "Location",
            "confidence": 0.94,
            "status": "verified",
            "content": """## Architecture & Design
Built directly over a geothermal lava fissure in DeepHaven, **The Molten Forge** stands as the economic backbone of the community's survival infrastructure.

Features:
- **8-way Hopper Distribution Network:** Balances incoming raw iron, copper, and gold.
- **Infinite Fuel Injectors:** Continuously fed by dripstone lava collectors.
- **Safety Glass Viewing Gallery:** Installed after Professor Beaks' near-catastrophic tampering incident.
""",
            "topics": ["minecraft", "redstone-engineering", "community-builds"],
            "entities": ["The Molten Forge", "The Underground Village (DeepHaven)"],
            "sources": [
                {"video": v2, "segment": seg2_2, "start": 2150, "end": 2230, "quote": "The lava dispenser just triggered! Grab the buckets!", "note": "Forge testing sequence"}
            ]
        },
        {
            "slug": "the-great-flooding-of-deephaven",
            "title": "The Great Flooding of DeepHaven",
            "summary": "A catastrophic breach of the upper mountain reservoir during an expansion project that submerged lower district workshops.",
            "category": "Event",
            "confidence": 0.99,
            "status": "verified",
            "content": """## Incident Summary
During stream broadcast **The Great Flooding of DeepHaven**, Aria attempted to route water from a mountain lake directly into the automated potion brewery.

A miscalculated TNT excavation cracked an adjacent underwater gravel pocket, dumping an estimated 100,000 virtual gallons into the underground village.

## Community Relief Efforts
Viewers coordinated in chat to suggest exact coordinates for placement of sponges, dirt dams, and drainage channels. Within 45 minutes of frantic gameplay, the floodwaters were contained.
""",
            "topics": ["minecraft", "underground-lore"],
            "entities": ["The Underground Village (DeepHaven)"],
            "sources": [
                {"video": v3, "segment": seg3_1, "start": 450, "end": 512, "quote": "The aqueduct wall gave way! Water is rushing down into the residential quarter!", "note": "Breach point captured live"}
            ]
        },
        {
            "slug": "the-clutch-water-bucket-incident",
            "title": "The Clutch Water Bucket Incident",
            "summary": "A famous clip where Aria boasted about guaranteed MLG water-bucket landing accuracy seconds before plunging directly into a stone ledge.",
            "category": "Inside Joke",
            "confidence": 0.99,
            "status": "verified",
            "content": """## The Meme
"Watch this MLG water bucket from 150 blocks up. Easy."

These words immediately preceded one of the most clipped deaths in channel history. Due to a split-second server tick desync (and hitting the absolute edge of a cobblestone step), the water failed to place in time.

## Channel Legacy
The incident spawned the channel emote `:ariaPlat:` and is referenced whenever any high-altitude maneuver is attempted on stream.
""",
            "topics": ["inside-jokes", "speedrunning"],
            "entities": ["The Clutch Water Bucket Incident"],
            "sources": [
                {"video": v3, "segment": seg3_2, "start": 4210, "end": 4280, "quote": "Watch this MLG water bucket from 150 blocks up. Easy. *splat* ...Wait.", "note": "The original clip and chat reaction"}
            ]
        },
        {
            "slug": "the-obsidian-monolith",
            "title": "The Obsidian Monolith of Mount Solitude",
            "summary": "A towering obsidian and crying obsidian needle erected to mark the completion of the 100-day Hardcore trial.",
            "category": "Location",
            "confidence": 0.92,
            "status": "verified",
            "content": """## Monument Description
Constructed from over 1,400 hand-mined obsidian blocks, the Monolith serves as the channel's central landmark. During **Community Build Day**, chat voted on adding glowing amethyst geodes along its spire.

## Lore
According to community canon written by chat moderators, the Monolith contains a hidden time capsule chest with relics from Season 1.
""",
            "topics": ["community-builds", "minecraft"],
            "entities": ["The Obsidian Monolith"],
            "sources": [
                {"video": v4, "segment": None, "start": 1800, "end": 2100, "quote": "Placing the final crying obsidian block at the apex!", "note": "Spire completion"}
            ]
        },
        {
            "slug": "ironclad-golem-bartholomew",
            "title": "Bartholomew the Pacifist Golem",
            "summary": "A defective or remarkably calm Iron Golem who spent two full seasons handing poppies to baby villagers while hostile mobs burned in sunlight.",
            "category": "Character",
            "confidence": 0.90,
            "status": "verified",
            "content": """## Profile
Spawned using four iron blocks from the first Molten Forge batch, Bartholomew was intended to be the primary defender of DeepHaven's market square.

Instead, Bartholomew acquired a persistent AI bug that prevented him from aggroing onto skeletons or zombies, choosing instead to wander around the central fountain admiring flowers.
""",
            "topics": ["inside-jokes", "underground-lore"],
            "entities": ["Ironclad Golem 'Bartholomew'", "The Underground Village (DeepHaven)"],
            "sources": [
                {"video": v1, "segment": None, "start": 1890, "end": 1960, "quote": "Bartholomew, there is literally a creeper three blocks behind you. Why are you smelling that dandelion?", "note": "Bartholomew's legendary pacifism"}
            ]
        },
        {
            "slug": "redstone-disaster-protocol-zero",
            "title": "Protocol Zero: The Safety Circuit",
            "summary": "A community-designed redstone lockdown mechanism installed across DeepHaven to prevent rogue parrots from detonating blast chambers.",
            "category": "Tutorial",
            "confidence": 0.91,
            "status": "verified",
            "content": """## Overview & Blueprint
Following the infamous *Professor Beaks Meltdown*, chat engineer **Lore Master Kai** drafted a schematic for a two-key verification circuit.

### Circuit Requirements
- 2x Sticky Pistons
- 4x Redstone Repeaters set to 4-tick delay
- Encased tripwires positioned above parrot-flight heights.
""",
            "topics": ["redstone-engineering", "minecraft"],
            "entities": ["Professor Beaks", "The Molten Forge"],
            "sources": [
                {"video": v2, "segment": None, "start": 3600, "end": 3720, "quote": "This lockout system guarantees that even if Beaks dances on the main desk, no lava drops.", "note": "Tutorial demonstration"}
            ]
        }
    ]

    created_entries = {}
    for item in wiki_articles:
        entry = WikiEntry(
            id=str(uuid.uuid4()),
            streamer_id=streamer.id,
            slug=item["slug"],
            title=item["title"],
            summary=item["summary"],
            content=item["content"],
            category=item["category"],
            confidence=item["confidence"],
            status=item["status"],
            revision=1,
            author_id=streamer_user.id
        )
        # Add topics
        for t_slug in item["topics"]:
            if t_slug in topics_map:
                entry.topics.append(topics_map[t_slug])
        # Add entities
        for e_name in item["entities"]:
            if e_name in entities_map:
                entry.entities.append(entities_map[e_name])

        db.add(entry)
        db.flush()
        created_entries[item["slug"]] = entry

        # Add sources
        for s in item["sources"]:
            src = WikiEntrySource(
                id=str(uuid.uuid4()),
                wiki_entry_id=entry.id,
                video_id=s["video"].id,
                segment_id=s["segment"].id if s.get("segment") else None,
                start_timestamp=s["start"],
                end_timestamp=s["end"],
                quote_text=s["quote"],
                context_note=s["note"]
            )
            db.add(src)

    # 8. Relationships between Wiki Entries
    rel1 = WikiRelationship(
        id=str(uuid.uuid4()),
        source_entry_id=created_entries["discovery-of-deephaven"].id,
        target_entry_id=created_entries["the-molten-forge"].id,
        relationship_type="led_to",
        description="The discovery of DeepHaven provided the subterranean crater required to construct The Molten Forge."
    )
    rel2 = WikiRelationship(
        id=str(uuid.uuid4()),
        source_entry_id=created_entries["the-molten-forge"].id,
        target_entry_id=created_entries["professor-beaks"].id,
        relationship_type="introduced",
        description="Professor Beaks was first encountered nesting in the scaffolding of the Forge."
    )
    rel3 = WikiRelationship(
        id=str(uuid.uuid4()),
        source_entry_id=created_entries["professor-beaks"].id,
        target_entry_id=created_entries["redstone-disaster-protocol-zero"].id,
        relationship_type="necessitated",
        description="Beaks' frequent pressure plate triggers forced the engineering team to install Protocol Zero."
    )
    rel4 = WikiRelationship(
        id=str(uuid.uuid4()),
        source_entry_id=created_entries["discovery-of-deephaven"].id,
        target_entry_id=created_entries["the-great-flooding-of-deephaven"].id,
        relationship_type="backdrop_for",
        description="The fragile cavern roof collapsed into the residential quarter during the flood."
    )
    db.add_all([rel1, rel2, rel3, rel4])

    # 9. Community Contributions
    c1 = Contribution(
        id=str(uuid.uuid4()),
        streamer_id=streamer.id,
        wiki_entry_id=created_entries["the-clutch-water-bucket-incident"].id,
        user_id=viewer_user.id,
        contribution_type="add_timestamp",
        title="Add exact frame timestamp for the water block bounce",
        description="The water placed for 1 game tick before the server registered the collision on the slab. Added microsecond precision note.",
        content_diff={"timestamp_precision": "01:10:14.250", "tick_rate": "19.8 TPS"},
        status="approved",
        reviewed_by=mod_user.id,
        review_comment="Great eye! Verified against server logs."
    )
    c2 = Contribution(
        id=str(uuid.uuid4()),
        streamer_id=streamer.id,
        wiki_entry_id=created_entries["discovery-of-deephaven"].id,
        user_id=viewer_user.id,
        contribution_type="correction",
        title="Correct the number of initial librarian villagers",
        description="There were actually 6 librarians; one was hidden behind the compost bin at coordinate -1405, Y=-44.",
        content_diff={"librarian_count_old": 5, "librarian_count_new": 6},
        status="pending",
        review_comment=None
    )
    c3 = Contribution(
        id=str(uuid.uuid4()),
        streamer_id=streamer.id,
        wiki_entry_id=None,
        user_id=viewer_user.id,
        contribution_type="new_article",
        title="The Midnight Nether Wart Heist",
        description="Draft for an article recounting the collaborative raid during Season 2 Episode 8 where chat navigated the fortress maze.",
        content_diff={"draft_title": "The Midnight Nether Wart Heist", "category": "Event", "approx_stream": "v217800111"},
        status="pending",
        review_comment=None
    )
    db.add_all([c1, c2, c3])

    # 10. Generate mock embeddings for search
    import random
    random.seed(42)
    for slug, entry in created_entries.items():
        # 128-dimensional mock vector for cosine similarity test
        vec = [random.uniform(-0.1, 0.1) for _ in range(128)]
        emb = Embedding(
            id=str(uuid.uuid4()),
            entity_type="wiki_entry",
            entity_id=entry.id,
            text_content=f"{entry.title} {entry.summary} {entry.category}",
            vector=vec
        )
        db.add(emb)

    db.commit()
    print("Demo data seeded successfully! Streamer: aria_valkyrie")

