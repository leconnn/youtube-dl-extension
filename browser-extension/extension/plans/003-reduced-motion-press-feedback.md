# 003 — Respect prefers-reduced-motion for button press feedback

- **Status**: DONE
- **Commit**: caf781bee
- **Severity**: LOW
- **Category**: Accessibility
- **Estimated scope**: 1 file (`browser-extension/extension/popup.css`), 1 new block

## Problem

`browser-extension/extension/popup.css` has five `:active` rules that apply a
scale-down transform as press feedback, and zero `@media (prefers-reduced-motion: reduce)`
handling anywhere in the file:

```css
/* line 91-93 */
.icon-btn:active {
  transform: scale(0.92);
}

/* line 154-156 */
#browse-dir:active {
  transform: scale(0.96);
}

/* line 188-190 */
#save-settings:active {
  transform: scale(0.96);
}

/* line 329-331 */
#download:active {
  transform: scale(0.98);
}

/* line 358-360 */
#download-to:active {
  transform: scale(0.94);
}
```

`AUDIT.md` category 6: "Reduced motion means fewer and gentler animations,
not zero — keep transitions that aid comprehension, remove position
changes." These scale transforms are movement that should be dropped for
users with `prefers-reduced-motion: reduce`, while the color/background
feedback these same buttons already have (e.g. `.icon-btn:hover`'s
background/color change, `#download:hover`'s background change) should be
kept — it doesn't involve movement and aids comprehension of the pressed
state.

## Target

Add a single new block at the end of
`browser-extension/extension/popup.css` (after the last existing rule,
`#progress-wrap.is-error #progress-text`):

```css
@media (prefers-reduced-motion: reduce) {
  .icon-btn:active,
  #browse-dir:active,
  #save-settings:active,
  #download:active,
  #download-to:active {
    transform: none;
  }
}
```

This overrides only the `transform` value back to `none` under reduced
motion, for exactly the five selectors listed in Problem. It does not touch
`transition` (so color/background feedback continues to animate normally)
and does not affect any `:hover` or `:disabled` rule.

## Repo conventions to follow

- This is the first `@media` query in the file; place it as a new top-level
  block, not nested inside any existing rule.
- Match the file's existing multi-selector comma-list style (see
  `#progress-wrap.is-success #progress-bar` and its sibling rules for the
  formatting convention already used for grouped selectors elsewhere, or
  simply follow the Target block's formatting exactly).

## Steps

1. Open `browser-extension/extension/popup.css` and confirm the five
   `:active` selectors listed in Problem still exist with a `transform:
   scale(...)` declaration (the exact scale values don't matter for this
   plan — only that a transform is present to override).
2. Append the Target `@media (prefers-reduced-motion: reduce) { ... }`
   block to the end of the file.

## Boundaries

- Do NOT modify the five `:active` rules themselves — only add the new
  override block.
- Do NOT add `prefers-reduced-motion` handling to anything else in the file
  (e.g. the `background-color`/`border-color`/`color` transitions elsewhere
  are not movement and should keep animating under reduced motion, per
  `AUDIT.md`'s explicit "not zero" guidance).
- Do NOT touch `browser-extension/extension-chromium/` — `popup.css` is
  copied from `browser-extension/extension/` at build time.
- If any of the five selectors no longer exist verbatim (drift since commit
  `caf781bee`), STOP and report which one is missing instead of guessing a
  replacement selector.

## Verification

- **Mechanical**: no JS/build changes; a visual re-read of the appended
  block for valid CSS syntax is sufficient.
- **Feel check**:
  - In Chrome/Edge DevTools, open the Rendering tab (Cmd/Ctrl+Shift+P →
    "Show Rendering"), set "Emulate CSS media feature
    prefers-reduced-motion" to `reduce`, then click and hold each of the
    five buttons (theme toggle, settings toggle, Browse, Save, Download,
    Download-to) and confirm none of them visibly shrink/scale on press.
  - With the emulation still set to `reduce`, confirm hover states (e.g.
    `.icon-btn:hover`'s background change, `#download:hover`'s background
    darken) still visibly animate — reduced motion should not have
    silenced all feedback, only the scale movement.
  - Turn the emulation back to "No emulation" and confirm all five buttons
    scale down on press exactly as before.
- **Done when**: pressing any of the five buttons produces zero transform
  movement under emulated `prefers-reduced-motion: reduce`, while color/
  background hover and press feedback remains animated in both modes.
