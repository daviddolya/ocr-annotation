#!/usr/bin/env python3
"""Сборка README из метрик и разбора пар (P4e, шаг 6).

Приём перенесён из A2, A3 и A4 и работает так же: числа генерируются из
reports/ocr_metrics.json, а твои комментарии сохраняются. Текст между
маркерами <!-- note:ключ --> и <!-- /note --> вычитывается из существующего
README и переносится в новый, поэтому пересборка ничего не затирает.

Единица раздела здесь — ПАРА «эталонное слово — моё слово», и у каждой
подписаны обе оси: IoU и CER. Смысл именно в том, чтобы они стояли рядом.

    .venv/bin/python tools/build_readme.py
"""

import argparse
import json
import re
from pathlib import Path

PLACEHOLDER = "> **Что здесь произошло:** _заполнить_"
NOTE_RE = re.compile(r"<!-- note:(?P<key>[^\s>]+) -->\n(?P<body>.*?)\n<!-- /note -->",
                     re.DOTALL)


def existing_notes(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return {m.group("key"): m.group("body").strip()
            for m in NOTE_RE.finditer(path.read_text(encoding="utf-8"))}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--metrics", type=Path, default=Path("reports/ocr_metrics.json"))
    p.add_argument("--readme", type=Path, default=Path("README.md"))
    p.add_argument("--review", default="reports/review")
    p.add_argument("--repo", default="ocr-annotation-agreement")
    a = p.parse_args()

    m = json.loads(a.metrics.read_text(encoding="utf-8"))
    notes = existing_notes(a.readme)
    review = Path(a.review)
    manifest = review / "pairs_manifest.json"
    pairs = (json.loads(manifest.read_text(encoding="utf-8"))
             if manifest.exists() else [])

    out = [f"# {a.repo}", "",
           "Согласованность разметки текста в сцене: полигон по границе слова",
           "плюс транскрипция. Каждый объект размечен дважды по сути, и метрики",
           f"тоже две, разной природы. {m['frames']} кадров Total-Text размечены вручную",
           "вслепую от эталона.",
           "Этап A5 портфолио по контролю качества разметки.", "",
           "<!-- note:intro -->", notes.get("intro", PLACEHOLDER), "<!-- /note -->", "",
           "## Результат", "", "| | |", "|---|---|",
           f"| кадров | {m['frames']} |",
           f"| объектов своих / эталонных | {m['my_objects']} / {m['gt_objects']} |",
           f"| сопоставлено пар | {m['matched']} |",
           f"| **mask IoU на парах** | **{m['iou_mean']:.3f}** |",
           f"| **CER** | **{m['cer']:.3f}** |",
           f"| WER | {m['wer']:.3f} |",
           f"| совпало дословно | {m['exact_matches']} из {m['text_pairs']} |",
           f"| согласие по «читаемо / нечитаемо» | {m['legibility_agreement']:.3f} |",
           f"| каппа Коэна по читаемости | {m['legibility_kappa']:.3f} |", "",
           f"Порог сопоставления — mask IoU {m['iou_threshold']}. Средний IoU считается",
           "только по сопоставленным парам, поэтому рядом обязана стоять строка",
           f"«без пары»: эталонных {m['unmatched_gt']}, своих {m['unmatched_mine']}. "
           "Объект, обведённый совсем",
           "мимо, в пару не попадает и средний IoU не портит — он уходит туда.", ""]

    out += ["## Геометрия или текст", "",
            "Главный вопрос этапа. Две оси меряют разное, и усреднять их в одно",
            "число нельзя: контур чинится правилом о границах, транскрипция —",
            "правилом о регистре и пунктуации.", ""]
    if m.get("iou_by_orientation"):
        out += ["| ориентация эталонного текста | пар | средний IoU |", "|---|---|---|"]
        for name, v in sorted(m["iou_by_orientation"].items(), key=lambda kv: kv[1]["iou"]):
            out.append(f"| {name} | {v['pairs']} | {v['iou']:.3f} |")
        out.append("")
    if (review / "iou_by_orientation.png").exists():
        out += [f"![IoU по ориентациям]({a.review}/iou_by_orientation.png)", ""]
    if (review / "geometry_vs_text.png").exists():
        out += ["Точка на пару: по горизонтали геометрия, по вертикали текст.",
                "Расхождения, собравшиеся у одной оси, — это разные проблемы",
                "с разными лечениями.", "",
                f"![геометрия против текста]({a.review}/geometry_vs_text.png)", ""]

    out += ["## Сколько ошибки объясняется конвенцией", "",
            f"CER как есть — **{m['cer']:.3f}**. Тот же расчёт после приведения обеих",
            f"сторон к нижнему регистру — **{m['cer_case_insensitive']:.3f}**. Разница и есть та часть",
            "ошибки, которая объясняется правилом записи, а не чтением: "
            f"**{m['case_share']:.0%}**.", "",
            f"CER посчитан микроусреднением (правки, делённые на все "
            f"{m['ref_chars']} символов эталона);",
            f"макро, то есть среднее по объектам, дало бы {m['cer_macro']:.3f}. "
            "Разница между ними",
            "тем больше, чем короче слова, поэтому в отчёте называется, какое взято.", ""]

    out += ["## Читаемо или нет", "",
            "Отдельная ось, которой не видят ни IoU, ни CER: объект, который я",
            "счёл нечитаемым, а эталон прочитал, просто выпадает из расчёта CER",
            "и молча его улучшает.", "",
            "| эталон \\ моё | читаемо | нечитаемо |", "|---|---|---|",
            f"| читаемо | {m['legibility_matrix'][0][0]} | {m['legibility_matrix'][0][1]} |",
            f"| нечитаемо | {m['legibility_matrix'][1][0]} | {m['legibility_matrix'][1][1]} |",
            "",
            f"Доля совпадений {m['legibility_agreement']:.3f} при каппе "
            f"{m['legibility_kappa']:.3f}: каппа стоит рядом потому,",
            "что при редком классе доля совпадений высока сама по себе.", ""]

    if pairs:
        out += ["## Разбор худших пар", "",
                "Синий — эталон, оранжевый — моё. У каждой пары подписаны обе оси.", ""]
        for item in pairs:
            key = f"{Path(item['image']).stem}_{item['gt_id']}"
            cer_text = "—" if item["cer"] is None else f"{item['cer']:.3f}"
            axis = "геометрия" if item["source"] == "geometry" else "текст"
            out += [f"### {item['image']} · эталон #{item['gt_id']} · {axis}", "",
                    f"IoU {item['iou']:.3f} · CER {cer_text} · "
                    f"«{item['gt_text']}» против «{item['my_text']}»", "",
                    f"![{key}]({a.review}/{item['file']})", "",
                    f"<!-- note:{key} -->", notes.get(key, PLACEHOLDER),
                    "<!-- /note -->", ""]

    out += ["## Что дальше", "",
            "- Инструкция и решения по спорным случаям — "
            "[annotation/GUIDELINES.md](annotation/GUIDELINES.md)",
            "- Полный отчёт — [reports/ocr_report.md](reports/ocr_report.md)",
            "- Долг по написанному не мной коду — [DEBT.md](DEBT.md)", "",
            "README пересобирается `tools/build_readme.py`; комментарии между маркерами",
            "`<!-- note:… -->` и `<!-- /note -->` при пересборке сохраняются.", ""]

    a.readme.write_text("\n".join(out), encoding="utf-8")
    kept = sum(1 for v in notes.values() if v != PLACEHOLDER)
    print(f"{a.readme}: разделов по парам {len(pairs)}, "
          f"сохранено комментариев {kept}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
