# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

"Asteroid Typer" — a dependency-free typing game for kids (ages ~1-12), playable on the web, iOS, and
Android from **one codebase**. Words ("asteroids") fall from the top of the screen toward a ship; the
player types each word exactly to destroy it before it lands. Instead of difficulty levels, the player
picks a subject **pack** (Animals, Colors, Space, Math, etc.) — 12 free packs and 12 premium (visually
locked, no payment integration yet).

The entire game is still one file, [index.html](index.html) (HTML + a `<style>` block + a single `<script>`
IIFE) — no framework, no bundler for the game logic itself. Mobile packaging is handled by **Capacitor**,
which wraps that same `index.html` in a thin native WebView shell for iOS/Android. **`index.html` at the
repo root is the single source of truth** — never hand-edit anything under `www/`, `android/app/src/main/
assets/public/`, or `ios/App/App/public/`; those are generated copies (see Mobile section below).

## Running it (web)

There's no bundler/dev-server dependency baked into the game itself — just serve the static file and open
it in a browser:

```bash
python -m http.server 5173
```

This matches the `static-server` configuration in `.claude/launch.json` (used by the Claude Code preview
tool). Prefer this over `npx serve` for quick local checks of `index.html` directly — Node is now installed
(see Mobile section) but the plain static server is still the fastest loop for pure web/gameplay changes.

There is no test suite, linter, or build command for the game logic — verify changes by loading the page in
a browser and playing through the game loop (see Verification below).

## Mobile (Capacitor) — iOS & Android

`package.json` + `capacitor.config.json` (`appId: com.sinanekounam.asteroidtyper`, `webDir: www`) wrap the
web app for native platforms. Key thing to internalize: **`www/` is a build output, not source** — it's
populated by copying root-level files, never edited directly.

- `scripts/sync-web.js` copies `index.html`, `og-image.png`, `manifest.json`, `service-worker.js`, and
  `icons/` from the repo root into `www/`. Run via `npm run sync-web`.
- `npm run cap:sync` runs that sync, then `npx cap sync` (copies `www/` into `android/app/src/main/assets/
  public/` and `ios/App/App/public/`, and updates native plugin registration). **Run this after any change
  to `index.html` before testing/building the native apps** — otherwise the native shells serve a stale copy.
- `android/` and `ios/` are the actual native projects (committed to git, per normal Capacitor convention —
  they're not disposable build output; `AndroidManifest.xml`, `Info.plist`, signing config, etc. all live in
  there and may need hand-editing later). Build artifacts inside them (`android/app/build/`, `ios/App/Pods/`,
  etc.) are gitignored.
- App icon/splash source images live in `assets/` (`icon.png`, `icon-foreground.png`, `splash.png`,
  `splash-dark.png` — all derived from one square rocket-ship icon). Regenerate all platform sizes after
  changing these with `npx capacitor-assets generate`, which also refreshes the PWA icon set in `icons/`.
