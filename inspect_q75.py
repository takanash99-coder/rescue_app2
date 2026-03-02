import re
from pathlib import Path

fp = Path('data_raw/exam_10.txt')
txt = fp.read_text(encoding='utf-8', errors='ignore')

# 問75のブロックを抽出
pattern = re.compile(r'(問\s*75.*?)(?=問\s*76|$)', re.DOTALL)
m = pattern.search(txt)

if m:
    block = m.group(1)
    lines = block.split('\n')
    
    print('========== 問75 の全文 ==========')
    for i, line in enumerate(lines, 1):
        # 特殊文字を可視化
        display = line.replace(' ', '').replace('\t', '')
        print(f'{i:3d}: [{repr(line[:20])}...] {display[:80]}')
    
    print('\n========== チェック結果 ==========')
    print(f'「設問」の位置: {block.find("設問")}')
    print(f'「選択肢」の位置: {block.find("選択肢")}')
    print(f'「解答」の位置: {block.find("解答")}')
    
    # 解答部分を詳しく
    answer_match = re.search(r'解答\s*\n(.{0,30})', block)
    if answer_match:
        print(f'\n解答の次の行: {repr(answer_match.group(1))}')
    else:
        print('\n 解答パターンが見つかりません')
else:
    print(' 問75が見つかりませんでした')
