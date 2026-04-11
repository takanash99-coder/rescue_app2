import json
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="症例シミュレーター", layout="wide")

# =========================
# パス設定
# =========================
BASE_DIR = Path(__file__).resolve().parent
CASES_DIR = BASE_DIR / "cases"

# =========================
# 表示用ラベル
# =========================
FLAG_LABELS = {
    "cardiac_arrest": "心停止状態",
    "possible_acs": "急性冠症候群の可能性",
    "possible_forearm_fracture": "前腕骨折の可能性",
    "possible_head_trauma": "頭部外傷の可能性",
    "vf_rhythm": "心室細動波形",
    "bathroom_locked": "浴室ドアが施錠されている",
    "possible_suicide_attempt": "自傷・自殺企図の可能性",
    "possible_toxic_gas": "有毒ガス曝露の可能性",
    "scene_not_safe": "現場安全が確保されていない",
    "single_ambulance_unit": "出場隊数が限られている",
}

DANGER_LABELS = {
    "delay_defibrillation": "除細動の遅れに注意",
    "inadequate_cpr": "胸骨圧迫の質不足に注意",
    "missed_stemi": "STEMI見逃しに注意",
    "missed_trauma": "外傷評価の見落としに注意",
    "post_rosc_instability": "ROSC後の再増悪に注意",
    "delayed_rescue_support": "応援要請の遅れに注意",
    "scene_assessment_error": "現場評価ミスに注意",
    "secondary_disaster": "二次災害に注意",
    "toxic_exposure": "有害物質曝露に注意",
    "unsafe_entry": "安全未確認での進入に注意",
}

# =========================
# 共通関数
# =========================
def safe_get(d, key, default=None):
    if isinstance(d, dict):
        return d.get(key, default)
    return default


def load_case_files():
    if not CASES_DIR.exists():
        return []

    json_files = []
    for p in CASES_DIR.rglob("*.json"):
        if "media" not in p.parts:
            json_files.append(p)

    return sorted(json_files)


def load_case_data(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_media_path(media_path: str):
    return BASE_DIR / "cases" / media_path


def init_case_state(case_data):
    st.session_state.sim_case_data = case_data
    st.session_state.sim_current_scene_index = 0
    st.session_state.sim_answers = {}
    st.session_state.sim_total_score = 0
    st.session_state.sim_ideal_score = 0
    st.session_state.sim_scene_answered = {}

    initial_state = safe_get(case_data, "initial_state", {})
    st.session_state.sim_life = safe_get(initial_state, "life", 100)
    st.session_state.sim_max_life = safe_get(initial_state, "max_life", 100)
    st.session_state.sim_flags = set(safe_get(initial_state, "flags", []))
    st.session_state.sim_danger_tags = set(safe_get(initial_state, "danger_tags", []))
    st.session_state.sim_triggered_events = set()
    st.session_state.sim_finished = False


def reset_simulator():
    keys = [
        "sim_case_data",
        "sim_current_scene_index",
        "sim_answers",
        "sim_total_score",
        "sim_ideal_score",
        "sim_scene_answered",
        "sim_life",
        "sim_max_life",
        "sim_flags",
        "sim_danger_tags",
        "sim_triggered_events",
        "sim_finished",
    ]
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]


def apply_status_effect(status_effect):
    if not status_effect:
        return

    for f in status_effect.get("add_flags", []):
        st.session_state.sim_flags.add(f)

    for f in status_effect.get("remove_flags", []):
        st.session_state.sim_flags.discard(f)

    for d in status_effect.get("add_danger_tags", []):
        st.session_state.sim_danger_tags.add(d)

    for d in status_effect.get("remove_danger_tags", []):
        st.session_state.sim_danger_tags.discard(d)


def apply_option_effect(option):
    st.session_state.sim_total_score += safe_get(option, "score_delta", 0)
    st.session_state.sim_ideal_score += safe_get(option, "ideal_score_delta", 0)

    st.session_state.sim_life += safe_get(option, "life_delta", 0)
    st.session_state.sim_life = max(0, min(st.session_state.sim_life, st.session_state.sim_max_life))

    apply_status_effect(safe_get(option, "status_effect", {}))


def get_scene_index_by_id(case_data, scene_id):
    scenes = safe_get(case_data, "scenes", [])
    for i, s in enumerate(scenes):
        if s.get("scene_id") == scene_id:
            return i
    return None


