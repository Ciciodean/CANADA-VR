#!/usr/bin/env python3
"""
Canada VR — BC / AAMVA driver's-licence PDF417 **test-data** generator.

Builds *synthetic* payloads for software testing, in two well-documented styles:

  1. ``bc``     – BC combined Driver's Licence & Services Card style:
                  AAMVA *magnetic-stripe track* layout inside the PDF417,
                  including BC's documented two-character ``_%`` Track-3
                  constant (Province of BC MSP Teleplan spec v4.4).
  2. ``aamva``  – Standard AAMVA DL/ID subfile format (element IDs: DAQ,
                  DCS, DBB, ...) with a proper ANSI header. Defaults to BC
                  jurisdiction values (IIN 636028, DAJ=BC, DCG=CAN).

A ``raw`` mode renders any payload you paste, so you can reproduce specimens
your software actually encountered in the field.

DISCLAIMER: This tool exists to produce SYNTHETIC TEST FIXTURES for parser /
verification software. Producing or using fabricated barcodes as real
identification is a criminal offence (Canada Criminal Code: forgery,
identity fraud).
"""

from __future__ import annotations

import argparse
import base64
import io
import sys
from datetime import date

import pdf417gen

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

BC_IIN = "636028"  # British Columbia, per AAMVA IIN registry

HAIR_CODES = ["BAL", "BLK", "BLN", "BRO", "GRY", "RED", "WHI", "SDY", "UNK"]
EYE_CODES = ["BLK", "BLU", "BRO", "GRN", "GRY", "HAZ", "MAR", "PNK", "UNK"]

