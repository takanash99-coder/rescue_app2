import re
from pathlib import Path

def clean(s):
    lines = [ln.rstrip() for ln in s.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
    return '\n'.join(lines).strip()

QUESTION_SPLIT_RE = re.compile(r"(?=^\s*問\s*\d+\s*$)", re.MULTILINE)

fp = Path('data_raw/exam_08.txt')
txt = fp.read_text(encoding='utf-8', errors='ignore')
parts = [p for p in QUESTION_SPLIT_RE.split(txt) if clean(p)]

print(f'総ブロック数: {len(parts)}')
print('=' * 60)

# 最初の3ブロックの構造確認
for i, p in enumerate(parts[:3], 1):
    lines = p.strip().split('\n')
    print(f'ブロック{i}:')
    for j, line in enumerate(lines[:10], 1):  # 最初の10行
        print(f'  {j}: {line[:80]}')
    print()
