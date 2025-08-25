import argparse
from functools import lru_cache
import hashlib
import os
import pickle
import sys
from collections import defaultdict

# --------------------------------------------------------------------
# 1. Русский алфавит и вспомогательные функции
# --------------------------------------------------------------------
RUS_ALPHABET = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
CHAR_TO_IDX = {ch: i for i, ch in enumerate(RUS_ALPHABET)}
ALPHABET_SIZE = len(RUS_ALPHABET)


def word_to_counts(word: str) -> list[int]:
    """Возвращает массив из ALPHABET_SIZE чисел – частоты каждой буквы."""
    arr = [0] * ALPHABET_SIZE
    for ch in word:
        idx = CHAR_TO_IDX.get(ch.lower())
        if idx is not None:
            arr[idx] += 1
    return arr


def counts_leq(a: list[int], b: list[int]) -> bool:
    """Проверка a[i] <= b[i] для всех i. Останавливается при первом несоответствии."""
    for x, y in zip(a, b):
        if x > y:
            return False
    return True

# --------------------------------------------------------------------
# 2. Кэширование индекса словаря
# --------------------------------------------------------------------
def _cache_file_path(dict_path: str) -> str:
    """Путь к файлу‑кешу для данного словаря."""
    size_bits = os.path.getsize(dict_path) * 8
    key = f"{dict_path}_{size_bits}"
    h = hashlib.sha256(key.encode()).hexdigest()
    cache_dir = os.path.join(os.path.curdir, ".wheel_solver_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{h}.pkl")


@lru_cache
def load_dictionary_cached(path: str) -> dict[int, list[tuple[str, list[int], int]]]:
    """
    Загружает индекс словаря из кэша (если он существует и актуален),
    иначе строит его заново и сохраняет в кэш.
    """
    cache_file = _cache_file_path(path)

    # Попытка загрузить из кеша
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "rb") as cf:
                return pickle.load(cf)
        except Exception:   # если что‑то пошло не так – будем пересчитывать
            pass

    # ---- Пересчёт индекса -------------------------------------------------
    index = defaultdict(list)
    try:
        with open(path, encoding="utf-8") as f:
            for rank, line in enumerate(f):
                word = line.strip()
                if not word:
                    continue
                filtered = [ch.lower() for ch in word if ch.isalpha()]
                if not filtered:
                    continue
                length = len(filtered)
                counts = [0] * ALPHABET_SIZE
                for ch in filtered:
                    idx = CHAR_TO_IDX.get(ch)
                    if idx is None:          # буква не в нашем алфавите – пропускаем слово
                        break
                    counts[idx] += 1
                else:
                    index[length].append((word.lower(), counts, rank))
    except OSError as e:
        print(f"Ошибка чтения словаря '{path}': {e}", file=sys.stderr)
        sys.exit(1)

    # Сохраняем в кэш
    try:
        with open(cache_file, "wb") as cf:
            pickle.dump(dict(index), cf)  # сохраняем как обычный dict
    except Exception:   # не критично – просто продолжаем без кеша
        pass

    return dict(index)

# --------------------------------------------------------------------
# 3. Поиск подходящих слов
# --------------------------------------------------------------------
def find_words(
    index: dict[int, list[tuple[str, list[int], int]]],
    letters: str,
    length: int,
) -> list[tuple[str, int]]:
    """Возвращает список всех слов нужной длины, которые можно собрать из букв."""
    input_counts = [0] * ALPHABET_SIZE
    for ch in letters.lower():
        idx = CHAR_TO_IDX.get(ch)
        if idx is not None:
            input_counts[idx] += 1

    candidates = index.get(length, [])
    result = []

    for word, w_counts, rank in candidates:
        if counts_leq(w_counts, input_counts):
            result.append((word, rank))

    # Слова уже в порядке популярности (как они встречаются в словаре)
    return result

def find_words_by_indx(indx, letters):
    d = {}
    for L in range(len(letters)+1):
        matches = find_words(indx, letters, L)
        if matches:
            d[L] = [w[0] for w in sorted(matches, key=lambda x: x[1])]
    return d    

def get_words_data(letters):
    index = load_dictionary_cached("nouns.txt")
    d = find_words_by_indx(index, letters)
    if d:
        return d
    index = load_dictionary_cached("russian_words50.txt")
    d = find_words_by_indx(index, letters)
    return d

# --------------------------------------------------------------------
# 4. CLI
# --------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Solver для игры «колесо букв» с кэшированием словаря"
    )
    parser.add_argument("-l", "--letters", required=True,
                        help="Набор доступных букв (строка)")
    # Принимаем несколько длин; если не указано – используем все длины
    parser.add_argument(
        "-n",
        "--lengths",
        nargs="*",
        type=int,
        help=(
            "Список нужных длин слов. Если не задано, "
            "будут использованы все возможные (от 1 до количества букв)"
        ),
    )
    parser.add_argument(
        "-d",
        "--dict",
        default="/usr/share/dict/words",
        help="Путь к файлу со списком слов (по умолчанию /usr/share/dict/words)",
    )
    args = parser.parse_args()

    # Определяем длины, которые нужно проверить
    if args.lengths:
        lengths = sorted(set(args.lengths))
    else:
        max_len_from_letters = len(args.letters)
        lengths = list(range(1, max_len_from_letters + 1))

    index = load_dictionary_cached(args.dict)

    for L in lengths:
        matches = find_words(index, args.letters, L)
        if matches:
            print(f"\nДлина {L} ({len(matches)} слов):")
            a = sorted(matches, key=lambda x: x[1])
            for w, r in a:
                print(w)
        else:
            print(f"\nДлина {L}: Совпадений не найдено.")

if __name__ == "__main__":
    main()