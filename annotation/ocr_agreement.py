#!/usr/bin/env python3
"""Согласие по текстовой разметке: геометрия и текст отдельно (P4e, шаг 5).

Главный код этапа. Конвейер из четырёх стадий, и главное в нём — что
стадии 2 и 3 меряют РАЗНЫЕ вещи и не сводятся в одно число.

  1. КОГО С КЕМ СРАВНИВАТЬ. Внутри кадра мои контуры сопоставляются
     с эталонными жадно по убыванию mask IoU, порог 0.5. Код сопоставления
     перенесён из A2 (common/polygons.py, match_polys).
     Смещение, которое отсюда следует, надо назвать в отчёте: средний IoU
     считается ТОЛЬКО по сопоставленным парам, а объект, обведённый совсем
     мимо, в пару не попадёт и метрику не испортит — он окажется в строке
     «без пары». Поэтому оба числа приводятся рядом.

  2. ГЕОМЕТРИЯ. mask IoU на парах, с разбивкой по ориентации эталонного
     текста: криволинейный, горизонтальный, наклонный. Разбивка тут не
     украшение — на прямом тексте полигон почти не отличается от рамки,
     и общий средний IoU без неё ничего не объясняет.

  3. ТЕКСТ. CER и WER на парах, где обе стороны сочли объект читаемым.
     Рядом считается CER при приведении ОБЕИХ сторон к нижнему регистру:
     разница между двумя числами и есть та часть ошибки, которая
     объясняется конвенцией записи, а не чтением.

  4. ЧИТАЕМОСТЬ. Согласие по признаку «читаемо / нечитаемо» отдельной
     метрикой, с каппой Коэна. Ни IoU, ни CER этой оси не видят: объект,
     который я счёл нечитаемым, а эталон прочитал, просто выпадает
     из расчёта CER и молча улучшает его.

    python3 annotation/ocr_agreement.py --gt data/totaltext/gt \
        --mine annotation/my_labels --selection data/subset/selection_text.json \
        --out reports/ocr_metrics.json
"""

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

from icdar import by_image, load_cvat_icdar, load_totaltext  # noqa: E402
from polygons import Poly, match_polys, rasterize  # noqa: E402
from text import corpus_cer, corpus_wer, cer as pair_cer  # noqa: E402

ORNT_NAMES = {"h": "горизонтальный", "m": "наклонный",
              "c": "криволинейный", "#": "нечитаемый", "v": "вертикальный"}
MAX_SIDE = 1600


def frame_masks(groups: list[list], ):
    """Растеризует все объекты кадра в одной локальной рамке.

    Рамка общая и урезанная по масштабу: полное разрешение снимка здесь
    не нужно, а на кадрах в три тысячи пикселей маски съели бы память.
    """
    rings = [o.ring for g in groups for o in g]
    if not rings:
        return [[] for _ in groups]
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    x0, y0 = min(xs), min(ys)
    w, h = max(xs) - x0, max(ys) - y0
    scale = min(1.0, MAX_SIDE / max(w, h, 1))
    width = max(2, int(w * scale) + 2)
    height = max(2, int(h * scale) + 2)
    out = []
    for g in groups:
        masks = []
        for o in g:
            flat = [c for p in o.ring
                    for c in ((p[0] - x0) * scale, (p[1] - y0) * scale)]
            masks.append(rasterize(Poly(cls=o.text, parts=[flat]), width, height))
        out.append(masks)
    return out


