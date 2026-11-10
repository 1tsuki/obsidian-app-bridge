# obsidian-app-bridge

[English](README.md) | 日本語

チャットなど `obsidian://` を押せない画面から Obsidian のノートを開くための転送サーバー。

`https://<host>/o/<vault>/<Vault からの相対パス>` を開くと、`obsidian://open?vault=...&file=...` に移る HTML を返す（自動で移らないブラウザ向けに「Obsidian で開く」ボタンも出す）。Obsidian に移ったあと（タブが隠れる・フォーカスを失う）か、離れてから戻ってきたときに `window.close()` でタブを閉じる。Windows では、フォーカスを失っただけでは閉じない（Chrome・Edge では外部アプリの確認ダイアログで blur が起き、そこで閉じるとダイアログごとタブが消えるため）。Windows 以外では、Obsidian が前に出てもタブが隠れた扱いにならないことがあるので、blur で閉じる。閉じられるかはブラウザ次第で、閉じられないときは「このタブは閉じてかまいません」と出す。

ページの文言は、ブラウザの `Accept-Language` に合わせて日本語か英語で出す（どちらにも当てはまらないときは英語）。言語を足すときは `server.py` の `MESSAGES` に追加する。

- Vault のファイルは読まない。受け取ったパスを転送先に組み直すだけ
- 受け付ける vault は設定したものだけ。それ以外と `/` は 404
- パスはログに残さない
- 既定では 127.0.0.1:8765 だけで待ち受ける。外からは [Tailscale Funnel](https://tailscale.com/kb/1223/funnel) などのリバースプロキシ経由で届ける

Python 3.9 以降の標準ライブラリだけで動く。

## 設定

環境変数か、クローンの直下に置く `.env` で渡す（環境変数が優先）。

| 変数 | 使うもの | 内容 |
|---|---|---|
| `OBSIDIAN_LINK_BASE` | link.py | 出すリンクの先頭（例：`https://<host>.<tailnet>.ts.net/o`）。必須 |
| `OBSIDIAN_LINK_VAULTS` | server.py | 受け付ける vault の名前（カンマ区切り）。必須 |
| `OBSIDIAN_LINK_HOST` | server.py | 待ち受けるアドレス（既定 `127.0.0.1`） |
| `OBSIDIAN_LINK_PORT` | server.py | 待ち受けるポート（既定 `8765`） |

```bash
cp env.example .env
chmod 600 .env
# .env を編集する
```

## リンクを出す

```bash
python3 -I link.py MyVault 'Folder/Note.md'
```

## 導入（systemd のユーザーユニットと Tailscale Funnel の例）

`obsidian-app-bridge.service` の `ExecStart` のパスを、クローンの場所に合わせてから使う。

```bash
# 1. 常駐（ログアウト中も動かすなら loginctl enable-linger）
systemctl --user link "$PWD/obsidian-app-bridge.service"
systemctl --user enable --now obsidian-app-bridge.service

# 2. Funnel で公開（初回は、表示された URL で tailnet の Funnel を許可する）
sudo tailscale funnel --bg 8765

# 確認
tailscale funnel status
```

## 止める

```bash
sudo tailscale funnel --https=443 off
systemctl --user disable --now obsidian-app-bridge.service
```

## 注意

URL を知っていれば誰でも開ける。返すのは渡されたパスを組み直した転送先だけなので、ノートの中身は出ないが、Vault の名前とノートのパスは URL に含まれる。

## ライセンス

[MIT](LICENSE)
