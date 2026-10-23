"""Bakes the Players page's look into the lineup animation, so browsers don't recolour it on every frame.

Run from the repo root:  python tools/tint_lineup.py
Needs ffmpeg on PATH and numpy. Writes optimized/girloffs3/video/lineup-tinted-1080.av1.mp4 and -720.h264.mp4
(same encoder settings as tools/optimize_assets.py).

The look: greyscale, contrast 0.9, brightness 0.88, then the brand gradient (orange top-left -> pink bottom-right) on top with the
CSS `mix-blend-mode: color` formula at 85% opacity: every pixel keeps its brightness and takes the gradient's colour.
"""

import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "girloffs3branding" / "GIRLOFFS 3 LINEUP ANIMATION desktop aspect all players.mp4"
OUT = ROOT / "optimized" / "girloffs3" / "video"
# brand gradient stops; drawn at 135deg so it runs from orange (top left) to light pink (bottom right)
STOPS = [(0, "#faa916"), (0.55, "#f26a8d"), (1, "#f49cbb")]
ANGLE = 135
OPACITY = 0.85
CONTRAST = 0.9
BRIGHTNESS = 0.88
BT709 = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


def css_gradient(w, h):
    """Same geometry as CSS linear-gradient(<angle>, ...): the 0% and 100% lines pass through opposite corners."""
    a = np.radians(ANGLE)
    ys, xs = np.mgrid[0:h, 0:w] + 0.5
    t = ((xs - w / 2) * np.sin(a) - (ys - h / 2) * np.cos(a)) / (abs(w * np.sin(a)) + abs(h * np.cos(a))) + 0.5
    colours = [[int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)] for _, c in STOPS]
    pos = [p for p, _ in STOPS]
    return np.stack([np.interp(t, pos, [c[i] for c in colours]) for i in range(3)], -1).astype(np.float32)


def tint(frame, grad, grad_lum):
    rgb = frame.astype(np.float32) / 255
    grey = ((rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32) - 0.5) * CONTRAST + 0.5) * BRIGHTNESS
    l = grey[..., None]
    # W3C compositing spec: Color(Cb, Cs) = SetLum(Cs, Lum(Cb)), then ClipColor keeps it inside 0..1
    c = grad + l - grad_lum
    n = c.min(-1, keepdims=True)
    c = np.where(n < 0, l + (c - l) * l / np.maximum(l - n, 1e-6), c)
    x = c.max(-1, keepdims=True)
    c = np.where(x > 1, l + (c - l) * (1 - l) / np.maximum(x - l, 1e-6), c)
    out = (1 - OPACITY) * l + OPACITY * c
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes()


def main():
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height,r_frame_rate", "-of", "csv=p=0", str(SRC)],
                           capture_output=True, text=True, check=True).stdout.strip()
    w, h, rate = probe.split(",")
    w, h = int(w), int(h)
    grad = css_gradient(w, h)
    grad_lum = (grad @ np.array([0.3, 0.59, 0.11], np.float32))[..., None]

    av1 = OUT / "lineup-tinted-1080.av1.mp4"
    h264 = OUT / "lineup-tinted-720.h264.mp4"
    OUT.mkdir(parents=True, exist_ok=True)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(SRC), "-vf", "scale=in_color_matrix=bt709",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                            "-r", rate, "-i", "-",
                            "-vf", "scale=out_color_matrix=bt709:out_range=tv", *BT709,
                            "-c:v", "libsvtav1", "-preset", "4", "-crf", "30", "-pix_fmt", "yuv420p10le",
                            "-g", "300", "-movflags", "+faststart", str(av1),
                            "-vf", "scale=-2:720:flags=lanczos:out_color_matrix=bt709:out_range=tv", *BT709,
                            "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-profile:v", "high",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(h264)], stdin=subprocess.PIPE)
    frames = 0
    while frame := dec.stdout.read(w * h * 3):
        enc.stdin.write(tint(np.frombuffer(frame, np.uint8).reshape(h, w, 3), grad, grad_lum))
        frames += 1
    enc.stdin.close()
    if dec.wait() or enc.wait():
        raise RuntimeError("ffmpeg failed")
    for path in (av1, h264):
        print(f"{path.relative_to(ROOT)}: {path.stat().st_size / 1024:.0f} KB ({frames} frames)")


if __name__ == "__main__":
    main()
