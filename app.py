from __future__ import annotations

import copy
import json
import random
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

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
DIFFICULTY_LABEL = {"easy": "Easy（3択）", "normal": "Normal（5択）", "hard": "Hard（5択）"}

COUNT_OPTIONS = [5, 10, 15, 20]

RANK_TABLE = [
    (100, 100, "🏆 神",         "#fbbf24", "#92400e", "完璧！ あなたは神！ 全問正解おめでとう！"),
    (80,  99,  "✨ 秀才",       "#60a5fa", "#1e3a5f", "素晴らしい！ この調子で合格を掴み取ろう！"),
    (60,  79,  "🎓 合格点",     "#34d399", "#064e3b", "合格ライン！ あと一歩、詰めていこう！"),
    (30,  59,  "📖 基本に戻れ",  "#fcd34d", "#78350f", "基礎を固め直せば、まだまだ伸びる！"),
    (0,   29,  "💪 ここから伸びる", "#fb923c", "#7c2d12", "ここが土台！ 繰り返せば必ず上がる！"),
]


# =========================================================
# CSS
# =========================================================
def inject_css() -> None:
    st.markdown(
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

        /* ---------- cover hero ---------- */
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

        /* ---------- nickname ---------- */
        .nick-card {
            background: white; border: 1px solid #d8e2f0; border-radius: 18px;
            padding: .9rem 1rem; margin-bottom: .8rem;
            box-shadow: 0 4px 12px rgba(0,0,0,.03);
        }
        .nick-label { font-size: .85rem; font-weight: 700; color: #6b7280; margin-bottom: .3rem; }
        .nick-name { font-size: 1.15rem; font-weight: 800; color: #15253f; }

        /* ---------- generic ---------- */
        .card {
            background: white; border: 1px solid #d8e2f0;
            border-radius: 20px; padding: 1rem;
            box-shadow: 0 6px 18px rgba(0,0,0,.03); margin-bottom: .8rem;
        }
        .section-title {
            font-size: 1.1rem; font-weight: 800; color: #15253f;
            margin: 1.2rem 0 .5rem 0;
        }

        /* ---------- active indicator bar ---------- */
        .active-bar {
            height: 4px; background: linear-gradient(90deg, #0f766e, #1d4ed8);
            border-radius: 99px; margin-top: 2px; margin-bottom: 4px;
        }

        /* ---------- buttons ---------- */
        div[data-testid="stButton"] > button {
            border-radius: 14px !important;
            font-weight: 700 !important;
        }

        /* ---------- metric row ---------- */
        .metric-row { display: flex; gap: .6rem; margin-bottom: .8rem; }
        .metric-card {
            flex: 1; background: white; border: 1px solid #d8e2f0;
            border-radius: 16px; padding: .7rem .5rem; text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,.03);
        }
        .metric-label { font-size: .78rem; color: #6b7280; }
        .metric-value { font-size: 1.3rem; font-weight: 800; color: #15253f; margin-top: .15rem; }

        /* ---------- progress bar ---------- */
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

        /* ---------- question ---------- */
        .q-card {
            background: white; border: 1px solid #d8e2f0;
            border-radius: 20px; padding: 1.1rem;
            box-shadow: 0 8px 20px rgba(0,0,0,.04); margin-bottom: .8rem;
        }
        .q-meta { font-size: .82rem; color: #6b7280; margin-bottom: .5rem; }
        .q-text { font-size: 1.05rem; font-weight: 700; line-height: 1.75; color: #15253f; }

        /* ---------- result rank ---------- */
        @keyframes rankPop {
            0%   { transform: scale(.5); opacity: 0; }
            60%  { transform: scale(1.1); }
            100% { transform: scale(1); opacity: 1; }
        }
        .rank-card {
            border-radius: 24px; padding: 1.5rem 1rem; text-align: center;
            margin-bottom: 1rem; animation: rankPop .6s ease-out;
        }
        .rank-icon { font-size: 2.5rem; }
        .rank-label { font-size: 1.6rem; font-weight: 900; margin: .3rem 0; }
        .rank-rate { font-size: 1.1rem; font-weight: 700; }
        .rank-msg { font-size: .95rem; margin-top: .4rem; line-height: 1.6; }

        /* ---------- bar chart ---------- */
        .bar-row { display: flex; align-items: center; margin-bottom: .45rem; }
        .bar-label { width: 160px; font-size: .85rem; font-weight: 600; color: #15253f; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .bar-track { flex: 1; height: 14px; background: #e5e7eb; border-radius: 99px; overflow: hidden; margin: 0 .5rem; }
        .bar-fill { height: 100%; border-radius: 99px; transition: width .3s; }
        .bar-pct { width: 48px; font-size: .82rem; font-weight: 700; color: #15253f; text-align: right; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# Helpers
# =========================================================
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


def to_3_choices(choices: List[str], correct_index: int) -> Tuple[List[str], int]:
    correct = choices[correct_index]
    wrongs = [c for i, c in enumerate(choices) if i != correct_index]
    picked = random.sample(wrongs, min(2, len(wrongs)))
    new_choices = picked + [correct]
    random.shuffle(new_choices)
    new_index = new_choices.index(correct)
    return new_choices, new_index


def get_rank(rate: float):
    for lo, hi, label, bg, fg, msg in RANK_TABLE:
        if lo <= rate <= hi:
            return label, bg, fg, msg
    return RANK_TABLE[-1][2:]


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
                correct_index = item.get("correct_index")
                if not qid or not question:
                    continue
                if not isinstance(choices, list) or len(choices) < 2:
                    continue
                if not isinstance(correct_index, int):
                    continue
                if not (0 <= correct_index < len(choices)):
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

                questions.append({
                    "id": qid,
                    "question": question,
                    "choices": [str(c).strip() for c in choices],
                    "correct_index": correct_index,
                    "explanation": str(item.get("explanation", "")).strip(),
                    "why_wrong": str(item.get("why_wrong", "")).strip(),
                    "field": field,
                    "difficulty": diff,
                })
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


def get_field_stat(field: str) -> Dict[str, int]:
    s = st.session_state.field_stats
    if field not in s:
        s[field] = {"answered": 0, "correct": 0}
    return s[field]


def get_question_stat(qid: str) -> Dict[str, int]:
    s = st.session_state.question_stats
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
            q2["choices"], q2["correct_index"] = to_3_choices(
                q2["choices"], q2["correct_index"]
            )
        quiz.append(q2)
    return quiz


# =========================================================
# Weak-field analysis
# =========================================================
def analyze_weak_fields() -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for field in FIELD_ORDER:
        if field == "00. 全選択ランダム":
            continue
        fs = st.session_state.field_stats.get(field)
        if not fs or fs["answered"] == 0:
            continue
        rate = fs["correct"] / fs["answered"] * 100
        results.append({
            "field": field,
            "answered": fs["answered"],
            "correct": fs["correct"],
            "rate": rate,
        })
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

    # ---- メイン診断 ----
    lines.append(f"**{emoji} 「{worst['field']}」** が最も弱い分野です。")
    lines.append(f"正答率 {w_rate:.0f}%（{worst['correct']}/{w_ans}問正解 / {w_wrong}問誤答）")
    lines.append("")

    # ---- 正答率に応じたコメント ----
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

    # ---- 問題数に応じた追加アドバイス ----
    lines.append("")
    if w_ans < 10:
        lines.append(f"💡 まだ {w_ans}問しか解いていません。最低でも20問は解くと傾向が見えてきます。")
    elif w_ans < 30:
        lines.append(f"💡 {w_ans}問のデータです。もう少し解くと、より正確な分析ができます。")
    else:
        lines.append(f"💡 {w_ans}問分のデータがあります。信頼性の高い分析です。")

    # ---- 2位の分野 ----
    if len(weak) >= 2:
        second = weak[1]
        e2 = FIELD_EMOJI.get(second["field"], "📚")
        lines.append("")
        lines.append(
            f"次に弱いのは **{e2} 「{second['field']}」**（正答率 {second['rate']:.0f}%）です。"
            " この分野もあわせて復習すると効率的です。"
        )

    # ---- 共通の学習テクニック ----
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
    wrong_count = sum(
        1 for v in st.session_state.question_stats.values() if v.get("wrong", 0) > 0
    )

    nick = st.session_state.nickname.strip()
    lead = (
        f"{nick} さん、今日も頑張ろう！"
        if nick
        else "分野別 × 難易度別で効率よく国試対策"
    )

    st.markdown(
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
        """,
        unsafe_allow_html=True,
    )

    # -------- nickname --------
    if not st.session_state.nickname_registered:
        st.markdown(
            '<div class="section-title">■ ニックネーム登録</div>',
            unsafe_allow_html=True,
        )
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
        st.markdown(
            f"""
            <div class="nick-card">
                <div class="nick-label">👤 ニックネーム</div>
                <div class="nick-name">{st.session_state.nickname}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("✏️ ニックネーム変更", key="change_nick"):
            st.session_state.nickname = ""
            st.session_state.nickname_registered = False
            if "nick" in st.query_params:
                del st.query_params["nick"]
            st.rerun()

    # -------- difficulty --------
    st.markdown(
        '<div class="section-title">■ 難易度を選ぶ</div>',
        unsafe_allow_html=True,
    )
    diff_cols = st.columns(3)
    for i, diff in enumerate(DIFFICULTY_OPTIONS):
        with diff_cols[i]:
            is_active = st.session_state.sel_difficulty == diff
            flames = DIFFICULTY_FLAMES[diff]
            sub = "3択" if diff == "easy" else "5択"
            label = f"{flames}  {diff.capitalize()}（{sub}）"
            if st.button(label, key=f"diff_{diff}", use_container_width=True):
                st.session_state.sel_difficulty = diff
                st.rerun()
            if is_active:
                st.markdown(
                    '<div class="active-bar"></div>',
                    unsafe_allow_html=True,
                )

    # -------- field --------
    st.markdown(
        '<div class="section-title">■ 分野を選ぶ</div>',
        unsafe_allow_html=True,
    )
    cols_per_row = 3
    for row_start in range(0, len(FIELD_ORDER), cols_per_row):
        row_fields = FIELD_ORDER[row_start : row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col_i, field in enumerate(row_fields):
            with cols[col_i]:
                is_active = st.session_state.sel_field == field
                emoji = FIELD_EMOJI.get(field, "📚")
                short_name = field.replace("00. ", "")
                label = f"{emoji} {short_name}"
                if st.button(label, key=f"field_{field}", use_container_width=True):
                    st.session_state.sel_field = field
                    st.rerun()
                if is_active:
                    st.markdown(
                        '<div class="active-bar"></div>',
                        unsafe_allow_html=True,
                    )

    # -------- count --------
    st.markdown(
        '<div class="section-title">■ 問題数</div>',
        unsafe_allow_html=True,
    )
    count_cols = st.columns(len(COUNT_OPTIONS))
    for i, cnt in enumerate(COUNT_OPTIONS):
        with count_cols[i]:
            is_active = st.session_state.sel_count == cnt
            label = f"{cnt} 問"
            if st.button(label, key=f"cnt_{cnt}", use_container_width=True):
                st.session_state.sel_count = cnt
                st.rerun()
            if is_active:
                st.markdown(
                    '<div class="active-bar"></div>',
                    unsafe_allow_html=True,
                )

    # -------- start --------
    st.markdown("")
    if st.button(
        "🚀 学習スタート！", use_container_width=True, type="primary"
    ):
        _start_quiz(
            questions,
            st.session_state.sel_field,
            st.session_state.sel_difficulty,
            st.session_state.sel_count,
        )

    # -------- random 100 --------
    st.markdown("")
    if st.button("🎲 ランダム100問チャレンジ！", use_container_width=True):
        _start_quiz(
            questions,
            "00. 全選択ランダム",
            st.session_state.sel_difficulty,
            100,
        )

    # -------- bottom --------
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
        st.warning(
            "選択した条件に合う問題がありません。分野や難易度を変えてみてください。"
        )
    else:
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

    diff_label = st.session_state.sel_difficulty.capitalize()
    diff_flames = DIFFICULTY_FLAMES.get(st.session_state.sel_difficulty, "")
    field_label = q.get("field", "")
    pct = int((idx / total) * 100)

    # ---- progress ----
    st.markdown(
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
        """,
        unsafe_allow_html=True,
    )

    # ---- question ----
    st.markdown(
        f"""
        <div class="q-card">
            <div class="q-meta">問題ID：{q["id"]}</div>
            <div class="q-text">{q["question"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- choices ----
    if not checked:
        labels = [f"{i+1}. {c}" for i, c in enumerate(q["choices"])]
        default_idx = None
        if saved_answer is not None and 0 <= saved_answer < len(labels):
            default_idx = saved_answer

        picked = st.radio(
            "選択肢",
            labels,
            index=default_idx,
            label_visibility="collapsed",
            key=f"radio_{idx}",
        )
        if picked:
            st.session_state.quiz_answers[idx] = labels.index(picked)

        if st.button(
            "✅ チェック（判定する）",
            use_container_width=True,
            type="primary",
        ):
            if st.session_state.quiz_answers[idx] is None:
                st.warning("選択肢を選んでください。")
            else:
                st.session_state.quiz_checked[idx] = True
                st.rerun()
    else:
        sel = saved_answer
        is_correct = sel == q["correct_index"]

        if is_correct:
            st.success("✅ 正解！")
        else:
            st.error("❌ 不正解")

        for i, c in enumerate(q["choices"]):
            label = f"{i+1}. {c}"
            if i == q["correct_index"] and i == sel:
                st.success(f"{label}（正解 ✅）")
            elif i == q["correct_index"]:
                st.success(f"{label}（正解）")
            elif i == sel:
                st.error(f"{label}（あなたの解答）")
            else:
                st.write(label)

        if q.get("explanation"):
            st.markdown("**💡 解説**")
            st.info(q["explanation"])
        if not is_correct and q.get("why_wrong"):
            st.markdown("**📖 詳しい解説**")
            st.warning(q["why_wrong"])

    # ---- navigation ----
    st.markdown("")
    c1, c2, c3 = st.columns(3)
    with c1:
        if idx > 0:
            if st.button("◀ 戻る", use_container_width=True):
                st.session_state.quiz_index = idx - 1
                st.rerun()
        else:
            if st.button("◀ 表紙へ", use_container_width=True):
                st.session_state.page = "cover"
                st.rerun()
    with c2:
        st.write("")
    with c3:
        if checked:
            is_last = idx >= total - 1
            btn_label = "📊 結果を見る" if is_last else "次へ ▶"
            if st.button(
                btn_label, use_container_width=True, type="primary"
            ):
                if is_last:
                    finalize_quiz()
                else:
                    st.session_state.quiz_index = idx + 1
                    st.rerun()


def finalize_quiz() -> None:
    quiz = st.session_state.quiz_questions
    answers = st.session_state.quiz_answers
    details: List[Dict[str, Any]] = []
    correct_count = 0

    for i, q in enumerate(quiz):
        sel = answers[i]
        is_correct = sel == q["correct_index"]
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

        st.session_state.total_answered += 1
        if is_correct:
            st.session_state.total_correct += 1

        details.append({
            "id": q["id"],
            "field": q["field"],
            "question": q["question"],
            "choices": q["choices"],
            "correct_index": q["correct_index"],
            "selected_index": sel,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
            "why_wrong": q.get("why_wrong", ""),
        })

    total = len(quiz)
    rate = (correct_count / total * 100) if total else 0

    session_record = {
        "nickname": st.session_state.nickname,
        "field": st.session_state.sel_field,
        "difficulty": st.session_state.sel_difficulty,
        "count": total,
        "correct": correct_count,
        "rate": rate,
        "ts": datetime.now().strftime("%m/%d %H:%M"),
        "details": details,
    }

    st.session_state.sessions.append(session_record)

    nick = st.session_state.nickname.strip()
    if nick:
        if nick not in st.session_state.user_sessions:
            st.session_state.user_sessions[nick] = []
        st.session_state.user_sessions[nick].append(session_record)

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

    rank_label, bg, fg, msg = get_rank(rate)
    if rate == 100:
        st.balloons()
    elif rate >= 80:
        st.snow()

    nick_line = (
        f"<div style='font-size:.9rem; margin-bottom:.3rem;'>👤 {nick}</div>"
        if nick
        else ""
    )

    st.markdown(
        f"""
        <div class="rank-card" style="background:{bg}; color:{fg};">
            {nick_line}
            <div class="rank-icon">{rank_label.split(' ')[0]}</div>
            <div class="rank-label">{rank_label}</div>
            <div class="rank-rate">{rate:.0f}%（{correct}/{total}問正解）</div>
            <div class="rank-msg">{msg}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    wrong = total - correct
    st.markdown(
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
        """,
        unsafe_allow_html=True,
    )

    diff_flames = DIFFICULTY_FLAMES.get(session["difficulty"], "")
    diff_label = session["difficulty"].capitalize()
    field_label = session["field"]
    st.caption(f"分野：{field_label}　｜　難易度：{diff_flames} {diff_label}")

    # ---- detail ----
    st.markdown(
        '<div class="section-title">■ 全問題の結果</div>',
        unsafe_allow_html=True,
    )

    for i, d in enumerate(details, 1):
        icon = "✅" if d["is_correct"] else "❌"
        short_q = d["question"][:50] + (
            "…" if len(d["question"]) > 50 else ""
        )
        title = f"{icon} Q{i}. {short_q}"

        with st.expander(title):
            st.markdown(f"**問題：** {d['question']}")
            st.markdown("")
            for ci, c in enumerate(d["choices"]):
                label = f"{ci+1}. {c}"
                if ci == d["correct_index"] and ci == d["selected_index"]:
                    st.success(f"{label}（正解 ✅ あなたの解答）")
                elif ci == d["correct_index"]:
                    st.success(f"{label}（正解）")
                elif ci == d["selected_index"]:
                    st.error(f"{label}（あなたの解答）")
                else:
                    st.write(label)

            if d.get("explanation"):
                st.info(f"💡 {d['explanation']}")
            if not d["is_correct"] and d.get("why_wrong"):
                st.warning(f"📖 {d['why_wrong']}")

    # ---- buttons ----
    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "🏠 表紙に戻る", use_container_width=True, type="primary"
        ):
            st.session_state.page = "cover"
            st.rerun()
    with c2:
        if st.button("🗑 履歴をクリア", use_container_width=True):
            reset_all()


# =========================================================
# Page: History
# =========================================================
def render_history() -> None:
    st.markdown(
        '<div class="section-title">📊 学習履歴</div>',
        unsafe_allow_html=True,
    )

    nick = st.session_state.nickname.strip()
    if nick:
        st.markdown(
            f"""
            <div class="nick-card">
                <div class="nick-label">👤 ニックネーム</div>
                <div class="nick-name">{nick}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    total = st.session_state.total_answered
    correct = st.session_state.total_correct
    rate = (correct / total * 100) if total else 0

    st.markdown(
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
        """,
        unsafe_allow_html=True,
    )

    # ---- field bars ----
    st.markdown(
        '<div class="section-title">■ 分野別正答率</div>',
        unsafe_allow_html=True,
    )
    has_data = False
    for field in FIELD_ORDER:
        if field == "00. 全選択ランダム":
            continue
        fs = st.session_state.field_stats.get(field)
        if not fs or fs["answered"] == 0:
            continue
        has_data = True
        f_rate = fs["correct"] / fs["answered"] * 100
        emoji = FIELD_EMOJI.get(field, "📚")
        color = (
            "#059669"
            if f_rate >= 60
            else "#dc2626"
            if f_rate < 40
            else "#d97706"
        )
        st.markdown(
            f"""
            <div class="bar-row">
                <div class="bar-label">{emoji} {field}</div>
                <div class="bar-track">
                    <div class="bar-fill" style="width:{f_rate}%; background:{color};"></div>
                </div>
                <div class="bar-pct">{f_rate:.0f}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not has_data:
        st.info("まだ学習データがありません。")

    # ---- session list ----
    sessions = st.session_state.user_sessions.get(nick, []) if nick else []
    if sessions:
        st.markdown(
            '<div class="section-title">■ セッション履歴</div>',
            unsafe_allow_html=True,
        )
        for s in reversed(sessions[-20:]):
            icon = "🟢" if s["rate"] >= 60 else "🔴"
            diff_flames = DIFFICULTY_FLAMES.get(s["difficulty"], "")
            s_nick = s.get("nickname", "")
            nick_part = f"👤{s_nick}　" if s_nick else ""
            st.markdown(
                f"""
                <div class="card">
                    {icon} {s["ts"]}　{nick_part}{s["field"]}　
                    {diff_flames} {s["difficulty"].capitalize()}　
                    {s["correct"]}/{s["count"]}問　
                    <strong>{s["rate"]:.0f}%</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ---- buttons ----
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
    st.markdown(
        '<div class="section-title">🧠 AI 苦手分野分析</div>',
        unsafe_allow_html=True,
    )

    weak = analyze_weak_fields()

    if not weak:
        st.info(
            "まだ十分な学習データがありません。いくつかの分野を学習してから確認しましょう。"
        )
        if st.button("🏠 表紙へ", use_container_width=True):
            st.session_state.page = "cover"
            st.rerun()
        return

    st.markdown(
        """
        <div class="card">
            <div style="font-weight:800; color:#dc2626; margin-bottom:.5rem;">
                ⚠️ あなたの苦手分野
            </div>
        """,
        unsafe_allow_html=True,
    )

    for i, w in enumerate(weak[:3], 1):
        emoji = FIELD_EMOJI.get(w["field"], "📚")
        color = (
            "#dc2626"
            if w["rate"] < 40
            else "#d97706"
            if w["rate"] < 60
            else "#059669"
        )
        st.markdown(
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
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # ---- advice ----
    st.markdown(
        '<div class="section-title">💬 AIからのアドバイス</div>',
        unsafe_allow_html=True,
    )
    advice = generate_advice(weak)
    st.markdown(advice)

    st.markdown("")
    if weak:
        worst_field = weak[0]["field"]
        if st.button(
            f"🔥 「{worst_field}」を今すぐ学習",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.sel_field = worst_field
            st.session_state.sel_difficulty = "easy"
            quiz = build_quiz(
                questions, worst_field, "easy", st.session_state.sel_count
            )
            if not quiz:
                quiz = build_quiz(
                    questions, worst_field, "normal", st.session_state.sel_count
                )
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
        st.error(
            "問題データを読み込めませんでした。data フォルダを確認してください。"
        )
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