@"
import re
from pathlib import Path
from typing import Optional

def clean(s):
    lines = [ln.rstrip() for ln in s.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
    return '\n'.join(lines).strip()

def is_separator_only(block):
    cleaned = block.strip()
    return bool(cleaned) and re.fullmatch(r'[_\-=\s]+', cleaned) is not None

QUESTION_SPLIT_RE = re.compile(r\"(?=^\s*問\s*\d+\s*$)\", re.MULTILINE)
QNO_RE = re.compile(r\"^\s*問\s*(\d+)\s*$\", re.MULTILINE)
STEM_RE = re.compile(r\"設問\s*\n(.+?)\n\s*選択肢\s*\n\", re.DOTALL)
ANSWER_RE = re.compile(r\"解答\s*\n(\d+)\s*$\", re.MULTILINE)

fp = Path('data_raw/exam_07.txt')
txt = fp.read_text(encoding='utf-8', errors='ignore')
parts = [p for p in QUESTION_SPLIT_RE.split(txt) if clean(p)]

failed_qnos = []

for p in parts:
    if is_separator_only(p.strip()):
        continue
    
    block = clean(p)
    m_qno = QNO_RE.search(block)
    
    if not m_qno:
        failed_qnos.append('(問番号なし)')
        continue
    
    qno = int(m_qno.group(1))
    
    # 各パートのチェック
    has_stem = STEM_RE.search(block) is not None
    has_answer = ANSWER_RE.search(block) is not None
    
    if not has_stem or not has_answer:
        reason = []
        if not has_stem:
            reason.append('設問なし')
        if not has_answer:
            reason.append('解答なし')
        failed_qnos.append(f'問{qno} ({\" \".join(reason)})')

print(f'失敗した問題: {len(failed_qnos)}個')
print('=' * 60)
for f in failed_qnos:
    print(f)
"@ | Out-File "debug_failed.py" -Encoding utf8

python debug_failed.py
