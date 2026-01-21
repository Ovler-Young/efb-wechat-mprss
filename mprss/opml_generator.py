"""
OPML generator module for exporting all RSS feeds.
"""

from typing import List, Dict, Any
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime


def generate_opml(
    mps: List[Dict[str, Any]],
    base_url: str,
    title: str = "WeChat MP RSS Feeds"
) -> str:
    """
    Generate OPML 2.0 XML for all public accounts.
    
    Args:
        mps: List of MP dicts with puid, name, signature
        base_url: Base URL for RSS feeds (e.g., http://localhost:8080)
        title: Title for the OPML document
    
    Returns:
        OPML 2.0 XML string
    """
    opml = Element("opml", version="2.0")
    
    # Head section
    head = SubElement(opml, "head")
    
    title_el = SubElement(head, "title")
    title_el.text = title
    
    date_created = SubElement(head, "dateCreated")
    date_created.text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z").strip()
    
    # Body section
    body = SubElement(opml, "body")
    
    # Create outline for each MP
    for mp in mps:
        puid = mp.get("puid", "")
        name = mp.get("name", "Unknown")
        signature = mp.get("signature", "")
        
        feed_url = f"{base_url}/api/rss/{puid}"
        
        outline = SubElement(body, "outline")
        outline.set("type", "rss")
        outline.set("text", name)
        outline.set("title", name)
        outline.set("description", signature)
        outline.set("xmlUrl", feed_url)
        outline.set("htmlUrl", "https://mp.weixin.qq.com")
    
    # Pretty print XML
    xml_str = tostring(opml, encoding="unicode")
    dom = minidom.parseString(xml_str)
    return dom.toprettyxml(indent="  ", encoding=None)
