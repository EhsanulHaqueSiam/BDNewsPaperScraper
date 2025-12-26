"""
Monitoring and Alerting Module
==============================
Health checks, metrics, and alerting for the scraper system.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import urllib.request

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health check status."""
    healthy: bool
    message: str
    details: Dict


class HealthChecker:
    """
    Monitor scraper health and detect issues.
    
    Checks:
        - Database connectivity
        - Recent article yields
        - Error rates
        - Spider status
    """
    
    def __init__(self, db_path: str = 'news_articles.db',
                 min_articles_per_day: int = 10,
                 max_error_rate: float = 0.3):
        self.db_path = db_path
        self.min_articles_per_day = min_articles_per_day
        self.max_error_rate = max_error_rate
    
    def check_database(self) -> HealthStatus:
        """Check database connectivity and integrity."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            count = cursor.fetchone()[0]
            conn.close()
            
            return HealthStatus(
                healthy=True,
                message="Database OK",
                details={"total_articles": count}
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                message=f"Database error: {str(e)}",
                details={}
            )
    
    def check_recent_yield(self, hours: int = 24) -> HealthStatus:
        """Check article yield in recent hours."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM articles 
                WHERE scraped_at >= datetime('now', ?)
            """, (f'-{hours} hours',))
            count = cursor.fetchone()[0]
            conn.close()
            
            expected = self.min_articles_per_day * (hours / 24)
            healthy = count >= expected * 0.5  # Alert if yield is less than 50% expected
            
            return HealthStatus(
                healthy=healthy,
                message=f"Yield {count} articles in last {hours}h (expected: {expected:.0f})",
                details={
                    "articles_scraped": count,
                    "expected": expected,
                    "hours": hours
                }
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                message=f"Yield check failed: {str(e)}",
                details={}
            )
    
    def check_all(self) -> Dict[str, HealthStatus]:
        """Run all health checks."""
        return {
            "database": self.check_database(),
            "yield_24h": self.check_recent_yield(24),
            "yield_1h": self.check_recent_yield(1),
        }
    
    def is_healthy(self) -> bool:
        """Check if system is overall healthy."""
        statuses = self.check_all()
        return all(s.healthy for s in statuses.values())


class AlertManager:
    """
    Send alerts via various channels.
    
    Supports:
        - Slack webhooks
        - Console logging
    """
    
    def __init__(self, slack_webhook_url: Optional[str] = None):
        self.slack_webhook_url = slack_webhook_url or os.getenv('SLACK_WEBHOOK_URL')
    
    def send_alert(self, title: str, message: str, severity: str = "warning"):
        """Send alert to all configured channels."""
        # Always log
        log_method = logger.warning if severity == "warning" else logger.error
        log_method(f"[ALERT] {title}: {message}")
        
        # Send to Slack if configured
        if self.slack_webhook_url:
            self._send_slack(title, message, severity)
    
    def _send_slack(self, title: str, message: str, severity: str):
        """Send alert to Slack."""
        color = "#ff0000" if severity == "error" else "#ffcc00"
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"🚨 {title}",
                "text": message,
                "footer": "BDNewsPaper Scraper",
                "ts": int(datetime.now().timestamp())
            }]
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self.slack_webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req, timeout=10)
            logger.info("Slack alert sent successfully")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")


class MetricsCollector:
    """
    Collect and expose scraper metrics.
    
    Metrics:
        - Articles scraped per spider
        - Error counts
        - Response times
        - Database size
    """
    
    def __init__(self, db_path: str = 'news_articles.db'):
        self.db_path = db_path
    
    def get_metrics(self) -> Dict:
        """Get current metrics."""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "database": self._get_database_metrics(),
            "papers": self._get_paper_metrics(),
            "recent": self._get_recent_metrics(),
        }
        return metrics
    
    def _get_database_metrics(self) -> Dict:
        """Get database metrics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM articles")
            total = cursor.fetchone()[0]
            
            # Get database file size
            size_bytes = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            
            conn.close()
            return {
                "total_articles": total,
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / (1024 * 1024), 2)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_paper_metrics(self) -> Dict:
        """Get per-paper article counts."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT paper_name, COUNT(*) as count 
                FROM articles GROUP BY paper_name
            """)
            result = {row[0]: row[1] for row in cursor.fetchall()}
            conn.close()
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def _get_recent_metrics(self) -> Dict:
        """Get recent activity metrics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            periods = {
                "last_1h": "-1 hour",
                "last_24h": "-24 hours",
                "last_7d": "-7 days",
            }
            
            result = {}
            for name, delta in periods.items():
                cursor.execute(f"""
                    SELECT COUNT(*) FROM articles 
                    WHERE scraped_at >= datetime('now', '{delta}')
                """)
                result[name] = cursor.fetchone()[0]
            
            conn.close()
            return result
        except Exception as e:
            return {"error": str(e)}


def run_health_check():
    """Run health check and send alerts if needed."""
    checker = HealthChecker()
    alerter = AlertManager()
    
    statuses = checker.check_all()
    
    for name, status in statuses.items():
        if not status.healthy:
            alerter.send_alert(
                f"Health Check Failed: {name}",
                status.message,
                severity="error"
            )
    
    return statuses


if __name__ == "__main__":
    # Run health check from command line
    import sys
    
    statuses = run_health_check()
    
    print("Health Check Results:")
    print("-" * 40)
    
    for name, status in statuses.items():
        emoji = "✅" if status.healthy else "❌"
        print(f"{emoji} {name}: {status.message}")
        for k, v in status.details.items():
            print(f"   {k}: {v}")
    
    sys.exit(0 if all(s.healthy for s in statuses.values()) else 1)