def evaluate_dynamic_events(scene):
    events = safe_get(scene, "dynamic_events", [])
    triggered = []

    current_flags = st.session_state.sim_flags

    for event in events:
        event_id = event.get("event_id")
        if not event_id or event_id in st.session_state.sim_triggered_events:
            continue

        trigger_flags = set(event.get("trigger_flags", []))
        if trigger_flags.issubset(current_flags):
            triggered.append(event)
            st.session_state.sim_triggered_events.add(event_id)

            effects = event.get("effects", {})
            st.session_state.sim_life += effects.get("life_delta", 0)
            st.session_state.sim_life = max(
                0, min(st.session_state.sim_life, st.session_state.sim_max_life)
            )

            apply_status_effect(effects.get("status_effect", {}))

    return triggered


def get_rank(case_data):
    result_rank = safe_get(case_data, "result_rank", {})
    excellent = safe_get(result_rank, "excellent", {})
    good = safe_get(result_rank, "good", {})
    normal = safe_get(result_rank, "normal", {})
    bad = safe_get(result_rank, "bad", {})

    score = st.session_state.sim_total_score
    life = st.session_state.sim_life

    if life <= 0:
        return "bad", bad

    ex_min = excellent.get("min_score", 9999)
    good_min = good.get("min_score", 9999)
    normal_min = normal.get("min_score", -9999)

    if score >= ex_min:
        return "excellent", excellent
    if score >= good_min:
        return "good", good
    if score >= normal_min:
        return "normal", normal
    return "bad", bad


def format_visible_value(value):
    if isinstance(value, list):
        return " / ".join(str(v) for v in value)
    if isinstance(value, dict):
        return " / ".join(f"{k}: {v}" for k, v in value.items())
    return str(value)


