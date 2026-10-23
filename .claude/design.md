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
  - Video: `<video autoplay muted loop playsinline>` with the AV1 source first,
    `type='video/mp4; codecs="av01.0.08M.10"'` (exact string per file in preview.html), then H.264.
    The page background video uses its poster as the `html` background instead of a `poster=` attribute (it's
    already loaded by the loading screen, covers the gap until the video plays, and is all that shows under
    `prefers-reduced-motion`, where the video is hidden).
  - Fonts: WOFF2 with `font-display: swap`.

## Pages
- Existing: bracket, schedule, players (tabs in `index.html`), credits (`#credits` tab, linked from the footer).
- Planned: a page per player, results.

## Known gaps in the Girloffs 2 frontend (fix while redesigning)
- "Live" is decided by the browser clock only (`updateBracketStatuses`), so a match that starts early shows as
  upcoming with a score. Use the API's `match.status` (`live` = games in progress) and the clock only as a fallback.
  With `demo-design`, matches 12 (1-0) and 13 (1-1) are live but render as upcoming because of this.
- A forfeit win shows 0-0 with the winner highlighted and no marker. `match.forfeit` is in the API.

## Decisions
- Credits page: keep it simple and looking like the rest of the site. Left-aligned file tree, no colons:
  `credits/` → roles with a trailing `/` (bold) → names (regular, linked to their profile) with a dim `(site)`;
  tree lines dim. A small gap between role sections so they read as separate lists. `credits/` sits centered
  under the header logo at every width. The Minecraft font has no box-drawing characters or backtick, so tree
  lines are drawn in CSS, not typed.
- Credits art: the owner's braille art (heart/swirl vine, bottom of `notes.md`) fills the empty space right of the
  tree. It stays real, selectable braille text with visible individual dots (the owner wants that texture, not
  solid pixel art) and is soft, 50% white, much quieter than the tree text. 80% of the list's height, centered
  between the tree and the right screen edge. Phones (≤700px): it creeps in from beyond the right edge instead.
  Font: a braille-only subset of Noto Sans Symbols 2 (`assets/fonts/braille.woff2`, `font-display: block`):
  Windows' own braille font has a narrower blank character, which skews the art.
- Backgrounds cover the whole page, header and footer included. Bracket, Schedule and every other tab: the plain
  gradient loop video. Players: the lineup animation behind the whole page. `main` keeps the Girloffs 2 look on top
  (dark tint + inset shadow, same strength on every tab).
- Players header/footer: the lineup behind them is blurred as a gradient, strongest at the page edge (full blur
  for the outer quarter) and fading to sharp towards the content. The blur also nudges hue/saturation/brightness
  so the top-left reads as a pretty orange, not mustard yellow. Tried and dropped: a uniform frosted blur over
  the whole header/footer; the lineup only in the content area (with or without a slow pan).
