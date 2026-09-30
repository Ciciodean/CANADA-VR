/* CANADA VR — BC / AAMVA licence-barcode test generator — client-side logic.
 * Port of generator.py / batch.py. Runs fully offline in the browser.
 * Synthetic test data only. */
'use strict';

/* ================= payload builders (port of generator.py) ================= */

const BC_IIN = '636028';
const HAIR_CODES = ['BAL', 'BLK', 'BLN', 'BRO', 'GRY', 'RED', 'WHI', 'SDY', 'UNK'];
const EYE_CODES = ['BLK', 'BLU', 'BRO', 'GRN', 'GRY', 'HAZ', 'MAR', 'PNK', 'UNK'];

const DEFAULTS = {
  family: 'SAMPLECARD', first: 'TEST', middle: 'Q',
  dob: '1990-05-15', sex: '1',
  street: '123 SAMPLE AVE', street2: '', city: 'VICTORIA',
  province: 'BC', postal: 'V8W 2E4',
  licence: '1234567', dl_class: '5', restrictions: '', endorsements: '',
  height_cm: '178', height_fi: '510', weight_kg: '080',
  hair: 'BRO', eyes: 'BRO',
  issue: '2024-01-02', expiry: '2029-05-15',
  phn: '9123456789', iin: BC_IIN, dcf: 'TESTCARD0000001',
  cds_version: '1', juris_version: '00',
};

const ccyymmdd = s => s.replaceAll('-', '');
const mmddccyy = s => { const [y, m, d] = s.split('-'); return m + d + y; };
const yymm = s => { const [y, m] = s.split('-'); return y.slice(2) + m; };

/** Uppercase, right-pad/truncate to fixed width (mirrors Python _fix). */
function fix(s, w, pad = ' ') {
  s = String(s).toUpperCase();
  return (s + pad.repeat(w)).slice(0, w);
}
/** Weight: left-pad with zeros (kg), 3 chars. */
const weight3 = s => String(s).padStart(3, '0').slice(-3);

function buildBcTrack1(d) {
  const city = d.city.toUpperCase().slice(0, 13);
  const name = `${d.family}$${d.first}$${d.middle}`.toUpperCase()
    .replace(/\$+$/, '').slice(0, 35);
  let addr = d.street.toUpperCase();
  if (d.street2) addr = (addr + '$' + d.street2.toUpperCase()).slice(0, 29);
  else addr = addr.slice(0, 29);
  let out = '%' + fix(d.province, 2);
  out += city + (city.length < 13 ? '^' : '');
  out += name + (name.length < 35 ? '^' : '');
  out += addr + '?';
  return out;
}

function buildBcTrack2(d) {
  let dlnum = (d.licence.toUpperCase().match(/[A-Z0-9]/g) || []).join('');
  let overflow = '';
  if (dlnum.length > 13) {
    overflow = dlnum.slice(13, 18);
    dlnum = dlnum.slice(0, 13);
  }
  let out = ';' + d.iin + dlnum + '=' + yymm(d.expiry) + ccyymmdd(d.dob);
  if (overflow) out += overflow;
  return out + '?';
}

function buildBcTrack3(d, bcQuirk = true, heightMode = 'fi') {
  const sentinel = bcQuirk ? '_%' : '%';
  const height = fix(heightMode === 'cm' ? d.height_cm : d.height_fi, 3);
  return sentinel
    + fix(d.cds_version, 1)
    + fix(d.juris_version.slice(-1), 1)
    + fix(d.postal.replace(/ /g, ''), 11)
    + fix(d.dl_class, 2)
    + fix(d.restrictions, 10)
    + fix(d.endorsements, 4)
    + fix(d.sex, 1)
    + height
    + weight3(d.weight_kg)
    + fix(d.hair, 3)
    + fix(d.eyes, 3)
    + '?';
}

function buildBcPayload(d, opts = {}) {
  const { bc_quirk = true, height_mode = 'fi', joiner = '' } = opts;
  return [buildBcTrack1(d), buildBcTrack2(d),
          buildBcTrack3(d, bc_quirk, height_mode)].join(joiner);
}

