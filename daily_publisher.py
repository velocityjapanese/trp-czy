"""
Daily Publisher for Tropicozy
Generates tropical music & tropical vibes metadata using Pollinations AI,
and uploads processed videos to YouTube.
"""
import os
import sys
import json
import random
import requests
import datetime
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

# Import YouTube upload function
try:
    from upload.upload_to_youtube import upload_to_youtube
except ImportError:
    from trp_czy.upload.upload_to_youtube import upload_to_youtube

PUBLISHED_LOG = Path("published_videos.json")
POLLINATIONS_KEY = os.getenv("POLLINATIONS_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gemini-fast")
GEN_API = "https://gen.pollinations.ai"

# Fallback titles explicitly focused on Tropical Music & Tropical Vibes (NOT lo-fi)
FALLBACK_TITLES = [
    "Tropical Sunset Melodies 🌴 Soothing Island Breeze & Ambient Beats",
    "Rainforest Canopy Drift 🦜 Calming Tropical Music & Nature Sounds",
    "Azure Lagoon Harmonies 🌊 Relaxing Tropical Island Soundscape",
    "Emerald Jungle Serenity 🌺 Peaceful Tropical Music to Unwind",
    "Sunny Island Horizon ☀️ Warm Tropical Music & Gentle Waves",
    "Paradise Drift 🥥 Calming Tropical Rhythms for Stress Relief",
    "Golden Sand Melodies 🌴 Relaxing Tropical Chillout Music",
    "Lush Canopy Sunrise 🦜 Beautiful Tropical Morning Ambient Music",
    "Breezy Coral Bay 🏝️ Uplifting Tropical Vibes & Warm Melodies",
    "Exotic Island Dreams 🌺 Soothing Tropical Music for Relaxation",
    "Caribbean Tide Groove 🌊 Chill Tropical Sounds & Ocean Waves",
    "Macaw Haven Sanctuary 🦜 Tropical Rainforest Ambient & Melodic Drift",
    "Whispering Palms 🌴 Peaceful Tropical Island Harmony",
    "Sun-Kissed Shoreline ☀️ Relaxing Tropical Atmosphere & Beats",
    "Turquoise Waters & Warm Winds 🌺 Calming Tropical Music Escape",
    "Tropical Twilight Chill 🌴 Soothing Evening Rainforest Sounds",
    "Crystal Lagoon Melodies 🌊 Gentle Tropical Ocean Breeze",
    "Island Solitude & Sunshine 🥥 Warm Tropical Beats for Deep Focus",
    "Jungle River Reflections 🦜 Tranquil Tropical Ambience & Acoustic Warmth",
    "Wild Canopy Harmonies 🌴 Pure Tropical Summer Music"
]

FALLBACK_DESCRIPTIONS = [
    (
        "Welcome to your tropical music paradise on Tropicozy! 🌴 Let the soothing rhythms, warm island breeze, "
        "and lush rainforest melodies sweep away your stress. Whether you are relaxing, working, or dreaming "
        "of turquoise oceans and exotic canopies, this tropical soundscape brings eternal sunshine to your day. 🌺🦜\n\n"
        "✨ Subscribe to Tropicozy for your daily dose of tropical vibes and relaxing music!\n"
        "💬 Where is your favorite tropical place in the world? Let us know below! 🥥\n\n"
        "#tropicalmusic #tropicalvibes #tropicozy #islandvibes #caribbeanvibes #relaxingmusic #naturemusic #rainforestvibes #summermusic #shorts"
    ),
    (
        "Escape into the emerald heart of the rainforest with Tropicozy 🦜🌿 Immerse yourself in calming tropical music "
        "paired with the vibrant sights and sounds of paradise macaws and gentle breezes. Designed to rejuvenate your spirit, "
        "calm your mind, and surround you with warm, positive energy. ☀️🌴\n\n"
        "🔔 Tap subscribe to never miss a tropical music journey with Tropicozy!\n"
        "👍 Drop a 🌴 if you felt instant peace listening to this track!\n\n"
        "#tropicalmusic #tropicalvibes #tropicozy #chillmusic #islandbeats #rainforestambient #naturevibes #relaxingsounds #shorts"
    ),
    (
        "Feel the gentle rhythm of ocean tides and rustling palm trees on Tropicozy! 🌊🥥 This tropical music track "
        "is crafted to give you that carefree, sun-drenched holiday feeling wherever you are. Let the warm melodies "
        "lift your mood and invite total tranquility. 🌺🌴\n\n"
        "🎶 Hit like and subscribe to Tropicozy to keep the tropical summer vibes alive all year!\n"
        "💬 What does your perfect island day look like? Share in the comments!\n\n"
        "#tropicalmusic #tropicalvibes #tropicozy #summerchill #caribbeansounds #peacefulmusic #positivevibes #shorts"
    ),
    (
        "Close your eyes and breathe in the warm island air with Tropicozy 🌴☀️ Experience uplifting, peaceful "
        "tropical music harmonies blending with exotic rainforest ambience. Perfect soundtrack for unwinding after a long day, "
        "meditating, or bringing calm energy to your space. 🦜🌸\n\n"
        "✨ Welcome to the Tropicozy family — subscribe for daily relaxing tropical music!\n"
        "💬 Comment your dream vacation spot below! 🏝️\n\n"
        "#tropicalmusic #tropicalvibes #tropicozy #islandlife #relaxingbeats #ambientmusic #summermusic #paradise #shorts"
    )
]


