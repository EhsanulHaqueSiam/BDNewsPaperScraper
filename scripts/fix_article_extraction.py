#!/usr/bin/env python3
"""
Spider Parse Article Fixer v3 - Direct String Replacement
===========================================================
Simple approach: directly replace the target pattern in all spiders.
"""

from pathlib import Path

SPIDERS_DIR = Path("/home/siam/Personal/BDNewsPaperScraper/BDNewsPaper/spiders")

# All spiders to fix
SPIDERS_TO_FIX = [
    'amadershomoy', 'banglavision', 'bssbangla', 'comillarkagoj',
    'dailyinqilab', 'ctgtimes', 'dbcnews', 'deshrupantor',
    'dhakacourier', 'dwbangla', 'ekattor', 'gramerkagoj', 'narayanganjtimes',
    'manabzamin', 'news24bd', 'rtvonline', 'unbbangla',
    'unb', 'theindependent', 'voabangla',
    'alokitobangladesh', 'bangladeshpost', 'barishaltimes', 'bhorerkagoj',
    'channeli', 'coxsbazarnews', 'dailyasianage', 'dailysangram',
    'dainikbangla', 'dhakapost', 'dhakatimes24', 'ekusheytv',
    'itvbd', 'jagonews24', 'janakantha', 'nayadiganta', 'netrokona24',
    'ntvbd', 'ntvbd_bangla', 'observerbd', 'rajshahipratidin',
    'sangbad', 'sarabangla', 'sylhetmirror', 'techshohor',
]

# What we're looking for (variations)
TARGET_PATTERNS = [
    ('        """Parse individual article page."""\n        url = response.url',
     '''        """Parse individual article page."""
        url = response.url
        
        # ROBUST FALLBACK: Try universal extraction first
        fallback = self.extract_article_fallback(response)
        if fallback and fallback.get('headline') and fallback.get('article_body'):
            if len(fallback.get('article_body', '')) >= 100:
                pub_date = self.parse_article_date(str(fallback.get('publication_date', ''))) if fallback.get('publication_date') else None
                if pub_date and not self.is_date_in_range(pub_date):
                    self.stats['date_filtered'] += 1
                    return
                if not self.filter_by_search_query(fallback['headline'], fallback['article_body']):
                    return
                self.stats['articles_processed'] += 1
                yield self.create_article_item(
                    url=url,
                    headline=fallback['headline'],
                    article_body=fallback['article_body'],
                    author=fallback.get('author') or self.extract_author(response),
                    publication_date=pub_date.isoformat() if pub_date else None,
                    image_url=fallback.get('image_url'),
                    category=response.meta.get('category', 'General'),
                )
                return
        
        # Original extraction'''
    ),
]


def fix_spider(filepath: Path) -> tuple[bool, str]:
    """Add extract_article_fallback using direct string replacement."""
    content = filepath.read_text()
    
    if 'BaseNewsSpider' not in content:
        return False, "Not a BaseNewsSpider"
    
    if 'extract_article_fallback' in content:
        return False, "Already has fallback"
    
    for target, replacement in TARGET_PATTERNS:
        if target in content:
            content = content.replace(target, replacement)
            filepath.write_text(content)
            return True, "Added extract_article_fallback()"
    
    return False, "Pattern not found"


def main():
    print("=" * 70)
    print("Spider Parse Article Fixer v3 (Direct Replacement)")
    print("=" * 70)
    
    fixed = 0
    already = 0
    failed = 0
    
    for spider_name in SPIDERS_TO_FIX:
        filepath = SPIDERS_DIR / f"{spider_name}.py"
        if not filepath.exists():
            print(f"[SKIP] {spider_name}.py not found")
            continue
        
        success, msg = fix_spider(filepath)
        if success:
            print(f"[FIXED] {spider_name}")
            fixed += 1
        elif "Already has fallback" in msg:
            print(f"[OK] {spider_name}")
            already += 1
        else:
            print(f"[----] {spider_name} - {msg}")
            failed += 1
    
    print("=" * 70)
    print(f"Fixed: {fixed}, Already OK: {already}, Failed: {failed}")
    print("=" * 70)


if __name__ == '__main__':
    main()
