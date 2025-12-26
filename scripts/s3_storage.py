#!/usr/bin/env python3
"""
S3 Cloud Storage
=================
Backup and sync data to AWS S3 or compatible storage.

Supports:
    - AWS S3
    - DigitalOcean Spaces
    - Backblaze B2
    - MinIO

Setup:
    pip install boto3
    export AWS_ACCESS_KEY_ID=your-key
    export AWS_SECRET_ACCESS_KEY=your-secret
    export S3_BUCKET=your-bucket

Usage:
    python s3_storage.py --backup           # Backup database
    python s3_storage.py --sync             # Sync all data
    python s3_storage.py --restore          # Restore from S3
    python s3_storage.py --list             # List backups
"""

import argparse
import os
import gzip
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import json


DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"
DATA_DIR = Path(__file__).parent / "data"
BACKUP_DIR = Path(__file__).parent / "backups"

# S3 Configuration
S3_CONFIG = {
    "bucket": os.getenv("S3_BUCKET", "bdnews-backups"),
    "endpoint_url": os.getenv("S3_ENDPOINT_URL"),  # For non-AWS (DO Spaces, MinIO)
    "region": os.getenv("AWS_REGION", "us-east-1"),
    "access_key": os.getenv("AWS_ACCESS_KEY_ID"),
    "secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
}

# Try to import boto3
try:
    import boto3
    from botocore.exceptions import ClientError
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False


