# tools/check_local_imports.py
#
# Ищет локальные "from X import Y" внутри функций, где Y также используется
# до импорта (что приводит к UnboundLocalError).

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"__pycache__", ".venv", "venv", "backups", "data", ".git", "tools"}


def check_file(path: Path) -> list[str]:
    problems = []
    s = path.read_text(encoding="utf-8", errors="ignore")
    lines = s.split("\n")

    # Найти все "def " функции
    funcs = []
    for i, line in enumerate(lines):
        m = re.match(r'^(\s*)def (\w+)\(', line)
        if m:
            funcs.append((i, m.group(2), len(m.group(1))))

    for start, name, indent in funcs:
        # Границы функции — до следующего def с меньшим/равным отступом
        end = len(lines)
        for j in range(start + 1, len(lines)):
            m = re.match(r'^(\s*)def ', lines[j])
            if m and len(m.group(1)) <= indent:
                end = j
                break

        # Найти локальные импорты внутри функции
        body = "\n".join(lines[start:end])
        local_imports = []
        for j, line in enumerate(lines[start:end], start):
            m = re.match(r'^\s+from\s+(\S+)\s+import\s+(.+?)\s*$', line)
            if not m: continue
            module = m.group(1)
            imported = [x.strip().split(" as ")[-1].strip() for x in m.group(2).split(",")]
            for imp in imported:
                local_imports.append((j, module, imp, line))

        if not local_imports:
            continue

        for imp_line, module, imp, _ in local_imports:
            # Ищем использование imp до строки импорта
            for k in range(start + 1, imp_line):
                if re.search(rf'\b{re.escape(imp)}\s*\(', lines[k]) or re.search(rf'\b{re.escape(imp)}\.', lines[k]):
                    problems.append(
                        f"{path.relative_to(ROOT)}:{k+1}: '{imp}' used before local import (line {imp_line+1}) in function '{name}'"
                    )
                    break

    return problems


def main():
    all_problems = []
    for py in ROOT.rglob("*.py"):
        if any(p in py.parts for p in SKIP_DIRS):
            continue
        problems = check_file(py)
        all_problems.extend(problems)

    if not all_problems:
        print("=== NO PROBLEMS ===")
        return 0

    print(f"=== {len(all_problems)} POTENTIAL UnboundLocalError ===")
    for p in all_problems:
        print(f"  {p}")
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