# =========================
# 表示関数
# =========================
def render_header(case_data):
    st.title("救急救命士 臨床推論トレーニング")

    title = safe_get(case_data, "title", "無題症例")
    category = safe_get(case_data, "category", "-")
    difficulty = safe_get(case_data, "difficulty", "-")
    algorithm_type = safe_get(case_data, "algorithm_type", "-")
    overview = safe_get(case_data, "overview", "")

    st.subheader(title)
    st.caption(f"カテゴリ: {category} / 難易度: {difficulty} / アルゴリズム: {algorithm_type}")

    if isinstance(overview, str) and overview.strip():
        st.write(overview)
    elif isinstance(overview, dict):
        learning_objectives = overview.get("learning_objectives", [])
        target_level = overview.get("target_level", "")
        estimated_time = overview.get("estimated_time_min", "")
        keywords = overview.get("keywords", [])

        with st.expander("症例概要", expanded=False):
            if learning_objectives:
                st.markdown("**学習目標**")
                for item in learning_objectives:
                    st.write(f"・{item}")

            if target_level:
                st.write(f"**対象**: {target_level}")

            if estimated_time != "":
                st.write(f"**想定時間**: {estimated_time}分")

            if keywords:
                st.write(f"**キーワード**: {', '.join(keywords)}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("スコア", st.session_state.sim_total_score)
    with col2:
        st.metric("理想スコア", st.session_state.sim_ideal_score)
    with col3:
        st.metric("Life", f"{st.session_state.sim_life}/{st.session_state.sim_max_life}")

    with st.expander("状態と注意点", expanded=False):
        flags = sorted(list(st.session_state.sim_flags))
        danger_tags = sorted(list(st.session_state.sim_danger_tags))

        st.markdown("**この症例で意識すること**")
        st.write("表示される内容は、傷病者の状態や現場で注意すべき点の整理です。")
        st.write("行動の優先順位を考えるヒントとして使ってください。")

        if flags:
            st.markdown("**現在の状態**")
            for f in flags:
                label = FLAG_LABELS.get(f, f)
                st.write(f"・{label}")
        else:
            st.write("現在の状態情報はありません。")

        if danger_tags:
            st.markdown("**注意点**")
            for d in danger_tags:
                label = DANGER_LABELS.get(d, d)
                st.write(f"・{label}")
        else:
            st.write("特記すべき注意点はありません。")


def render_visible_data(scene):
    visible_data = safe_get(scene, "visible_data", {})
    if not visible_data:
        return

    st.markdown("### 観察情報")
    for key, value in visible_data.items():
        st.write(f"**{key}**: {format_visible_value(value)}")


def render_media(scene):
    media_list = safe_get(scene, "media", [])
    if not media_list:
        return

    st.markdown("### 画像・図")
    for media in media_list:
        path_str = media.get("path")
        caption = media.get("caption", "")
        if not path_str:
            continue

        media_path = resolve_media_path(path_str)
        if media_path.exists():
            try:
                st.image(str(media_path), caption=caption, use_container_width=True)
            except Exception:
                st.warning(f"画像表示に失敗: {path_str}")
        else:
            st.info(f"画像ファイル未配置: {path_str}")


def render_question(scene, q_index, question):
    q_type = question.get("type", "single_choice")
    prompt = question.get("prompt", "")
    options = question.get("options", [])
    q_key = f"{scene['scene_id']}_q{q_index}"

    st.markdown(f"### 問題 {q_index + 1}")
    st.write(prompt)

    if q_type == "single_choice":
        labels = [f"{opt.get('option_id', '')}: {opt.get('text', '')}" for opt in options]
        selected_label = st.radio(
            "選択してください",
            labels,
            key=f"radio_{q_key}",
            index=None,
        )

        if st.button("この回答を確定", key=f"submit_{q_key}"):
            if not selected_label:
                st.warning("選択してください。")
                return

            selected_idx = labels.index(selected_label)
            selected_option = options[selected_idx]

            st.session_state.sim_answers[q_key] = {
                "question": prompt,
                "selected_option_id": selected_option.get("option_id"),
                "selected_text": selected_option.get("text"),
                "rationale": selected_option.get("rationale", ""),
            }
            st.session_state.sim_scene_answered[scene["scene_id"]] = True

            apply_option_effect(selected_option)

            rationale = selected_option.get("rationale")
            if rationale:
                st.info(f"解説: {rationale}")

            next_scene_id = selected_option.get("next_scene_id")
            if next_scene_id:
                next_idx = get_scene_index_by_id(st.session_state.sim_case_data, next_scene_id)
                if next_idx is not None:
                    st.session_state.sim_current_scene_index = next_idx
                    st.rerun()

            st.rerun()

    elif q_type == "multiple_choice":
        labels = [f"{opt.get('option_id', '')}: {opt.get('text', '')}" for opt in options]
        selected_labels = st.multiselect(
            "該当するものを選択してください",
            labels,
            key=f"multi_{q_key}",
        )

        if st.button("この回答を確定", key=f"submit_{q_key}"):
            if not selected_labels:
                st.warning("選択してください。")
                return

            selected_options = [options[labels.index(lbl)] for lbl in selected_labels]

            st.session_state.sim_answers[q_key] = {
                "question": prompt,
                "selected_option_ids": [o.get("option_id") for o in selected_options],
                "selected_texts": [o.get("text") for o in selected_options],
            }
            st.session_state.sim_scene_answered[scene["scene_id"]] = True

            for opt in selected_options:
                apply_option_effect(opt)

            st.rerun()

    elif q_type == "ranking":
        st.info("ranking は現在の最小版では未対応です。")

    elif q_type == "template_select":
        labels = [f"{opt.get('option_id', '')}: {opt.get('text', '')}" for opt in options]
        selected_label = st.selectbox(
            "テンプレートを選択してください",
            [""] + labels,
            key=f"template_{q_key}",
        )

        if st.button("この回答を確定", key=f"submit_{q_key}"):
            if not selected_label:
                st.warning("選択してください。")
                return

            selected_idx = labels.index(selected_label)
            selected_option = options[selected_idx]

            st.session_state.sim_answers[q_key] = {
                "question": prompt,
                "selected_option_id": selected_option.get("option_id"),
                "selected_text": selected_option.get("text"),
            }
            st.session_state.sim_scene_answered[scene["scene_id"]] = True

            apply_option_effect(selected_option)
            st.rerun()


def render_scene(case_data):
    scenes = safe_get(case_data, "scenes", [])
    current_idx = st.session_state.sim_current_scene_index

    if current_idx >= len(scenes):
        st.session_state.sim_finished = True
        st.rerun()
        return

    scene = scenes[current_idx]

    st.markdown("---")
    st.header(f"{scene.get('phase', 'scene')}：{scene.get('scene_goal', '')}")

    narrative = scene.get("narrative", "")
    if narrative:
        st.write(narrative)

    render_visible_data(scene)
    render_media(scene)

    triggered = evaluate_dynamic_events(scene)
    if triggered:
        st.markdown("### 状況変化")
        for ev in triggered:
            st.warning(ev.get("narrative", "状況変化あり"))
            vdu = ev.get("visible_data_update", {})
            if vdu:
                for k, v in vdu.items():
                    st.write(f"**{k}**: {format_visible_value(v)}")

    questions = safe_get(scene, "questions", [])
    if not questions:
        st.info("この場面には設問がありません。")
        if st.button("次の場面へ", key=f"next_scene_{scene.get('scene_id')}"):
            st.session_state.sim_current_scene_index += 1
            st.rerun()
        return

    for i, q in enumerate(questions):
        render_question(scene, i, q)

    scene_answered = st.session_state.sim_scene_answered.get(scene.get("scene_id"), False)

    if scene_answered:
        st.button("この場面は回答済みです", disabled=True, key=f"answered_{scene.get('scene_id')}")
        if st.button("次の場面へ", key=f"go_next_after_{scene.get('scene_id')}"):
            st.session_state.sim_current_scene_index += 1
            st.rerun()


def render_debriefing(case_data):
    st.success("症例終了")
    st.markdown("---")
    st.header("Debriefing")

    rank_key, rank_data = get_rank(case_data)

    rank_label_map = {
        "excellent": "Excellent",
        "good": "Good",
        "normal": "Normal",
        "bad": "Bad",
    }
    st.subheader(f"最終評価: {rank_label_map.get(rank_key, rank_key)}")

    if rank_data:
        message = rank_data.get("message", "")
        if message:
            st.write(message)

    st.write(f"**総合スコア**: {st.session_state.sim_total_score}")
    st.write(f"**理想スコア**: {st.session_state.sim_ideal_score}")
    st.write(f"**Life**: {st.session_state.sim_life}/{st.session_state.sim_max_life}")

    debriefing = safe_get(case_data, "debriefing", {})

    if debriefing.get("summary"):
        st.markdown("### 総括")
        st.write(debriefing["summary"])

    if debriefing.get("ideal_actions"):
        st.markdown("### 理想行動")
        for x in debriefing["ideal_actions"]:
            st.write(f"・{x}")

    if debriefing.get("good_points"):
        st.markdown("### 良かった点")
        for x in debriefing["good_points"]:
            st.write(f"・{x}")

    if debriefing.get("common_pitfalls"):
        st.markdown("### よくある落とし穴")
        for x in debriefing["common_pitfalls"]:
            st.write(f"・{x}")

    if debriefing.get("scoring_message"):
        st.markdown("### スコアコメント")
        for k, v in debriefing["scoring_message"].items():
            st.write(f"**{k}**: {v}")

    with st.expander("回答履歴"):
        for k, v in st.session_state.sim_answers.items():
            st.write(f"**{k}**")
            st.write(v)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("最初に戻る"):
            reset_simulator()
            st.rerun()
    with col2:
        if st.button("同じ症例を再開"):
            case_data = st.session_state.sim_case_data
            init_case_state(case_data)
            st.rerun()


def render_case_selector():
    st.title("救急救命士 臨床推論トレーニング")
    st.write("訓練したい症例を選んで開始します。")

    case_files = load_case_files()

    if not case_files:
        st.error("症例データが見つかりません。")
        st.code(
            "rescue_app/\n"
            "├─ app.py\n"
            "├─ app_simulator.py\n"
            "└─ cases/\n"
            "   ├─ neuro/\n"
            "   ├─ trauma/\n"
            "   └─ media/\n"
        )
        return

    case_options = []
    for p in case_files:
        try:
            case_data = load_case_data(p)
            title = case_data.get("title", p.stem)
            category = case_data.get("category", "")
            difficulty = case_data.get("difficulty", "")
            display_name = f"{title}"
            if category or difficulty:
                display_name += f" 〔{category} / {difficulty}〕"
            case_options.append((display_name, p))
        except Exception:
            case_options.append((p.stem, p))

    display_labels = [x[0] for x in case_options]
    selected_label = st.selectbox("訓練する症例", display_labels)

    if st.button("開始"):
        selected_path = dict(case_options)[selected_label]
        case_data = load_case_data(selected_path)
        init_case_state(case_data)
        st.rerun()


# =========================
# メイン
# =========================
def main():
    if "sim_case_data" not in st.session_state:
        render_case_selector()
        return

    case_data = st.session_state.sim_case_data
    render_header(case_data)

    if st.session_state.sim_finished:
        render_debriefing(case_data)
    else:
        render_scene(case_data)


if __name__ == "__main__":
    main()