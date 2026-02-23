#!/usr/bin/env python3
"""
Строит словарь emoji -> custom_emoji_id из ответа getStickerSet (tgiosicons и др.).
Использование:
  python scripts/build_emoji_map.py < sticker_set.json
  python scripts/build_emoji_map.py path/to/sticker_set.json
  echo '{"ok":true,"result":{...}}' | python scripts/build_emoji_map.py
Вывод: Python-файл emoji_to_custom_id.py с константой EMOJI_TO_CUSTOM_ID.
"""

import json
import sys
from pathlib import Path


def build_map(data: dict) -> dict[str, str]:
    """Из result.get("stickers", []) строит {emoji: custom_emoji_id}, первый id для каждого emoji."""
    result = data.get("result") or data
    stickers = result.get("stickers") or []
    out = {}
    for s in stickers:
        emoji = s.get("emoji") or ""
        eid = s.get("custom_emoji_id")
        if emoji and eid is not None and emoji not in out:
            out[emoji] = str(eid)
    return out


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        raw = path.read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()
    data = json.loads(raw)
    if not data.get("ok"):
        print("JSON не ok:", data, file=sys.stderr)
        sys.exit(1)
    mapping = build_map(data)
    # Пишем Python-модуль
    lines = [
        "# Auto-generated from getStickerSet result. emoji -> custom_emoji_id (string).",
        "EMOJI_TO_CUSTOM_ID = {",
    ]
    for emoji, eid in sorted(mapping.items(), key=lambda x: (x[0], x[1])):
        # Экранируем кавычки и бэкслеши в emoji для repr
        lines.append(f'    {repr(emoji)}: {repr(eid)},')
    lines.append("}")
    out_path = Path(__file__).resolve().parent.parent / "emoji_to_custom_id.py"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Written {len(mapping)} entries to {out_path}", file=sys.stderr)
    print(out_path)


if __name__ == "__main__":
    main()
