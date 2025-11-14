# Switch2 多言語版抽選販売監視システム

Nintendo Switch2の多言語版抽選販売を監視し、新しい抽選情報があればLINE Messaging APIで通知するシステムです。

## クイックスタート

### ローカルで試す（5分で完了）

```bash
# 1. リポジトリをクローン
git clone <your-repo-url>
cd switch2

# 2. 環境設定
cp .env.example .env
# .envファイルを編集してLINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID/LINE_GROUP_IDを設定

# 3. Pythonパッケージをインストール
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 4. テスト実行
python test_local.py
```

### Cloud Functionsにデプロイ（10分で完了）

詳細な手順は [DEPLOYMENT.md](DEPLOYMENT.md) を参照してください。

```bash
# 1. Google Cloudにログイン
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. デプロイ
gcloud functions deploy switch2_monitor \
  --gen2 \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point main \
  --set-env-vars LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token,LINE_USER_ID=your_user_id,LINE_GROUP_ID=your_group_id \
  --region asia-northeast1

# 3. 1時間ごとに自動実行
gcloud scheduler jobs create http switch2_monitor_job \
  --schedule="0 * * * *" \
  --uri="https://YOUR_FUNCTION_URL" \
  --http-method=GET \
  --location asia-northeast1
```

## 機能

- 任天堂公式ストア（https://store-jp.nintendo.com/）を監視
- キーワードベースの検出（Switch2、多言語、抽選、招待販売など）
- コンテンツハッシュによる変更検出
- 前回の状態と比較し、変更があった場合のみ通知
- エラーハンドリングとリトライ機能
- 詳細なログ出力
- Google Cloud Functionsで自動実行可能

## セットアップ

### 1. LINE Messaging API の設定

#### ステップ1: LINE Developersコンソールへのアクセス

