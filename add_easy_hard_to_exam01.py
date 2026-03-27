from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI


# =========================
# 設定
# =========================
INPUT_TXT = Path("data_raw/exam_10.txt")
OUTPUT_JSON = Path("data/exam_10_plus.json")
DEBUG_TXT = Path("data_raw/_debug_exam10_bad.txt")

FIELD_NAME = "総合模試"
MODEL_NAME = "gpt-4o-mini"
SLEEP_SEC = 0.5


# =========================
# TXT解析
# =========================
def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\ufeff", "")
    text = re.sub(r"\n?_{5,}\n?", "\n", text)
    return text.strip()


def clean_text_for_api(text: str) -> str:
    if not isinstance(text, str):
        return ""

    text = text.replace("\ufeff", "")
    text = text.replace("\t", " ")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    text = re.sub(r"\n?_{5,}\n?", "\n", text)
    return text.strip()


def split_question_blocks(text: str) -> List[str]:
    text = normalize_text(text)
    blocks = re.split(r"(?=^問\s*0*\d+\s*$)", text, flags=re.MULTILINE)
    return [b.strip() for b in blocks if b.strip()]


def extract_section(block: str, start_label: str, end_labels: List[str]) -> str:
    start_pat = re.escape(start_label)

    if end_labels:
        end_pat = "|".join(re.escape(label) for label in end_labels)
        pattern = rf"{start_pat}\s*\n(.*?)(?=\n(?:{end_pat})\s*\n|\Z)"
    else:
        pattern = rf"{start_pat}\s*\n(.*)$"

    m = re.search(pattern, block, flags=re.DOTALL)
    if not m:
        return ""

    value = m.group(1).strip()
    return normalize_text(value)


def extract_first_available_section(
    block: str,
    start_labels: List[str],
    end_labels: List[str],
) -> str:
    for label in start_labels:
        value = extract_section(block, label, end_labels)
        if value:
            return value
    return ""


def parse_choices(choices_text: str) -> List[str]:
    lines = [line.strip() for line in choices_text.splitlines() if line.strip()]
    choices: List[str] = []

    current: Optional[str] = None
    for line in lines:
        m = re.match(r"^(\d+)\.\s*(.+)$", line)
        if m:
            if current:
                choices.append(current.strip())
            current = m.group(2).strip()
        else:
            if current:
                current += " " + line.strip()

    if current:
        choices.append(current.strip())

    return choices


