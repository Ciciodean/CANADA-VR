# Canada VR — Driver's-Licence PDF417 Test-Barcode Generator

**Live demo:** https://ciciodean.github.io/CANADA-VR/ (static build — no server needed; everything runs in your browser)

**Repo:** https://github.com/Ciciodean/CANADA-VR

Generates **synthetic** PDF417 barcodes shaped like British Columbia and generic
AAMVA driver's-licence barcodes — for unit-testing barcode parsers, ID-scanning
flows, and verification software.

> ⚠️ **Test data only.** All default values are fictitious. Creating or using
> fabricated barcodes as real identification is a crime.

## Quick start

```bash
pip install -r requirements.txt
python app.py            # web UI on http://localhost:8080
```

## CLI

```bash
# BC combined-card style (mag-stripe tracks + BC "_%" quirk)
python generator.py bc --out bc_test.png

# Standard AAMVA DL-subfile (ANSI header, element IDs, BC jurisdiction values)
python generator.py aamva --version 09 --out aamva_test.png

# Render a payload you captured/crafted yourself
python generator.py raw --raw-file specimen.txt --out specimen.png

# Batch: 50 randomized synthetic identities (ZIP of PNGs + payloads + manifest.json)
python batch.py --count 50 --mode mixed --seed 42 --out batch_test_set.zip
```

The batch ZIP contains:

```
barcodes/000_bc.png ...        payloads/000_bc.txt ...        manifest.json
```

`manifest.json` holds, per item: the payload (text + hex) and an `expected`
block with the values a correct parser should extract (name, licence number,
dates as `yyyymmdd`, class, height/weight, etc.) — ready for test assertions.
Slots 0–3 are **deterministic edge cases**: name truncation, missing middle
name/address line 2, sex `X`, and maximum-size/heavy data. Pass `--seed` for
reproducible batches. The same batch is available in the web UI under the
**Batch → ZIP** tab.


Every sample shows the exact payload (`repr` + byte length) and can also dump the
raw payload to a file with `--payload-out payload.bin` — handy for unit tests that
feed strings directly to your parser instead of scanning images.

## Formats emitted

### `bc` mode (default)
Mirrors the Province of BC "Card Specifications – Combined Card" documentation:
the PDF417 contains AAMVA *magnetic-stripe* tracks 1–3:

```
%BCVICTORIA^SAMPLECARD$TEST$Q^123 SAMPLE AVE?;6360281234567=290519900515?_%10V8W2E4     5           1   080BROBRO?
```

* Track 1 – `%` province, city, `FAMILY$FIRST$MIDDLE`, address
* Track 2 – `;` IIN `636028`, licence number, `=`, expiry `YYMM`, DOB `CCYYMMDD`
* Track 3 – BC's two-char constant `_%` (offset +1!), CDS/jurisdiction versions,
  postal(11), class(2), restrictions(10), endorsements(4), sex, height, weight(kg),
  hair, eyes, `?`

Toggle `--no-bc-quirk` for a standard `%`, and `--height-mode cm|fi` for the
Track-3 height encoding.

### `aamva` mode
Standard subfile format used across North America:

```
@\n\x1e\rANSI 636028090001DL00310194DLDCA5\rDCBNONE\r...DAQ1234567\rDCG CAN\r...
```

Versions 02–10 selectable; dates `CCYYMMDD` (Canada) or `MMDDCCYY` (US);
element separator CR or LF.

### `raw` mode
Paste any payload (escape sequences `\n`, `\r`, `\x1e` interpreted) to reproduce a
specimen your software met in the wild.

## Library use

```python
from generator import DEFAULTS, build_bc_payload, build_aamva_payload, render_png_bytes

d = dict(DEFAULTS, family="DOE", first="JANE")
png_bytes = render_png_bytes(build_bc_payload(d), columns=6, security_level=5)
```

## Notes & caveats

* All barcodes are **unencrypted plain text**, exactly like the real cards.
* Real BC cards differ slightly between card generations; if your software cares
  about a specific generation, scan one with a generic PDF417 app and paste the
  payload into **Raw mode** to clone its structure.
* PDF417 symbol geometry is tunable (columns, error-correction level, module
  scale) so you can test your scanner across symbol densities.
