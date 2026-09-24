"""
Tropicozy YouTube Automation Pipeline
Full End-to-End Long-Form Video Orchestrator:
1. Fetches Video, Audio, Image triplets from Google Drive (or local folders)
2. Auto-upscales to 1080p Full HD (Lanczos + Unsharp)
3. Generates high-CTR 1280x720 custom Tropical Music thumbnail
4. Renders 1-Hour Full HD Video (Forward + Reverse ping-pong seamless loop)
5. Generates high-converting SEO metadata for Tropical Music & publishes to YouTube
6. Automatically cleans up rendered video to conserve disk space
"""
import os
import sys
import json
import glob
import random
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

from google_drive_fetch import fetch_assets_triplet
from thumbnail_generator import create_tropical_thumbnail, TROPICAL_HOOKS
from video_generator import build_tropical_longform_video

PUBLISHED_LOG = "published_videos.json"
ALLOW_REPOST = os.getenv("ALLOW_REPOST", "true").lower() == "true"
CHANNEL_NAME = os.getenv("CHANNEL_NAME", "Tropicozy")
POLLINATIONS_KEY = os.getenv("POLLINATIONS_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gemini-fast")
GEN_API = "https://gen.pollinations.ai"


def get_published_history():
    if os.path.exists(PUBLISHED_LOG):
        try:
            with open(PUBLISHED_LOG, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_published_entry(video_name, audio_name, image_name, yt_video_id=None, title=""):
    history = get_published_history()
    entry = {
        "video_file": os.path.basename(video_name),
        "audio_file": os.path.basename(audio_name),
        "image_file": os.path.basename(image_name) if image_name else "",
        "youtube_id": yt_video_id,
        "youtube_url": f"https://youtu.be/{yt_video_id}" if yt_video_id else "LOCAL_RENDER",
        "title": title,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    history.append(entry)
    with open(PUBLISHED_LOG, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    print(f"[LOG] Saved publication record to {PUBLISHED_LOG}")


def generate_youtube_metadata(audio_path, video_path):
    """
    Generate high-converting SEO Tropical Music title, description, and tags.
    Explicitly focused on Tropical Music & Tropical Vibes (NOT lo-fi).
    """
    base_name = os.path.splitext(os.path.basename(audio_path))[0].replace("_", " ").title()

    prompt = (
        "You are the creative director for 'Tropicozy', a popular YouTube music channel featuring "
        "1-HOUR LONG-FORM TROPICAL MUSIC & TROPICAL VIBES.\n\n"
        "STRICT GUIDELINES:\n"
        "- The content is strictly TROPICAL MUSIC, warm island beats, lush rainforest atmosphere, "
        "gentle ocean waves, sunny beach breezes, and exotic wildlife (macaws, tropical flora).\n"
        "- DO NOT use the word 'lo-fi' or 'lofi'. This is NOT a lo-fi channel.\n"
        "- Generate a high-CTR YouTube title (max 95 chars) formatted for 1-hour videos, e.g. "
        f"'1 Hour Tropical Island Music | {base_name} · Relaxing Summer Beats & Ocean Vibes (1080p HD)'\n"
        "- Generate an engaging, atmospheric description (4-6 sentences) inviting listeners to relax, work, study, or sleep "
        "to soothing tropical rhythms, asking for their favorite tropical paradise in the comments, "
        "and encouraging subscriptions to Tropicozy.\n"
        "- Include relevant hashtags: #tropicalmusic #tropicalvibes #tropicozy #islandvibes #caribbeanmusic #relaxingmusic #1hourmusic\n\n"
        f"Audio track: '{base_name}'. Visual asset: '{os.path.basename(video_path)}'.\n\n"
        "Return ONLY a valid JSON object without markdown fences, with this exact schema:\n"
        "{\n"
        '  "title": "<title under 95 chars>",\n'
        '  "description": "<rich description>",\n'
        '  "tags": ["tropical music", "1 hour tropical music", "tropical vibes", "tropicozy", "relaxing music", "island vibes", "caribbean vibes", "summer beats", "rainforest ambience", "study music", "sleep music"]\n'
        "}"
    )

    if POLLINATIONS_KEY:
        try:
            res = requests.post(
                f"{GEN_API}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {POLLINATIONS_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": AI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.85
                },
                timeout=30
            )
            if res.status_code == 200:
                raw = res.json()["choices"][0]["message"]["content"].strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                data = json.loads(raw.strip())
                title = data.get("title", "").strip().replace('"', '')
                desc = data.get("description", "").strip()
                tags = data.get("tags", [])

                title = title.replace("lo-fi", "tropical").replace("Lo-Fi", "Tropical").replace("lofi", "tropical")
                desc = desc.replace("lo-fi", "tropical").replace("Lo-Fi", "Tropical").replace("lofi", "tropical")

                if title and desc:
                    return title, desc, tags
        except Exception as e:
            print(f"[METADATA NOTE] Pollinations AI fallback: {e}")

    # Curated high-converting long-form fallback templates
    titles_templates = [
        f"1 Hour Tropical Island Music | {base_name} · Relaxing Summer Beats & Ocean Vibes (1080p HD)",
        f"Escape to Paradise 🌴 {base_name} · 1 Hour Calming Tropical Music & Rainforest Ambience",
        f"Sun-Drenched Island Chillout | {base_name} (1 Hour Pure Tropical Vibes & Gentle Waves)",
        f"Canopy Sunset Melodies 🦜 {base_name} · 1 Hour Soothing Tropical Nature & Acoustic Warmth",
        f"Warm Ocean Breeze & Tropical Beats | {base_name} · 1 Hour Stress Relief & Deep Focus",
        f"Caribbean Solitude & Emerald Tides | {base_name} (1 Hour Peaceful Tropical Music)"
    ]
    title = random.choice(titles_templates)

    desc = (
        f"Immerse yourself in 1 hour of deep tropical relaxation, sunny island rhythms, and gentle rainforest melodies with '{base_name}'.\n\n"
        f"Escape the stress of everyday life and let the warm sunshine, turquoise waves, and soothing acoustic harmonies "
        f"transport you to a tranquil island paradise. Perfectly crafted for relaxation, deep study sessions, creative focus, meditation, or peaceful sleep.\n\n"
        f"🌺 ABOUT TROPICOZY:\n"
        f"Tropicozy is your sanctuary for uplifting tropical music, exotic nature ambiences, and sunny soundscapes.\n\n"
        f"✨ Key Highlights:\n"
        f"• 1 Hour continuous seamless tropical flow in Full HD 1080p\n"
        f"• High-fidelity acoustic guitars, island marimba, and soothing ambient pads\n"
        f"• Natural rainforest birds and gentle ocean tide frequencies\n"
        f"• Ideal background music for work, reading, yoga, and relaxation\n\n"
        f"🎧 Best enjoyed with headphones or speakers at a gentle volume.\n"
        f"🔔 Subscribe to Tropicozy to join our island family and enjoy weekly tropical music journeys!\n"
        f"💬 Where in the world is your dream tropical getaway? Let us know in the comments below! 🌴🥥\n\n"
        f"#tropicalmusic #tropicalvibes #tropicozy #1hourmusic #islandvibes #caribbeanvibes #relaxingmusic #summerbeats #rainforestambient #naturemusic #studymusic"
    )

    tags = [
        "tropical music", "1 hour tropical music", "tropical vibes", "tropicozy",
        "relaxing music", "island vibes", "caribbean vibes", "summer beats",
        "rainforest ambience", "study music", "sleep music", "nature sounds",
        "peaceful music", "1 hour relaxation", "summer music", "island beats"
    ]

    return title, desc, tags


def run_pipeline(duration=3600, dry_run=False, video_override=None, audio_override=None):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_thumb_dir = os.path.join(script_dir, "output_thumbnails")
    output_video_dir = os.path.join(script_dir, "output_videos")

    os.makedirs(output_thumb_dir, exist_ok=True)
    os.makedirs(output_video_dir, exist_ok=True)

    print("\n" + "=" * 65)
    print(f"      TROPICOZY ({CHANNEL_NAME}) - 1-HOUR VIDEO AUTOMATION PIPELINE")
    print("=" * 65)

    # Step 1: Fetch triplet
    if video_override and audio_override:
        vid_path = video_override
        aud_path = audio_override
        img_path = None
        is_repost = False
    else:
        vid_path, aud_path, img_path, is_repost = fetch_assets_triplet(allow_repost=ALLOW_REPOST)

    if not vid_path or not aud_path:
        print("[ERROR] Could not fetch required video and audio assets.")
        return False

    print(f"\n[STEP 1] Assets Selected:")
    print(f"  • Video: {os.path.basename(vid_path)}")
    print(f"  • Audio: {os.path.basename(aud_path)}")
    print(f"  • Image: {os.path.basename(img_path) if img_path else 'Extracting frame from video'}")

    # If no thumbnail image, extract frame at 2s from video
    if not img_path or not os.path.exists(img_path):
        os.makedirs(os.path.join(script_dir, "input_images"), exist_ok=True)
        img_path = os.path.join(script_dir, "input_images", f"frame_{os.path.splitext(os.path.basename(vid_path))[0]}.jpg")
        import subprocess
        subprocess.run(["ffmpeg", "-y", "-ss", "00:00:02", "-i", vid_path, "-frames:v", "1", img_path], check=True)

    # Step 2: Generate Thumbnail
    safe_name = "".join(c for c in os.path.splitext(os.path.basename(aud_path))[0] if c.isalnum() or c in (" ", "_", "-")).strip()
    thumb_output = os.path.join(output_thumb_dir, f"Thumb_{safe_name}.jpg")

    hook = random.choice(TROPICAL_HOOKS)
    print(f"\n[STEP 2] Creating 1280x720 Thumbnail with Hook: '{hook['main']}'...")
    create_tropical_thumbnail(img_path, thumb_output, main_text=hook["main"], sub_text=hook["sub"], badge_text=hook.get("badge"))

    # Step 3: Render Full Video
    dur_label = f"{duration // 60}min" if duration >= 60 else f"{duration}s"
    final_video_path = os.path.join(output_video_dir, f"Tropicozy_{safe_name}_{dur_label}.mp4")

    print(f"\n[STEP 3] Rendering {dur_label} 1080p HD Video...")
    success = build_tropical_longform_video(
        input_video=vid_path,
        input_audio=aud_path,
        output_path=final_video_path,
        duration_seconds=duration,
        remove_watermark=True,
        upscale_to_1080p=True
    )

    if not success:
        print("[ERROR] Video generation failed.")
        return False

    # Step 4: Metadata & Publishing
    title, desc, tags = generate_youtube_metadata(aud_path, vid_path)
    print(f"\n[STEP 4] Generated YouTube Metadata:")
    print(f"  • Title: {title}")
    print(f"  • Tags: {', '.join(tags[:6])}...")

    if dry_run:
        print(f"\n[DRY RUN] Completed. Video saved at: {final_video_path}")
        print(f"[DRY RUN] Thumbnail saved at: {thumb_output}")
        save_published_entry(vid_path, aud_path, img_path, yt_video_id=None, title=title)
        return True

    # Step 5: Upload to YouTube & Set Custom Thumbnail
    try:
        from publish_youtube import upload_to_youtube, set_video_thumbnail
        print(f"\n[STEP 5] Uploading 1-Hour Video to YouTube...")
        video_id = upload_to_youtube(final_video_path, title, desc, tags=tags)
        if video_id:
            set_video_thumbnail(video_id, thumb_output)
            save_published_entry(vid_path, aud_path, img_path, yt_video_id=video_id, title=title)
            print(f"🎉 SUCCESS! Published to YouTube: https://youtu.be/{video_id}")

            # Step 6: Cleanup rendered video to free disk space
            if os.path.exists(final_video_path):
                try:
                    os.remove(final_video_path)
                    print(f"[CLEANUP] Deleted rendered video to save disk space: {final_video_path}")
                except Exception:
                    pass

            return True
    except Exception as e:
        print(f"[YOUTUBE NOTE] YouTube API upload error: {e}")
        save_published_entry(vid_path, aud_path, img_path, yt_video_id=None, title=title)
        return False


if __name__ == "__main__":
    dur = 3600
    is_dry = "--dry-run" in sys.argv
    for idx, arg in enumerate(sys.argv):
        if arg == "--duration" and idx + 1 < len(sys.argv):
            dur = int(sys.argv[idx + 1])
    run_pipeline(duration=dur, dry_run=is_dry)
