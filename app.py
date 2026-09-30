#!/usr/bin/env python3
"""Web UI for the synthetic BC/AAMVA PDF417 test-barcode generator."""

from flask import Flask, Response, jsonify, request

from batch import make_batch
from generator import (DEFAULTS, EYE_CODES, HAIR_CODES, build_aamva_payload,
                       build_bc_payload, render_png_b64)

app = Flask(__name__)

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Canada VR — Licence Barcode Test-Data Generator</title>
<style>
  :root { --bg:#0f172a; --card:#1e293b; --fg:#e2e8f0; --muted:#94a3b8;
          --accent:#38bdf8; --warn:#b45309; --warnbg:#fffbeb; --ok:#16a34a; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
         background:var(--bg); color:var(--fg); }
  header { padding:18px 22px 6px; }
  h1 { font-size:19px; margin:0; }
  h1 small { color:var(--muted); font-weight:400; font-size:13px; }
  .tabs { display:flex; gap:8px; padding:6px 22px; }
  .tabs button { background:var(--card); color:var(--muted); border:1px solid #334155;
                 border-radius:8px 8px 0 0; padding:9px 16px; cursor:pointer;
                 font-size:14px; }
  .tabs button.active { color:var(--fg); border-bottom-color:transparent;
                        background:#263449; }
  .panel { display:none; margin:0 22px 22px; padding:18px; background:var(--card);
           border:1px solid #334155; border-radius:0 8px 8px 8px; }
  .panel.active { display:block; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(170px,1fr));
          gap:10px 14px; max-width:980px; }
  label { font-size:11px; color:var(--muted); display:block; margin-bottom:3px;
          text-transform:uppercase; letter-spacing:.4px; }
  input, select, textarea { width:100%; background:#0b1220; color:var(--fg);
        border:1px solid #334155; border-radius:6px; padding:7px 9px; font-size:14px;
        font-family:ui-monospace,Menlo,Consolas,monospace; }
  textarea { min-height:120px; }
  .opts { display:flex; flex-wrap:wrap; gap:14px; margin-top:14px; align-items:end; }
  .opts > div { min-width:130px; }
  button.go { margin-top:16px; background:var(--accent); color:#082f49; border:0;
              font-weight:700; font-size:15px; border-radius:8px; padding:11px 26px;
              cursor:pointer; }
  button.go:hover { filter:brightness(1.1); }
  button.ghost { margin-top:16px; background:transparent; color:var(--accent);
                 border:1px dashed var(--accent); font-weight:600; font-size:13px;
                 border-radius:8px; padding:9px 16px; cursor:pointer; }
  button.ghost:hover { background:rgba(56,189,248,.12); }
  #result { margin:0 22px 30px; display:none; }
  #result article { background:var(--card); border:1px solid #334155;
                    border-radius:8px; padding:18px; }
  #bcimg { background:#fff; padding:12px; border-radius:6px; max-width:100%;
           image-rendering:pixelated; }
  pre { background:#0b1220; border:1px solid #334155; border-radius:6px;
        padding:12px; font-size:12px; white-space:pre-wrap; word-break:break-all;
        max-height:180px; overflow:auto; }
  .row { display:flex; gap:10px; flex-wrap:wrap; margin-top:12px; }
  .row a { background:#334155; color:var(--fg); text-decoration:none; padding:8px 14px;
           border-radius:6px; font-size:13px; }
  .row a:hover { background:#475569; }
  .err { color:#f87171; margin-top:12px; font-size:13px; }
  h3 { margin:0 0 10px; font-size:14px; color:var(--accent); }
  .section { margin-top:16px; padding-top:12px; border-top:1px solid #334155; }
  footer { color:var(--muted); font-size:12px; padding:0 22px 30px; }
</style>
</head>
<body>
<header>
  <h1>CANADA VR <small>BC &amp; AAMVA driver&rsquo;s-licence PDF417
      &middot; synthetic fixtures for software testing</small></h1>
</header>

<div class="tabs">
  <button class="active" onclick="tab('bc',this)">BC track format</button>
  <button onclick="tab('aamva',this)">AAMVA DL subfile</button>
  <button onclick="tab('raw',this)">Raw payload &rarr; PDF417</button>
  <button onclick="tab('batch',this)">Batch &rarr; ZIP</button>
</div>

<!-- ======================= shared person data ======================= -->
<div class="panel active" id="p-bc">
  <h3>BC combined-card style &mdash; magnetic-stripe tracks in a PDF417</h3>
  __FIELDS__
  <div class="section opts">
    <div><label>Height format (track 3)</label>
      <select id="height_mode"><option value="fi">feet+inches (510)</option>
      <option value="cm">centimetres (178)</option></select></div>
    <div><label>BC &ldquo;_%&rdquo; quirk</label>
      <select id="bc_quirk"><option value="1">on (real BC cards)</option>
      <option value="0">off (standard %)</option></select></div>
    <div><label>Track joiner</label>
      <select id="joiner"><option value="">none</option>
      <option value="\\n">LF</option><option value="\\r">CR</option></select></div>
    __RENDER_OPTS__
    <div><button class="ghost" type="button" onclick="loadSample(this)">&#8635; Load sample identity</button>
    <button class="go" onclick="generate('bc')">Generate BC barcode</button></div>
  </div>
</div>

<div class="panel" id="p-aamva">
  <h3>Standard AAMVA DL subfile (ANSI header + element IDs)</h3>
  __FIELDS__
  <div class="section opts">
    <div><label>AAMVA version</label><select id="aa_version">
      <option>09</option><option>02</option><option>03</option><option>06</option>
      <option>08</option><option>10</option></select></div>
    <div><label>Date format</label><select id="aa_datefmt">
      <option value="CCYYMMDD">CCYYMMDD (Canada)</option>
      <option value="MMDDCCYY">MMDDCCYY (US)</option></select></div>
    <div><label>Element separator</label><select id="aa_sep">
      <option value="cr">CR (0x0D)</option><option value="lf">LF (0x0A)</option></select></div>
    <div><label>DAU height unit</label><select id="aa_hunit">
      <option value="cm">cm</option><option value="in">in</option></select></div>
    __RENDER_OPTS__
    <div><button class="ghost" type="button" onclick="loadSample(this)">&#8635; Load sample identity</button>
    <button class="go" onclick="generate('aamva')">Generate AAMVA barcode</button></div>
  </div>
</div>

<div class="panel" id="p-raw">
  <h3>Render any raw payload as PDF417</h3>
  <p style="color:var(--muted);font-size:13px;margin-top:0">Paste a payload you captured from a
  real-world specimen (decode escapes such as \\n, \\r, \\x1e are interpreted).</p>
  <textarea id="raw_payload">@\\n\\x1e\\rANSI 636028090001DL00310175DCA5\\rDCBNONE\\rDCDNONE\\rDBA20290515\\rDCSSAMPLECARD\\rDACTEST\\rDADQ\\rDBD20240102\\rDBB19900515\\rDBC1\\rDAYBRO\\rDAU178 cm\\rDAG123 SAMPLE AVE\\rDAIVICTORIA\\rDAJBC\\rDAKV8W2E4     \\rDAQ1234567\\rDCGCAN\\r</textarea>
  <div class="section opts">
    __RENDER_OPTS__
    <div><button class="go" onclick="generate('raw')">Render raw payload</button></div>
  </div>
</div>

<div class="panel" id="p-batch">
  <h3>Batch mode &mdash; ZIP of randomized synthetic identities</h3>
  <p style="color:var(--muted);font-size:13px;margin-top:0">Downloads a ZIP with
  <b>barcodes/*.png</b>, <b>payloads/*.txt</b> (exact payload strings) and
  <b>manifest.json</b> containing every payload, its hex form, and the field values a
  correct parser should extract &mdash; ready-made for test assertions. Slots 0&ndash;3 are
  deterministic edge cases: name truncation, missing fields, sex&nbsp;X, heavy data.</p>
  <div class="opts">
    <div><label>Count (1&ndash;500)</label>
      <input id="bcount" type="number" value="50" min="1" max="500"></div>
    <div><label>Format</label>
      <select id="bmode"><option value="mixed">mixed (alternating)</option>
      <option value="bc">BC track format</option>
      <option value="aamva">AAMVA subfile</option></select></div>
    <div><label>Seed (blank = random)</label>
      <input id="bseed" type="number" placeholder="e.g. 42"></div>
    __RENDER_OPTS__
    <div><button class="go" onclick="generateBatch()">Generate ZIP</button></div>
  </div>
  <div id="batch_done" class="section" style="display:none">
    <a id="dl_zip" download="licence_test_batch.zip"
       style="background:var(--ok);color:#fff;padding:10px 18px;border-radius:8px;
              text-decoration:none;font-weight:600">&#11015;&#65039; Download batch ZIP</a>
    <span id="batch_size" style="margin-left:12px;color:var(--muted)"></span>
  </div>
  <div class="err" id="batch_err"></div>
</div>

<div id="result"><article>
  <h3>Result</h3>
  <img id="bcimg" alt="generated PDF417 barcode">
  <div class="row">
    <a id="dl_png" download="licence_test_barcode.png">&#11015;&#65039; Download PNG</a>
    <a id="dl_txt" download="licence_test_payload.txt">&#11015;&#65039; Download payload (.txt)</a>
    <a id="dl_hex" download="licence_test_payload.hex">&#11015;&#65039; Download hex dump</a>
  </div>
  <h3 style="margin-top:16px">Payload (escaped)</h3><pre id="ptext"></pre>
  <h3>Payload (hex)</h3><pre id="phex"></pre>
  <div class="err" id="errbox"></div>
</article></div>

<footer>BC track layout per Province of BC MSP Teleplan spec &amp; AAMVA Annex F &middot;
BC IIN 636028 &middot; PDF417 = ISO/IEC 15438 &middot; all data unencrypted by design.</footer>

<script>
const SAMPLES = [
  {family:'SAMPLECARD',first:'TEST',middle:'Q',dob:'1990-05-15',sex:'1',
   street:'123 SAMPLE AVE',street2:'',city:'VICTORIA',province:'BC',
   postal:'V8W 2E4',licence:'1234567',dl_class:'5',restrictions:'',
   endorsements:'',height_cm:'178',height_fi:'510',weight_kg:'080',
   hair:'BRO',eyes:'BRO',issue:'2024-01-02',expiry:'2029-05-15',
   iin:'636028',dcf:'TESTCARD0000001'},
  {family:'VERYLONGFAMILYNAMEFIXTURE',first:'EXTRAORDINARILONGFIRSTNAME',
   middle:'Z',dob:'1988-11-30',sex:'1',street:'4588 WHIFFIN SPIT RD',
   street2:'',city:'PRINCE GEORGE',province:'BC',postal:'V2M 6Z9',
   licence:'27687537',dl_class:'6',restrictions:'21',endorsements:'',
   height_cm:'185',height_fi:'601',weight_kg:'092',hair:'BLK',eyes:'BRO',
   issue:'2022-06-14',expiry:'2027-11-30',iin:'636028',dcf:'TST0000000017'},
  {family:'SPECIMAN',first:'JORDAN',middle:'',dob:'2003-04-09',sex:'2',
   street:'77 TERMINAL AVE',street2:'',city:'NANAIMO',province:'BC',
   postal:'V9R 5C6',licence:'58441209',dl_class:'7',restrictions:'46',
   endorsements:'',height_cm:'160',height_fi:'503',weight_kg:'061',
   hair:'BLN',eyes:'BLU',issue:'2025-02-19',expiry:'2030-04-09',
   iin:'636028',dcf:'TST0000000003'},
  {family:'REGRESS',first:'ARJUN',middle:'K',dob:'1995-03-22',sex:'9',
   street:'850 GRANVILLE ST',street2:'UNIT 1205',city:'VANCOUVER',
   province:'BC',postal:'V6Z 1K3',licence:'92744215',dl_class:'5',
   restrictions:'21 46',endorsements:'',height_cm:'172',height_fi:'508',
   weight_kg:'076',hair:'UNK',eyes:'UNK',issue:'2023-09-10',
   expiry:'2028-03-22',iin:'636028',dcf:'TST0000000042'},
];
function loadSample(btn){
  const s = SAMPLES[Math.floor(Math.random()*SAMPLES.length)];
  const panel = btn.closest('.panel');
  panel.querySelectorAll('[data-f]').forEach(el=>{
    if(s[el.dataset.f] !== undefined) el.value = s[el.dataset.f];
  });
}
function tab(id, btn){
  document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('p-'+id).classList.add('active');
}
function interpEscapes(s){
  return s.replace(/\\\\(x[0-9a-fA-F]{2}|n|r|t|0)/g, (m,e)=>{
    if(e.startsWith('x')) return String.fromCharCode(parseInt(e.slice(1),16));
    return {n:'\\n',r:'\\r',t:'\\t','0':'\\0'}[e];
  });
}
function collectFields(root){
  const d = {};
  root.querySelectorAll('input[data-f],select[data-f]').forEach(el=>d[el.dataset.f]=el.value);
  return d;
}
function designatorCheck(p){
  const out=[];
  const m=/^@\\n\\x1e\\rANSI ([0-9A-Za-z]{6})(\\d{2})(\\d{2})(\\d{2})/.exec(p);
  if(!m){ if(p[0]==='@') out.push('starts with @ but ANSI header is malformed'); return out; }
  const entries=parseInt(m[4],10), hdrLen=m[0].length, dataStart=hdrLen+entries*10;
  const type=p.substr(hdrLen,2), off=parseInt(p.substr(hdrLen+2,4),10),
        len=parseInt(p.substr(hdrLen+6,4),10);
  if(off!==dataStart) out.push(`${type} offset says ${off}, correct is ${dataStart}`);
  if(entries===1){
    const actual=p.length-dataStart;
    if(len!==actual) out.push(`${type} length says ${len} but actual subfile is ${actual} bytes — strict decoders drop the last ${actual-len} byte(s)`);
  }
  return out;
}
async function generate(mode){
  const panel = document.getElementById('p-'+mode);
  const body = { mode, fields: collectFields(panel),
                 render: { columns:+panel.querySelector('#rcols').value,
                           security_level:+panel.querySelector('#rec').value,
                           scale:+panel.querySelector('#rscale').value } };
  if(mode==='bc'){
    body.options = { height_mode: panel.querySelector('#height_mode').value,
                     bc_quirk: panel.querySelector('#bc_quirk').value==='1',
                     joiner: interpEscapes(panel.querySelector('#joiner').value) };
  } else if(mode==='aamva'){
    body.options = { version: panel.querySelector('#aa_version').value,
                     datefmt: panel.querySelector('#aa_datefmt').value,
                     sep: panel.querySelector('#aa_sep').value,
                     hunit: panel.querySelector('#aa_hunit').value };
  } else {
    body.raw = interpEscapes(document.getElementById('raw_payload').value);
  }
  const res = await fetch('/api/generate',{method:'POST',
      headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const data = await res.json();
  document.getElementById('result').style.display='block';
  const err = document.getElementById('errbox');
  if(data.error){ err.textContent = 'Error: '+data.error; return; }
  err.textContent='';
  if(mode==='raw'){ const w = designatorCheck(body.raw);
    if(w.length) err.textContent = '\u26a0 Designator check: '+w.join(' \u00b7 '); }
  document.getElementById('bcimg').src='data:image/png;base64,'+data.png_b64;
  document.getElementById('ptext').textContent=data.payload_repr;
  document.getElementById('phex').textContent=data.payload_hex;
  document.getElementById('dl_png').href='data:image/png;base64,'+data.png_b64;
  document.getElementById('dl_txt').href='data:text/plain;base64,'+data.payload_b64;
  document.getElementById('dl_hex').href='data:text/plain;base64,'+btoa(data.payload_hex);
  document.getElementById('result').scrollIntoView({behavior:'smooth'});
}
async function generateBatch(){
  const panel = document.getElementById('p-batch');
  const seedVal = panel.querySelector('#bseed').value;
  const body = { count:+panel.querySelector('#bcount').value,
                 mode: panel.querySelector('#bmode').value,
                 seed: seedVal === '' ? null : +seedVal,
                 render: { columns:+panel.querySelector('#rcols').value,
                           security_level:+panel.querySelector('#rec').value,
                           scale:+panel.querySelector('#rscale').value } };
  const res = await fetch('/api/batch',{method:'POST',
      headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const err = document.getElementById('batch_err');
  if(!res.ok){
    let msg = 'HTTP '+res.status;
    try { msg = (await res.json()).error || msg; } catch(e){}
    err.textContent = 'Error: '+msg; return;
  }
  err.textContent='';
  const blob = await res.blob();
  const a = document.getElementById('dl_zip');
  if(a.dataset.url) URL.revokeObjectURL(a.dataset.url);
  a.dataset.url = URL.createObjectURL(blob);
  a.href = a.dataset.url;
  document.getElementById('batch_size').textContent =
      (blob.size/1024).toFixed(1)+' KB ready';
  document.getElementById('batch_done').style.display='block';
}
generate('bc');
</script>
</body>
</html>"""

FIELD_SPEC = [
    ("family", "Family name"), ("first", "First name"), ("middle", "Middle"),
    ("licence", "Licence #"), ("dob", "DOB (YYYY-MM-DD)"),
    ("issue", "Issue date"), ("expiry", "Expiry date"),
    ("sex", "Sex (1/2/9)"), ("street", "Street"), ("street2", "Street 2"),
    ("city", "City"), ("province", "Province"), ("postal", "Postal"),
    ("dl_class", "Class"), ("restrictions", "Restrictions"),
    ("endorsements", "Endorsements"), ("height_cm", "Height (cm)"),
    ("height_fi", "Height (F+II)"), ("weight_kg", "Weight kg"),
    ("iin", "IIN"), ("dcf", "Doc discriminator (DCF)"),
]


def _fields_html() -> str:
    cells = []
    for key, label in FIELD_SPEC:
        cells.append(
            f'<div><label>{label}</label>'
            f'<input data-f="{key}" value="{DEFAULTS[key]}"></div>')
    hair = "".join(f'<option{" selected" if c == "BRO" else ""}>{c}</option>'
                   for c in HAIR_CODES)
    eyes = "".join(f'<option{" selected" if c == "BRO" else ""}>{c}</option>'
                   for c in EYE_CODES)
    cells.append(f'<div><label>Hair</label><select data-f="hair">{hair}</select></div>')
    cells.append(f'<div><label>Eyes</label><select data-f="eyes">{eyes}</select></div>')
    return '<div class="grid">' + "".join(cells) + "</div>"


RENDER_OPTS = """
    <div><label>PDF417 columns</label><select id="rcols">
      <option>6</option><option>4</option><option>5</option><option>8</option>
      <option>10</option><option>3</option><option>2</option></select></div>
    <div><label>Error correction</label><select id="rec">
      <option>5</option><option>2</option><option>3</option><option>4</option>
      <option>6</option><option>7</option><option>8</option></select></div>
    <div><label>Module scale</label><select id="rscale">
      <option>3</option><option>2</option><option>4</option><option>5</option></select></div>
"""

PAGE = (PAGE.replace("__FIELDS__", _fields_html())
            .replace("__RENDER_OPTS__", RENDER_OPTS))


@app.get("/")
def index():
    return PAGE


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/generate")
def generate():
    body = request.get_json(force=True)
    mode = body.get("mode", "bc")
    render = body.get("render", {}) or {}
    render_kw = dict(
        columns=max(1, min(30, int(render.get("columns", 6)))),
        security_level=max(0, min(8, int(render.get("security_level", 5)))),
        scale=max(1, min(10, int(render.get("scale", 3)))),
    )
    try:
        if mode == "raw":
            payload = body.get("raw", "")
        else:
            d = dict(DEFAULTS)
            d.update({k: ("" if v is None else str(v))
                      for k, v in (body.get("fields") or {}).items()})
            opts = body.get("options") or {}
            if mode == "bc":
                payload = build_bc_payload(
                    d,
                    bc_quirk=bool(opts.get("bc_quirk", True)),
                    height_mode=opts.get("height_mode", "fi"),
                    joiner=opts.get("joiner", ""))
            elif mode == "aamva":
                payload = build_aamva_payload(
                    d,
                    version=str(opts.get("version", "09")),
                    datefmt=opts.get("datefmt", "CCYYMMDD"),
                    sep="\r" if opts.get("sep", "cr") == "cr" else "\n",
                    height_unit=opts.get("hunit", "cm"))
            else:
                return jsonify(error=f"unknown mode {mode}"), 400

        raw = payload.encode("latin-1", "replace")
        import base64
        return jsonify(
            png_b64=render_png_b64(payload, **render_kw),
            payload_repr=repr(payload),
            payload_hex=raw.hex(" "),
            payload_b64=base64.b64encode(raw).decode(),
            byte_len=len(raw),
        )
    except Exception as exc:  # surface generator errors to the UI
        return jsonify(error=str(exc)), 400


@app.post("/api/batch")
def api_batch():
    body = request.get_json(force=True)
    count = max(1, min(500, int(body.get("count", 50) or 50)))
    mode = body.get("mode", "mixed")
    if mode not in ("bc", "aamva", "mixed"):
        mode = "mixed"
    seed = body.get("seed")
    seed = int(seed) if seed is not None else None
    render = body.get("render", {}) or {}
    render_kw = dict(
        columns=max(1, min(30, int(render.get("columns", 6)))),
        security_level=max(0, min(8, int(render.get("security_level", 5)))),
        scale=max(1, min(10, int(render.get("scale", 3)))),
    )
    try:
        data = make_batch(count, mode, seed, render_kw)
    except Exception as exc:
        return jsonify(error=str(exc)), 400
    return Response(data, mimetype="application/zip", headers={
        "Content-Disposition": "attachment; filename=licence_test_batch.zip"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
