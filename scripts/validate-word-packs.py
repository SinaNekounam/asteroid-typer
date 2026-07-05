"""
Validates content/word-packs.json against content/blocklist.json.

Checks every word in every pack/tier for:
  1. Blocklist matches (case-insensitive, exact word)
  2. Invalid characters (must be a single continuous alphabetic token --
     the game types words as one string, so spaces/hyphens/digits break it)
  3. Duplicate words within the same pack (across its three tiers)
  4. Tiers with far fewer than the ~30 target word count

Run after any edit to either JSON file:
    python scripts/validate-word-packs.py
"""
import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
PACKS_PATH = ROOT / "content" / "word-packs.json"
BLOCKLIST_PATH = ROOT / "content" / "blocklist.json"

TOKEN_RE = re.compile(r"^[a-z]+$")
TARGET_COUNT = 30
MIN_ACCEPTABLE = 20


def load_blocklist(data):
    banned = set()
    for key, words in data.items():
        if key.startswith("_"):
            continue
        for w in words:
            banned.add(w.lower())
    return banned


def main():
    packs = json.loads(PACKS_PATH.read_text(encoding="utf-8"))
    blocklist_raw = json.loads(BLOCKLIST_PATH.read_text(encoding="utf-8"))
    banned = load_blocklist(blocklist_raw)

    errors = []
    warnings = []
    total_words = 0

    for tier_group in ("free", "premium"):
        for pack_id, pack in packs.get(tier_group, {}).items():
            pack_words_seen = {}  # word -> list of tiers it appears in
            for level in ("starter", "explorer", "champion"):
                words = pack.get(level, [])
                count = len(words)
                total_words += count

                if count < MIN_ACCEPTABLE:
                    warnings.append(
                        f"[{tier_group}/{pack_id}/{level}] only {count} words "
                        f"(target ~{TARGET_COUNT}, minimum {MIN_ACCEPTABLE})"
                    )

                seen_in_level = set()
                for w in words:
                    lw = w.lower()

                    if not TOKEN_RE.match(lw):
                        errors.append(
                            f"[{tier_group}/{pack_id}/{level}] invalid token: '{w}' "
                            f"(must be a single a-z word, no spaces/hyphens/digits)"
                        )

                    if lw in banned:
                        errors.append(
                            f"[{tier_group}/{pack_id}/{level}] BLOCKED WORD: '{w}' "
                            f"is on the blocklist and must be removed"
                        )

                    if lw in seen_in_level:
                        warnings.append(
                            f"[{tier_group}/{pack_id}/{level}] duplicate within tier: '{w}'"
                        )
                    seen_in_level.add(lw)

                    pack_words_seen.setdefault(lw, []).append(level)

            for w, levels in pack_words_seen.items():
                if len(levels) > 1:
                    warnings.append(
                        f"[{tier_group}/{pack_id}] '{w}' appears in multiple tiers: {levels}"
                    )

    total_packs = sum(len(packs.get(g, {})) for g in ("free", "premium"))
    print(f"Checked {total_words} words across {total_packs} packs.\n")

    if errors:
        print(f"❌ {len(errors)} ERROR(S) — must fix before going live:\n")
        for e in errors:
            print("  " + e)
        print()
    else:
        print("✅ No blocklist violations or invalid tokens found.\n")

    if warnings:
        print(f"⚠️  {len(warnings)} warning(s) (not safety issues, but worth cleaning up):\n")
        for w in warnings:
            print("  " + w)
    else:
        print("✅ No warnings.")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
