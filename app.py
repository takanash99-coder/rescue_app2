import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
from collections import Counter

import streamlit as st

APP_TITLE = "レスキューアプリ - 国試モード"
DATA_DIR = Path(__file__).parent / "data"

FIELD_MAP = {
    "exam_01": "09. 生命倫理と社会保障",
    "exam_02": "01. 人体の構造と機能",
    "exam_03": "02. 疾患の成り立ちと薬理学",
    "exam_04": "06. 医療体制と法規",
    "exam_05": "05. 観察と重症度判断",
    "exam_06": "03. 内因性救急",
    "exam_07": "07. 症候別アプローチ",
    "exam_08": "04. 外傷救急",
    "exam_09": "08. 特殊病態",
    "exam_10": "10. 総合模試",
}

# ★ FIELD_MAP が変わるたびにキャッシュ破棄するためのハッシュ
_FIELD_MAP_HASH = str(sorted(FIELD_MAP.items()))

ALL_FIELDS_LABEL = "📚 全分野"


# ────────────────────────────────────────────────
#  バリデーション
# ────────────────────────────────────────────────
def _is_valid_question(q: Dict[str, Any]) -> Tuple[bool, str]:
    required = {"id", "question", "choices", "correct_index", "field"}
    missing = [k for k in required if k not in q]
    if missing:
        return False, f"キー不足: {missing}"
    if not isinstance(q["choices"], list) or len(q["choices"]) != 5:
        return False, "choicesが5つではない"
    if not isinstance(q["correct_index"], int) or not (0 <= q["correct_index"] <= 4):
        return False, "correct_indexが0〜4ではない"
    return True, ""


# ────────────────────────────────────────────────
#  データ読込（FIELD_MAP 変更時にキャッシュ自動破棄）
# ────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_exam_questions(
    data_dir: Path,
    field_map_hash: str,  # キャッシュキー用（直接は使わない）
) -> Tuple[List[Dict[str, Any]], List[str]]:
    questions: List[Dict[str, Any]] = []
    logs: List[str] = []
    seen_ids: set[str] = set()

    files = sorted(data_dir.glob("exam_*.json"))
    if not files:
        logs.append("[NG] exam_*.json が見つかりません")
        return questions, logs

    for fp in files:
        try:
            obj = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            logs.append(f"[SKIP] {fp.name}: JSON読込失敗")
            continue

        if "questions" not in obj:
            continue

        stem = fp.stem  # 例: "exam_01"

        for q in obj["questions"]:
            if not isinstance(q, dict):
                continue

            # 旧仕様(answer_index)→新仕様(correct_index)
            if "correct_index" not in q and "answer_index" in q:
                q["correct_index"] = q["answer_index"]

            q["mode"] = "exam"
            q["field"] = FIELD_MAP.get(stem, stem)   # 表示名
            q["field_key"] = stem                    # フィルタ用キー

            q.setdefault("difficulty", "")
            q.setdefault("explanation", "")
            q.setdefault("why_wrong", "")

            valid, _ = _is_valid_question(q)
            if not valid or q["id"] in seen_ids:
                continue

            seen_ids.add(q["id"])
            questions.append(q)

    logs.append(f"[OK] 有効問題数: {len(questions)}")

    key_counts = Counter(q["field_key"] for q in questions)
    for key, cnt in sorted(key_counts.items()):
        label = FIELD_MAP.get(key, key)
        logs.append(f"  {key} → {label}：{cnt}問")

    return questions, logs


# ────────────────────────────────────────────────
#  セッション初期化
# ────────────────────────────────────────────────
def init_state() -> None:
    ss = st.session_state
    ss.setdefault("quiz_ids", [])
    ss.setdefault("pos", 0)
    ss.setdefault("correct", 0)
    ss.setdefault("answered", False)
    ss.setdefault("last_choice", None)
    ss.setdefault("history", [])  # 復習用：解答履歴


def reset_quiz_state() -> None:
    ss = st.session_state
    ss.quiz_ids = []
    ss.pos = 0
    ss.correct = 0
    ss.answered = False
    ss.last_choice = None
    ss.history = []


# ────────────────────────────────────────────────
#  解答履歴の保存（復習用）
# ────────────────────────────────────────────────
def push_history(q: Dict[str, Any], user_choice: Any) -> None:
    """
    user_choice:
      - 1つ選べ: int
      - 2つ選べ: List[int]
    """
    correct_idx = q.get("correct_index")
    if isinstance(user_choice, list):
        is_correct = correct_idx in user_choice
    else:
        is_correct = (user_choice == correct_idx)

    st.session_state.history.append(
        {
            "id": q.get("id", ""),
            "field": q.get("field", ""),
            "question": q.get("question", ""),
            "choices": q.get("choices", []),
            "correct_index": correct_idx,
            "user_choice": user_choice,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
            "why_wrong": q.get("why_wrong", ""),
        }
    )


