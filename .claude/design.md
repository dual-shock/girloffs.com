# Girloffs 3 design

Loaded into every session (imported from CLAUDE.md), so all parallel sessions work from the same decisions.

**Keep this file current, aggressively.** The moment the owner states a design preference or approves/rejects
something ("I like pink borders", "the header is too tall", "never use rounded corners"), add it under
Decisions in one short, concrete line, before continuing the task. Update or delete lines that get overruled.
Only things that matter for the design: no task logs, no code details that the CSS already shows.

## Rules (from the owner, always)
1. **Responsive.** People watch on phones and on desktops of every size, like the Girloffs 2 site. Check every
   change at phone (~375px), tablet (~768px) and wide desktop (~1440px+) widths.
2. **Hand-made, not AI-looking.** It should feel like the old hand-written HTML/CSS, just more polished. No
   generic template look (default system fonts, glassmorphism cards everywhere, stock purple-blue gradients,
   emoji icons, symmetric hero + 3 cards). Build from the Girloffs 3 branding itself.
3. **Vanilla stack.** Plain HTML, CSS and JS modules. No framework, no build step.

## Brand
- **Gradient:** orange `#faa916` 0% → pink `#f26a8d` 55% → light pink `#f49cbb` 100%
  (`girloffs3branding/orange_to_pink_gradient_settings.txt`). The flat `GIRLOFFS_3_GRADIENT.webp` is exactly
  this, so use CSS `linear-gradient` instead of the image.
- **Fonts:** Escargoth (Girloffs 3 display font, bought), Minecraft (Girloffs 2 pixel font, may stay).
- **Assets:** logo (with/without border), left/right stars 1-3 (full-frame 1920x1080 overlays), blue-pink-orange
  grain gradient, gradient loop video (plain / with subtle logo), lineup image + animation, one render per
  player (named by lowercase Minecraft name).
- **Use the optimized copies** in `optimized/` (sizes and quality in `optimized/README.md`, everything visible
  in `optimized/preview.html`). Move only what's used into `frontend/assets/`.
  - Images: `<picture>` with the AVIF source first and WebP as the `<img>` (or `image-set()` in CSS).
  - Video: `<video autoplay muted loop playsinline poster=...>` with the AV1 source first,
    `type='video/mp4; codecs="av01.0.08M.10"'` (exact string per file in preview.html), then H.264.
    Poster only under `prefers-reduced-motion`.
  - Fonts: WOFF2 with `font-display: swap`.

## Pages
- Existing: bracket, schedule, players (tabs in `index.html`).
- Planned: credits, a page per player, results.

## Known gaps in the Girloffs 2 frontend (fix while redesigning)
- "Live" is decided by the browser clock only (`updateBracketStatuses`), so a match that starts early shows as
  upcoming with a score. Use the API's `match.status` (`live` = games in progress) and the clock only as a fallback.
  With `demo-design`, matches 12 (1-0) and 13 (1-1) are live but render as upcoming because of this.
- A forfeit win shows 0-0 with the winner highlighted and no marker. `match.forfeit` is in the API.

## Decisions
(none yet)
