#!/usr/bin/env python3
"""
Scheduled Email Reports
========================
Auto-generate and send PDF/HTML news reports via email.

Features:
    - Daily/weekly summary reports
    - PDF generation with charts
    - HTML email with styling
    - Configurable via environment or .env

Setup:
    export EMAIL_SENDER=your@email.com
    export EMAIL_PASSWORD=your-app-password
    export EMAIL_RECIPIENTS=recipient@email.com
    export SMTP_HOST=smtp.gmail.com
    export SMTP_PORT=587

Usage:
    python email_reports.py --send           # Send today's report
    python email_reports.py --weekly         # Send weekly summary
    python email_reports.py --preview        # Preview without sending
    python email_reports.py --schedule       # Run scheduled (daily)
"""

import argparse
import os
import sqlite3
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter
import io

DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"
REPORTS_DIR = Path(__file__).parent / "reports"

# Email configuration from environment
EMAIL_CONFIG = {
    "sender": os.getenv("EMAIL_SENDER", ""),
    "password": os.getenv("EMAIL_PASSWORD", ""),
    "recipients": os.getenv("EMAIL_RECIPIENTS", "").split(","),
    "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", "587")),
}


class EmailReporter:
    """Generate and send email reports."""
    
    def __init__(self):
        self.config = EMAIL_CONFIG
        REPORTS_DIR.mkdir(exist_ok=True)
    
    def get_summary(self, days: int = 1) -> Dict:
        """Get news summary for specified days."""
        if not DB_PATH.exists():
            return {"error": "Database not found"}
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Total articles
        total = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE scraped_at >= ?", (cutoff,)
        ).fetchone()[0]
        
        # By paper
        by_paper = {
            row["paper_name"]: row["count"]
            for row in conn.execute("""
                SELECT paper_name, COUNT(*) as count 
                FROM articles WHERE scraped_at >= ?
                GROUP BY paper_name ORDER BY count DESC
            """, (cutoff,)).fetchall()
        }
        
        # By category
        by_category = {
            row["category"]: row["count"]
            for row in conn.execute("""
                SELECT category, COUNT(*) as count 
                FROM articles WHERE scraped_at >= ? AND category IS NOT NULL
                GROUP BY category ORDER BY count DESC LIMIT 10
            """, (cutoff,)).fetchall()
        }
        
        # Top headlines
        headlines = [
            dict(row) for row in conn.execute("""
                SELECT headline, paper_name, url, category
                FROM articles WHERE scraped_at >= ?
                ORDER BY scraped_at DESC LIMIT 20
            """, (cutoff,)).fetchall()
        ]
        
        conn.close()
        
        return {
            "period": f"Last {days} day(s)",
            "generated_at": datetime.now().isoformat(),
            "total_articles": total,
            "by_paper": by_paper,
            "by_category": by_category,
            "top_headlines": headlines
        }
    
    def generate_html_report(self, summary: Dict) -> str:
        """Generate HTML email content."""
        period = summary.get("period", "Today")
        total = summary.get("total_articles", 0)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .header p {{ margin: 10px 0 0; opacity: 0.9; }}
        .content {{ padding: 20px; }}
        .stats {{ display: flex; justify-content: space-around; text-align: center; padding: 20px; background: #f8f9fa; }}
        .stat {{ }}
        .stat-number {{ font-size: 28px; font-weight: bold; color: #667eea; }}
        .stat-label {{ font-size: 12px; color: #666; }}
        .section {{ margin: 20px 0; }}
        .section h2 {{ font-size: 18px; color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
        .paper-list {{ list-style: none; padding: 0; }}
        .paper-list li {{ padding: 8px 0; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; }}
        .headline {{ padding: 15px; background: #f8f9fa; border-radius: 8px; margin: 10px 0; }}
        .headline a {{ color: #333; text-decoration: none; font-weight: 500; }}
        .headline a:hover {{ color: #667eea; }}
        .headline .meta {{ font-size: 12px; color: #666; margin-top: 5px; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; background: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗞️ BD News Report</h1>
            <p>{period} | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-number">{total:,}</div>
                <div class="stat-label">Total Articles</div>
            </div>
            <div class="stat">
                <div class="stat-number">{len(summary.get('by_paper', {}))}</div>
                <div class="stat-label">Newspapers</div>
            </div>
            <div class="stat">
                <div class="stat-number">{len(summary.get('by_category', {}))}</div>
                <div class="stat-label">Categories</div>
            </div>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>📰 By Newspaper</h2>
                <ul class="paper-list">
"""
        
        for paper, count in list(summary.get("by_paper", {}).items())[:10]:
            html += f'<li><span>{paper}</span><span><strong>{count}</strong></span></li>\n'
        
        html += """
                </ul>
            </div>
            
            <div class="section">
                <h2>📌 Top Headlines</h2>
"""
        
        for h in summary.get("top_headlines", [])[:10]:
            html += f"""
                <div class="headline">
                    <a href="{h['url']}">{h['headline'][:100]}{'...' if len(h['headline']) > 100 else ''}</a>
                    <div class="meta">📰 {h['paper_name']} | 📁 {h.get('category', 'N/A')}</div>
                </div>
"""
        
        html += """
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by <a href="https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper">BDNewsPaperScraper</a></p>
            <p>Unsubscribe by removing your email from EMAIL_RECIPIENTS</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def send_email(self, subject: str, html_content: str, pdf_path: str = None) -> bool:
        """Send email with optional PDF attachment."""
        if not self.config["sender"] or not self.config["password"]:
            print("❌ Email credentials not configured!")
            print("   Set EMAIL_SENDER and EMAIL_PASSWORD environment variables")
            return False
        
        recipients = [r.strip() for r in self.config["recipients"] if r.strip()]
        if not recipients:
            print("❌ No recipients configured!")
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.config["sender"]
            msg["To"] = ", ".join(recipients)
            
            # Text version
            text = f"View this email in HTML format\n\n{subject}"
            msg.attach(MIMEText(text, "plain"))
            
            # HTML version
            msg.attach(MIMEText(html_content, "html"))
            
            # PDF attachment
            if pdf_path and Path(pdf_path).exists():
                with open(pdf_path, "rb") as f:
                    attachment = MIMEBase("application", "pdf")
                    attachment.set_payload(f.read())
                    encoders.encode_base64(attachment)
                    attachment.add_header(
                        "Content-Disposition",
                        f"attachment; filename={Path(pdf_path).name}"
                    )
                    msg.attach(attachment)
            
            # Send
            with smtplib.SMTP(self.config["smtp_host"], self.config["smtp_port"]) as server:
                server.starttls()
                server.login(self.config["sender"], self.config["password"])
                server.sendmail(self.config["sender"], recipients, msg.as_string())
            
            print(f"✅ Email sent to {len(recipients)} recipient(s)")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False
    
    def send_daily_report(self) -> bool:
        """Send daily news report."""
        summary = self.get_summary(days=1)
        
        if "error" in summary:
            print(f"❌ {summary['error']}")
            return False
        
        if summary["total_articles"] == 0:
            print("ℹ️ No articles to report")
            return False
        
        html = self.generate_html_report(summary)
        subject = f"🗞️ BD News Daily Report - {datetime.now().strftime('%B %d, %Y')}"
        
        return self.send_email(subject, html)
    
    def send_weekly_report(self) -> bool:
        """Send weekly summary report."""
        summary = self.get_summary(days=7)
        
        if "error" in summary:
            print(f"❌ {summary['error']}")
            return False
        
        html = self.generate_html_report(summary)
        subject = f"🗞️ BD News Weekly Report - Week of {(datetime.now() - timedelta(days=7)).strftime('%B %d')}"
        
        return self.send_email(subject, html)
    
    def preview_report(self, days: int = 1) -> str:
        """Preview report without sending."""
        summary = self.get_summary(days=days)
        html = self.generate_html_report(summary)
        
        # Save preview
        preview_path = REPORTS_DIR / f"preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        preview_path.write_text(html)
        
        print(f"📄 Preview saved: {preview_path}")
        return str(preview_path)
    
    def run_scheduled(self, interval_hours: int = 24):
        """Run as scheduled service."""
        print(f"📅 Running scheduled email reports every {interval_hours} hours")
        print("   Press Ctrl+C to stop")
        
        while True:
            try:
                self.send_daily_report()
                print(f"💤 Sleeping for {interval_hours} hours...")
                time.sleep(interval_hours * 3600)
            except KeyboardInterrupt:
                print("\n👋 Stopping scheduler")
                break


def main():
    parser = argparse.ArgumentParser(description="Email news reports")
    parser.add_argument("--send", action="store_true", help="Send daily report")
    parser.add_argument("--weekly", action="store_true", help="Send weekly report")
    parser.add_argument("--preview", action="store_true", help="Preview report")
    parser.add_argument("--days", type=int, default=1, help="Days to include")
    parser.add_argument("--schedule", action="store_true", help="Run scheduled")
    parser.add_argument("--interval", type=int, default=24, help="Schedule interval (hours)")
    
    args = parser.parse_args()
    
    reporter = EmailReporter()
    
    if args.send:
        reporter.send_daily_report()
    elif args.weekly:
        reporter.send_weekly_report()
    elif args.preview:
        reporter.preview_report(args.days)
    elif args.schedule:
        reporter.run_scheduled(args.interval)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