# ────────────────────────────────────────────────
#  サイドバー
# ────────────────────────────────────────────────
def render_sidebar(questions: List[Dict[str, Any]], logs: List[str]) -> None:
    # field_key ベースで問題数を集計
    key_counts: Dict[str, int] = {k: 0 for k in FIELD_MAP}
    for q in questions:
        fk = q.get("field_key", "")
        if fk in key_counts:
            key_counts[fk] += 1

    # 表示名の番号順にソート
    sorted_items = sorted(FIELD_MAP.items(), key=lambda x: x[1])
    field_keys = [k for k, _ in sorted_items]
    field_labels = [f"{ALL_FIELDS_LABEL}（{len(questions)}問）"]
    for key in field_keys:
        name = FIELD_MAP[key]
        cnt = key_counts[key]
        field_labels.append(f"{name}（{cnt}問）")

    with st.sidebar:
        st.header("⚙️ 国試モード設定")
        st.divider()

        shuffle = st.toggle("🔀 ランダム（全分野）", value=False)

        if shuffle:
            pool = questions
            st.info(f"全分野 {len(pool)}問 からランダムに出題")
        else:
            selected_idx: int = st.selectbox(
                "📂 分野を選択",
                options=list(range(len(field_labels))),
                format_func=lambda i: field_labels[i],
                key="field_select_idx",
            )

            if selected_idx == 0:
                pool = questions
            else:
                target_key = field_keys[selected_idx - 1]
                pool = [q for q in questions if q.get("field_key") == target_key]

            st.caption(f"対象: **{len(pool)}問**")

        st.divider()

        max_options = [n for n in [10, 20, 50, 100] if n <= len(pool)] or ([len(pool)] if len(pool) > 0 else [0])
        n_questions = st.selectbox("📝 出題数", max_options)

        st.divider()

        start_disabled = (len(pool) == 0) or (n_questions == 0)
        if start_disabled:
            st.warning("この分野の問題データがありません")

        if st.button("▶ 開始", use_container_width=True, disabled=start_disabled):
            ids = [q["id"] for q in pool]
            if shuffle:
                random.shuffle(ids)
            st.session_state.quiz_ids = ids[:n_questions]
            st.session_state.pos = 0
            st.session_state.correct = 0
            st.session_state.answered = False
            st.session_state.last_choice = None
            st.session_state.history = []
            st.rerun()

        st.divider()
        with st.expander("🔍 読込ログ"):
            for line in logs:
                st.caption(line)


# ────────────────────────────────────────────────
#  終了後の復習画面（おすすめ版：番号＋内容も表示）
# ────────────────────────────────────────────────
def render_review_screen() -> None:
    history: List[Dict[str, Any]] = st.session_state.get("history", [])
    total = len(history)
    correct = sum(1 for h in history if h.get("is_correct"))
    wrong = total - correct

    if total == 0:
        st.warning("結果がありません（履歴が空です）。左のサイドバーから開始してください。")
        if st.button("⚙️ 設定へ戻る"):
            reset_quiz_state()
            st.rerun()
        return

    st.success(
        f"## 🎉 終了！　正答 **{correct} / {total}**　"
        f"({(correct / total * 100):.1f}%)"
    )

    col1, col2, col3 = st.columns([1.2, 1.2, 2])
    with col1:
        if st.button("🔁 同じ問題でもう一度", use_container_width=True):
            st.session_state.pos = 0
            st.session_state.correct = 0
            st.session_state.answered = False
            st.session_state.last_choice = None
            st.session_state.history = []
            st.rerun()

    with col2:
        if st.button("⚙️ 分野選択からやり直す", use_container_width=True):
            reset_quiz_state()
            st.rerun()

    with col3:
        st.info(f"復習：全{total}問（❌{wrong} / ✅{correct}）")

    st.divider()
    st.subheader("📖 復習（全問一覧）")

    show_only_wrong = st.toggle("❌ 間違えた問題だけ表示", value=True)
    items = [h for h in history if (not show_only_wrong or not h.get("is_correct"))]

    if not items:
        st.success("間違えた問題はありません。強い。")
        return

    # 分野ごとにまとめる
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for h in items:
        grouped.setdefault(h.get("field", "（分野なし）"), []).append(h)

    for field_name, arr in grouped.items():
        st.markdown(f"### 📂 {field_name}（{len(arr)}問）")

        for h in arr:
            mark = "✅" if h.get("is_correct") else "❌"
            qid = h.get("id", "")
            title = f"{mark} {qid}"

            with st.expander(title, expanded=not h.get("is_correct")):
                question_text = h.get("question", "")
                st.write(question_text)

                choices: List[str] = h.get("choices", [])
                correct_idx = h.get("correct_index", None)
                user_choice = h.get("user_choice", None)

                # ── サマリー（番号表示） ──────────────────
                correct_no = (correct_idx + 1) if isinstance(correct_idx, int) else "-"
                if isinstance(user_choice, list):
                    chosen_no = ", ".join(str(i + 1) for i in user_choice) if user_choice else "-"
                elif isinstance(user_choice, int):
                    chosen_no = str(user_choice + 1)
                else:
                    chosen_no = "-"

                st.markdown(f"**正解：{correct_no}**　｜　**あなたの選択：{chosen_no}**")

                # ── サマリー（内容表示） ──────────────────
                correct_text = ""
                if isinstance(correct_idx, int) and 0 <= correct_idx < len(choices):
                    correct_text = choices[correct_idx]

                chosen_texts: List[str] = []
                if isinstance(user_choice, list):
                    chosen_texts = [choices[i] for i in user_choice if 0 <= i < len(choices)]
                elif isinstance(user_choice, int) and 0 <= user_choice < len(choices):
                    chosen_texts = [choices[user_choice]]

                if correct_text:
                    st.caption(f"正解の内容：{correct_text}")
                if chosen_texts:
                    st.caption(f"あなたの選択内容：{' / '.join(chosen_texts)}")

                st.divider()

                # ── 選択肢（タグ表示） ──────────────────
                for c_idx, choice_text in enumerate(choices):
                    tags: List[str] = []

                    if isinstance(user_choice, list) and c_idx in user_choice:
                        tags.append("あなたの選択")
                    if isinstance(user_choice, int) and c_idx == user_choice:
                        tags.append("あなたの選択")
                    if isinstance(correct_idx, int) and c_idx == correct_idx:
                        tags.append("正解")

                    tag_text = f"（{' / '.join(tags)}）" if tags else ""
                    st.write(f"{c_idx + 1}. {choice_text} {tag_text}")

                if h.get("explanation"):
                    with st.expander("📖 解説", expanded=False):
                        st.write(h["explanation"])

                if (not h.get("is_correct")) and h.get("why_wrong"):
                    with st.expander("🧠 補足（なぜ他が違うか）", expanded=False):
                        st.write(h["why_wrong"])


