# 002 — Fix progress bar to animate transform, not width, with linear easing

- **Status**: DONE
- **Commit**: caf781bee
- **Severity**: HIGH
- **Category**: Performance + Easing & Duration
- **Estimated scope**: 2 files (`popup.css`, `popup.js`), 1 rule + 1 line

## Problem

The download progress bar — the single most continuously-watched animation
in this popup, since it updates repeatedly throughout every download —
violates two audit rules at once.

`browser-extension/extension/popup.css:379-384` (current):

```css
#progress-bar {
  background: var(--accent);
  height: 100%;
  width: 0%;
  transition: width 200ms ease, background-color 150ms ease;
}
```

1. **Performance**: it animates `width`, a layout-triggering property.
   `AUDIT.md` category 5: "Animate `transform` and `opacity` only.
   `width`/`height`/`margin`/`padding`/`top`/`left` trigger layout + paint +
   composite."
2. **Easing**: it uses `ease` for a progress indicator. `AUDIT.md` category 2
   decision order: "Constant motion (marquee, progress) → `linear`." Bare
   `ease` on a value that's updated many times per second (see
   `browser-extension/extension/popup.js:79`, called from `renderJob()` on
   every `jobUpdate` message) means each retargeted transition eases in/out
   instead of tracking the reported percentage at a steady rate, which reads
   as subtly laggy/springy rather than a mechanical fill.

`browser-extension/extension/popup.js:79` (current, inside `renderJob`):

```js
  progressBar.style.width = percent + '%';
```

## Target

`browser-extension/extension/popup.css` — replace the `#progress-bar` rule
(lines 379-384) with:

```css
#progress-bar {
  background: var(--accent);
  height: 100%;
  width: 100%;
  transform: scaleX(0);
  transform-origin: left;
  transition: transform var(--duration-slow) linear, background-color var(--duration-base) ease;
}
```

`browser-extension/extension/popup.js` — replace line 79 with:

```js
  progressBar.style.transform = 'scaleX(' + (percent / 100) + ')';
```

## Repo conventions to follow

- This plan depends on `001-motion-tokens.md` having already added
  `--duration-slow: 200ms;` and `--duration-base: 150ms;` to `:root` in
  `popup.css`. If those tokens are not present when you run this plan, run
  plan 001 first — do not hardcode `200ms`/`150ms` here.
- `#progress-track` (the bar's parent, immediately above `#progress-bar` in
  the file) already has `overflow: hidden;` — this is required for
  `scaleX()` to look identical to the old `width` behavior (the scaled
  element must be clipped to the track), and is already present, so no
  change needed there. Just confirm it's still there after your edit.
- `transform-origin: left` is required — without it, `scaleX()` scales from
  the element's center by default, which would make the bar grow from the
  middle outward instead of filling left-to-right.

## Steps

1. In `browser-extension/extension/popup.css`, replace the `#progress-bar`
   rule (currently lines 379-384) with the Target block above.
2. In `browser-extension/extension/popup.js`, replace line 79
   (`progressBar.style.width = percent + '%';`) with the Target line above.
3. Confirm `#progress-track` still has `overflow: hidden;` immediately
   above the `#progress-bar` rule you just edited.

## Boundaries

- Do NOT change `#progress-track`'s own rule beyond confirming
  `overflow: hidden` is present.
- Do NOT touch `#progress-wrap.is-success`/`#progress-wrap.is-error`
  overrides (they only change `background`, which still applies correctly
  to the transform-based bar unchanged).
- Do NOT touch `browser-extension/extension-chromium/` — `popup.js`/`popup.css`
  are copied from `browser-extension/extension/` at build time.
- If `popup.js:79` no longer reads `progressBar.style.width = percent + '%';`
  verbatim (drift since commit `caf781bee`), STOP and report instead of
  guessing where the equivalent line moved to.

## Verification

- **Mechanical**: `node --check browser-extension/extension/popup.js`
  succeeds.
- **Feel check**: load the extension and start a real download.
  - The bar should fill left-to-right exactly as before, visually
    indistinguishable in direction/position from the old `width`-based
    version.
  - In DevTools' Performance panel, record a download in progress and
    confirm the `#progress-bar` updates now show as compositor-only
    (no purple "Layout" entries triggered by the bar itself).
  - The fill should look mechanically steady rather than easing in/out on
    each update — most noticeable when percentage jumps happen in quick
    succession (e.g. watch the console log added earlier in this project's
    `background.js` for `jobUpdate` frequency, or just observe a fast
    download).
  - Trigger both a successful download (bar should end solid
    `--success-text` green) and a failed one (bar should end
    `--error-text` red) to confirm the `is-success`/`is-error` background
    override still applies correctly to the transform-based bar.
- **Done when**: the bar fills via `transform: scaleX()` (verify in
  DevTools' Elements > Computed panel that `width` is static at `100%` and
  only `transform` changes as downloads progress), using `linear` timing,
  and the visual fill behavior matches the old version in direction and
  position.
