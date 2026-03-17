---
name: ugc-video-merger
description: Use when the user wants to "merge a product image and voiceover video", "combine image and video into portrait", "stack product image on top of my recording", "merge my UGC video with a product screenshot", "merge my UGC video with a product demo video", or provides a voiceover video and a product image or demo video and wants a single portrait output video.
version: 2.0.0
---

# UGC Video Merger Skill

Combine a **product image or demo video** (top, muted) and a **voiceover video** (bottom) into one portrait 9:16 video — ready to post as a Reel, TikTok, or YouTube Short.

```
┌─────────────────────┐
│                     │
│   Product Image     │  ← top half
│   OR Demo Video     │    (muted, loops/trims to match voiceover)
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
     Duration = voiceover length
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

Provide a voiceover video and either a product image or a product demo video:

```bash
# With a product image
python3 ~/.claude/skills/ugc-video-merger/scripts/merge.py /path/to/voiceover.mp4 /path/to/product.png

# With a product demo video
python3 ~/.claude/skills/ugc-video-merger/scripts/merge.py /path/to/voiceover.mp4 /path/to/demo.mp4
```

Output is saved as `voiceover_merged.mp4` in the same folder as the voiceover.

## What It Does

### Product Image (top panel)
- Scales image to fit the top half (1080×960), preserving aspect ratio
- Pads with a configurable background colour (default: white)
- Holds the image for the full voiceover duration

### Product Demo Video (top panel)
- Scales video to fill the top half (1080×960), cropping edges if needed
- **Muted** — no audio from the demo video
- **Auto-loops** if the demo video is shorter than the voiceover
- **Auto-trims** if the demo video is longer than the voiceover
- Always exactly matches the voiceover length

### Both modes
- Bottom panel: voiceover video scaled to fill its half
- Stack & encode: 1080×1920 portrait, H.264 + AAC
- Audio: voiceover audio only, carried through untouched
- Final duration: always equals the voiceover video length

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `voiceover` | required | Path to the voiceover/face-cam video (sets final length) |
| `product` | required | Path to product image (PNG/JPG/WebP) OR demo video (MP4/MOV/etc.) |
| `-o / --output` | auto | Output path (default: `<voiceover>_merged.mp4`) |
| `--width` | `1080` | Canvas width in px |
| `--height` | `1920` | Canvas height in px |
| `--bg-color` | `white` | Background fill for image panel only (ignored for video) |

## Common Customisations

```bash
# Dark background behind the product image
python3 merge.py voiceover.mp4 product.png --bg-color black

# Product demo video (auto-loops/trims, muted)
python3 merge.py voiceover.mp4 demo_clip.mp4

# Custom output path
python3 merge.py voiceover.mp4 product.png -o ~/Desktop/final.mp4

# Different canvas size (e.g. square)
python3 merge.py voiceover.mp4 product.png --width 1080 --height 1080
```

## How to Handle User Requests

When the user provides a voiceover video and a product image or demo video:

1. Confirm both file paths (ask if not provided)
2. Auto-detect whether the product input is an image or video (by file extension)
3. Run the script with defaults
4. Report the output path when done

If the user mentions a background colour (images only) or custom output path, add the appropriate flags.

## Troubleshooting

**`ffmpeg: command not found`**
Install FFmpeg: `brew install ffmpeg`

**Image looks stretched**
The script preserves aspect ratio by default. If it still looks off, check the image file is not corrupted.

**Demo video has audio in the output**
The script maps audio from the voiceover only (`-map 0:a?`). Audio from the product demo video is never included.

**Demo video doesn't loop**
Ensure FFmpeg version is 4.0+. The `-stream_loop -1` flag requires a modern FFmpeg build.

**No audio in output**
The voiceover video may not have an audio track. The `-map 0:a?` flag makes audio optional — the video still renders correctly.

**Output is landscape, not portrait**
Ensure `--width` < `--height` (default 1080×1920 is correct).
