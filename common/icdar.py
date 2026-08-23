#!/usr/bin/env python3
"""Формат текстовых полигонов: эталон Total-Text и экспорт CVAT (P4e).

Два формата, и они почти зеркальны — поэтому загрузчик один.

ЭТАЛОН Total-Text, файл на кадр `poly_gt_<image>.txt`, строка на объект:

    x: [[206 251 386]], y: [[633 811 931]], ornt: [u'c'], transcriptions: [u'PETROSAINS']

Координаты бывают перенесены на несколько строк — читать построчно нельзя,
записи склеиваются до полной. На наивном разборе теряется 11 строк из 2547.
Поле `ornt` — ориентация текста: c кривой, h горизонтальный, m наклонный,
# нечитаемый. Поле `transcriptions` со значением `#` означает «прочитать
нельзя»; таких в тестовом наборе 332 из 2547.

ЭКСПОРТ CVAT, формат ICDAR Text Localization 1.0, файл на кадр
`gt_<image>.txt`, строка на объект:

    206,633,251,811,386,931,"PETROSAINS"

Проверено по исходнику datumaro (plugins/data_formats/icdar/exporter.py,
IcdarTextLocalizationExporter): координаты через запятую, дальше в кавычках
значение атрибута с именем ровно `text`. Ориентации там нет — она есть
только у эталона, и разбивка по ней делается по эталонной стороне пары.

Зависимостей нет.
"""

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

# Общепринятые пометки «прочитать нельзя»: Total-Text ставит '#',
# датасеты ICDAR — '###'. Принимаем обе, чтобы не спорить о числе решёток.
ILLEGIBLE = {"#", "##", "###"}

_HEAD = re.compile(r"^x:\s*\[\[")
_FULL = re.compile(
    r"x:\s*\[\[(.*?)\]\]\s*,\s*y:\s*\[\[(.*?)\]\]\s*,"
    r"\s*ornt:\s*\[(.*?)\]\s*,\s*transcriptions:\s*\[(.*?)\]\s*$", re.S)
_QUOTED = re.compile(r"^u?['\"](.*)['\"]$", re.S)


@dataclass
class TextObject:
    """Один текстовый объект: контур плюс транскрипция."""

    image: str
    ring: list[tuple[float, float]]
    text: str
    ornt: str = ""                      # только у эталона
    ident: int = 0
    attrs: dict = field(default_factory=dict)

    @property
    def legible(self) -> bool:
        """Читаемо ли — по мнению того, кто размечал."""
        return bool(self.text) and self.text not in ILLEGIBLE

    @property
    def vertices(self) -> int:
        return len(self.ring)

    def bbox(self) -> tuple[float, float, float, float]:
        xs = [p[0] for p in self.ring]
        ys = [p[1] for p in self.ring]
        return min(xs), min(ys), max(xs), max(ys)

    def bbox_ring(self) -> list[tuple[float, float]]:
        """Описанный прямоугольник как контур — для замера «цены прямоугольника»."""
        x0, y0, x1, y1 = self.bbox()
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

    def flat(self) -> list[float]:
        return [c for p in self.ring for c in p]

    def area_hint(self) -> float:
        x0, y0, x1, y1 = self.bbox()
        return (x1 - x0) * (y1 - y0)


def _unquote(group: str) -> str:
    g = group.strip()
    m = _QUOTED.match(g)
    return m.group(1) if m else g


def parse_totaltext_file(path: Path, image: str) -> list[TextObject]:
    out: list[TextObject] = []
    buf = ""
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip()
        if not s:
            continue
        buf = s if _HEAD.match(s) else (buf + " " + s if buf else s)
        m = _FULL.match(buf)
        if not m:
            continue
        xs = [float(v) for v in m.group(1).split()]
        ys = [float(v) for v in m.group(2).split()]
        if len(xs) != len(ys):
            raise ValueError(f"{path}: {len(xs)} иксов против {len(ys)} игреков")
        out.append(TextObject(image=image, ring=list(zip(xs, ys)),
                              text=_unquote(m.group(4)), ornt=_unquote(m.group(3)),
                              ident=len(out) + 1))
        buf = ""
    return out


def load_totaltext(directory: str | Path, images: set[str] | None = None
                   ) -> list[TextObject]:
    out: list[TextObject] = []
    for p in sorted(Path(directory).glob("poly_gt_*.txt")):
        image = p.stem.replace("poly_gt_", "") + ".jpg"
        if images is not None and image not in images:
            continue
        out.extend(parse_totaltext_file(p, image))
    return out


def parse_icdar_file(path: Path, image: str) -> list[TextObject]:
    out: list[TextObject] = []
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        s = raw.strip()
        if not s:
            continue
        text = ""
        head = s
        if '"' in s:
            first = s.index('"')
            last = s.rindex('"')
            head = s[:first].rstrip(", ")
            text = s[first + 1:last]
        nums = [float(v) for v in re.split(r"[,\s]+", head) if v]
        if len(nums) < 6 or len(nums) % 2:
            continue
        ring = [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
        out.append(TextObject(image=image, ring=ring, text=text,
                              ident=len(out) + 1))
    return out


def load_cvat_icdar(directory: str | Path, images: set[str] | None = None
                    ) -> list[TextObject]:
    """Экспорт лежит либо плоско, либо в подкаталоге подмножества."""
    root = Path(directory)
    files = sorted(root.rglob("gt_*.txt"))
    out: list[TextObject] = []
    for p in files:
        if p.name.startswith("poly_gt_"):
            continue
        image = p.stem[3:] + ".jpg"
        if images is not None and image not in images:
            continue
        out.extend(parse_icdar_file(p, image))
    return out


def load_any(directory: str | Path, images: set[str] | None = None
             ) -> list[TextObject]:
    """Определяет формат по именам файлов. Эталон и экспорт различаются
    префиксом: poly_gt_ против gt_."""
    root = Path(directory)
    if any(root.rglob("poly_gt_*.txt")):
        return load_totaltext(root, images)
    return load_cvat_icdar(root, images)


def save_icdar(objs: list[TextObject], directory: str | Path) -> int:
    """Пишет в формате экспорта CVAT. Нужно для репетиции конвейера."""
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    grouped = by_image(objs)
    for image, items in grouped.items():
        lines = []
        for o in items:
            coords = ",".join(f"{c:g}" for c in o.flat())
            lines.append(f'{coords},"{o.text}"')
        (root / f"gt_{Path(image).stem}.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8")
    return len(grouped)


def by_image(objs: list[TextObject]) -> dict[str, list[TextObject]]:
    out: dict[str, list[TextObject]] = {}
    for o in objs:
        out.setdefault(o.image, []).append(o)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Что лежит в каталоге разметки")
    ap.add_argument("directory", type=Path)
    args = ap.parse_args()
    objs = load_any(args.directory)
    legible = [o for o in objs if o.legible]
    print(f"кадров {len(by_image(objs))}, объектов {len(objs)}, "
          f"читаемых {len(legible)}, нечитаемых {len(objs) - len(legible)}")
    print(f"вершин всего {sum(o.vertices for o in objs)}, "
          f"символов в транскрипциях {sum(len(o.text) for o in legible)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
