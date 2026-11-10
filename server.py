"""https のリンクを obsidian:// に転送する小さな Web サーバー。

GET /o/<vault>/<Vault からの相対パス> に、obsidian://open?vault=...&file=... へ
移る HTML を返す。Vault のファイルは読まない。パスはログに残さない。
Tailscale Funnel から 127.0.0.1 に転送して使う。

設定は環境変数か、このファイルと同じフォルダの .env で渡す（環境変数が優先）。
  OBSIDIAN_LINK_VAULTS  受け付ける vault の名前（カンマ区切り。必須）
  OBSIDIAN_LINK_HOST    待ち受けるアドレス（既定 127.0.0.1）
  OBSIDIAN_LINK_PORT    待ち受けるポート（既定 8765）
"""

import html
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit


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


CONFIG = {**load_env(Path(__file__).resolve().parent / ".env"), **os.environ}
HOST = CONFIG.get("OBSIDIAN_LINK_HOST", "127.0.0.1")
PORT = int(CONFIG.get("OBSIDIAN_LINK_PORT", "8765"))
VAULTS = {v.strip() for v in CONFIG.get("OBSIDIAN_LINK_VAULTS", "").split(",") if v.strip()}
MAX_PATH = 2048

MESSAGES = {
    "en": {"open": "Open in Obsidian", "done": "You can close this tab."},
    "ja": {"open": "Obsidian で開く", "done": "このタブは閉じてかまいません"},
}
DEFAULT_LANG = "en"


def pick_lang(accept_language: str) -> str:
    """Accept-Language から、MESSAGES にある言語のうち q がいちばん高いものを選ぶ。"""
    best, best_q = DEFAULT_LANG, 0.0
    for part in accept_language.split(","):
        tag, _, params = part.strip().partition(";")
        lang = tag.strip().lower().split("-")[0]
        q = 1.0
        for param in params.split(";"):
            key, _, value = param.strip().partition("=")
            if key == "q":
                try:
                    q = float(value)
                except ValueError:
                    q = 0.0
        if lang in MESSAGES and q > best_q:
            best, best_q = lang, q
    return best


PAGE = """<!doctype html>
<html lang="{lang}"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>{title}</title>
<style>
body{{font-family:-apple-system,system-ui,sans-serif;margin:0;display:flex;min-height:100vh;align-items:center;justify-content:center;background:#1e1e1e;color:#ddd}}
a{{display:block;padding:1.2em 2em;border-radius:12px;background:#7c3aed;color:#fff;text-decoration:none;font-size:1.2em;text-align:center}}
p{{text-align:center;color:#999;word-break:break-all;padding:0 1em}}
</style>
</head><body><div>
<a href="{url}">{open}</a>
<p>{title}</p>
<p id="done" hidden>{done}</p>
</div>
<script>
// Obsidian に移ったあと（タブが隠れる）か、離れてから戻ってきたときにタブを閉じる。
// 外部アプリの確認ダイアログを消さないよう、時間では閉じない。
// フォーカスを失っただけでは閉じない（Windows の Chrome・Edge では確認ダイアログで blur が起き、
// そこで閉じるとダイアログごとタブが消える）。
// window.close() はブラウザが許したときだけ効く（Chrome などで、リンクから開いた新しいタブ）。
let left = false;
function tryClose() {{
  window.close();
  document.getElementById("done").hidden = false;
}}
document.addEventListener("visibilitychange", () => {{
  if (document.hidden) {{ left = true; tryClose(); }}
  else if (left) {{ tryClose(); }}
}});
window.addEventListener("blur", () => {{ left = true; }});
window.addEventListener("focus", () => {{ if (left) tryClose(); }});
location.href={url_js};
</script>
</body></html>
"""


def obsidian_url(vault: str, file: str) -> str:
    return f"obsidian://open?vault={quote(vault, safe='')}&file={quote(file, safe='')}"


class Handler(BaseHTTPRequestHandler):
    server_version = "obsidian-app-bridge"
    sys_version = ""

    def do_GET(self):
        path = urlsplit(self.path).path
        if len(path) > MAX_PATH or not path.startswith("/o/"):
            return self.reply(404, "not found")
        vault, _, file = path[len("/o/"):].partition("/")
        file = unquote(file)
        if vault not in VAULTS or not file:
            return self.reply(404, "not found")
        url = obsidian_url(vault, file)
        title = file.rsplit("/", 1)[-1].removesuffix(".md")
        lang = pick_lang(self.headers.get("Accept-Language", ""))
        body = PAGE.format(
            lang=lang,
            open=html.escape(MESSAGES[lang]["open"]),
            done=html.escape(MESSAGES[lang]["done"]),
            title=html.escape(title),
            url=html.escape(url),
            url_js='"' + url.replace("\\", "\\\\").replace('"', '\\"') + '"',
        )
        self.reply(200, body, "text/html; charset=utf-8")

    def reply(self, status, body, ctype="text/plain; charset=utf-8"):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Vary", "Accept-Language")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Robots-Tag", "noindex")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        # ノートのパスを journal に残さない
        pass


if __name__ == "__main__":
    if not VAULTS:
        sys.exit("OBSIDIAN_LINK_VAULTS が未設定（env.example を参照）")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
