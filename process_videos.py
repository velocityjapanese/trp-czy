"""
Video Processing Module for Tropicozy
Enhances visual assets, formats into 1080x1920 (9:16 Shorts format),
loops video if needed, and merges with high-fidelity tropical music soundtracks.
"""
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

OUTPUT_DIR = Path("Processed_Videos")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
DEFAULT_DURATION = 30  # Standard Shorts duration (seconds)


def get_duration(media_path):
    """Retrieve duration of video or audio file in seconds via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(media_path)
    ]
    try:
        out = subprocess.check_output(cmd).decode("utf-8").strip()
        return float(out)
    except Exception as e:
        print(f"Warning: Failed to get duration for {media_path}: {e}")
        return None


def has_audio_stream(video_path):
    """Check if video file contains an audio stream."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0",
        str(video_path)
    ]
    try:
        out = subprocess.check_output(cmd).decode("utf-8").strip()
        return bool(out)
    except Exception:
        return False


def process_video_asset(video_path, music_path=None, output_filename=None):
    """
    Format and enhance video:
    - Scales and crops to 1080x1920 (9:16)
    - Loops seamlessly to match audio or target duration (25-35s)
    - Integrates tropical music with optional ambient sound blending
    - Normalizes audio with loudnorm
    """
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"Error: Video not found at {video_path}")
        return None

    if not output_filename:
        output_filename = f"tropicozy_{video_path.stem}.mp4"

    out_path = OUTPUT_DIR / output_filename
    video_dur = get_duration(video_path) or 10.0

    target_dur = DEFAULT_DURATION
    if music_path and Path(music_path).exists():
        music_dur = get_duration(music_path)
        if music_dur:
            # Shorts must be strictly under 60 seconds
            target_dur = min(int(music_dur), 55)
            target_dur = max(target_dur, 20)

    print(f"Processing Video: {video_path.name}")
    print(f"  Source Duration: {video_dur:.1f}s | Target Output Duration: {target_dur}s")
    print(f"  Target Resolution: {TARGET_WIDTH}x{TARGET_HEIGHT} (9:16 Shorts)")

    video_has_audio = has_audio_stream(video_path)

    # Calculate loop count required
    loop_count = max(1, int(target_dur // video_dur) + 1)

    # Video filter: scale to fill 1080x1920 without stretching, center crop, slight sharpen
    vf = (
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={TARGET_WIDTH}:{TARGET_HEIGHT},"
        f"unsharp=5:5:0.8:5:5:0.0"
    )

    # Audio handling
    # If music_path is available, use it as primary soundtrack with audio normalization & fade out
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", str(loop_count),
        "-i", str(video_path)
    ]

    if music_path and Path(music_path).exists():
        cmd.extend(["-i", str(music_path)])

        if video_has_audio:
            # Mix music (85%) with gentle background ambient sound (20%)
            filter_complex = (
                f"[0:v]{vf}[v];"
                f"[0:a]volume=0.20[a_amb];"
                f"[1:a]volume=0.85[a_mus];"
                f"[a_mus][a_amb]amix=inputs=2:duration=first:dropout_transition=2[a_mix];"
                f"[a_mix]loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:ss=0:d=1,afade=t=out:st={target_dur-2}:d=2[a]"
            )
        else:
            # Pure tropical music track
            filter_complex = (
                f"[0:v]{vf}[v];"
                f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:ss=0:d=1,afade=t=out:st={target_dur-2}:d=2[a]"
            )
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "[a]",
            "-t", str(target_dur),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            str(out_path)
        ])
    else:
        # No external music; use video audio or silent loop
        if video_has_audio:
            cmd.extend([
                "-vf", vf,
                "-t", str(target_dur),
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=out:st={target_dur-2}:d=2",
                "-c:a", "aac", "-b:a", "192k",
                str(out_path)
            ])
        else:
            cmd.extend([
                "-vf", vf,
                "-t", str(target_dur),
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-an",
                str(out_path)
            ])

    print("  Running FFmpeg encoding...")
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode == 0 and out_path.exists():
        print(f"✅ Video processing complete: {out_path} ({out_path.stat().st_size} bytes)")
        return str(out_path)
    else:
        print(f"❌ FFmpeg processing failed with exit code {proc.returncode}")
        print("FFmpeg stderr summary:", proc.stderr[-800:] if proc.stderr else "None")
        return None


def process_image_asset(image_path, music_path, output_filename=None):
    """
    Convert image + tropical music track into an animated 1080x1920 video with slow zoom (Ken Burns).
    """
    image_path = Path(image_path)
    if not image_path.exists():
        print(f"Error: Image not found at {image_path}")
        return None

    if not output_filename:
        output_filename = f"tropicozy_{image_path.stem}.mp4"

    out_path = OUTPUT_DIR / output_filename
    target_dur = DEFAULT_DURATION
    if music_path and Path(music_path).exists():
        music_dur = get_duration(music_path)
        if music_dur:
            target_dur = min(int(music_dur), 55)
            target_dur = max(target_dur, 20)

    fps = 30
    total_frames = int(target_dur * fps)

    # Smooth Ken Burns zoompan filter
    vf = (
        f"zoompan=z='min(zoom+0.0005,1.15)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={TARGET_WIDTH}x{TARGET_HEIGHT}:fps={fps},"
        f"unsharp=5:5:0.6:5:5:0.0"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path)
    ]

    if music_path and Path(music_path).exists():
        cmd.extend([
            "-i", str(music_path),
            "-vf", vf,
            "-t", str(target_dur),
            "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:ss=0:d=1,afade=t=out:st={target_dur-2}:d=2",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            str(out_path)
        ])
    else:
        cmd.extend([
            "-vf", vf,
            "-t", str(target_dur),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-an",
            str(out_path)
        ])

    print(f"  Rendering Image Animation to {out_path.name}...")
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode == 0 and out_path.exists():
        print(f"✅ Image video generated: {out_path}")
        return str(out_path)
    else:
        print(f"❌ FFmpeg image processing failed: {proc.stderr[-600:] if proc.stderr else ''}")
        return None


def process_media(asset_info):
    """
    Main entry point for media processing.
    Accepts asset dict from google_drive_fetch.
    """
    visual_path = asset_info.get("visual_path")
    visual_type = asset_info.get("visual_type", "video")
    music_path = asset_info.get("music_path")

    if visual_type == "video":
        return process_video_asset(visual_path, music_path)
    else:
        return process_image_asset(visual_path, music_path)
