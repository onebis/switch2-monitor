"""
LINE Messaging API通知機能
LINE Notify終了に伴い、Messaging APIに移行
"""
import requests
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LineNotifier:
    """LINE Messaging APIで通知を送信するクラス"""

    PUSH_API_URL = 'https://api.line.me/v2/bot/message/push'
    MAX_TEXT_LENGTH = 5000  # Messaging APIのテキストメッセージの最大文字数

    def __init__(self, channel_access_token: str, user_id: str = '', group_id: str = ''):
        """
        Args:
            channel_access_token: LINE Messaging APIのチャネルアクセストークン
            user_id: 送信先のユーザーID（個人宛ての場合）
            group_id: 送信先のグループID（グループ宛ての場合）
        """
        self.channel_access_token = channel_access_token
        self.user_id = user_id
        self.group_id = group_id

        # 送信先の決定（グループIDが優先）
        self.to = group_id if group_id else user_id

        if not self.to:
            raise ValueError("user_idまたはgroup_idのいずれかを指定してください")

        self.headers = {
            'Authorization': f'Bearer {channel_access_token}',
            'Content-Type': 'application/json'
        }

    def send_message(self, message: str) -> bool:
        """
        メッセージを送信

        Args:
            message: 送信するメッセージ

        Returns:
            送信成功時True、失敗時False
        """
        try:
            # 文字数制限のチェック
            if len(message) > self.MAX_TEXT_LENGTH:
                message = message[:self.MAX_TEXT_LENGTH - 50] + '\n...\n(文字数制限のため省略されました)'
                logger.warning(f"メッセージが{self.MAX_TEXT_LENGTH}文字を超えたため切り詰めました")

            # リクエストボディの作成
            data = {
                'to': self.to,
                'messages': [
                    {
                        'type': 'text',
                        'text': message
                    }
                ]
            }

            response = requests.post(
                self.PUSH_API_URL,
                headers=self.headers,
                json=data,
                timeout=10
            )
            response.raise_for_status()

            logger.info("LINE Messaging API経由で通知を送信しました")
            return True

        except requests.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("認証エラー: チャネルアクセストークンが無効です")
            elif e.response.status_code == 400:
                logger.error(f"リクエストエラー: {e.response.text}")
            else:
                logger.error(f"HTTPエラー: {e}")
            return False
        except requests.RequestException as e:
            logger.error(f"LINE通知の送信に失敗: {e}")
            return False

    def send_lottery_notification(self, lotteries: List[Dict[str, str]]) -> bool:
        """
        抽選情報の通知を送信（旧形式、互換性のため残す）

        Args:
            lotteries: 抽選情報のリスト

        Returns:
            送信成功時True、失敗時False
        """
        if not lotteries:
            logger.info("通知する抽選情報がありません")
            return False

        # メッセージ作成
        message_parts = ["\n🎮 Switch2 抽選販売情報 🎮\n"]

        for i, lottery in enumerate(lotteries, 1):
            title = lottery.get('title', 'タイトルなし')
            period = lottery.get('period', '期間不明')
            url = lottery.get('url', '')

            message_parts.append(f"\n【{i}】{title}")
            if period:
                message_parts.append(f"期間: {period}")
            if url:
                message_parts.append(f"URL: {url}")

        message = '\n'.join(message_parts)
        return self.send_message(message)

    def send_lottery_notification_v2(self, items: List[Dict[str, str]]) -> bool:
        """
        検出されたアイテムの通知を送信（改善版）

        Args:
            items: 検出されたアイテムのリスト
                   各アイテムは type, title, content, url を含む辞書

        Returns:
            送信成功時True、失敗時False
        """
        if not items:
            logger.info("通知するアイテムがありません")
            return False

        from datetime import datetime

        # メッセージヘッダー
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        message_parts = [
            "\n━━━━━━━━━━━━━━━━━━",
            "🎮 Switch2 新情報検出！",
            "━━━━━━━━━━━━━━━━━━\n"
        ]

        # アイテムをタイプ別にグループ化
        grouped_items = {}
        for item in items:
            item_type = item.get('type', 'unknown')
            if item_type not in grouped_items:
                grouped_items[item_type] = []
            grouped_items[item_type].append(item)

        # タイプの優先順位と絵文字
        type_priority = ['heading', 'banner', 'link', 'paragraph']
        type_info = {
            'heading': {'label': '📌 重要見出し', 'emoji': '💡'},
            'banner': {'label': '📢 バナー情報', 'emoji': '🔔'},
            'link': {'label': '🔗 関連リンク', 'emoji': '➡️'},
            'paragraph': {'label': '📝 詳細情報', 'emoji': '📄'}
        }

        total_count = 0
        max_items_per_type = 3  # 各タイプ最大3件まで（見やすさのため）

        for item_type in type_priority:
            if item_type not in grouped_items:
                continue

            type_items = grouped_items[item_type]
            info = type_info.get(item_type, {'label': item_type, 'emoji': '•'})

            # タイプヘッダー
            if total_count > 0:
                message_parts.append("")  # 空行で区切り
            message_parts.append(f"{info['label']}")
            message_parts.append("─" * 20)

            for i, item in enumerate(type_items[:max_items_per_type], 1):
                total_count += 1
                title = item.get('title', '').strip()
                content = item.get('content', '').strip()
                url = item.get('url', '')

                # タイトル
                if len(title) > 80:
                    title = title[:77] + '...'
                message_parts.append(f"\n{info['emoji']} {title}")

                # 概要（タイトルと異なる場合のみ、かつ短い場合）
                if content and content != title and len(content) <= 120:
                    # コンテキスト情報がある場合は表示
                    if '|' in content:
                        # "タイトル | 追加情報" の形式
                        parts = content.split('|')
                        if len(parts) > 1 and parts[1].strip():
                            summary = parts[1].strip()[:100]
                            message_parts.append(f"   {summary}")

                # URL（トップページ以外の場合のみ）
                if url and 'store-jp.nintendo.com' in url:
                    if url != 'https://store-jp.nintendo.com/' and url != 'https://store-jp.nintendo.com':
                        # URLを短縮表示
                        display_url = url.replace('https://store-jp.nintendo.com', '...nintendo.com')
                        if len(display_url) > 60:
                            display_url = display_url[:57] + '...'
                        message_parts.append(f"   🔗 {display_url}")

            # タイプ内のアイテム数表示
            remaining_in_type = len(type_items) - max_items_per_type
            if remaining_in_type > 0:
                message_parts.append(f"   ...他 {remaining_in_type}件")

        # フッター
        message_parts.append("\n━━━━━━━━━━━━━━━━━━")
        message_parts.append(f"検出時刻: {current_time}")
        message_parts.append(f"検出総数: {len(items)}件")
        message_parts.append("━━━━━━━━━━━━━━━━━━")

        message = '\n'.join(message_parts)
        return self.send_message(message)

    def send_test_notification(self) -> bool:
        """
        テスト通知を送信

        Returns:
            送信成功時True、失敗時False
        """
        from datetime import datetime
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        message = (
            "\n━━━━━━━━━━━━━━━━━━\n"
            "✅ Switch2監視システム\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "📡 テスト通知\n\n"
            "システムは正常に動作しています。\n"
            "LINE Messaging API連携が正しく設定されました。\n\n"
            f"送信時刻: {current_time}\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        return self.send_message(message)

    def send_error_notification(self, error_message: str) -> bool:
        """
        エラー通知を送信（改善版）

        Args:
            error_message: エラーメッセージ

        Returns:
            送信成功時True、失敗時False
        """
        from datetime import datetime
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # エラーメッセージを整形
        error_lines = error_message.split('\n')
        formatted_error = '\n'.join(f"  {line}" for line in error_lines if line.strip())

        message = (
            "\n━━━━━━━━━━━━━━━━━━\n"
            "⚠️ Switch2監視システム\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "❌ エラーが発生しました\n\n"
            "【エラー内容】\n"
            f"{formatted_error}\n\n"
            f"発生時刻: {current_time}\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💡 確認項目:\n"
            "  • 環境変数の設定\n"
            "  • ネットワーク接続\n"
            "  • 監視対象サイトの状態\n"
            "━━━━━━━━━━━━━━━━━━"
        )

        return self.send_message(message)

    def send_status_notification(self, status: str, details: str = "") -> bool:
        """
        ステータス通知を送信

        Args:
            status: ステータス（success, info, warning, errorなど）
            details: 詳細メッセージ

        Returns:
            送信成功時True、失敗時False
        """
        from datetime import datetime
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')

        status_info = {
            'success': {'emoji': '✅', 'label': '成功'},
            'info': {'emoji': 'ℹ️', 'label': '情報'},
            'warning': {'emoji': '⚠️', 'label': '警告'},
            'error': {'emoji': '❌', 'label': 'エラー'}
        }

        info = status_info.get(status, {'emoji': '📢', 'label': '通知'})

        message = (
            "\n━━━━━━━━━━━━━━━━━━\n"
            f"{info['emoji']} Switch2監視システム\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"【{info['label']}】\n"
            f"{details}\n\n"
            f"時刻: {current_time}\n"
            "━━━━━━━━━━━━━━━━━━"
        )

        return self.send_message(message)


def main():
    """テスト用のメイン関数"""
    import os
    from dotenv import load_dotenv
    import time

    load_dotenv()

    channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    user_id = os.getenv('LINE_USER_ID')
    group_id = os.getenv('LINE_GROUP_ID')

    if not channel_access_token:
        print("❌ エラー: LINE_CHANNEL_ACCESS_TOKENが設定されていません")
        print("   .envファイルにLINE_CHANNEL_ACCESS_TOKENを設定してください")
        return

    if not user_id and not group_id:
        print("❌ エラー: LINE_USER_IDまたはLINE_GROUP_IDが設定されていません")
        print("   .envファイルにLINE_USER_IDまたはLINE_GROUP_IDを設定してください")
        return

    notifier = LineNotifier(channel_access_token, user_id, group_id)

    print("=" * 60)
    print("LINE Messaging API 通知機能テスト")
    print("=" * 60)

    # 1. テスト通知
    print("\n1️⃣  テスト通知を送信します...")
    if notifier.send_test_notification():
        print("   ✅ 送信成功")
    else:
        print("   ❌ 送信失敗")

    time.sleep(2)  # API制限を考慮

    # 2. 抽選情報の通知テスト（旧形式）
    print("\n2️⃣  抽選情報の通知テスト（旧形式）...")
    test_lotteries = [
        {
            'title': 'Nintendo Switch2 本体 抽選販売',
            'period': '2025-01-15 10:00 ~ 2025-01-20 23:59',
            'url': 'https://store-jp.nintendo.com/lottery/switch2'
        },
        {
            'title': 'Switch2 多言語版 + ゲームソフトセット 抽選',
            'period': '2025-01-18 00:00 ~ 2025-01-25 23:59',
            'url': 'https://store-jp.nintendo.com/lottery/switch2-bundle'
        }
    ]
    if notifier.send_lottery_notification(test_lotteries):
        print("   ✅ 送信成功")
    else:
        print("   ❌ 送信失敗")

    time.sleep(2)

    # 3. 新形式の通知テスト
    print("\n3️⃣  新情報検出の通知テスト（新形式）...")
    test_items = [
        {
            'type': 'heading',
            'title': '「Nintendo Switch 2（多言語対応）」招待販売について',
            'content': '「Nintendo Switch 2（多言語対応）」招待販売について | 申込期限: 11月18日（火）午前11:00',
            'url': 'https://store-jp.nintendo.com/switch2'
        },
        {
            'type': 'banner',
            'title': 'Switch2 抽選販売 受付中',
            'content': 'Switch2 抽選販売 受付中 | 詳細はこちら',
            'url': 'https://store-jp.nintendo.com/lottery/switch2'
        },
        {
            'type': 'link',
            'title': '多言語版Switch2の詳細を見る',
            'content': '多言語版Switch2の詳細を見る',
            'url': 'https://store-jp.nintendo.com/products/switch2-multilingual'
        }
    ]
    if notifier.send_lottery_notification_v2(test_items):
        print("   ✅ 送信成功")
    else:
        print("   ❌ 送信失敗")

    time.sleep(2)

    # 4. エラー通知テスト
    print("\n4️⃣  エラー通知テスト...")
    test_error = "設定エラー: LINE_CHANNEL_ACCESS_TOKENが設定されていません\nネットワークエラー: タイムアウトが発生しました"
    if notifier.send_error_notification(test_error):
        print("   ✅ 送信成功")
    else:
        print("   ❌ 送信失敗")

    time.sleep(2)

    # 5. ステータス通知テスト
    print("\n5️⃣  ステータス通知テスト...")
    if notifier.send_status_notification('success', '監視システムが正常に起動しました。\n定期監視を開始します。'):
        print("   ✅ 送信成功")
    else:
        print("   ❌ 送信失敗")

    print("\n" + "=" * 60)
    print("テスト完了！LINEアプリで通知を確認してください。")
    print("=" * 60)


if __name__ == '__main__':
    main()
