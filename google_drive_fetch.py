"""
Google Drive Integration Module for Tropicozy
Fetches:
1. Video Loops (MP4) from GOOGLE_DRIVE_VIDEO_FOLDER_ID
2. Audio Tracks (MP3/WAV) from GOOGLE_DRIVE_AUDIO_FOLDER_ID
3. Thumbnail Images (JPG/PNG) from GOOGLE_DRIVE_IMAGE_FOLDER_ID

Supports:
- Unpublished track priority
- Infinite circulation mode (Weighted Least-Recently-Used selection)
- Dynamic remixing across video, audio, and thumbnail assets
- Local folder fallback (input_videos, input_audio, input_images)
"""
import os
import io
import json
import sys
import glob
import random
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

GOOGLE_DRIVE_VIDEO_FOLDER_ID = os.getenv("GOOGLE_DRIVE_VIDEO_FOLDER_ID", os.getenv("GOOGLE_DRIVE_VIDEOS_FOLDER_ID", "1JN7vSSwtsw6DVKI8VODgDq3_6qx9xPcS"))
GOOGLE_DRIVE_AUDIO_FOLDER_ID = os.getenv("GOOGLE_DRIVE_AUDIO_FOLDER_ID", os.getenv("GOOGLE_DRIVE_MUSIC_FOLDER_ID", "1_BE7XGZBUiGUGfXZZVuA22Arek9fOYzs"))
GOOGLE_DRIVE_IMAGE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_IMAGE_FOLDER_ID", os.getenv("GOOGLE_DRIVE_IMAGES_FOLDER_ID", "1433aZGIv1ujDx7l7s7k0NUAdX37wkSpe"))
GOOGLE_SERVICE_ACCOUNT_KEY = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY", "service_account.json")

