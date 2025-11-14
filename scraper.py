"""
Switch2 抽選販売ページのスクレイピング
任天堂公式ストア（https://store-jp.nintendo.com/）向けに最適化
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Set
import logging
import hashlib
import re
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Switch2Scraper:
    """Switch2の抽選販売情報をスクレイピングするクラス"""

    def __init__(self, target_url: str, keywords: List[str], match_mode: str = 'any'):
        """
        Args:
            target_url: 監視対象のURL
            keywords: 検出対象のキーワードリスト
            match_mode: 'any'（いずれか） or 'all'（すべて）
        """
        self.target_url = target_url
        self.keywords = keywords
        self.match_mode = match_mode
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def fetch_page(self, max_retries: int = 3) -> Optional[str]:
        """
        ページのHTMLを取得（リトライ機能付き）

        Args:
            max_retries: 最大リトライ回数

        Returns:
            HTML文字列、取得失敗時はNone
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"ページ取得中... (試行 {attempt + 1}/{max_retries})")
                response = requests.get(
                    self.target_url,
                    headers=self.headers,
                    timeout=30
                )
                response.raise_for_status()
                response.encoding = response.apparent_encoding

                logger.info(f"ページ取得成功: {len(response.text)} 文字")
                return response.text

            except requests.Timeout:
                logger.warning(f"タイムアウト (試行 {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    logger.error("タイムアウトによりページ取得失敗")
                    return None

            except requests.RequestException as e:
                logger.error(f"ページ取得エラー (試行 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return None

        return None

    def check_keywords_in_text(self, text: str) -> bool:
        """
        テキストにキーワードが含まれているかチェック

        Args:
            text: チェック対象のテキスト

        Returns:
            条件に一致する場合True
        """
        text_lower = text.lower()
        matches = [keyword.lower() in text_lower for keyword in self.keywords]

        if self.match_mode == 'all':
            return all(matches)
        else:  # 'any'
            return any(matches)

    def extract_relevant_content(self, html: str) -> List[Dict[str, str]]:
        """
        HTMLからキーワードに関連するコンテンツを抽出

        Args:
            html: HTML文字列

        Returns:
            関連コンテンツのリスト
        """
        soup = BeautifulSoup(html, 'lxml')
        relevant_items = []
        found_elements = set()  # 重複を避けるため

        try:
            # 1. 見出し要素（h1-h6）をチェック
            for heading_tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                headings = soup.find_all(heading_tag)
                for heading in headings:
                    text = heading.get_text(strip=True)
                    if text and self.check_keywords_in_text(text):
                        element_id = hashlib.md5(text.encode()).hexdigest()
                        if element_id not in found_elements:
                            found_elements.add(element_id)

                            # 周辺のコンテキストを取得
                            context = self._extract_context(heading)

                            item = {
                                'type': 'heading',
                                'tag': heading_tag,
                                'title': text,
                                'content': context,
                                'url': self.target_url
                            }

                            # リンクがあれば取得
                            link = heading.find('a') or heading.find_parent('a')
                            if link and link.get('href'):
                                item['url'] = urljoin(self.target_url, link['href'])

                            relevant_items.append(item)
                            logger.debug(f"見出し検出: {text[:50]}...")

            # 2. リンク要素をチェック
            links = soup.find_all('a', href=True)
            for link in links:
                text = link.get_text(strip=True)
                href = link.get('href', '')

                # URLパターンチェック（/switch2 など）
                url_matches_keyword = any(
                    keyword.lower() in href.lower()
                    for keyword in self.keywords
                )

                if text and (self.check_keywords_in_text(text) or url_matches_keyword):
                    element_id = hashlib.md5((text + href).encode()).hexdigest()
                    if element_id not in found_elements:
                        found_elements.add(element_id)

                        item = {
                            'type': 'link',
                            'title': text,
                            'url': urljoin(self.target_url, href),
                            'content': text
                        }
                        relevant_items.append(item)
                        logger.debug(f"リンク検出: {text[:50]}...")

            # 3. バナー・通知エリアをチェック
            banner_classes = ['banner', 'notification', 'alert', 'announcement', 'notice']
            for class_name in banner_classes:
                banners = soup.find_all(class_=re.compile(class_name, re.I))
                for banner in banners:
                    text = banner.get_text(strip=True)
                    if text and self.check_keywords_in_text(text):
                        element_id = hashlib.md5(text.encode()).hexdigest()
                        if element_id not in found_elements:
                            found_elements.add(element_id)

                            item = {
                                'type': 'banner',
                                'title': text[:100],  # 長すぎる場合は切り詰め
                                'content': text,
                                'url': self.target_url
                            }

                            # リンクがあれば取得
                            link = banner.find('a')
                            if link and link.get('href'):
                                item['url'] = urljoin(self.target_url, link['href'])

                            relevant_items.append(item)
                            logger.debug(f"バナー検出: {text[:50]}...")

            # 4. 段落・div要素をチェック（厳しめの条件）
            paragraphs = soup.find_all(['p', 'div'])
            for para in paragraphs:
                text = para.get_text(strip=True)
                # 長すぎる、または短すぎるテキストは除外
                if text and 10 < len(text) < 500 and self.check_keywords_in_text(text):
                    element_id = hashlib.md5(text.encode()).hexdigest()
                    if element_id not in found_elements:
                        found_elements.add(element_id)

                        item = {
                            'type': 'paragraph',
                            'title': text[:100],
                            'content': text,
                            'url': self.target_url
                        }

                        # 親要素にリンクがあれば取得
                        link = para.find('a') or para.find_parent('a')
                        if link and link.get('href'):
                            item['url'] = urljoin(self.target_url, link['href'])

                        relevant_items.append(item)
                        logger.debug(f"段落検出: {text[:50]}...")

            logger.info(f"{len(relevant_items)}件の関連コンテンツを検出")

        except Exception as e:
            logger.error(f"HTML解析エラー: {e}", exc_info=True)

        return relevant_items

    def _extract_context(self, element) -> str:
        """
        要素の周辺コンテキストを抽出

        Args:
            element: BeautifulSoup要素

        Returns:
            コンテキスト文字列
        """
        context_parts = []

        # 要素自体のテキスト
        context_parts.append(element.get_text(strip=True))

        # 次の兄弟要素を最大3つまで取得
        next_sibling = element.find_next_sibling()
        count = 0
        while next_sibling and count < 3:
            sibling_text = next_sibling.get_text(strip=True)
            if sibling_text and len(sibling_text) > 5:
                context_parts.append(sibling_text)
                count += 1
            next_sibling = next_sibling.find_next_sibling()

        return ' | '.join(context_parts[:3])  # 最大3つまで

    def get_page_hash(self, html: str) -> str:
        """
        ページコンテンツのハッシュ値を計算

        Args:
            html: HTML文字列

        Returns:
            SHA256ハッシュ値
        """
        # HTMLから関連コンテンツのみを抽出してハッシュ化
        relevant_content = self.extract_relevant_content(html)
        content_str = str(relevant_content)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def scan_page(self) -> Dict[str, any]:
        """
        ページをスキャンして関連情報を取得

        Returns:
            スキャン結果の辞書
        """
        html = self.fetch_page()
        if not html:
            return {
                'success': False,
                'error': 'ページの取得に失敗しました',
                'items': [],
                'hash': None
            }

        try:
            items = self.extract_relevant_content(html)
            page_hash = self.get_page_hash(html)

            return {
                'success': True,
                'items': items,
                'hash': page_hash,
                'item_count': len(items),
                'url': self.target_url
            }

        except Exception as e:
            logger.error(f"スキャンエラー: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'items': [],
                'hash': None
            }


def main():
    """テスト用のメイン関数"""
    from config import TARGET_URL, WATCH_KEYWORDS, KEYWORD_MATCH_MODE

    print("=" * 60)
    print("Switch2 スクレイピングテスト")
    print("=" * 60)
    print(f"監視URL: {TARGET_URL}")
    print(f"キーワード: {', '.join(WATCH_KEYWORDS)}")
    print(f"マッチモード: {KEYWORD_MATCH_MODE}")
    print("=" * 60)

    scraper = Switch2Scraper(TARGET_URL, WATCH_KEYWORDS, KEYWORD_MATCH_MODE)
    result = scraper.scan_page()

    if result['success']:
        print(f"\n✓ スキャン成功")
        print(f"検出数: {result['item_count']}件")
        print(f"ハッシュ値: {result['hash'][:16]}...")

        if result['items']:
            print(f"\n検出されたアイテム:")
            for i, item in enumerate(result['items'], 1):
                print(f"\n{i}. [{item['type']}] {item['title'][:80]}")
                if item.get('url') != TARGET_URL:
                    print(f"   URL: {item['url']}")
        else:
            print("\nキーワードに一致するコンテンツは見つかりませんでした")
    else:
        print(f"\n✗ スキャン失敗: {result.get('error')}")


if __name__ == '__main__':
    main()
