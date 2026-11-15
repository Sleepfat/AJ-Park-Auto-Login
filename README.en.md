# P._.A Dorm Auto Login

A small Python script that logs you into a **MikroTik Hotspot (CHAP)** captive portal without opening a browser, and logs you back in automatically whenever the connection drops.

Pure standard library. No dependencies. [ภาษาไทย](README.md)

```
██████╗                █████╗
██╔══██╗              ██╔══██╗
██████╔╝              ███████║
██╔═══╝               ██╔══██║
██║     ██╗███████╗██╗██║  ██║
╚═╝     ╚═╝╚══════╝╚═╝╚═╝  ╚═╝
```

## Features

- Logs in with plain HTTP requests (no Chrome / Selenium)
- Checks connectivity every 10 s and re-logs in automatically
- Reads the portal's reply and tells apart: wrong password, session limit reached, portal unreachable
- Pauses after repeated password rejections so your account doesn't get locked
- Exponential backoff with jitter on failed logins
- Single-instance guard, automatic log rotation
- Live status line and ASCII banners

## Requirements

- Python 3.9+ (tested in CI on 3.9, 3.11, 3.13)
- No third-party packages

## Quick start

```bash
git clone https://github.com/<your-name>/pa-dorm-autologin.git
cd pa-dorm-autologin
python autologin.py
```

On first run it asks for your username and password and saves them to `autologin.json` (the password prompt is hidden). You can also copy `autologin.example.json` to `autologin.json` and edit it. Delete the file to re-enter credentials.

> `autologin.json` is stored as plain text and is already in `.gitignore`. **Never commit it.**

## Configuration

Edit the constants at the top of `autologin.py`:

| Name | Meaning |
|---|---|
| `BASE` | Portal address, e.g. `http://10.0.6.1` |
| `INTERVAL` | Seconds between connectivity checks (10 or more recommended) |
| `BAD_PASS_LIMIT` / `BAD_PASS_PAUSE` | Consecutive rejections before pausing / pause length in seconds |
| `CHECKS` | URLs used to verify real internet access |

## How it works

The MikroTik login page hashes the password in the browser before sending it:

```
password = MD5( chap-id + password + chap-challenge )
```

`chap-id` and `chap-challenge` are embedded in the login page's JavaScript and change on every page load. So each attempt does the following:

1. `GET /login` and extract chap-id / challenge from `hexMD5('...' + ... + '...')`
2. Compute the same MD5 the browser would
3. `POST /login` with `username`, `password` (the hash), `dst`, `popup`
4. Verify by checking real internet access (`generate_204`) instead of trusting HTTP 200

If your portal isn't MikroTik or uses a customised page, inspect the login request in DevTools (Network → POST `login`) and adapt `make_hash()`, `login()` and `classify()`.

## Run at startup (Windows)

1. Run it once in a terminal so `autologin.json` exists
2. Open **Task Scheduler** → **Create Task...**
3. **Triggers**: At log on
4. **Actions**: Start a program
   - Program: path to `pythonw.exe` (no console window)
   - Arguments: full path to `autologin.py`
   - Start in: the script's folder
5. **Settings**: untick "Stop the task if it runs longer than"

Logs are written to `autologin.log` next to the script.

## Development

```bash
python -m unittest discover -s tests -v
```

Tests are offline (hash formula, reply classification, backoff, logo layout). GitHub Actions runs them on every push.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Portal rejected the password | Wrong credentials in `autologin.json` |
| Cannot reach portal | Not on the dorm network, or `BASE` is wrong |
| hexMD5 not found | The portal changed its login page; update the regex |
| Already running | Another instance holds the lock; close it first |

## Disclaimer

Use only with your own account and follow your dorm's / institution's network policy. The author is not responsible for misuse.

## Credits

The `CONNECTED` / `LOST` ASCII banner style is inspired by CE-HOUSE's `authen.py`.

## License

MIT - see [LICENSE](LICENSE)
