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

# ★ FIELD_MAP が変わるたびに自動でキャッシュ破棄するためのハッシュ
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
#  データ読込
#  ★ field_map_hash を引数に追加 → FIELD_MAP 変更時にキャッシュ自動破棄
# ────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_exam_questions(
    data_dir: Path,
    field_map_hash: str,          # ← キャッシュキー用（直接は使わない）
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

            if "correct_index" not in q and "answer_index" in q:
                q["correct_index"] = q["answer_index"]

            q["mode"]      = "exam"
            q["field"]     = FIELD_MAP.get(stem, stem)  # 表示名
            q["field_key"] = stem                        # フィルタ用キー

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

    # 表示名（"01. ..."）の番号順にソート
    sorted_items = sorted(FIELD_MAP.items(), key=lambda x: x[1])
    field_keys   = [k for k, _ in sorted_items]
    field_labels = [f"{ALL_FIELDS_LABEL}（{len(questions)}問）"]
    for key in field_keys:
        name = FIELD_MAP[key]
        cnt  = key_counts[key]
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

        max_options = [n for n in [10, 20, 50, 100] if n <= len(pool)] or [len(pool)]
        n_questions = st.selectbox("📝 出題数", max_options)

        st.divider()

        start_disabled = len(pool) == 0
        if start_disabled:
            st.warning("この分野の問題データがありません")

        if st.button("▶ 開始", use_container_width=True, disabled=start_disabled):
            ids = [q["id"] for q in pool]
            if shuffle:
                random.shuffle(ids)
            st.session_state.quiz_ids = ids[:n_questions]
            st.session_state.pos      = 0
            st.session_state.correct  = 0
            st.session_state.answered = False
            st.session_state.last_choice = None
            st.rerun()

        st.divider()
        with st.expander("🔍 読込ログ"):
            for line in logs:
                st.caption(line)


# ────────────────────────────────────────────────
#  クイズ本体
# ────────────────────────────────────────────────
def render_quiz(questions: List[Dict[str, Any]]) -> None:
    if not st.session_state.quiz_ids:
        st.info("← 左のサイドバーで分野を選択して開始してください")
        return

    q_map = {q["id"]: q for q in questions}
    total = len(st.session_state.quiz_ids)
    pos   = st.session_state.pos

    # 終了画面
    if pos >= total:
        correct = st.session_state.correct
        st.success(
            f"## 🎉 終了！　正答 **{correct} / {total}**　"
            f"({correct / total * 100:.1f}%)"
        )
        if st.button("🔄 もう一度"):
            st.session_state.quiz_ids = []
            st.rerun()
        return

    # 問題画面
    current_id = st.session_state.quiz_ids[pos]
    q = q_map[current_id]

    st.progress(pos / total, text=f"問題 {pos + 1} / {total}")

    # ★ 現在の分野を表示（確認用）
    st.caption(f"📂 分野：{q.get('field', '')}")

    st.write(f"### 問題 {pos + 1}")
    st.write(q["question"])

    labels = [f"{i + 1}. {c}" for i, c in enumerate(q["choices"])]

    if not st.session_state.answered:
        # 「2つ選べ」判定（問題文に "2つ選べ" が含まれるか）
        qtext = q["question"]
        is_multi = bool(re.search(r"2\s*つ\s*選", qtext))

        if not is_multi:
            # 1つ選べ（従来通り）
            choice = st.radio(
                "選択肢",
                labels,
                key=f"radio_{current_id}",
                label_visibility="collapsed",
            )

            if st.button("✅ 解答する"):
                selected_index = int(choice.split(".")[0]) - 1
                st.session_state.last_choice = selected_index
                st.session_state.answered    = True
                if selected_index == q["correct_index"]:
                    st.session_state.correct += 1
                st.rerun()

        else:
            # 2つ選べ（最大2つまで選択）
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
                st.session_state.answered    = True

                # ★ 暫定採点：
                # データが correct_index（単一）仕様のままなので、
                # 選んだ2つの中に correct_index が含まれていれば正解扱い
                if q["correct_index"] in selected_indices:
                    st.session_state.correct += 1
                st.rerun()

    else:
        correct_idx = q["correct_index"]
        chosen      = st.session_state.last_choice

        # chosen が int（1つ選べ） or list（2つ選べ）どちらでも動くようにする
        if isinstance(chosen, list):
            is_correct = correct_idx in chosen
        else:
            is_correct = (chosen == correct_idx)

        if is_correct:
            st.success("⭕ 正解！")
        else:
            st.error(
                f"❌ 不正解　（正答: **{correct_idx + 1}. {q['choices'][correct_idx]}**）"
            )

        if q.get("explanation"):
            with st.expander("📖 解説を見る"):
                st.write(q["explanation"])

        if st.button("次の問題 →"):
            st.session_state.pos      += 1
            st.session_state.answered  = False
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

    # ★ FIELD_MAP ハッシュを渡すことで変更時にキャッシュ自動破棄
    questions, logs = load_exam_questions(DATA_DIR, _FIELD_MAP_HASH)

    render_sidebar(questions, logs)
    render_quiz(questions)


if __name__ == "__main__":
    main()