from __future__ import annotations

import copy
import json
import random
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, List, Tuple

import streamlit as st
import streamlit.components.v1 as components

# =========================================================
# Config
# =========================================================
st.set_page_config(
    page_title="救命士国家試験アプリ",
    page_icon="🚑",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DATA_DIR = Path("data")

FIELD_ORDER = [
    "00. 全選択ランダム",
    "生命倫理と社会保障",
    "人体の構造と機能",
    "疾患の成り立ちと薬理学",
    "医療体制と法規",
    "観察と重症度判断",
    "内因性救急",
    "症候別アプローチ",
    "外傷救急",
    "特殊病態",
    "総合模試",
]

FIELD_EMOJI: Dict[str, str] = {
    "00. 全選択ランダム": "🎲",
    "生命倫理と社会保障": "⚖️",
    "人体の構造と機能": "🫀",
    "疾患の成り立ちと薬理学": "💊",
    "医療体制と法規": "📘",
    "観察と重症度判断": "🩺",
    "内因性救急": "🧠",
    "症候別アプローチ": "🔎",
    "外傷救急": "🩹",
    "特殊病態": "⚠️",
    "総合模試": "🏁",
}

DIFFICULTY_OPTIONS = ["easy", "normal", "hard"]
DIFFICULTY_FLAMES = {"easy": "🔥", "normal": "🔥🔥", "hard": "🔥🔥🔥"}
DIFFICULTY_LABEL = {
    "easy": "Easy（3択）",
    "normal": "Normal（5択）",
    "hard": "Hard（5択）",
}

COUNT_OPTIONS = [5, 10, 15, 20]

RANK_TABLE = [
    (100, 100, "🏆 神", "#fbbf24", "#92400e", "完璧！ あなたは神！ 全問正解おめでとう！"),
    (80, 99, "✨ 秀才", "#60a5fa", "#1e3a5f", "素晴らしい！ この調子で合格を掴み取ろう！"),
    (60, 79, "🎓 合格点", "#34d399", "#064e3b", "合格ライン！ あと一歩、詰めていこう！"),
    (30, 59, "📖 基本に戻れ", "#fcd34d", "#78350f", "基礎を固め直せば、まだまだ伸びる！"),
    (0, 29, "💪 ここから伸びる", "#fb923c", "#7c2d12", "ここが土台！ 繰り返せば必ず上がる！"),
]


# =========================================================
# Helpers
# =========================================================
def render_html(content: str) -> None:
    st.markdown(dedent(content).strip(), unsafe_allow_html=True)


def render_rank_card_html(rate: float, correct: int, total: int, nick: str, is_partial: bool) -> None:
    rank_label, bg, fg, msg = get_rank(rate)
    rank_icon = rank_label.split(" ")[0]

    nick_html = f"<div class='nick-line'>👤 {nick}</div>" if nick else ""
    partial_html = "<div class='partial-line'>※ 途中中断時点の成績</div>" if is_partial else ""

    html = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
      <meta charset="utf-8">
      <style>
        body {{
          margin: 0;
          padding: 0;
          background: transparent;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}
        .rank-card {{
          border-radius: 24px;
          padding: 24px 16px;
          text-align: center;
          background: {bg};
          color: {fg};
          box-sizing: border-box;
          animation: rankPop .5s ease-out;
        }}
        .nick-line {{
          font-size: .9rem;
          margin-bottom: .3rem;
          font-weight: 700;
        }}
        .rank-icon {{
          font-size: 2.5rem;
          line-height: 1;
        }}
        .rank-label {{
          font-size: 1.6rem;
          font-weight: 900;
          margin: .35rem 0;
        }}
        .rank-rate {{
          font-size: 1.05rem;
          font-weight: 700;
        }}
        .rank-msg {{
          font-size: .95rem;
          margin-top: .45rem;
          line-height: 1.6;
        }}
        .partial-line {{
          font-size: .85rem;
          margin-top: .45rem;
          opacity: .9;
        }}
        @keyframes rankPop {{
          0%   {{ transform: scale(.5); opacity: 0; }}
          60%  {{ transform: scale(1.05); }}
          100% {{ transform: scale(1); opacity: 1; }}
        }}
      </style>
    </head>
    <body>
      <div class="rank-card">
        {nick_html}
        <div class="rank-icon">{rank_icon}</div>
        <div class="rank-label">{rank_label}</div>
        <div class="rank-rate">{rate:.0f}%（{correct}/{total}問正解）</div>
        <div class="rank-msg">{msg}</div>
        {partial_html}
      </div>
    </body>
    </html>
    """
    components.html(html, height=230)


def infer_field_from_filename(filename: str) -> str:
    mapping = {
        "exam_01": "生命倫理と社会保障",
        "exam_02": "人体の構造と機能",
        "exam_03": "疾患の成り立ちと薬理学",
        "exam_04": "医療体制と法規",
        "exam_05": "観察と重症度判断",
        "exam_06": "内因性救急",
        "exam_07": "症候別アプローチ",
        "exam_08": "外傷救急",
        "exam_09": "特殊病態",
        "exam_10": "総合模試",
    }
    for key, value in mapping.items():
        if key in filename:
            return value
    return ""


def normalize_field(raw: Any) -> str:
    return str(raw).strip()


def normalize_correct_indices(item: Dict[str, Any]) -> List[int]:
    raw = item.get("correct_indices")
    if isinstance(raw, list):
        vals = [v for v in raw if isinstance(v, int)]
        if vals:
            return sorted(list(dict.fromkeys(vals)))

    correct_index = item.get("correct_index")
    if isinstance(correct_index, int):
        return [correct_index]

    return []


def infer_select_count(question_text: str, correct_indices: List[int]) -> int:
    if len(correct_indices) >= 2:
        return len(correct_indices)
    text = str(question_text)
    if "2つ選べ" in text or "２つ選べ" in text:
        return 2
    return 1


def to_3_choices_single(
    choices: List[str], correct_index: int
) -> Tuple[List[str], int, List[int]]:
    correct = choices[correct_index]
    wrongs = [c for i, c in enumerate(choices) if i != correct_index]
    picked = random.sample(wrongs, min(2, len(wrongs)))
    new_choices = picked + [correct]
    random.shuffle(new_choices)
    new_index = new_choices.index(correct)
    return new_choices, new_index, [new_index]


def to_3_choices_multi(
    choices: List[str], correct_indices: List[int]
) -> Tuple[List[str], int, List[int]]:
    correct_choices = [choices[i] for i in correct_indices if 0 <= i < len(choices)]
    wrong_choices = [c for i, c in enumerate(choices) if i not in correct_indices]

    if len(correct_choices) < 2 or len(wrong_choices) < 1:
        first_idx = correct_indices[0] if correct_indices else 0
        return choices, first_idx, correct_indices

    picked_wrong = random.choice(wrong_choices)
    new_choices = correct_choices[:2] + [picked_wrong]
    random.shuffle(new_choices)
    new_correct_indices = sorted([new_choices.index(c) for c in correct_choices[:2]])
    first_idx = new_correct_indices[0]
    return new_choices, first_idx, new_correct_indices


def get_rank(rate: float):
    for lo, hi, label, bg, fg, msg in RANK_TABLE:
        if lo <= rate <= hi:
            return label, bg, fg, msg
    return RANK_TABLE[-1][2:]


def is_answer_correct(selected: Any, correct_indices: List[int], select_count: int) -> bool:
    if select_count == 1:
        return isinstance(selected, int) and selected in correct_indices

    if not isinstance(selected, list):
        return False

    clean_sel = sorted([v for v in selected if isinstance(v, int)])
    clean_correct = sorted([v for v in correct_indices if isinstance(v, int)])
    return clean_sel == clean_correct


# =========================================================
# CSS
# =========================================================
def inject_css() -> None:
    st.markdown(
        dedent(
            """
            <style>
            .stApp { background: #f7f9fc; }
            header[data-testid="stHeader"] { height: 0rem !important; background: transparent !important; }
            .block-container {
                max-width: 780px;
                padding-top: 2.5rem !important;
                padding-bottom: 3rem !important;
            }
            @media (max-width: 768px) {
                .block-container {
                    padding-top: 3rem !important;
                    padding-left: 0.9rem !important;
                    padding-right: 0.9rem !important;
                }
            }

            .cover-hero {
                background: linear-gradient(135deg, #0f766e 0%, #155e75 55%, #1d4ed8 100%);
                color: white; border-radius: 28px;
                padding: 1.6rem 1.3rem 1.4rem; margin-bottom: 1rem;
                box-shadow: 0 18px 36px rgba(15,118,110,.18);
            }
            .cover-badge {
                display: inline-block; background: rgba(255,255,255,.18);
                border: 1px solid rgba(255,255,255,.22); color: white;
                border-radius: 999px; padding: .28rem .7rem;
                font-size: .82rem; font-weight: 700; margin-bottom: .9rem;
            }
            .cover-title { font-size: 2rem; font-weight: 900; line-height: 1.3; margin: 0 0 .3rem 0; }
            .cover-lead { font-size: .95rem; line-height: 1.7; color: rgba(255,255,255,.92); }
            .cover-stats { display: flex; gap: .6rem; margin-top: .9rem; }
            .cover-stat {
                flex: 1; background: rgba(255,255,255,.14);
                border: 1px solid rgba(255,255,255,.18);
                border-radius: 16px; padding: .7rem .5rem; text-align: center;
            }
            .cover-stat-val { font-size: 1.15rem; font-weight: 900; }
            .cover-stat-lbl { font-size: .78rem; color: rgba(255,255,255,.88); margin-top: .15rem; }

            .nick-card {
                background: white; border: 1px solid #d8e2f0; border-radius: 18px;
                padding: .9rem 1rem; margin-bottom: .8rem;
                box-shadow: 0 4px 12px rgba(0,0,0,.03);
            }
            .nick-label { font-size: .85rem; font-weight: 700; color: #6b7280; margin-bottom: .3rem; }
            .nick-name { font-size: 1.15rem; font-weight: 800; color: #15253f; }

            .card {
                background: white; border: 1px solid #d8e2f0;
                border-radius: 20px; padding: 1rem;
                box-shadow: 0 6px 18px rgba(0,0,0,.03); margin-bottom: .8rem;
            }
            .section-title {
                font-size: 1.1rem; font-weight: 800; color: #15253f;
                margin: 1.2rem 0 .5rem 0;
            }

            div[data-testid="stButton"] > button {
                border-radius: 14px !important;
                font-weight: 700 !important;
            }

            div[data-testid="stSegmentedControl"] {
                margin-bottom: .5rem;
            }
            div[data-testid="stSegmentedControl"] button {
                border-radius: 14px !important;
                font-weight: 700 !important;
                min-height: 46px !important;
            }
            div[data-testid="stPills"] button {
                border-radius: 14px !important;
                font-weight: 700 !important;
                min-height: 44px !important;
            }

            .metric-row { display: flex; gap: .6rem; margin-bottom: .8rem; }
            .metric-card {
                flex: 1; background: white; border: 1px solid #d8e2f0;
                border-radius: 16px; padding: .7rem .5rem; text-align: center;
                box-shadow: 0 4px 12px rgba(0,0,0,.03);
            }
            .metric-label { font-size: .78rem; color: #6b7280; }
            .metric-value { font-size: 1.3rem; font-weight: 800; color: #15253f; margin-top: .15rem; }

            .progress-wrap { margin-bottom: .8rem; }
            .progress-meta {
                display: flex; justify-content: space-between;
                font-size: .82rem; color: #6b7280; margin-bottom: .3rem;
            }
            .progress-bar { height: 8px; background: #e5e7eb; border-radius: 99px; overflow: hidden; }
            .progress-fill {
                height: 100%; border-radius: 99px;
                background: linear-gradient(90deg, #0f766e, #1d4ed8); transition: width .3s;
            }

            .q-card {
                background: white; border: 1px solid #d8e2f0;
                border-radius: 20px; padding: 1.1rem;
                box-shadow: 0 8px 20px rgba(0,0,0,.04); margin-bottom: .8rem;
            }
            .q-meta { font-size: .82rem; color: #6b7280; margin-bottom: .5rem; }
            .q-text { font-size: 1.05rem; font-weight: 700; line-height: 1.75; color: #15253f; }

            .bar-row { display: flex; align-items: center; margin-bottom: .45rem; }
            .bar-label { width: 160px; font-size: .85rem; font-weight: 600; color: #15253f; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .bar-track { flex: 1; height: 14px; background: #e5e7eb; border-radius: 99px; overflow: hidden; margin: 0 .5rem; }
            .bar-fill { height: 100%; border-radius: 99px; transition: width .3s; }
            .bar-pct { width: 48px; font-size: .82rem; font-weight: 700; color: #15253f; text-align: right; }
            </style>
            """
        ).strip(),
        unsafe_allow_html=True,
    )


# =========================================================
# Data loading
# =========================================================
@st.cache_data(show_spinner=False)
def load_questions(data_dir: Path) -> List[Dict[str, Any]]:
    questions: List[Dict[str, Any]] = []
    if not data_dir.exists():
        return questions

    for path in sorted(data_dir.glob("exam_*.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            raw = data.get("questions", [])
            if not isinstance(raw, list):
                continue

            inferred_field = infer_field_from_filename(path.name)
            is_plus = "_plus" in path.name

            for item in raw:
                if not isinstance(item, dict):
                    continue

                qid = str(item.get("id", "")).strip()
                question = str(item.get("question", "")).strip()
                choices = item.get("choices", [])

                if not qid or not question:
                    continue
                if not isinstance(choices, list) or len(choices) < 2:
                    continue

                correct_indices = normalize_correct_indices(item)
                if not correct_indices:
                    continue
                if any(not (0 <= idx < len(choices)) for idx in correct_indices):
                    continue

                field = normalize_field(item.get("field", ""))
                if not field:
                    field = inferred_field

                if is_plus:
                    diff = str(item.get("difficulty", "")).strip().lower()
                    if diff not in ("easy", "hard"):
                        diff = "hard"
                else:
                    diff = "normal"

                select_count = infer_select_count(question, correct_indices)

                questions.append(
                    {
                        "id": qid,
                        "question": question,
                        "choices": [str(c).strip() for c in choices],
                        "correct_index": correct_indices[0],
                        "correct_indices": correct_indices,
                        "select_count": select_count,
                        "explanation": str(item.get("explanation", "")).strip(),
                        "why_wrong": str(item.get("why_wrong", "")).strip(),
                        "field": field,
                        "difficulty": diff,
                    }
                )
        except Exception:
            continue

    return questions


# =========================================================
# Session state
# =========================================================
def init_session_state() -> None:
    saved_nickname = str(st.query_params.get("nick", "")).strip()

    defaults: Dict[str, Any] = {
        "page": "cover",
        "nickname": saved_nickname,
        "nickname_registered": bool(saved_nickname),
        "sel_difficulty": "normal",
        "sel_field": "00. 全選択ランダム",
        "sel_count": 10,
        "quiz_questions": [],
        "quiz_answers": [],
        "quiz_checked": [],
        "quiz_index": 0,
        "total_answered": 0,
        "total_correct": 0,
        "field_stats": {},
        "question_stats": {},
        "sessions": [],
        "user_sessions": {},
        "user_stats": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_all() -> None:
    nickname = st.session_state.get("nickname", "")
    registered = st.session_state.get("nickname_registered", False)
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.session_state["nickname"] = nickname
    st.session_state["nickname_registered"] = registered
    st.rerun()


def get_current_nick() -> str:
    nick = st.session_state.get("nickname", "").strip()
    return nick if nick else "__guest__"


def get_user_store() -> Dict[str, Any]:
    nick = get_current_nick()
    stores = st.session_state.user_stats

    if nick not in stores:
        stores[nick] = {
            "total_answered": 0,
            "total_correct": 0,
            "field_stats": {},
            "question_stats": {},
            "sessions": [],
        }
    return stores[nick]


def get_field_stat(field: str) -> Dict[str, int]:
    user_store = get_user_store()
    s = user_store["field_stats"]
    if field not in s:
        s[field] = {"answered": 0, "correct": 0}
    return s[field]


def get_question_stat(qid: str) -> Dict[str, int]:
    user_store = get_user_store()
    s = user_store["question_stats"]
    if qid not in s:
        s[qid] = {"seen": 0, "correct": 0, "wrong": 0}
    return s[qid]


# =========================================================
# Quiz builder
# =========================================================
def build_quiz(
    questions: List[Dict[str, Any]], field: str, difficulty: str, count: int
) -> List[Dict[str, Any]]:
    pool = [q for q in questions if q["difficulty"] == difficulty]
    if field != "00. 全選択ランダム":
        pool = [q for q in pool if normalize_field(q.get("field", "")) == field]
    if not pool:
        return []

    picked = random.sample(pool, min(count, len(pool)))
    quiz: List[Dict[str, Any]] = []

    for q in picked:
        q2 = copy.deepcopy(q)

        if difficulty == "easy" and len(q2["choices"]) > 3:
            if q2.get("select_count", 1) == 1:
                new_choices, new_correct_index, new_correct_indices = to_3_choices_single(
                    q2["choices"], q2["correct_index"]
                )
            else:
                new_choices, new_correct_index, new_correct_indices = to_3_choices_multi(
                    q2["choices"], q2["correct_indices"]
                )

            q2["choices"] = new_choices
            q2["correct_index"] = new_correct_index
            q2["correct_indices"] = new_correct_indices

        quiz.append(q2)

    return quiz


# =========================================================
# Weak-field analysis
# =========================================================
def analyze_weak_fields() -> List[Dict[str, Any]]:
    user_store = get_user_store()
    field_stats = user_store["field_stats"]

    results: List[Dict[str, Any]] = []
    for field in FIELD_ORDER:
        if field == "00. 全選択ランダム":
            continue
        fs = field_stats.get(field)
        if not fs or fs["answered"] == 0:
            continue
        rate = fs["correct"] / fs["answered"] * 100
        results.append(
            {
                "field": field,
                "answered": fs["answered"],
                "correct": fs["correct"],
                "rate": rate,
            }
        )
    results.sort(key=lambda x: x["rate"])
    return results


def generate_advice(weak: List[Dict[str, Any]]) -> str:
    if not weak:
        return "まだ十分なデータがありません。各分野を学習してからもう一度チェックしましょう。"

    worst = weak[0]
    emoji = FIELD_EMOJI.get(worst["field"], "📚")
    w_rate = worst["rate"]
    w_ans = worst["answered"]
    w_wrong = w_ans - worst["correct"]

    lines: List[str] = []

    lines.append(f"**{emoji} 「{worst['field']}」** が最も弱い分野です。")
    lines.append(f"正答率 {w_rate:.0f}%（{worst['correct']}/{w_ans}問正解 / {w_wrong}問誤答）")
    lines.append("")

    if w_rate < 30:
        lines.append("⚠️ **かなり苦手な分野です。** 基礎から見直す必要があります。")
        lines.append("")
        lines.append("**おすすめアクション：**")
        lines.append("1. 📖 まずテキストでこの分野の基礎用語・基本概念を読み直す")
        lines.append("2. 📝 間違えた問題を1問ずつテキストで調べ、なぜ間違えたかノートに書く")
        lines.append("3. 🔥 Easy モードで基礎問題を繰り返す")
        lines.append("4. 🔄 3日後にもう一度同じ分野をやって定着を確認")
    elif w_rate < 50:
        lines.append("📉 **基礎はあるが定着が弱い分野です。** 反復が鍵になります。")
        lines.append("")
        lines.append("**おすすめアクション：**")
        lines.append("1. 📖 間違えた問題の選択肢を1つずつテキストで確認する")
        lines.append("2. 📝 「なぜその選択肢が正解か」「なぜ他が不正解か」を自分の言葉で説明してみる")
        lines.append("3. 🔥 Easy → Normal の順で出題し、正答率の変化を見る")
        lines.append("4. 🧠 似た問題が出たとき、どのキーワードに注目すべきか意識する")
    elif w_rate < 70:
        lines.append("📊 **あと一歩で安定する分野です。** 弱点の穴を埋めましょう。")
        lines.append("")
        lines.append("**おすすめアクション：**")
        lines.append("1. ❌ 間違えた問題だけを抜き出して、テキストの該当ページを重点的に読む")
        lines.append("2. 📝 間違えやすいパターン（似た選択肢・引っかけ）をメモしておく")
        lines.append("3. 🔥🔥 Normal モードで連続正解を目指す")
        lines.append("4. 📚 過去問や参考書の類似問題も解いてみる")
    else:
        lines.append("✅ **正答率は高いですが、他の分野と比べると相対的に弱い部分です。**")
        lines.append("")
        lines.append("**おすすめアクション：**")
        lines.append("1. 🔥🔥🔥 Hard モードで応用力を確認")
        lines.append("2. ❌ 数少ない誤答問題をテキストで徹底的に調べる")
        lines.append("3. ⏱ 時間を意識して解くスピード練習をする")
        lines.append("4. 📖 テキストの発展内容・補足コラムにも目を通す")

    lines.append("")
    if w_ans < 10:
        lines.append(f"💡 まだ {w_ans}問しか解いていません。最低でも20問は解くと傾向が見えてきます。")
    elif w_ans < 30:
        lines.append(f"💡 {w_ans}問のデータです。もう少し解くと、より正確な分析ができます。")
    else:
        lines.append(f"💡 {w_ans}問分のデータがあります。信頼性の高い分析です。")

    if len(weak) >= 2:
        second = weak[1]
        e2 = FIELD_EMOJI.get(second["field"], "📚")
        lines.append("")
        lines.append(
            f"次に弱いのは **{e2} 「{second['field']}」**（正答率 {second['rate']:.0f}%）です。"
            " この分野もあわせて復習すると効率的です。"
        )

    lines.append("")
    lines.append("---")
    lines.append("**📚 効果的な復習のコツ：**")
    lines.append("- 間違えた問題は **テキストの該当ページを開いて確認** する習慣をつける")
    lines.append("- 正解の選択肢だけでなく **不正解の選択肢がなぜ違うのか** も調べる")
    lines.append("- 1日後・3日後・1週間後に **同じ問題を再挑戦** して記憶を定着させる")
    lines.append("- 友達に **問題の解説を自分の言葉で教える** と理解が深まる")

    return "\n".join(lines)


# =========================================================
# Page: Cover
# =========================================================
def render_cover(questions: List[Dict[str, Any]]) -> None:
    total_q = len(questions)
    fields_available = len(set(q["field"] for q in questions if q["field"]))
    user_store = get_user_store()
    wrong_count = sum(
        1 for v in user_store["question_stats"].values() if v.get("wrong", 0) > 0
    )

    nick = st.session_state.nickname.strip()
    lead = (
        f"{nick} さん、今日も頑張ろう！"
        if nick
        else "分野別 × 難易度別で効率よく国試対策"
    )

    render_html(
        f"""
        <div class="cover-hero">
            <div class="cover-badge">🚑 EMT NATIONAL EXAM APP</div>
            <div class="cover-title">救命士国家試験アプリ</div>
            <div class="cover-lead">{lead}</div>
            <div class="cover-stats">
                <div class="cover-stat">
                    <div class="cover-stat-val">{total_q}</div>
                    <div class="cover-stat-lbl">登録問題数</div>
                </div>
                <div class="cover-stat">
                    <div class="cover-stat-val">{fields_available}</div>
                    <div class="cover-stat-lbl">学習分野</div>
                </div>
                <div class="cover-stat">
                    <div class="cover-stat-val">{wrong_count}</div>
                    <div class="cover-stat-lbl">復習対象</div>
                </div>
            </div>
        </div>
        """
    )

    if not st.session_state.nickname_registered:
        render_html('<div class="section-title">■ ニックネーム登録</div>')
        c1, c2 = st.columns([3, 1])
        with c1:
            name_input = st.text_input(
                "ニックネーム",
                value=st.session_state.nickname,
                placeholder="例：太郎",
                label_visibility="collapsed",
            )
        with c2:
            if st.button("登録", use_container_width=True, type="primary"):
                if name_input.strip():
                    clean_name = name_input.strip()
                    st.session_state.nickname = clean_name
                    st.session_state.nickname_registered = True
                    st.query_params["nick"] = clean_name
                    st.rerun()
                else:
                    st.warning("入力してね")
    else:
        render_html(
            f"""
            <div class="nick-card">
                <div class="nick-label">👤 ニックネーム</div>
                <div class="nick-name">{st.session_state.nickname}</div>
            </div>
            """
        )
        if st.button("✏️ ニックネーム変更", key="change_nick"):
            st.session_state.nickname = ""
            st.session_state.nickname_registered = False
            if "nick" in st.query_params:
                del st.query_params["nick"]
            st.rerun()

    render_html('<div class="section-title">■ 難易度を選ぶ</div>')
    selected_diff = st.segmented_control(
        "難易度",
        DIFFICULTY_OPTIONS,
        default=st.session_state.sel_difficulty,
        selection_mode="single",
        format_func=lambda diff: f"{DIFFICULTY_FLAMES[diff]} {diff.capitalize()}（{'3択' if diff == 'easy' else '5択'}）",
        label_visibility="collapsed",
        width="stretch",
        key="seg_difficulty",
    )
    if selected_diff:
        st.session_state.sel_difficulty = selected_diff

    render_html('<div class="section-title">■ 分野を選ぶ</div>')
    selected_field = st.pills(
        "分野",
        FIELD_ORDER,
        default=st.session_state.sel_field,
        selection_mode="single",
        format_func=lambda field: f"{FIELD_EMOJI.get(field, '📚')} {field.replace('00. ', '')}",
        label_visibility="collapsed",
        width="stretch",
        key="pill_field",
    )
    if selected_field:
        st.session_state.sel_field = selected_field

    render_html('<div class="section-title">■ 問題数</div>')
    selected_count = st.segmented_control(
        "問題数",
        COUNT_OPTIONS,
        default=st.session_state.sel_count,
        selection_mode="single",
        format_func=lambda cnt: f"{cnt} 問",
        label_visibility="collapsed",
        width="stretch",
        key="seg_count",
    )
    if selected_count:
        st.session_state.sel_count = selected_count

    st.markdown("")
    if st.button("🚀 学習スタート！", use_container_width=True, type="primary"):
        _start_quiz(
            questions,
            st.session_state.sel_field,
            st.session_state.sel_difficulty,
            st.session_state.sel_count,
        )

    st.markdown("")
    if st.button("🎲 ランダム100問チャレンジ！", use_container_width=True):
        _start_quiz(
            questions,
            "00. 全選択ランダム",
            st.session_state.sel_difficulty,
            100,
        )

    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📊 学習履歴", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()
    with c2:
        if st.button("🧠 苦手分野を見る", use_container_width=True):
            st.session_state.page = "weak"
            st.rerun()

    st.markdown("")
    if st.button("🗑 履歴をすべてクリア", use_container_width=True):
        reset_all()


def _start_quiz(
    questions: List[Dict[str, Any]],
    field: str,
    difficulty: str,
    count: int,
) -> None:
    quiz = build_quiz(questions, field, difficulty, count)
    if not quiz:
        st.warning("選択した条件に合う問題がありません。分野や難易度を変えてみてください。")
        return

    st.session_state.quiz_questions = quiz
    st.session_state.quiz_answers = [None] * len(quiz)
    st.session_state.quiz_checked = [False] * len(quiz)
    st.session_state.quiz_index = 0
    st.session_state.sel_field = field
    st.session_state.sel_count = count
    st.session_state.page = "question"
    st.rerun()


# =========================================================
# Page: Question
# =========================================================
def render_question_page() -> None:
    quiz = st.session_state.quiz_questions
    idx = st.session_state.quiz_index
    total = len(quiz)

    if not quiz or idx >= total:
        st.session_state.page = "cover"
        st.rerun()
        return

    q = quiz[idx]
    checked = st.session_state.quiz_checked[idx]
    saved_answer = st.session_state.quiz_answers[idx]
    select_count = q.get("select_count", 1)

    diff_label = st.session_state.sel_difficulty.capitalize()
    diff_flames = DIFFICULTY_FLAMES.get(st.session_state.sel_difficulty, "")
    field_label = q.get("field", "")
    pct = int((idx / total) * 100)

    render_html(
        f"""
        <div class="progress-wrap">
            <div class="progress-meta">
                <span>{idx + 1} / {total} 問目</span>
                <span>{field_label} ｜ {diff_flames} {diff_label}</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width:{pct}%"></div>
            </div>
        </div>
        """
    )

    render_html(
        f"""
        <div class="q-card">
            <div class="q-meta">問題ID：{q["id"]}</div>
            <div class="q-text">{q["question"]}</div>
        </div>
        """
    )

    labels = [f"{i + 1}. {c}" for i, c in enumerate(q["choices"])]

    if not checked:
        if select_count == 1:
            default_idx = None
            if isinstance(saved_answer, int) and 0 <= saved_answer < len(labels):
                default_idx = saved_answer

            picked = st.radio(
                "選択肢",
                labels,
                index=default_idx,
                label_visibility="collapsed",
                key=f"radio_{q['id']}_{idx}",
            )
            if picked:
                st.session_state.quiz_answers[idx] = labels.index(picked)

        else:
            default_multi: List[str] = []
            if isinstance(saved_answer, list):
                default_multi = [
                    labels[i] for i in saved_answer
                    if isinstance(i, int) and 0 <= i < len(labels)
                ]

            picked_multi = st.multiselect(
                "選択肢",
                labels,
                default=default_multi,
                max_selections=select_count,
                label_visibility="collapsed",
                key=f"multi_{q['id']}_{idx}",
            )
            st.session_state.quiz_answers[idx] = sorted([labels.index(v) for v in picked_multi])

            st.caption(f"この問題は {select_count}つ選択")

        if st.button("✅ チェック（判定する）", use_container_width=True, type="primary"):
            current_answer = st.session_state.quiz_answers[idx]

            if select_count == 1:
                if current_answer is None:
                    st.warning("選択肢を選んでください。")
                    return
            else:
                if not isinstance(current_answer, list) or len(current_answer) != select_count:
                    st.warning(f"選択肢を {select_count}つ選んでください。")
                    return

            st.session_state.quiz_checked[idx] = True
            st.rerun()

    else:
        sel = saved_answer
        is_correct = is_answer_correct(sel, q["correct_indices"], select_count)

        if is_correct:
            st.success("✅ 正解！")
        else:
            st.error("❌ 不正解")

        selected_set = set(sel) if isinstance(sel, list) else ({sel} if isinstance(sel, int) else set())
        correct_set = set(q["correct_indices"])

        for i, c in enumerate(q["choices"]):
            label = f"{i + 1}. {c}"
            is_selected = i in selected_set
            is_correct_choice = i in correct_set

            if is_selected and is_correct_choice:
                st.success(f"{label}（正解 ✅）")
            elif is_correct_choice:
                st.success(f"{label}（正解）")
            elif is_selected:
                st.error(f"{label}（あなたの解答）")
            else:
                st.write(label)

        if q.get("explanation"):
            st.markdown("**💡 解説**")
            st.info(q["explanation"])
        if not is_correct and q.get("why_wrong"):
            st.markdown("**📖 詳しい解説**")
            st.warning(q["why_wrong"])

    st.markdown("")
    c1, c2, c3 = st.columns(3)
    with c1:
        if idx > 0:
            if st.button("◀ 戻る", use_container_width=True):
                st.session_state.quiz_index = idx - 1
                st.rerun()
        else:
            st.write("")
    with c2:
        if st.button("⏹ 中断して結果を見る", use_container_width=True):
            finalize_quiz(is_partial=True)
    with c3:
        if checked:
            is_last = idx >= total - 1
            btn_label = "📊 結果を見る" if is_last else "次へ ▶"
            if st.button(btn_label, use_container_width=True, type="primary"):
                if is_last:
                    finalize_quiz(is_partial=False)
                else:
                    st.session_state.quiz_index = idx + 1
                    st.rerun()


# =========================================================
# Finalize
# =========================================================
def finalize_quiz(is_partial: bool = False) -> None:
    quiz = st.session_state.quiz_questions
    answers = st.session_state.quiz_answers
    checked_list = st.session_state.quiz_checked

    target_indices = [i for i, checked in enumerate(checked_list) if checked]

    if not target_indices:
        st.warning("まだ1問も判定していません。")
        return

    details: List[Dict[str, Any]] = []
    correct_count = 0

    for i in target_indices:
        q = quiz[i]
        sel = answers[i]
        is_correct = is_answer_correct(sel, q["correct_indices"], q.get("select_count", 1))

        if is_correct:
            correct_count += 1

        qs = get_question_stat(q["id"])
        qs["seen"] += 1
        if is_correct:
            qs["correct"] += 1
        else:
            qs["wrong"] += 1

        fs = get_field_stat(q["field"])
        fs["answered"] += 1
        if is_correct:
            fs["correct"] += 1

        details.append(
            {
                "id": q["id"],
                "field": q["field"],
                "question": q["question"],
                "choices": q["choices"],
                "correct_index": q["correct_index"],
                "correct_indices": q["correct_indices"],
                "selected_index": sel if isinstance(sel, int) else None,
                "selected_indices": sel if isinstance(sel, list) else [],
                "select_count": q.get("select_count", 1),
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
                "why_wrong": q.get("why_wrong", ""),
            }
        )

    total_answered = len(target_indices)
    rate = (correct_count / total_answered * 100) if total_answered else 0

    session_record = {
        "nickname": st.session_state.nickname,
        "field": st.session_state.sel_field,
        "difficulty": st.session_state.sel_difficulty,
        "count": total_answered,
        "planned_count": len(quiz),
        "correct": correct_count,
        "rate": rate,
        "ts": datetime.now().strftime("%m/%d %H:%M"),
        "details": details,
        "is_partial": is_partial,
    }

    st.session_state.sessions.append(session_record)

    nick = st.session_state.nickname.strip()
    if nick:
        if nick not in st.session_state.user_sessions:
            st.session_state.user_sessions[nick] = []
        st.session_state.user_sessions[nick].append(session_record)

    user_store = get_user_store()
    user_store["total_answered"] += total_answered
    user_store["total_correct"] += correct_count
    user_store["sessions"].append(session_record)

    st.session_state.quiz_questions = []
    st.session_state.quiz_answers = []
    st.session_state.quiz_checked = []
    st.session_state.quiz_index = 0
    st.session_state.page = "summary"
    st.rerun()


# =========================================================
# Page: Summary
# =========================================================
def render_summary() -> None:
    if not st.session_state.sessions:
        st.session_state.page = "cover"
        st.rerun()
        return

    session = st.session_state.sessions[-1]
    total = session["count"]
    correct = session["correct"]
    rate = session["rate"]
    details = session["details"]
    nick = session.get("nickname", "")
    planned_count = session.get("planned_count", total)
    is_partial = session.get("is_partial", False)

    if not is_partial:
        if rate == 100:
            st.balloons()
        elif rate >= 80:
            st.snow()

    render_rank_card_html(rate, correct, total, nick, is_partial)

    if is_partial:
        st.info(f"この結果は途中中断時点の成績です。回答済み {total} / {planned_count} 問")

    wrong = total - correct
    render_html(
        f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-label">正解数</div>
                <div class="metric-value" style="color:#059669">{correct}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">誤答数</div>
                <div class="metric-value" style="color:#dc2626">{wrong}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">正答率</div>
                <div class="metric-value">{rate:.0f}%</div>
            </div>
        </div>
        """
    )

    diff_flames = DIFFICULTY_FLAMES.get(session["difficulty"], "")
    diff_label = session["difficulty"].capitalize()
    field_label = session["field"]
    st.caption(f"分野：{field_label}　｜　難易度：{diff_flames} {diff_label}")

    render_html('<div class="section-title">■ 全問題の結果</div>')

    for i, d in enumerate(details, 1):
        icon = "✅" if d["is_correct"] else "❌"
        short_q = d["question"][:50] + ("…" if len(d["question"]) > 50 else "")
        title = f"{icon} Q{i}. {short_q}"

        with st.expander(title, expanded=False):
            st.markdown(f"**問題**  {d['question']}")

            for j, c in enumerate(d["choices"]):
                label = f"{j + 1}. {c}"
                is_correct_choice = j in set(d.get("correct_indices", [d["correct_index"]]))
                selected_indices = set(d.get("selected_indices", []))
                selected_single = d.get("selected_index")
                is_selected = j in selected_indices or j == selected_single

                if is_selected and is_correct_choice:
                    st.success(f"{label}（正解 ✅）")
                elif is_correct_choice:
                    st.success(f"{label}（正解）")
                elif is_selected:
                    st.error(f"{label}（あなたの解答）")
                else:
                    st.write(label)

            if d.get("explanation"):
                st.markdown("**💡 解説**")
                st.info(d["explanation"])
            if not d["is_correct"] and d.get("why_wrong"):
                st.markdown("**📖 詳しい解説**")
                st.warning(d["why_wrong"])

    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🏠 表紙へ", use_container_width=True, type="primary"):
            st.session_state.page = "cover"
            st.rerun()
    with c2:
        if st.button("🗑 全クリア", use_container_width=True):
            reset_all()


# =========================================================
# Page: History
# =========================================================
def render_history() -> None:
    render_html('<div class="section-title">📊 学習履歴</div>')

    user_store = get_user_store()
    total = user_store["total_answered"]
    correct = user_store["total_correct"]
    rate = (correct / total * 100) if total else 0

    render_html(
        f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-label">総問題数</div>
                <div class="metric-value">{total}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">正解数</div>
                <div class="metric-value">{correct}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">正答率</div>
                <div class="metric-value">{rate:.1f}%</div>
            </div>
        </div>
        """
    )

    render_html('<div class="section-title">■ 分野別正答率</div>')
    has_data = False
    field_stats = user_store["field_stats"]

    for field in FIELD_ORDER:
        if field == "00. 全選択ランダム":
            continue
        fs = field_stats.get(field)
        if not fs or fs["answered"] == 0:
            continue
        has_data = True
        f_rate = fs["correct"] / fs["answered"] * 100
        emoji = FIELD_EMOJI.get(field, "📚")
        color = "#059669" if f_rate >= 60 else "#dc2626" if f_rate < 40 else "#d97706"
        render_html(
            f"""
            <div class="bar-row">
                <div class="bar-label">{emoji} {field}</div>
                <div class="bar-track">
                    <div class="bar-fill" style="width:{f_rate}%; background:{color};"></div>
                </div>
                <div class="bar-pct">{f_rate:.0f}%</div>
            </div>
            """
        )

    if not has_data:
        st.info("まだ学習データがありません。")

    sessions = st.session_state.user_sessions.get(st.session_state.nickname, []) if st.session_state.nickname else []
    if sessions:
        render_html('<div class="section-title">■ セッション履歴</div>')
        for s in reversed(sessions[-20:]):
            icon = "🟢" if s["rate"] >= 60 else "🔴"
            diff_flames = DIFFICULTY_FLAMES.get(s["difficulty"], "")
            s_nick = s.get("nickname", "")
            nick_part = f"👤{s_nick}　" if s_nick else ""
            partial_tag = "（中断）" if s.get("is_partial") else ""
            render_html(
                f"""
                <div class="card">
                    {icon} {s["ts"]}　{nick_part}{s["field"]}　
                    {diff_flames} {s["difficulty"].capitalize()}　
                    {s["correct"]}/{s["count"]}問　
                    <strong>{s["rate"]:.0f}%</strong> {partial_tag}
                </div>
                """
            )

    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🏠 表紙へ", use_container_width=True, type="primary"):
            st.session_state.page = "cover"
            st.rerun()
    with c2:
        if st.button("🗑 全クリア", use_container_width=True):
            reset_all()


# =========================================================
# Page: Weak Analysis
# =========================================================
def render_weak(questions: List[Dict[str, Any]]) -> None:
    render_html('<div class="section-title">🧠 AI 苦手分野分析</div>')

    weak = analyze_weak_fields()

    if not weak:
        st.info("まだ十分な学習データがありません。いくつかの分野を学習してから確認しましょう。")
        if st.button("🏠 表紙へ", use_container_width=True):
            st.session_state.page = "cover"
            st.rerun()
        return

    render_html(
        """
        <div class="card">
            <div style="font-weight:800; color:#dc2626; margin-bottom:.5rem;">
                ⚠️ あなたの苦手分野
            </div>
        </div>
        """
    )

    for i, w in enumerate(weak[:3], 1):
        emoji = FIELD_EMOJI.get(w["field"], "📚")
        color = "#dc2626" if w["rate"] < 40 else "#d97706" if w["rate"] < 60 else "#059669"
        render_html(
            f"""
            <div class="bar-row">
                <div class="bar-label">
                    <strong>{i}位</strong> {emoji} {w["field"]}
                </div>
                <div class="bar-track">
                    <div class="bar-fill" style="width:{w['rate']}%; background:{color};"></div>
                </div>
                <div class="bar-pct">{w['rate']:.0f}%</div>
            </div>
            """
        )

    render_html('<div class="section-title">💬 AIからのアドバイス</div>')
    advice = generate_advice(weak)
    st.markdown(advice)

    st.markdown("")
    if weak:
        worst_field = weak[0]["field"]
        if st.button(f"🔥 「{worst_field}」を今すぐ学習", use_container_width=True, type="primary"):
            st.session_state.sel_field = worst_field
            st.session_state.sel_difficulty = "easy"
            st.session_state.sel_count = st.session_state.sel_count
            st.session_state["pill_field"] = worst_field
            st.session_state["seg_difficulty"] = "easy"

            quiz = build_quiz(questions, worst_field, "easy", st.session_state.sel_count)
            if not quiz:
                quiz = build_quiz(questions, worst_field, "normal", st.session_state.sel_count)
                if quiz:
                    st.session_state.sel_difficulty = "normal"
                    st.session_state["seg_difficulty"] = "normal"

            if quiz:
                st.session_state.quiz_questions = quiz
                st.session_state.quiz_answers = [None] * len(quiz)
                st.session_state.quiz_checked = [False] * len(quiz)
                st.session_state.quiz_index = 0
                st.session_state.page = "question"
                st.rerun()
            else:
                st.warning("この分野の問題が見つかりません。")

    if st.button("🏠 表紙へ", use_container_width=True):
        st.session_state.page = "cover"
        st.rerun()


# =========================================================
# Main
# =========================================================
def main() -> None:
    inject_css()
    init_session_state()

    questions = load_questions(DATA_DIR)

    if not questions:
        st.error("問題データを読み込めませんでした。data フォルダを確認してください。")
        return

    page = st.session_state.page

    if page == "cover":
        render_cover(questions)
    elif page == "question":
        render_question_page()
    elif page == "summary":
        render_summary()
    elif page == "history":
        render_history()
    elif page == "weak":
        render_weak(questions)
    else:
        st.session_state.page = "cover"
        st.rerun()


if __name__ == "__main__":
    main()