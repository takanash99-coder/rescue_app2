# word_to_exam_json.py
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


# ==============
# 設定（基本いじらない）
# ==============
MODE = "exam"

# app.py が要求するキーに合わせる
DEFAULT_WHY_WRONG = (
    "誤答は用語の定義・分類・条件の取り違え、または優先順位の誤りが原因になりやすい。"
    "根拠となる語句（定義・数値・原則）に立ち返って確認する。"
)

# ==============
# ユーティリティ
# ==============
def script_root() -> Path:
    """このスクリプトが置いてあるフォルダを基準にする（pwdズレ対策）"""
    return Path(__file__).resolve().parent


def read_text_flexible(fp: Path) -> str:
    """UTF-8優先、ダメならCP932(Shift-JIS系)で読む"""
    try:
        return fp.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return fp.read_text(encoding="cp932", errors="strict")


def normalize_newlines(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\r", "\n")


def clean(s: str) -> str:
    # 末尾の空白を整える（内容は壊さない）
    lines = [ln.rstrip() for ln in normalize_newlines(s).split("\n")]
    return "\n".join(lines).strip()


def ensure_dirs(*dirs: Path) -> None:
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def safe_stem(fp: Path) -> str:
    """ファイル名からカテゴリ用のラベルを作る"""
    return fp.stem.strip()


def pick_subject_no_from_name(name: str) -> str:
    """
    例:
      exam_01.txt -> 01
      01.人体の構造と機能.txt -> 01
      1_人体.txt -> 01
    見つからなければ '00'
    """
    m = re.search(r"(?:^|[^0-9])(\d{1,2})(?:[^0-9]|$)", name)
    if not m:
        return "00"
    n = int(m.group(1))
    return f"{n:02d}"


def output_json_name(subject_no: str) -> str:
    return f"exam_{subject_no}.json"


# ==============
# パーサ本体
# ==============
@dataclass
class ParsedQuestion:
    qno: int
    question: str
    choices: list[str]
    correct_indices: list[int]  # 複数解答対応：リストに変更
    explanation: str
    difficulty: Optional[str] = None


QUESTION_SPLIT_RE = re.compile(r"(?=^\s*問\s*\d+\s*$)", re.MULTILINE)

# 「問 1」みたいなゆれも拾う
QNO_RE = re.compile(r"^\s*問\s*(\d+)\s*$", re.MULTILINE)

# 設問～選択肢
STEM_RE = re.compile(r"設問\s*\n(.+?)\n\s*選択肢\s*\n", re.DOTALL)

# 解答（単一または複数対応：「1」「1、2」「1,2」「2,3」など）
ANSWER_RE = re.compile(r"解答\s*\n([\d、,\s]+)\s*$", re.MULTILINE)

# 難易度（あってもなくてもOK）
DIFF_RE = re.compile(r"難易度\s*\n([★☆]+)\s*$", re.MULTILINE)

# 解説（最後まで）
EXPL_RE = re.compile(r"解説\s*\n(.+)$", re.DOTALL)

# 選択肢： "1." "1。" "1\t" "1 " など対応
CHOICE_LINE_RE = re.compile(r"^\s*(\d)\s*[.\u3002]\s*(.+?)\s*$", re.MULTILINE)
CHOICE_TAB_RE = re.compile(r"^\s*(\d)\s+(.+?)\s*$", re.MULTILINE)


def is_separator_only(block: str) -> bool:
    """
    区切り線のみのブロックを判定
    例: ________________________________________
        ========================================
        ----------------------------------------
    """
    cleaned = block.strip()
    # 区切り線文字のみで構成されているかチェック
    return bool(cleaned) and re.fullmatch(r'[_\-=\s]+', cleaned) is not None


def extract_choices(block: str) -> list[str]:
    found: dict[int, str] = {}
    for m in CHOICE_LINE_RE.finditer(block):
        idx = int(m.group(1))
        found[idx] = m.group(2).strip()
    # 上の形式で拾えない場合、タブ/スペース区切りも拾う
    if len(found) < 5:
        for m in CHOICE_TAB_RE.finditer(block):
            idx = int(m.group(1))
            if idx in {1, 2, 3, 4, 5} and idx not in found:
                found[idx] = m.group(2).strip()

    choices = [found.get(i, "").strip() for i in range(1, 6)]
    if any(c == "" for c in choices):
        return []
    return choices


def parse_answer(answer_str: str) -> Optional[list[int]]:
    """
    解答文字列から正解番号のリストを抽出（複数解答対応）
    例：「1」→[0], 「1、2」→[0, 1], 「1,2」→[0, 1], 「2,3」→[1, 2]
    """
    # 数字のみを抽出（全角・半角カンマ、全角・半角スペース対応）
    numbers = re.findall(r'\d+', answer_str.strip())
    if not numbers:
        return None
    
    # 全ての数字をインデックスに変換（1-based → 0-based）
    indices = []
    for num_str in numbers:
        num = int(num_str)
        if num < 1 or num > 5:
            return None
        indices.append(num - 1)
    
    # 重複を削除してソート
    return sorted(list(set(indices)))


def parse_one_block(block: str) -> Optional[ParsedQuestion]:
    block = clean(block)
    if not block:
        return None

    # 区切り線のみのブロックをスキップ（failed にカウントしない）
    if is_separator_only(block):
        return None

    m_qno = QNO_RE.search(block)
    if not m_qno:
        return None
    qno = int(m_qno.group(1))

    m_stem = STEM_RE.search(block)
    if not m_stem:
        return None
    question = clean(m_stem.group(1))

    choices = extract_choices(block)
    if len(choices) != 5:
        return None

    m_ans = ANSWER_RE.search(block)
    if not m_ans:
        return None
    
    correct_indices = parse_answer(m_ans.group(1))
    if correct_indices is None or len(correct_indices) == 0:
        return None

    m_diff = DIFF_RE.search(block)
    difficulty = m_diff.group(1).strip() if m_diff else None

    m_expl = EXPL_RE.search(block)
    explanation = clean(m_expl.group(1)) if m_expl else ""

    return ParsedQuestion(
        qno=qno,
        question=question,
        choices=choices,
        correct_indices=correct_indices,
        explanation=explanation,
        difficulty=difficulty,
    )


def parse_txt_to_questions(txt: str) -> tuple[list[ParsedQuestion], int]:
    txt = clean(txt)
    parts = [p for p in QUESTION_SPLIT_RE.split(txt) if clean(p)]
    parsed: list[ParsedQuestion] = []
    failed = 0

    # split結果の最初が問ブロックでない可能性があるので、問番号があるものだけ拾う
    for p in parts:
        # 区切り線のみのブロックは事前に除外（failedにカウントしない）
        if is_separator_only(p.strip()):
            continue
        
        q = parse_one_block(p)
        if q is None:
            failed += 1
        else:
            parsed.append(q)

    # 問番号で並べ替え
    parsed.sort(key=lambda x: x.qno)
    return parsed, failed


# ==============
# JSON生成
# ==============
def to_app_schema(
    pq: ParsedQuestion,
    subject_no: str,
) -> dict:
    """
    複数解答の場合は最初の正解をcorrect_indexに設定
    app.pyが複数解答に対応していない場合の互換性のため
    """
    return {
        "id": f"exam{subject_no}__q{pq.qno:04d}",
        "mode": MODE,
        "question": pq.question,
        "choices": pq.choices,
        "correct_index": pq.correct_indices[0],  # 最初の正解を使用
        "correct_indices": pq.correct_indices,    # 複数解答用に追加
        "explanation": pq.explanation,
        "why_wrong": DEFAULT_WHY_WRONG,
    }


def write_json(fp: Path, questions: list[dict]) -> None:
    fp.write_text(
        json.dumps({"questions": questions}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ==============
# メイン：data_raw内のtxtを全部変換
# ==============
def main() -> int:
    root = script_root()
    data_raw = root / "data_raw"
    data_out = root / "data"

    ensure_dirs(data_raw, data_out)

    txt_files = sorted(data_raw.glob("*.txt"))
    if not txt_files:
        print(f"入力txtが見つかりません: {data_raw}")
        print("data_raw フォルダに .txt を入れてください。例: data_raw/exam_01.txt")
        return 1

    total_written = 0
    any_failed = False

    print(f"入力フォルダ: {data_raw}")
    print(f"出力フォルダ: {data_out}")
    print("-" * 60)

    for fp in txt_files:
        name = fp.name
        subject_no = pick_subject_no_from_name(name)
        out_fp = data_out / output_json_name(subject_no)

        try:
            raw = read_text_flexible(fp)
        except Exception as e:
            print(f"[NG] {name} 読み込み失敗: {e}")
            any_failed = True
            continue

        parsed, failed = parse_txt_to_questions(raw)
        if not parsed:
            print(f"[NG] {name} 解析できた問題が0件（形式ゆれの可能性）")
            any_failed = True
            continue

        app_qs = [to_app_schema(pq, subject_no) for pq in parsed]
        write_json(out_fp, app_qs)
        total_written += len(app_qs)

        status = "OK" if failed == 0 else "WARN"
        print(f"[{status}] {name} -> {out_fp.name} 生成: {len(app_qs)}問 / スキップ: {failed}ブロック")
        if failed:
            any_failed = True

    print("-" * 60)
    print(f"完了: 合計 {total_written}問 を JSON化しました。")
    if any_failed:
        print("注意: 一部ファイルで 'WARN/NG' があります。形式ゆれのブロックがある可能性。")
    return 0 if total_written > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