# Obviously-synthetic defaults (override everything via CLI flags or the UI).
DEFAULTS = dict(
    family="SAMPLECARD",
    first="TEST",
    middle="Q",
    dob="1990-05-15",
    sex="1",                       # 1 = male, 2 = female, 9 = X/other
    street="123 SAMPLE AVE",
    street2="",
    city="VICTORIA",
    province="BC",
    postal="V8W 2E4",
    licence="1234567",
    dl_class="5",
    restrictions="",
    endorsements="",
    height_cm="178",
    height_fi="510",               # feet+inches, e.g. 5'10" -> 510
    weight_kg="080",
    hair="BRO",
    eyes="BRO",
    issue="2024-01-02",
    expiry="2029-05-15",
    phn="9123456789",              # BC PHNs start with 9; this is synthetic
    iin=BC_IIN,
    dcf="TESTCARD0000001",
    cds_version="1",
    juris_version="00",
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _d(s: str) -> date:
    return date.fromisoformat(s)


def _ccyymmdd(s: str) -> str:
    return _d(s).strftime("%Y%m%d")


def _mmddccyy(s: str) -> str:
    return _d(s).strftime("%m%d%Y")


def _yymm(s: str) -> str:
    return _d(s).strftime("%y%m")


def _fix(s: str, width: int, pad: str = " ") -> str:
    """Uppercase, truncate/pad to fixed width."""
    return str(s).upper().ljust(width, pad)[:width]


# ---------------------------------------------------------------------------
# 1. BC magnetic-stripe-track payload (combined card style)
# ---------------------------------------------------------------------------

def build_bc_track1(d: dict) -> str:
    """Track 1: % + province + city + ^ + FAMILY$FIRST$MIDDLE + ^ + addr + ?"""
    city = d["city"].upper()[:13]
    name = f"{d['family']}${d['first']}${d['middle']}".upper().rstrip("$")[:35]
    addr = d["street"].upper()
    if d["street2"]:
        addr = (addr + "$" + d["street2"].upper())[:29]
    else:
        addr = addr[:29]
    out = "%" + _fix(d["province"], 2)
    out += city + ("^" if len(city) < 13 else "")
    out += name + ("^" if len(name) < 35 else "")
    out += addr + "?"
    return out


def build_bc_track2(d: dict) -> str:
    """Track 2: ; + IIN + DL# + = + expiry YYMM + DOB CCYYMMDD + overflow + ?"""
    dlnum = "".join(ch for ch in d["licence"].upper() if ch.isalnum())
    overflow = ""
    if len(dlnum) > 13:
        dlnum, overflow = dlnum[:13], dlnum[13:18]
    out = ";" + d["iin"] + dlnum + "=" + _yymm(d["expiry"]) + _ccyymmdd(d["dob"])
    if overflow:
        out += overflow
    out += "?"
    return out


def build_bc_track3(d: dict, bc_quirk: bool = True, height_mode: str = "fi") -> str:
    """Track 3: BC ' _%' constant + fixed fields + ?

    Layout (verified against py-aamva issue #3 offsets):
      [0..1]  constant '%'  (BC: '_%', 2 chars -> everything shifts +1)
      [2]     CDS version      [3]  jurisdiction version
      [4..14] postal (11)      [15..16] class (2)
      [17..26] restrictions (10) [27..30] endorsements (4)
      [31]    sex (1)          [32..34] height (3)
      [35..37] weight (3)      [38..40] hair (3)  [41..43] eyes (3)
      [44]    '?' end sentinel
    """
    sentinel = "_%" if bc_quirk else "%"
    height = _fix(d["height_cm"] if height_mode == "cm" else d["height_fi"], 3)
    out = (
        sentinel
        + _fix(d["cds_version"], 1)
        + _fix(d["juris_version"][-1:], 1)
        + _fix(d["postal"].replace(" ", ""), 11)
        + _fix(d["dl_class"], 2)
        + _fix(d["restrictions"], 10)
        + _fix(d["endorsements"], 4)
        + _fix(d["sex"], 1)
        + height
        + d["weight_kg"].zfill(3)[-3:]           # kg, zero-padded
        + _fix(d["hair"], 3)
        + _fix(d["eyes"], 3)
        + "?"
    )
    return out


def build_bc_payload(d: dict, bc_quirk: bool = True, height_mode: str = "fi",
                     joiner: str = "") -> str:
    return joiner.join([
        build_bc_track1(d),
        build_bc_track2(d),
        build_bc_track3(d, bc_quirk=bc_quirk, height_mode=height_mode),
    ])


# ---------------------------------------------------------------------------
# 2. Standard AAMVA DL-subfile payload
# ---------------------------------------------------------------------------

def build_aamva_payload(d: dict, version: str = "09",
                        datefmt: str = "CCYYMMDD",
                        sep: str = "\r",
                        height_unit: str = "cm") -> str:
    dfmt = _ccyymmdd if datefmt == "CCYYMMDD" else _mmddccyy
    if height_unit == "cm":
        dau = f"{int(d['height_cm']):03d} cm"
    else:
        ft, inch = int(d["height_fi"][0]), int(d["height_fi"][1:])
        dau = f"{ft * 12 + inch:03d} in"

    elements = [
        ("DCA", d["dl_class"].upper()),              # jurisdiction vehicle class
        ("DCB", d["restrictions"].upper() or "NONE"),
        ("DCD", d["endorsements"].upper() or "NONE"),
        ("DBA", dfmt(d["expiry"])),
        ("DCS", d["family"].upper()),
        ("DAC", d["first"].upper()),
        ("DAD", d["middle"].upper()),
        ("DBD", dfmt(d["issue"])),
        ("DBB", dfmt(d["dob"])),
        ("DBC", d["sex"]),
        ("DAY", d["eyes"].upper()),
        ("DAU", dau),
        ("DAG", d["street"].upper()),
        ("DAI", d["city"].upper()),
        ("DAJ", d["province"].upper()),
        ("DAK", _fix(d["postal"].replace(" ", ""), 11)),
        ("DAQ", d["licence"]),
        ("DCF", d["dcf"]),
        ("DCG", "CAN"),
        ("DDE", "N"), ("DDF", "N"), ("DDG", "N"),   # truncation flags
    ]
    subfile = sep.join(f"{k}{v}" for k, v in elements) + sep

    entries = 1
    header = (
        "@\n\x1e\rANSI "
        + d["iin"]
        + version.zfill(2)
        + d["juris_version"].zfill(2)
        + str(entries).zfill(2)
    )
    offset = len(header.encode("latin-1")) + entries * 10
    designator = "DL" + str(offset).zfill(4) + str(len(subfile.encode("latin-1"))).zfill(4)
    return header + designator + subfile


# ---------------------------------------------------------------------------
# 3. PDF417 rendering
# ---------------------------------------------------------------------------

def render_pdf417(payload: str, columns: int = 6, security_level: int = 5,
                  scale: int = 3, ratio: int = 3, padding: int = 10):
    """Encode payload as PDF417 and return a PIL Image."""
    codes = pdf417gen.encode(payload, columns=columns, security_level=security_level)
    return pdf417gen.render_image(codes, scale=scale, ratio=ratio, padding=padding)


def render_png_bytes(payload: str, **kw) -> bytes:
    img = render_pdf417(payload, **kw)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_png_b64(payload: str, **kw) -> str:
    return base64.b64encode(render_png_bytes(payload, **kw)).decode()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    ap = argparse.ArgumentParser(
        description="Generate SYNTHETIC BC/AAMVA driver's-licence PDF417 test barcodes.")
    ap.add_argument("mode", choices=["bc", "aamva", "raw"])
    ap.add_argument("--out", default="barcode_test.png", help="output PNG path")
    ap.add_argument("--payload-out", default=None, help="also dump raw payload to this file")
    ap.add_argument("--columns", type=int, default=6)
    ap.add_argument("--ec", type=int, default=5, help="PDF417 error-correction level 0-8")
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--raw-file", default=None, help="payload file for raw mode")
    ap.add_argument("--version", default="09", help="AAMVA version (aamva mode)")
    ap.add_argument("--datefmt", default="CCYYMMDD", choices=["CCYYMMDD", "MMDDCCYY"])
    ap.add_argument("--sep", default="cr", choices=["cr", "lf"], help="element separator")
    ap.add_argument("--height-mode", default="fi", choices=["fi", "cm"], help="bc mode height format")
    ap.add_argument("--no-bc-quirk", action="store_true", help="use standard '%' not '_%'")
    ap.add_argument("--no-png", action="store_true", help="print payload only")
    for key in DEFAULTS:
        ap.add_argument(f"--{key.replace('_', '-')}", default=None)
    args = ap.parse_args()

    data = dict(DEFAULTS)
    for key in DEFAULTS:
        val = getattr(args, key, None)
        if val is not None:
            data[key] = val

    if args.mode == "bc":
        payload = build_bc_payload(data, bc_quirk=not args.no_bc_quirk,
                                   height_mode=args.height_mode)
    elif args.mode == "aamva":
        payload = build_aamva_payload(data, version=args.version,
                                      datefmt=args.datefmt,
                                      sep="\r" if args.sep == "cr" else "\n",
                                      height_unit="cm")
    else:
        if not args.raw_file:
            ap.error("raw mode needs --raw-file")
        payload = open(args.raw_file, "r", encoding="latin-1").read()

    print("── payload (repr) ──")
    print(repr(payload))
    print(f"── {len(payload.encode('latin-1'))} bytes ──")
    if args.payload_out:
        with open(args.payload_out, "w", encoding="latin-1", newline="") as f:
            f.write(payload)
        print(f"payload written to {args.payload_out}")

    if not args.no_png:
        png = render_png_bytes(payload, columns=args.columns,
                               security_level=args.ec, scale=args.scale)
        with open(args.out, "wb") as f:
            f.write(png)
        print(f"barcode written to {args.out}")


if __name__ == "__main__":
    sys.exit(_cli())