LOCAL_VIDEO_DIR = os.getenv("LOCAL_VIDEO_DIR", "input_videos")
LOCAL_AUDIO_DIR = os.getenv("LOCAL_AUDIO_DIR", "input_audio")
LOCAL_IMAGE_DIR = os.getenv("LOCAL_IMAGE_DIR", "input_images")
PUBLISHED_LOG = "published_videos.json"

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service():
    """Build and return an authorized Google Drive v3 service instance."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        print("[DRIVE] Google API libraries not installed.")
        return None

    if not GOOGLE_SERVICE_ACCOUNT_KEY:
        return None

    try:
        key_str = GOOGLE_SERVICE_ACCOUNT_KEY.strip()
        if key_str.startswith("{"):
            info = json.loads(key_str)
            credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            return build("drive", "v3", credentials=credentials)
        elif os.path.exists(GOOGLE_SERVICE_ACCOUNT_KEY):
            credentials = service_account.Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_KEY, scopes=SCOPES)
            return build("drive", "v3", credentials=credentials)
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            sa_path = os.path.join(script_dir, GOOGLE_SERVICE_ACCOUNT_KEY)
            if os.path.exists(sa_path):
                credentials = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
                return build("drive", "v3", credentials=credentials)
            return None
    except Exception as e:
        print(f"[DRIVE ERROR] Failed to initialize Google Drive: {e}")
        return None


def list_files_in_folder(folder_id, extensions=None):
    """List non-trashed files inside a Google Drive folder."""
    if not folder_id or folder_id.startswith("your_"):
        return []
    service = get_drive_service()
    if not service:
        return []
    try:
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, size)",
            pageSize=100
        ).execute()
        files = results.get("files", [])
        if extensions:
            filtered = []
            for f in files:
                name = f.get("name", "").lower()
                if any(name.endswith(ext) for ext in extensions):
                    filtered.append(f)
            return filtered
        return files
    except Exception as e:
        print(f"[DRIVE ERROR] Error listing files in folder {folder_id}: {e}")
        return []


def download_file(file_id, dest_path):
    """Downloads a single file from Google Drive."""
    try:
        from googleapiclient.http import MediaIoBaseDownload
    except ImportError:
        return False
    service = get_drive_service()
    if not service:
        return False
    try:
        request = service.files().get_media(fileId=file_id)
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        with io.FileIO(dest_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request, chunksize=10 * 1024 * 1024)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        return True
    except Exception as e:
        print(f"[DRIVE ERROR] Error downloading {file_id}: {e}")
        return False


def get_repost_counts():
    """Counts how many times each audio track has been published."""
    if os.path.exists(PUBLISHED_LOG):
        try:
            with open(PUBLISHED_LOG, "r", encoding="utf-8") as f:
                data = json.load(f)
                counts = {}
                for item in data:
                    sname = (item.get("audio_file") or item.get("audio_name") or item.get("music_name") or "").strip().lower()
                    if sname:
                        counts[sname] = counts.get(sname, 0) + 1
                return counts
        except Exception:
            return {}
    return {}


def fetch_assets_triplet(allow_repost=True):
    """
    Fetches ONE video, ONE audio track, and ONE thumbnail image.
    Supports Infinite Circulation Mode with Weighted Least-Recently-Used selection.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    vid_dir = os.path.join(script_dir, LOCAL_VIDEO_DIR)
    aud_dir = os.path.join(script_dir, LOCAL_AUDIO_DIR)
    img_dir = os.path.join(script_dir, LOCAL_IMAGE_DIR)

    os.makedirs(vid_dir, exist_ok=True)
    os.makedirs(aud_dir, exist_ok=True)
    os.makedirs(img_dir, exist_ok=True)

    drive_service = get_drive_service()
    drive_ready = (drive_service is not None) and bool(GOOGLE_DRIVE_AUDIO_FOLDER_ID) and not GOOGLE_DRIVE_AUDIO_FOLDER_ID.startswith("your_")

    if drive_ready:
        print("[DRIVE] Querying Google Drive folders for Tropicozy assets...")
        v_drive = list_files_in_folder(GOOGLE_DRIVE_VIDEO_FOLDER_ID, extensions=[".mp4", ".mov", ".mkv"])
        a_drive = list_files_in_folder(GOOGLE_DRIVE_AUDIO_FOLDER_ID, extensions=[".mp3", ".wav", ".flac"])
        i_drive = list_files_in_folder(GOOGLE_DRIVE_IMAGE_FOLDER_ID, extensions=[".jpg", ".jpeg", ".png", ".webp"])
    else:
        v_drive, a_drive, i_drive = [], [], []

    local_vids = sorted(glob.glob(os.path.join(vid_dir, "*.mp4")) + glob.glob(os.path.join(vid_dir, "*.mov")))
    local_auds = sorted(glob.glob(os.path.join(aud_dir, "*.mp3")) + glob.glob(os.path.join(aud_dir, "*.wav")))
    local_imgs = sorted(glob.glob(os.path.join(img_dir, "*.jpg")) + glob.glob(os.path.join(img_dir, "*.png")) + glob.glob(os.path.join(img_dir, "*.jpeg")))

    # Resolve Audio
    repost_counts = get_repost_counts()
    sel_audio_path = None
    is_repost = False

    if a_drive:
        unpublished = [f for f in a_drive if f["name"].strip().lower() not in repost_counts]
        if unpublished:
            chosen = unpublished[0]
            is_repost = False
        elif allow_repost:
            weights = [max(1, 1000 // (3 ** min(repost_counts.get(f["name"].strip().lower(), 0), 6))) for f in a_drive]
            chosen = random.choices(a_drive, weights=weights, k=1)[0]
            is_repost = True
        else:
            chosen = None

        if chosen:
            dest = os.path.join(aud_dir, chosen["name"])
            if not os.path.exists(dest):
                download_file(chosen["id"], dest)
            sel_audio_path = dest

    if not sel_audio_path and local_auds:
        unpublished = [f for f in local_auds if os.path.basename(f).strip().lower() not in repost_counts]
        if unpublished:
            sel_audio_path = unpublished[0]
            is_repost = False
        elif allow_repost:
            weights = [max(1, 1000 // (3 ** min(repost_counts.get(os.path.basename(f).strip().lower(), 0), 6))) for f in local_auds]
            sel_audio_path = random.choices(local_auds, weights=weights, k=1)[0]
            is_repost = True

    if not sel_audio_path:
        print("[ERROR] No audio tracks found in Drive or local input_audio folder.")
        return None, None, None, False

    # Resolve Video
    sel_video_path = None
    if v_drive:
        chosen_v = v_drive[len(repost_counts) % len(v_drive)] if not is_repost else random.choice(v_drive)
        dest_v = os.path.join(vid_dir, chosen_v["name"])
        if not os.path.exists(dest_v):
            download_file(chosen_v["id"], dest_v)
        sel_video_path = dest_v
    elif local_vids:
        sel_video_path = local_vids[len(repost_counts) % len(local_vids)] if not is_repost else random.choice(local_vids)

    if not sel_video_path:
        print("[ERROR] No videos found in Drive or local input_videos folder.")
        return None, None, None, False

    # Resolve Image (for thumbnail)
    sel_image_path = None
    if i_drive:
        chosen_i = i_drive[len(repost_counts) % len(i_drive)] if not is_repost else random.choice(i_drive)
        dest_i = os.path.join(img_dir, chosen_i["name"])
        if not os.path.exists(dest_i):
            download_file(chosen_i["id"], dest_i)
        sel_image_path = dest_i
    elif local_imgs:
        sel_image_path = local_imgs[len(repost_counts) % len(local_imgs)] if not is_repost else random.choice(local_imgs)

    return sel_video_path, sel_audio_path, sel_image_path, is_repost
