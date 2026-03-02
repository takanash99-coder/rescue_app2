import re
from pathlib import Path

fp = Path('data_raw/exam_09.txt')
txt = fp.read_text(encoding='utf-8', errors='ignore')

# 「問題」が使われている箇所を検出
count = len(re.findall(r'^問題$', txt, re.MULTILINE))
print(f'「問題」の出現回数: {count}')

# 問番号を全て抽出
questions = re.findall(r'問(\d+)', txt)
questions = [int(q) for q in questions]

print(f'検出された問題数: {len(questions)}')
print(f'問番号の範囲: {min(questions)} ～ {max(questions)}')
print()

# 欠番を検出
missing = []
for i in range(1, 101):
    if i not in questions:
        missing.append(i)

if missing:
    print(f'欠けている問番号: {missing}')
else:
    print('欠番はありません')
