# 005 — Crossfade the theme toggle's sun/moon icon swap

- **Status**: DONE
- **Commit**: caf781bee
- **Severity**: Missed opportunity (treat as LOW impact when scheduling)
- **Category**: Missed opportunities / Cohesion
- **Estimated scope**: 1 file (`browser-extension/extension/popup.css`), CSS only — no JS changes

## Problem

Switching themes already crossfades smoothly: `body`'s background and text
color animate over `150ms` (`browser-extension/extension/popup.css:44`,
`transition: background-color var(--duration-base) ease, color var(--duration-base) ease;`
after plan 001 — currently `150ms` literal). But the sun/moon icon inside the
same toggle button swaps with an instant, unanimated `display: none` cut via
the shared `.hidden` class, driven by
`browser-extension/extension/popup.js:263-264`:

```js
  iconMoon.classList.toggle('hidden', isDark);
  iconSun.classList.toggle('hidden', !isDark);
```

The two icons are both plain children of `#theme-toggle`
(`browser-extension/extension/popup.html:13-21`):

```html
<button id="theme-toggle" class="icon-btn" type="button" title="Switch to dark mode" aria-label="Toggle theme">
  <svg id="icon-moon" width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
    <path d="M13.8 10.2A6 6 0 0 1 6.2 2.4a.5.5 0 0 0-.7-.6 7 7 0 1 0 9 9 .5.5 0 0 0-.7-.6z"/>
  </svg>
  <svg id="icon-sun" class="hidden" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3">
    <circle cx="8" cy="8" r="2.2"/>
    <path d="M8 1.5v1.6M8 12.9v1.6M14.5 8h-1.6M3.1 8H1.5M12.4 3.6l-1.1 1.1M4.7 11.3l-1.1 1.1M12.4 12.4l-1.1-1.1M4.7 4.7 3.6 3.6"/>
  </svg>
</button>
```

Right now this is a mismatch of polish on a single user action: the button's
own background color transitions smoothly (via `.icon-btn`'s existing
transition), the page-wide colors crossfade smoothly, but the glyph in the
middle of that same button just cuts.

## Target

The two `<svg>` icons are normal flow children of `#theme-toggle` (a flex
container via `.icon-btn`), so a plain opacity crossfade would make the
button briefly grow/shift as both icons exist in flow simultaneously during
the transition. They need to be stacked on top of each other first.

Add this new block to `browser-extension/extension/popup.css`, placed
directly after the `.icon-btn:active { transform: scale(0.92); }` rule
(currently lines 91-93):

```css
#theme-toggle {
  position: relative;
}

#icon-moon,
#icon-sun {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  opacity: 1;
  transition: opacity var(--duration-base) var(--ease-out), display var(--duration-base) allow-discrete;
}

#icon-moon.hidden,
#icon-sun.hidden {
  opacity: 0;
  display: none;
}

@starting-style {
  #icon-moon:not(.hidden),
  #icon-sun:not(.hidden) {
    opacity: 0;
  }
}
```

## Repo conventions to follow

- This plan depends on `001-motion-tokens.md` having already added
  `--duration-base: 150ms;` and `--ease-out: cubic-bezier(0.23, 1, 0.32, 1);`
  to `:root` in `popup.css`, and pairs with `004-settings-video-info-crossfade.md`,
  which uses the identical `@starting-style` + `allow-discrete` pattern —
  follow that plan's block as the exemplar for this technique if there's
  any ambiguity.
- `.icon-btn` (which `#theme-toggle` uses) already sets
  `display: inline-flex; align-items: center; justify-content: center;`
  (lines 71-84) to center a single child. Once the icons are
  `position: absolute`, they're removed from that flex flow — the
  `top: 50%; left: 50%; transform: translate(-50%, -50%)` centering in
  Target is what replaces it for these two specific children. Do not remove
  or change `.icon-btn`'s own centering, since `#settings-toggle` (the
  other button using this class) has only one icon and still needs it.

## Steps

1. In `browser-extension/extension/popup.css`, locate `.icon-btn:active`
   (currently lines 91-93).
2. Immediately after it, insert the four new rule blocks shown in Target
   verbatim.
3. Do not modify `browser-extension/extension/popup.js` or `popup.html` —
   this is a CSS-only fix; the existing `classList.toggle('hidden', ...)`
   calls already drive the new transition correctly.

## Boundaries

- Do NOT modify the shared `.hidden` class (lines 204-206) — see
  `004-settings-video-info-crossfade.md`'s Boundaries for why (it's shared
  by unrelated elements not in scope).
- Do NOT change `#settings-toggle` or its icon — only `#theme-toggle` and
  its two child SVGs (`#icon-moon`, `#icon-sun`) are in scope.
- Do NOT touch `browser-extension/extension-chromium/` — `popup.css` is
  copied from `browser-extension/extension/` at build time.
- If `#icon-moon`/`#icon-sun` are no longer both direct children of
  `#theme-toggle` (drift since commit `caf781bee`), STOP and report instead
  of restructuring the markup yourself.

## Verification

- **Mechanical**: no JS changes to check. Confirm the CSS is valid CSS by
  re-reading the edited region.
- **Feel check**:
  - Click the theme toggle repeatedly: the moon and sun icons should
    crossfade in place (same position, no shift/jump in the button), in
    sync with the page-wide color transition already happening.
  - Confirm the button's overall size (22x22px, from `.icon-btn`) does not
    change or jump during the transition — both icons must occupy the
    exact same visual slot throughout.
  - In DevTools' Animations panel, set playback to 10% and confirm both
    icons are genuinely cross-fading (one opacity ramping down, the other
    ramping up) rather than one instantly popping in after the other fully
    disappears.
  - Toggle rapidly (click several times in quick succession): the fade
    should smoothly retarget each time (CSS transitions do this
    automatically), never getting stuck with both icons visible or both
    hidden.
  - Reduced motion: this is a pure opacity fade with no positional
    movement, so it should NOT be gated behind `prefers-reduced-motion`
    (same reasoning as plan 004) — confirm it still fades normally with
    reduced motion emulated in DevTools' Rendering panel.
- **Done when**: toggling the theme crossfades the sun/moon icons in place
  with no layout shift, matches the timing of the existing body color
  transition, and survives rapid repeated toggling without getting stuck.
