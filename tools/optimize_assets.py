"""Converts the source artwork into web-optimised copies in optimized/. Nothing in the site changes.

Run from the repo root:  python tools/optimize_assets.py
Needs ffmpeg on PATH. Fonts also need fontTools + brotli; without them the fonts are skipped with a message.

- Images: AVIF (main, ~5-20x smaller) + WebP (fallback for the few browsers without AVIF).
  Pixel art: lossless WebP only, because lossy formats smear hard pixel edges.
- Videos: AV1 MP4 (main) + H.264 MP4 (fallback), each at 1080p and 720p, plus a poster image.
- Fonts: WOFF2.
Also writes optimized/README.md (sizes + quality scores) and optimized/preview.html (open it to eyeball everything).
"""

import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC3 = ROOT / "girloffs3branding"
SRC2 = ROOT / "frontend" / "assets"
OUT = ROOT / "optimized"

sys.path.insert(0, str(ROOT / "backend"))
from app.event import PLAYERS  # noqa: E402

# Settings picked from a size/SSIM/VMAF sweep (2026-10-23).
#   art:    logos, stars (sharp edges, transparency) -> full colour resolution (4:4:4)
#   photo:  renders, lineup, grainy gradients
#   smooth: clean gradients -> 10-bit, so no colour banding
#   pixel:  pixel-art logos -> lossless WebP
IMAGE_KINDS = {
    "art": {"crf": 18, "pix": "yuv444p", "webp_q": 92},
    "photo": {"crf": 20, "pix": "yuv444p", "webp_q": 90},
    "smooth": {"crf": 18, "pix": "yuv420p10le", "webp_q": 90},
}

results = []  # (group, source, [(output, kb, quality)])
notes = []


def ff(*args, tries=5):
    """Run ffmpeg, retrying failures: libaom in this ffmpeg build randomly fails to start (~1 in 5 runs).
    Retrying is safe because a successful run always produces the same file."""
    for _ in range(tries):
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], capture_output=True, text=True)
        if r.returncode == 0:
            return
    raise RuntimeError(f"ffmpeg failed {tries} times: {r.stderr[-600:]}")


def ff_stderr(*args):
    return subprocess.run(["ffmpeg", "-v", "info", *map(str, args)], capture_output=True, text=True).stderr


def kb(path):
    return path.stat().st_size / 1024