def kappa_2x2(matrix: list[list[int]]) -> float:
    total = sum(sum(r) for r in matrix)
    if not total:
        return 0.0
    observed = (matrix[0][0] + matrix[1][1]) / total
    rows = [sum(r) / total for r in matrix]
    cols = [(matrix[0][j] + matrix[1][j]) / total for j in range(2)]
    expected = sum(rows[i] * cols[i] for i in range(2))
    return (observed - expected) / (1 - expected) if expected < 1 else 1.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--mine", type=Path, required=True)
    ap.add_argument("--selection", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("reports/ocr_metrics.json"))
    ap.add_argument("--iou-threshold", type=float, default=0.5)
    args = ap.parse_args()

    images = set(json.loads(args.selection.read_text(encoding="utf-8"))["files"])
    gt = load_totaltext(args.gt, images=images)
    mine = load_cvat_icdar(args.mine, images=images)
    g_by, m_by = by_image(gt), by_image(mine)

    pairs = []
    lost_gt, lost_mine = [], []
    for image in sorted(images):
        gs, ms = g_by.get(image, []), m_by.get(image, [])
        if not gs or not ms:
            lost_gt.extend(gs)
            lost_mine.extend(ms)
            continue
        masks_gt, masks_mine = frame_masks([gs, ms])
        matched, extra, missing = match_polys(
            [Poly(o.text, [o.flat()]) for o in ms],
            [Poly(o.text, [o.flat()]) for o in gs],
            masks_mine, masks_gt, args.iou_threshold)
        for i, j, score in matched:
            pairs.append((gs[j], ms[i], score))
        lost_mine.extend(ms[i] for i in extra)
        lost_gt.extend(gs[j] for j in missing)

    print(f"кадров {len(images)}; эталонных объектов {len(gt)}, своих {len(mine)}")
    print(f"сопоставление по mask IoU, порог {args.iou_threshold}: "
          f"пар {len(pairs)}, эталонных без пары {len(lost_gt)}, "
          f"своих без пары {len(lost_mine)}")
    if not pairs:
        raise SystemExit("ни одной пары: проверь экспорт через tools/check_export.py")

    # --- геометрия
    ious = [s for _, _, s in pairs]
    by_ornt = defaultdict(list)
    for g, _, s in pairs:
        by_ornt[g.ornt].append(s)
    print()
    print(f"mask IoU на парах: средний {statistics.mean(ious):.3f}, "
          f"медиана {statistics.median(ious):.3f}, минимум {min(ious):.3f}")
    print("| ориентация эталонного текста | пар | средний IoU |")
    print("|---|---|---|")
    for key in ("h", "m", "c", "#"):
        v = by_ornt.get(key, [])
        if v:
            print(f"| {ORNT_NAMES[key]} | {len(v)} | {statistics.mean(v):.3f} |")

    # --- текст
    both = [(g.text, m.text) for g, m, _ in pairs if g.legible and m.legible]
    c = corpus_cer(both)
    w = corpus_wer(both)
    lowered = corpus_cer([(r.lower(), h.lower()) for r, h in both])
    print()
    print(f"пар, где обе стороны прочитали текст: {len(both)} "
          f"({c['ref_chars']} символов эталона)")
    print(f"CER {c['cer']:.3f} (микро) | {c['cer_macro']:.3f} (макро) | "
          f"WER {w['wer']:.3f} | совпало дословно {c['exact']} из {len(both)}")
    print(f"CER при приведении обеих сторон к нижнему регистру: {lowered['cer']:.3f}")
    share = (c["cer"] - lowered["cer"]) / c["cer"] if c["cer"] > 0 else 0.0
    print(f"  значит на конвенцию регистра приходится {share:.0%} всей ошибки чтения")

    # --- читаемость
    matrix = [[0, 0], [0, 0]]
    for g, m, _ in pairs:
        matrix[0 if g.legible else 1][0 if m.legible else 1] += 1
    total = sum(sum(r) for r in matrix)
    agree = (matrix[0][0] + matrix[1][1]) / total
    k = kappa_2x2(matrix)
    print()
    print(f"согласие по «читаемо / нечитаемо»: {agree:.3f}, каппа Коэна {k:.3f}")
    print("| эталон \\ моё | читаемо | нечитаемо |")
    print("|---|---|---|")
    print(f"| читаемо | {matrix[0][0]} | {matrix[0][1]} |")
    print(f"| нечитаемо | {matrix[1][0]} | {matrix[1][1]} |")

    worst_geom = sorted(pairs, key=lambda t: t[2])[:5]
    worst_text = sorted(
        [(g, m, pair_cer(g.text, m.text)) for g, m, _ in pairs
         if g.legible and m.legible], key=lambda t: -t[2])[:5]
    print()
    print("худшие по геометрии:")
    for g, m, s in worst_geom:
        print(f"  {g.image} эталон#{g.ident}: IoU {s:.3f}, вершин {g.vertices}/{m.vertices}, "
              f"«{g.text}» ↔ «{m.text}»")
    print("худшие по тексту:")
    for g, m, value in worst_text:
        print(f"  {g.image} эталон#{g.ident}: CER {value:.3f}, «{g.text}» ↔ «{m.text}»")

    doc = {
        "frames": len(images),
        "gt_objects": len(gt), "my_objects": len(mine),
        "matched": len(pairs),
        "unmatched_gt": len(lost_gt), "unmatched_mine": len(lost_mine),
        "iou_threshold": args.iou_threshold,
        "iou_mean": statistics.mean(ious), "iou_median": statistics.median(ious),
        "iou_by_orientation": {ORNT_NAMES.get(k2, k2): {
            "pairs": len(v), "iou": statistics.mean(v)} for k2, v in by_ornt.items()},
        "text_pairs": len(both), "ref_chars": c["ref_chars"],
        "cer": c["cer"], "cer_macro": c["cer_macro"], "wer": w["wer"],
        "cer_case_insensitive": lowered["cer"], "case_share": share,
        "exact_matches": c["exact"],
        "legibility_agreement": agree, "legibility_kappa": k,
        "legibility_matrix": matrix,
        "worst_geometry": [{"image": g.image, "gt_id": g.ident, "iou": s,
                            "gt_text": g.text, "my_text": m.text,
                            "gt_vertices": g.vertices, "my_vertices": m.vertices}
                           for g, m, s in worst_geom],
        "worst_text": [{"image": g.image, "gt_id": g.ident, "cer": v,
                        "gt_text": g.text, "my_text": m.text}
                       for g, m, v in worst_text],
        "pairs": [{"image": g.image, "gt_id": g.ident, "my_id": m.ident,
                   "iou": s, "ornt": g.ornt, "gt_text": g.text, "my_text": m.text,
                   "cer": (pair_cer(g.text, m.text)
                           if g.legible and m.legible else None)}
                  for g, m, s in pairs],
        "unmatched_gt_list": [{"image": o.image, "id": o.ident, "text": o.text,
                               "ornt": o.ornt} for o in lost_gt],
        "unmatched_mine_list": [{"image": o.image, "id": o.ident, "text": o.text}
                                for o in lost_mine],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"метрики: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
