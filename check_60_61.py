import re
from pathlib import Path

fp = Path('data_raw/exam_08.txt')
txt = fp.read_text(encoding='utf-8', errors='ignore')

# 問60～問62を抽出
pattern = re.compile(r'(問60.*?(?=問61|$))', re.DOTALL)
match60 = pattern.search(txt)

pattern61 = re.compile(r'(問61.*?(?=問62|$))', re.DOTALL)
match61 = pattern61.search(txt)

if match60:
    print('=== 問60 ===')
    lines = match60.group(1).strip().split('\n')
    for i, line in enumerate(lines[:20], 1):
        print(f'{i:2d}: {line[:80]}')

print('\n' + '='*60 + '\n')

if match61:
    print('=== 問61 ===')
    lines = match61.group(1).strip().split('\n')
    for i, line in enumerate(lines[:20], 1):
        print(f'{i:2d}: {line[:80]}')
