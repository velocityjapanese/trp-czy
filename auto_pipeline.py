"""
Tropicozy - Master Video Automation Pipeline
1. Fetch visual (video/image) and tropical music soundtrack from Google Drive
2. Process & enhance (upscale to 1080x1920 9:16, loop, mix audio, normalize)
3. Generate AI tropical music metadata and upload to YouTube (Tropicozy)
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

from google_drive_fetch import fetch_media_assets
from process_videos import process_media
from daily_publisher import publish_video


def run_pipeline():
    print("\n" + "=" * 60)
    print("🌴 STARTING TROPICOZY AUTOMATION PIPELINE 🦜")
    print("=" * 60 + "\n")

    # Step 1: Fetch media from Google Drive
    print("📥 STEP 1: Fetching tropical media from Google Drive...")
    asset_info = fetch_media_assets(allow_repost=True)

    if not asset_info or not asset_info.get("visual_path"):
        print("❌ No media available to process. Pipeline stopped.")
        sys.exit(0)

    print(f"✅ Step 1 complete:")
    print(f"   Visual: {asset_info['visual_name']} ({asset_info['visual_type']})")
    print(f"   Music:  {asset_info.get('music_name') or 'Original video audio'}\n")

    # Step 2: Process media
    print("🎬 STEP 2: Processing and enhancing video into 1080x1920...")
    processed_video = process_media(asset_info)

    if not processed_video or not os.path.exists(processed_video):
        print("❌ Video processing failed!")
        sys.exit(1)

    print(f"✅ Step 2 complete: Video rendered at {processed_video}\n")

    # Step 3: Publish to YouTube
    print("📤 STEP 3: Generating tropical music metadata & uploading to YouTube...")
    success = publish_video(processed_video, asset_info)

    if not success:
        print("❌ Video upload failed!")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🎉 TROPICOZY AUTOMATION PIPELINE COMPLETED SUCCESSFULLY! 🌴")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_pipeline()
