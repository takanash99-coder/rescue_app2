import re
from pathlib import Path

def clean(s):
    lines = [ln.rstrip() for ln in s.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
    return '\n'.join(lines).strip()

QUESTION_SPLIT_RE = re.compile(r"(?=^\s*問\s*\d+\s*$)", re.MULTILINE)
STEM_HEADER_RE = re.compile(r"^設問\s*$", re.MULTILINE)
CHOICE_HEADER_RE = re.compile(r"^選択肢\s*$", re.MULTILINE)
ANSWER_HEADER_RE = re.compile(r"^解答\s*$", re.MULTILINE)

fp = Path('data_raw/exam_10.txt')
txt = fp.read_text(encoding='utf-8', errors='ignore')
parts = [p for p in QUESTION_SPLIT_RE.split(txt) if clean(p)]

print(f'総ブロック数: {len(parts)}')

# 各ブロックの問番号を抽出
parsed_questions = []
failed_questions = []

for p in parts:
    block = clean(p)
    if not block:
        continue
    
    # 問番号を取得
    m = re.search(r'^\s*問\s*(\d+)\s*$', block, re.MULTILINE)
    if not m:
        continue
    qnum = int(m.group(1))
    
    # チェック項目
    has_stem = bool(STEM_HEADER_RE.search(block))
    has_choices = bool(CHOICE_HEADER_RE.search(block))
    has_answer = bool(ANSWER_HEADER_RE.search(block))
    
    # 選択肢数カウント
    choice_count = len(re.findall(r'^[1-5]\.', block, re.MULTILINE))
    
    if has_stem and has_choices and has_answer and choice_count == 5:
        parsed_questions.append(qnum)
    else:
        failed_questions.append({
            'qnum': qnum,
            'has_stem': has_stem,
            'has_choices': has_choices,
            'has_answer': has_answer,
            'choice_count': choice_count
        })

print(f'\n 正常にパースされた問題: {len(parsed_questions)}問')
print(f' スキップされた問題: {len(failed_questions)}問')

if failed_questions:
    print('\n========== スキップされた問題の詳細 ==========')
    for f in failed_questions:
        print(f"\n問{f['qnum']}:")
        print(f"  設問あり: {'' if f['has_stem'] else ''}")
        print(f"  選択肢ヘッダあり: {'' if f['has_choices'] else ''}")
        print(f"  解答あり: {'' if f['has_answer'] else ''}")
        print(f"  選択肢数: {f['choice_count']}/5")

# 欠番チェック
all_nums = set(range(1, 101))
parsed_set = set(parsed_questions)
missing = sorted(all_nums - parsed_set)

if missing:
    print(f'\n 欠けている問番号: {missing}')
