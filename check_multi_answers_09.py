import re
from pathlib import Path

fp = Path('data_raw/exam_09.txt')
txt = fp.read_text(encoding='utf-8', errors='ignore')

# 解答行を全て抽出
answers = re.findall(r'解答\s*\n(.+?)$', txt, re.MULTILINE)

print(f'総解答数: {len(answers)}')
print('=' * 60)

# 複数解答（、を含む）を検出
multi_answers = []
for i, ans in enumerate(answers, 1):
    if '、' in ans or ',' in ans:
        multi_answers.append((i, ans.strip()))

if multi_answers:
    print(f'複数解答が見つかりました: {len(multi_answers)}個')
    print()
    for qno, ans in multi_answers:
        print(f'  問{qno}: 解答 {ans}')
else:
    print('複数解答は見つかりませんでした')
