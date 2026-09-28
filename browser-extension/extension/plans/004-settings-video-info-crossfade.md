# 004 — Crossfade the settings panel / video info swap instead of an instant cut

- **Status**: DONE (amended — see "Correction after feel-check" below; the
  originally-planned CSS-only simultaneous crossfade did not work as
  intended and was replaced by a small JS timing sequence)
- **Commit**: caf781bee
- **Severity**: Missed opportunity (treat as MEDIUM impact when scheduling)
- **Category**: Missed opportunities / Physicality
- **Estimated scope**: 2 files (`popup.css`, `popup.js`)

## Correction after feel-check

The CSS-only approach below shipped first, but real-world testing showed it
doesn't produce a crossfade: because `#settings-panel` (short) and
`#video-info` (tall) are DOM siblings in normal flow, and `allow-discrete`
makes an *entering* element's `display` flip to visible immediately (while
an *exiting* element holds its full height until its transition ends),
toggling both classes in the same tick means the incoming, shorter panel
gets inserted above the still-fading, taller outgoing one for the full
150ms — visibly pushing/growing the popup rather than crossfading in place.
That read as "settings appears, then the downloader area collapses," not a
crossfade.

The actual fix keeps every CSS rule below as-is (still needed for the
fade-in/fade-out itself), but sequences the two class changes in
`browser-extension/extension/popup.js` instead of firing them together, so
only one section is ever in flow at a time:

```js
// Matches --duration-base in popup.css.
const PANEL_FADE_MS = 150;

settingsToggleBtn.addEventListener('click', () => {
  const opening = settingsPanel.classList.contains('hidden');
  if (opening) {
    loadSettings();
    videoInfoEl.classList.add('hidden');
    setTimeout(() => settingsPanel.classList.remove('hidden'), PANEL_FADE_MS);
  } else {
    settingsPanel.classList.add('hidden');
    if (infoLoaded) {
      setTimeout(() => videoInfoEl.classList.remove('hidden'), PANEL_FADE_MS);
    }
  }
});
```

This is a sequential fade (outgoing fully fades out and leaves flow, then
incoming fades in), not a true simultaneous crossfade — the right tradeoff
here since the two sections are different heights and true overlap would
either clip or jump. `PANEL_FADE_MS` duplicates `--duration-base`'s value
(`150`) as a plain number since reading a CSS custom property from JS via
`getComputedStyle` was judged not worth the complexity for one constant;
keep the two in sync by hand if `--duration-base` ever changes.

## Problem

`#settings-panel` and `#video-info` are mutually exclusive: opening settings
hides the video info section, and closing settings (when info was loaded)
shows it again. This logic lives in
`browser-extension/extension/popup.js:223-234`:

```js
settingsToggleBtn.addEventListener('click', () => {
  const opening = settingsPanel.classList.contains('hidden');
  settingsPanel.classList.toggle('hidden');
  if (opening) {
    videoInfoEl.classList.add('hidden');
    loadSettings();
  } else if (infoLoaded) {
    videoInfoEl.classList.remove('hidden');
  }
});
```

Both elements use the generic `.hidden` class
(`browser-extension/extension/popup.css:204-206`):

```css
.hidden {
  display: none;
}
```

`display: none` cannot be transitioned — the swap is an instant, jarring cut
between two full sections of the popup, every single time the gear icon is
clicked. This is exactly the "state changes that teleport" case in
`AUDIT.md` category 8: "State changes that teleport (content swaps, layout
jumps) where a brief transition would prevent a jarring change."

Because the two sections are already mutually exclusive by the JS logic
above (never both visible, and the class toggles happen synchronously in
the same click handler), fading each one independently — without any JS
timing changes — produces a natural crossfade for free: the outgoing
section fades out while the incoming one fades in, in the same frame.

## Target

Use `@starting-style` + `transition-behavior: allow-discrete` (the modern,
JS-free way to transition a `display: none` toggle) scoped to only these two
elements — do NOT modify the shared `.hidden` class, since it's also used by
`#thumb`, `#icon-sun`, `#icon-moon`, and `#progress-wrap`, which are out of
scope for this plan (see Boundaries).

