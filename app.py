from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st


# =========================================================
# 基本設定
# =========================================================
st.set_page_config(
    page_title="救命士国家試験アプリ",
    page_icon="🚑",
    layout="wide",
)

DATA_DIR = Path(__file__).parent / "data"
STATS_FILE = Path(__file__).parent / "user_stats.json"


# =========================================================
# 分野定義（表示順 = join順）
# 先頭に「全選択ランダム」を追加
# =========================================================
CATEGORY_DEFS = [
    {"key": "all_random", "label": "00. 全選択ランダム", "short": "全選択ランダム", "icon": "🎲"},
    {"key": "ethics", "label": "01. 生命倫理と社会保障", "short": "生命倫理と社会保障", "icon": "🤝"},
    {"key": "anatomy", "label": "02. 人体の構造と機能", "short": "人体の構造と機能", "icon": "📁"},
    {"key": "pathology", "label": "03. 疾患の成り立ちと薬理学", "short": "疾患の成り立ちと薬理学", "icon": "💊"},
    {"key": "law", "label": "04. 医療体制と法規", "short": "医療体制と法規", "icon": "⚖️"},
    {"key": "assessment", "label": "05. 観察と重症度判断", "short": "観察と重症度判断", "icon": "🔍"},
    {"key": "endogenous", "label": "06. 内因性救急", "short": "内因性救急", "icon": "🩺"},
    {"key": "symptom", "label": "07. 症候別アプローチ", "short": "症候別アプローチ", "icon": "🚨"},
    {"key": "trauma", "label": "08. 外傷救急", "short": "外傷救急", "icon": "🩹"},
    {"key": "special", "label": "09. 特殊病態", "short": "特殊病態", "icon": "☣️"},
    {"key": "mock", "label": "10. 総合模試", "short": "総合模試", "icon": "🎯"},
]


# =========================================================
# カテゴリと exam 番号の対応
# =========================================================
CATEGORY_TO_PREFIX = {
    "ethics": "exam01",
    "anatomy": "exam02",
    "pathology": "exam03",
    "law": "exam04",
    "assessment": "exam05",
    "endogenous": "exam06",
    "symptom": "exam07",
    "trauma": "exam08",
    "special": "exam09",
    "mock": "exam10",
}


# =========================================================
# 共通関数
# =========================================================
def normalize_text(text: str) -> str:
    return str(text).replace("　", "").replace(" ", "").lower()


@st.cache_data(show_spinner=False)
def load_questions(data_dir: Path) -> List[Dict[str, Any]]:
    """dataフォルダ内のexam_*.jsonを読み込む"""
    questions: List[Dict[str, Any]] = []

    if not data_dir.exists():
        return questions

    json_files = sorted(data_dir.glob("exam_*.json"))
    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for q in data.get("questions", []):
                if (
                    isinstance(q, dict)
                    and "id" in q
                    and "question" in q
                    and "choices" in q
                    and "correct_index" in q
                ):
                    item = dict(q)
                    item["_source_file"] = file_path.name
                    questions.append(item)
        except Exception:
            continue

    return questions


def get_stats() -> Dict[str, Any]:
    if not STATS_FILE.exists():
        return {}

    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_stats(stats: Dict[str, Any]) -> None:
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def update_user_stats(nickname: str, correct_count: int, total_count: int) -> None:
    stats = get_stats()

    if nickname not in stats:
        stats[nickname] = {
            "total_correct": 0,
            "total_answered": 0,
            "sessions": 0,
        }

    stats[nickname]["total_correct"] += correct_count
    stats[nickname]["total_answered"] += total_count
    stats[nickname]["sessions"] += 1

    save_stats(stats)


def get_user_stats(nickname: str) -> Dict[str, int]:
    stats = get_stats()
    return stats.get(
        nickname,
        {"total_correct": 0, "total_answered": 0, "sessions": 0},
    )


def get_sorted_score_rows() -> List[Dict[str, Any]]:
    stats = get_stats()
    rows: List[Dict[str, Any]] = []

    for nickname, s in stats.items():
        total_correct = s.get("total_correct", 0)
        total_answered = s.get("total_answered", 0)
        sessions = s.get("sessions", 0)
        rate = (total_correct / total_answered * 100) if total_answered > 0 else 0.0

        rows.append(
            {
                "nickname": nickname,
                "total_correct": total_correct,
                "total_answered": total_answered,
                "rate": rate,
                "sessions": sessions,
            }
        )

    rows.sort(key=lambda x: (-x["rate"], -x["total_answered"], x["nickname"]))
    return rows


