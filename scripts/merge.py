#!/usr/bin/env python3
"""
ugc-video-merger: Stacks a product image OR demo video (top, muted) and a voiceover video
(bottom) into a single portrait video. Output length always matches the voiceover exactly.

- Product image  : padded with bg colour, static for full duration.
- Product video  : muted, looped if shorter than voiceover, trimmed if longer.
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif"}


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] FFmpeg failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result


def get_duration(path: str) -> float:
    """Return duration of a media file in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Could not probe duration: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return float(result.stdout.strip())


def is_image(path: str) -> bool:
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


def merge(
    voiceover: str,
    product: str,
    output: str,
    canvas_w: int = 1080,
    canvas_h: int = 1920,
    bg_color: str = "white",
):
    """
    Layout (portrait canvas):
      - Top half    (canvas_h // 2) : product image or demo video (muted, looped/trimmed)
      - Bottom half (canvas_h // 2) : voiceover video
    Final duration = voiceover duration.
    """
    half_h = canvas_h // 2
    product_is_image = is_image(product)

    # Voiceover duration drives the final length
    vo_duration = get_duration(voiceover)

    # Scale bottom (voiceover) to fill its panel
    bot_filter = (
        f"[0:v]scale={canvas_w}:{half_h}:force_original_aspect_ratio=increase,"
        f"crop={canvas_w}:{half_h}[bot]"
    )

    if product_is_image:
        # Static image: scale to fit, pad with bg colour
        top_filter = (
            f"[1:v]scale={canvas_w}:{half_h}:force_original_aspect_ratio=decrease,"
            f"pad={canvas_w}:{half_h}:(ow-iw)/2:(oh-ih)/2:color={bg_color}[top]"
        )
        filter_complex = f"{top_filter};{bot_filter};[top][bot]vstack=inputs=2[out]"

        cmd = [
            "ffmpeg", "-y",
            "-i", voiceover,          # input 0: voiceover (main)
            "-loop", "1",             # repeat the single image frame
            "-i", product,            # input 1: product image
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "0:a?",           # audio from voiceover only
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(vo_duration),   # exact voiceover length
            output,
        ]

    else:
        # Demo video: scale to fill top panel, loop if short, trim if long, always muted
        top_filter = (
            f"[1:v]scale={canvas_w}:{half_h}:force_original_aspect_ratio=increase,"
            f"crop={canvas_w}:{half_h}[top]"
        )
        filter_complex = f"{top_filter};{bot_filter};[top][bot]vstack=inputs=2[out]"

        cmd = [
            "ffmpeg", "-y",
            "-i", voiceover,          # input 0: voiceover (main)
            "-stream_loop", "-1",     # loop input 1 indefinitely (handles short videos)
            "-i", product,            # input 1: product demo video (looped, muted)
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "0:a?",           # audio from voiceover only — product video is silent
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(vo_duration),   # trim/stop at voiceover length
            output,
        ]

    product_type = "image" if product_is_image else "demo video (muted)"
    print(f"[ugc-video-merger] Merging...")
    print(f"  Voiceover      : {voiceover}")
    print(f"  Product ({product_type}): {product}")
    print(f"  Output         : {output}")
    print(f"  Canvas         : {canvas_w}x{canvas_h} (portrait 9:16)")
    print(f"  Final duration : {vo_duration:.2f}s (matches voiceover)")
    run(cmd)
    print(f"\n[ugc-video-merger] Done! Saved to: {output}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Merge a product image or demo video (top, muted) + voiceover video (bottom) "
            "into a portrait UGC video. Output length = voiceover length."
        )
    )
    parser.add_argument("voiceover", help="Path to the voiceover/face-cam video (sets final length)")
    parser.add_argument(
        "product",
        help="Path to the product image (PNG/JPG/WebP) OR product demo video (MP4/MOV/etc.)",
    )
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
        help="Background fill colour for image panel (default: white). Ignored for video input.",
    )

    args = parser.parse_args()

    for path, label in [(args.voiceover, "voiceover"), (args.product, "product")]:
        if not os.path.isfile(path):
            print(f"[ERROR] {label} file not found: {path}", file=sys.stderr)
            sys.exit(1)

    if args.output is None:
        stem = Path(args.voiceover).stem
        parent = Path(args.voiceover).parent
        args.output = str(parent / f"{stem}_merged.mp4")

    merge(
        voiceover=args.voiceover,
        product=args.product,
        output=args.output,
        canvas_w=args.width,
        canvas_h=args.height,
        bg_color=args.bg_color,
    )


if __name__ == "__main__":
    main()
