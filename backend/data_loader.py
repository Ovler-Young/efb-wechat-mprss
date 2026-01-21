"""
Data loader module for loading wxpy.pkl and wxpy_puid.pkl files.

Note: Since the pickle files reference efb_wechat_slave module classes,
we use the pre-extracted JSON files instead.
"""

import json
from pathlib import Path
from typing import List, Dict, Any


def load_json(path: str) -> Any:
    """Load a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_mp_list(wxpy_pkl_path: str) -> List[Dict[str, Any]]:
    """
    Extract mpList (public accounts) from wxpy extracted JSON.
    
    Uses the pre-extracted JSON file (wxpy_extracted.json) instead of pkl
    to avoid module dependency issues.
    
    Returns:
        List of MP dicts with UserName, NickName, Signature, HeadImgUrl, etc.
    """
    # Try to use the extracted JSON file instead
    json_path = Path(wxpy_pkl_path).with_name("wxpy_extracted.json")
    
    if json_path.exists():
        data = load_json(str(json_path))
    else:
        raise FileNotFoundError(
            f"JSON file not found: {json_path}. "
            f"Please run extract_pkl.py to generate it."
        )
    
    # The JSON file has a 'storage' key with 'mpList'
    storage = data.get("storage", {})
    mp_list = storage.get("mpList", [])
    
    return mp_list


def get_puid_map(wxpy_puid_pkl_path: str) -> Dict[str, str]:
    """
    Extract puid_map from wxpy_puid extracted JSON.
    
    The JSON structure is:
    [{"__type__": "TwoWayDict", "__dict__": {"data": {UserName: puid, ...}}}]
    
    Returns:
        Dict mapping UserName to puid.
    """
    # Try to use the extracted JSON file instead
    json_path = Path(wxpy_puid_pkl_path).with_name("wxpy_puid_extracted.json")
    
    if json_path.exists():
        data = load_json(str(json_path))
    else:
        raise FileNotFoundError(
            f"JSON file not found: {json_path}. "
            f"Please run extract_pkl.py to generate it."
        )
    
    # Handle the TwoWayDict structure: [{__type__, __dict__: {data: {...}}}]
    if isinstance(data, list) and len(data) > 0:
        first_item = data[0]
        if isinstance(first_item, dict) and "__dict__" in first_item:
            puid_map = first_item["__dict__"].get("data", {})
            return puid_map
    
    # Fallback: try to get 'puid_map' key directly
    if isinstance(data, dict):
        return data.get("puid_map", {})
    
    return {}


def get_mps_with_puid(
    wxpy_pkl_path: str,
    wxpy_puid_pkl_path: str
) -> List[Dict[str, Any]]:
    """
    Get all public accounts with their puid mapped.
    
    Returns:
        List of dicts with puid, name, signature, head_img.
    """
    mp_list = get_mp_list(wxpy_pkl_path)
    puid_map = get_puid_map(wxpy_puid_pkl_path)
    
    result = []
    for mp in mp_list:
        user_name = mp.get("UserName", "")
        puid = puid_map.get(user_name)
        
        if not puid:
            # Skip MPs without puid mapping
            continue
        
        result.append({
            "puid": puid,
            "name": mp.get("NickName", ""),
            "signature": mp.get("Signature", ""),
            "head_img": mp.get("HeadImgUrl", ""),
        })
    
    return result


if __name__ == "__main__":
    # Quick test
    import yaml
    
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    mps = get_mps_with_puid(
        config["wxpy_pkl_path"],
        config["wxpy_puid_pkl_path"]
    )
    
    print(f"Found {len(mps)} public accounts with puid:")
    for mp in mps[:5]:
        print(f"  - {mp['name']} ({mp['puid']})")