def dims(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout
    w, h = out.strip().split(",")[:2]
    return int(w), int(h)


def alpha_used(src):
    """True if any pixel is not fully opaque (many 'transparent' files are actually opaque)."""
    w, h = dims(src)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-vf", "format=rgba,alphaextract",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return len(raw) >= w * h and min(raw) < 255


def ssim(src, out, has_alpha):
    """SSIM of the output against the source at the output's size (1.0 = identical). Hidden pixels don't count."""
    w, h = dims(out)
    a = f"[0:v]scale={w}:{h}:flags=lanczos,format=rgba,premultiply=inplace=1,format=yuv444p[a]"
    if out.suffix == ".avif" and has_alpha:
        b = "[1:v:0][1:v:1]alphamerge,format=rgba,premultiply=inplace=1,format=yuv444p[b]"
    else:
        b = "[1:v]format=rgba,premultiply=inplace=1,format=yuv444p[b]"
    m = re.search(r"All:([0-9.]+)", ff_stderr("-i", src, "-i", out, "-filter_complex", f"{a};{b};[a][b]ssim",
                                               "-f", "null", "-"))
    return f"SSIM {float(m.group(1)):.4f}" if m else "SSIM ?"


def avif(src, dst, kind, has_alpha, width):
    s = IMAGE_KINDS[kind]
    scale = f"scale={width}:-2:flags=lanczos," if width else ""
    common = ["-c:v", "libaom-av1", "-still-picture", "1", "-crf", s["crf"], "-cpu-used", "3"]
    if has_alpha:
        # AVIF keeps transparency as a second (greyscale) image next to the colour image. Encoded one after the
        # other and then combined, because starting both encoders at once makes libaom fail far more often.
        color, alpha = dst.with_suffix(".color.ivf"), dst.with_suffix(".alpha.ivf")
        ff("-i", src, "-vf", f"{scale}format=yuva444p,format=yuv444p", *common, color)
        ff("-i", src, "-vf", f"{scale}format=yuva444p,alphaextract", *common, alpha)
        ff("-i", color, "-i", alpha, "-map", "0", "-map", "1", "-c", "copy", "-f", "avif", dst)
        color.unlink()
        alpha.unlink()
    else:
        ff("-i", src, "-vf", f"{scale}format={s['pix']}", *common, dst)


def webp(src, dst, quality, has_alpha, width, lossless=False):
    scale = f"scale={width}:-2:flags=lanczos," if width else ""
    if lossless:
        ff("-i", src, "-vf", f"{scale}format=rgba", "-c:v", "libwebp", "-lossless", "1", "-compression_level", "6", dst)
    else:
        fmt = "yuva420p" if has_alpha else "yuv420p"
        ff("-i", src, "-vf", f"{scale}format={fmt}", "-c:v", "libwebp", "-quality", quality,
           "-compression_level", "6", dst)


def image(group, src, name, kind, widths=(None,)):
    has_alpha = alpha_used(src)
    outs = []
    for width in widths:
        base = OUT / group / (f"{name}-{width}" if width else name)
        base.parent.mkdir(parents=True, exist_ok=True)
        if kind == "pixel":
            dst = base.with_suffix(".webp")
            webp(src, dst, None, has_alpha, width, lossless=True)
            outs.append((dst, kb(dst), "lossless"))
            continue
        for dst in (base.with_suffix(".avif"), base.with_suffix(".webp")):
            if dst.suffix == ".avif":
                avif(src, dst, kind, has_alpha, width)
            else:
                webp(src, dst, IMAGE_KINDS[kind]["webp_q"], has_alpha, width)
            outs.append((dst, kb(dst), ssim(src, dst, has_alpha)))
    results.append((group, src, outs))
    print(f"  {src.name}: {kb(src):.0f} KB -> " + ", ".join(f"{o.name} {s:.0f} KB" for o, s, _ in outs), flush=True)


def vmaf(src, out):
    """Perceptual video quality (VMAF, 0-100) against the source; 720p is upscaled to 1080p first, as is standard."""
    log = out.with_suffix(".vmaf.json")
    up = "" if dims(out)[1] == 1080 else "scale=1920:1080:flags=bicubic,"
    fc = (f"[0:v]{up}setpts=PTS-STARTPTS,format=yuv420p[d];[1:v]setpts=PTS-STARTPTS,format=yuv420p[r];"
          f"[d][r]libvmaf=n_threads=6:log_fmt=json:log_path={log.name}")
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(out), "-i", str(src), "-lavfi", fc, "-f", "null", "-"],
                   cwd=log.parent, check=True)
    score = json.loads(log.read_text())["pooled_metrics"]["vmaf"]["mean"]
    log.unlink()
    return score


def av1_codecs(path):
    """The codecs string for <source type=...>, so browsers without AV1 skip straight to the H.264 file."""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=level",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.strip()
    return f"av01.0.{int(out):02d}M.10"


def video(src, name, grain, av1_crf, h264_crf):
    outs = []
    for height in (1080, 720):
        scale = [] if height == 1080 else ["-vf", f"scale=-2:{height}:flags=lanczos"]
        base = ["-i", src, "-map", "0:v:0", "-an", "-map_metadata", "-1", "-map_chapters", "-1", *scale]
        dst = OUT / "girloffs3" / "video" / f"{name}-{height}.av1.mp4"
        dst.parent.mkdir(parents=True, exist_ok=True)
        # 10-bit avoids banding in the gradients; film-grain=8 re-creates the source's grain on playback
        # instead of spending bits on it (VMAF doesn't credit synthesised grain, so those scores read low)
        params = ["-svtav1-params", "film-grain=8"] if grain else []
        ff(*base, "-c:v", "libsvtav1", "-preset", "4", "-crf", av1_crf, *params, "-pix_fmt", "yuv420p10le",
           "-g", "300", "-movflags", "+faststart", dst)
        outs.append((dst, kb(dst), f"VMAF {vmaf(src, dst):.1f}" + (" (grain re-created)" if grain else "")))
        dst = dst.with_name(f"{name}-{height}.h264.mp4")
        ff(*base, "-c:v", "libx264", "-preset", "slow", "-crf", h264_crf, "-profile:v", "high", "-pix_fmt",
           "yuv420p", "-movflags", "+faststart", dst)
        outs.append((dst, kb(dst), f"VMAF {vmaf(src, dst):.1f}"))
    poster = OUT / "girloffs3" / "video" / f"{name}-poster.png"
    ff("-i", src, "-frames:v", "1", poster)
    results.append(("girloffs3/video", src, outs))
    print(f"  {src.name}: {kb(src):.0f} KB -> " + ", ".join(f"{o.name} {s:.0f} KB" for o, s, _ in outs), flush=True)
    image("girloffs3/video", poster, f"{name}-poster", "photo")
    poster.unlink()


