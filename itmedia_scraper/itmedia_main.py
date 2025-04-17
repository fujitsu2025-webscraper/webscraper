#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ITmedia AIスクレイパーのメインスクリプト
"""
import argparse
import time
from itmedia.scraper import ItmediaScraper

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='ITmedia AIから記事をスクレイピング')
    parser.add_argument('--pages', type=int, default=1, help='スクレイピングするページ数')
    parser.add_argument('--delay', type=int, default=2, help='リクエスト間の遅延（秒）')
    parser.add_argument('--output', type=str, help='出力ファイルパス（拡張子なし、.jsonと.csvの両方が追加されます）')
    parser.add_argument('--metadata-only', action='store_true', help='全文ではなくメタデータのみをスクレイピング')
    parser.add_argument('--keyword', type=str, help='キーワードで記事をフィルタリング')
    parser.add_argument('--category', type=str, help='カテゴリで記事をフィルタリング')
    parser.add_argument('--openai-api-key', type=str, help='内容要約用のOpenAI APIキー（オプション、デフォルトキーは埋め込まれています）')
    parser.add_argument('--disable-llm', action='store_true', help='LLM要約を無効にし、基本的なテキスト抽出を使用')
    parser.add_argument('--output-dir', type=str, default='output', help='出力ファイルを保存するディレクトリ')
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                        default='INFO', help='ロギングレベル')
    parser.add_argument('--archive', type=str, help='特定のアーカイブページをスクレイピング（例：https://www.itmedia.co.jp/aiplus/subtop/archive/2503.html）')
    parser.add_argument('--archive-month', type=str, help='特定の月のアーカイブをスクレイピング（形式：YYMM 例：2503は2025年3月）')
    parser.add_argument('--recent-archives', type=int, default=3, help='最近のN月分のアーカイブをスクレイピング（デフォルト：3、最大：12）')
    parser.add_argument('--start-from-month', type=str, help='特定の月からスクレイピングを再開（形式：YYMM 例：2503は2025年3月）')
    parser.add_argument('--max-articles', type=int, default=0, help='スクレイピングする最大記事数（0は無制限）')

    args = parser.parse_args()
    
    # スクレイパーを作成（APIキーが提供されている場合は使用、それ以外はデフォルトを使用）
    scraper = ItmediaScraper(
        delay=args.delay, 
        api_key=args.openai_api_key, 
        disable_llm=args.disable_llm,
        output_dir=args.output_dir,
        log_level=args.log_level
    )
    
    scraper.logger.info("ITmedia AIのスクレイピングを開始します...")
    
    # 開始時間を記録
    start_time = time.time()
    
    all_articles = []
    
    # 最大記事数のパラメータを渡す
    if args.archive:
        scraper.logger.info(f"アーカイブページをスクレイピング: {args.archive}")
        all_articles = scraper.scrape_archive(args.archive, not args.metadata_only, args.max_articles)
    elif args.archive_month:
        archive_url = f"https://www.itmedia.co.jp/aiplus/subtop/archive/{args.archive_month}.html"
        scraper.logger.info(f"月別アーカイブをスクレイピング: {archive_url}")
        all_articles = scraper.scrape_archive(archive_url, not args.metadata_only, args.max_articles)
    elif args.recent_archives:
        num_months = args.recent_archives if args.recent_archives > 0 else 3
        if num_months > 12:
            num_months = 12
            scraper.logger.warning(f"月数が最大の12に制限されました。num_months=12を使用します。")
        scraper.logger.info(f"最近の{num_months}ヶ月分のアーカイブをスクレイピング")
        all_articles = scraper.scrape_recent_archives(
            num_months, 
            not args.metadata_only, 
            args.start_from_month,
            args.max_articles
        )
    else:
        scraper.logger.info(f"対象: {scraper.base_url}")
        scraper.logger.info(f"スクレイピングするページ数: {args.pages}")
        all_articles = scraper.scrape(args.pages, not args.metadata_only, args.max_articles)
    
    scraper.logger.info(f"リクエスト間の遅延: {args.delay}秒")
    scraper.logger.info(f"モード: {'メタデータのみ' if args.metadata_only else '全文（記事内容を取得）'}")
    if scraper.api_key and not scraper.disable_llm:
        scraper.logger.info(f"URLベースの内容要約にOpenAI APIを使用")
    else:
        scraper.logger.info(f"要約に基本的なテキスト抽出を使用")
    
    scraper.logger.info("-" * 50)
    
    # フィルターを適用（指定されている場合）
    if args.keyword:
        scraper.logger.info(f"キーワードで記事をフィルタリング: '{args.keyword}'")
        all_articles = [a for a in all_articles if args.keyword.lower() in a.get('title', '').lower() or 
                                                  args.keyword.lower() in a.get('content', '').lower()]
        scraper.logger.info(f"キーワード'{args.keyword}'を含む{len(all_articles)}件の記事にフィルタリングしました")
    
    if args.category:
        scraper.logger.info(f"カテゴリで記事をフィルタリング: '{args.category}'")
        all_articles = [a for a in all_articles if args.category.lower() in a.get('custom_category', '').lower()]
        scraper.logger.info(f"カテゴリ'{args.category}'の{len(all_articles)}件の記事にフィルタリングしました")
    
    # ファイルに保存（JSONとCSVの両方）
    output_files = scraper.save_to_file(all_articles, args.output)
    
    if output_files:
        scraper.logger.info("\nスクレイピングが完了しました！")
        scraper.logger.info(f"スクレイピングした記事の総数: {len(all_articles)}")
        scraper.logger.info(f"データの保存先: {', '.join(output_files)}")
        scraper.logger.info(f"合計実行時間: {time.time() - start_time:.2f}秒")
        
        if all_articles:
            scraper.logger.info("\n最初の記事のサンプル:")
            for key in ['title', 'url', 'custom_category']:
                if key in all_articles[0]:
                    scraper.logger.info(f"{key}: {all_articles[0][key]}")
    else:
        scraper.logger.warning("データは保存されませんでした。")

if __name__ == "__main__":
    main()
