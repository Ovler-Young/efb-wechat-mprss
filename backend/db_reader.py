"""
Database reader module for querying tgdata.db.
"""

import pickle
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


def get_messages_for_mp(
    db_path: str,
    puid: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get messages for a specific public account from tgdata.db.
    
    Args:
        db_path: Path to tgdata.db
        puid: The puid of the public account
        limit: Maximum number of messages to return
    
    Returns:
        List of message dicts with title, description, url, image, pub_date.
    """
    slave_origin_uid = f"blueset.wechat {puid}"
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Query messages of type 'Link' for this MP
    cursor.execute(
        """
        SELECT slave_message_id, text, pickle, time, msg_type
        FROM msglog
        WHERE slave_origin_uid = ?
          AND msg_type = 'Link'
        ORDER BY time DESC
        LIMIT ?
        """,
        (slave_origin_uid, limit)
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    seen_urls = set()
    
    for row in rows:
        msg = parse_message_row(row)
        if msg and msg.get("url"):
            url = msg["url"].replace("http://", "https://")
            # Only include mp.weixin.qq.com links, http or https
            if not url.startswith("https://mp.weixin.qq.com"):
                continue
            # Deduplicate by URL
            if url not in seen_urls:
                seen_urls.add(url)
                result.append(msg)
    
    return result


def parse_message_row(row: sqlite3.Row) -> Optional[Dict[str, Any]]:
    """
    Parse a message row from the database.
    
    Extracts LinkAttribute from the pickle field.
    """
    pickle_data = row["pickle"]
    pub_date = row["time"]
    
    if not pickle_data:
        return None
    
    try:
        data = pickle.loads(pickle_data)
    except Exception:
        return None
    
    attributes = data.get("attributes")
    if not attributes:
        return None
    
    # LinkAttribute has: title, description, url, image
    title = getattr(attributes, "title", None) or ""
    description = getattr(attributes, "description", None) or ""
    url = getattr(attributes, "url", None) or ""
    image = getattr(attributes, "image", None) or ""
    
    return {
        "title": title,
        "description": description,
        "url": url,
        "image": image,
        "pub_date": pub_date,
    }


def get_mp_message_count(db_path: str, puid: str) -> int:
    """Get the count of Link messages for a public account."""
    slave_origin_uid = f"blueset.wechat {puid}"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT COUNT(*) FROM msglog
        WHERE slave_origin_uid = ?
          AND msg_type = 'Link'
        """,
        (slave_origin_uid,)
    )
    
    count = cursor.fetchone()[0]
    conn.close()
    
    return count


def has_articles_for_mp(db_path: str, puid: str) -> bool:
    """
    Check if a public account has any Link messages.
    
    Uses EXISTS for efficiency - stops as soon as one row is found.
    """
    slave_origin_uid = f"blueset.wechat {puid}"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT EXISTS(
            SELECT 1 FROM msglog
            WHERE slave_origin_uid = ?
              AND msg_type = 'Link'
            LIMIT 1
        )
        """,
        (slave_origin_uid,)
    )
    
    has_articles = cursor.fetchone()[0] == 1
    conn.close()
    
    return has_articles


if __name__ == "__main__":
    # Quick test
    import yaml
    
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # Test with a known puid
    test_puid = "2a44d45d"
    messages = get_messages_for_mp(config["tgdata_db_path"], test_puid, limit=5)
    
    print(f"Found {len(messages)} messages for puid {test_puid}:")
    for msg in messages:
        print(f"  - {msg['title'][:50]}... ({msg['pub_date']})")