function buildAamvaPayload(d, opts = {}) {
  const { version = '09', datefmt = 'CCYYMMDD', sep = '\r', hunit = 'cm' } = opts;
  const dfmt = datefmt === 'CCYYMMDD' ? ccyymmdd : mmddccyy;
  let dau;
  if (hunit === 'cm') dau = String(parseInt(d.height_cm, 10)).padStart(3, '0') + ' cm';
  else {
    const ft = parseInt(d.height_fi[0], 10), inch = parseInt(d.height_fi.slice(1), 10);
    dau = String(ft * 12 + inch).padStart(3, '0') + ' in';
  }
  const elements = [
    ['DCA', d.dl_class.toUpperCase()],
    ['DCB', d.restrictions.toUpperCase() || 'NONE'],
    ['DCD', d.endorsements.toUpperCase() || 'NONE'],
    ['DBA', dfmt(d.expiry)],
    ['DCS', d.family.toUpperCase()],
    ['DAC', d.first.toUpperCase()],
    ['DAD', d.middle.toUpperCase()],
    ['DBD', dfmt(d.issue)],
    ['DBB', dfmt(d.dob)],
    ['DBC', d.sex],
    ['DAY', d.eyes.toUpperCase()],
    ['DAU', dau],
    ['DAG', d.street.toUpperCase()],
    ['DAI', d.city.toUpperCase()],
    ['DAJ', d.province.toUpperCase()],
    ['DAK', fix(d.postal.replace(/ /g, ''), 11)],
    ['DAQ', d.licence],
    ['DCF', d.dcf],
    ['DCG', 'CAN'],
    ['DDE', 'N'], ['DDF', 'N'], ['DDG', 'N'],
  ];
  const subfile = elements.map(([k, v]) => k + v).join(sep) + sep;
  const entries = 1;
  const header = '@\n\x1e\rANSI ' + d.iin
    + String(version).padStart(2, '0')
    + String(d.juris_version).padStart(2, '0')
    + String(entries).padStart(2, '0');
  const offset = header.length + entries * 10;   // all chars are single-byte
  const designator = 'DL' + String(offset).padStart(4, '0')
    + String(subfile.length).padStart(4, '0');
  return header + designator + subfile;
}

/* ================= batch identities (port of batch.py) ================= */

