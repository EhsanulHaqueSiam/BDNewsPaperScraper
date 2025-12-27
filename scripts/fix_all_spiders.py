#!/usr/bin/env python3
"""
Universal Spider Fixer v3
=========================
Applies the proven fallback pattern to ALL spiders.

This script adds:
1. discover_links() fallback after article link extraction fails
2. extract_article_fallback() as first attempt in parse_article
"""

import os
import re
from pathlib import Path

SPIDERS_DIR = Path("/home/siam/Personal/BDNewsPaperScraper/BDNewsPaper/spiders")

# Skip these
SKIP = {'__init__.py', 'base_spider.py', 'smoketest.py', 'auto_spider.py', 'generic_playwright.py'}


def fix_spider(filepath: Path) -> tuple[bool, str]:
    """Fix a single spider file."""
    content = filepath.read_text()
    original = content
    name = filepath.name
    changes = []
    
    if 'BaseNewsSpider' not in content:
        return False, "Not BaseNewsSpider"
    
    # Already fixed?
    if 'discover_links' in content and 'extract_article_fallback' in content:
        return False, "Already fixed"
    
    # FIX 1: Add discover_links fallback
    # Look for: self.logger.info(f"Found {len(...)} articles
    if 'discover_links' not in content:
        pattern = r'(\s+)(self\.logger\.info\(f"Found \{len\(([a-zA-Z_]+)\)\} articles)'
        match = re.search(pattern, content)
        if match:
            indent = match.group(1)
            log_line = match.group(2)
            var_name = match.group(3)
            
            fallback_code = f'''{indent}# ROBUST FALLBACK: Use universal link discovery if selectors fail
{indent}if not {var_name}:
{indent}    self.logger.info("CSS selectors failed, using universal link discovery")
{indent}    {var_name} = self.discover_links(response, limit=50)
{indent}
{indent}{log_line}'''
            
            content = content.replace(f'{indent}{log_line}', fallback_code)
            changes.append("Added discover_links() fallback")
    
    # FIX 2: Add extract_article_fallback to parse_article
    if 'extract_article_fallback' not in content:
        # Find: def parse_article(self, response...): 
        # Then add fallback block after docstring
        pattern = r'(def parse_article\(self, response[^)]*\):[^\n]*\n\s+"""[^"]*"""\n)(\s+)'
        match = re.search(pattern, content)
        
        if match:
            method_with_docstring = match.group(1)
            indent = match.group(2)
            
            fallback_block = f'''{method_with_docstring}{indent}# ROBUST FALLBACK: Try universal extraction first
{indent}fallback = self.extract_article_fallback(response)
{indent}if fallback and fallback.get('headline') and fallback.get('article_body'):
{indent}    if len(fallback.get('article_body', '')) >= 100:
{indent}        pub_date = self.parse_article_date(str(fallback.get('publication_date', ''))) if fallback.get('publication_date') else None
{indent}        if pub_date and not self.is_date_in_range(pub_date):
{indent}            self.stats['date_filtered'] += 1
{indent}            return
{indent}        if not self.filter_by_search_query(fallback['headline'], fallback['article_body']):
{indent}            return
{indent}        self.stats['articles_processed'] += 1
{indent}        yield self.create_article_item(
{indent}            url=response.url,
{indent}            headline=fallback['headline'],
{indent}            article_body=fallback['article_body'],
{indent}            author=fallback.get('author') or self.extract_author(response),
{indent}            publication_date=pub_date.isoformat() if pub_date else None,
{indent}            image_url=fallback.get('image_url'),
{indent}            category=response.meta.get('category', 'General'),
{indent}        )
{indent}        return

{indent}# Original CSS extraction (fallback)
{indent}'''
            
            content = content.replace(method_with_docstring + indent, fallback_block)
            changes.append("Added extract_article_fallback()")
        else:
            # Try without docstring
            pattern2 = r'(def parse_article\(self, response[^)]*\):[^\n]*\n)(\s+)(url\s*=|#)'
            match2 = re.search(pattern2, content)
            if match2:
                method_def = match2.group(1)
                indent = match2.group(2)
                first_line = match2.group(3)
                
                fallback_block = f'''{method_def}{indent}# ROBUST FALLBACK: Try universal extraction first
{indent}fallback = self.extract_article_fallback(response)
{indent}if fallback and fallback.get('headline') and fallback.get('article_body'):
{indent}    if len(fallback.get('article_body', '')) >= 100:
{indent}        pub_date = self.parse_article_date(str(fallback.get('publication_date', ''))) if fallback.get('publication_date') else None
{indent}        if pub_date and not self.is_date_in_range(pub_date):
{indent}            self.stats['date_filtered'] += 1
{indent}            return
{indent}        if not self.filter_by_search_query(fallback['headline'], fallback['article_body']):
{indent}            return
{indent}        self.stats['articles_processed'] += 1
{indent}        yield self.create_article_item(
{indent}            url=response.url,
{indent}            headline=fallback['headline'],
{indent}            article_body=fallback['article_body'],
{indent}            author=fallback.get('author') or self.extract_author(response),
{indent}            publication_date=pub_date.isoformat() if pub_date else None,
{indent}            image_url=fallback.get('image_url'),
{indent}            category=response.meta.get('category', 'General'),
{indent}        )
{indent}        return

{indent}# Original CSS extraction
{indent}{first_line}'''
                
                content = content.replace(method_def + indent + first_line, fallback_block)
                changes.append("Added extract_article_fallback()")
    
    if content != original:
        filepath.write_text(content)
        return True, ", ".join(changes)
    
    return False, "No pattern matched"


def main():
    print("=" * 70)
    print("Universal Spider Fixer v3")
    print("=" * 70)
    
    fixed = 0
    skipped = 0
    already = 0
    failed = 0
    
    for f in sorted(SPIDERS_DIR.glob('*.py')):
        if f.name in SKIP:
            print(f"[SKIP] {f.name}")
            skipped += 1
            continue
        
        try:
            success, msg = fix_spider(f)
            if success:
                print(f"[FIXED] {f.name} - {msg}")
                fixed += 1
            elif "Already fixed" in msg:
                print(f"[OK] {f.name} - {msg}")
                already += 1
            else:
                print(f"[----] {f.name} - {msg}")
                failed += 1
        except Exception as e:
            print(f"[ERROR] {f.name} - {e}")
            failed += 1
    
    print("=" * 70)
    print(f"Fixed: {fixed}, Already OK: {already}, Skipped: {skipped}, No match: {failed}")
    print("=" * 70)


if __name__ == '__main__':
    main()
