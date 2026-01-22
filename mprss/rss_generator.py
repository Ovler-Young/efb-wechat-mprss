"""
RSS feed generator module.
"""

from datetime import datetime
from email.utils import formatdate
from typing import List, Dict, Any
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


def generate_rss_feed(
    mp_name: str,
    mp_signature: str,
    messages: List[Dict[str, Any]],
    feed_url: str = ""
) -> str:
    """
    Generate RSS 2.0 XML feed from messages.
    
    Args:
        mp_name: Name of the public account
        mp_signature: Description/signature of the public account
        messages: List of message dicts with title, description, url, image, pub_date
        feed_url: URL of this RSS feed (for self-reference)
    
    Returns:
        RSS 2.0 XML string
    """
    rss = Element("rss", version="2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    
    channel = SubElement(rss, "channel")
    
    # Channel metadata
    title_el = SubElement(channel, "title")
    title_el.text = mp_name
    
    link_el = SubElement(channel, "link")
    link_el.text = feed_url or "https://mp.weixin.qq.com"
    
    desc_el = SubElement(channel, "description")
    desc_el.text = mp_signature or f"{mp_name} - WeChat Public Account"
    
    lang_el = SubElement(channel, "language")
    lang_el.text = "zh-CN"
    
    # Last build date
    last_build = SubElement(channel, "lastBuildDate")
    last_build.text = formatdate(localtime=True)
    
    # Atom self-link (for RSS best practices)
    if feed_url:
        atom_link = SubElement(channel, "{http://www.w3.org/2005/Atom}link")
        atom_link.set("href", feed_url)
        atom_link.set("rel", "self")
        atom_link.set("type", "application/rss+xml")
    
    # Items
    for msg in messages:
        item = SubElement(channel, "item")
        
        item_title = SubElement(item, "title")
        item_title.text = msg.get("title", "Untitled")
        
        item_link = SubElement(item, "link")
        item_link.text = msg.get("url", "")
        
        item_desc = SubElement(item, "description")
        description = msg.get("description", "")
        image_url = msg.get("image", "")
        
        # Include image in description if available
        if image_url:
            if "telegra.ph" in image_url:
                # Telegraph links are article pages, not direct images
                description = f'<a href="{image_url}">[Telegraph]</a><br/>{description}'
            else:
                description = f'<img src="{image_url}" /><br/>{description}'
        item_desc.text = description
        
        # GUID - use URL as stable identifier
        item_guid = SubElement(item, "guid", isPermaLink="true")
        item_guid.text = msg.get("url", "")
        
        # Pub date
        pub_date = msg.get("pub_date")
        if pub_date:
            item_pubdate = SubElement(item, "pubDate")
            try:
                if isinstance(pub_date, str):
                    dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                elif isinstance(pub_date, datetime):
                    dt = pub_date
                else:
                    dt = datetime.now()
                item_pubdate.text = formatdate(dt.timestamp(), localtime=True)
            except Exception:
                item_pubdate.text = formatdate(localtime=True)
    
    # Pretty print XML
    xml_str = tostring(rss, encoding="unicode")
    dom = minidom.parseString(xml_str)
    return dom.toprettyxml(indent="  ", encoding=None)
