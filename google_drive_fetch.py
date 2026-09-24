"""
Google Drive Fetch Module for Tropicozy
Fetches videos, music, and images from Google Drive folders using Service Account credentials.
Supports weighted random reposting when all items have been published.
"""
import os
import sys
import json
import random
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from googleapiclient.http import MediaIoBaseDownload

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

# Google Drive folder IDs
MUSIC_FOLDER_ID = os.getenv("GOOGLE_DRIVE_MUSIC_FOLDER_ID", "1_BE7XGZBUiGUGfXZZVuA22Arek9fOYzs")
IMAGES_FOLDER_ID = os.getenv("GOOGLE_DRIVE_IMAGES_FOLDER_ID", "1433aZGIv1ujDx7l7s7k0NUAdX37wkSpe")
VIDEOS_FOLDER_ID = os.getenv("GOOGLE_DRIVE_VIDEOS_FOLDER_ID", "1JN7vSSwtsw6DVKI8VODgDq3_6qx9xPcS")

GOOGLE_SERVICE_ACCOUNT_KEY = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")

LOCAL_VIDEOS_DIR = Path("Videos")
LOCAL_MUSIC_DIR = Path("Music")
LOCAL_IMAGES_DIR = Path("Images")
PUBLISHED_LOG = Path("published_videos.json")


def get_published_records():
    """Retrieve full history of published items."""
    if PUBLISHED_LOG.exists():
        try:
            with open(PUBLISHED_LOG, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def get_published_names():
    """Get list of video/asset names that were already published."""
    records = get_published_records()
    names = []
    for r in records:
        if isinstance(r, dict):
            names.append(r.get("video_name") or r.get("asset_name", ""))
        elif isinstance(r, str):
            names.append(r)
    return [n for n in names if n]


def get_repost_counts():
    """Count how many times each item has been published."""
    names = get_published_names()
    counts = {}
    for n in names:
        counts[n] = counts.get(n, 0) + 1
    return counts


def get_drive_service():
    """Authenticate and build Google Drive API service."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]

    if not GOOGLE_SERVICE_ACCOUNT_KEY:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_KEY is not set.")

    key_str = GOOGLE_SERVICE_ACCOUNT_KEY.strip()

    # Check if key is a file path
    if os.path.exists(key_str):
        creds = service_account.Credentials.from_service_account_file(key_str, scopes=scopes)
        return build("drive", "v3", credentials=creds)

    # Check if key is JSON content
    if key_str.startswith("{"):
        info = json.loads(key_str)
        creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
        return build("drive", "v3", credentials=creds)

    raise ValueError("GOOGLE_SERVICE_ACCOUNT_KEY format unrecognized (not a valid file path or JSON object).")


def list_files_in_folder(service, folder_id, mime_filter=None):
    """List all non-trashed files in a Google Drive folder."""
    if not service or not folder_id:
        return []

    try:
        query = f"'{folder_id}' in parents and trashed=false"
        files = []
        page_token = None

        while True:
            response = service.files().list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType, size)",
                pageToken=page_token,
                pageSize=100
            ).execute()

            for f in response.get("files", []):
                if mime_filter:
                    if any(m in f.get("mimeType", "") for m in mime_filter):
                        files.append(f)
                else:
                    files.append(f)

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        files.sort(key=lambda x: x.get("name", ""))
        return files
    except Exception as e:
        print(f"Error listing files in folder {folder_id}: {e}")
        return []


def download_file(service, file_info, local_path):
    """Download a file from Google Drive."""
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"  Downloading '{file_info['name']}'...")
    request = service.files().get_media(fileId=file_info["id"])
    with open(local_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"  Progress: {int(status.progress() * 100)}%")
    print(f"  ✅ Saved: {local_path}")
    return local_path


def fetch_media_assets(allow_repost=True):
    """
    Fetch 1 visual asset (video or image) and 1 tropical music track.
    
    Returns:
        dict: {
            'visual_path': Path,
            'visual_name': str,
            'visual_type': 'video' | 'image',
            'music_path': Path,
            'music_name': str
        }
    """
    LOCAL_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    service = get_drive_service()
    if not service:
        print("❌ Failed to initialize Google Drive service.")
        return None

    published_names = get_published_names()
    repost_counts = get_repost_counts()

    # 1. Fetch Visual Asset (Primary: Videos, Fallback: Images)
    video_files = list_files_in_folder(service, VIDEOS_FOLDER_ID, mime_filter=["video/"])
    print(f"Found {len(video_files)} video(s) in Drive.")

    selected_visual = None
    visual_type = "video"

    # Filter unpublished videos
    unpublished_videos = [v for v in video_files if v["name"] not in published_names]

    if unpublished_videos:
        selected_visual = random.choice(unpublished_videos)
        print(f"✨ Selected new unpublished video: {selected_visual['name']}")
    elif video_files and allow_repost:
        # Weighted random selection: lower repost count = higher weight
        weights = [max(1, 100 // (repost_counts.get(v["name"], 0) + 1)) for v in video_files]
        selected_visual = random.choices(video_files, weights=weights, k=1)[0]
        count = repost_counts.get(selected_visual["name"], 0)
        print(f"🔄 Reposting video (previously posted {count}x): {selected_visual['name']}")
    else:
        # Fallback to images
        print("No videos found. Checking images folder...")
        image_files = list_files_in_folder(service, IMAGES_FOLDER_ID, mime_filter=["image/"])
        if image_files:
            unpublished_images = [img for img in image_files if img["name"] not in published_names]
            if unpublished_images:
                selected_visual = random.choice(unpublished_images)
            else:
                selected_visual = random.choice(image_files)
            visual_type = "image"
            print(f"🖼️ Selected image: {selected_visual['name']}")

    if not selected_visual:
        print("❌ No visual assets found in Videos or Images folders.")
        return None

    # Download visual asset
    if visual_type == "video":
        visual_path = LOCAL_VIDEOS_DIR / selected_visual["name"]
    else:
        visual_path = LOCAL_IMAGES_DIR / selected_visual["name"]

    if not visual_path.exists() or visual_path.stat().st_size == 0:
        download_file(service, selected_visual, visual_path)
    else:
        print(f"  Visual asset already cached locally: {visual_path.name}")

    # 2. Fetch Tropical Music Track
    music_files = list_files_in_folder(service, MUSIC_FOLDER_ID, mime_filter=["audio/"])
    print(f"Found {len(music_files)} music track(s) in Drive.")

    selected_music = None
    if music_files:
        selected_music = random.choice(music_files)
        print(f"🎵 Selected tropical music track: {selected_music['name']}")
        music_path = LOCAL_MUSIC_DIR / selected_music["name"]
        if not music_path.exists() or music_path.stat().st_size == 0:
            download_file(service, selected_music, music_path)
        else:
            print(f"  Music track already cached locally: {music_path.name}")
    else:
        music_path = None
        print("⚠️ No music tracks found in Music folder.")

    return {
        "visual_path": str(visual_path),
        "visual_name": selected_visual["name"],
        "visual_type": visual_type,
        "music_path": str(music_path) if music_path else None,
        "music_name": selected_music["name"] if selected_music else None
    }


if __name__ == "__main__":
    assets = fetch_media_assets()
    print("Fetch result:", assets)
