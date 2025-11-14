"""
状態管理モジュール
前回のスキャン結果を保存し、変更を検出する
"""
import json
import os
from datetime import datetime
from typing import Dict, Optional, List
import logging

# GCS対応（オプショナル）
try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("google-cloud-storage がインストールされていません。ローカルファイルのみ使用可能です。")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StateManager:
    """スキャン結果の状態を管理するクラス"""

    def __init__(self, state_file_path: str, use_gcs: bool = False,
                 gcs_bucket_name: str = '', gcs_state_file: str = ''):
        """
        Args:
            state_file_path: ローカル状態ファイルのパス
            use_gcs: Google Cloud Storageを使用するか
            gcs_bucket_name: GCSバケット名
            gcs_state_file: GCS上の状態ファイル名
        """
        self.state_file_path = state_file_path
        self.use_gcs = use_gcs and GCS_AVAILABLE
        self.gcs_bucket_name = gcs_bucket_name
        self.gcs_state_file = gcs_state_file

        if use_gcs and not GCS_AVAILABLE:
            logger.warning("GCSの使用が指定されていますが、google-cloud-storageが利用できません。ローカルファイルを使用します。")
            self.use_gcs = False

        if self.use_gcs and not gcs_bucket_name:
            logger.error("GCS使用時はgcs_bucket_nameが必須です")
            raise ValueError("gcs_bucket_nameが指定されていません")

    def _load_state_from_gcs(self) -> Optional[Dict]:
        """
        GCSから状態を読み込み

        Returns:
            状態辞書、存在しない場合はNone
        """
        try:
            client = storage.Client()
            bucket = client.bucket(self.gcs_bucket_name)
            blob = bucket.blob(self.gcs_state_file)

            if not blob.exists():
                logger.info(f"GCS上に状態ファイルが存在しません: gs://{self.gcs_bucket_name}/{self.gcs_state_file}")
                return None

            content = blob.download_as_text(encoding='utf-8')
            state = json.loads(content)
            logger.info(f"GCSから状態を読み込みました: gs://{self.gcs_bucket_name}/{self.gcs_state_file}")
            return state

        except json.JSONDecodeError as e:
            logger.error(f"GCS状態ファイルの読み込みエラー（JSON解析失敗）: {e}")
            return None
        except Exception as e:
            logger.error(f"GCS状態ファイルの読み込みエラー: {e}")
            return None

    def _load_state_from_local(self) -> Optional[Dict]:
        """
        ローカルファイルから状態を読み込み

        Returns:
            状態辞書、存在しない場合はNone
        """
        if not os.path.exists(self.state_file_path):
            logger.info(f"状態ファイルが存在しません: {self.state_file_path}")
            return None

        try:
            with open(self.state_file_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
                logger.info(f"状態を読み込みました: {self.state_file_path}")
                return state
        except json.JSONDecodeError as e:
            logger.error(f"状態ファイルの読み込みエラー（JSON解析失敗）: {e}")
            return None
        except Exception as e:
            logger.error(f"状態ファイルの読み込みエラー: {e}")
            return None

    def load_state(self) -> Optional[Dict]:
        """
        前回の状態を読み込み（GCSまたはローカル）

        Returns:
            状態辞書、存在しない場合はNone
        """
        if self.use_gcs:
            return self._load_state_from_gcs()
        else:
            return self._load_state_from_local()

    def _save_state_to_gcs(self, state: Dict) -> bool:
        """
        GCSに状態を保存

        Args:
            state: 保存する状態辞書

        Returns:
            保存成功時True
        """
        try:
            # タイムスタンプを追加
            state['last_updated'] = datetime.now().isoformat()

            client = storage.Client()
            bucket = client.bucket(self.gcs_bucket_name)
            blob = bucket.blob(self.gcs_state_file)

            content = json.dumps(state, ensure_ascii=False, indent=2)
            blob.upload_from_string(content, content_type='application/json')

            logger.info(f"GCSに状態を保存しました: gs://{self.gcs_bucket_name}/{self.gcs_state_file}")
            return True

        except Exception as e:
            logger.error(f"GCS状態ファイルの保存エラー: {e}")
            return False

    def _save_state_to_local(self, state: Dict) -> bool:
        """
        ローカルファイルに状態を保存

        Args:
            state: 保存する状態辞書

        Returns:
            保存成功時True
        """
        try:
            # ディレクトリが存在しない場合は作成
            directory = os.path.dirname(self.state_file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            # タイムスタンプを追加
            state['last_updated'] = datetime.now().isoformat()

            with open(self.state_file_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

            logger.info(f"状態を保存しました: {self.state_file_path}")
            return True

        except Exception as e:
            logger.error(f"状態ファイルの保存エラー: {e}")
            return False

    def save_state(self, state: Dict) -> bool:
        """
        現在の状態を保存（GCSまたはローカル）

        Args:
            state: 保存する状態辞書

        Returns:
            保存成功時True
        """
        if self.use_gcs:
            return self._save_state_to_gcs(state)
        else:
            return self._save_state_to_local(state)

    def has_content_changed(self, current_hash: str, previous_hash: Optional[str]) -> bool:
        """
        コンテンツが変更されたかチェック

        Args:
            current_hash: 現在のハッシュ値
            previous_hash: 前回のハッシュ値

        Returns:
            変更があればTrue
        """
        if previous_hash is None:
            logger.info("前回のハッシュ値がありません（初回実行）")
            return True

        if current_hash != previous_hash:
            logger.info("コンテンツが変更されました")
            return True

        logger.info("コンテンツに変更はありません")
        return False

    def get_new_items(self, current_items: List[Dict], previous_items: List[Dict]) -> List[Dict]:
        """
        新しいアイテムを検出

        Args:
            current_items: 現在のアイテムリスト
            previous_items: 前回のアイテムリスト

        Returns:
            新しいアイテムのリスト
        """
        # タイトルと内容で識別
        previous_signatures = set()
        for item in previous_items:
            signature = f"{item.get('title', '')}:{item.get('content', '')}"
            previous_signatures.add(signature)

        new_items = []
        for item in current_items:
            signature = f"{item.get('title', '')}:{item.get('content', '')}"
            if signature not in previous_signatures:
                new_items.append(item)

        if new_items:
            logger.info(f"{len(new_items)}件の新しいアイテムを検出")
        else:
            logger.info("新しいアイテムはありません")

        return new_items

    def create_state_from_scan_result(self, scan_result: Dict) -> Dict:
        """
        スキャン結果から状態辞書を作成

        Args:
            scan_result: スキャン結果

        Returns:
            状態辞書
        """
        return {
            'hash': scan_result.get('hash'),
            'items': scan_result.get('items', []),
            'item_count': scan_result.get('item_count', 0),
            'url': scan_result.get('url'),
            'last_updated': datetime.now().isoformat()
        }

    def compare_and_update(self, current_scan_result: Dict) -> Dict:
        """
        前回の状態と比較し、変更があれば更新

        Args:
            current_scan_result: 現在のスキャン結果

        Returns:
            比較結果の辞書:
            {
                'has_changes': bool,
                'new_items': List[Dict],
                'previous_hash': str,
                'current_hash': str,
                'is_first_run': bool
            }
        """
        previous_state = self.load_state()
        is_first_run = previous_state is None

        current_hash = current_scan_result.get('hash')
        current_items = current_scan_result.get('items', [])

        if is_first_run:
            # 初回実行
            logger.info("初回実行です")
            new_state = self.create_state_from_scan_result(current_scan_result)
            self.save_state(new_state)

            return {
                'has_changes': True,
                'new_items': current_items,
                'previous_hash': None,
                'current_hash': current_hash,
                'is_first_run': True
            }

        # 前回の状態と比較
        previous_hash = previous_state.get('hash')
        previous_items = previous_state.get('items', [])

        has_changes = self.has_content_changed(current_hash, previous_hash)
        new_items = self.get_new_items(current_items, previous_items) if has_changes else []

        # 状態を更新
        if has_changes:
            new_state = self.create_state_from_scan_result(current_scan_result)
            self.save_state(new_state)

        return {
            'has_changes': has_changes,
            'new_items': new_items,
            'previous_hash': previous_hash,
            'current_hash': current_hash,
            'is_first_run': False
        }

    def reset_state(self) -> bool:
        """
        状態をリセット（ファイルを削除）

        Returns:
            成功時True
        """
        try:
            if self.use_gcs:
                client = storage.Client()
                bucket = client.bucket(self.gcs_bucket_name)
                blob = bucket.blob(self.gcs_state_file)
                if blob.exists():
                    blob.delete()
                    logger.info(f"GCS状態ファイルを削除しました: gs://{self.gcs_bucket_name}/{self.gcs_state_file}")
            else:
                if os.path.exists(self.state_file_path):
                    os.remove(self.state_file_path)
                    logger.info(f"状態ファイルを削除しました: {self.state_file_path}")
            return True
        except Exception as e:
            logger.error(f"状態ファイルの削除エラー: {e}")
            return False


def main():
    """テスト用のメイン関数"""
    import tempfile

    # テスト用の一時ファイル
    temp_file = os.path.join(tempfile.gettempdir(), 'test_state.json')

    print(f"テスト用状態ファイル: {temp_file}")

    manager = StateManager(temp_file)

    # テストデータ1（初回）
    scan_result_1 = {
        'success': True,
        'hash': 'abc123',
        'items': [
            {'title': 'Switch2 抽選開始', 'content': '詳細はこちら', 'url': 'https://example.com/1'}
        ],
        'item_count': 1,
        'url': 'https://store-jp.nintendo.com/'
    }

    print("\n=== 初回実行 ===")
    result_1 = manager.compare_and_update(scan_result_1)
    print(f"変更あり: {result_1['has_changes']}")
    print(f"初回実行: {result_1['is_first_run']}")
    print(f"新アイテム数: {len(result_1['new_items'])}")

    # テストデータ2（変更なし）
    scan_result_2 = scan_result_1.copy()

    print("\n=== 2回目実行（変更なし） ===")
    result_2 = manager.compare_and_update(scan_result_2)
    print(f"変更あり: {result_2['has_changes']}")
    print(f"新アイテム数: {len(result_2['new_items'])}")

    # テストデータ3（変更あり）
    scan_result_3 = {
        'success': True,
        'hash': 'xyz789',
        'items': [
            {'title': 'Switch2 抽選開始', 'content': '詳細はこちら', 'url': 'https://example.com/1'},
            {'title': 'Switch2 多言語版 抽選', 'content': '新しい抽選', 'url': 'https://example.com/2'}
        ],
        'item_count': 2,
        'url': 'https://store-jp.nintendo.com/'
    }

    print("\n=== 3回目実行（変更あり） ===")
    result_3 = manager.compare_and_update(scan_result_3)
    print(f"変更あり: {result_3['has_changes']}")
    print(f"新アイテム数: {len(result_3['new_items'])}")

    # クリーンアップ
    manager.reset_state()
    print(f"\n状態ファイルをクリーンアップしました")


if __name__ == '__main__':
    main()