def generate_tropical_metadata(asset_name="", music_name=""):
    """
    Generate tropical music & tropical vibes metadata using Pollinations AI.
    Strictly focuses on tropical vibes/music and explicitly excludes lo-fi.
    """
    prompt = (
        "You are the creative director for 'Tropicozy', a popular YouTube music channel dedicated to "
        "TROPICAL MUSIC and TROPICAL VIBES.\n\n"
        "IMPORTANT RULES:\n"
        "- This channel is strictly about TROPICAL MUSIC, island vibes, sunny beaches, lush rainforests, "
        "and exotic wildlife (macaws, palms, turquoise ocean waters).\n"
        "- DO NOT use the word 'lo-fi' or 'lofi'. This is NOT a lo-fi channel. It is a TROPICAL MUSIC channel.\n"
        "- Emphasize feelings of warm sunshine, soothing island instruments (acoustic guitars, marimba, steel pans, gentle synth pads), "
        "exotic bird songs, peaceful ocean tides, and tranquil holiday relaxation.\n"
        "- Generate an engaging, high-CTR YouTube Short title (maximum 75 characters) with 1-2 relevant tropical emojis (🌴, 🦜, 🌺, ☀️, 🌊).\n"
        "- Generate a rich, immersive description (3-4 sentences) that transports listeners to a tropical paradise, "
        "includes a friendly call-to-action to like and subscribe to Tropicozy, asks an engaging question for the comments, "
        "and concludes with relevant hashtags like #tropicalmusic #tropicalvibes #tropicozy #islandvibes #caribbeanvibes #relaxingmusic #shorts.\n\n"
        f"Context details: Visual asset name: '{asset_name}', Soundtrack title: '{music_name}'.\n\n"
        "Return ONLY a valid JSON object without markdown formatting, with this exact schema:\n"
        "{\n"
        '  "title": "<tropical music title under 75 chars>",\n'
        '  "description": "<rich atmospheric description with calls to action and hashtags>",\n'
        '  "tags": ["tropical music", "tropical vibes", "tropicozy", "island vibes", "caribbean vibes", "relaxing music", "summer music", "nature sounds", "ambient music"]\n'
        "}"
    )

    if POLLINATIONS_KEY:
        models_to_try = [AI_MODEL, "gemini-flash-lite-3.1", "openai-fast", "mistral"]
        for attempt in range(len(models_to_try)):
            model = models_to_try[attempt]
            try:
                print(f"[metadata] Requesting tropical music metadata from Pollinations ({model})...")
                res = requests.post(
                    f"{GEN_API}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {POLLINATIONS_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.85
                    },
                    timeout=30
                )
                if res.status_code == 200:
                    content = res.json()["choices"][0]["message"]["content"].strip()
                    # Clean markdown code blocks if present
                    if content.startswith("```"):
                        content = content.split("```")[1]
                        if content.startswith("json"):
                            content = content[4:]
                    content = content.strip()
                    data = json.loads(content)
                    title = data.get("title", "").strip().replace('"', '')
                    description = data.get("description", "").strip()
                    tags = data.get("tags", [
                        "tropicozy", "tropical music", "tropical vibes", "island vibes",
                        "caribbean vibes", "relaxing music", "summer music", "nature sounds"
                    ])

                    # Ensure 'lofi' is filtered out if model hallucinated it
                    title = title.replace("lo-fi", "tropical").replace("Lo-Fi", "Tropical").replace("lofi", "tropical")
                    description = description.replace("lo-fi", "tropical").replace("Lo-Fi", "Tropical").replace("lofi", "tropical")

                    if title and description:
                        print(f"✅ Generated Title: {title}")
                        return title, description, tags
            except Exception as e:
                print(f"[metadata] Pollinations attempt {attempt+1} ({model}) failed: {e}")

    # Fallback to curated tropical titles and descriptions
    print("[metadata] Using curated tropical music fallback metadata.")
    title = random.choice(FALLBACK_TITLES)
    desc = random.choice(FALLBACK_DESCRIPTIONS)
    tags = [
        "tropicozy", "tropical music", "tropical vibes", "island vibes",
        "caribbean vibes", "relaxing music", "summer music", "nature sounds", "shorts"
    ]
    return title, desc, tags


def record_published_video(visual_name, music_name, title, youtube_id):
    """Save record to published_videos.json to prevent unwanted repeats."""
    records = []
    if PUBLISHED_LOG.exists():
        try:
            with open(PUBLISHED_LOG, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            records = []

    records.append({
        "video_name": visual_name,
        "music_name": music_name,
        "title": title,
        "youtube_id": youtube_id,
        "published_at": datetime.datetime.utcnow().isoformat() + "Z"
    })

    with open(PUBLISHED_LOG, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"📝 Recorded upload in {PUBLISHED_LOG}")


def publish_video(video_path, asset_info):
    """Generate tropical metadata and upload to YouTube channel."""
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"❌ Cannot publish: file does not exist at {video_path}")
        return False

    visual_name = asset_info.get("visual_name", video_path.name)
    music_name = asset_info.get("music_name", "")

    title, description, tags = generate_tropical_metadata(visual_name, music_name)

    print("\n" + "=" * 60)
    print("READY TO UPLOAD TO YOUTUBE (TROPICOZY)")
    print("=" * 60)
    print(f"Title: {title}")
    print(f"Description (first 100 chars): {description[:100]}...")
    print(f"Tags: {', '.join(tags[:6])}...")
    print("=" * 60 + "\n")

    response = upload_to_youtube(video_path, title, description, tags, category_id="10")
    if response and "id" in response:
        record_published_video(visual_name, music_name, title, response["id"])
        return True
    return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        vid = sys.argv[1]
        dummy_info = {"visual_name": Path(vid).name, "music_name": ""}
        publish_video(vid, dummy_info)
    else:
        print("Usage: python daily_publisher.py <path_to_video>")
