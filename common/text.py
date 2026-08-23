#!/usr/bin/env python3
"""Метрики транскрипции: CER и WER (P4e).

ЧТО ЭТО МЕРИТ. Расстояние Левенштейна между двумя строками — минимальное
число правок (вставить символ, удалить, заменить), которыми одна строка
превращается в другую. CER нормирует это число на длину ЭТАЛОНА:

    CER = правки(эталон, моё) / длина(эталон)

Знаменатель именно эталон, и это не мелочь. Нормировка на свою строку
даёт метрику, которую можно улучшить, написав больше символов, — а с
эталоном такой лазейки нет. Отсюда же следует свойство, которое пугает
при первой встрече: CER НЕ ОГРАНИЧЕН ЕДИНИЦЕЙ. Если в эталоне «ABC»,
а я написал «ABCDEFGH», правок пять, длина эталона три, CER = 1.667.
Это не ошибка расчёта, а честный ответ: я дописал больше, чем там было.

WER — то же самое, но единица правки не символ, а слово. На пословном
датасете вроде Total-Text у объекта ровно одно слово, поэтому WER
вырождается в долю объектов, транскрибированных не идентично. Полезен
он всё равно: CER 0.1 может означать «в каждом слове по одной ошибке»
или «одно слово из десяти прочитано целиком неверно», и WER их различает.

МИКРО- И МАКРОУСРЕДНЕНИЕ. CER по набору считается как сумма правок,
делённая на суммарную длину эталонов (микро), а не как среднее
покадровых CER (макро). Иначе одно короткое слово с одной ошибкой
весит столько же, сколько длинная вывеска, прочитанная целиком верно.
Обе величины возвращаются, и в отчёте называется, какая приводится.

Зависимостей нет.
"""

import argparse
import unicodedata


def levenshtein(a, b) -> int:
    """Минимальное число правок. Работает и на строке символов,
    и на списке слов — важно лишь, что элементы сравнимы."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1,          # удалить
                           cur[j - 1] + 1,       # вставить
                           prev[j - 1] + (ca != cb)))  # заменить
        prev = cur
    return prev[-1]


def cer(ref: str, hyp: str) -> float:
    """CER одной пары. Пустой эталон обрабатывается отдельно: делить не на что,
    и любая непустая гипотеза — это чистая выдумка."""
    if not ref:
        return 0.0 if not hyp else float("inf")
    return levenshtein(ref, hyp) / len(ref)


def wer(ref: str, hyp: str) -> float:
    r, h = ref.split(), hyp.split()
    if not r:
        return 0.0 if not h else float("inf")
    return levenshtein(r, h) / len(r)


def corpus_cer(pairs: list[tuple[str, str]]) -> dict:
    """Микро- и макроусреднение по набору пар (эталон, моё)."""
    edits = sum(levenshtein(r, h) for r, h in pairs)
    chars = sum(len(r) for r, _ in pairs)
    per_pair = [cer(r, h) for r, h in pairs if r]
    return {
        "cer": edits / chars if chars else 0.0,
        "cer_macro": sum(per_pair) / len(per_pair) if per_pair else 0.0,
        "edits": edits,
        "ref_chars": chars,
        "pairs": len(pairs),
        "exact": sum(1 for r, h in pairs if r == h),
    }


def corpus_wer(pairs: list[tuple[str, str]]) -> dict:
    edits = sum(levenshtein(r.split(), h.split()) for r, h in pairs)
    words = sum(len(r.split()) for r, _ in pairs)
    return {"wer": edits / words if words else 0.0,
            "edits": edits, "ref_words": words}


# --- нормализации: каждая соответствует одному решению инструкции ---------

def as_is(s: str) -> str:
    return s


def lower(s: str) -> str:
    return s.lower()


def upper(s: str) -> str:
    return s.upper()


def no_punct(s: str) -> str:
    """Выбросить всё, что не буква и не цифра."""
    return "".join(c for c in s if c.isalnum())


def no_diacritics(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if not unicodedata.combining(c))


def lower_no_punct(s: str) -> str:
    return no_punct(s.lower())


NORMALIZERS = {
    "as_is": ("транскрибирую как в эталоне", as_is),
    "lower": ("привожу всё к нижнему регистру", lower),
    "upper": ("привожу всё к ВЕРХНЕМУ регистру", upper),
    "no_punct": ("выбрасываю знаки препинания", no_punct),
    "lower_no_punct": ("нижний регистр + без знаков", lower_no_punct),
}


# --- контрольные случаи ----------------------------------------------------

CASES = [
    ("совпадает с эталоном", "PARKING", "PARKING", 0.0),
    ("одна буква не та", "PARKING", "PARKINH", 1 / 7),
    ("прочитано верно, но нижним регистром", "PARKING", "parking", 1.0),
    ("дописал лишнее", "ABC", "ABCDEFGH", 5 / 3),
    ("не транскрибировал вовсе", "PARKING", "", 1.0),
]


def _selftest() -> int:
    print("| случай | эталон | моё | CER | WER |")
    print("|---|---|---|---|---|")
    ok = True
    for name, ref, hyp, expect in CASES:
        got = cer(ref, hyp)
        print(f"| {name} | `{ref}` | `{hyp or '—'}` | {got:.4f} | {wer(ref, hyp):.4f} |")
        if abs(got - expect) > 1e-9:
            print(f"  ПРОВАЛ: ожидалось {expect:.4f}")
            ok = False

    print()
    print("Третий случай стоит перечитать: каждая буква прочитана правильно,")
    print("а CER равен ровно 1.000 — как если бы слово не было прочитано вовсе.")
    print("Регистр для метрики не «мелкая деталь оформления», а семь правок из семи.")
    print()
    print("Четвёртый: CER больше единицы — это не сбой, а нормировка на эталон.")
    print()

    # микро против макро на трёх объектах
    pairs = [("EXIT", "EXIT"), ("A", "B"), ("RESTAURANT", "RESTAURANT")]
    m = corpus_cer(pairs)
    print("| набор из трёх объектов | значение |")
    print("|---|---|")
    print(f"| правок всего | {m['edits']} |")
    print(f"| символов в эталоне | {m['ref_chars']} |")
    print(f"| CER микро (правки / все символы) | {m['cer']:.4f} |")
    print(f"| CER макро (среднее по объектам) | {m['cer_macro']:.4f} |")
    if abs(m["cer"] - 1 / 15) > 1e-9 or abs(m["cer_macro"] - 1 / 3) > 1e-9:
        print("  ПРОВАЛ: микро должно быть 1/15, макро 1/3")
        ok = False
    print()
    print("Одна ошибка в однобуквенном объекте: микро даёт 0.0667, макро — 0.3333.")
    print("Разница в пять раз на пустом месте, поэтому в отчёте пишут, какая взята.")
    print()
    print("все контрольные случаи сошлись" if ok else "есть расхождения")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