- **No local Xcode or Android Studio is assumed available in this environment** (this is a Windows machine;
  iOS builds require macOS per Apple's toolchain requirement). `.github/workflows/build-mobile.yml` builds an
  unsigned debug APK (Android, `ubuntu-latest`) and an unsigned iOS Simulator build (`macos-latest`) on every
  push, purely to catch native-project breakage in CI. **Neither job produces a store-submittable build** —
  real App Store/Play Store releases need the user's own Apple/Google developer accounts and signing
  certificates wired in as repo secrets, which hasn't been set up.
- The web build also doubles as an installable PWA: `manifest.json` + `service-worker.js` (offline caching)
  are linked from `index.html`'s `<head>`. The service worker registration is guarded to skip when running
  inside the Capacitor native shell (`window.Capacitor` present) or over plain `http://` (registration
  requires a secure context) — see the small `<script>` block right before `</body>`.

There is no test suite, linter, or build command beyond what's described above — verify changes by loading
the page in a browser and playing through the game loop (see Verification below).

## Architecture (all in `index.html`)

The script is one IIFE with distinct sections marked by `/* ---- Section ---- */` comments. Reading order
that matters:

1. **Word packs** (`PACKS` — a `{ free: {...}, premium: {...} }` object) — each pack has `name`, `icon`, and
   three word-list tiers: `starter`/`explorer`/`champion` (easy → hard within that subject). `PACKS` is a
   direct embed of [content/word-packs.json](content/word-packs.json) (minus its `_readme` key); **that JSON
   file is the source of truth** — edit it, run `scripts/validate-word-packs.py` (checks every word against
   [content/blocklist.json](content/blocklist.json) for kid-safety and flags cross-tier duplicates or
   invalid tokens), then re-embed the compact JSON into the `PACKS` const in `index.html`. Every word must be
   a single a-z token — no spaces/hyphens/accents — since the game types words as one continuous string.
   `pickWord` walks `[starter, explorer, champion]` as the player's level increases, same mechanism the old
   difficulty tiers used. Premium packs render with a lock badge (`.pack-tile.locked`) and show a toast
   (`showLockedMessage`) instead of starting a game — there's no real payment/subscription system wired up
   yet, so treat "premium" as UI-only gating for now.

2. **Audio** (`ensureAudio`, `beep`, `sfx`) — all sound is synthesized via the Web Audio API (oscillators),
   no audio files. `sfx` is a small dictionary of named cues (`key`, `destroy`, `miss`, `lifeLost`,
   `levelUp`, `gameOver`) composed from `beep()` calls.

3. **Game state** (`makeState`, `state`) — a single mutable `state` object holds everything for the current
   run (asteroids, score, lives, combo, level, keystroke counters, rAF id). There is no framework/virtual
   DOM: asteroid words are plain `<div>`s created in `spawnAsteroid` and mutated directly
   (`el.style.top`, `innerHTML`) each frame.

4. **Main loop** (`tick`) — a single `requestAnimationFrame` loop drives spawning and falling. Movement is
   **delta-time normalized**, not frame-count based: `frames = dt / (1000/60)`, then
   `a.y += a.speed * frames`, with `dt` clamped to 100ms to avoid teleporting after tab-throttling/backgrounding.
   Keep this pattern when changing movement/timing logic — a naive `a.y += a.speed` per rAF call ties speed
   to actual frame rate and was a real bug fixed previously. Per-asteroid fall speed (set in `spawnAsteroid`)
   is **word-length- and level-based**, not pack-based: `BASE_FALL_SPEED * lengthFactor(word) *
   levelMultiplier(level) * jitter` — shorter words fall slowly (friendly for young kids), longer words fall
   faster and are worth more points (`word.length * 10` in `handleWordComplete`). There's no per-pack
   difficulty config anymore; `BASE_FALL_SPEED`/`BASE_SPAWN_MS`/`LIVES` are the same for every pack.

5. **Input handling** (`onKeyDown`) — listens on `document`, not just a focused input (a hidden `<input>`
   exists only to summon mobile keyboards). Typed characters are matched as a *prefix* against all live
   asteroid words; a wrong keystroke resets the typed buffer and breaks the combo. Word completion is
   detected via exact match against `s.typed`.

6. **Screen management** (`showScreen`, `startGame`, `endGame`) — three top-level screens (`#startScreen`,
   `#gameScreen`, `#gameOverScreen`) are toggled via a `.hidden` class; only one is visible at a time.

## Known environment quirk (not a code bug)

In the Claude Code preview tool, the embedded browser tab is sometimes reported as `document.hidden = true`
even while "focused," which pauses `requestAnimationFrame` entirely (no spawning/falling motion) and can
make `preview_screenshot` calls time out. If falling asteroids appear frozen during automated testing,
check `document.hidden`/`document.visibilityState` before assuming the game logic is broken — restarting
the preview server (`preview_stop` + `preview_start`) or clicking into the page can restore visibility.
Direct `.click()` via `preview_eval` is a reliable fallback when coordinate-based `preview_click` misfires.

## Verification

Manual test pass after any change (no automated tests exist):
- If `content/word-packs.json` or `content/blocklist.json` changed, run
  `python scripts/validate-word-packs.py` first and fix any errors before re-embedding into `index.html`.
- Select a free pack and confirm words on screen come from that pack (not another one).
- Click a premium pack — confirm it shows the lock toast and does **not** start a game.
- Type full words correctly — confirm progressive letter highlighting, destroy animation + sound, and
  score/WPM/accuracy updates; confirm longer words visibly fall faster than short ones.
- Mistype deliberately — confirm accuracy drops and combo resets.
- Let a word fall to the bottom — confirm a life is lost, screen-shake plays, and game-over triggers at 0
  lives with correct final stats.
- Check `preview_console_logs` (or browser devtools) for runtime errors.
- Resize to mobile/tablet/desktop — the HUD uses `clamp()` sizing and `flex-wrap`, and the start screen
  `.panel` scrolls (`max-height: 88vh; overflow-y: auto`) to fit the 24-pack grid on short viewports;
  re-check both if touching that CSS.
- If `index.html` changed, run `npm run cap:sync` before assuming the native apps reflect it — the
  `.github/workflows/build-mobile.yml` CI run (Android debug APK + iOS Simulator build) is the cheapest way
  to confirm the native projects still build after a change.