def extract_answer_number(block: str, answer_text: str) -> Optional[int]:
    m = re.search(r"\d+", answer_text)
    if m:
        return int(m.group(0))

    patterns = [
        r"(?:^|\n)解答\s*[:：]?\s*(\d+)\s*(?=\n|$)",
        r"(?:^|\n)正答\s*[:：]?\s*(\d+)\s*(?=\n|$)",
        r"(?:^|\n)解答\s*[:：]?\s*\n\s*(\d+)",
        r"(?:^|\n)正答\s*[:：]?\s*\n\s*(\d+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, block)
        if m:
            return int(m.group(1))

    return None


def parse_question_block(block: str) -> Dict[str, Any]:
    qnum_match = re.search(r"^問\s*0*(\d+)\s*$", block, flags=re.MULTILINE)
    qnum = int(qnum_match.group(1)) if qnum_match else -1

    question = extract_first_available_section(
        block,
        ["設問", "問題"],
        ["選択肢"],
    )

    choices_text = extract_first_available_section(
        block,
        ["選択肢"],
        ["解答", "正答"],
    )

    answer_text = extract_first_available_section(
        block,
        ["解答", "正答"],
        ["難易度", "解説"],
    )
    if not answer_text:
        answer_text = extract_first_available_section(
            block,
            ["解答", "正答"],
            ["解説"],
        )

    explanation = extract_first_available_section(
        block,
        ["解説"],
        [],
    )

    choices = parse_choices(choices_text)
    answer_num = extract_answer_number(block, answer_text)

    if not question:
        raise ValueError(f"問題文が見つかりません: 問{qnum}")
    if len(choices) < 2:
        raise ValueError(f"選択肢の解析に失敗: 問{qnum}")
    if answer_num is None:
        raise ValueError(f"正答が見つかりません: 問{qnum}")

    correct_index = answer_num - 1
    if not (0 <= correct_index < len(choices)):
        raise ValueError(f"正答番号が不正: 問{qnum}")

    return {
        "qnum": qnum,
        "question": question,
        "choices": choices,
        "correct_index": correct_index,
        "explanation": explanation,
        "field": FIELD_NAME,
    }


def load_source_questions(txt_path: Path) -> List[Dict[str, Any]]:
    text = txt_path.read_text(encoding="utf-8")
    blocks = split_question_blocks(text)
    return [parse_question_block(block) for block in blocks]


# =========================
# OpenAI生成
# =========================
def build_prompt(source_q: Dict[str, Any]) -> str:
    source_q = {
        **source_q,
        "question": clean_text_for_api(source_q["question"]),
        "choices": [clean_text_for_api(c) for c in source_q["choices"]],
        "explanation": clean_text_for_api(source_q["explanation"]),
    }

    correct_choice = source_q["choices"][source_q["correct_index"]]

    payload = {
        "field": source_q["field"],
        "source_question_number": source_q["qnum"],
        "source_question": source_q["question"],
        "source_choices": source_q["choices"],
        "source_correct_choice": correct_choice,
        "source_explanation": source_q["explanation"],
    }

    return f"""
あなたは救急救命士国家試験向け問題の作成アシスタントです。
入力された元問題をもとに、日本語で Easy版 と Hard版 の2問を作成してください。

【重要ルール】
- 学習テーマは元問題と同じにする
- 医学的・教育的に不自然な内容にしない
- 正解は必ず1つ
- Easy版は初心者向けに、3択にする
- Easy版は基礎的・直接的な問い方にする
- Easy版の correct_index は 0〜2 の整数
- Hard版は応用・判断を少し含む5択にする
- Hard版の correct_index は 0〜4 の整数
- explanation は簡潔でよい
- why_wrong は空文字でよい
- 出力はJSONのみ
- Markdownやコードブロックは禁止

【出力形式】
{{
  "easy": {{
    "question": "...",
    "choices": ["...", "...", "..."],
    "correct_index": 0,
    "explanation": "...",
    "why_wrong": ""
  }},
  "hard": {{
    "question": "...",
    "choices": ["...", "...", "...", "...", "..."],
    "correct_index": 0,
    "explanation": "...",
    "why_wrong": ""
  }}
}}

【元問題】
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()


def validate_generated(data: Dict[str, Any]) -> None:
    if "easy" not in data or "hard" not in data:
        raise ValueError("easy または hard がありません")

    easy = data["easy"]
    hard = data["hard"]

    if not isinstance(easy.get("question"), str) or not easy["question"].strip():
        raise ValueError("easy: question 不正")
    if not isinstance(easy.get("choices"), list) or len(easy["choices"]) != 3:
        raise ValueError("easy: choices は3個必要")
    if not all(isinstance(c, str) and c.strip() for c in easy["choices"]):
        raise ValueError("easy: 空の選択肢があります")
    if not isinstance(easy.get("correct_index"), int) or not (0 <= easy["correct_index"] < 3):
        raise ValueError("easy: correct_index 不正")
    if not isinstance(easy.get("explanation", ""), str):
        raise ValueError("easy: explanation 不正")
    if not isinstance(easy.get("why_wrong", ""), str):
        raise ValueError("easy: why_wrong 不正")

    if not isinstance(hard.get("question"), str) or not hard["question"].strip():
        raise ValueError("hard: question 不正")
    if not isinstance(hard.get("choices"), list) or len(hard["choices"]) != 5:
        raise ValueError("hard: choices は5個必要")
    if not all(isinstance(c, str) and c.strip() for c in hard["choices"]):
        raise ValueError("hard: 空の選択肢があります")
    if not isinstance(hard.get("correct_index"), int) or not (0 <= hard["correct_index"] < 5):
        raise ValueError("hard: correct_index 不正")
    if not isinstance(hard.get("explanation", ""), str):
        raise ValueError("hard: explanation 不正")
    if not isinstance(hard.get("why_wrong", ""), str):
        raise ValueError("hard: why_wrong 不正")


def generate_easy_hard(client: OpenAI, source_q: Dict[str, Any]) -> Dict[str, Any]:
    prompt = build_prompt(source_q)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "あなたは日本語の国家試験問題作成を支援する厳密なアシスタントです。必ずJSONのみ返してください。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
    )

    content = response.choices[0].message.content
    data = json.loads(content)

    validate_generated(data)
    return data


# =========================
# JSON組み立て
# =========================
def make_output_question(
    source_q: Dict[str, Any],
    gen_item: Dict[str, Any],
    difficulty: str,
) -> Dict[str, Any]:
    qnum = source_q["qnum"]
    suffix = difficulty.lower()

    return {
        "id": f"exam10_q{qnum:03d}_{suffix}",
        "question": gen_item["question"].strip(),
        "choices": [c.strip() for c in gen_item["choices"]],
        "correct_index": gen_item["correct_index"],
        "explanation": gen_item.get("explanation", "").strip(),
        "why_wrong": gen_item.get("why_wrong", "").strip(),
        "field": source_q["field"],
        "difficulty": difficulty,
    }


def save_output_json(path: Path, questions: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"questions": questions}
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def append_debug_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(message.rstrip() + "\n\n")


# =========================
# メイン処理
# =========================
def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が設定されていません。")

    if not INPUT_TXT.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {INPUT_TXT}")

    client = OpenAI(api_key=api_key)
    source_questions = load_source_questions(INPUT_TXT)

    print(f"元問題数: {len(source_questions)}")
    generated_questions: List[Dict[str, Any]] = []

    if DEBUG_TXT.exists():
        DEBUG_TXT.unlink()

    for i, source_q in enumerate(source_questions, start=1):
        qlabel = f"問{source_q['qnum']}"
        print(f"[{i}/{len(source_questions)}] 生成中: {qlabel}")

        try:
            gen = generate_easy_hard(client, source_q)

            easy_q = make_output_question(source_q, gen["easy"], "Easy")
            hard_q = make_output_question(source_q, gen["hard"], "Hard")

            generated_questions.append(easy_q)
            generated_questions.append(hard_q)

            time.sleep(SLEEP_SEC)

        except Exception as e:
            msg = (
                f"{qlabel} 生成失敗\n"
                f"question: {source_q['question']}\n"
                f"error: {repr(e)}"
            )
            append_debug_log(DEBUG_TXT, msg)
            print(f"  -> 失敗: {e}")

    save_output_json(OUTPUT_JSON, generated_questions)

    print("完了")
    print(f"保存先: {OUTPUT_JSON}")
    print(f"生成問題数: {len(generated_questions)}")
    if DEBUG_TXT.exists():
        print(f"失敗ログ: {DEBUG_TXT}")


if __name__ == "__main__":
    main()