def fonts(jobs):
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        notes.append("Fonts were skipped: fontTools + brotli aren't installed in the Python that ran this script.")
        return
    for group, src, name in jobs:
        dst = OUT / group / f"{name}.woff2"
        dst.parent.mkdir(parents=True, exist_ok=True)
        font = TTFont(src)
        glyphs = len(font.getBestCmap())
        font.flavor = "woff2"
        font.save(dst)
        assert len(TTFont(dst).getBestCmap()) == glyphs  # nothing lost on the way
        results.append((group, src, [(dst, kb(dst), f"{glyphs} characters, unchanged")]))
        print(f"  {src.name}: {kb(src):.0f} KB -> {dst.name} {kb(dst):.0f} KB", flush=True)


def find_player(label):
    """The player a render file is about: by Minecraft name, then display name, then the closest spelling."""
    by_name = {p[2].lower(): p for p in PLAYERS}
    by_display = {p[3].lower(): p for p in PLAYERS}
    if label in by_name:
        return by_name[label], False
    if label in by_display:
        return by_display[label], False
    close = difflib.get_close_matches(label, [*by_name, *by_display], n=1, cutoff=0.8)
    return ((by_name | by_display)[close[0]], True) if close else (None, False)


def players(only=None):
    for src in sorted((SRC3 / "PLAYER RENDERS").glob("*.png"), key=lambda p: int(p.stem.split("-")[0])):
        file_seed, label = src.stem.split("-", 1)
        if only and label.lower() != only.lower():
            continue
        player, guessed = find_player(label.lower())
        if player is None:
            notes.append(f"`PLAYER RENDERS/{src.name}`: no player with a matching name, skipped.")
            continue
        seed, match = player[0], player[2].lower()
        if guessed:
            notes.append(f"`PLAYER RENDERS/{src.name}`: name doesn't match any player; used **{player[2]}** "
                         f"(closest spelling). Saved as `{match}`.")
        if int(file_seed) != seed:
            notes.append(f"`PLAYER RENDERS/{src.name}`: file says seed {file_seed}, but {player[2]} is "
                         f"seed {seed}. Outputs are named by IGN, so it doesn't matter for the site.")
        image("girloffs3/players", src, match, "photo")
    if only:
        return
    done = {r[2][0][0].stem for r in results if r[0] == "girloffs3/players"}
    for p in PLAYERS:
        if p[2].lower() not in done:
            notes.append(f"No render found for **{p[2]}** (seed {p[0]}).")


def write_report():
    lines = ["# Optimized assets", "",
             "Generated by `tools/optimize_assets.py` from `girloffs3branding/` and `frontend/assets/`. "
             "Nothing here is used by the site yet.", ""]
    if notes:
        lines += ["## Things to check", ""] + [f"- {n}" for n in notes] + [""]
    summary = ["## Summary", "", "What a modern browser downloads (largest AVIF / AV1 1080p / WOFF2 / lossless WebP) "
               "compared with the source files:", "", "| Group | Sources | Optimized |", "|---|---|---|"]
    tables = []
    for group in dict.fromkeys(r[0] for r in results):
        tables += [f"## {group}", "", "| Source | Size | Output | Size | Quality |", "|---|---|---|---|---|"]
        size_in = size_out = 0
        for g, src, outs in results:
            if g != group:
                continue
            if not src.name.endswith("-poster.png"):
                size_in += kb(src)
            main = [s for o, s, q in outs if o.suffix in (".avif", ".woff2") or ".av1." in o.name and "-1080" in o.name
                    or q == "lossless"]
            size_out += max(main, default=0)
            for i, (out, size, quality) in enumerate(outs):
                first = i == 0
                src_size = f"{kb(src):,.0f} KB" if first and not src.name.endswith("-poster.png") else ""
                tables.append(f"| {src.name if first else ''} | {src_size} | "
                              f"`{out.relative_to(OUT).as_posix()}` | {size:,.1f} KB | {quality} |")
        tables.append("")
        summary.append(f"| {group} | {size_in / 1024:,.2f} MB | {size_out / 1024:,.2f} MB |")
    lines += summary + [""] + tables
    lines += ["SSIM: 1.0 = identical to the source (transparent pixels excluded). "
              "VMAF: 0-100 perceptual video score; this source footage tops out around 96 even for a "
              "near-lossless copy.", ""]
    OUT.joinpath("README.md").write_text("\n".join(lines), encoding="utf-8")


