"""Vault のノートを開く https のリンクを出す。

使い方：python3 -I link.py <vault> '<Vault からの相対パス>'

転送サーバーの URL は、環境変数か、このファイルと同じフォルダの .env の
OBSIDIAN_LINK_BASE で渡す（例：https://<host>.ts.net/o。環境変数が優先）。
"""

import os
import sys
from pathlib import Path
from urllib.parse import quote


def load_env(path: Path) -> dict:
    """KEY=VALUE の行だけを読む。空行と # で始まる行は飛ばす。"""
    env = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip().strip("\"'")
    return env


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    config = {**load_env(Path(__file__).resolve().parent / ".env"), **os.environ}
    base = config.get("OBSIDIAN_LINK_BASE", "").rstrip("/")
    if not base:
        sys.exit("OBSIDIAN_LINK_BASE が未設定（env.example を参照）")
    vault, path = sys.argv[1], sys.argv[2]
    print(f"{base}/{quote(vault, safe='')}/{quote(path)}")
