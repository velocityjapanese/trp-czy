"""
YouTube Upload Module for Tropicozy
Uploads processed videos to YouTube using OAuth refresh token.
Category: Music (10)
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load environment variables
load_dotenv()


def get_authenticated_service():
    """Authenticate with YouTube Data API v3 using OAuth refresh token."""
    client_id = (os.getenv("YOUTUBE_CLIENT_ID") or os.getenv("YT_CLIENT_ID", "")).strip()
    client_secret = (os.getenv("YOUTUBE_CLIENT_SECRET") or os.getenv("YT_CLIENT_SECRET", "")).strip()
    refresh_token = (os.getenv("YOUTUBE_REFRESH_TOKEN") or os.getenv("YT_REFRESH_TOKEN", "")).strip()
    token_uri = os.getenv("YOUTUBE_TOKEN_URI", "https://oauth2.googleapis.com/token").strip()

    # Fallback to local token_Tropicozy.json if running locally and env vars aren't set
    if not all([client_id, client_secret, refresh_token]):
        possible_token_paths = [
            Path(__file__).parent.parent / "token_Tropicozy.json",
            Path(r"C:\Users\kreg9\Downloads\kreggscode\open code\bots\youtube refresh tokens bot\token_Tropicozy.json"),
        ]
        for p in possible_token_paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        client_id = data.get("client_id", "")
                        client_secret = data.get("client_secret", "")
                        refresh_token = data.get("refresh_token", "")
                        token_uri = data.get("token_uri", token_uri)
                        print(f"[youtube] Loaded credentials from local file: {p.name}")
                        break
                except Exception as e:
                    print(f"[youtube] Error reading {p}: {e}")

    def mask(s):
        return f"{s[:4]}...{s[-4:]}" if s and len(s) > 8 else "MISSING"

    print(f"[youtube] Client ID: {mask(client_id)}")
    print(f"[youtube] Client Secret: {mask(client_secret)}")
    print(f"[youtube] Refresh Token: {mask(refresh_token)}")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError(
            "Missing YouTube credentials! Ensure YOUTUBE_CLIENT_ID, "
            "YOUTUBE_CLIENT_SECRET, and YOUTUBE_REFRESH_TOKEN are provided."
        )

    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube"]
    )

    try:
        creds.refresh(Request())
    except Exception as e:
        if "invalid_grant" in str(e).lower():
            print("\n❌ [youtube] AUTH ERROR: Refresh token has EXPIRED or been REVOKED.")
        raise

    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(video_path, title, description, tags=None, category_id="10"):
    """
    Upload a video to YouTube.
    
    Args:
        video_path: Path to the MP4 file
        title: Video title (max 100 chars)
        description: Video description (max 5000 chars)
        tags: List of tags
        category_id: YouTube category (10 = Music)
    """
    if tags is None:
        tags = [
            "tropicozy", "tropical music", "tropical vibes", "chill music",
            "island vibes", "caribbean vibes", "rainforest sounds", "relaxing music",
            "summer vibes", "ambient music", "nature sounds"
        ]

    # Ensure title is within 100 characters
    if len(title) > 100:
        title = title[:97] + "..."

    youtube = get_authenticated_service()

    if "#Shorts" not in description:
        description += "\n\n#Shorts"

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        str(video_path),
        chunksize=-1,
        resumable=True,
        mimetype="video/mp4"
    )

    print(f"[youtube] Uploading: {title}")
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"[youtube] Upload progress: {int(status.progress() * 100)}%")

    print(f"✅ [youtube] Upload Successful! Video ID: {response.get('id')}")
    print(f"   URL: https://youtu.be/{response.get('id')}")
    return response
