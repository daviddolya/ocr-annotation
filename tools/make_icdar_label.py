#!/usr/bin/env python3
"""Готовый конфиг метки для CVAT: полигон плюс транскрипция (P4e, шаг 4).

Здесь важны два имени, и оба заданы форматом, а не вкусом:

  * метка называется `icdar` — так требует формат ICDAR при импорте
    (docs.cvat.ai/docs/dataset_management/formats/format-icdar/);
  * атрибут называется ровно `text` — экспортёр datumaro читает
    именно это имя (plugins/data_formats/icdar/exporter.py,
    IcdarTextLocalizationExporter). Назовёшь «transcription» —
    полигоны выгрузятся без текста, и заметишь ты это уже после разметки.

Атрибут делается mutable: транскрипцию правят, не перерисовывая контур.

    python3 tools/make_icdar_label.py --out cvat_icdar_label.json

Дальше содержимое файла целиком вставляется во вкладку Raw редактора меток.
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
            "values": [],
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
    print(f"{args.out}: метка «{spec[0]['name']}» типа {spec[0]['type']}, "
          f"атрибут «{a['name']}» типа {a['input_type']}")
    print("экспортировать потом в формат ICDAR Text Localization 1.0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