# ────────────────────────────────────────────────
#  クイズ本体
# ────────────────────────────────────────────────
def render_quiz(questions: List[Dict[str, Any]]) -> None:
    if not st.session_state.quiz_ids:
        st.info("← 左のサイドバーで分野を選択して開始してください")
        return

    q_map = {q["id"]: q for q in questions}
    total = len(st.session_state.quiz_ids)
    pos = st.session_state.pos

    # 終了画面
    if pos >= total:
        render_review_screen()
        return

    # 問題画面
    current_id = st.session_state.quiz_ids[pos]
    q = q_map[current_id]

    st.progress(pos / total, text=f"問題 {pos + 1} / {total}")
    st.caption(f"📂 分野：{q.get('field', '')}")

    st.write(f"### 問題 {pos + 1}")
    st.write(q["question"])

    labels = [f"{i + 1}. {c}" for i, c in enumerate(q["choices"])]

    if not st.session_state.answered:
        # 「2つ選べ」判定
        qtext = q["question"]
        is_multi = bool(re.search(r"2\s*つ\s*選", qtext))

        if not is_multi:
            choice = st.radio(
                "選択肢",
                labels,
                key=f"radio_{current_id}",
                label_visibility="collapsed",
            )

            if st.button("✅ 解答する"):
                selected_index = int(choice.split(".")[0]) - 1

                st.session_state.last_choice = selected_index
                st.session_state.answered = True

                if selected_index == q["correct_index"]:
                    st.session_state.correct += 1

                push_history(q, selected_index)
                st.rerun()

        else:
            selected = st.multiselect(
                "選択肢（2つ選べ）",
                labels,
                default=[],
                max_selections=2,
                key=f"multi_{current_id}",
            )

            if st.button("✅ 解答する"):
                selected_indices = [int(s.split(".")[0]) - 1 for s in selected]

                st.session_state.last_choice = selected_indices
                st.session_state.answered = True

                # ★暫定採点：correct_index（単一）が含まれていれば正解扱い
                if q["correct_index"] in selected_indices:
                    st.session_state.correct += 1

                push_history(q, selected_indices)
                st.rerun()

    else:
        correct_idx = q["correct_index"]
        chosen = st.session_state.last_choice

        if isinstance(chosen, list):
            is_correct = correct_idx in chosen
        else:
            is_correct = (chosen == correct_idx)

        if is_correct:
            st.success("⭕ 正解！")
        else:
            st.error(f"❌ 不正解　（正答: **{correct_idx + 1}. {q['choices'][correct_idx]}**）")

        if q.get("explanation"):
            with st.expander("📖 解説を見る"):
                st.write(q["explanation"])

        if st.button("次の問題 →"):
            st.session_state.pos += 1
            st.session_state.answered = False
            st.session_state.last_choice = None
            st.rerun()


# ────────────────────────────────────────────────
#  エントリポイント
# ────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🚑",
        layout="wide",
    )
    st.title(f"🚑 {APP_TITLE}")

    init_state()

    questions, logs = load_exam_questions(DATA_DIR, _FIELD_MAP_HASH)

    render_sidebar(questions, logs)
    render_quiz(questions)


if __name__ == "__main__":
    main()