function mulberry32(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

const FIRST = ['ALEX','JORDAN','TAYLOR','MORGAN','CASEY','RILEY','JAMIE','PRIYA',
  'WEI','FATIMA','LUCAS','EMMA','NOAH','OLIVIA','ARJUN','SOFIA','LIAM','MAYA',
  'ETHAN','ZARA'];
const LAST = ['TESTER','SAMPLE','FIXTURE','MOCKSMITH','DATATEST','PROVABLE',
  'CHECKFIELD','UNITCASE','REGRESS','SPECIMAN','PLACEHOLDER','DEMOCRAFT',
  'VALIDOR','SYNTHETIC','FAKEMAN','PARSLEY'];
const CITIES = ['VICTORIA','VANCOUVER','SURREY','BURNABY','KELOWNA','NANAIMO',
  'KAMLOOPS','PRINCE GEORGE','ABBOTSFORD','RICHMOND','SAANICH','LANGLEY',
  'COQUITLAM','CHILLIWACK','VERNON'];
const STREET_NAMES = ['MAIN ST','OAK AVE','CEDAR ST','MARINE DR','KINGSWAY',
  'GOVERNMENT ST','LOUGHEED HWY','GRANVILLE ST','DOUGLAS ST','BROADWAY',
  'FORT ST','QUADRA ST','WHIFFIN SPIT RD'];
const CLASSES = ['5','5','5','7','7','6','4','2','8','1'];
const RESTRICTIONS = ['','','','21','21','46','21 46','15'];
const POSTAL_LETTERS = 'ABCEGHJKLMNPRSTVXY';

function makeRng(seed) {
  const rnd = seed == null ? Math.random : mulberry32(seed >>> 0);
  return {
    next: rnd,
    int: (lo, hi) => lo + Math.floor(rnd() * (hi - lo + 1)),
    choice: arr => arr[Math.floor(rnd() * arr.length)],
  };
}

function randIsoDate(rng, startMs, endMs) {
  return new Date(startMs + Math.floor(rng.next() * (endMs - startMs)))
    .toISOString().slice(0, 10);
}

function randomIdentity(rng) {
  const ft = rng.choice([5, 5, 5, 5, 6, 6]);
  const inch = rng.int(0, 11);
  const cm = Math.round((ft * 12 + inch) * 2.54);
  const dob = randIsoDate(rng, Date.UTC(1955, 0, 1), Date.UTC(2007, 11, 31));
  const issue = randIsoDate(rng, Date.UTC(2016, 0, 1), Date.UTC(2026, 5, 1));
  const expY = Math.min(parseInt(issue.slice(0, 4), 10) + 5, 2031);
  const pL = () => POSTAL_LETTERS[rng.int(0, POSTAL_LETTERS.length - 1)];
  return {
    family: rng.choice(LAST), first: rng.choice(FIRST),
    middle: rng.choice([...'ABCDEFGHJKLMNPQRSTW', '', '', '', '']),
    dob, sex: rng.choice(['1', '1', '2', '2', '9']),
    street: `${rng.int(1, 9899)} ${rng.choice(STREET_NAMES)}`,
    street2: rng.choice(['', '', '', `UNIT ${rng.int(1, 399)}`, `APT ${rng.int(1, 98)}`]),
    city: rng.choice(CITIES), province: 'BC',
    postal: `V${rng.int(0, 9)}${pL()} ${rng.int(0, 9)}${pL()}${rng.int(0, 9)}`,
    licence: String(rng.int(1000000, 99999999)),
    dl_class: rng.choice(CLASSES),
    restrictions: rng.choice(RESTRICTIONS), endorsements: '',
    height_cm: String(cm), height_fi: `${ft}${String(inch).padStart(2, '0')}`,
    weight_kg: String(rng.int(45, 120)).padStart(3, '0'),
    hair: rng.choice(HAIR_CODES), eyes: rng.choice(EYE_CODES),
    issue, expiry: `${expY}${issue.slice(4)}`,
    phn: `9${rng.int(100000000, 999999999)}`,
    iin: BC_IIN, dcf: `TST${String(rng.int(0, 9999999999)).padStart(10, '0')}`,
    cds_version: '1', juris_version: '00',
  };
}

function applyEdgeCases(items) {
  if (items.length >= 1) Object.assign(items[0], {
    family: 'VERYLONGFAMILYNAMEFIXTURE',
    first: 'EXTRAORDINARILONGFIRSTNAME', middle: 'Z' });
  if (items.length >= 2) Object.assign(items[1], { middle: '', street2: '' });
  if (items.length >= 3) Object.assign(items[2], { sex: '9', hair: 'UNK', eyes: 'UNK' });
  if (items.length >= 4) Object.assign(items[3], {
    licence: '98765432', restrictions: '21 46', street2: 'PH 1201' });
}

function expectedFields(d) {
  return {
    family_name: d.family, first_name: d.first, middle_name: d.middle.trim(),
    licence_number: d.licence,
    date_of_birth_yyyymmdd: ccyymmdd(d.dob), sex: d.sex,
    street: d.street, city: d.city.trim(), province: 'BC', postal_code: d.postal,
    licence_class: d.dl_class.trim(), restrictions: d.restrictions.trim(),
    endorsements: d.endorsements.trim(),
    height_cm: parseInt(d.height_cm, 10), weight_kg: parseInt(d.weight_kg, 10),
    hair: d.hair, eyes: d.eyes,
    issue_date_yyyymmdd: ccyymmdd(d.issue),
    expiry_date_yyyymmdd: ccyymmdd(d.expiry),
    iin: BC_IIN, country: 'CAN',
  };
}

function batchPayload(ident, mode) {
  return mode === 'bc'
    ? buildBcPayload(ident, { bc_quirk: true, height_mode: 'fi' })
    : buildAamvaPayload(ident, { version: '09', datefmt: 'CCYYMMDD', sep: '\r', hunit: 'cm' });
}

function buildManifest(count, mode, seed, seedUsed) {
  const rng = makeRng(seed);
  const items = [];
  const manifest = {
    generator: 'Canada VR — static build',
    note: 'ALL DATA SYNTHETIC / FICTITIOUS — test fixtures only',
    count, mode, seed: seedUsed, items,
  };
  return { rng, manifest };
}

/* ============ canned sample identities (shared with the server UI) ============ */

const SAMPLES = [
  { family: 'SAMPLECARD', first: 'TEST', middle: 'Q', dob: '1990-05-15', sex: '1',
    street: '123 SAMPLE AVE', street2: '', city: 'VICTORIA', province: 'BC',
    postal: 'V8W 2E4', licence: '1234567', dl_class: '5', restrictions: '',
    endorsements: '', height_cm: '178', height_fi: '510', weight_kg: '080',
    hair: 'BRO', eyes: 'BRO', issue: '2024-01-02', expiry: '2029-05-15',
    iin: '636028', dcf: 'TESTCARD0000001' },
  { family: 'VERYLONGFAMILYNAMEFIXTURE', first: 'EXTRAORDINARILONGFIRSTNAME',
    middle: 'Z', dob: '1988-11-30', sex: '1', street: '4588 WHIFFIN SPIT RD',
    street2: '', city: 'PRINCE GEORGE', province: 'BC', postal: 'V2M 6Z9',
    licence: '27687537', dl_class: '6', restrictions: '21', endorsements: '',
    height_cm: '185', height_fi: '601', weight_kg: '092', hair: 'BLK', eyes: 'BRO',
    issue: '2022-06-14', expiry: '2027-11-30', iin: '636028', dcf: 'TST0000000017' },
  { family: 'SPECIMAN', first: 'JORDAN', middle: '', dob: '2003-04-09', sex: '2',
    street: '77 TERMINAL AVE', street2: '', city: 'NANAIMO', province: 'BC',
    postal: 'V9R 5C6', licence: '58441209', dl_class: '7', restrictions: '46',
    endorsements: '', height_cm: '160', height_fi: '503', weight_kg: '061',
    hair: 'BLN', eyes: 'BLU', issue: '2025-02-19', expiry: '2030-04-09',
    iin: '636028', dcf: 'TST0000000003' },
  { family: 'REGRESS', first: 'ARJUN', middle: 'K', dob: '1995-03-22', sex: '9',
    street: '850 GRANVILLE ST', street2: 'UNIT 1205', city: 'VANCOUVER',
    province: 'BC', postal: 'V6Z 1K3', licence: '92744215', dl_class: '5',
    restrictions: '21 46', endorsements: '', height_cm: '172', height_fi: '508',
    weight_kg: '076', hair: 'UNK', eyes: 'UNK', issue: '2023-09-10',
    expiry: '2028-03-22', iin: '636028', dcf: 'TST0000000042' },
];

function loadSample(panelEl, rngNext = Math.random) {
  const s = SAMPLES[Math.floor(rngNext() * SAMPLES.length)];
  panelEl.querySelectorAll('[data-f]').forEach(el => {
    if (s[el.dataset.f] !== undefined) el.value = s[el.dataset.f];
  });
}

/* ============ ANSI header / subfile designator sanity check (raw mode) ============ */

function designatorCheck(p) {
  const out = [];
  const m = /^@\n\x1e\rANSI ([0-9A-Za-z]{6})(\d{2})(\d{2})(\d{2})/.exec(p);
  if (!m) {
    if (p[0] === '@') out.push('starts with @ but ANSI header is malformed');
    return out;
  }
  const entries = parseInt(m[4], 10), hdrLen = m[0].length,
        dataStart = hdrLen + entries * 10;
  const type = p.substr(hdrLen, 2), off = parseInt(p.substr(hdrLen + 2, 4), 10),
        len = parseInt(p.substr(hdrLen + 6, 4), 10);
  if (off !== dataStart) out.push(`${type} offset says ${off}, correct is ${dataStart}`);
  if (entries === 1) {
    const actual = p.length - dataStart;
    if (len !== actual) out.push(`${type} length says ${len} but actual subfile is ${actual} bytes — strict decoders drop the last ${actual - len} byte(s)`);
  }
  return out;
}

/* ================= helpers ================= */

const interpEscapes = s => s.replace(/\\(x[0-9a-fA-F]{2}|n|r|t|0)/g, (m, e) =>
  e.startsWith('x') ? String.fromCharCode(parseInt(e.slice(1), 16))
                    : { n: '\n', r: '\r', t: '\t', 0: '\0' }[e]);

const escRepr = s => s.replace(/[\x00-\x1f\x7f]/g, c =>
  ({ '\n': '\\n', '\r': '\\r', '\t': '\\t' })[c]
  || '\\x' + c.charCodeAt(0).toString(16).padStart(2, '0'));

function hexDump(s) {
  const bytes = [];
  for (let i = 0; i < s.length; i++) bytes.push(s.charCodeAt(i) & 0xff);
  return bytes.map(b => b.toString(16).padStart(2, '0')).join(' ');
}

function renderToCanvas(payload, { columns = 6, eclevel = 5, scale = 3 } = {}) {
  const canvas = document.createElement('canvas');
  bwipjs.toCanvas(canvas, {
    bcid: 'pdf417', text: payload,
    columns, eclevel, scale, scaleX: scale, scaleY: scale,
  });
  return canvas;
}

/* ================= UI wiring (browser only) ================= */

function collectFields(root) {
  const d = {};
  root.querySelectorAll('input[data-f],select[data-f]').forEach(el => { d[el.dataset.f] = el.value; });
  return d;
}

function renderOpts(root) {
  return {
    columns: +root.querySelector('#rcols').value,
    eclevel: +root.querySelector('#rec').value,
    scale: +root.querySelector('#rscale').value,
  };
}

function wireTabs() {
  document.querySelectorAll('.tabs button[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tabs button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
      document.getElementById('p-' + btn.dataset.tab).classList.add('active');
    });
  });
}

