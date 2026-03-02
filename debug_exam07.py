# debug_exam_txt.py
import re
from pathlib import Path

SRC = Path("data_raw/exam_07.txt")
OUT = Path("data_raw/_debug_exam07_bad_blocks.txt")

SEP_RE = re.compile(r"^\s*_{10,}\s*$", re.MULTILINE)  # ＿＿＿＿＿＿＿＿＿＿

QNO_RE = re.compile(r"^\s*問\s*(\d+)\s*$", re.MULTILINE)
HAS_STEM_RE = re.compile(r"^\s*設問\s*$", re.MULTILINE)
HAS_CHOICES_RE = re.compile(r"^\s*選択肢\s*$", re.MULTILINE)
# 「解答」行：次行に数字 or 同一行に数字（解答 3 / 解答 2、3）
ANSWER_RE = re.compile(r"^\s*解答(?:\s*[:：]?\s*)?([0-9０-９、, ]+)?\s*$", re.MULTILINE)
# 「難易度」行：次行に★ or 同一行に★（難易度 ★☆☆）
DIFF_RE = re.compile(r"^\s*難易度(?:\s*[:：]?\s*)?([★☆]{2,3})?\s*$", re.MULTILINE)

CHOICE_LINE_RE = re.compile(r"^\s*(\d+)[\.\)]\s+.+$", re.MULTILINE)

def split_blocks(text: str) -> list[str]:
    # 区切り線で分割し、空は捨てる
    parts = [p.strip("\n") for p in SEP_RE.split(text)]
    return [p for p in parts if p.strip()]

def first_n_lines(s: str, n: int = 14) -> str:
    lines = s.splitlines()
    return "\n".join(lines[:n])

def analyze_block(b: str):
    reasons = []

    m_q = QNO_RE.search(b)
    qno = m_q.group(1) if m_q else "?"
    if not m_q:
        reasons.append("NO_QNO")

    if not HAS_STEM_RE.search(b):
        reasons.append("NO_STEM_LABEL(設問)")

    if not HAS_CHOICES_RE.search(b):
        reasons.append("NO_CHOICES_LABEL(選択肢)")

    # 選択肢が本当にあるか（1. 〜 5. 形式）
    choice_lines = CHOICE_LINE_RE.findall(b)
    if len(choice_lines) < 2:  # 1行もない/極端に少ないのは怪しい
        reasons.append(f"CHOICES_TOO_FEW({len(choice_lines)})")

    # 解答の形式チェック
    m_a = ANSWER_RE.search(b)
    if not m_a:
        reasons.append("NO_ANSWER_LABEL(解答)")
        ans = ""
    else:
        ans = (m_a.group(1) or "").strip()
        # 「解答」行があるのに数字が同一行にも次行にも無いケースを検出
        if not ans:
            # 次行に数字があるか
            # （解答 の次の行を見にいく）
            lines = b.splitlines()
            for i, line in enumerate(lines):
                if re.match(r"^\s*解答\s*$", line):
                    if i + 1 < len(lines) and re.match(r"^\s*[0-9０-９][0-9０-９、, ]*\s*$", lines[i+1]):
                        ans = lines[i+1].strip()
                    break
        if not ans:
            reasons.append("BAD_ANSWER_FORMAT")
        else:
            # 全角数字→半角、区切り統一
            norm = ans.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
            norm = norm.replace("，", ",").replace("、", ",").replace(" ", "")
            # 1～5のみ許容（2つ選べ等ならカンマ区切り）
            if not re.fullmatch(r"[1-5](?:,[1-5]){0,4}", norm):
                reasons.append(f"BAD_ANSWER_VALUE({ans})")

    # 難易度チェック
    m_d = DIFF_RE.search(b)
    if not m_d:
        reasons.append("NO_DIFF_LABEL(難易度)")
        diff = ""
    else:
        diff = (m_d.group(1) or "").strip()
        if not diff:
            # 次行に★があるか
            lines = b.splitlines()
            for i, line in enumerate(lines):
                if re.match(r"^\s*難易度\s*$", line):
                    if i + 1 < len(lines) and re.match(r"^\s*[★☆]{2,3}\s*$", lines[i+1]):
                        diff = lines[i+1].strip()
                    break
        if diff not in {"★☆☆", "★★☆", "★★★"}:
            reasons.append(f"BAD_DIFFICULTY({diff or 'EMPTY'})")

    return qno, reasons

def main():
    text = SRC.read_text(encoding="utf-8")
    blocks = split_blocks(text)

    bad = []
    for idx, b in enumerate(blocks, start=1):
        qno, reasons = analyze_block(b)
        if reasons:
            bad.append((idx, qno, reasons, b))

    print(f"総ブロック数: {len(blocks)}")
    print(f"不適合ブロック数: {len(bad)}")
    print("-" * 60)

    for idx, qno, reasons, b in bad:
        print(f"[BAD] block#{idx} / 問{qno} :: {', '.join(reasons)}")
        print(first_n_lines(b, 12))
        print("-" * 60)

    if bad:
        with OUT.open("w", encoding="utf-8") as f:
            for idx, qno, reasons, b in bad:
                f.write(f"===== block#{idx} / 問{qno} :: {', '.join(reasons)} =====\n")
                f.write(b.strip() + "\n\n")
        print(f"保存先: {OUT}")

if __name__ == "__main__":
    main()
