#!/usr/bin/env python3
"""
=============================================================
 Inventory Uploader — Web Interface
=============================================================
 Run:  python inventory_uploader.py
 Then: Browser opens automatically at http://localhost:5050
=============================================================
"""

from flask import Flask, request, jsonify, render_template_string
import requests
import pandas as pd
import json
import io
import webbrowser
import threading
from datetime import date

# ============================================================
# CONFIG — Pre-filled, do not change
# ============================================================
CLIENT_ID     = "1000.6WO83JXS5LUZIC8VRSCPYZR8C852RN"
CLIENT_SECRET = "9d34605184126768bbe1928d56dc11db27ac5ed562"
REFRESH_TOKEN = "1000.b0fa5dea26d1be52244b290b19773626.cab87ea08523c29c39f3e4f0c685e19d"
ORG_ID        = "60023902523"
WORKSPACE_ID  = "316848000001435063"
TABLE_NAME    = "Inventory_Snapshots"

ZOHO_ACCOUNTS_URL = "https://accounts.zoho.in/oauth/v2/token"
ZOHO_API_BASE     = "https://analyticsapi.zoho.in/api/v2"

COLUMN_MAP = {
    "Warehouse"              : "Warehouse",
    "Barcode"                : "Barcode",
    "SKU"                    : "SKU",
    "Title"                  : "Title",
    "Brand"                  : "Brand",
    "MRP"                    : "MRP",
    "Total Stock"            : "Total_Stock",
    "Mfg Date"               : "Mfg_Date",
    "Exp Date"               : "Exp_Date",
    "Batch No"               : "Batch_No",
    "Left Days"              : "Left_Days",
    "Shelf Life"             : "Shelf_Life_Raw",
    "Stock Last Updated Date": "Stock_Last_Updated",
    "Bin"                    : "Bin",
}

