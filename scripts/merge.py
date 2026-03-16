#!/usr/bin/env python3
"""
ugc-video-merger: Stacks a product image (top) and a voiceover video (bottom)
into a single portrait video. Output dimensions default to 1080x1920 (9:16).
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] FFmpeg failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result


def get_video_dimensions(video_path: str) -> tuple[int, int]:
    """Return (width, height) of a video file."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Could not probe video: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    parts = result.stdout.strip().split(",")
    return int(parts[0]), int(parts[1])


def merge(
    voiceover: str,
    product_image: str,
    output: str,
    canvas_w: int = 1080,
    canvas_h: int = 1920,
    image_bg_color: str = "white",
):
    """
    Layout (portrait canvas):
      - Top half  (canvas_h // 2) : product image, scaled to fit, centred on solid bg
      - Bottom half (canvas_h // 2): voiceover video, scaled to fill
    """
    half_h = canvas_h // 2

    # Scale image to fit inside the top panel, preserve aspect ratio, pad with bg colour
    image_filter = (
        f"[1:v]scale={canvas_w}:{half_h}:force_original_aspect_ratio=decrease,"
        f"pad={canvas_w}:{half_h}:(ow-iw)/2:(oh-ih)/2:color={image_bg_color}[img]"
    )

    # Scale video to fill the bottom panel (crop to exact size)
    video_filter = (
        f"[0:v]scale={canvas_w}:{half_h}:force_original_aspect_ratio=increase,"
        f"crop={canvas_w}:{half_h}[vid]"
    )

    # Stack: image on top, video on bottom
    stack_filter = "[img][vid]vstack=inputs=2[out]"

    filter_complex = f"{image_filter};{video_filter};{stack_filter}"

    cmd = [
        "ffmpeg", "-y",
        "-i", voiceover,          # input 0: video
        "-i", product_image,      # input 1: image
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", "0:a?",           # carry audio from voiceover if present
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output,
    ]

    print(f"[ugc-video-merger] Merging...")
    print(f"  Voiceover : {voiceover}")
    print(f"  Image     : {product_image}")
    print(f"  Output    : {output}")
    print(f"  Canvas    : {canvas_w}x{canvas_h} (portrait 9:16)")
    run(cmd)
    print(f"\n[ugc-video-merger] Done! Saved to: {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Merge a product image (top) + voiceover video (bottom) into a portrait UGC video."
    )
    parser.add_argument("voiceover", help="Path to the voiceover/screen-recording video")
    parser.add_argument("image", help="Path to the product image (PNG/JPG/WebP)")
    parser.add_argument(
        "-o", "--output",
        help="Output path (default: <voiceover_name>_merged.mp4)",
        default=None,
    )
    parser.add_argument(
        "--width", type=int, default=1080, help="Canvas width in px (default: 1080)"
    )
    parser.add_argument(
        "--height", type=int, default=1920, help="Canvas height in px (default: 1920)"
    )
    parser.add_argument(
        "--bg-color",
        default="white",
        help="Background fill colour for the image panel (default: white)",
    )

    args = parser.parse_args()

    # Validate inputs
    for path, label in [(args.voiceover, "voiceover"), (args.image, "image")]:
        if not os.path.isfile(path):
            print(f"[ERROR] {label} file not found: {path}", file=sys.stderr)
            sys.exit(1)

    # Default output path
    if args.output is None:
        stem = Path(args.voiceover).stem
        parent = Path(args.voiceover).parent
        args.output = str(parent / f"{stem}_merged.mp4")

    merge(
        voiceover=args.voiceover,
        product_image=args.image,
        output=args.output,
        canvas_w=args.width,
        canvas_h=args.height,
        image_bg_color=args.bg_color,
    )


if __name__ == "__main__":
    main()