def get_category_info(category_key: str) -> Dict[str, str]:
    for cat in CATEGORY_DEFS:
        if cat["key"] == category_key:
            return cat
    return {"key": "", "label": "", "short": "", "icon": ""}


def match_category(question: Dict[str, Any], category_key: str) -> bool:
    if category_key == "all_random":
        return True

    qid = normalize_text(question.get("id", ""))
    prefix = normalize_text(CATEGORY_TO_PREFIX.get(category_key, ""))

    if not prefix:
        return False

    return qid.startswith(prefix)


def filter_questions_by_category(
    all_questions: List[Dict[str, Any]],
    category_key: str,
) -> List[Dict[str, Any]]:
    return [q for q in all_questions if match_category(q, category_key)]


def init_session_state() -> None:
    defaults = {
        "page": "home",
        "nickname": "",
        "nickname_input": "",
        "selected_category": "",
        "question_count": 10,
        "quiz_questions": [],
        "current_index": 0,
        "current_correct": 0,
        "answer_checked": False,
        "selected_choice": None,
        "review_list": [],
        "result_saved": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if not st.session_state.nickname_input and st.session_state.nickname:
        st.session_state.nickname_input = st.session_state.nickname


def sync_nickname_from_input() -> None:
    st.session_state.nickname = st.session_state.nickname_input.strip()


def reset_quiz_state() -> None:
    st.session_state.quiz_questions = []
    st.session_state.current_index = 0
    st.session_state.current_correct = 0
    st.session_state.answer_checked = False
    st.session_state.selected_choice = None
    st.session_state.review_list = []
    st.session_state.result_saved = False
    # nickname は保持する


def start_quiz(all_questions: List[Dict[str, Any]]) -> tuple[bool, str]:
    sync_nickname_from_input()

    nickname = st.session_state.nickname.strip()
    category_key = st.session_state.selected_category
    question_count = st.session_state.question_count

    if not nickname:
        return False, "ニックネームを入力してね。"

    if not category_key:
        return False, "分野カードを選んでね。"

    filtered = filter_questions_by_category(all_questions, category_key)

    if not filtered:
        return False, "この分野の問題が見つからないよ。JSONの id を確認してね。"

    actual_count = min(question_count, len(filtered))
    selected_questions = random.sample(filtered, actual_count)

    st.session_state.quiz_questions = selected_questions
    st.session_state.current_index = 0
    st.session_state.current_correct = 0
    st.session_state.answer_checked = False
    st.session_state.selected_choice = None
    st.session_state.review_list = []
    st.session_state.result_saved = False
    st.session_state.page = "quiz"
    return True, ""


def inject_css() -> None:
    st.markdown(
        """
        <style>
        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Hiragino Sans",
                         "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at top, #e8f3ff 0%, #f7fbff 45%, #f4f7fb 100%);
        }

        .block-container {
            max-width: 540px;
            padding-top: 1.2rem;
            padding-bottom: 4rem;
        }

        .phone-shell {
            background: rgba(255,255,255,0.82);
            border: 1px solid rgba(255,255,255,0.7);
            border-radius: 28px;
            padding: 18px 16px 24px 16px;
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.10);
            backdrop-filter: blur(6px);
        }

        .app-title {
            font-size: 1.8rem;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: 0.15rem;
            text-align: center;
        }

        .app-subtitle {
            font-size: 0.95rem;
            color: #64748b;
            margin-bottom: 1rem;
            text-align: center;
        }

        .section-label {
            font-size: 0.92rem;
            font-weight: 700;
            color: #334155;
            margin-top: 0.9rem;
            margin-bottom: 0.4rem;
        }

        .soft-card {
            background: #ffffff;
            border-radius: 20px;
            padding: 14px 14px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
            margin-bottom: 0.8rem;
        }

        .quiz-card {
            background: #ffffff;
            border-radius: 22px;
            padding: 18px 16px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
            margin-top: 0.75rem;
            margin-bottom: 0.75rem;
        }

        .question-chip {
            display: inline-block;
            background: #e0f2fe;
            color: #0369a1;
            font-size: 0.82rem;
            font-weight: 700;
            border-radius: 999px;
            padding: 6px 10px;
            margin-bottom: 0.7rem;
        }

        .selected-pill {
            display: inline-block;
            background: #dbeafe;
            color: #1d4ed8;
            border-radius: 999px;
            padding: 7px 12px;
            font-size: 0.88rem;
            font-weight: 700;
        }

        .result-box {
            background: #ffffff;
            border-radius: 20px;
            padding: 16px 10px;
            text-align: center;
            border: 1px solid #e2e8f0;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
        }

        .result-label {
            color: #64748b;
            font-size: 0.85rem;
            margin-bottom: 0.25rem;
        }

        .result-value {
            color: #0f172a;
            font-size: 1.65rem;
            font-weight: 800;
            line-height: 1.1;
        }

        .review-box {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 18px;
            padding: 14px;
            margin-bottom: 12px;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
        }

        .score-row {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 12px 14px;
            margin-bottom: 10px;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.04);
        }

        .debug-box {
            background: #f8fafc;
            border: 1px dashed #cbd5e1;
            border-radius: 14px;
            padding: 10px 12px;
            font-size: 0.85rem;
            color: #475569;
            margin-top: 10px;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stSelectbox"] > div {
            border-radius: 14px !important;
        }

        div[data-testid="stButton"] > button {
            width: 100%;
            border-radius: 18px !important;
            border: 1px solid #dbeafe !important;
            background: white !important;
            color: #0f172a !important;
            font-weight: 700 !important;
            padding-top: 0.95rem !important;
            padding-bottom: 0.95rem !important;
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.08) !important;
        }

        div[data-testid="stButton"] > button:hover {
            border-color: #60a5fa !important;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.14) !important;
            transform: translateY(-1px);
        }

        div[data-testid="stRadio"] label {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 8px 10px;
            margin-bottom: 0.4rem;
        }

        .center-note {
            color: #64748b;
            font-size: 0.88rem;
            text-align: center;
            margin-top: 0.2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 画面描画
# =========================================================
def render_home(all_questions: List[Dict[str, Any]]) -> None:
    inject_css()
    st.markdown('<div class="phone-shell">', unsafe_allow_html=True)

    st.markdown('<div class="app-title">🚑 救命士国家試験アプリ</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="app-subtitle">ホーム → 問題 → 結果 → 成績表 のスマホ風UI</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">ニックネーム</div>', unsafe_allow_html=True)
    st.text_input(
        "ニックネーム",
        key="nickname_input",
        label_visibility="collapsed",
        placeholder="例：としくん",
        on_change=sync_nickname_from_input,
    )

    st.markdown('<div class="section-label">出題数</div>', unsafe_allow_html=True)
    st.selectbox(
        "出題数",
        options=[5, 10, 20, 30, 50],
        key="question_count",
        label_visibility="collapsed",
    )

    st.markdown(
        f'<div class="center-note">読み込み済み問題数：{len(all_questions)}問</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-label">分野を選択</div>', unsafe_allow_html=True)

    selected = get_category_info(st.session_state.selected_category)
    if selected.get("short"):
        st.markdown(
            f'<div style="margin-bottom:0.75rem;"><span class="selected-pill">選択中：{selected["icon"]} {selected["short"]}</span></div>',
            unsafe_allow_html=True,
        )

    for i in range(0, len(CATEGORY_DEFS), 2):
        cols = st.columns(2)
        chunk = CATEGORY_DEFS[i:i + 2]

        for col, cat in zip(cols, chunk):
            with col:
                label = f'{cat["icon"]}\n{cat["label"]}'
                if st.session_state.selected_category == cat["key"]:
                    label += "\n✅"

                if st.button(label, key=f'cat_{cat["key"]}', use_container_width=True):
                    st.session_state.selected_category = cat["key"]
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        if st.button("▶ 問題スタート", use_container_width=True):
            ok, msg = start_quiz(all_questions)
            if ok:
                st.rerun()
            else:
                st.warning(msg)

    with c2:
        if st.button("📊 成績表を見る", use_container_width=True):
            sync_nickname_from_input()
            st.session_state.page = "score"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_quiz() -> None:
    inject_css()
    questions = st.session_state.quiz_questions
    idx = st.session_state.current_index
    total = len(questions)
    current_q = questions[idx]

    category = get_category_info(st.session_state.selected_category)
    progress = (idx + 1) / total if total > 0 else 0

    st.markdown('<div class="phone-shell">', unsafe_allow_html=True)

    top1, top2 = st.columns([3, 1])
    with top1:
        st.markdown('<div class="app-title">📝 問題</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="app-subtitle">{category.get("icon", "")} {category.get("short", "")}</div>',
            unsafe_allow_html=True,
        )
    with top2:
        if st.button("🏠", key="home_from_quiz"):
            st.session_state.page = "home"
            reset_quiz_state()
            st.rerun()

    st.progress(progress)
    st.markdown(
        f'<div class="center-note">{idx + 1} / {total} 問</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="quiz-card">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="question-chip">Q{idx + 1}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"### {current_q.get('question', '')}")

    choices = current_q.get("choices", [])
    radio_index = st.session_state.selected_choice if st.session_state.selected_choice is not None else 0

    if choices:
        selected_choice = st.radio(
            "選択肢",
            options=list(range(len(choices))),
            format_func=lambda x: f"{x + 1}. {choices[x]}",
            index=radio_index,
            key=f"radio_{idx}",
            label_visibility="collapsed",
        )
    else:
        selected_choice = None
        st.error("この問題に選択肢がないよ。JSONを確認してね。")

    st.markdown(
        f"""
        <div class="debug-box">
        <b>問題ID</b>：{current_q.get("id", "")}<br>
        <b>field</b>：{current_q.get("field", "")}<br>
        <b>source</b>：{current_q.get("_source_file", "")}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    if not st.session_state.answer_checked:
        if st.button("✅ 解答する", use_container_width=True):
            if selected_choice is None:
                st.warning("選択肢が読み込めていないため解答できないよ。")
            else:
                st.session_state.selected_choice = selected_choice
                st.session_state.answer_checked = True

                correct_index = current_q.get("correct_index", -1)
                if selected_choice == correct_index:
                    st.session_state.current_correct += 1
                else:
                    st.session_state.review_list.append(
                        {
                            "question": current_q.get("question", ""),
                            "choices": choices,
                            "your_answer": selected_choice,
                            "correct_answer": correct_index,
                            "explanation": current_q.get("explanation", ""),
                            "why_wrong": current_q.get("why_wrong", ""),
                            "field": current_q.get("field", ""),
                            "id": current_q.get("id", ""),
                            "source": current_q.get("_source_file", ""),
                        }
                    )
                st.rerun()

    if st.session_state.answer_checked:
        correct_index = current_q.get("correct_index", -1)
        is_correct = st.session_state.selected_choice == correct_index

        if is_correct:
            st.success("正解！ いいぞ。")
        else:
            correct_text = choices[correct_index] if 0 <= correct_index < len(choices) else ""
            st.error(f"不正解。正解は {correct_index + 1}. {correct_text}")

        explanation = current_q.get("explanation", "")
        why_wrong = current_q.get("why_wrong", "")

        if explanation:
            st.info(f"解説：{explanation}")
        if why_wrong:
            st.warning(f"補足：{why_wrong}")

        if st.button("➡ 次へ", use_container_width=True):
            if idx + 1 < total:
                st.session_state.current_index += 1
                st.session_state.answer_checked = False
                st.session_state.selected_choice = None
            else:
                st.session_state.page = "result"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_result() -> None:
    inject_css()
    total = len(st.session_state.quiz_questions)
    correct = st.session_state.current_correct
    wrong = total - correct
    rate = (correct / total * 100) if total > 0 else 0.0
    nickname = st.session_state.nickname.strip()

    if not st.session_state.result_saved and nickname:
        update_user_stats(nickname, correct, total)
        st.session_state.result_saved = True

    user_stats = get_user_stats(nickname)
    total_correct = user_stats.get("total_correct", 0)
    total_answered = user_stats.get("total_answered", 0)
    sessions = user_stats.get("sessions", 0)
    total_rate = (total_correct / total_answered * 100) if total_answered > 0 else 0.0

    st.markdown('<div class="phone-shell">', unsafe_allow_html=True)
    st.markdown('<div class="app-title">🏁 結果</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="app-subtitle">{nickname} さんの成績</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">今回の成績</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"""
            <div class="result-box">
                <div class="result-label">正解数</div>
                <div class="result-value">{correct}/{total}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="result-box">
                <div class="result-label">正答率</div>
                <div class="result-value">{rate:.1f}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="result-box">
                <div class="result-label">不正解</div>
                <div class="result-value">{wrong}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="section-label">累計成績</div>', unsafe_allow_html=True)
    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown(
            f"""
            <div class="result-box">
                <div class="result-label">累計正解</div>
                <div class="result-value">{total_correct}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown(
            f"""
            <div class="result-box">
                <div class="result-label">累計解答</div>
                <div class="result-value">{total_answered}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c6:
        st.markdown(
            f"""
            <div class="result-box">
                <div class="result-label">累計正答率 / 回数</div>
                <div class="result-value">{total_rate:.1f}%</div>
                <div class="center-note">挑戦 {sessions} 回</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🔁 もう一度", use_container_width=True):
            all_questions = load_questions(DATA_DIR)
            ok, msg = start_quiz(all_questions)
            if ok:
                st.rerun()
            else:
                st.warning(msg)

    with c2:
        if st.button("📊 成績表", use_container_width=True):
            st.session_state.page = "score"
            st.rerun()

    with c3:
        if st.button("🏠 ホーム", use_container_width=True):
            st.session_state.page = "home"
            reset_quiz_state()
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">復習</div>', unsafe_allow_html=True)

    if not st.session_state.review_list:
        st.success("全問正解！ きれいに抜けたね。")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    for i, item in enumerate(st.session_state.review_list, start=1):
        choices = item.get("choices", [])
        your_idx = item.get("your_answer", -1)
        correct_idx = item.get("correct_answer", -1)

        your_text = choices[your_idx] if 0 <= your_idx < len(choices) else "未選択"
        correct_text = choices[correct_idx] if 0 <= correct_idx < len(choices) else ""

        st.markdown('<div class="review-box">', unsafe_allow_html=True)
        st.markdown(f"**復習 {i}**")
        st.markdown(f"**問題**：{item.get('question', '')}")
        st.markdown(f"**ID**：{item.get('id', '')}")
        st.markdown(f"**source**：{item.get('source', '')}")
        if item.get("field"):
            st.caption(f"分野情報：{item.get('field')}")
        st.markdown(f"**あなたの解答**：{your_text}")
        st.markdown(f"**正解**：{correct_text}")
        if item.get("explanation"):
            st.markdown(f"**解説**：{item.get('explanation', '')}")
        if item.get("why_wrong"):
            st.markdown(f"**補足**：{item.get('why_wrong', '')}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_score() -> None:
    inject_css()
    rows = get_sorted_score_rows()
    current_name = st.session_state.nickname.strip()

    st.markdown('<div class="phone-shell">', unsafe_allow_html=True)
    st.markdown('<div class="app-title">📊 成績表</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="app-subtitle">保存されている累計成績の一覧</div>',
        unsafe_allow_html=True,
    )

    if not rows:
        st.info("まだ成績データがないよ。まずは問題を解いてみよう。")
    else:
        for rank, row in enumerate(rows, start=1):
            mark = " 👈 あなた" if current_name and row["nickname"] == current_name else ""
            st.markdown(
                f"""
                <div class="score-row">
                    <b>{rank}位　{row["nickname"]}{mark}</b><br>
                    累計正解：{row["total_correct"]}　
                    累計解答：{row["total_answered"]}　
                    正答率：{row["rate"]:.1f}%　
                    挑戦回数：{row["sessions"]}
                </div>
                """,
                unsafe_allow_html=True,
            )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🏠 ホームへ戻る", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()
    with c2:
        if st.button("📝 問題へ戻る", use_container_width=True):
            if st.session_state.quiz_questions:
                st.session_state.page = "quiz"
            else:
                st.session_state.page = "home"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# メイン
# =========================================================
def main() -> None:
    init_session_state()
    all_questions = load_questions(DATA_DIR)

    if not all_questions:
        st.error("問題データが見つからないよ。dataフォルダに exam_*.json があるか確認してね。")
        st.stop()

    if st.session_state.page == "home":
        render_home(all_questions)
    elif st.session_state.page == "quiz":
        if not st.session_state.quiz_questions:
            st.session_state.page = "home"
            st.rerun()
        render_quiz()
    elif st.session_state.page == "result":
        render_result()
    elif st.session_state.page == "score":
        render_score()
    else:
        st.session_state.page = "home"
        st.rerun()


if __name__ == "__main__":
    main()