async function onGenerate(mode) {
  const panel = document.getElementById('p-' + mode);
  const errBox = document.getElementById('errbox');
  let payload;
  try {
    if (mode === 'raw') {
      payload = interpEscapes(document.getElementById('raw_payload').value);
    } else {
      const d = Object.assign({}, DEFAULTS, collectFields(panel));
      if (mode === 'bc') {
        payload = buildBcPayload(d, {
          bc_quirk: panel.querySelector('#bc_quirk').value === '1',
          height_mode: panel.querySelector('#height_mode').value,
          joiner: interpEscapes(panel.querySelector('#joiner').value),
        });
      } else if (mode === 'aamva') {
        payload = buildAamvaPayload(d, {
          version: panel.querySelector('#aa_version').value,
          datefmt: panel.querySelector('#aa_datefmt').value,
          sep: panel.querySelector('#aa_sep').value === 'cr' ? '\r' : '\n',
          hunit: panel.querySelector('#aa_hunit').value,
        });
      }
    }
    const canvas = renderToCanvas(payload, renderOpts(panel));
    showResult(payload, canvas);
    errBox.textContent = '';
    if (mode === 'raw') {
      const w = designatorCheck(payload);
      if (w.length) errBox.textContent = '⚠ Designator check: ' + w.join(' · ');
    }
  } catch (exc) {
    document.getElementById('result').style.display = 'block';
    errBox.textContent = 'Error: ' + exc.message;
  }
}

