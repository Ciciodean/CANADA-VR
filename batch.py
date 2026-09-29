#!/usr/bin/env python3
"""Canada VR — batch generation of synthetic licence test fixtures.

Produces a ZIP containing:
  barcodes/NNN_<mode>.png   – PDF417 barcode image per identity
  payloads/NNN_<mode>.txt   – exact payload string (latin-1)
  manifest.json             – every identity + payload + the field values a
                              correct parser should extract (for assertions)

All identities are fictitious synthetic data.
"""

from __future__ import annotations

import io
import json
import random
import zipfile
from datetime import date, timedelta

from generator import (EYE_CODES, HAIR_CODES, build_aamva_payload,
                       build_bc_payload, render_png_bytes)

FIRST = ["ALEX", "JORDAN", "TAYLOR", "MORGAN", "CASEY", "RILEY", "JAMIE",
         "PRIYA", "WEI", "FATIMA", "LUCAS", "EMMA", "NOAH", "OLIVIA",
         "ARJUN", "SOFIA", "LIAM", "MAYA", "ETHAN", "ZARA"]
LAST = ["TESTER", "SAMPLE", "FIXTURE", "MOCKSMITH", "DATATEST", "PROVABLE",
        "CHECKFIELD", "UNITCASE", "REGRESS", "SPECIMAN", "PLACEHOLDER",
        "DEMOCRAFT", "VALIDOR", "SYNTHETIC", "FAKEMAN", "PARSLEY"]
CITIES = ["VICTORIA", "VANCOUVER", "SURREY", "BURNABY", "KELOWNA", "NANAIMO",
          "KAMLOOPS", "PRINCE GEORGE", "ABBOTSFORD", "RICHMOND", "SAANICH",
          "LANGLEY", "COQUITLAM", "CHILLIWACK", "VERNON"]
STREET_NAMES = ["MAIN ST", "OAK AVE", "CEDAR ST", "MARINE DR", "KINGSWAY",
                "GOVERNMENT ST", "LOUGHEED HWY", "GRANVILLE ST", "DOUGLAS ST",
                "BROADWAY", "FORT ST", "QUADRA ST", "WHIFFIN SPIT RD"]
CLASSES = ["5", "5", "5", "7", "7", "6", "4", "2", "8", "1"]  # BC licence classes
RESTRICTIONS = ["", "", "", "21", "21", "46", "21 46", "15"]
POSTAL_LETTERS = "ABCEGHJKLMNPRSTVXY"


def _rand_date(rng, start, end) -> str:
    delta = (end - start).days
    return (start + timedelta(days=rng.randrange(delta))).isoformat()


def random_identity(rng: random.Random) -> dict:
    ft = rng.choice([5, 5, 5, 5, 6, 6])
    inch = rng.randrange(0, 12)
    cm = round((ft * 12 + inch) * 2.54)
    dob = _rand_date(rng, date(1955, 1, 1), date(2007, 12, 31))
    issue = _rand_date(rng, date(2016, 1, 1), date(2026, 6, 1))
    exp_y = min(int(issue[:4]) + 5, 2031)
    postal = (f"V{rng.randrange(10)}{rng.choice(POSTAL_LETTERS)} "
              f"{rng.randrange(10)}{rng.choice(POSTAL_LETTERS)}{rng.randrange(10)}")
    return {
        "family": rng.choice(LAST),
        "first": rng.choice(FIRST),
        "middle": rng.choice(list("ABCDEFGHJKLMNPQRSTW") + [""] * 4),
        "dob": dob,
        "sex": rng.choice(["1", "1", "2", "2", "9"]),
        "street": f"{rng.randrange(1, 9900)} {rng.choice(STREET_NAMES)}",
        "street2": rng.choice(["", "", "", f"UNIT {rng.randrange(1, 400)}",
                               f"APT {rng.randrange(1, 99)}"]),
        "city": rng.choice(CITIES),
        "province": "BC",
        "postal": postal,
        "licence": f"{rng.randrange(1000000, 99999999)}",
        "dl_class": rng.choice(CLASSES),
        "restrictions": rng.choice(RESTRICTIONS),
        "endorsements": "",
        "height_cm": str(cm),
        "height_fi": f"{ft}{inch:02d}",
        "weight_kg": f"{rng.randrange(45, 121):03d}",
        "hair": rng.choice(HAIR_CODES),
        "eyes": rng.choice(EYE_CODES),
        "issue": issue,
        "expiry": f"{exp_y}{issue[4:]}",
        "phn": f"9{rng.randrange(100000000, 999999999)}",
        "iin": "636028",
        "dcf": f"TST{rng.randrange(10**10):010d}",
        "cds_version": "1",
        "juris_version": "00",
    }


