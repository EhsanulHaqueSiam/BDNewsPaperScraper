#!/usr/bin/env python3
"""
Spider Batch Updater
====================
Adds robust fallback patterns to all spiders.

This script:
1. Finds all spiders inheriting from BaseNewsSpider
2. Adds fallback to parse_category/parse methods if not present
3. Adds fallback to parse_article methods if not present
"""

import os
import re
import sys

SPIDERS_DIR = "/home/siam/Personal/BDNewsPaperScraper/BDNewsPaper/spiders"

# Skip these spiders (already working or special)
SKIP_SPIDERS = {
    '__init__.py',
    'base_spider.py',
    'smoketest.py',
    'generic_playwright.py',
    'prothomalo.py',  # Working
    'ittefaq.py',      # Working
    'jugantor.py',     # Working  
    'thedailystar.py', # Working
    'newage.py',       # Working
    'financialexpress.py',  # Working
    'bdnews24.py',     # Working
    'khulnagazette.py',  # Working
    'bd24live.py',     # Working
    'channeli.py',     # Working
    'BDpratidin.py',   # Working
    'tbsnews.py',      # Working
    'banglatribune.py',  # Already updated
}

def add_fallback_to_spider(filepath):
    """Add fallback patterns to a spider file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    modified = False
    spider_name = os.path.basename(filepath)
    
    # Check if spider uses BaseNewsSpider
    if 'BaseNewsSpider' not in content:
        print(f"  Skipping {spider_name} - doesn't use BaseNewsSpider")
        return False
    
    # Check if already has fallback
    if 'discover_links' in content or 'extract_article_fallback' in content:
        print(f"  Skipping {spider_name} - already has fallback")
        return False
    
    # Pattern 1: Add fallback to parse methods that find article links
    # Look for patterns like: article_links = response.css(...).getall()
    link_patterns = [
        r'(article_links\s*=\s*response\.css\([^)]+\)\.getall\(\))',
        r'(links\s*=\s*response\.css\([^)]+\)\.getall\(\))',
        r'(article_urls\s*=\s*response\.css\([^)]+\)\.getall\(\))',
    ]
    
    for pattern in link_patterns:
        matches = list(re.finditer(pattern, content))
        for match in matches:
            original = match.group(1)
            # Get variable name
            var_name = original.split('=')[0].strip()
            
            # Create fallback code
            fallback_code = f'''{original}
        
        # ROBUST FALLBACK: Use universal link discovery if selectors fail
        if not {var_name}:
            self.logger.info(f"CSS selectors failed, using universal link discovery")
            {var_name} = self.discover_links(response, limit=50)'''
            
            if fallback_code not in content:
                content = content.replace(original, fallback_code)
                modified = True
                print(f"  Added link discovery fallback to {spider_name}")
                break
        if modified:
            break
    
    # Pattern 2: Add extract_article_fallback to parse_article methods
    # Look for: def parse_article(self, response)
    if 'def parse_article' in content and 'extract_article_fallback' not in content:
        # Find the parse_article method and add fallback at the start
        parse_article_pattern = r'(def parse_article\(self, response[^)]*\)[^:]*:)\s*\n(\s+)(["\']|#|url\s*=|if|try)'
        
        match = re.search(parse_article_pattern, content)
        if match:
            method_def = match.group(1)
            indent = match.group(2)
            first_line = match.group(3)
            
            # Check what the first line is
            if first_line in ['"', "'"]:
                # It's a docstring, skip past it
                pass  # Complex case, skip for now
            else:
                fallback_insert = f'''
{indent}# ROBUST FALLBACK: Try universal extraction first
{indent}fallback_result = self.extract_article_fallback(response)
{indent}if fallback_result and fallback_result.get('headline') and fallback_result.get('article_body'):
{indent}    if len(fallback_result.get('article_body', '')) >= 100:
{indent}        yield self.create_article_item(
{indent}            url=response.url,
{indent}            headline=fallback_result['headline'],
{indent}            article_body=fallback_result['article_body'],
{indent}            author=fallback_result.get('author') or self.extract_author(response),
{indent}            publication_date=fallback_result.get('publication_date'),
{indent}            image_url=fallback_result.get('image_url'),
{indent}            category=response.meta.get('category', 'General'),
{indent}        )
{indent}        return
{indent}
{indent}# Original parsing logic below
'''
                replacement = f'{method_def}\n{indent}{first_line}'
                new_content = content.replace(
                    f'{method_def}\n{indent}{first_line}',
                    f'{method_def}{fallback_insert}{first_line}'
                )
                if new_content != content:
                    content = new_content
                    modified = True
                    print(f"  Added article extraction fallback to {spider_name}")
    
    if modified:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    
    return False


def main():
    """Process all spider files."""
    print("=" * 60)
    print("Spider Batch Updater - Adding Robust Fallbacks")
    print("=" * 60)
    
    updated = 0
    skipped = 0
    errors = 0
    
    for filename in sorted(os.listdir(SPIDERS_DIR)):
        if not filename.endswith('.py'):
            continue
        
        if filename in SKIP_SPIDERS:
            print(f"[SKIP] {filename}")
            skipped += 1
            continue
        
        filepath = os.path.join(SPIDERS_DIR, filename)
        print(f"[CHECK] {filename}")
        
        try:
            if add_fallback_to_spider(filepath):
                updated += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1
    
    print("=" * 60)
    print(f"SUMMARY: Updated={updated}, Skipped={skipped}, Errors={errors}")
    print("=" * 60)


if __name__ == '__main__':
    main()
