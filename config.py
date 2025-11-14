"""
設定ファイル
"""
import os
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# LINE Messaging API設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_USER_ID = os.getenv('LINE_USER_ID', '')  # 個人宛て通知の場合
LINE_GROUP_ID = os.getenv('LINE_GROUP_ID', '')  # グループ宛て通知の場合

# 監視対象URL
TARGET_URL = os.getenv(
    'TARGET_URL',
    'https://store-jp.nintendo.com/'
)

# 監視キーワード（これらのキーワードを含むコンテンツを検出）
WATCH_KEYWORDS = [
    'Switch2',
    'Switch 2',
    'Nintendo Switch 2',
    '多言語',
    '多言語対応',
    '抽選',
    '抽選販売',
    '招待販売',
    '申込み',
    '申し込み',
]

# 検出条件（'any': いずれか、'all': すべて）
KEYWORD_MATCH_MODE = os.getenv('KEYWORD_MATCH_MODE', 'any')

# スクレイピング設定
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))  # タイムアウト（秒）
USER_AGENT = os.getenv(
    'USER_AGENT',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)

# 状態管理設定
STATE_FILE = os.getenv('STATE_FILE', 'switch2_state.json')  # ローカルの状態ファイル

# Cloud Storage設定（前回の抽選情報を保存する場合）
GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', '')
GCS_STATE_FILE = os.getenv('GCS_STATE_FILE', 'switch2_lottery_state.json')
USE_CLOUD_STORAGE = os.getenv('USE_CLOUD_STORAGE', 'False').lower() == 'true'

# ログレベル
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# デバッグモード
DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'


def validate_config():
    """設定のバリデーション"""
    errors = []

    if not LINE_CHANNEL_ACCESS_TOKEN:
        errors.append("LINE_CHANNEL_ACCESS_TOKENが設定されていません")

    if not LINE_USER_ID and not LINE_GROUP_ID:
        errors.append("LINE_USER_IDまたはLINE_GROUP_IDのいずれかを設定してください")

    if not TARGET_URL:
        errors.append("TARGET_URLが設定されていません")

    if not WATCH_KEYWORDS:
        errors.append("監視キーワードが設定されていません")

    if KEYWORD_MATCH_MODE not in ['any', 'all']:
        errors.append("KEYWORD_MATCH_MODEは'any'または'all'を指定してください")

    if errors:
        error_message = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"設定エラー:\n{error_message}")


if __name__ == '__main__':
    print("設定情報:")
    print(f"TARGET_URL: {TARGET_URL}")
    print(f"LINE_CHANNEL_ACCESS_TOKEN: {'設定済み' if LINE_CHANNEL_ACCESS_TOKEN else '未設定'}")
    print(f"LINE_USER_ID: {'設定済み' if LINE_USER_ID else '未設定'}")
    print(f"LINE_GROUP_ID: {'設定済み' if LINE_GROUP_ID else '未設定'}")
    print(f"監視キーワード数: {len(WATCH_KEYWORDS)}")
    print(f"キーワードマッチモード: {KEYWORD_MATCH_MODE}")
    print(f"REQUEST_TIMEOUT: {REQUEST_TIMEOUT}秒")
    print(f"STATE_FILE: {STATE_FILE}")
    print(f"DEBUG_MODE: {DEBUG_MODE}")

    try:
        validate_config()
        print("\n✓ 設定は正常です")
    except ValueError as e:
        print(f"\n✗ {e}")
