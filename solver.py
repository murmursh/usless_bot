from itertools import permutations


def find_word_slots(matrix):
    slots = []
    rows, cols = len(matrix), len(matrix[0])

    # Horizontal
    for r in range(rows):
        c = 0
        while c < cols:
            if matrix[r][c] == 1:
                start = c
                while c < cols and matrix[r][c] == 1:
                    c += 1
                length = c - start
                if length > 1:
                    slots.append([(r, cc) for cc in range(start, c)])
            else:
                c += 1

    # Vertical
    for c in range(cols):
        r = 0
        while r < rows:
            if matrix[r][c] == 1:
                start = r
                while r < rows and matrix[r][c] == 1:
                    r += 1
                length = r - start
                if length > 1:
                    slots.append([(rr, c) for rr in range(start, r)])
            else:
                r += 1

    return slots


def build_constraints(slots):
    """Find intersections between slots."""
    constraints = {}
    for i, slot1 in enumerate(slots):
        for j, slot2 in enumerate(slots):
            if i >= j:
                continue
            for idx1, pos1 in enumerate(slot1):
                if pos1 in slot2:
                    idx2 = slot2.index(pos1)
                    constraints.setdefault(i, []).append((j, idx1, idx2))
                    constraints.setdefault(j, []).append((i, idx2, idx1))
    return constraints


def backtrack(slots, words_dict, constraints, assignment=None, used=None, slot_idx=0):
    if assignment is None:
        assignment = {}
    if used is None:
        used = set()

    if slot_idx == len(slots):
        return assignment  # all slots filled

    slot = slots[slot_idx]
    length = len(slot)
    candidates = words_dict.get(length, [])

    for word in candidates:
        if word in used:
            continue

        # Check constraints with already assigned slots
        ok = True
        for (other, i1, i2) in constraints.get(slot_idx, []):
            if other in assignment:
                if assignment[other][i2] != word[i1]:
                    ok = False
                    break
        if not ok:
            continue

        # Assign word
        assignment[slot_idx] = word
        used.add(word)

        result = backtrack(slots, words_dict, constraints, assignment, used, slot_idx + 1)
        if result:
            return result

        # Undo
        del assignment[slot_idx]
        used.remove(word)

    return None


def solve_crossword(matrix, words_dict):
    slots = find_word_slots(matrix)
    constraints = build_constraints(slots)
    return backtrack(slots, words_dict, constraints)


def backtrack_all(slots, words_dict, constraints, assignment=None, used=None, slot_idx=0, solutions=None):
    if assignment is None:
        assignment = {}
    if used is None:
        used = set()
    if solutions is None:
        solutions = []

    if slot_idx == len(slots):
        # Found full solution
        solutions.append(assignment.copy())
        return solutions

    slot = slots[slot_idx]
    length = len(slot)
    candidates = words_dict.get(length, [])

    for word in candidates:
        if word in used:
            continue

        # Check constraints
        ok = True
        for (other, i1, i2) in constraints.get(slot_idx, []):
            if other in assignment:
                if assignment[other][i2] != word[i1]:
                    ok = False
                    break
        if not ok:
            continue

        # Assign
        assignment[slot_idx] = word
        used.add(word)

        backtrack_all(slots, words_dict, constraints, assignment, used, slot_idx + 1, solutions)

        # Undo
        del assignment[slot_idx]
        used.remove(word)

    return solutions


def solve_crossword_all(matrix, words_dict):
    slots = find_word_slots(matrix)
    constraints = build_constraints(slots)
    return backtrack_all(slots, words_dict, constraints)


if __name__ == "__main__":
    matrix = [
        [0, 0, 1, 0, 1, 0],
        [0, 0, 1, 0, 1, 0],
        [0, 1, 1, 1, 1, 1],
        [0, 1, 0, 0, 0, 0],
        [1, 1, 1, 0, 0, 0],
        [0, 1, 0, 0, 0, 0],
    ]

    words_dict = {
        2: list(permutations('СМЕХА', 2)),
        3: list(permutations('СМЕХА', 3)),
        4: list(permutations('СМЕХА', 4)),
        5: list(permutations('СМЕХА', 5)),
    }

    solutions = solve_crossword_all(matrix, words_dict)
    if solutions:
        for solution in solutions:
            for idx, word in solution.items():
                print(f"Slot {idx}: {word}")
    else:
        print("No solution found.")

