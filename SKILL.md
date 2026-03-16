---
name: ugc-video-merger
description: Use when the user wants to "merge a product image and voiceover video", "combine image and video into portrait", "stack product image on top of my recording", "merge my UGC video with a product screenshot", or provides a voiceover video and a product image and wants a single portrait output video.
version: 1.0.0
---

# UGC Video Merger Skill

Combine a **product image** (top) and a **voiceover video** (bottom) into one portrait 9:16 video — ready to post as a Reel, TikTok, or YouTube Short.

```
┌─────────────────────┐
│                     │
│   Product Image     │  ← top half
│   (app / software)  │
│                     │
├─────────────────────┤
│                     │
│   Voiceover Video   │  ← bottom half
│   (face cam / screen│
│    recording)       │
│                     │
└─────────────────────┘
     1080 × 1920 px
```

## Prerequisites

FFmpeg only — install once:

```bash
brew install ffmpeg          # macOS
# sudo apt install ffmpeg   # Ubuntu/Debian
```

Verify:
```bash
ffmpeg -version
```

## Quick Start

When the user provides a voiceover video and a product image, run:

```bash
python3 ~/.claude/skills/ugc-video-merger/scripts/merge.py /path/to/voiceover.mp4 /path/to/product.png
```

Output is saved as `voiceover_merged.mp4` in the same folder as the voiceover. That's it.

## What It Does

1. **Top panel** — Scales the product image to fit the top half (1080×960), preserving aspect ratio and padding with a white background so no stretching occurs.
2. **Bottom panel** — Scales the voiceover video to fill the bottom half (1080×960), cropping edges if needed to cover the area cleanly.
3. **Stack & encode** — Stacks both panels into a single 1080×1920 portrait video and re-encodes with H.264 + AAC. Audio from the voiceover is carried through untouched.

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `voiceover` | required | Path to the voiceover/face-cam video |
| `image` | required | Path to the product image (PNG/JPG/WebP) |
| `-o / --output` | auto | Output path (default: `<voiceover>_merged.mp4`) |
| `--width` | `1080` | Canvas width in px |
| `--height` | `1920` | Canvas height in px |
| `--bg-color` | `white` | Background fill for image panel (white/black/gray/any hex) |

## Common Customisations

```bash
# Dark background behind the product image (good for dark UI screenshots)
python3 merge.py voiceover.mp4 product.png --bg-color black

# Custom output path
python3 merge.py voiceover.mp4 product.png -o ~/Desktop/final.mp4

# Different canvas size (e.g. square)
python3 merge.py voiceover.mp4 product.png --width 1080 --height 1080
```

## How to Handle User Requests

When the user says something like "merge my voiceover with this product image":

1. Confirm both file paths (ask if not provided)
2. Run the script with defaults
3. Report the output path when done

If the user mentions a background colour preference or custom output location, add the appropriate flags.

## Troubleshooting

**`ffmpeg: command not found`**
Install FFmpeg: `brew install ffmpeg`

**Image looks stretched**
The script preserves aspect ratio by default. If it still looks off, check that the image file is not corrupted.

**No audio in output**
The voiceover video may not have an audio track. The `-map 0:a?` flag makes audio optional — the video will still render correctly.

**Output is landscape, not portrait**
Ensure `--width` < `--height` (default is 1080×1920 which is correct).
