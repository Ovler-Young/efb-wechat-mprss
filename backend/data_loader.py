"""
Data loader module for loading wxpy.pkl and wxpy_puid.pkl files.

Since efb_wechat_slave module is available in the runtime environment,
we can directly load the pickle files.
"""

import pickle
from pathlib import Path
from typing import Any, Dict, List


def _fix_pickle_module_path(path: str) -> bytes:
    """
    Fix pickle module path migration issues.
    
    Older pickle files may reference:
    - efb_wechat_slave.wxpy.utils.puid_map
    - itchat.storage.templates
    
    Newer ones reference:
    - efb_wechat_slave.vendor.wxpy.utils.puid_map
    - efb_wechat_slave.vendor.itchat.storage.templates
    
    This function patches the binary content to use the newer module paths.
    """
    with open(path, "rb") as f:
        data = f.read()
    
    # Fix wxpy module path
    data = data.replace(
        b"cefb_wechat_slave.wxpy.",
        b"cefb_wechat_slave.vendor.wxpy."
    )
    # Fix itchat module path
    data = data.replace(
        b"citchat.",
        b"cefb_wechat_slave.vendor.itchat."
    )
    
    return data


def load_wxpy_pkl(path: str) -> Dict[str, Any]:
    """
    Load wxpy.pkl and return the storage data.
    
    The pickle structure is:
    {
        'version': str,
        'loginInfo': {...},
        'cookies': {...},
        'storage': {
            'userName': str,
            'nickName': str,
            'memberList': ContactList,
            'mpList': ContactList,  # This is what we need
            'chatroomList': ContactList,
            'lastInputUserName': str
        }
    }
    
    Returns:
        The storage dict from the pickle file.
    """
    path = Path(path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"wxpy.pkl not found: {path}")
    
    fixed_data = _fix_pickle_module_path(str(path))
    data = pickle.loads(fixed_data)
    
    return data.get("storage", {})


def load_puid_pkl(path: str) -> Dict[str, str]:
    """
    Load wxpy_puid.pkl and return UserName -> puid mapping.
    
    The pickle structure is a tuple of 4 TwoWayDict:
    (
        user_names,    # UserName -> puid (this is what we need)
        wxids,         # wxid -> puid
        remark_names,  # remark_name -> puid
        captions       # (nick_name, sex, province, city, signature) -> puid
    )
    
    TwoWayDict inherits from UserDict, so .data gives us the underlying dict.
    
    Returns:
        Dict mapping UserName to puid.
    """
    path = Path(path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"wxpy_puid.pkl not found: {path}")
    
    fixed_data = _fix_pickle_module_path(str(path))
    data = pickle.loads(fixed_data)
    
    # data is a tuple: (user_names, wxids, remark_names, captions)
    if isinstance(data, tuple) and len(data) >= 1:
        user_names_dict = data[0]
        # TwoWayDict inherits from UserDict, access .data for the underlying dict
        if hasattr(user_names_dict, "data"):
            return dict(user_names_dict.data)
        # If it's already a plain dict
        return dict(user_names_dict)
    
    return {}


def get_mp_list(wxpy_pkl_path: str) -> List[Dict[str, Any]]:
    """
    Extract mpList (public accounts) from wxpy.pkl.
    
    Returns:
        List of MP dicts with UserName, NickName, Signature, HeadImgUrl, etc.
    """
    storage = load_wxpy_pkl(wxpy_pkl_path)
    mp_list = storage.get("mpList", [])
    
    # ContactList is a list-like object, convert to plain list of dicts
    return [dict(mp) for mp in mp_list]


def get_puid_map(wxpy_puid_pkl_path: str) -> Dict[str, str]:
    """
    Extract puid_map from wxpy_puid.pkl.
    
    Returns:
        Dict mapping UserName to puid.
    """
    return load_puid_pkl(wxpy_puid_pkl_path)


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
