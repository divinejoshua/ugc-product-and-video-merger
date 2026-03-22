#!/usr/bin/env python3
"""
ugc-video-merger: Stacks a product image OR demo video (top, muted) and a voiceover video
(bottom) into a single portrait video. Output length always matches the voiceover exactly.

- Product image  : padded with bg colour, static for full duration.
- Product video  : muted, looped if shorter than voiceover, trimmed if longer.
  - Default (fill): scales to fill the top panel, cropping edges if needed.
  - Fit mode (--demo-fit): scales to show the full video with padding around it.
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
    demo_fit: bool = False,
    demo_padding: int = 20,
    demo_bg_color: str = "black",
):
    """
    Layout (portrait canvas):
      - Top half    (canvas_h // 2) : product image or demo video (muted, looped/trimmed)
      - Bottom half (canvas_h // 2) : voiceover video
    Final duration = voiceover duration.

    demo_fit=True  → show full demo video, no cropping, with padding around it
    demo_fit=False → fill top panel, cropping edges if needed (default)
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

    elif demo_fit:
        # Fit mode: show full demo video, no cropping, with padding around it
        # Inner area = panel minus padding on all sides
        inner_w = canvas_w - 2 * demo_padding
        inner_h = half_h - 2 * demo_padding
        top_filter = (
            f"[1:v]scale={inner_w}:{inner_h}:force_original_aspect_ratio=decrease,"
            f"pad={canvas_w}:{half_h}:(ow-iw)/2:(oh-ih)/2:color={demo_bg_color},"
            f"fps=fps=25[top]"
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

    else:
        # Fill mode (default): scale to fill top panel, cropping edges if needed, always muted
        # fps filter normalises frame rate to match voiceover and prevents glitches at loop points
        top_filter = (
            f"[1:v]scale={canvas_w}:{half_h}:force_original_aspect_ratio=increase,"
            f"crop={canvas_w}:{half_h},"
            f"fps=fps=25[top]"
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
    demo_mode = "" if product_is_image else f" [{'fit+pad' if demo_fit else 'fill+crop'}]"
    print(f"[ugc-video-merger] Merging...")
    print(f"  Voiceover      : {voiceover}")
    print(f"  Product ({product_type}){demo_mode}: {product}")
    if demo_fit and not product_is_image:
        print(f"  Demo mode      : fit — full video visible, {demo_padding}px padding, bg={demo_bg_color}")
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
    parser.add_argument(
        "--demo-fit",
        action="store_true",
        help=(
            "Show the full demo video without cropping. "
            "Adds padding around it instead of filling the panel edge-to-edge. "
            "Use --demo-padding and --demo-bg-color to control the padding."
        ),
    )
    parser.add_argument(
        "--demo-padding",
        type=int,
        default=20,
        help="Padding in px between the demo video and the panel edges (default: 20). Only used with --demo-fit.",
    )
    parser.add_argument(
        "--demo-bg-color",
        default="black",
        help="Background colour behind the demo video in fit mode (default: black). Only used with --demo-fit.",
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
        demo_fit=args.demo_fit,
        demo_padding=args.demo_padding,
        demo_bg_color=args.demo_bg_color,
    )


if __name__ == "__main__":
    main()