1. ブラウザで [LINE Developers Console](https://developers.line.biz/console/) にアクセス
2. LINEアカウントでログイン

#### ステップ2: プロバイダーとチャネルの作成

1. 「プロバイダーを作成」をクリック（初回のみ）
   - プロバイダー名: 任意（例: `Switch2Monitor`）
2. 作成したプロバイダーを選択
3. 「チャネルを作成」をクリック
4. 「Messaging API」を選択
5. チャネル情報を入力：
   - チャネル名: `Switch2監視システム` など
   - チャネル説明: 任意
   - カテゴリ: 適当なものを選択
   - サブカテゴリ: 適当なものを選択
6. 利用規約に同意して「作成」をクリック

#### ステップ3: チャネルアクセストークンの発行

1. 作成したチャネルを選択
2. 「Messaging API設定」タブを選択
3. 「チャネルアクセストークン（長期）」の「発行」ボタンをクリック
4. 表示されたトークンをコピーして安全に保存

⚠️ **重要**: トークンは厳重に管理してください

#### ステップ4: ユーザーID / グループIDの取得

**個人宛てに通知する場合（USER_ID）:**
1. LINEアプリで作成したBotを友だち追加
2. Botにメッセージを送信
3. Webhook経由、または[LINE Official Account Manager](https://manager.line.biz/)でユーザーIDを確認

**グループ宛てに通知する場合（GROUP_ID）:**
1. LINEグループにBotを追加
2. Webhook経由でグループIDを確認

#### ステップ5: 環境変数の設定

ローカル環境の場合:
```bash
# .envファイルに設定
echo "LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token_here" > .env
echo "LINE_USER_ID=your_user_id_here" >> .env
# またはグループの場合
echo "LINE_GROUP_ID=your_group_id_here" >> .env
```

Cloud Functionsの場合:
```bash
# デプロイ時に環境変数として設定（後述）
gcloud functions deploy ... --set-env-vars LINE_CHANNEL_ACCESS_TOKEN=your_token,LINE_USER_ID=your_user_id
```

#### 設定のテスト

```bash
# Pythonでテスト
python notifier.py
```

#### トラブルシューティング

- **チャネルアクセストークンが無効**: トークンを再発行
- **USER_ID/GROUP_IDが不明**: Webhook URLを設定してログから確認
- **メッセージが届かない**: チャネルの応答設定を確認

### 2. 環境変数の設定

```bash
cp .env.example .env
```

`.env` ファイルを編集し、LINE Messaging API情報を設定：

```
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token_here
LINE_USER_ID=your_user_id_here
# またはグループ宛ての場合
LINE_GROUP_ID=your_group_id_here
```

### 3. ローカルでのテスト

#### ステップ1: Python環境の準備

Python 3.11以上がインストールされていることを確認：
```bash
python --version
# または
python3 --version
```

#### ステップ2: 仮想環境の作成と有効化

```bash
# 仮想環境の作成
python -m venv venv

# 仮想環境の有効化
# Windows (コマンドプロンプト)
venv\Scripts\activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate
```

仮想環境が有効化されると、プロンプトの先頭に `(venv)` が表示されます。

#### ステップ3: 依存関係のインストール

```bash
# requirements.txtから一括インストール
pip install -r requirements.txt

# インストール確認
pip list
```

#### ステップ4: 統合テストスイートの実行（推奨）

```bash
# 統合テストスクリプトを実行
python test_local.py
```

このスクリプトは以下をテストします：
1. ✅ 設定の確認（環境変数、キーワードなど）
2. ✅ LINE Messaging API通知（実際に通知を送信）
3. ✅ スクレイピング（任天堂ストアのページを取得）
4. ✅ 状態管理（変更検出ロジック）
5. ✅ システム全体（実際の監視実行）

#### ステップ5: 個別コンポーネントのテスト（オプション）

特定のコンポーネントだけをテストしたい場合：

```bash
# 設定のテスト
python config.py

# スクレイピングのテスト
python scraper.py

# 通知のテスト（5種類の通知を送信）
python notifier.py

# 状態管理のテスト
python state_manager.py

# 全体のテスト（実際の監視実行）
python main.py
```

#### ステップ6: 動作確認のポイント

**正常に動作している場合:**
- ✅ LINEアプリに通知が届く
- ✅ ログに "スキャン成功" と表示される
- ✅ `switch2_state.json` ファイルが作成される
- ✅ 初回実行では「初回実行のため、通知をスキップ」と表示される
- ✅ 2回目以降は変更がない場合「変更なし」と表示される

**エラーが発生する場合:**
- ❌ `LINE_CHANNEL_ACCESS_TOKEN` が設定されていない → `.env` ファイルを確認
- ❌ ネットワークエラー → インターネット接続を確認
- ❌ スクレイピング失敗 → 任天堂ストアがアクセス可能か確認

### 4. テストモードと強制通知モード

Cloud Functionsデプロイ後、以下のクエリパラメータでテスト可能：

- `?test=true` : LINE Messaging APIの疎通確認（テスト通知を送信）
- `?force=true` : 強制通知モード（状態をリセットして通知）

## Google Cloud Functionsへのデプロイ

📖 **詳細なデプロイ手順は [DEPLOYMENT.md](DEPLOYMENT.md) を参照してください**

### 前提条件

- Google Cloudアカウント
- 課金が有効化されたGCPプロジェクト
- LINE Messaging APIトークン

### 1. Google Cloud SDKのインストール

[Google Cloud SDK](https://cloud.google.com/sdk/docs/install) をインストールします。

```bash
# インストール確認
gcloud --version
```

### 2. Google Cloudの初期設定

```bash
# Google Cloudにログイン
gcloud auth login

# プロジェクトIDを設定（YOUR_PROJECT_IDは実際のプロジェクトIDに置き換え）
gcloud config set project YOUR_PROJECT_ID

# 使用するリージョンを設定（例：東京リージョン）
gcloud config set functions/region asia-northeast1

# 必要なAPIの有効化
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 3. Cloud Functionsへのデプロイ

```bash
# プロジェクトディレクトリに移動
cd switch2

# デプロイコマンド実行（LINE_CHANNEL_ACCESS_TOKENは実際のトークンに置き換え）
gcloud functions deploy switch2_monitor \
  --gen2 \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point main \
  --memory 256MB \
  --timeout 60s \
  --set-env-vars LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token,LINE_USER_ID=your_user_id,LINE_GROUP_ID=your_group_id \
  --region asia-northeast1
```

デプロイが完了すると、関数のURLが表示されます：
```
https://asia-northeast1-YOUR_PROJECT_ID.cloudfunctions.net/switch2_monitor
```

### 4. デプロイ確認

```bash
# テスト通知の送信
curl "https://asia-northeast1-YOUR_PROJECT_ID.cloudfunctions.net/switch2_monitor?test=true"

# 正常動作確認（実際の監視実行）
curl "https://asia-northeast1-YOUR_PROJECT_ID.cloudfunctions.net/switch2_monitor"
```

### 5. Cloud Schedulerで定期実行

```bash
# App Engineアプリの初期化（Cloud Scheduler使用に必要）
gcloud app create --region=asia-northeast1

# スケジューラージョブの作成（1時間ごとに実行）
gcloud scheduler jobs create http switch2_monitor_job \
  --location asia-northeast1 \
  --schedule="0 * * * *" \
  --uri="https://asia-northeast1-YOUR_PROJECT_ID.cloudfunctions.net/switch2_monitor" \
  --http-method=GET \
  --time-zone="Asia/Tokyo" \
  --description="Switch2 lottery monitor - runs every hour"

# スケジューラーの動作確認
gcloud scheduler jobs run switch2_monitor_job --location asia-northeast1

# スケジューラーの状態確認
gcloud scheduler jobs describe switch2_monitor_job --location asia-northeast1
```

### 6. 環境変数の更新（必要に応じて）

```bash
# 環境変数の更新
gcloud functions deploy switch2_monitor \
  --gen2 \
  --update-env-vars LINE_CHANNEL_ACCESS_TOKEN=new_channel_access_token,LINE_USER_ID=new_user_id \
  --region asia-northeast1
```

### 7. ログの確認

```bash
# Cloud Functionsのログを表示
gcloud functions logs read switch2_monitor \
  --region asia-northeast1 \
  --limit 50

# リアルタイムでログを監視
gcloud functions logs read switch2_monitor \
  --region asia-northeast1 \
  --limit 10 \
  --follow
```

## トラブルシューティング

### ローカル環境のトラブルシューティング

#### エラー: `ModuleNotFoundError: No module named 'xxx'`

**原因**: 依存関係がインストールされていない

**解決方法**:
```bash
# 仮想環境が有効化されているか確認
which python  # macOS/Linux
where python  # Windows

# 依存関係を再インストール
pip install -r requirements.txt

# 特定のモジュールのみインストール
pip install requests beautifulsoup4 lxml
```

#### エラー: `ValueError: LINE_CHANNEL_ACCESS_TOKEN is not set`

**原因**: 環境変数が設定されていない

**解決方法**:
```bash
# .envファイルが存在するか確認
ls -la .env  # macOS/Linux
dir .env     # Windows

# .envファイルが存在しない場合は作成
cp .env.example .env

# .envファイルを編集してトークンを設定
# Windowsの場合
notepad .env

# macOS/Linuxの場合
nano .env
# または
vi .env
```

`.env`ファイルの内容:
```
LINE_CHANNEL_ACCESS_TOKEN=your_actual_token_here_without_quotes
```

⚠️ **注意**: トークンは引用符（`"`）で囲まない

#### エラー: `requests.exceptions.ConnectionError`

**原因**: ネットワーク接続の問題

**解決方法**:
1. インターネット接続を確認
2. プロキシ設定が必要な場合は環境変数を設定:
```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```
3. ファイアウォールで `https://store-jp.nintendo.com` と `https://api.line.me` へのアクセスが許可されているか確認

#### エラー: LINE通知が届かない

**原因1**: トークンが間違っている

**確認方法**:
```bash
# Pythonでテスト
python notifier.py
```

または、curlで直接テスト（USER_IDまたはGROUP_IDが必要）:
```bash
curl -X POST https://api.line.me/v2/bot/message/push \
  -H "Authorization: Bearer YOUR_CHANNEL_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "USER_ID_OR_GROUP_ID",
    "messages": [{"type": "text", "text": "テスト"}]
  }'
```

**原因2**: トークンに余分な文字が含まれている

**解決方法**:
- トークンの前後にスペースや改行がないか確認
- `.env`ファイルで引用符を使用していないか確認

**原因3**: LINEアプリで通知がブロックされている

**解決方法**:
1. LINEアプリを開く
2. 設定 → 通知 → LINE Messaging API
3. 通知がONになっているか確認

---

### Google Cloud Functions のトラブルシューティング

#### エラー: `gcloud: command not found`

**原因**: Google Cloud SDKがインストールされていない

**解決方法**:
1. [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) をダウンロードしてインストール
2. インストール後、ターミナルを再起動
3. 確認: `gcloud --version`

#### エラー: `ERROR: (gcloud.functions.deploy) PERMISSION_DENIED`

**原因**: 権限が不足している

**解決方法**:
```bash
# 現在のアカウントを確認
gcloud auth list

# 必要に応じて再認証
gcloud auth login

# プロジェクトの所有者/編集者権限があるか確認
gcloud projects get-iam-policy YOUR_PROJECT_ID

# Cloud Functions管理者ロールを追加（プロジェクトオーナーが実行）
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:YOUR_EMAIL" \
  --role="roles/cloudfunctions.admin"
```

#### エラー: `ERROR: (gcloud.functions.deploy) RESOURCE_EXHAUSTED: Quota exceeded`

**原因**: Cloud Functionsのクォータ（割り当て）を超過している

**解決方法**:
1. [GCP Console](https://console.cloud.google.com/) にアクセス
2. IAMと管理 → 割り当て
3. Cloud Functionsの割り当てを確認し、必要に応じて増加リクエスト
4. または既存の不要な関数を削除:
```bash
gcloud functions list
gcloud functions delete FUNCTION_NAME
```

#### エラー: `ERROR: (gcloud.functions.deploy) Build failed`

**原因**: requirements.txtの依存関係の問題

**解決方法**:
```bash
# ローカルで依存関係をテスト
pip install -r requirements.txt

# バージョン指定を緩和（requirements.txtで==を>=に変更）
# 例: requests==2.31.0 → requests>=2.31.0

# Cloud Buildのログを確認
gcloud builds list --limit=5
gcloud builds log BUILD_ID
```

#### エラー: デプロイは成功するが関数が動作しない

**原因1**: 環境変数が設定されていない

**確認方法**:
```bash
# 環境変数を確認
gcloud functions describe switch2_monitor \
  --region asia-northeast1 \
  --format="value(environmentVariables)"
```

**解決方法**:
```bash
# 環境変数を更新
gcloud functions deploy switch2_monitor \
  --gen2 \
  --update-env-vars LINE_CHANNEL_ACCESS_TOKEN=your_token \
  --region asia-northeast1
```

**原因2**: エントリーポイントが間違っている

**確認方法**:
```bash
# main.pyに@functions_framework.httpデコレータが付いたmain関数があるか確認
grep -A 5 "@functions_framework.http" main.py
```

**解決方法**: エントリーポイントを明示的に指定
```bash
gcloud functions deploy switch2_monitor \
  --entry-point main \
  ...
```

#### エラー: Cloud Schedulerが実行されない

**原因1**: App Engineアプリが初期化されていない

**確認方法**:
```bash
gcloud app describe
```

エラーが出る場合:
```bash
gcloud app create --region=asia-northeast1
```

**原因2**: スケジューラージョブが無効になっている

**確認方法**:
```bash
gcloud scheduler jobs list --location asia-northeast1
```

**解決方法**:
```bash
# ジョブを有効化
gcloud scheduler jobs resume switch2_monitor_job --location asia-northeast1

# ジョブを手動実行してテスト
gcloud scheduler jobs run switch2_monitor_job --location asia-northeast1
```

**原因3**: タイムゾーンの設定ミス

**解決方法**:
```bash
# タイムゾーンを確認・更新
gcloud scheduler jobs update http switch2_monitor_job \
  --location asia-northeast1 \
  --time-zone="Asia/Tokyo"
```

---

### 実行時のトラブルシューティング

#### 問題: 初回実行で通知が来ない

**これは正常な動作です！**

理由: システムは初回実行時にベースラインを確立するため、通知を送信しません。

確認方法:
```bash
# ログで「初回実行のため、通知をスキップ」というメッセージを確認
gcloud functions logs read switch2_monitor --region asia-northeast1
```

2回目以降の実行で変更があれば通知が送信されます。

#### 問題: 変更があるのに通知が来ない

**原因1**: 状態ファイルが更新されていない

**解決方法**: 強制通知モードで実行
```bash
curl "https://YOUR_FUNCTION_URL?force=true"
```

**原因2**: キーワードにマッチしていない

**解決方法**:
1. ログでスキャン結果を確認:
```bash
gcloud functions logs read switch2_monitor --region asia-northeast1 | grep "検出"
```

2. 必要に応じてキーワードを追加（config.py の WATCH_KEYWORDS）

#### 問題: 通知が多すぎる

**原因**: ページの動的コンテンツがキーワードにマッチしている

**解決方法**:
1. キーワードマッチモードを `all` に変更（.env）:
```
KEYWORD_MATCH_MODE=all
```

2. より具体的なキーワードに変更（config.py）

#### 問題: タイムアウトエラー

**原因**: 処理時間が制限（60秒）を超過

**解決方法**:
```bash
# タイムアウトを延長（最大540秒）
gcloud functions deploy switch2_monitor \
  --gen2 \
  --timeout 120s \
  --region asia-northeast1
```

---

### よくある質問（FAQ）

**Q: 状態ファイルはどこに保存されますか？**

A:
- ローカル: プロジェクトディレクトリの `switch2_state.json`
- Cloud Functions: 関数の一時ストレージ（永続化されない）

Cloud Functionsで永続化したい場合は、Cloud Storageを使用してください（config.pyで設定可能）。

**Q: 監視頻度はどのくらいが適切ですか？**

A:
- 推奨: 1時間ごと（`0 * * * *`）
- 最小: 15分ごと（ただしAPI制限に注意）
- 注意: あまり頻繁だとサイトに負荷をかける可能性があります

**Q: 複数のキーワードを監視できますか？**

A: はい、`config.py`の`WATCH_KEYWORDS`リストに追加してください。

**Q: 費用はどのくらいかかりますか？**

A:
- Cloud Functions: 月間200万リクエストまで無料
- 1時間ごと実行: 約720回/月（無料枠内）
- Cloud Scheduler: 月3ジョブまで無料
- 合計: **ほぼ無料**（無料枠内で運用可能）

**Q: テストモードと強制通知モードの違いは？**

A:
- テストモード（`?test=true`）: LINE Messaging API連携のテスト通知のみ送信（スクレイピングなし）
- 強制通知モード（`?force=true`）: 状態をリセットして実際にスクレイピング＆通知を送信

## ファイル構成

```
switch2/
├── main.py              # Cloud Functions エントリーポイント
├── scraper.py           # スクレイピングロジック（任天堂ストア最適化）
├── notifier.py          # LINE Messaging API通知ロジック
├── state_manager.py     # 状態管理（変更検出）
├── config.py            # 設定ファイル
├── test_local.py        # ローカルテストスイート
├── requirements.txt     # Python依存関係
├── .env.example         # 環境変数サンプル
├── .gitignore           # Git除外設定
├── .gcloudignore        # Cloud Functions デプロイ除外設定
├── README.md            # このファイル（プロジェクト概要）
├── DEPLOYMENT.md        # デプロイ手順書
└── CLAUDE.md            # 開発者向けガイド（Claude Code用）
```

## 実装の詳細

### スクレイピング (scraper.py)

任天堂公式ストアのHTML構造に最適化：

- **キーワード検出**: 設定されたキーワード（Switch2、多言語、抽選など）を含むコンテンツを検出
- **複数の要素タイプに対応**:
  - 見出し（h1-h6）
  - リンク（a要素）
  - バナー・通知エリア
  - 段落・div要素
- **リトライ機能**: 最大3回までリトライ
- **ハッシュ値計算**: コンテンツの変更検出用

### 状態管理 (state_manager.py)

前回の状態と比較して変更を検出：

- **JSONファイルで状態を保存**: ローカルまたはCloud Storage
- **ハッシュ値による変更検出**: コンテンツが変更されたかを正確に判定
- **新規アイテムの抽出**: 前回から追加されたアイテムのみを通知
- **初回実行の特別処理**: 初回は通知をスキップ

### 通知 (notifier.py)

LINE Messaging APIで通知を送信：

#### 主要機能

1. **新情報検出通知** (`send_lottery_notification_v2`)
   - タイプ別グループ化（見出し、バナー、リンク、段落）
   - 絵文字による視覚的な区別
   - タイトル、概要、URLを整形表示
   - 検出時刻と総数を表示
   - 各タイプ最大3件まで表示（見やすさ重視）

2. **テスト通知** (`send_test_notification`)
   - システム動作確認用
   - LINE Messaging API連携の疎通確認

3. **エラー通知** (`send_error_notification`)
   - エラー内容の整形表示
   - 発生時刻の記録
   - 確認項目のリスト表示

4. **ステータス通知** (`send_status_notification`)
   - success, info, warning, error の4種類
   - ステータスに応じた絵文字表示

#### 通知フォーマットの特徴

```
━━━━━━━━━━━━━━━━━━
🎮 Switch2 新情報検出！
━━━━━━━━━━━━━━━━━━

📌 重要見出し
────────────────────

💡 「Nintendo Switch 2（多言語対応）」招待販売について
   申込期限: 11月18日（火）午前11:00
   🔗 ...nintendo.com/switch2

📢 バナー情報
────────────────────

🔔 Switch2 抽選販売 受付中
   詳細はこちら
   🔗 ...nintendo.com/lottery/switch2

━━━━━━━━━━━━━━━━━━
検出時刻: 2025-11-14 10:00
検出総数: 5件
━━━━━━━━━━━━━━━━━━
```

#### 文字数制限

- LINE Messaging APIは5000文字まで
- 超過する場合は自動的に切り詰め

## 注意事項

- スクレイピングは対象サイトの利用規約を確認してください
- リクエスト頻度は適切に設定してください（サーバーに負荷をかけないよう）
- LINE Messaging APIトークンは厳重に管理してください

## ライセンス

MIT
