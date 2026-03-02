import re
from pathlib import Path

def clean(s):
    lines = [ln.rstrip() for ln in s.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
    return '\n'.join(lines).strip()

QUESTION_SPLIT_RE = re.compile(r"(?=^\s*問\s*\d+\s*$)", re.MULTILINE)

fp = Path('data_raw/exam_01.txt')
if not fp.exists():
    print(f'[ERROR] {fp} が見つかりません')
    exit(1)

txt = fp.read_text(encoding='utf-8', errors='ignore')
parts = [p for p in QUESTION_SPLIT_RE.split(txt) if clean(p)]

print(f'総ブロック数: {len(parts)}')
print('=' * 60)

# 最初の3ブロックを表示
for i, p in enumerate(parts[:3], 1):
    lines = p.strip().split('\n')
    print(f'ブロック{i}:')
    for j, line in enumerate(lines[:12], 1):
        print(f'  {j}: {line[:80]}')
    print()

# 問番号の確認
questions = [int(q) for q in re.findall(r'問(\d+)', txt)]
print(f'検出された問題数: {len(questions)}')
if questions:
    print(f'問番号の範囲: {min(questions)} ～ {max(questions)}')
    missing = [i for i in range(1, max(questions)+1) if i not in questions]
    if missing:
        print(f'欠けている問番号: {missing}')
    else:
        print('欠番はありません')

# 見出しパターンの確認
print('\n見出しパターン:')
print(f'  「設問」の出現回数: {txt.count(chr(0x8a2d) + chr(0x554f)) if chr(0x8a2d) in txt else txt.count("設問")}')
print(f'  「問題」の出現回数: {txt.count("問題")}')
print(f'  「選択肢」の出現回数: {txt.count("選択肢")}')
print(f'  「解答」の出現回数: {txt.count("解答")}')
