# obsidian-app-bridge

English | [日本語](README.ja.md)

A tiny web server that lets you open Obsidian notes from places where `obsidian://` links can't be clicked, such as chat apps.

Opening `https://<host>/o/<vault>/<path relative to the vault>` returns an HTML page that forwards to `obsidian://open?vault=...&file=...`. For browsers that don't follow the redirect automatically, the page also shows an "Open in Obsidian" button.

The page text is shown in English or Japanese, chosen from the browser's `Accept-Language` (English when neither matches). To add a language, add an entry to `MESSAGES` in `server.py`.

After the hand-off to Obsidian, the page closes its own tab with `window.close()`. It does this when the tab becomes hidden, or when you come back to it after it lost focus. Losing focus alone doesn't close the tab: on Windows, Chrome and Edge show a confirmation dialog for external apps, which fires `blur`, and closing the tab at that point would dismiss the dialog with it. Whether the tab can be closed depends on the browser; if it can't, the page shows "You can close this tab."

- It never reads vault files; it only rebuilds the received path into the target URL
- Only the configured vaults are accepted; anything else, and `/`, returns 404
- Paths are not logged
- By default it listens only on 127.0.0.1:8765. Expose it through a reverse proxy such as [Tailscale Funnel](https://tailscale.com/kb/1223/funnel)

Requires Python 3.9+ (standard library only).

## Configuration

Set environment variables, or put a `.env` file at the root of the clone (environment variables take precedence).

| Variable | Used by | Description |
|---|---|---|
| `OBSIDIAN_LINK_BASE` | link.py | Prefix of generated links (e.g. `https://<host>.<tailnet>.ts.net/o`). Required |
| `OBSIDIAN_LINK_VAULTS` | server.py | Accepted vault names (comma-separated). Required |
| `OBSIDIAN_LINK_HOST` | server.py | Listen address (default `127.0.0.1`) |
| `OBSIDIAN_LINK_PORT` | server.py | Listen port (default `8765`) |

```bash
cp env.example .env
chmod 600 .env
# edit .env
```

## Generate a link

```bash
python3 -I link.py MyVault 'Folder/Note.md'
```

## Install (example: systemd user unit + Tailscale Funnel)

First, change the `ExecStart` path in `obsidian-app-bridge.service` to match where you cloned the repository.

```bash
# 1. Run as a service (use loginctl enable-linger to keep it running while logged out)
systemctl --user link "$PWD/obsidian-app-bridge.service"
systemctl --user enable --now obsidian-app-bridge.service

# 2. Expose via Funnel (the first time, enable Funnel for your tailnet at the URL shown)
sudo tailscale funnel --bg 8765

# Check
tailscale funnel status
```

## Uninstall

```bash
sudo tailscale funnel --https=443 off
systemctl --user disable --now obsidian-app-bridge.service
```

## Security note

Anyone who knows the URL can open it. The server only returns a redirect rebuilt from the given path, so note contents are never exposed, but the vault name and note path are part of the URL.

## License

[MIT](LICENSE)