def edge_cases(batch: list[dict]) -> None:
    """Inject deterministic edge cases (overwrite first slots if present)."""
    if len(batch) >= 1:  # long name -> forces truncation in track 1
        batch[0].update(family="VERYLONGFAMILYNAMEFIXTURE",
                        first="EXTRAORDINARILONGFIRSTNAME", middle="Z")
    if len(batch) >= 2:  # minimal: no middle, no unit
        batch[1].update(middle="", street2="")
    if len(batch) >= 3:  # sex X + unknown descriptors
        batch[2].update(sex="9", hair="UNK", eyes="UNK")
    if len(batch) >= 4:  # longest realistic BC licence number + heavy data
        batch[3].update(licence="98765432", restrictions="21 46", street2="PH 1201")


def expected_fields(d: dict) -> dict:
    """Values a correct parser should report for an identity."""
    return {
        "family_name": d["family"].strip(),
        "first_name": d["first"].strip(),
        "middle_name": d["middle"].strip(),
        "licence_number": d["licence"],
        "date_of_birth_yyyymmdd": d["dob"].replace("-", ""),
        "sex": d["sex"],
        "street": d["street"], "city": d["city"].strip(),
        "province": "BC", "postal_code": d["postal"],
        "licence_class": d["dl_class"].strip(),
        "restrictions": d["restrictions"].strip(),
        "endorsements": d["endorsements"].strip(),
        "height_cm": int(d["height_cm"]),
        "weight_kg": int(d["weight_kg"]),
        "hair": d["hair"], "eyes": d["eyes"],
        "issue_date_yyyymmdd": d["issue"].replace("-", ""),
        "expiry_date_yyyymmdd": d["expiry"].replace("-", ""),
        "iin": "636028", "country": "CAN",
    }


def make_batch(count: int, mode: str = "mixed", seed: int | None = None,
               render_kw: dict | None = None) -> bytes:
    """Build the batch ZIP in memory and return its bytes."""
    render_kw = render_kw or {}
    rng = random.Random(seed)
    identities = [random_identity(rng) for _ in range(count)]
    edge_cases(identities)

    buf = io.BytesIO()
    manifest = {"generator": "Canada VR batch mode",
                "note": "ALL DATA SYNTHETIC / FICTITIOUS — test fixtures only",
                "count": count, "mode": mode, "seed": seed, "items": []}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, ident in enumerate(identities):
            use_mode = (mode if mode in ("bc", "aamva")
                        else ("bc" if i % 2 == 0 else "aamva"))
            if use_mode == "bc":
                payload = build_bc_payload(ident, bc_quirk=True,
                                           height_mode="fi")
            else:
                payload = build_aamva_payload(ident, version="09",
                                              datefmt="CCYYMMDD", sep="\r",
                                              height_unit="cm")
            base = f"{i:03d}_{use_mode}"
            zf.writestr(f"barcodes/{base}.png",
                        render_png_bytes(payload, **render_kw))
            zf.writestr(f"payloads/{base}.txt",
                        payload.encode("latin-1"))
            manifest["items"].append({
                "index": i, "mode": use_mode,
                "png": f"barcodes/{base}.png",
                "payload_file": f"payloads/{base}.txt",
                "payload": payload,
                "payload_hex": payload.encode("latin-1").hex(),
                "expected": expected_fields(ident),
            })
        zf.writestr("manifest.json",
                    json.dumps(manifest, indent=2, ensure_ascii=False))
    return buf.getvalue()


def _cli() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Batch-generate synthetic licence "
                                 "test barcodes (ZIP of PNGs + manifest.json).")
    ap.add_argument("--count", type=int, default=50)
    ap.add_argument("--mode", choices=["bc", "aamva", "mixed"], default="mixed")
    ap.add_argument("--seed", type=int, default=None,
                    help="set for reproducible batches")
    ap.add_argument("--columns", type=int, default=6)
    ap.add_argument("--ec", type=int, default=5)
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--out", default="batch_test_set.zip")
    a = ap.parse_args()
    data = make_batch(a.count, a.mode, a.seed,
                      dict(columns=a.columns, security_level=a.ec, scale=a.scale))
    with open(a.out, "wb") as f:
        f.write(data)
    print(f"wrote {a.out} ({len(data):,} bytes, {a.count} synthetic identities)")


if __name__ == "__main__":
    _cli()
