# Google Cloud Functions デプロイ手順書

Switch2監視システムをGoogle Cloud Functionsにデプロイするための詳細手順です。

## 目次

1. [前提条件](#前提条件)
2. [Google Cloud プロジェクトの準備](#google-cloud-プロジェクトの準備)
3. [ローカル環境でのテスト](#ローカル環境でのテスト)
4. [Cloud Functionsへのデプロイ](#cloud-functionsへのデプロイ)
5. [Cloud Schedulerの設定](#cloud-schedulerの設定)
6. [動作確認](#動作確認)
7. [メンテナンス](#メンテナンス)

---

## 前提条件

### 必要なもの

- ✅ Googleアカウント
- ✅ クレジットカード（GCP課金設定用、無料枠内で運用可能）
- ✅ LINE Messaging API チャネルアクセストークン（取得方法はREADME.md参照）
- ✅ LINE ユーザーID または グループID
- ✅ Python 3.11以上（ローカルテスト用）

### 推定コスト

**月間コスト: ほぼ$0（無料枠内）**

- Cloud Functions: 200万リクエスト/月まで無料
- Cloud Scheduler: 3ジョブ/月まで無料
- 1時間ごと実行: 約720回/月（十分に無料枠内）

---

## Google Cloud プロジェクトの準備

### ステップ1: GCPプロジェクトの作成

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 右上の「プロジェクトを選択」→「新しいプロジェクト」
3. プロジェクト名を入力（例: `switch2-monitor`）
4. 「作成」をクリック
5. プロジェクトIDをメモ（例: `switch2-monitor-123456`）

### ステップ2: 課金の有効化

1. [課金](https://console.cloud.google.com/billing) ページにアクセス
2. 「課金アカウントをリンク」をクリック
3. クレジットカード情報を入力
4. ⚠️ **注意**: 無料枠を超えない限り請求されません

### ステップ3: Google Cloud SDKのインストール

#### Windows

1. [Google Cloud SDK インストーラー](https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe) をダウンロード
2. インストーラーを実行
3. デフォルト設定で「次へ」を進める
4. 「Google Cloud SDKシェルを起動」にチェックを入れて完了
5. コマンドプロンプトまたはPowerShellを開き直す

#### macOS

```bash
# Homebrewを使用
brew install --cask google-cloud-sdk

# または公式インストーラー
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

#### Linux

```bash
# Debian/Ubuntu
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install google-cloud-sdk

# Red Hat/CentOS
sudo tee -a /etc/yum.repos.d/google-cloud-sdk.repo << EOM
[google-cloud-sdk]
name=Google Cloud SDK
baseurl=https://packages.cloud.google.com/yum/repos/cloud-sdk-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg
       https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
EOM
sudo yum install google-cloud-sdk
```

#### インストール確認

```bash
gcloud --version
# 出力例:
# Google Cloud SDK 456.0.0
# bq 2.0.101
# core 2024.01.12
# gcloud-crc32c 1.0.0
# gsutil 5.27
```

---

## ローカル環境でのテスト

### ステップ1: プロジェクトのセットアップ

```bash
# プロジェクトディレクトリに移動
cd switch2

# 仮想環境の作成
python -m venv venv

# 仮想環境の有効化
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt
```

### ステップ2: 環境変数の設定

```bash
# .envファイルの作成
cp .env.example .env

# .envファイルを編集（お好みのエディタで）
notepad .env        # Windows
nano .env           # macOS/Linux
```

`.env`ファイルの内容:
```
# LINE Messaging API設定
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token_here

# 送信先の指定（個人宛て or グループ宛て）
# 個人宛ての場合: LINE_USER_IDを設定
# グループ宛ての場合: LINE_GROUP_IDを設定（優先）
LINE_USER_ID=your_user_id_here
LINE_GROUP_ID=

# 監視対象URL
TARGET_URL=https://store-jp.nintendo.com/

# キーワードマッチモード
KEYWORD_MATCH_MODE=any

# 状態管理設定
STATE_FILE=switch2_state.json

# ログレベル
LOG_LEVEL=INFO
```

### ステップ3: ローカルテストの実行

```bash
# 統合テストスイートを実行
python test_local.py
```

テスト項目:
1. ✅ 設定の確認
2. ✅ LINE Messaging API通知テスト（実際に通知が届く）
3. ✅ Webスクレイピング
4. ✅ 状態管理
5. ✅ システム全体テスト

**すべてのテストが成功したらデプロイ準備完了です！**

---

## Cloud Functionsへのデプロイ

### ステップ1: gcloud CLIの初期化

```bash
# Google Cloudにログイン（ブラウザが開く）
gcloud auth login

# プロジェクトを設定
gcloud config set project YOUR_PROJECT_ID

# リージョンを設定（東京リージョン推奨）
gcloud config set functions/region asia-northeast1

# 現在の設定を確認
gcloud config list
```

### ステップ2: 必要なAPIの有効化

```bash
# Cloud Functions API
gcloud services enable cloudfunctions.googleapis.com

# Cloud Build API（デプロイに必要）
gcloud services enable cloudbuild.googleapis.com

# Cloud Scheduler API（定期実行に必要）
gcloud services enable cloudscheduler.googleapis.com

# 有効化されたAPIの確認
gcloud services list --enabled
```

### ステップ3: Cloud Functionsへのデプロイ

```bash
# プロジェクトディレクトリに移動
cd switch2

# デプロイコマンド実行
gcloud functions deploy switch2_monitor \
  --gen2 \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point main \
  --memory 256MB \
  --timeout 60s \
  --set-env-vars LINE_CHANNEL_ACCESS_TOKEN=YOUR_CHANNEL_ACCESS_TOKEN,LINE_USER_ID=YOUR_USER_ID \
  --region asia-northeast1

# グループに通知する場合は以下を使用
gcloud functions deploy switch2_monitor \
  --gen2 \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point main \
  --memory 256MB \
  --timeout 60s \
  --set-env-vars LINE_CHANNEL_ACCESS_TOKEN=YOUR_CHANNEL_ACCESS_TOKEN,LINE_GROUP_ID=YOUR_GROUP_ID \
  --region asia-northeast1
```

⚠️ **重要**: 以下を実際の値に置き換えてください
- `YOUR_CHANNEL_ACCESS_TOKEN`: LINE Messaging APIのチャネルアクセストークン
- `YOUR_USER_ID`: LINEユーザーID（個人宛ての場合）
- `YOUR_GROUP_ID`: LINEグループID（グループ宛ての場合）

#### デプロイパラメータの説明

- `--gen2`: 第2世代のCloud Functionsを使用（推奨）
- `--runtime python311`: Python 3.11ランタイム
- `--trigger-http`: HTTP経由でトリガー
- `--allow-unauthenticated`: 認証なしでアクセス可能（Scheduler用）
- `--entry-point main`: main.pyのmain関数をエントリーポイントに指定
- `--memory 256MB`: メモリ割り当て（最小限で十分）
- `--timeout 60s`: タイムアウト時間
- `--set-env-vars`: 環境変数の設定
- `--region asia-northeast1`: 東京リージョン

#### デプロイの出力例

```
Deploying function (may take a while - up to 2 minutes)...
⠹ Building...
✓ Function deployed.
Function URL: https://asia-northeast1-YOUR_PROJECT_ID.cloudfunctions.net/switch2_monitor
```

**この関数URLをメモしてください！**

---

## Cloud Schedulerの設定

### ステップ1: App Engineアプリの初期化

Cloud Schedulerを使用するには、App Engineアプリの初期化が必要です。

```bash
# App Engineアプリを作成（初回のみ）
gcloud app create --region=asia-northeast1
```

既に作成済みの場合はスキップされます。

### ステップ2: スケジューラージョブの作成

```bash
# 1時間ごとに実行するジョブを作成
gcloud scheduler jobs create http switch2_monitor_job \
  --location asia-northeast1 \
  --schedule="0 * * * *" \
  --uri="https://asia-northeast1-YOUR_PROJECT_ID.cloudfunctions.net/switch2_monitor" \
  --http-method=GET \
  --time-zone="Asia/Tokyo" \
  --description="Switch2 lottery monitor - runs hourly"
```

⚠️ **重要**: `YOUR_PROJECT_ID`を実際のプロジェクトIDに置き換えてください

#### スケジュール設定の例

| スケジュール | Cron式 | 説明 |
|------------|--------|------|
| 1時間ごと | `0 * * * *` | 毎時0分に実行 |
| 30分ごと | `*/30 * * * *` | 30分間隔で実行 |
| 2時間ごと | `0 */2 * * *` | 2時間ごとに実行 |
| 毎日9時 | `0 9 * * *` | 毎日午前9時に実行 |
| 平日9時 | `0 9 * * 1-5` | 平日の午前9時に実行 |

### ステップ3: スケジューラーの動作確認

```bash
# ジョブの一覧を確認
gcloud scheduler jobs list --location asia-northeast1

# ジョブを手動実行してテスト
gcloud scheduler jobs run switch2_monitor_job --location asia-northeast1

# 実行履歴の確認
gcloud scheduler jobs describe switch2_monitor_job --location asia-northeast1
```

---

## 動作確認

### 1. テスト通知の送信

```bash
# テストモードで実行（スクレイピングなし、テスト通知のみ）
curl "https://asia-northeast1-YOUR_PROJECT_ID.cloudfunctions.net/switch2_monitor?test=true"
```

LINEアプリで通知を確認してください。

### 2. 実際の監視実行

```bash
# 通常モードで実行（実際のスクレイピング＆通知）
curl "https://asia-northeast1-YOUR_PROJECT_ID.cloudfunctions.net/switch2_monitor"
```

**初回実行時は通知が送信されません**（ベースライン確立のため）。

### 3. ログの確認

```bash
# 最新のログを表示
gcloud functions logs read switch2_monitor \
  --region asia-northeast1 \
  --limit 50

# リアルタイムでログを監視
gcloud functions logs read switch2_monitor \
  --region asia-northeast1 \
  --follow
```

### 4. 強制通知モードでテスト

```bash
# 状態をリセットして通知を強制送信
curl "https://asia-northeast1-YOUR_PROJECT_ID.cloudfunctions.net/switch2_monitor?force=true"
```

このモードでは、検出された内容が必ず通知されます。

---

## メンテナンス

### 環境変数の更新

LINE Messaging APIトークンやユーザーIDを変更した場合：

```bash
# チャネルアクセストークンの更新
gcloud functions deploy switch2_monitor \
  --gen2 \
  --update-env-vars LINE_CHANNEL_ACCESS_TOKEN=NEW_TOKEN_HERE \
  --region asia-northeast1

# ユーザーIDの更新
gcloud functions deploy switch2_monitor \
  --gen2 \
  --update-env-vars LINE_USER_ID=NEW_USER_ID \
  --region asia-northeast1

# グループIDの更新
gcloud functions deploy switch2_monitor \
  --gen2 \
  --update-env-vars LINE_GROUP_ID=NEW_GROUP_ID \
  --region asia-northeast1

# 複数の環境変数を同時に更新
gcloud functions deploy switch2_monitor \
  --gen2 \
  --update-env-vars LINE_CHANNEL_ACCESS_TOKEN=NEW_TOKEN,LINE_USER_ID=NEW_USER_ID \
  --region asia-northeast1
```

### コードの更新

ローカルでコードを変更した後：

```bash
# プロジェクトディレクトリで再デプロイ
gcloud functions deploy switch2_monitor \
  --gen2 \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point main \
  --memory 256MB \
  --timeout 60s \
  --region asia-northeast1
```

⚠️ **注意**: 環境変数は再度設定する必要はありません（既存の値が保持されます）

### スケジュールの変更

```bash
# スケジュールを30分ごとに変更
gcloud scheduler jobs update http switch2_monitor_job \
  --location asia-northeast1 \
  --schedule="*/30 * * * *"
```

### 関数の削除

不要になった場合：

```bash
# Cloud Functionの削除
gcloud functions delete switch2_monitor --region asia-northeast1

# Cloud Schedulerジョブの削除
gcloud scheduler jobs delete switch2_monitor_job --location asia-northeast1
```

### コスト監視

```bash
# 使用状況の確認（GCP Consoleで詳細確認）
gcloud billing accounts list
```

[GCP Console](https://console.cloud.google.com/billing) で詳細なコスト分析が可能です。

---

## チェックリスト

デプロイ完了時に以下を確認してください：

- [ ] Google Cloud SDKがインストールされている
- [ ] GCPプロジェクトが作成され、課金が有効化されている
- [ ] 必要なAPI（Cloud Functions, Cloud Build, Cloud Scheduler）が有効化されている
- [ ] ローカルテスト（`python test_local.py`）が成功している
- [ ] Cloud Functionsにデプロイが成功している
- [ ] テストモード（`?test=true`）で通知が届く
- [ ] Cloud Schedulerジョブが作成されている
- [ ] スケジューラーの手動実行が成功している
- [ ] ログで正常な動作を確認できている

すべてにチェックが付いたら、デプロイ完了です！🎉

---

## サポート

問題が発生した場合は、README.mdの「トラブルシューティング」セクションを参照してください。

- [README.md - トラブルシューティング](README.md#トラブルシューティング)
- [Google Cloud Functions ドキュメント](https://cloud.google.com/functions/docs)
- [Cloud Scheduler ドキュメント](https://cloud.google.com/scheduler/docs)
