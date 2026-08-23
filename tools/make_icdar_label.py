#!/usr/bin/env python3
"""A ready-made CVAT label config: polygon plus transcription.

Two names matter here, and both are dictated by the format rather than taste:

  * the label is called `icdar` -- that is what the ICDAR format requires on
    import (docs.cvat.ai/docs/dataset_management/formats/format-icdar/);
  * the attribute is called exactly `text` -- the datumaro exporter reads that
    name and no other (plugins/data_formats/icdar/exporter.py,
    IcdarTextLocalizationExporter). Name it "transcription" and the polygons
    export without any text, which you only notice after annotating.

The attribute is mutable: a transcription gets corrected without redrawing
the contour. Its `values` list holds one empty string rather than nothing at
all -- CVAT's raw label editor rejects an empty array outright.

    python3 tools/make_icdar_label.py --out cvat_icdar_label.json

The contents of the file then go into the Raw tab of the label editor.
"""

import argparse
import json
from pathlib import Path


def build(label: str = "icdar", attribute: str = "text") -> list[dict]:
    return [{
        "name": label,
        "type": "polygon",
        "attributes": [{
            "name": attribute,
            "input_type": "text",
            "mutable": True,
            "values": [""],
            "default_value": "",
        }],
    }]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=Path("cvat_icdar_label.json"))
    ap.add_argument("--label", default="icdar")
    ap.add_argument("--attribute", default="text")
    args = ap.parse_args()

    spec = build(args.label, args.attribute)
    args.out.write_text(json.dumps(spec, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    a = spec[0]["attributes"][0]
    print(f"{args.out}: label \"{spec[0]['name']}\" of type {spec[0]['type']}, "
          f"attribute \"{a['name']}\" of type {a['input_type']}")
    print("export later to the ICDAR Text Localization 1.0 format")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
