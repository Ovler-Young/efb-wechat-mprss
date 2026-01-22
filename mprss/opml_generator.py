"""
OPML generator module for exporting all RSS feeds.
"""

from collections import defaultdict
from typing import List, Dict, Any, Optional
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime


def generate_opml(
    mps: List[Dict[str, Any]],
    base_url: str,
    title: str = "WeChat MP RSS Feeds",
    groups: Optional[Dict[str, str]] = None
) -> str:
    """
    Generate OPML 2.0 XML for all public accounts.
    
    Args:
        mps: List of MP dicts with puid, name, signature
        base_url: Base URL for RSS feeds (e.g., http://localhost:8080)
        title: Title for the OPML document
        groups: Optional dict mapping puid -> tag name for grouping
    
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
    
    # Group MPs by tag
    if groups:
        tag_to_mps: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for mp in mps:
            puid = mp.get("puid", "")
            tag = groups.get(puid, "All")
            tag_to_mps[tag].append(mp)
        
        # Ensure "All" is last if it exists
        tag_order = [t for t in tag_to_mps.keys() if t != "All"]
        if "All" in tag_to_mps:
            tag_order.append("All")
        
        # Create grouped outlines
        for tag in tag_order:
            group_outline = SubElement(body, "outline")
            group_outline.set("text", tag)
            
            for mp in tag_to_mps[tag]:
                _add_mp_outline(group_outline, mp, base_url)
    else:
        # No grouping - flat structure
        for mp in mps:
            _add_mp_outline(body, mp, base_url)
    
    # Pretty print XML
    xml_str = tostring(opml, encoding="unicode")
    dom = minidom.parseString(xml_str)
    return dom.toprettyxml(indent="  ", encoding=None)


def _add_mp_outline(parent: Element, mp: Dict[str, Any], base_url: str) -> None:
    """Add a single MP outline element to parent."""
    puid = mp.get("puid", "")
    name = mp.get("name", "Unknown")
    signature = mp.get("signature", "")
    
    feed_url = f"{base_url}/api/rss/{puid}"
    
    outline = SubElement(parent, "outline")
    outline.set("type", "rss")
    outline.set("text", name)
    outline.set("title", name)
    outline.set("description", signature)
    outline.set("xmlUrl", feed_url)
    outline.set("htmlUrl", "https://mp.weixin.qq.com")
