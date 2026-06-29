#!/usr/bin/env bash
#
# deploy.sh - mashiro をリポジトリのクローンから docker compose 起動まで自動化する
#
# 配置場所:
#   このスクリプトは「mashiro デプロイ用ディレクトリ」に置く想定。
#   同じディレクトリ内に以下が存在することを前提とする:
#     - .env          (必須: Bot トークン等の環境変数)
#     - assets/       (必須: 自撮り画像・ボイス等 -> コンテナ内 /bot/data/assets に read-only マウント)
#     - .netrc        (任意: /dl 用の認証情報)
#     - cookies.txt   (任意: YouTube のログイン済み Cookie)
#     - saves/        (永続化したい保存データ -> コンテナ内 /bot/data/saves にマウント)
#
# 動作:
#   1. リポジトリを ./app にクローン (既にあれば最新へ更新)
#   2. 上記の外部ファイルをクローンへ注入
#   3. saves/ を永続ボリュームとしてマウントする override を生成
#   4. docker compose up -d --build で起動
#
set -euo pipefail

REPO_URL="https://github.com/mimaraka/mashiro.git"
BRANCH="main"
APP_DIRNAME="app"

# このスクリプトが置かれているディレクトリ (シンボリックリンクも解決)
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
APP_DIR="$SCRIPT_DIR/$APP_DIRNAME"

log()  { printf '\033[1;34m[deploy]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[deploy] 警告:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[deploy] エラー:\033[0m %s\n' "$*" >&2; exit 1; }

################################################################################
# 1. 前提条件のチェック
################################################################################

command -v git >/dev/null 2>&1 || die "git がインストールされていません。"
command -v docker >/dev/null 2>&1 || die "docker がインストールされていません。"

# docker compose (v2) / docker-compose (v1) を検出
if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
else
    die "docker compose / docker-compose が見つかりません。"
fi

# 必須ファイルの確認
[ -f "$SCRIPT_DIR/.env" ]   || die ".env が $SCRIPT_DIR に存在しません。"
[ -d "$SCRIPT_DIR/assets" ] || die "assets/ が $SCRIPT_DIR に存在しません。"

# 任意ファイルの確認 (無ければ警告のみ)
[ -f "$SCRIPT_DIR/.netrc" ]      || warn ".netrc が見つかりません (/dl の認証なしで続行)。"
[ -f "$SCRIPT_DIR/cookies.txt" ] || warn "cookies.txt が見つかりません (Cookie なしで続行)。"

# saves/ ディレクトリは永続マウント先。無ければ作成する。
if [ ! -d "$SCRIPT_DIR/saves" ]; then
    warn "saves/ が見つからないため新規作成します。"
    mkdir -p "$SCRIPT_DIR/saves"
fi

################################################################################
# 2. リポジトリのクローン / 更新
################################################################################

if [ -d "$APP_DIR/.git" ]; then
    log "既存のクローンを更新します ($BRANCH)..."
    git -C "$APP_DIR" fetch --prune origin
    git -C "$APP_DIR" checkout "$BRANCH"
    git -C "$APP_DIR" reset --hard "origin/$BRANCH"
elif [ -e "$APP_DIR" ]; then
    die "$APP_DIR が存在しますが git リポジトリではありません。手動で削除してください。"
else
    log "リポジトリをクローンします -> $APP_DIR"
    git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

################################################################################
# 3. 外部ファイルをクローンへ注入
################################################################################

log "設定ファイルをクローンへ反映します..."

# .env: docker compose の env_file が参照 (クローン直下に必要)
cp -f "$SCRIPT_DIR/.env" "$APP_DIR/.env"

# .netrc: ビルド時に /bot/.netrc としてイメージへ取り込まれる
if [ -f "$SCRIPT_DIR/.netrc" ]; then
    cp -f "$SCRIPT_DIR/.netrc" "$APP_DIR/.netrc"
fi

# cookies.txt: docker-compose.yml が ./cookies.txt をマウントする
if [ -f "$SCRIPT_DIR/cookies.txt" ]; then
    cp -f "$SCRIPT_DIR/cookies.txt" "$APP_DIR/cookies.txt"
else
    # base の docker-compose.yml は ./cookies.txt を read-only マウントする。
    # 実体が無いと docker が空ディレクトリを作ってしまうため、空ファイルを用意する。
    : > "$APP_DIR/cookies.txt"
fi

# saves/ を永続ボリューム、assets/ を read-only でマウントする override を生成。
# (base の docker-compose.yml はリポジトリ汎用なのでホスト固有パスを書かない。
#  assets はリポジトリに含めず外部化しているため、ここでホストからマウントする)
log "saves/ ・ assets/ のマウント設定を生成します..."
cat > "$APP_DIR/docker-compose.override.yml" <<YAML
services:
  mashiro:
    volumes:
      - $SCRIPT_DIR/saves:/bot/data/saves
      - $SCRIPT_DIR/assets:/bot/data/assets:ro
YAML

################################################################################
# 4. docker compose で起動
################################################################################

log "docker compose で起動します (ビルド込み)..."
( cd "$APP_DIR" && "${COMPOSE[@]}" up -d --build )

log "起動しました。状態:"
( cd "$APP_DIR" && "${COMPOSE[@]}" ps )

cat <<EOF

完了しました。
  ログ表示:   cd "$APP_DIR" && ${COMPOSE[*]} logs -f
  停止:       cd "$APP_DIR" && ${COMPOSE[*]} down
  再デプロイ: "$SCRIPT_DIR/$(basename "$0")"
EOF