Add this new block to `browser-extension/extension/popup.css`, placed
directly after the existing `.hidden { display: none; }` rule (currently
lines 204-206):

```css
#settings-panel,
#video-info {
  opacity: 1;
  transition: opacity var(--duration-base) var(--ease-out), display var(--duration-base) allow-discrete;
}

#settings-panel.hidden,
#video-info.hidden {
  opacity: 0;
  display: none;
}

@starting-style {
  #settings-panel:not(.hidden),
  #video-info:not(.hidden) {
    opacity: 0;
  }
}
```

## Repo conventions to follow

- This plan depends on `001-motion-tokens.md` having already added
  `--duration-base: 150ms;` and `--ease-out: cubic-bezier(0.23, 1, 0.32, 1);`
  to `:root` in `popup.css`. If those tokens are not present, run plan 001
  first — do not hardcode the duration or invent a different curve here.
- `#settings-panel` already has its own rule block at lines 95-98
  (`margin-bottom`, `padding-bottom`, `border-bottom`) — this plan adds a
  **separate, new** rule block for the opacity/display transition rather
  than merging into that existing block, matching this file's existing
  pattern of one selector block per concern (compare how `#thumb` at line
  214 and `#thumb.hidden` at line 225 are already two separate blocks for
  the same element).

## Steps

1. In `browser-extension/extension/popup.css`, locate the `.hidden { display:
   none; }` rule (currently lines 204-206).
2. Immediately after it, insert the three new rule blocks shown in Target
   verbatim.
3. Do not modify the `.hidden` rule itself, and do not modify
   `browser-extension/extension/popup.js` — this is a CSS-only fix.

## Boundaries

- Do NOT modify the generic `.hidden` class (lines 204-206) — it's shared
  by `#thumb`, `#icon-sun`, `#icon-moon`, and `#progress-wrap`, none of
  which are in scope here (the icon crossfade is a separate plan,
  `005-theme-icon-crossfade.md`; `#thumb` and `#progress-wrap` are not part
  of any approved finding).
- Do NOT touch `browser-extension/extension/popup.js` — the existing toggle
  logic already produces a correct crossfade once the CSS above is in
  place; no JS timing changes are needed or wanted.
- Do NOT touch `browser-extension/extension-chromium/` — `popup.css` is
  copied from `browser-extension/extension/` at build time.
- If `#settings-panel` or `#video-info` no longer use the `.hidden` class
  for visibility (drift since commit `caf781bee`), STOP and report instead
  of inventing a new toggle mechanism.

## Verification

- **Mechanical**: no JS changes to check. Confirm the CSS is valid (no
  stray braces) by re-reading the edited region.
- **Feel check**:
  - Open the popup on a valid video page (so `#video-info` populates) and
    click the settings gear icon: `#video-info` should fade out smoothly
    while `#settings-panel` fades in, instead of an instant cut. Click it
    again: the reverse should happen.
  - In DevTools' Animations panel (Chrome/Edge), trigger the toggle and set
    playback to 10% to confirm both elements are genuinely animating
    opacity over `150ms`, not still snapping instantly.
  - Confirm the popup's height still updates correctly with no layout
    glitch mid-fade (the scrollbar bug this session's earlier fix solved
    must not reappear) — the two sections must still never be
    simultaneously laid-out and visible long enough to overflow the
    popup's height budget.
  - Reduced motion: this is a pure opacity fade with no positional
    movement, so per `AUDIT.md` category 6 ("keep transitions that aid
    comprehension, remove position changes") it should NOT be gated behind
    `prefers-reduced-motion` — confirm it still fades normally with
    reduced motion emulated in DevTools' Rendering panel.
- **Done when**: toggling settings produces a visible crossfade (not an
  instant cut) in both directions, the popup's height/scrollbar behavior is
  unaffected, and the fade still plays under emulated
  `prefers-reduced-motion: reduce`.