def write_preview():
    blocks = []
    for group, src, outs in results:
        for out, size, quality in outs:
            rel = out.relative_to(OUT).as_posix()
            label = f"{rel} · {size:,.1f} KB · {quality}"
            if out.suffix in (".avif", ".webp"):
                blocks.append(f'<figure><img src="{rel}" loading="lazy"><figcaption>{label}</figcaption></figure>')
            elif out.suffix == ".mp4":
                typ = f'video/mp4; codecs="{av1_codecs(out)}"' if ".av1." in out.name else "video/mp4"
                blocks.append(f'<figure><video src="{rel}" autoplay muted loop playsinline></video>'
                              f'<figcaption>{label}<br><code>type=\'{typ}\'</code></figcaption></figure>')
            elif out.suffix == ".woff2":
                fam = out.stem
                blocks.append(f'<style>@font-face{{font-family:"{fam}";src:url("{rel}") format("woff2")}}</style>'
                              f'<figure><p style="font-family:\'{fam}\';font-size:42px;margin:0">'
                              f'GIRLOFFS 3 · Girloffs 3 · 0123456789</p><figcaption>{label}</figcaption></figure>')
    html = ("<!doctype html><meta charset=utf-8><title>Optimized assets preview</title><style>"
            "body{font:14px system-ui;margin:16px;background:#222;color:#eee}"
            "figure{display:inline-block;vertical-align:top;margin:8px;max-width:480px}"
            "img,video{max-width:480px;max-height:300px;display:block;"
            "background:repeating-conic-gradient(#999 0 25%,#666 0 50%) 0 0/20px 20px}"
            "figcaption{font-size:12px;color:#bbb;word-break:break-all}</style>"
            "<h1>Optimized assets</h1><p>Every output on a checkerboard, so transparency is visible.</p>"
            + "\n".join(blocks))
    OUT.joinpath("preview.html").write_text(html, encoding="utf-8")


def main():
    print("Girloffs 3 images")
    image("girloffs3/logo", SRC3 / "girloffs_logo_revised.webp", "girloffs-logo", "art")
    image("girloffs3/logo", SRC3 / "girloffs_logo_revised_no_border.webp", "girloffs-logo-no-border", "art")
    for side in ("LEFT", "RIGHT"):
        for n in (1, 2, 3):
            image("girloffs3/stars", SRC3 / f"{side} STAR {n}.png", f"{side.lower()}-star-{n}", "art")
    image("girloffs3/gradients", SRC3 / "BLUE PINK ORANGE GRADIENT.webp", "blue-pink-orange", "photo")
    image("girloffs3/gradients", SRC3 / "GIRLOFFS_3_GRADIENT.webp", "girloffs3-gradient", "smooth")
    image("girloffs3/lineup", SRC3 / "GIRLOFFS 3 LINEUP desktop aspect all players.jpg", "lineup", "photo",
          (3840, 1920, 1280))
    print("Girloffs 3 player renders")
    players()
    print("Girloffs 2 images")
    image("girloffs2/logos", SRC2 / "branding/GirloffsLogo.png", "girloffs-logo-pixel", "pixel")
    image("girloffs2/logos", SRC2 / "branding/Girloffs2Logo.png", "girloffs2-logo-pixel", "pixel")
    for n in (1, 2, 3, 4):
        # the old -720p/-340p files were smaller copies of these; regenerated from the full-size originals
        image("girloffs2/gradients", SRC2 / f"branding/gradient{n}.png", f"gradient{n}", "smooth", (1920, 1280, 640))
    print("Fonts")
    fonts([("girloffs3/fonts", SRC3 / "Escargoth.otf", "escargoth"),
           ("girloffs2/fonts", SRC2 / "fonts/regular.otf", "minecraft-regular"),
           ("girloffs2/fonts", SRC2 / "fonts/bold.otf", "minecraft-bold")])
    print("Girloffs 3 videos (slow: AV1)")
    video(SRC3 / "GIRLOFFS MOVING GRADIENT LOOP.mp4", "gradient-loop", True, 30, 23)
    video(SRC3 / "GIRLOFFS MOVING GRADIENT LOOP WITH SUBTLE TRANSPARENT LOGO.mp4", "gradient-loop-logo", True, 30, 23)
    video(SRC3 / "GIRLOFFS 3 LINEUP ANIMATION desktop aspect all players.mp4", "lineup-animation", False, 30, 21)
    write_report()
    write_preview()
    print(f"Done: {OUT / 'README.md'} and {OUT / 'preview.html'}")


if __name__ == "__main__":
    main()
