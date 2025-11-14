"""
Switch2 抽選販売監視システム - Cloud Functions エントリーポイント
"""
import json
import logging
from typing import Any, Dict
import functions_framework
from flask import Request

from scraper import Switch2Scraper
from notifier import LineNotifier
from state_manager import StateManager
import config

# ロギング設定
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_lottery_and_notify() -> Dict:
    """
    抽選情報をチェックして、新しい情報があれば通知

    Returns:
        実行結果の辞書
    """
    try:
        # 設定のバリデーション
        config.validate_config()

        # コンポーネントの初期化
        scraper = Switch2Scraper(
            config.TARGET_URL,
            config.WATCH_KEYWORDS,
            config.KEYWORD_MATCH_MODE
        )
        notifier = LineNotifier(
            config.LINE_CHANNEL_ACCESS_TOKEN,
            config.LINE_USER_ID,
            config.LINE_GROUP_ID
        )
        state_manager = StateManager(
            config.STATE_FILE,
            use_gcs=config.USE_CLOUD_STORAGE,
            gcs_bucket_name=config.GCS_BUCKET_NAME,
            gcs_state_file=config.GCS_STATE_FILE
        )

        logger.info("=" * 60)
        logger.info("Switch2 抽選販売監視を開始")
        logger.info(f"監視URL: {config.TARGET_URL}")
        logger.info(f"キーワード数: {len(config.WATCH_KEYWORDS)}")
        logger.info("=" * 60)

        # ページをスキャン
        scan_result = scraper.scan_page()

        if not scan_result['success']:
            error_msg = f"スキャン失敗: {scan_result.get('error')}"
            logger.error(error_msg)
            notifier.send_error_notification(error_msg)
            return {
                'status': 'error',
                'error': error_msg
            }

        logger.info(f"スキャン成功: {scan_result['item_count']}件検出")

        # 前回の状態と比較
        comparison = state_manager.compare_and_update(scan_result)

        result = {
            'status': 'success',
            'item_count': scan_result['item_count'],
            'has_changes': comparison['has_changes'],
            'new_items_count': len(comparison['new_items']),
            'is_first_run': comparison['is_first_run'],
            'notification_sent': False
        }

        # 変更があれば通知
        if comparison['has_changes']:
            if comparison['is_first_run']:
                logger.info("初回実行のため、通知をスキップします")
                result['notification_sent'] = False
                result['message'] = '初回実行完了（通知なし）'
            else:
                logger.info(f"{len(comparison['new_items'])}件の新しいコンテンツを検出")

                # 通知用のメッセージを作成
                if notifier.send_lottery_notification_v2(comparison['new_items']):
                    logger.info("LINE通知を送信しました")
                    result['notification_sent'] = True
                    result['message'] = f"{len(comparison['new_items'])}件の新情報を通知"
                else:
                    logger.error("LINE通知の送信に失敗しました")
                    result['status'] = 'partial_success'
                    result['message'] = '通知送信失敗'
        else:
            logger.info("変更なし: 通知はスキップします")
            result['message'] = '変更なし'

        logger.info("=" * 60)
        logger.info(f"監視結果: {result['message']}")
        logger.info("=" * 60)

        return result

    except ValueError as e:
        # 設定エラー
        error_msg = f"設定エラー: {str(e)}"
        logger.error(error_msg)

        try:
            notifier = LineNotifier(
                config.LINE_CHANNEL_ACCESS_TOKEN,
                config.LINE_USER_ID,
                config.LINE_GROUP_ID
            )
            notifier.send_error_notification(error_msg)
        except:
            pass

        return {
            'status': 'error',
            'error': error_msg
        }

    except Exception as e:
        # その他のエラー
        error_msg = f"予期しないエラー: {str(e)}"
        logger.exception(error_msg)

        try:
            if config.LINE_CHANNEL_ACCESS_TOKEN:
                notifier = LineNotifier(
                    config.LINE_CHANNEL_ACCESS_TOKEN,
                    config.LINE_USER_ID,
                    config.LINE_GROUP_ID
                )
                notifier.send_error_notification(error_msg)
        except:
            pass

        return {
            'status': 'error',
            'error': error_msg
        }


@functions_framework.http
def main(request: Request) -> Any:
    """
    Cloud Functions HTTPトリガーのエントリーポイント

    Args:
        request: Flaskリクエストオブジェクト

    Returns:
        JSON レスポンス
    """
    logger.info("Switch2監視システムを起動（HTTP）")

    # クエリパラメータでテストモードを確認
    test_mode = request.args.get('test', 'false').lower() == 'true'
    force_notify = request.args.get('force', 'false').lower() == 'true'

    if test_mode:
        # テストモード: テスト通知を送信
        logger.info("テストモードで実行")
        try:
            config.validate_config()
            notifier = LineNotifier(
                config.LINE_CHANNEL_ACCESS_TOKEN,
                config.LINE_USER_ID,
                config.LINE_GROUP_ID
            )
            notifier.send_test_notification()

            return {
                'status': 'success',
                'mode': 'test',
                'message': 'テスト通知を送信しました'
            }, 200
        except Exception as e:
            logger.exception(f"テストモードでエラー: {e}")
            return {
                'status': 'error',
                'mode': 'test',
                'error': str(e)
            }, 500

    elif force_notify:
        # 強制通知モード: 状態をリセットして実行
        logger.info("強制通知モードで実行")
        try:
            state_manager = StateManager(
                config.STATE_FILE,
                use_gcs=config.USE_CLOUD_STORAGE,
                gcs_bucket_name=config.GCS_BUCKET_NAME,
                gcs_state_file=config.GCS_STATE_FILE
            )
            state_manager.reset_state()
            logger.info("状態をリセットしました")

            result = check_lottery_and_notify()
            status_code = 200 if result['status'] in ['success', 'partial_success'] else 500
            return result, status_code

        except Exception as e:
            logger.exception(f"強制通知モードでエラー: {e}")
            return {
                'status': 'error',
                'mode': 'force',
                'error': str(e)
            }, 500

    else:
        # 通常モード: 抽選をチェック
        result = check_lottery_and_notify()
        status_code = 200 if result['status'] in ['success', 'partial_success'] else 500
        return result, status_code


# Cloud Pub/Subトリガー用（オプション）
@functions_framework.cloud_event
def main_pubsub(cloud_event):
    """
    Cloud Pub/Subトリガーのエントリーポイント

    Args:
        cloud_event: CloudEventオブジェクト
    """
    logger.info("Switch2監視システムを起動（Pub/Sub）")

    result = check_lottery_and_notify()
    logger.info(f"実行結果: {json.dumps(result, ensure_ascii=False)}")


# ローカルテスト用
if __name__ == '__main__':
    print("=" * 60)
    print("Switch2 抽選販売監視システム - ローカルテスト")
    print("=" * 60)
    print(f"監視URL: {config.TARGET_URL}")
    print(f"状態ファイル: {config.STATE_FILE}")
    print("=" * 60)

    # テスト実行
    result = check_lottery_and_notify()

    print("\n" + "=" * 60)
    print("実行結果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=" * 60)

    if result['status'] == 'success':
        print("\n✓ 正常に完了しました")
    else:
        print(f"\n✗ エラーが発生しました: {result.get('error')}")
