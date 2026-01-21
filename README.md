# efb-wechat-mprss

Generate RSS feeds for WeChat public accounts from EFB message logs.

## Setup

```bash
uv venv
uv pip install -e .
```

## Usage

```bash
# Start the server
cd d:\dev\efb-wechat-mprss
.venv\Scripts\activate
python -m backend.app
```

Then open http://localhost:8080

## Configuration

Edit `config.yaml` to set:
- `wxpy_pkl_path`: Path to wxpy.pkl
- `wxpy_puid_pkl_path`: Path to wxpy_puid.pkl  
- `tgdata_db_path`: Path to tgdata.db
