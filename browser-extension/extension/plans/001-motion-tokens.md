# 001 — Introduce shared duration/easing tokens

- **Status**: DONE
- **Commit**: caf781bee
- **Severity**: LOW
- **Category**: Cohesion & tokens
- **Estimated scope**: 1 file (`browser-extension/extension/popup.css`), ~11 line edits

## Problem

`popup.css` hand-types the same three duration values over and over instead of
naming them once. Every occurrence uses the exact same numbers (no drift
between them), but there is no `:root` token for any of them, so every future
transition rule (including the ones added by plans 002, 004, and 005 in this
same batch) has to re-guess or re-copy a bare number.

Current occurrences (verbatim, `browser-extension/extension/popup.css`):

```css
/* line 44 */
  transition: background-color 150ms ease, color 150ms ease;

/* line 83 */
  transition: background-color 150ms ease, color 150ms ease, transform 100ms ease;

/* line 118 */
  transition: border-color 150ms ease;

/* line 147 */
  transition: border-color 150ms ease, transform 100ms ease;

/* line 181 */
  transition: background-color 150ms ease, transform 100ms ease;

/* line 241 */
  transition: border-color 150ms ease;

/* line 297 */
  transition: border-color 150ms ease;

/* line 322 */
  transition: background-color 150ms ease, transform 100ms ease;

/* line 351 */
  transition: border-color 150ms ease, transform 100ms ease;

/* line 391 */
  transition: color 150ms ease;
```

Note: `#progress-bar`'s transition rule (currently at line 383) is
**deliberately excluded** from this plan — it is fully rewritten by plan 002
(`002-progress-bar-transform-linear.md`), which owns that rule going forward.
Do not touch line 379-384 in this plan.

## Target

Add duration tokens (and one new easing curve, for plans 004/005's crossfades
— unused by this plan itself, but this is the natural place to define it
since it's a `:root` token) to the top of the file, then replace every
hardcoded duration number above with the matching token, keeping the `ease`
keyword literal (it is a short built-in identifier, not a magic number worth
tokenizing on its own):

```css
/* browser-extension/extension/popup.css — inside the existing :root block, after --radius: 6px; */
:root {
  --canvas: #fbfbfa;
  --surface: #ffffff;
  --border: #eaeaea;
  --text: #111111;
  --text-muted: #787774;
  --accent: #111111;
  --accent-hover: #333333;
  --accent-text: #ffffff;
  --radius: 6px;
  --success-text: #346538;
  --success-bg: #edf3ec;
  --error-text: #9f2f2d;
  --error-bg: #fdebec;
  --duration-fast: 100ms;
  --duration-base: 150ms;
  --duration-slow: 200ms;
  --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
}
```

Then each of the 10 lines listed in Problem becomes (number replaced with
token, `ease` keyword kept as-is):

```css
/* line 44 */
  transition: background-color var(--duration-base) ease, color var(--duration-base) ease;

/* line 83 */
  transition: background-color var(--duration-base) ease, color var(--duration-base) ease, transform var(--duration-fast) ease;

/* line 118 */
  transition: border-color var(--duration-base) ease;

/* line 147 */
  transition: border-color var(--duration-base) ease, transform var(--duration-fast) ease;

/* line 181 */
  transition: background-color var(--duration-base) ease, transform var(--duration-fast) ease;

/* line 241 */
  transition: border-color var(--duration-base) ease;

/* line 297 */
  transition: border-color var(--duration-base) ease;

/* line 322 */
  transition: background-color var(--duration-base) ease, transform var(--duration-fast) ease;

/* line 351 */
  transition: border-color var(--duration-base) ease, transform var(--duration-fast) ease;

/* line 391 */
  transition: color var(--duration-base) ease;
```

## Repo conventions to follow

- This file already has exactly one `:root { ... }` token block (lines 1-15)
  and one `:root[data-theme="dark"] { ... }` override block (lines 17-30).
  Durations/easings are theme-independent — add them only to the base
  `:root` block, never to the dark-mode override.
- Existing token naming is flat and semantic (`--text-muted`, `--accent-hover`),
  not numbered — `--duration-fast`/`--duration-base`/`--duration-slow` matches
  that style (fast/base/slow, not `--duration-1`/`--duration-2`).

## Steps

1. In `browser-extension/extension/popup.css`, inside the `:root { ... }`
   block (currently lines 1-15), add the four new custom properties shown in
   Target immediately after `--error-bg: #fdebec;` and before the closing
   `}`.
2. Replace each of the 10 transition declarations listed in Problem with its
   Target counterpart, by exact line match on the current file. Do not
   touch the `#progress-bar` rule (currently around line 383) — that belongs
   to plan 002.
3. Re-read the file after editing and confirm no other hardcoded `150ms`,
   `100ms`, or `200ms` remain outside of the `#progress-bar` rule.

## Boundaries

- Do NOT touch `#progress-bar`'s transition rule — plan 002 owns it.
- Do NOT touch `browser-extension/extension-chromium/` — it has no CSS of
  its own; the Chromium build copies `popup.css` from `browser-extension/extension/`
  at build time (`browser-extension/installer/build-chromium.ps1`), so
  editing the canonical file is sufficient.
- Do NOT change any color values, selectors, or non-transition properties.
- If any of the 10 line numbers cited above don't match what you find (file
  drifted since commit `caf781bee`), STOP and report instead of guessing
  which rule was meant.

## Verification

- **Mechanical**: `node --check browser-extension/extension/popup.js` is
  unaffected (this plan touches no JS). Open
  `browser-extension/extension/popup.css` and confirm it's still valid CSS
  (no stray commas/semicolons) — e.g. `npx stylelint browser-extension/extension/popup.css`
  if stylelint is available, otherwise a visual re-read is sufficient for a
  file this size.
- **Feel check**: load the extension unpacked (or as a Firefox temporary
  add-on) and confirm every existing transition still looks and times
  identically to before — hovering the theme/settings icons, focusing the
  download-dir/title text fields, pressing the Download/Save/Browse
  buttons. Nothing should look different; this plan is a pure refactor of
  identical values into named tokens.
- **Done when**: every transition rule in the file other than `#progress-bar`
  uses `var(--duration-fast|base|slow)` instead of a bare millisecond
  number, and the popup's visual behavior is unchanged.