class S3Storage:
    """S3 cloud storage management."""
    
    def __init__(self):
        self.config = S3_CONFIG
        self.client = None
        BACKUP_DIR.mkdir(exist_ok=True)
        
        if S3_AVAILABLE and self.config["access_key"]:
            self._connect()
    
    def _connect(self):
        """Connect to S3."""
        try:
            kwargs = {
                "service_name": "s3",
                "region_name": self.config["region"],
                "aws_access_key_id": self.config["access_key"],
                "aws_secret_access_key": self.config["secret_key"],
            }
            
            if self.config["endpoint_url"]:
                kwargs["endpoint_url"] = self.config["endpoint_url"]
            
            self.client = boto3.client(**kwargs)
            print(f"✅ Connected to S3: {self.config['bucket']}")
        except Exception as e:
            print(f"❌ S3 connection failed: {e}")
    
    @property
    def is_available(self) -> bool:
        return self.client is not None
    
    def compress_file(self, filepath: Path) -> Path:
        """Compress file with gzip."""
        gz_path = BACKUP_DIR / f"{filepath.name}.gz"
        
        with open(filepath, "rb") as f_in:
            with gzip.open(gz_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return gz_path
    
    def backup_database(self) -> Optional[str]:
        """Backup database to S3."""
        if not DB_PATH.exists():
            print("❌ Database not found")
            return None
        
        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"news_articles_{timestamp}.db.gz"
        
        # Compress
        print(f"📦 Compressing database...")
        gz_path = self.compress_file(DB_PATH)
        
        # Upload
        s3_key = f"backups/database/{backup_name}"
        
        if self.is_available:
            try:
                self.client.upload_file(str(gz_path), self.config["bucket"], s3_key)
                print(f"✅ Uploaded: s3://{self.config['bucket']}/{s3_key}")
                
                # Clean local backup
                gz_path.unlink()
                
                return s3_key
            except ClientError as e:
                print(f"❌ Upload failed: {e}")
                return None
        else:
            # Save locally if S3 not configured
            local_backup = BACKUP_DIR / backup_name
            gz_path.rename(local_backup)
            print(f"✅ Local backup: {local_backup}")
            return str(local_backup)
    
    def sync_data(self) -> int:
        """Sync data directory to S3."""
        if not DATA_DIR.exists():
            print("❌ Data directory not found")
            return 0
        
        if not self.is_available:
            print("❌ S3 not configured")
            return 0
        
        uploaded = 0
        
        for filepath in DATA_DIR.rglob("*"):
            if filepath.is_file():
                relative = filepath.relative_to(DATA_DIR)
                s3_key = f"data/{relative}"
                
                try:
                    self.client.upload_file(str(filepath), self.config["bucket"], s3_key)
                    uploaded += 1
                except ClientError as e:
                    print(f"⚠️ Failed: {relative}")
        
        print(f"✅ Synced {uploaded} files to S3")
        return uploaded
    
    def restore_database(self, backup_key: str = None) -> bool:
        """Restore database from S3."""
        if not self.is_available:
            print("❌ S3 not configured")
            return False
        
        try:
            if not backup_key:
                # Get latest backup
                response = self.client.list_objects_v2(
                    Bucket=self.config["bucket"],
                    Prefix="backups/database/"
                )
                
                backups = sorted(
                    [obj["Key"] for obj in response.get("Contents", [])],
                    reverse=True
                )
                
                if not backups:
                    print("❌ No backups found")
                    return False
                
                backup_key = backups[0]
            
            print(f"📥 Downloading: {backup_key}")
            
            # Download
            local_gz = BACKUP_DIR / Path(backup_key).name
            self.client.download_file(self.config["bucket"], backup_key, str(local_gz))
            
            # Decompress
            with gzip.open(local_gz, "rb") as f_in:
                with open(DB_PATH, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            local_gz.unlink()
            print(f"✅ Restored database from {backup_key}")
            return True
            
        except ClientError as e:
            print(f"❌ Restore failed: {e}")
            return False
    
    def list_backups(self) -> List[Dict]:
        """List available backups."""
        if not self.is_available:
            # List local backups
            backups = []
            for f in BACKUP_DIR.glob("*.db.gz"):
                backups.append({
                    "key": str(f),
                    "size": f.stat().st_size,
                    "date": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    "location": "local"
                })
            return backups
        
        try:
            response = self.client.list_objects_v2(
                Bucket=self.config["bucket"],
                Prefix="backups/database/"
            )
            
            backups = []
            for obj in response.get("Contents", []):
                backups.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "date": obj["LastModified"].isoformat(),
                    "location": "s3"
                })
            
            return sorted(backups, key=lambda x: x["date"], reverse=True)
            
        except ClientError as e:
            print(f"❌ Error: {e}")
            return []
    
    def cleanup_old_backups(self, keep: int = 7):
        """Delete old backups, keeping latest N."""
        backups = self.list_backups()
        
        if len(backups) <= keep:
            print(f"ℹ️ Only {len(backups)} backups, nothing to clean")
            return
        
        to_delete = backups[keep:]
        
        for backup in to_delete:
            if backup["location"] == "s3":
                try:
                    self.client.delete_object(Bucket=self.config["bucket"], Key=backup["key"])
                    print(f"🗑️ Deleted: {backup['key']}")
                except ClientError:
                    pass
            else:
                Path(backup["key"]).unlink(missing_ok=True)
        
        print(f"✅ Cleaned {len(to_delete)} old backups")


def main():
    parser = argparse.ArgumentParser(description="S3 cloud storage")
    parser.add_argument("--backup", action="store_true", help="Backup database")
    parser.add_argument("--sync", action="store_true", help="Sync data dir")
    parser.add_argument("--restore", action="store_true", help="Restore latest")
    parser.add_argument("--list", action="store_true", help="List backups")
    parser.add_argument("--cleanup", action="store_true", help="Clean old backups")
    parser.add_argument("--keep", type=int, default=7, help="Backups to keep")
    
    args = parser.parse_args()
    
    storage = S3Storage()
    
    if args.backup:
        storage.backup_database()
    elif args.sync:
        storage.sync_data()
    elif args.restore:
        storage.restore_database()
    elif args.list:
        backups = storage.list_backups()
        print(f"\n📁 Available Backups ({len(backups)}):\n")
        for b in backups[:10]:
            size_mb = b["size"] / 1024 / 1024
            print(f"  {b['date'][:19]} - {size_mb:.1f} MB - {b['location']}")
    elif args.cleanup:
        storage.cleanup_old_backups(args.keep)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
