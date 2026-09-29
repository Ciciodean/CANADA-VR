# Canada VR — taking the barcode generator online

**Deployed instance:** https://ciciodean.github.io/CANADA-VR/ (GitHub Pages, static build)

Two versions of the tool:

| Version | File | Needs a server? | Best for |
|---|---|---|---|
| **Static (this folder)** | `online/index.html` | ❌ No — one file, all client-side | Permanent online hosting, sharing, offline use |
| Flask app | `../app.py` | ✅ Yes (Python) | Driving generation from automated tests via `/api/*` |

## Option A — Host the static file (recommended, free, 5 minutes)

`index.html` is fully self-contained (bwip-js + JSZip + app all inlined, ~1.2 MB).
It works from any static host — or even by double-clicking it on your own machine.

### GitHub Pages
1. Create a repo (e.g. `barcode-testgen`) on GitHub.
2. Upload `index.html` to the root of the repo.
3. Repo → **Settings → Pages** → Source: *Deploy from a branch* → `main` / `/ (root)`.
4. Your tool is live at `https://<you>.github.io/barcode-testgen/`.

### Netlify / Vercel / Cloudflare Pages
Drag-and-drop `index.html` (or the folder) into Netlify Drop
(https://app.netlify.com/drop) — instant URL, no account config needed.
Same for Vercel/Cloudflare Pages (framework preset: *Other/None*).

### S3 / any web space
Upload `index.html` to the bucket/host root. Done.

> Privacy note: the static build never sends anything anywhere — generation is
> 100% in-browser, so it is safe to share for barcode test-data purposes.

## Option B — Put the Flask app on a real server (API access)

If you want the HTTP API (`/api/generate`, `/api/batch`) online permanently:

```bash
pip install -r requirements.txt gunicorn
gunicorn -w 2 -b 0.0.0.0:8080 app:app
```

Deploy targets: Render / Railway / Fly.io (all have free tiers; point them at
this folder, start command above), PythonAnywhere, or any VPS/Docker host.

## Local use
- Static: double-click `online/index.html` (works offline, even with no internet).
- CLI: `python generator.py bc ...` / `python batch.py --count 50 ...` (see ../README.md).

**Reminder: synthetic test data only — fabricating usable ID barcodes is illegal.**
