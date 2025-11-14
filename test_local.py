"""
ローカルテスト実行スクリプト
Switch2監視システムの各コンポーネントを個別にテストします
"""
import sys
import os
from datetime import datetime


def print_section(title: str):
    """セクション区切りを表示"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_config():
    """設定のテスト"""
    print_section("1. 設定の確認")
    try:
        import config

        print(f"✓ 監視URL: {config.TARGET_URL}")
        print(f"✓ 状態ファイル: {config.STATE_FILE}")
        print(f"✓ キーワード数: {len(config.WATCH_KEYWORDS)}")
        print(f"✓ キーワードマッチモード: {config.KEYWORD_MATCH_MODE}")
        print(f"✓ ログレベル: {config.LOG_LEVEL}")

        # LINE Notifyトークンの確認（伏せ字で表示）
        if config.LINE_CHANNEL_ACCESS_TOKEN:
            masked_token = config.LINE_CHANNEL_ACCESS_TOKEN[:8] + "*" * 20 + config.LINE_CHANNEL_ACCESS_TOKEN[-4:]
            print(f"✓ LINE Notifyトークン: {masked_token}")
        else:
            print("⚠ LINE Notifyトークンが設定されていません")
            return False

        # 設定のバリデーション
        config.validate_config()
        print("\n✅ 設定は正常です")
        return True

    except ValueError as e:
        print(f"\n❌ 設定エラー: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        return False


def test_line_notify():
    """LINE Notify通知のテスト"""
    print_section("2. LINE Notify通知テスト")
    try:
        import config
        from notifier import LineNotifier

        notifier = LineNotifier(config.LINE_CHANNEL_ACCESS_TOKEN, config.LINE_USER_ID)

        print("テスト通知を送信します...")
        print("（LINEアプリで通知を確認してください）\n")

        if notifier.send_test_notification():
            print("✅ テスト通知の送信に成功しました")
            return True
        else:
            print("❌ テスト通知の送信に失敗しました")
            return False

    except Exception as e:
        print(f"❌ エラー: {e}")
        return False


def test_scraping():
    """スクレイピングのテスト"""
    print_section("3. スクレイピングテスト")
    try:
        import config
        from scraper import Switch2Scraper

        scraper = Switch2Scraper(
            config.TARGET_URL,
            config.WATCH_KEYWORDS,
            config.KEYWORD_MATCH_MODE
        )

        print(f"監視URL: {config.TARGET_URL}")
        print(f"キーワード: {', '.join(config.WATCH_KEYWORDS[:5])}...")
        print("\nページをスキャン中...\n")

        result = scraper.scan_page()

        if result['success']:
            print(f"✅ スキャン成功")
            print(f"   検出件数: {result['item_count']}件")
            print(f"   ページハッシュ: {result['hash'][:16]}...")

            if result['items']:
                print(f"\n検出されたアイテム（最大5件表示）:")
                for i, item in enumerate(result['items'][:5], 1):
                    print(f"\n  [{i}] タイプ: {item['type']}")
                    print(f"      タイトル: {item['title'][:60]}...")
                    if item.get('url'):
                        print(f"      URL: {item['url'][:60]}...")

            return True
        else:
            print(f"❌ スキャン失敗: {result.get('error')}")
            return False

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_management():
    """状態管理のテスト"""
    print_section("4. 状態管理テスト")
    try:
        import config
        from state_manager import StateManager
        from scraper import Switch2Scraper

        # テスト用の一時状態ファイル
        test_state_file = "test_state.json"
        state_manager = StateManager(test_state_file)

        print(f"状態ファイル: {test_state_file}")

        # 現在の状態をロード
        current_state = state_manager.load_state()
        if current_state:
            print("✓ 既存の状態が見つかりました")
        else:
            print("✓ 新規状態ファイルを作成します")

        # スクレイピング実行
        scraper = Switch2Scraper(
            config.TARGET_URL,
            config.WATCH_KEYWORDS,
            config.KEYWORD_MATCH_MODE
        )
        scan_result = scraper.scan_page()

        if not scan_result['success']:
            print(f"❌ スキャン失敗: {scan_result.get('error')}")
            return False

        # 状態の比較と更新
        comparison = state_manager.compare_and_update(scan_result)

        print(f"\n✅ 状態管理テスト完了")
        print(f"   初回実行: {'はい' if comparison['is_first_run'] else 'いいえ'}")
        print(f"   変更検出: {'あり' if comparison['has_changes'] else 'なし'}")
        print(f"   新規アイテム: {len(comparison['new_items'])}件")

        if comparison['new_items']:
            print(f"\n   新規アイテムの例:")
            for item in comparison['new_items'][:3]:
                print(f"   - {item['title'][:50]}...")

        # テスト用ファイルのクリーンアップ
        print(f"\n   テスト状態ファイルを削除: {test_state_file}")
        if os.path.exists(test_state_file):
            os.remove(test_state_file)

        return True

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_system():
    """システム全体のテスト"""
    print_section("5. システム全体テスト")
    try:
        from main import check_lottery_and_notify

        print("監視システムを実行します...\n")

        result = check_lottery_and_notify()

        print(f"\n実行結果:")
        print(f"  ステータス: {result['status']}")
        print(f"  検出件数: {result.get('item_count', 0)}件")
        print(f"  変更検出: {'あり' if result.get('has_changes') else 'なし'}")
        print(f"  新規アイテム: {result.get('new_items_count', 0)}件")
        print(f"  通知送信: {'送信済み' if result.get('notification_sent') else '送信なし'}")
        print(f"  メッセージ: {result.get('message', 'なし')}")

        if result['status'] == 'success':
            print("\n✅ システム全体テスト成功")
            return True
        else:
            print(f"\n⚠ テスト完了（エラーあり）: {result.get('error')}")
            return False

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """メイン実行関数"""
    print("\n" + "=" * 70)
    print("  Switch2監視システム - ローカルテストスイート")
    print("=" * 70)
    print(f"  実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # .envファイルの確認
    if not os.path.exists('.env'):
        print("\n⚠ 警告: .envファイルが見つかりません")
        print("   .env.exampleをコピーして.envを作成し、設定を行ってください。")
        print("\n   コマンド: cp .env.example .env")
        print("   その後、.envファイルを編集してLINE_NOTIFY_TOKENを設定してください。")
        return

    # テストの実行
    results = []

    # 1. 設定テスト
    results.append(("設定", test_config()))

    # 設定に問題がある場合は中断
    if not results[0][1]:
        print("\n" + "=" * 70)
        print("  ❌ 設定に問題があるため、テストを中断します")
        print("=" * 70)
        return

    # 2. LINE Notify通知テスト（スキップ可能）
    print("\n" + "-" * 70)
    response = input("LINE Notify通知テストを実行しますか？ (y/N): ").strip().lower()
    if response in ['y', 'yes']:
        results.append(("LINE Notify", test_line_notify()))
    else:
        print("スキップしました")
        results.append(("LINE Notify", None))

    # 3. スクレイピングテスト
    results.append(("スクレイピング", test_scraping()))

    # 4. 状態管理テスト
    results.append(("状態管理", test_state_management()))

    # 5. システム全体テスト（スキップ可能）
    print("\n" + "-" * 70)
    response = input("システム全体テスト（実際の通知送信）を実行しますか？ (y/N): ").strip().lower()
    if response in ['y', 'yes']:
        results.append(("システム全体", test_full_system()))
    else:
        print("スキップしました")
        results.append(("システム全体", None))

    # 結果サマリー
    print_section("テスト結果サマリー")

    for name, result in results:
        if result is None:
            status = "⊘ スキップ"
        elif result:
            status = "✅ 成功"
        else:
            status = "❌ 失敗"
        print(f"  {status}  {name}")

    # 総合判定
    failures = [name for name, result in results if result is False]

    print("\n" + "=" * 70)
    if not failures:
        print("  ✅ すべてのテストが成功しました！")
        print("     Cloud Functionsにデプロイする準備が整っています。")
    else:
        print(f"  ⚠ {len(failures)}個のテストが失敗しました:")
        for name in failures:
            print(f"     - {name}")
        print("\n     エラーを修正してから再度テストしてください。")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n中断されました")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