# ============================================================
# HTML UI
# ============================================================
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Inventory Uploader — MamaNourish</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #f0f2f5;
    min-height: 100vh;
    padding: 40px 20px;
  }
  .header {
    text-align: center;
    margin-bottom: 40px;
  }
  .header h1 {
    font-size: 26px;
    color: #1a1a2e;
    font-weight: 700;
  }
  .header p {
    color: #666;
    margin-top: 6px;
    font-size: 14px;
  }
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    max-width: 900px;
    margin: 0 auto;
  }
  @media(max-width: 640px) { .grid { grid-template-columns: 1fr; } }
  .card {
    background: white;
    border-radius: 16px;
    padding: 32px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.08);
    border-top: 5px solid var(--accent);
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
  .card.b2b { --accent: #3498db; }
  .card.b2c { --accent: #e67e22; }
  .card-title {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .badge {
    background: var(--accent);
    color: white;
    font-size: 13px;
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 20px;
    letter-spacing: 1px;
  }
  .card-title h2 {
    font-size: 20px;
    color: #1a1a2e;
  }
  label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #444;
    margin-bottom: 6px;
  }
  input[type="date"], input[type="file"] {
    width: 100%;
    padding: 10px 14px;
    border: 1.5px solid #ddd;
    border-radius: 8px;
    font-size: 14px;
    color: #333;
    background: #fafafa;
    transition: border 0.2s;
  }
  input[type="date"]:focus, input[type="file"]:focus {
    outline: none;
    border-color: var(--accent);
    background: white;
  }
  .drop-zone {
    border: 2px dashed #ddd;
    border-radius: 10px;
    padding: 28px 20px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    background: #fafafa;
    position: relative;
  }
  .drop-zone:hover, .drop-zone.drag-over {
    border-color: var(--accent);
    background: #f8f9ff;
  }
  .drop-zone input[type="file"] {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
    width: 100%;
    height: 100%;
    padding: 0;
    border: none;
    background: none;
  }
  .drop-icon { font-size: 32px; margin-bottom: 8px; }
  .drop-text { font-size: 14px; color: #888; }
  .drop-text strong { color: #444; }
  .file-name {
    font-size: 13px;
    color: var(--accent);
    font-weight: 600;
    margin-top: 4px;
    display: none;
  }
  .btn {
    width: 100%;
    padding: 13px;
    background: var(--accent);
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
    transition: opacity 0.2s, transform 0.1s;
    letter-spacing: 0.3px;
  }
  .btn:hover { opacity: 0.9; transform: translateY(-1px); }
  .btn:active { transform: translateY(0); }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
  .status {
    border-radius: 10px;
    padding: 14px 16px;
    font-size: 13px;
    display: none;
    line-height: 1.5;
  }
  .status.success {
    background: #e8f5e9;
    color: #2e7d32;
    border: 1px solid #a5d6a7;
    display: block;
  }
  .status.error {
    background: #fdecea;
    color: #c62828;
    border: 1px solid #ef9a9a;
    display: block;
  }
  .status.loading {
    background: #e3f2fd;
    color: #1565c0;
    border: 1px solid #90caf9;
    display: block;
  }
  .spinner {
    display: inline-block;
    width: 12px; height: 12px;
    border: 2px solid currentColor;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    margin-right: 6px;
    vertical-align: middle;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .footer {
    text-align: center;
    margin-top: 36px;
    font-size: 12px;
    color: #aaa;
  }
</style>
</head>
<body>

<div class="header">
  <h1>📦 Inventory Uploader</h1>
  <p>MamaNourish — Upload WMS snapshots directly to Zoho Analytics</p>
</div>

<div class="grid">

  <!-- B2B Card -->
  <div class="card b2b">
    <div class="card-title">
      <span class="badge">B2B</span>
      <h2>B2B Upload</h2>
    </div>
    <div>
      <label>Snapshot Date</label>
      <input type="date" id="date-b2b" value="{{ today }}">
    </div>
    <div>
      <label>WMS CSV File</label>
      <div class="drop-zone" id="zone-b2b">
        <input type="file" accept=".csv" id="file-b2b"
               onchange="onFileChange('b2b')">
        <div class="drop-icon">📂</div>
        <div class="drop-text"><strong>Click to browse</strong> or drag & drop</div>
        <div class="file-name" id="fname-b2b"></div>
      </div>
    </div>
    <button class="btn" onclick="upload('b2b')" id="btn-b2b">
      ⬆️ Upload B2B Snapshot
    </button>
    <div class="status" id="status-b2b"></div>
  </div>

  <!-- B2C Card -->
  <div class="card b2c">
    <div class="card-title">
      <span class="badge">B2C</span>
      <h2>B2C Upload</h2>
    </div>
    <div>
      <label>Snapshot Date</label>
      <input type="date" id="date-b2c" value="{{ today }}">
    </div>
    <div>
      <label>WMS CSV File</label>
      <div class="drop-zone" id="zone-b2c">
        <input type="file" accept=".csv" id="file-b2c"
               onchange="onFileChange('b2c')">
        <div class="drop-icon">📂</div>
        <div class="drop-text"><strong>Click to browse</strong> or drag & drop</div>
        <div class="file-name" id="fname-b2c"></div>
      </div>
    </div>
    <button class="btn" onclick="upload('b2c')" id="btn-b2c">
      ⬆️ Upload B2C Snapshot
    </button>
    <div class="status" id="status-b2c"></div>
  </div>

</div>

<div class="footer">Data uploads directly to Zoho Analytics · Inventory Master workspace</div>

<script>
function onFileChange(ch) {
  const file = document.getElementById('file-' + ch).files[0];
  const el   = document.getElementById('fname-' + ch);
  if (file) {
    el.textContent = '✅ ' + file.name;
    el.style.display = 'block';
  }
}

async function upload(ch) {
  const file   = document.getElementById('file-' + ch).files[0];
  const dt     = document.getElementById('date-' + ch).value;
  const btn    = document.getElementById('btn-' + ch);
  const status = document.getElementById('status-' + ch);

  if (!file) {
    showStatus(ch, 'error', '⚠️ Please select a CSV file first.');
    return;
  }
  if (!dt) {
    showStatus(ch, 'error', '⚠️ Please select a snapshot date.');
    return;
  }

  btn.disabled = true;
  showStatus(ch, 'loading',
    '<span class="spinner"></span> Uploading ' + ch.toUpperCase() +
    ' snapshot for ' + dt + '...', true);

  const form = new FormData();
  form.append('file',    file);
  form.append('channel', ch.toUpperCase());
  form.append('date',    dt);

  try {
    const resp = await fetch('/upload', { method: 'POST', body: form });
    const data = await resp.json();
    if (data.success) {
      showStatus(ch, 'success',
        '🎉 Upload successful!<br>' +
        '&nbsp;&nbsp;Rows added: <strong>' + data.added + '</strong><br>' +
        '&nbsp;&nbsp;Rows updated: <strong>' + data.updated + '</strong><br>' +
        '&nbsp;&nbsp;Snapshot date: <strong>' + dt + '</strong>', true);
    } else {
      showStatus(ch, 'error', '❌ ' + data.error, false);
    }
  } catch(e) {
    showStatus(ch, 'error', '❌ Network error: ' + e.message, false);
  }
  btn.disabled = false;
}

function showStatus(ch, type, msg, isHtml) {
  const el = document.getElementById('status-' + ch);
  el.className = 'status ' + type;
  if (isHtml) {
    el.innerHTML = msg;
  } else {
    el.textContent = msg;
  }
}

// Drag & drop highlight
['b2b','b2c'].forEach(ch => {
  const zone = document.getElementById('zone-' + ch);
  zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    document.getElementById('file-' + ch).files = e.dataTransfer.files;
    onFileChange(ch);
  });
});
</script>
</body>
</html>
"""

# ============================================================
# FLASK APP
# ============================================================
app = Flask(__name__)

def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        # Print full response to terminal for debugging
        print(f"\n[DEBUG] HTTP {resp.status_code}")
        print(f"[DEBUG] Response headers: {dict(resp.headers)}")
        print(f"[DEBUG] Response body: {resp.text[:2000]}\n")
        raise Exception(f"Zoho HTTP {resp.status_code} — see Terminal for details. Preview: {resp.text[:200]}")

def get_access_token():
    resp = requests.post(ZOHO_ACCOUNTS_URL, params={
        "refresh_token": REFRESH_TOKEN,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type":    "refresh_token"
    })
    data = safe_json(resp)
    if "access_token" not in data:
        raise Exception(f"Auth failed: {data}")
    return data["access_token"]

def get_table_id(token):
    # Always include Accept: application/json so Zoho returns JSON, not HTML
    base_h  = {"Authorization": f"Zoho-oauthtoken {token}", "Accept": "application/json"}
    headers = {**base_h, "ZANALYTICS-ORGID": ORG_ID}

    # ── Try /workspaces with ORGID (correct v2 endpoint) ──
    print(f"\n[DISCOVER] GET /workspaces with ORGID={ORG_ID} ...")
    r1 = requests.get(f"{ZOHO_API_BASE}/workspaces", headers=headers)
    print(f"[DISCOVER] HTTP {r1.status_code} | {r1.text[:300]}")

    # ── Try /users/me/workspaces with ORGID ──
    print(f"\n[DISCOVER] GET /users/me/workspaces with ORGID={ORG_ID} ...")
    r2 = requests.get(f"{ZOHO_API_BASE}/users/me/workspaces", headers=headers)
    print(f"[DISCOVER] HTTP {r2.status_code} | {r2.text[:300]}")

    # ── Try /users/me/workspaces without ORGID ──
    print(f"\n[DISCOVER] GET /users/me/workspaces WITHOUT ORGID ...")
    r3 = requests.get(f"{ZOHO_API_BASE}/users/me/workspaces", headers=base_h)
    print(f"[DISCOVER] HTTP {r3.status_code} | {r3.text[:300]}")

    # ── Try the workspace views directly ──
    print(f"\n[DISCOVER] GET /workspaces/{WORKSPACE_ID}/views with ORGID ...")
    r4 = requests.get(f"{ZOHO_API_BASE}/workspaces/{WORKSPACE_ID}/views", headers=headers)
    print(f"[DISCOVER] HTTP {r4.status_code} | {r4.text[:300]}")

    raise Exception("Diagnostics printed above — check Terminal")

def process_csv(file_bytes, channel, snapshot_date):
    df = pd.read_csv(io.BytesIO(file_bytes), thousands=",", dtype=str)
    present = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    df = df[list(present.keys())].rename(columns=present)
    if "MRP" in df.columns:
        df["MRP"] = df["MRP"].str.replace(",", "", regex=False)
    df["Snapshot_Date"] = snapshot_date
    df["Channel"]       = channel
    return df

def upload_to_zoho(token, table_id, df):
    url = f"{ZOHO_API_BASE}/workspaces/{WORKSPACE_ID}/views/{table_id}/data"
    config = {
        "importType": "APPEND",
        "fileType":   "CSV",
        "autoIdentifyColumnTypes": "true",
        "columnSeparator": ","
    }
    resp = requests.post(url,
        headers={
            "Authorization":    f"Zoho-oauthtoken {token}",
            "ZANALYTICS-ORGID": ORG_ID,
            "Accept":           "application/json"
        },
        files={"FILE": ("upload.csv", df.to_csv(index=False).encode(), "text/csv")},
        data={"CONFIG": json.dumps(config)}
    )
    result = safe_json(resp)
    if resp.status_code != 200:
        raise Exception(f"Upload failed (HTTP {resp.status_code}): {result}")
    s = result.get("data", {}).get("importSummary", {})
    return int(s.get("addedRows", 0)), int(s.get("updatedRows", 0))

@app.route("/")
def index():
    return render_template_string(HTML, today=str(date.today()))

@app.route("/upload", methods=["POST"])
def handle_upload():
    step = "init"
    try:
        channel       = request.form.get("channel")
        snapshot_date = request.form.get("date")
        file_bytes    = request.files["file"].read()

        step = "auth — getting access token"
        print(f"\n[STEP] {step}")
        token    = get_access_token()
        print(f"[OK] Token obtained: {token[:20]}...")

        step = "lookup — finding table ID"
        print(f"[STEP] {step}")
        table_id = get_table_id(token)
        print(f"[OK] Table ID: {table_id}")

        step = "process — parsing CSV"
        print(f"[STEP] {step}")
        df       = process_csv(file_bytes, channel, snapshot_date)
        print(f"[OK] {len(df)} rows ready")

        step = "upload — sending to Zoho"
        print(f"[STEP] {step}")
        added, updated = upload_to_zoho(token, table_id, df)

        return jsonify(success=True, added=added, updated=updated)

    except Exception as e:
        print(f"[FAILED at: {step}] {e}")
        return jsonify(success=False, error=f"Failed at [{step}]: {str(e)}")

# ============================================================
# LAUNCH
# ============================================================
if __name__ == "__main__":
    port = 5050
    url  = f"http://localhost:{port}"
    print(f"\n{'='*50}")
    print(f"  Inventory Uploader — MamaNourish")
    print(f"{'='*50}")
    print(f"  Opening browser at {url}")
    print(f"  Press Ctrl+C to stop\n")
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(port=port, debug=False)