- Transitions: short and only where they hide loading. Tab switches fade the content in quickly and crossfade the
  background (so the Players lineup arriving late doesn't pop); 0.8s was far too long, none at all felt abrupt.
  Player swaps stay instant. Card hovers fade their background like Schedule rows do.
- One hover colour for text links site-wide (nav, Twitch, footer, credits): deep berry, the same colour as the boxes.
  Pale pink hovers were unreadable on the pink gradient; berry reads on both the orange and the pink.
- Header: the left side (logo + nav) is perfect on desktop, don't change it. The countdown keeps Escargoth but
  lost the Girloffs 2 white pixel box and its double pink shadow ("2 visible layers of text", ugly). The right side
  is two matching label-over-value blocks (Next Match / On Twitch) on the nav's line. Tablet/phone: logo left with
  the two blocks stacked right of it, nav below; the old separate countdown row left dead space in the middle.
- Player heads: the owner's head renders (`girloffs3branding/PLAYER HEADS/<IGN>.png`), not mc-heads.net. The face
  fills the card's head slot and the outer hat layer pokes slightly out of the card (wanted), so cards get a
  little more gap. Heads live in `assets/heads/<seed>`.
- Players background must stay calm (the raw lineup looked "messy, jumbled, illegible"): the lineup is greyscaled
  and recoloured with the brand gradient, orange top-left to pink bottom-right (pink top-left was tried; the
  owner preferred orange), and baked slightly darker (brightness 0.88). Heavier darkening (brightness 0.8 plus a
  darker middle) was too dark. The recolour is baked into the video file (`tools/tint_lineup.py`), not CSS.
- The timezone picker in the footer is the same size as its "time shown in" label.
- Players layout: one featured player (seed 1 by default) gets the left column: their normal card (outlined) with
  their full-body render below it. The other 21 fill 3 columns x 7 rows in seed order. Clicking any card (or a
  player in the bracket/schedule) features them; the previous one drops back to their seed spot. Tablet: same idea
  in 2 columns (render spans 5 rows under the card). Phone: card, then render, then the list. On desktop the Twitch
  and Ranked icons stack vertically so names fit in the narrower cards. Renders live in `assets/players/<seed>`.
- Header and footer text: Escargoth (all caps, slight letter-spacing, hard dark-pink drop shadow). The rest of the
  site stays in the Minecraft font for now. The countdown uses fixed-width digit slots (Escargoth's digits differ
  in width and would wobble every second).
- Header logo and loading-screen logo: the Girloffs 3 logo with the cream border. The owner tried the no-border
  version on 2026-10-23 and went back to the bordered one.
- The Girloffs 2 solid grey boxes (`#333`/`#444` name, score, player and schedule-bar backgrounds) don't work with
  the new look anywhere: too solid, "plastered on", cluttered. Replace the grey with something that fits the
  pink/orange video. Bracket: only the grey needs to change, the layout is fine.
  Replacement (theme.css `--box-*`): a deep berry `rgb(70, 18, 48)`, see-through so the video glows through, no
  blur. Normal 55%, denser 72% (score cells), faint 32% (losers, TBD). Winners/live use the Girloffs 3 brand pinks
  `#f26a8d` / `#f49cbb`, not the old hot pink. The owner really likes this colourway on the Bracket: keep it.
  This session (credits) owns Bracket/Schedule/Players styling from 2026-10-23 13:30.
- Live = the API's `match.status === 'live'` (games in progress), with the clock only as a fallback (Bracket and
  Schedule both).
- Schedule states must be readable at a glance, quietest to loudest: played (faded row and time chip, only the
  winner's name stays bright) < upcoming (berry, no "0 - 0" until there are games) < Next (bright brand pink,
  never darker: it must attract attention) < Live (light pink, brightest).
- Players cards: the berry blended into the pink lineup and was illegible; more transparency made it worse (the
  lineup shows through the text). Now Minecraft-tooltip dark `rgba(16, 0, 16, 0.82)`, which separates cleanly from
  the pink background. No borders: not around the card (a pink inner border was tried) and not around the heads
  (a dark frame was tried); the owner prefers none.
- Players cards (owner, 2026-10-23): no structure, uneven; pronouns look slapped in; the spacing between cards is
  awkward. Needs a clear, even internal layout. Now every card: head | bold display name + dim pronouns right
  after it / dim Minecraft name below | Twitch + Ranked icons (same visible size). Display name is the main name
  because Bracket and Schedule show display names. The seed sits on the head like a Minecraft item-stack count
  (white, hard grey shadow, bottom-right) instead of floating in the gap between columns, so all gaps are equal.
  Everything in a card is sized in em from one font size, so it scales together.
- Schedule (owner, 2026-10-23): on two-column desktop the match bars are far too long with nothing in them; colours,
  font and overall look feel out of place with the current styling. Now each row looks like the Bracket: a denser
  berry time cell with white digits (no more white chip with hot-pink text), then a fixtures-table row:
  round (R1/R2/QF/SF/Final/3rd, dim) | player 1 right-aligned | score, or "vs" before any games | player 2 |
  Next!/Live!. Rows max 38em wide, centered in each day column. Time cell per state: Next brand pink, Live light
  pink, played faded. Phones (≤700px): the row flows left to right (no room for the aligned columns). Clicking a
  row outlines it in white, like the featured player card. Everything in a row is sized in em from one font size.
