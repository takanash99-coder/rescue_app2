import json
import random
from copy import deepcopy
from pathlib import Path

import streamlit as st

# =========================================================
# app_simulator_full.py
# 救急救命士向け 臨床推論シミュレーションアプリ（完全版）
# ---------------------------------------------------------
# - 既存の app.py / app_simulator.py はそのまま残す
# - 本ファイルを rescue_app 直下に保存して実行
# - 例: python -m streamlit run app_simulator_full.py
# =========================================================

st.set_page_config(
    page_title="臨床推論シミュレーション",
    page_icon="🚑",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
CASES_DIR = BASE_DIR / "cases"
MEDIA_DIR = CASES_DIR / "media"
LEGACY_MEDIA_DIR = BASE_DIR / "media"

CATEGORY_LABELS = {
    "neuro": "脳神経系",
    "cardiovascular": "循環器系",
    "respiratory": "呼吸器系",
    "gastrointestinal": "消化器系",
    "urinary": "泌尿器系",
    "endocrine_metabolic": "内分泌・代謝系",
    "reproductive_obstetric": "生殖器・産科",
    "orthopedic": "整形系",
    "special_population": "小児・妊婦・高齢者",
    "trauma": "外傷",
    "toxicology": "中毒",
    "environmental_special": "環境障害・特殊疾患",
    "psychiatric": "精神",
    "media": "画像素材",
}

STATE_FLAG_LABELS = {
    "airway_risk": "気道リスク",
    "breathing_risk": "呼吸リスク",
    "circulation_risk": "循環リスク",
    "shock": "ショック疑い",
    "c_spine_precaution": "頸椎保護",
    "sepsis_risk": "敗血症リスク",
    "stroke_risk": "脳卒中疑い",
    "acs_risk": "ACS疑い",
    "arrhythmia_risk": "不整脈リスク",
    "trauma_risk": "外傷重症化リスク",
    "infection_control": "感染対策必要",
    "agitation": "興奮・不穏",
    "suicide_risk": "自傷リスク",
    "transport_priority": "搬送優先",
    "time_critical": "時間依存性高い",
    "special_procedure_candidate": "特定行為検討",
    "first_call_needed": "ファーストコール必要",
    "observe_repeatedly": "繰り返し観察",
}


# ---------------------------------------------------------
# 初期化
# ---------------------------------------------------------
def init_session_state():
    defaults = {
        "page": "cover",                  # cover / case_select / scene / debrief
        "case_index": None,
        "case_data": None,
        "scene_index": 0,
        "answers": {},                    # {scene_index: answer_payload}
        "score_total": 0,
        "max_score_total": 0,
        "case_files_cache": None,
        "random_seed": random.randint(1, 999999),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ---------------------------------------------------------
# CSS
# ---------------------------------------------------------
def inject_css():
    st.markdown(
        """
        <style>
        :root{
            --navy:#15304f;
            --blue:#2563eb;
            --green:#10b981;
            --orange:#f59e0b;
            --red:#ef4444;
            --bg:#f3f6fb;
            --card:#ffffff;
            --text:#1f2937;
            --muted:#64748b;
            --border:#dbe4f0;
        }

        .stApp{
            background: linear-gradient(180deg, #f7f9fc 0%, #eef4fb 100%);
            color: var(--text);
        }

        .main .block-container{
            padding-top: 1.6rem;
            padding-bottom: 2rem;
            max-width: 1100px;
        }

        .hero-box{
            background: linear-gradient(135deg, #15304f 0%, #1d4e89 100%);
            color: white;
            border-radius: 24px;
            padding: 28px 28px 24px 28px;
            box-shadow: 0 12px 30px rgba(21,48,79,0.20);
            margin-bottom: 18px;
        }

        .hero-title{
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 0.35rem;
        }

        .hero-sub{
            font-size: 1rem;
            opacity: 0.95;
            line-height: 1.7;
        }

        .guide-card{
            background: white;
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 18px 18px 14px 18px;
            box-shadow: 0 6px 20px rgba(15,23,42,0.05);
            margin-bottom: 14px;
        }

        .guide-title{
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--navy);
            margin-bottom: 0.35rem;
        }

        .meta-pill{
            display:inline-block;
            padding: 4px 10px;
            border-radius:999px;
            background:#e8f0fb;
            color:#1d4e89;
            font-size:0.82rem;
            font-weight:700;
            margin-right:6px;
            margin-bottom:6px;
        }

        .case-card{
            background: white;
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 16px 16px 12px 16px;
            box-shadow: 0 8px 24px rgba(15,23,42,0.06);
            margin-bottom: 12px;
        }

        .case-title{
            font-size: 1.08rem;
            font-weight: 800;
            color: var(--navy);
            line-height: 1.5;
            margin-bottom: 8px;
        }

        .case-desc{
            color: var(--muted);
            font-size: 0.93rem;
            line-height: 1.65;
            margin-bottom: 12px;
        }

        .scene-shell{
            background: white;
            border: 1px solid var(--border);
            border-radius: 22px;
            box-shadow: 0 10px 26px rgba(15,23,42,0.06);
            padding: 22px 20px 18px 20px;
            margin-top: 10px;
            margin-bottom: 14px;
        }

        .scene-topline{
            display:flex;
            justify-content:space-between;
            gap:16px;
            align-items:center;
            flex-wrap:wrap;
            margin-bottom: 10px;
        }

        .scene-badge{
            display:inline-block;
            background:#e8f0fb;
            color:#1d4e89;
            border-radius:999px;
            padding: 6px 12px;
            font-weight:700;
            font-size:0.88rem;
        }

        .scene-title{
            font-size: 1.5rem;
            font-weight: 800;
            color: var(--navy);
            margin: 0.35rem 0 0.7rem 0;
        }

        .scene-text{
            font-size: 1rem;
            line-height: 1.9;
            color: var(--text);
            margin-bottom: 12px;
        }

        .question-card{
            background:#f8fbff;
            border:1px solid #d7e6fb;
            border-radius:16px;
            padding:14px 14px 10px 14px;
            margin-top:12px;
            margin-bottom:12px;
        }

        .section-title{
            font-size: 1.02rem;
            font-weight: 800;
            color: var(--navy);
            margin-top: 1rem;
            margin-bottom: .45rem;
        }

        .info-card{
            background:#f8fbff;
            border:1px solid #d7e6fb;
            border-radius:16px;
            padding:14px 14px 10px 14px;
            margin-bottom:12px;
        }

        .warn-card{
            background:#fff8ef;
            border:1px solid #fde0af;
            border-radius:16px;
            padding:14px 14px 10px 14px;
            margin-bottom:12px;
        }

        .good-card{
            background:#effcf7;
            border:1px solid #b8f1da;
            border-radius:16px;
            padding:14px 14px 10px 14px;
            margin-bottom:12px;
        }

        .danger-card{
            background:#fff3f2;
            border:1px solid #fecaca;
            border-radius:16px;
            padding:14px 14px 10px 14px;
            margin-bottom:12px;
        }

        .small-label{
            font-size:0.8rem;
            color:var(--muted);
            margin-bottom:4px;
            font-weight:700;
        }

        .big-value{
            font-size:1.05rem;
            font-weight:800;
            color:var(--navy);
        }

        .answer-status-ok{
            color:#047857;
            font-weight:800;
        }

        .answer-status-ng{
            color:#b45309;
            font-weight:800;
        }

        .debrief-head{
            border-radius:22px;
            padding:24px;
            box-shadow: 0 12px 30px rgba(21,48,79,0.20);
            margin-bottom:16px;
            color:white;
        }

        .debrief-score{
            font-size:2rem;
            font-weight:900;
            margin-top:6px;
            margin-bottom:8px;
        }

        .rank-badge{
            display:inline-block;
            padding:6px 12px;
            border-radius:999px;
            background:rgba(255,255,255,0.14);
            border:1px solid rgba(255,255,255,0.25);
            font-weight:700;
        }

        .debrief-s{
            background: linear-gradient(135deg, #7c3aed 0%, #2563eb 100%);
            color: white;
        }

        .debrief-a{
            background: linear-gradient(135deg, #059669 0%, #10b981 100%);
            color: white;
        }

        .debrief-b{
            background: linear-gradient(135deg, #2563eb 0%, #38bdf8 100%);
            color: white;
        }

        .debrief-c{
            background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%);
            color: white;
        }

        .debrief-d{
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
        }

        div.stButton > button{
            border-radius: 12px !important;
            font-weight: 700 !important;
            border: 1px solid #cdd8e8 !important;
            min-height: 42px !important;
        }

        div[data-testid="stHorizontalBlock"] div.stButton > button{
            width: 100%;
        }

        .muted{
            color: var(--muted);
        }

        .center-note{
            text-align:center;
            color:var(--muted);
            padding:10px 0 0 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
# 汎用ユーティリティ
# ---------------------------------------------------------
def safe_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return " / ".join(str(x) for x in value if x is not None)
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            if isinstance(v, list):
                v_txt = "、".join(str(x) for x in v)
            else:
                v_txt = str(v)
            lines.append(f"・{k}：{v_txt}")
        return "\n".join(lines)
    return str(value)


def normalize_overview(overview):
    if overview is None:
        return []
    if isinstance(overview, str):
        txt = overview.strip()
        return [txt] if txt else []
    if isinstance(overview, list):
        return [str(x) for x in overview if str(x).strip()]
    if isinstance(overview, dict):
        rows = []
        for k, v in overview.items():
            if isinstance(v, list):
                rows.append((str(k), "、".join(str(x) for x in v)))
            else:
                rows.append((str(k), str(v)))
        return rows
    return [str(overview)]


def state_flags_to_labels(flags):
    labels = []
    for flag in ensure_list(flags):
        if isinstance(flag, dict):
            for k, v in flag.items():
                key = str(k)
                if isinstance(v, bool):
                    if v:
                        labels.append(STATE_FLAG_LABELS.get(key, key))
                elif v not in [None, "", False]:
                    labels.append(f"{STATE_FLAG_LABELS.get(key, key)}：{v}")
        else:
            key = str(flag)
            labels.append(STATE_FLAG_LABELS.get(key, key))
    return labels


def normalize_difficulty(value):
    if not value:
        return "Normal"

    v = str(value).strip().lower()

    if v in ["easy", "beginner"]:
        return "Easy"
    if v in ["normal", "standard", "mid", "medium", "midium"]:
        return "Normal"
    if v in ["hard", "advanced", "expert"]:
        return "Hard"

    return "Normal"


def answer_key(scene_idx):
    return f"scene_answer_{scene_idx}"


def ranking_order_key(scene_idx):
    return f"scene_ranking_order_{scene_idx}"


def clear_scene_answer(scene_idx):
    if scene_idx in st.session_state.answers:
        del st.session_state.answers[scene_idx]
    recompute_scores()


# ---------------------------------------------------------
# 症例読込
# ---------------------------------------------------------
def get_case_files():
    if st.session_state.case_files_cache is not None:
        return st.session_state.case_files_cache

    case_files = []
    if not CASES_DIR.exists():
        st.session_state.case_files_cache = []
        return []

    for path in sorted(CASES_DIR.rglob("*.json")):
        if path.parent.name == "media":
            continue

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        rel_parent = path.parent.relative_to(CASES_DIR).as_posix()
        category = rel_parent.split("/")[0] if rel_parent else "uncategorized"

        title = (
            data.get("title")
            or data.get("case_title")
            or data.get("name")
            or path.stem.replace("_", " ")
        )

        difficulty = normalize_difficulty(data.get("difficulty") or data.get("level"))
        est_time = data.get("estimated_time") or data.get("time_required") or data.get("duration") or "約10〜15分"
        keywords = ensure_list(data.get("keywords") or data.get("tags"))
        scenes = data.get("scenes", [])
        scene_count = len(scenes) if isinstance(scenes, list) else 0

        summary = (
            data.get("summary")
            or data.get("description")
            or safe_get(data, "header", "overview")
            or ""
        )
        summary_text = normalize_text(summary)
        if len(summary_text) > 90:
            summary_text = summary_text[:90] + "..."

        case_files.append(
            {
                "path": path,
                "title": title,
                "category": category,
                "category_label": CATEGORY_LABELS.get(category, category),
                "difficulty": difficulty,
                "estimated_time": est_time,
                "keywords": keywords[:4],
                "summary": summary_text,
                "scene_count": scene_count,
                "raw": data,
            }
        )

    st.session_state.case_files_cache = case_files
    return case_files


def load_case_by_index(case_index):
    cases = get_case_files()
    if case_index is None or case_index < 0 or case_index >= len(cases):
        return None
    return deepcopy(cases[case_index]["raw"])


def get_current_case():
    data = st.session_state.case_data
    if data is not None:
        return data
    if st.session_state.case_index is not None:
        return load_case_by_index(st.session_state.case_index)
    return None


def get_scenes(case_data):
    scenes = case_data.get("scenes", [])
    return scenes if isinstance(scenes, list) else []


def get_scene(case_data, scene_index):
    scenes = get_scenes(case_data)
    if 0 <= scene_index < len(scenes):
        return scenes[scene_index]
    return None


def reset_case_progress():
    st.session_state.scene_index = 0
    st.session_state.answers = {}
    st.session_state.score_total = 0
    st.session_state.max_score_total = 0

    for k in list(st.session_state.keys()):
        if str(k).startswith("scene_ranking_order_"):
            del st.session_state[k]


def start_case(case_index):
    data = load_case_by_index(case_index)
    st.session_state.case_index = case_index
    st.session_state.case_data = data
    reset_case_progress()
    st.session_state.page = "scene"
    st.rerun()


def go_cover():
    st.session_state.page = "cover"
    st.rerun()


def go_case_select():
    st.session_state.page = "case_select"
    st.rerun()


# ---------------------------------------------------------
# scene 抽出
# ---------------------------------------------------------
def scene_title(scene, idx):
    return (
        scene.get("title")
        or scene.get("name")
        or scene.get("label")
        or f"場面 {idx + 1}"
    )


def scene_body_text(scene):
    return (
        scene.get("text")
        or scene.get("description")
        or scene.get("narrative")
        or ""
    )


def scene_prompt_text(scene):
    return (
        scene.get("prompt")
        or scene.get("instruction")
        or scene.get("guide")
        or scene.get("question")
        or scene.get("task")
        or "この場面で最も適切な判断・対応を選んでください。"
    )


def extract_scene_goal(scene):
    return normalize_text(scene.get("scene_goal") or scene.get("goal") or "")


def extract_ideal_flow(scene):
    val = scene.get("ideal_flow")
    if isinstance(val, list):
        return [str(x) for x in val]
    txt = normalize_text(val)
    return [txt] if txt else []


def extract_state_flags(case_data, scene):
    flags = []
    flags += ensure_list(case_data.get("state_flags"))
    flags += ensure_list(scene.get("state_flags"))
    flags += ensure_list(scene.get("flags"))
    return state_flags_to_labels(flags)


def detect_question_type(scene):
    qtype = scene.get("type") or scene.get("question_type") or scene.get("input_type")
    if qtype:
        return str(qtype).strip().lower()

    if scene.get("ranking") or scene.get("rank_items"):
        return "ranking"
    if scene.get("templates") or scene.get("template_options"):
        return "template_select"
    if scene.get("multiple_choice") or scene.get("multi_select"):
        return "multiple_choice"
    if scene.get("single_choice") or scene.get("choices") or scene.get("options") or scene.get("actions"):
        return "single_choice"

    return "single_choice"


def extract_media_list(scene):
    media = scene.get("media")
    if media is None:
        return []

    if isinstance(media, dict):
        media = [media]

    results = []
    for m in media:
        if isinstance(m, str):
            results.append({"path": m, "caption": "", "description": ""})
        elif isinstance(m, dict):
            path = m.get("path") or m.get("file") or m.get("src")
            if path:
                results.append(
                    {
                        "path": path,
                        "caption": m.get("caption") or m.get("title") or "",
                        "description": m.get("description") or "",
                    }
                )
    return results


def resolve_media_path(path_str):
    if not path_str:
        return None

    p = Path(path_str)
    if p.is_absolute():
        return p if p.exists() else None

    candidates = []

    candidates.append(BASE_DIR / p)

    if str(p).startswith("cases/"):
        candidates.append(BASE_DIR / p)

    if str(p).startswith("media/"):
        candidates.append(CASES_DIR / p)
        candidates.append(BASE_DIR / p)

    candidates.append(MEDIA_DIR / p.name)
    candidates.append(LEGACY_MEDIA_DIR / p.name)
    candidates.append(CASES_DIR / "media" / p.name)

    seen = set()
    unique_candidates = []
    for c in candidates:
        try:
            c_resolved = c.resolve()
        except Exception:
            c_resolved = c
        if str(c_resolved) not in seen:
            seen.add(str(c_resolved))
            unique_candidates.append(c)

    for c in unique_candidates:
        if c.exists():
            return c

    return None


def extract_options(scene):
    source = (
        scene.get("options")
        or scene.get("choices")
        or scene.get("actions")
        or scene.get("single_choice")
        or scene.get("multiple_choice")
        or scene.get("template_options")
        or scene.get("templates")
        or []
    )

    normalized = []

    if isinstance(source, dict):
        tmp = []
        for k, v in source.items():
            if isinstance(v, dict):
                item = deepcopy(v)
                item.setdefault("id", str(k))
                tmp.append(item)
            else:
                tmp.append({"id": str(k), "label": str(v)})
        source = tmp

    for i, item in enumerate(ensure_list(source)):
        if isinstance(item, str):
            normalized.append(
                {
                    "id": f"opt_{i}",
                    "label": item,
                    "score_delta": 0,
                    "action_tag": "",
                    "ideal": False,
                    "feedback": "",
                    "tone": "neutral",
                    "raw": {},
                }
            )
        elif isinstance(item, dict):
            label = (
                item.get("label")
                or item.get("text")
                or item.get("name")
                or item.get("title")
                or item.get("value")
                or f"選択肢{i+1}"
            )
            score_delta = item.get("score_delta")
            if score_delta is None:
                if item.get("ideal") is True or item.get("is_correct") is True:
                    score_delta = item.get("ideal_score_delta", 1)
                else:
                    score_delta = 0

            normalized.append(
                {
                    "id": item.get("id") or item.get("key") or f"opt_{i}",
                    "label": str(label),
                    "score_delta": score_delta,
                    "action_tag": item.get("action_tag") or "",
                    "ideal": bool(item.get("ideal") or item.get("is_correct") or False),
                    "feedback": item.get("feedback") or item.get("result") or item.get("comment") or "",
                    "tone": item.get("tone") or ("success" if score_delta > 0 else "neutral"),
                    "raw": item,
                }
            )

    return normalized


def extract_ranking_items(scene):
    source = scene.get("ranking") or scene.get("rank_items") or scene.get("items") or []
    items = []
    for i, item in enumerate(ensure_list(source)):
        if isinstance(item, str):
            items.append({"id": f"rank_{i}", "label": item, "ideal_rank": i + 1})
        elif isinstance(item, dict):
            items.append(
                {
                    "id": item.get("id") or f"rank_{i}",
                    "label": item.get("label") or item.get("text") or item.get("name") or f"項目{i+1}",
                    "ideal_rank": item.get("ideal_rank") or item.get("rank") or (i + 1),
                }
            )
    return items


def scene_has_interactive_input(scene):
    qtype = detect_question_type(scene)
    if qtype == "ranking":
        return len(extract_ranking_items(scene)) > 0
    if qtype in {"single_choice", "multiple_choice", "template_select"}:
        return len(extract_options(scene)) > 0
    return False


def scene_has_answer(scene_idx, scene=None):
    if scene_idx in st.session_state.answers:
        return True
    if scene is not None and not scene_has_interactive_input(scene):
        return True
    return False


def get_saved_answer(scene_idx):
    return st.session_state.answers.get(scene_idx)


# ---------------------------------------------------------
# 採点
# ---------------------------------------------------------
def recompute_scores():
    case_data = get_current_case()
    if not case_data:
        return 0, 0

    total = 0
    max_total = 0
    scenes = get_scenes(case_data)

    for idx, scene in enumerate(scenes):
        ideal_scene_score = scene.get("ideal_score_delta", 1)
        max_total += max(int(ideal_scene_score), 1)

        ans = st.session_state.answers.get(idx)
        if ans:
            total += int(ans.get("score", 0))

    st.session_state.score_total = total
    st.session_state.max_score_total = max_total
    return total, max_total


def calc_scene_answer_payload(scene, qtype, user_value):
    ideal_scene_score = int(scene.get("ideal_score_delta", 1))

    if qtype == "single_choice":
        options = extract_options(scene)
        selected = next((x for x in options if x["id"] == user_value), None)
        if selected is None:
            return None

        score = int(selected.get("score_delta", 0))
        if score == 0 and selected.get("ideal"):
            score = ideal_scene_score

        return {
            "type": qtype,
            "value": user_value,
            "labels": [selected["label"]],
            "score": score,
            "action_tags": [selected.get("action_tag", "")] if selected.get("action_tag") else [],
            "feedback": selected.get("feedback", ""),
            "is_ideal": bool(selected.get("ideal") or score >= ideal_scene_score),
        }

    if qtype in {"multiple_choice", "template_select"}:
        options = extract_options(scene)
        picked_ids = list(user_value) if user_value else []
        selected_items = [x for x in options if x["id"] in picked_ids]
        if not selected_items:
            return None

        score = sum(int(x.get("score_delta", 0)) for x in selected_items)
        if score <= 0:
            ideal_ids = {x["id"] for x in options if x.get("ideal")}
            if ideal_ids and set(picked_ids) == ideal_ids:
                score = ideal_scene_score

        return {
            "type": qtype,
            "value": picked_ids,
            "labels": [x["label"] for x in selected_items],
            "score": int(score),
            "action_tags": [x.get("action_tag", "") for x in selected_items if x.get("action_tag")],
            "feedback": " / ".join([x.get("feedback", "") for x in selected_items if x.get("feedback")]),
            "is_ideal": score >= ideal_scene_score,
        }

    if qtype == "ranking":
        ranking_items = extract_ranking_items(scene)
        if not user_value:
            return None

        ideal_map = {x["id"]: int(x["ideal_rank"]) for x in ranking_items}
        total_items = len(ranking_items)
        distance = 0
        labels = []

        for pos, rid in enumerate(user_value, start=1):
            distance += abs(pos - ideal_map.get(rid, pos))
            hit = next((x for x in ranking_items if x["id"] == rid), None)
            if hit:
                labels.append(hit["label"])

        max_distance = max(total_items * (total_items - 1) // 2, 1)
        closeness = 1 - min(distance / max_distance, 1)
        score = max(0, round(ideal_scene_score * closeness))
        is_ideal = distance == 0

        return {
            "type": qtype,
            "value": list(user_value),
            "labels": labels,
            "score": int(score),
            "action_tags": [scene.get("action_tag")] if scene.get("action_tag") else [],
            "feedback": scene.get("feedback", ""),
            "is_ideal": is_ideal,
        }

    return None


def save_scene_answer(scene_idx, scene, qtype, user_value):
    payload = calc_scene_answer_payload(scene, qtype, user_value)
    if payload is None:
        clear_scene_answer(scene_idx)
    else:
        st.session_state.answers[scene_idx] = payload
        recompute_scores()


def get_selected_transport_priority():
    tags = []
    for idx in sorted(st.session_state.answers.keys()):
        ans = st.session_state.answers[idx]
        tags.extend(ans.get("action_tags", []))

    transport_related = [t for t in tags if t in ["transport_priority", "load_and_go", "搬送優先", "搬送優先判断"]]
    if transport_related:
        return "搬送優先"
    if "stay_and_play" in tags:
        return "現場安定化優先"
    return "通常進行"


# ---------------------------------------------------------
# 描画
# ---------------------------------------------------------
def render_overview(case_data):
    header = case_data.get("header", {})
    overview = header.get("overview", case_data.get("overview"))
    rows = normalize_overview(overview)

    st.markdown('<div class="section-title">症例概要</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    if rows:
        if rows and isinstance(rows[0], tuple):
            for k, v in rows:
                st.markdown(f"**{k}**：{v}")
        else:
            for row in rows:
                st.markdown(f"- {row}")
    else:
        st.markdown('<span class="muted">概要情報はありません。</span>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_state_flags(case_data, scene):
    flags = extract_state_flags(case_data, scene)
    if not flags:
        return

    st.markdown('<div class="section-title">状態と注意点</div>', unsafe_allow_html=True)
    st.markdown('<div class="warn-card">', unsafe_allow_html=True)
    st.markdown(" / ".join([f"**{x}**" for x in flags]))
    st.markdown("</div>", unsafe_allow_html=True)


def render_scene_media(scene):
    media_list = extract_media_list(scene)
    if not media_list:
        return

    st.markdown('<div class="section-title">関連画像</div>', unsafe_allow_html=True)
    for m in media_list:
        p = resolve_media_path(m["path"])
        if p and p.exists():
            caption = m.get("caption", "")
            desc = m.get("description", "")
            final_caption = caption
            if desc:
                final_caption = f"{caption} / {desc}" if caption else desc
            st.image(str(p), caption=final_caption, use_container_width=True)
        else:
            st.warning(f"画像が見つかりません：{m['path']}")


def render_progress(scene_idx, total_scenes):
    ratio = (scene_idx + 1) / max(total_scenes, 1)
    st.markdown(
        f"""
        <div class="scene-topline">
            <div class="scene-badge">場面 {scene_idx + 1} / {total_scenes}</div>
            <div class="scene-badge">進行率 {int(ratio * 100)}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(ratio)


def render_cover():
    st.markdown(
        """
        <div class="hero-box">
            <div class="hero-title">🚑 臨床推論シミュレーション</div>
            <div class="hero-sub">
                症例をもとに、観察・判断・優先順位づけを練習する学習アプリです。<br>
                1場面ずつ進みながら、現場での思考の流れを確認できます。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1.15, 0.85], gap="large")

    with c1:
        st.markdown(
            """
            <div class="guide-card">
                <div class="guide-title">使い方</div>
                <div>
                ① 表紙から症例を選ぶ<br>
                ② 各場面で最も適切な対応を選ぶ<br>
                ③ 回答後に次の場面へ進む<br>
                ④ 最後に総合評価・改善点・理想行動を確認する
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="guide-card">
                <div class="guide-title">このアプリで練習すること</div>
                <div>
                ・初期評価と状況把握<br>
                ・重症度・緊急度判断<br>
                ・ファーストコール前後の整理<br>
                ・車内活動まで見据えた優先順位づけ
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        cases = get_case_files()
        case_count = len(cases)
        st.markdown(
            f"""
            <div class="guide-card">
                <div class="small-label">登録症例数</div>
                <div class="big-value">{case_count} 症例</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="guide-card">
                <div class="small-label">画面の流れ</div>
                <div class="big-value">表紙 → 症例選択 → 7場面 → 振り返り</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    col1, col2, col3 = st.columns([1, 1, 1.2])
    with col2:
        if st.button("はじめる", use_container_width=True, type="primary"):
            go_case_select()


def render_case_select():
    st.markdown(
        """
        <div class="hero-box">
            <div class="hero-title">症例を選ぶ</div>
            <div class="hero-sub">
                興味のある分野や難易度から症例を選んで開始します。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cases = get_case_files()

    if not cases:
        st.error("cases 配下にJSON症例ファイルが見つかりません。")
        if st.button("表紙へ戻る"):
            go_cover()
        return

    categories = sorted(list({c["category_label"] for c in cases}))

    difficulty_order = ["Easy", "Normal", "Hard"]
    existing_difficulties = {str(c["difficulty"]) for c in cases}
    difficulties = [d for d in difficulty_order if d in existing_difficulties]

    f1, f2 = st.columns([1, 1], gap="medium")
    with f1:
        selected_category = st.selectbox("カテゴリ", ["すべて"] + categories, index=0)
    with f2:
        selected_difficulty = st.selectbox("難易度", ["すべて"] + difficulties, index=0)

    filtered_indexes = []
    for i, c in enumerate(cases):
        ok_cat = selected_category == "すべて" or c["category_label"] == selected_category
        ok_diff = selected_difficulty == "すべて" or str(c["difficulty"]) == selected_difficulty
        if ok_cat and ok_diff:
            filtered_indexes.append(i)

    if not filtered_indexes:
        st.info("条件に合う症例がありません。")
        if st.button("表紙へ戻る"):
            go_cover()
        return

    cols = st.columns(2, gap="large")
    for idx, original_index in enumerate(filtered_indexes):
        case = cases[original_index]
        with cols[idx % 2]:
            with st.container():
                st.markdown(
                    f"""
                    <div class="case-card">
                        <div class="case-title">{case["title"]}</div>
                        <div>
                            <span class="meta-pill">{case["category_label"]}</span>
                            <span class="meta-pill">難易度：{case["difficulty"]}</span>
                            <span class="meta-pill">{case["estimated_time"]}</span>
                            <span class="meta-pill">{case["scene_count"]}場面</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if case["keywords"]:
                    st.markdown(
                        " ".join([f'<span class="meta-pill">#{kw}</span>' for kw in case["keywords"]]),
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    f"""
                    <div class="case-desc">
                        {case["summary"] or "症例概要が未設定です。"}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button(f"この症例を開始", key=f"start_case_{original_index}", use_container_width=True):
                    start_case(original_index)

    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        if st.button("表紙へ戻る", use_container_width=True):
            go_cover()


def render_case_header(case_data, total_scenes):
    title = case_data.get("title") or case_data.get("case_title") or "症例"
    category = case_data.get("category")
    category_label = CATEGORY_LABELS.get(category, category if category else "未分類")
    difficulty = normalize_difficulty(case_data.get("difficulty") or "Normal")
    est_time = case_data.get("estimated_time") or case_data.get("time_required") or "約10〜15分"
    keywords = ensure_list(case_data.get("keywords") or case_data.get("tags"))

    st.markdown(
        f"""
        <div class="hero-box">
            <div class="hero-title">{title}</div>
            <div class="hero-sub">
                <span class="meta-pill">{category_label}</span>
                <span class="meta-pill">難易度：{difficulty}</span>
                <span class="meta-pill">{est_time}</span>
                <span class="meta-pill">{total_scenes}場面</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if keywords:
        st.markdown(" ".join([f'<span class="meta-pill">#{kw}</span>' for kw in keywords]), unsafe_allow_html=True)

    render_overview(case_data)


# ---------------------------------------------------------
# 入力UI
# ---------------------------------------------------------
def render_single_choice(scene_idx, scene):
    options = extract_options(scene)
    if not options:
        st.warning("選択肢が設定されていません。")
        clear_scene_answer(scene_idx)
        return False

    saved = get_saved_answer(scene_idx)
    saved_value = saved["value"] if saved and saved.get("type") == "single_choice" else None

    labels = [opt["label"] for opt in options]
    label_to_id = {opt["label"]: opt["id"] for opt in options}
    selected_label = next((opt["label"] for opt in options if opt["id"] == saved_value), None)

    picked_label = st.radio(
        "選択してください",
        options=labels,
        index=labels.index(selected_label) if selected_label in labels else None,
        key=f"radio_scene_{scene_idx}",
        label_visibility="collapsed",
    )

    if picked_label:
        selected_id = label_to_id[picked_label]
        save_scene_answer(scene_idx, scene, "single_choice", selected_id)
        return True

    clear_scene_answer(scene_idx)
    return False


def render_multiple_choice(scene_idx, scene):
    options = extract_options(scene)
    if not options:
        st.warning("選択肢が設定されていません。")
        clear_scene_answer(scene_idx)
        return False

    saved = get_saved_answer(scene_idx)
    saved_values = saved["value"] if saved and saved.get("type") == "multiple_choice" else []

    label_to_id = {opt["label"]: opt["id"] for opt in options}
    default_labels = [opt["label"] for opt in options if opt["id"] in saved_values]

    selected_labels = st.multiselect(
        "該当するものを選択してください",
        options=list(label_to_id.keys()),
        default=default_labels,
        key=f"multi_scene_{scene_idx}",
        label_visibility="collapsed",
    )

    selected_ids = [label_to_id[x] for x in selected_labels]
    if selected_ids:
        save_scene_answer(scene_idx, scene, "multiple_choice", selected_ids)
        return True

    clear_scene_answer(scene_idx)
    return False


def render_template_select(scene_idx, scene):
    st.markdown(
        """
        <div class="info-card">
            ファーストコールや申し送りに使う項目を、必要なものから選択してください。
        </div>
        """,
        unsafe_allow_html=True,
    )

    options = extract_options(scene)
    if not options:
        st.warning("テンプレート項目が設定されていません。")
        clear_scene_answer(scene_idx)
        return False

    saved = get_saved_answer(scene_idx)
    saved_values = saved["value"] if saved and saved.get("type") == "template_select" else []

    cols = st.columns(2, gap="medium")
    selected_ids = []

    for i, opt in enumerate(options):
        with cols[i % 2]:
            checked = st.checkbox(
                opt["label"],
                value=opt["id"] in saved_values,
                key=f"template_scene_{scene_idx}_{opt['id']}",
            )
            if checked:
                selected_ids.append(opt["id"])

    if selected_ids:
        save_scene_answer(scene_idx, scene, "template_select", selected_ids)
        return True

    clear_scene_answer(scene_idx)
    return False


def render_ranking(scene_idx, scene):
    st.markdown(
        """
        <div class="info-card">
            項目を優先順に並べ替えてください。上へ / 下へ ボタンで順序を調整します。
        </div>
        """,
        unsafe_allow_html=True,
    )

    items = extract_ranking_items(scene)
    if not items:
        st.warning("並べ替え項目が設定されていません。")
        clear_scene_answer(scene_idx)
        return False

    order_key = ranking_order_key(scene_idx)
    if order_key not in st.session_state:
        saved = get_saved_answer(scene_idx)
        if saved and saved.get("type") == "ranking":
            st.session_state[order_key] = list(saved["value"])
        else:
            st.session_state[order_key] = [x["id"] for x in items]

    current_order = st.session_state[order_key]
    valid_ids = {x["id"] for x in items}
    current_order = [x for x in current_order if x in valid_ids]

    missing_ids = [x["id"] for x in items if x["id"] not in current_order]
    current_order.extend(missing_ids)
    st.session_state[order_key] = current_order

    id_to_label = {x["id"]: x["label"] for x in items}

    for idx, item_id in enumerate(current_order):
        c1, c2, c3 = st.columns([0.12, 0.68, 0.2])
        with c1:
            st.markdown(f"**{idx + 1}.**")
        with c2:
            st.markdown(id_to_label.get(item_id, item_id))
        with c3:
            up_col, down_col = st.columns(2)
            with up_col:
                if st.button("↑", key=f"rank_up_{scene_idx}_{item_id}", use_container_width=True, disabled=(idx == 0)):
                    current_order[idx - 1], current_order[idx] = current_order[idx], current_order[idx - 1]
                    st.session_state[order_key] = current_order
                    st.rerun()
            with down_col:
                if st.button("↓", key=f"rank_dn_{scene_idx}_{item_id}", use_container_width=True, disabled=(idx == len(current_order) - 1)):
                    current_order[idx + 1], current_order[idx] = current_order[idx], current_order[idx + 1]
                    st.session_state[order_key] = current_order
                    st.rerun()

    save_scene_answer(scene_idx, scene, "ranking", current_order)
    return True


def render_question_input(scene_idx, scene):
    qtype = detect_question_type(scene)

    st.markdown(
        f"""
        <div class="question-card">
            <div class="small-label">設問</div>
            <div><strong>{scene_prompt_text(scene)}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if qtype == "single_choice":
        return render_single_choice(scene_idx, scene)

    if qtype == "multiple_choice":
        return render_multiple_choice(scene_idx, scene)

    if qtype == "template_select":
        return render_template_select(scene_idx, scene)

    if qtype == "ranking":
        return render_ranking(scene_idx, scene)

    st.info("この場面の入力形式に対応していません。")
    clear_scene_answer(scene_idx)
    return False


def render_saved_feedback(scene_idx):
    saved = get_saved_answer(scene_idx)
    if not saved:
        return

    ok = saved.get("is_ideal", False)
    feedback = saved.get("feedback", "")

    if ok:
        st.markdown(
            """
            <div class="good-card">
                <span class="answer-status-ok">回答を保持しました。</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="warn-card">
                <span class="answer-status-ng">回答を保持しました。振り返りで改善点を確認できます。</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if feedback:
        st.markdown(
            f"""
            <div class="info-card">
                <div class="small-label">この選択に関するメモ</div>
                <div>{feedback}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_scene_page():
    case_data = get_current_case()
    if not case_data:
        st.error("症例データが読み込めません。")
        if st.button("症例選択へ戻る"):
            go_case_select()
        return

    scenes = get_scenes(case_data)
    if not scenes:
        st.error("この症例には scenes がありません。")
        if st.button("症例選択へ戻る"):
            go_case_select()
        return

    total_scenes = len(scenes)
    scene_idx = st.session_state.scene_index
    scene = get_scene(case_data, scene_idx)

    if scene is None:
        st.error("場面データが見つかりません。")
        if st.button("症例選択へ戻る"):
            go_case_select()
        return

    render_case_header(case_data, total_scenes)
    render_progress(scene_idx, total_scenes)

    st.markdown(
        f"""
        <div class="scene-shell">
            <div class="scene-badge">{scene.get("id", f"scene{scene_idx+1}")}</div>
            <div class="scene-title">{scene_title(scene, scene_idx)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    body = scene_body_text(scene)
    if body:
        st.markdown(f'<div class="scene-text">{body.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

    goal = extract_scene_goal(scene)
    if goal:
        st.markdown(
            f"""
            <div class="info-card">
                <div class="small-label">この場面の目標</div>
                <div>{goal}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    ideal_flow = extract_ideal_flow(scene)
    if ideal_flow:
        st.markdown('<div class="section-title">理想の流れ（ヒント）</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        for x in ideal_flow:
            st.markdown(f"- {x}")
        st.markdown("</div>", unsafe_allow_html=True)

    render_state_flags(case_data, scene)
    render_scene_media(scene)

    if scene_has_interactive_input(scene):
        st.markdown('<div class="section-title">あなたの判断</div>', unsafe_allow_html=True)
        render_question_input(scene_idx, scene)
        render_saved_feedback(scene_idx)
    else:
        st.markdown(
            """
            <div class="info-card">
                この場面は確認用です。内容を確認したら次へ進めます。
            </div>
            """,
            unsafe_allow_html=True,
        )

    total, max_total = recompute_scores()
    live_ratio = 0 if max_total == 0 else total / max_total
    live_percent = int(round(live_ratio * 100))

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.markdown(
            f"""
            <div class="guide-card">
                <div class="small-label">現在の得点</div>
                <div class="big-value">{total} / {max_total}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="guide-card">
                <div class="small-label">達成率</div>
                <div class="big-value">{live_percent}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="guide-card">
                <div class="small-label">活動方針</div>
                <div class="big-value">{get_selected_transport_priority()}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    nav1, nav2, nav3 = st.columns([1, 1, 1], gap="medium")

    with nav1:
        prev_disabled = scene_idx == 0
        if st.button("前の場面へ", use_container_width=True, disabled=prev_disabled):
            if scene_idx > 0:
                st.session_state.scene_index -= 1
                st.rerun()

    with nav2:
        if st.button("症例選択へ戻る", use_container_width=True):
            st.session_state.case_data = None
            st.session_state.case_index = None
            reset_case_progress()
            go_case_select()

    with nav3:
        next_disabled = not scene_has_answer(scene_idx, scene)
        next_label = "結果を見る" if scene_idx == total_scenes - 1 else "次の場面へ"
        if st.button(next_label, use_container_width=True, type="primary", disabled=next_disabled):
            if scene_idx < total_scenes - 1:
                st.session_state.scene_index += 1
                st.rerun()
            else:
                st.session_state.page = "debrief"
                st.rerun()

    if next_disabled:
        st.markdown('<div class="center-note">回答すると次へ進めます。</div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# 振り返り
# ---------------------------------------------------------
def rank_label(percent):
    if percent >= 90:
        return "S評価", "かなり安定した判断です。現場の優先順位づけがよく整理できています。", "debrief-s"
    if percent >= 80:
        return "A評価", "良い流れです。大事なポイントは押さえられています。", "debrief-a"
    if percent >= 65:
        return "B評価", "大枠はできています。細かな優先順位の磨き込みで伸びます。", "debrief-b"
    if percent >= 50:
        return "C評価", "観察はできていますが、判断の軸が少しぶれています。", "debrief-c"
    return "再挑戦", "焦点が散っています。まずは各場面の目標を意識してやり直すと伸びます。", "debrief-d"


def build_debrief(case_data):
    scenes = get_scenes(case_data)
    debriefing = case_data.get("debriefing", {}) if isinstance(case_data.get("debriefing"), dict) else {}

    json_good = ensure_list(debriefing.get("good_points"))
    json_cautions = ensure_list(debriefing.get("cautions"))
    json_ideal_actions = ensure_list(debriefing.get("ideal_actions"))
    json_summary = normalize_text(debriefing.get("summary"))

    good_points = []
    improvement_points = []
    ideal_actions = []

    for idx, scene in enumerate(scenes):
        ans = st.session_state.answers.get(idx)
        goal = extract_scene_goal(scene)
        ideal_flow = extract_ideal_flow(scene)
        title = scene_title(scene, idx)

        if ans and ans.get("is_ideal"):
            if goal:
                good_points.append(f"{title}：{goal}")
            else:
                good_points.append(f"{title}：適切な判断ができています。")
        else:
            if goal:
                improvement_points.append(f"{title}：{goal} を意識すると改善しやすいです。")
            else:
                improvement_points.append(f"{title}：場面の目標に沿った優先順位づけを再確認。")

        if ideal_flow:
            ideal_actions.append(f"{title}：{' → '.join(ideal_flow)}")
        else:
            tagged = scene.get("action_tag") or scene.get("ideal_action")
            if tagged:
                ideal_actions.append(f"{title}：{tagged}")

    if json_good:
        good_points = json_good + good_points
    if json_cautions:
        improvement_points = json_cautions + improvement_points
    if json_ideal_actions:
        ideal_actions = json_ideal_actions + ideal_actions

    return {
        "summary": json_summary,
        "good_points": good_points,
        "improvement_points": improvement_points,
        "ideal_actions": ideal_actions,
    }


def render_answer_summary(case_data):
    scenes = get_scenes(case_data)
    st.markdown('<div class="section-title">場面ごとの振り返り</div>', unsafe_allow_html=True)

    for idx, scene in enumerate(scenes):
        ans = st.session_state.answers.get(idx)
        title = scene_title(scene, idx)
        goal = extract_scene_goal(scene)
        ideal_flow = extract_ideal_flow(scene)

        if ans and ans.get("is_ideal"):
            box_class = "good-card"
            status = "良好"
        else:
            box_class = "warn-card"
            status = "見直し"

        if not scene_has_interactive_input(scene):
            box_class = "info-card"
            status = "確認"

        st.markdown(f'<div class="{box_class}">', unsafe_allow_html=True)
        st.markdown(f"**{title}**　/　**{status}**")

        if goal:
            st.markdown(f"- 目標：{goal}")

        if ans:
            labels = ans.get("labels", [])
            if labels:
                st.markdown(f"- あなたの選択：{' / '.join(labels)}")
            st.markdown(f"- 得点：{ans.get('score', 0)}")
            if ans.get("feedback"):
                st.markdown(f"- メモ：{ans.get('feedback')}")
        elif not scene_has_interactive_input(scene):
            st.markdown("- この場面は確認用")

        if ideal_flow:
            st.markdown(f"- 理想行動：{' → '.join(ideal_flow)}")

        st.markdown("</div>", unsafe_allow_html=True)


def render_debrief():
    case_data = get_current_case()
    if not case_data:
        st.error("症例データがありません。")
        if st.button("症例選択へ戻る"):
            go_case_select()
        return

    total, max_total = recompute_scores()
    percent = 0 if max_total == 0 else int(round((total / max_total) * 100))
    rank, comment, rank_class = rank_label(percent)
    debrief = build_debrief(case_data)

    st.markdown(
        f"""
        <div class="debrief-head {rank_class}">
            <div class="rank-badge">最終評価</div>
            <div class="debrief-score">{percent}%</div>
            <div style="font-size:1.2rem;font-weight:800;margin-bottom:8px;">{rank}</div>
            <div>{comment}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if debrief["summary"]:
        st.markdown(
            f"""
            <div class="info-card">
                <div class="small-label">総括</div>
                <div>{debrief["summary"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.markdown(
            f"""
            <div class="guide-card">
                <div class="small-label">得点</div>
                <div class="big-value">{total} / {max_total}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="guide-card">
                <div class="small-label">活動方針</div>
                <div class="big-value">{get_selected_transport_priority()}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        title = case_data.get("title") or case_data.get("case_title") or "症例"
        st.markdown(
            f"""
            <div class="guide-card">
                <div class="small-label">症例</div>
                <div class="big-value">{title}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown('<div class="section-title">よかった点</div>', unsafe_allow_html=True)
        st.markdown('<div class="good-card">', unsafe_allow_html=True)
        if debrief["good_points"]:
            for x in debrief["good_points"][:10]:
                st.markdown(f"- {x}")
        else:
            st.markdown("- 今回は見直しポイントが多めです。次回で伸ばせます。")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-title">改善点</div>', unsafe_allow_html=True)
        st.markdown('<div class="warn-card">', unsafe_allow_html=True)
        if debrief["improvement_points"]:
            for x in debrief["improvement_points"][:10]:
                st.markdown(f"- {x}")
        else:
            st.markdown("- 大きな改善点はありません。")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-title">理想行動</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        if debrief["ideal_actions"]:
            for x in debrief["ideal_actions"][:10]:
                st.markdown(f"- {x}")
        else:
            st.markdown("- 理想行動の設定がありません。")
        st.markdown("</div>", unsafe_allow_html=True)

    render_answer_summary(case_data)

    c1, c2, c3 = st.columns([1, 1, 1], gap="medium")
    with c1:
        if st.button("もう一度やる", use_container_width=True):
            reset_case_progress()
            st.session_state.page = "scene"
            st.rerun()

    with c2:
        if st.button("別症例へ", use_container_width=True):
            st.session_state.case_data = None
            st.session_state.case_index = None
            reset_case_progress()
            go_case_select()

    with c3:
        if st.button("表紙へ戻る", use_container_width=True):
            st.session_state.case_data = None
            st.session_state.case_index = None
            reset_case_progress()
            go_cover()


# ---------------------------------------------------------
# メイン
# ---------------------------------------------------------
def main():
    init_session_state()
    inject_css()

    page = st.session_state.page

    if page == "cover":
        render_cover()
    elif page == "case_select":
        render_case_select()
    elif page == "scene":
        render_scene_page()
    elif page == "debrief":
        render_debrief()
    else:
        render_cover()


if __name__ == "__main__":
    main()