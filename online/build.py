#!/usr/bin/env python3
"""Build the self-contained static page: online/index.html
Inlines bwip-js (PDF417 renderer), JSZip (batch ZIPs) and src/app.js into
shell.html. No network needed at runtime — one file, host anywhere."""

import pathlib

HERE = pathlib.Path(__file__).resolve().parent
BUILD = HERE.parent / "online-build" / "node_modules"

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

DEFAULTS = dict(family="SAMPLECARD", first="TEST", middle="Q", dob="1990-05-15",
                sex="1", street="123 SAMPLE AVE", street2="", city="VICTORIA",
                province="BC", postal="V8W 2E4", licence="1234567", dl_class="5",
                restrictions="", endorsements="", height_cm="178", height_fi="510",
                weight_kg="080", hair="BRO", eyes="BRO", issue="2024-01-02",
                expiry="2029-05-15", phn="9123456789", iin="636028",
                dcf="TESTCARD0000001", cds_version="1", juris_version="00")

HAIR = ["BAL", "BLK", "BLN", "BRO", "GRY", "RED", "WHI", "SDY", "UNK"]
EYES = ["BLK", "BLU", "BRO", "GRN", "GRY", "HAZ", "MAR", "PNK", "UNK"]


def fields_html() -> str:
    cells = [f'<div><label>{lab}</label>'
             f'<input data-f="{k}" value="{DEFAULTS[k]}"></div>'
             for k, lab in FIELD_SPEC]
    for name, codes in (("hair", HAIR), ("eyes", EYES)):
        opts = "".join(
            f'<option{" selected" if c == "BRO" else ""}>{c}</option>'
            for c in codes)
        cells.append(f'<div><label>{name.title()}</label>'
                     f'<select data-f="{name}">{opts}</select></div>')
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


def main() -> None:
    shell = (HERE / "shell.html").read_text()
    shell = shell.replace("__FIELDS__", fields_html())
    shell = shell.replace("__RENDER_OPTS__", RENDER_OPTS)

    bwipjs = (BUILD / "bwip-js" / "dist" / "bwip-js-min.js").read_text()
    jszip = (BUILD / "jszip" / "dist" / "jszip.min.js").read_text()
    app = (HERE / "src" / "app.js").read_text()

    for marker in ("/*__BWIPJS__*/", "/*__JSZIP__*/", "/*__APP__*/"):
        assert marker in shell, f"missing marker {marker}"
    for name, code in (("bwipjs", bwipjs), ("jszip", jszip), ("app", app)):
        assert "</script" not in code.lower(), f"{name} contains </script>"

    out = (shell.replace("/*__BWIPJS__*/", bwipjs)
                .replace("/*__JSZIP__*/", jszip)
                .replace("/*__APP__*/", app))
    dest = HERE / "index.html"
    dest.write_text(out)
    print(f"built {dest} ({len(out) / 1024:.0f} KB, single file)")


if __name__ == "__main__":
    main()