let lastPngUrl = null, lastTxtUrl = null, lastHexUrl = null;
function showResult(payload, canvas) {
  document.getElementById('result').style.display = 'block';
  document.getElementById('bcimg').src = canvas.toDataURL('image/png');
  document.getElementById('ptext').textContent = escRepr(payload);
  document.getElementById('phex').textContent = hexDump(payload);
  if (lastPngUrl) URL.revokeObjectURL(lastPngUrl);
  if (lastTxtUrl) URL.revokeObjectURL(lastTxtUrl);
  if (lastHexUrl) URL.revokeObjectURL(lastHexUrl);
  const dlPng = document.getElementById('dl_png');
  canvas.toBlob(b => {
    lastPngUrl = URL.createObjectURL(b); dlPng.href = lastPngUrl;
  }, 'image/png');
  lastTxtUrl = URL.createObjectURL(new Blob([payload], { type: 'text/plain;charset=latin-1' }));
  document.getElementById('dl_txt').href = lastTxtUrl;
  lastHexUrl = URL.createObjectURL(new Blob([hexDump(payload)], { type: 'text/plain' }));
  document.getElementById('dl_hex').href = lastHexUrl;
  document.getElementById('result').scrollIntoView({ behavior: 'smooth' });
}

let lastZipUrl = null;
async function onBatch() {
  const panel = document.getElementById('p-batch');
  const btn = panel.querySelector('.go');
  const err = document.getElementById('batch_err');
  err.textContent = '';
  btn.disabled = true; btn.textContent = 'Generating…';
  try {
    const count = Math.max(1, Math.min(500, +panel.querySelector('#bcount').value || 50));
    const mode = panel.querySelector('#bmode').value;
    const seedStr = panel.querySelector('#bseed').value;
    const seed = seedStr === '' ? null : (+seedStr >>> 0);
    const seedUsed = seed == null ? (Math.random() * 0x100000000) >>> 0 : seed;
    const { rng, manifest } = buildManifest(count, mode, seed, seedUsed);

    const identities = [];
    for (let i = 0; i < count; i++) identities.push(randomIdentity(rng));
    applyEdgeCases(identities);

    const zip = new JSZip();
    for (let i = 0; i < identities.length; i++) {
      const useMode = mode !== 'mixed' ? mode : (i % 2 === 0 ? 'bc' : 'aamva');
      const payload = batchPayload(identities[i], useMode);
      const base = String(i).padStart(3, '0') + '_' + useMode;
      const canvas = renderToCanvas(payload, renderOpts(panel));
      const blob = await new Promise(r => canvas.toBlob(r, 'image/png'));
      zip.file(`barcodes/${base}.png`, blob);
      zip.file(`payloads/${base}.txt`, payload);
      manifest.items.push({
        index: i, mode: useMode,
        png: `barcodes/${base}.png`,
        payload_file: `payloads/${base}.txt`,
        payload,
        payload_hex: hexDump(payload).replace(/ /g, ''),
        expected: expectedFields(identities[i]),
      });
    }
    zip.file('manifest.json', JSON.stringify(manifest, null, 2));
    const zipBlob = await zip.generateAsync({ type: 'blob' });
    if (lastZipUrl) URL.revokeObjectURL(lastZipUrl);
    lastZipUrl = URL.createObjectURL(zipBlob);
    const a = document.getElementById('dl_zip');
    a.href = lastZipUrl;
    document.getElementById('batch_size').textContent =
      (zipBlob.size / 1024).toFixed(1) + ' KB ready — ' + count +
      ' identities (seed ' + seedUsed + ')';
    document.getElementById('batch_done').style.display = 'block';
  } catch (exc) {
    err.textContent = 'Error: ' + exc.message;
  } finally {
    btn.disabled = false; btn.textContent = 'Generate ZIP';
  }
}

if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    wireTabs();
    document.querySelectorAll('button[data-gen]').forEach(btn =>
      btn.addEventListener('click', () => onGenerate(btn.dataset.gen)));
    document.querySelectorAll('button[data-sample]').forEach(btn =>
      btn.addEventListener('click', () => loadSample(btn.closest('.panel'))));
    document.getElementById('btn_batch').addEventListener('click', onBatch);
    onGenerate('bc');
  });
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    BC_IIN, DEFAULTS, fix, weight3, ccyymmdd, mmddccyy, yymm,
    buildBcTrack1, buildBcTrack2, buildBcTrack3, buildBcPayload,
    buildAamvaPayload, mulberry32, makeRng, randomIdentity,
    applyEdgeCases, expectedFields, interpEscapes, escRepr, hexDump,
    SAMPLES, loadSample, designatorCheck,
  };
}
