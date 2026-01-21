# efb-wechat-mprss

Generate RSS feeds for WeChat public accounts from EFB message logs.

## Installation

```bash
pip install -U git+https://github.com/Ovler-Young/efb-wechat-mprss
```

## Configuration

Create a configuration directory under your EFB profile:

```bash
mkdir -p ~/.ehforwarderbot/profiles/default/ovler.mprss
```

Then create `config.yaml` in that directory:

```bash
nano ~/.ehforwarderbot/profiles/default/ovler.mprss/config.yaml
```

Example configuration:

```yaml
wxpy_pkl_path: "../blueset.wechat/wxpy.pkl"
wxpy_puid_pkl_path: "../blueset.wechat/wxpy_puid.pkl"
tgdata_db_path: "../blueset.telegram/tgdata.db"
server:
  host: "0.0.0.0"
  port: 23185
```

> **Note**: Paths are relative to the configuration directory.

## Usage

Start the server from your configuration directory:

```bash
cd ~/.ehforwarderbot/profiles/default/ovler.mprss
python -m mprss.app
```

Then open `http://localhost:23185` in your browser.
