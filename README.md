# Switch2 多言語版抽選販売監視システム

Nintendo Switch2 の **多言語版 抽選 / 招待販売** を監視し、
新しい情報が見つかったときに **LINE Messaging API** で通知するシステムです。

---

## 機能

* 任天堂公式ストア（[https://store-jp.nintendo.com/）を定期的に監視](https://store-jp.nintendo.com/）を定期的に監視)
* キーワードベースの検出（例: `Switch2`, `多言語`, `抽選`, `招待販売` など）
* コンテンツハッシュによる変更検出（前回との差分のみ通知）
* 初回実行時は通知をスキップしてベースラインを作成
* エラーハンドリング・リトライ・詳細ログ出力
* Google Cloud Functions + Cloud Scheduler による自動実行

---

## ファイル構成

```text
switch2/
├── main.py              # Cloud Functions エントリーポイント
├── scraper.py           # スクレイピングロジック（任天堂ストア用）
├── notifier.py          # LINE Messaging API 通知ロジック
├── state_manager.py     # 状態管理（変更検出・永続化）
├── config.py            # 設定ファイル（キーワード等）
├── test_local.py        # ローカル統合テスト
├── requirements.txt     # Python 依存関係
├── .env.example         # 環境変数サンプル
├── .gitignore           # Git 除外設定
├── .gcloudignore        # Cloud Functions デプロイ除外設定
├── README.md            # このファイル
├── DEPLOYMENT.md        # デプロイ詳細手順書
└── CLAUDE.md            # 開発者向けガイド（Claude Code 用）
```

---

## クイックスタート（ローカルで試す）

> ※ まずローカルで一度動作確認し、その後 Cloud Functions へデプロイするのがおすすめです。

```bash
# 1. リポジトリをクローン
git clone <your-repo-url>
cd switch2

# 2. .env を作成
cp .env.example .env
# エディタで .env を開き、LINE_CHANNEL_ACCESS_TOKEN と
# LINE_USER_ID または LINE_GROUP_ID を設定

# 3. Python 仮想環境の作成 & 有効化
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

# 4. 依存関係のインストール
pip install -r requirements.txt

# 5. 統合テストを実行（実際に LINE に通知されます）
python test_local.py
```

* LINE に通知が届き、ログにエラーが出ていなければローカルセットアップ完了です。
* 本番運用は後述の「Google Cloud Functions へのデプロイ」を参照してください。

---

## セットアップ

### 1. LINE Messaging API の準備

#### ステップ1: LINE Developers コンソールへアクセス

1. ブラウザで [LINE Developers Console](https://developers.line.biz/console/) を開く
2. 使用する LINE アカウントでログイン

#### ステップ2: プロバイダー・チャネルの作成

1. 「**プロバイダーを作成**」をクリック（初回のみ）

   * プロバイダー名: 任意（例: `Switch2Monitor`）
2. 作成したプロバイダーを選択
3. 「**チャネルを作成**」→「**Messaging API**」を選択
4. チャネル情報を入力

   * チャネル名: `Switch2監視システム` など
   * チャネル説明 / カテゴリ / サブカテゴリ: 任意
5. 利用規約に同意して作成

#### ステップ3: チャネルアクセストークンの発行

1. 作成したチャネルを選択
2. 「**Messaging API 設定**」タブを開く
3. 「チャネルアクセストークン（長期）」で **「発行」** ボタンをクリック
4. 表示されたトークンをコピーして安全に保存

> ⚠️ **重要**
> チャネルアクセストークンは Git にコミットしないでください。`.env` などにのみ保存します。

---

### 2. ユーザー ID / グループ ID の取得

このシステムでは、通知先として **ユーザー単体** もしくは **グループ** を指定します。

#### 個人宛てに通知する場合（LINE_USER_ID）

1. 作成した Bot の QR コード等から、自分の LINE に Bot を友だち追加
2. Bot に適当なメッセージを送る（「テスト」など）
3. Webhook（後述）で受け取ったイベントの `event.source.userId` をログに出力するようにし、その値を控える

#### グループ宛てに通知する場合（LINE_GROUP_ID）

1. 通知したいグループに Bot を招待する
2. グループ内で Bot にメンションするかメッセージを送る
3. Webhook イベントの `event.source.groupId` をログに出力し、その値を使用する

> ※ 本 README のサンプルコードは **Webhook ハンドラの実装** を前提にしていませんが、
> ユーザー / グループ ID の取得時に一時的に Webhook を有効にすることを想定しています。

---

### 3. 環境変数の設定

#### ローカル（.env）

`.env.example` をコピーして `.env` を作成し、以下を設定します。

```env
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token_here
LINE_USER_ID=your_user_id_here
# グループ宛てに通知する場合は USER_ID の代わりに以下を使用
# LINE_GROUP_ID=your_group_id_here
```

* `LINE_USER_ID` と `LINE_GROUP_ID` は **どちらか片方だけ** を設定してください。
* トークンは **引用符で囲まない**（例: `LINE_CHANNEL_ACCESS_TOKEN="xxx"` は NG）。

#### Google Cloud Functions（環境変数）

Cloud Functions へデプロイする際に、`--set-env-vars` または `--update-env-vars` で同じキーを指定します。

```bash
gcloud functions deploy switch2_monitor \
  --gen2 \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point main \
  --region asia-northeast1 \
  --set-env-vars \
    LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token,\
    LINE_USER_ID=your_user_id,\
    LINE_GROUP_ID=your_group_id
```

---

## ローカルでのテスト（詳細）

### ステップ1: Python 環境の確認

```bash
python --version   # 3.11 以上推奨
# or
python3 --version
```

### ステップ2: 仮想環境の作成・有効化

```bash
python -m venv venv

# Windows (コマンドプロンプト)
venv\Scripts\activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1

# macOS / Linux
source venv/bin/activate
```

### ステップ3: 依存関係のインストール

```bash
pip install -r requirements.txt
pip list  # 必要に応じて確認
```

### ステップ4: 統合テストスイートの実行（推奨）

```bash
python test_local.py
```

このスクリプトでは、主に以下をテストします：

1. 設定の確認（環境変数、キーワードなど）
2. LINE Messaging API 通知（実際に通知を送信）
3. 任天堂ストアのスクレイピング
4. 状態管理（変更検出ロジック）
5. 監視処理全体

### ステップ5: 個別コンポーネントのテスト（任意）

```bash
# 設定
python config.py

# スクレイピングのみ
python scraper.py

# 通知のみ（数種類のメッセージを送信）
python notifier.py

# 状態管理
python state_manager.py

# 本番に近い動作
python main.py
```

### ステップ6: 正常動作チェック

**正常な場合**

* LINE アプリに通知が届く
* ログに「スキャン成功」等のメッセージ
* `switch2_state.json` が作成されている
* 初回実行では「初回実行のため、通知をスキップ」と表示
* 2回目以降、変更がない場合は「変更なし」と表示

**よくある原因**

* `.env` にトークンが入っていない
* ネットワークエラー
* 任天堂ストアへのアクセス制限 など

---

## Cloud Functions 用テストモード

Cloud Functions にデプロイ後、HTTP クエリパラメータで動作モードを切り替えられます。

* `?test=true`

  * LINE Messaging API 連携の疎通テスト
  * スクレイピングは行わず、テストメッセージのみ送信
* `?force=true`

  * 状態をリセットして監視 + 通知を強制実行
  * 「通知が来ないときに一度リセットしたい」場合に使用

例：

```bash
curl "https://YOUR_FUNCTION_URL?test=true"
curl "https://YOUR_FUNCTION_URL?force=true"
```

---

## Google Cloud Functions へのデプロイ

> さらに細かい説明は `DEPLOYMENT.md` にまとまっています。
> ここでは README 用に、よく使うコマンドだけを整理しています。

### 前提条件

* Google Cloud アカウント
* 課金が有効な GCP プロジェクト
* `gcloud`（Google Cloud SDK）がインストール済み
* LINE Messaging API のチャネルアクセストークン

### 1. Google Cloud SDK のインストール確認

```bash
gcloud --version
```

インストールされていなければ、公式のドキュメントからセットアップしてください。

### 2. プロジェクト・リージョンの設定と API 有効化

```bash
# 認証
gcloud auth login

# プロジェクト設定
gcloud config set project YOUR_PROJECT_ID

# Functions デフォルトリージョン（例: 東京）
gcloud config set functions/region asia-northeast1

# 必要な API を有効化
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 3. Cloud Functions へのデプロイ

```bash
cd switch2

gcloud functions deploy switch2_monitor \
  --gen2 \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point main \
  --memory 256MB \
  --timeout 60s \
  --region asia-northeast1 \
  --set-env-vars \
    LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token,\
    LINE_USER_ID=your_user_id,\
    LINE_GROUP_ID=your_group_id
```

デプロイ後、関数の URL が表示されます：

```text
https://asia-northeast1-YOUR_PROJECT_ID.cloudfunctions.net/switch2_monitor
```

### 4. デプロイ後の動作確認

```bash
# テスト通知（疎通確認）
curl "https://asia-northeast1-YOUR_PROJECT_ID.cloudfunctions.net/switch2_monitor?test=true"

# 実際の監視実行
curl "https://asia-northeast1-YOUR_PROJECT_ID.cloudfunctions.net/switch2_monitor"
```

### 5. Cloud Scheduler で定期実行

```bash
# App Engine アプリ作成（Cloud Scheduler 利用に必要）
gcloud app create --region=asia-northeast1

# 1時間ごとに実行するジョブを作成
gcloud scheduler jobs create http switch2_monitor_job \
  --location asia-northeast1 \
  --schedule="0 * * * *" \
  --uri="https://asia-northeast1-YOUR_PROJECT_ID.cloudfunctions.net/switch2_monitor" \
  --http-method=GET \
  --time-zone="Asia/Tokyo" \
  --description="Switch2 lottery monitor - runs every hour"

# 動作確認（手動実行）
gcloud scheduler jobs run switch2_monitor_job --location asia-northeast1
```

### 6. 環境変数の更新

```bash
gcloud functions deploy switch2_monitor \
  --gen2 \
  --region asia-northeast1 \
  --update-env-vars \
    LINE_CHANNEL_ACCESS_TOKEN=new_channel_access_token,\
    LINE_USER_ID=new_user_id
```

### 7. ログの確認

```bash
# 直近ログ
gcloud functions logs read switch2_monitor \
  --region asia-northeast1 \
  --limit 50

# リアルタイム監視
gcloud functions logs read switch2_monitor \
  --region asia-northeast1 \
  --limit 10 \
  --follow
```

---

## トラブルシューティング

### ローカル開発

#### `ModuleNotFoundError: No module named 'xxx'`

**原因**: 依存ライブラリが未インストール

**対処:**

```bash
# 仮想環境が有効化されているか確認
which python   # macOS / Linux
where python   # Windows

# 依存関係を再インストール
pip install -r requirements.txt

# 個別に入れる場合
pip install requests beautifulsoup4 lxml
```

---

#### `ValueError: LINE_CHANNEL_ACCESS_TOKEN is not set`

**原因**: `.env` にトークンが入っていない / 読み込めていない

**対処:**

```bash
# .env の存在確認
ls -la .env  # macOS / Linux
dir .env     # Windows

# 無ければコピー
cp .env.example .env
```

`.env` をエディタで開き、以下のように設定します。

```env
LINE_CHANNEL_ACCESS_TOKEN=your_actual_token_here_without_quotes
```

> ⚠️ トークンの前後にスペース・引用符を付けないよう注意してください。

---

#### `requests.exceptions.ConnectionError`

**原因**: ネットワーク障害 / プロキシ / ファイアウォール

**対処:**

1. 通常のブラウザで `https://store-jp.nintendo.com` にアクセスできるか確認
2. 必要ならプロキシ環境変数を設定

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

3. `https://api.line.me` への通信がブロックされていないか確認

---

#### LINE 通知が届かない

**主な原因**

1. チャネルアクセストークンの誤り
2. USER_ID / GROUP_ID の誤り
3. LINE 側の通知設定（ミュート・ブロック）

**追加確認用:** `curl` で直接叩く

```bash
curl -X POST https://api.line.me/v2/bot/message/push \
  -H "Authorization: Bearer YOUR_CHANNEL_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "USER_ID_OR_GROUP_ID",
    "messages": [{"type": "text", "text": "テスト"}]
  }'
```

---

### Google Cloud Functions

#### `gcloud: command not found`

→ Cloud SDK 未インストール。公式手順に従ってインストール後、ターミナルを再起動してください。

#### `ERROR: (gcloud.functions.deploy) PERMISSION_DENIED`

* `gcloud auth list` でアカウント確認
* プロジェクトの IAM で、Cloud Functions 管理権限があるか確認
* 必要に応じて `roles/cloudfunctions.admin` などを付与

#### `ERROR: (gcloud.functions.deploy) RESOURCE_EXHAUSTED: Quota exceeded`

* GCP コンソールの「割り当て」で Cloud Functions のクォータを確認
* 不要な関数の削除
* あるいはクォータ増加を申請

#### ビルドエラー（Build failed）

* ローカルで `pip install -r requirements.txt` を試してバージョンを調整
* `==` を `>=` に緩めるなどして依存ライブラリの制約を調整
* `gcloud builds` のログで詳細を確認

---

### 実行時の挙動に関する FAQ

#### Q. 初回実行で通知が来ません

**A. 正常です。**

初回実行は「ベースライン」作成のため、通知を送らずに状態だけ保存します。
2回目以降、変更があれば通知されます。

---

#### Q. 変更があるはずなのに通知が来ません

* `switch2_state.json` が壊れている / 古い可能性 → `?force=true` で一度状態リセット
* キーワードマッチ条件が厳しすぎる可能性 → `config.py` の `WATCH_KEYWORDS` を確認

```bash
curl "https://YOUR_FUNCTION_URL?force=true"
```

---

#### Q. 通知が多すぎます

* ページの動的な変化（日時・ランキングなど）で頻繁にハッシュが変わっている可能性
* `KEYWORD_MATCH_MODE=all` にする、キーワードを絞るなどで改善可能

---

#### Q. 実行時間のタイムアウトが発生します

Cloud Functions の `timeout` を延長します（例: 120 秒）。

```bash
gcloud functions deploy switch2_monitor \
  --gen2 \
  --timeout 120s \
  --region asia-northeast1
```

---

## 実装の概要

### スクレイピング（`scraper.py`）

* 任天堂ストアの HTML から、キーワードにマッチするテキスト・リンク・見出しなどを抽出
* 最大 3 回までリトライする堅牢な取得処理
* 抽出結果からハッシュ値を算出し、前回との差分判定に使用

### 状態管理（`state_manager.py`）

* ローカルでは `switch2_state.json` に状態を保存
* Cloud Functions 利用時は、必要に応じて Cloud Storage に永続化する設計
* 初回実行時は通知せず、2回目以降に差分があれば通知

### 通知（`notifier.py`）

* 新情報通知（Switch2 抽選情報など）
* テスト通知
* エラー通知
* ステータス通知（`success`, `info`, `warning`, `error`）

通知メッセージは、見出し / バナー / リンクなどをグルーピングし、
絵文字や区切り線で視認性を高めています。
LINE の 5000 文字制限を超えないように自動で切り詰めも行います。

---

## 注意事項

* 対象サイトの利用規約に従い、過度な高頻度アクセスは避けてください
* トークン類（LINE_CHANNEL_ACCESS_TOKEN など）は必ず秘匿し、Git にコミットしないでください
* 本リポジトリは学習・個人利用を想定しています。商用利用時は自己責任でお願いします

---

## ライセンス

MIT
