import copy
import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components


# =========================================================
# 基本設定
# =========================================================
st.set_page_config(
    page_title="臨床推論シミュレーション",
    page_icon="🚑",
    layout="wide",
)

APP_TITLE = "救急救命士向け 臨床推論シミュレーション"
REPO_ROOT = Path(__file__).parent
CASES_DIR = REPO_ROOT / "cases"
MEDIA_DIR = REPO_ROOT / "media"
LEVEL_SIZE = 10
DEFAULT_SCENE_COUNT = 7

FIELD_LABEL_FALLBACK = {
    "cardiovascular": "循環器",
    "endocrine_metabolic": "内分泌・代謝",
    "environmental_special": "環境障害・特殊病態",
    "gastrointestinal": "消化器",
    "neuro": "神経",
    "orthopedic": "整形",
    "psychiatric": "精神",
    "reproductive_obstetric": "産科・生殖器",
    "respiratory": "呼吸器",
    "special_population": "小児・高齢者など",
    "toxicology": "中毒",
    "trauma": "外傷",
    "urinary": "泌尿器",
    "other": "その他",
}

VISIBLE_DATA_LABELS = {
    "location": "場所",
    "chief_complaint": "主訴",
    "awareness": "意識",
    "consciousness": "意識",
    "mental_status": "意識状態",
    "respiratory_rate": "呼吸数",
    "respiration_rate": "呼吸数",
    "pulse_rate": "脈拍数",
    "heart_rate": "心拍数",
    "pulse_regular": "脈拍整",
    "blood_pressure": "血圧",
    "spo2": "SpO2",
    "temperature": "体温",
    "body_temperature": "体温",
    "skin_color": "皮膚色",
    "skin": "皮膚",
    "breathing": "呼吸",
    "circulation": "循環",
    "airway": "気道",
    "shock_sign": "ショック所見",
    "new_medication": "新規薬剤",
    "urine": "尿所見",
    "course": "経過",
    "fever": "発熱",
    "dark_urine": "赤黒色尿",
    "risk": "注意点",
    "ecg_impression": "心電図所見",
    "arrest_now": "現時点の心停止",
    "bp": "血圧",
    "last_seen_well": "最終健常確認時刻",
    "sleep_place": "就寝場所",
    "found_time": "発見時刻",
    "trauma_sign": "外傷所見",
    "external_injury": "外表外傷",
    "bleeding": "出血",
    "environment": "周囲環境",
    "ecg": "心電図",
    "suspected_condition": "疑う病態",
    "age_group": "年齢区分",
    "condition": "状態",
    "external_abnormality": "外表異常",
    "pregnancy_week": "妊娠週数",
    "rupture_of_membranes": "破水",
    "newborn_cry": "啼泣",
    "limb_activity": "四肢活動",
    "umbilical_cord": "臍帯",
    "body_wetness": "体表湿潤",
    "newborn_condition": "新生児状態",
    "major_next_risk": "次に注意すべきリスク",
    "newborn_after_wipe": "羊水拭き取り後",
    "goal": "目標",
    "maternal_risk_after_delivery": "分娩後の母体リスク",
    "mother_status": "母体状態",
    "newborn_status": "児の状態",
    "performed_care": "実施処置",
    "mechanism": "受傷機転",
    "extrication_delay": "救出までの時間",
    "trauma_type": "外傷種別",
    "flail_chest": "胸郭動揺",
    "subcutaneous_emphysema": "皮下気腫",
    "jugular_venous_distention": "頸静脈怒張",
    "external_bleeding": "外出血",
    "thoracic_red_flags": "胸部危険所見",
    "age_risk": "年齢リスク",
    "concern": "懸念病態",
    "seatbelt_sign": "シートベルト痕",
    "implication": "示唆",
    "suspected_shock_type": "疑うショック",
    "transport_priority": "搬送優先度",
}

BOOL_JA = {
    True: "あり",
    False: "なし",
}

STOPWORDS = {
    "する", "した", "して", "ます", "です", "ある", "ない", "よう", "ため", "こと",
    "この", "その", "傷病者", "場面", "選択", "必要", "優先", "確認", "判断", "対応",
    "実施", "行う", "行なう", "評価", "観察", "報告", "連絡", "考える", "べき", "まず",
    "次に", "あと", "および", "また", "など", "より", "ために", "状態", "内容", "模範",
    "方向", "理想", "良い", "よい", "患者", "救急隊", "救命士",
}


# =========================================================
# 基本ユーティリティ
# =========================================================
def html_escape(text: Any) -> str:
    if text is None:
        return ""
    text = str(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def to_text_lines(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        lines: List[str] = []
        for k, v in value.items():
            label = VISIBLE_DATA_LABELS.get(str(k), str(k))
            lines.append(f"{label}：{v}")
        return lines
    if isinstance(value, list):
        lines: List[str] = []
        for item in value:
            lines.extend(to_text_lines(item))
        return lines
    return [str(value)]


def normalize_text(text: Any) -> str:
    s = str(text or "").lower()
    s = s.replace("　", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def extract_keywords_from_text(text: Any, min_length: int = 2) -> List[str]:
    raw = normalize_text(text)
    if not raw:
        return []
    candidates = re.findall(r"[ぁ-んァ-ヶー一-龥a-zA-Z0-9\+\-/]{2,}", raw)
    keywords: List[str] = []
    for c in candidates:
        if len(c) < min_length:
            continue
        if c in STOPWORDS:
            continue
        if c.isdigit():
            continue
        if c not in keywords:
            keywords.append(c)
    return keywords


def unique_keep_order(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


# =========================================================
# CSS
# =========================================================
def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #f5f7fb;
            --card: #ffffff;
            --text: #162338;
            --muted: #607086;
            --line: #d9e2ef;
            --blue: #1f5fbf;
            --blue-soft: #eaf2ff;
            --green: #2e7d32;
            --green-soft: #e9f6ea;
            --orange: #ef6c00;
            --orange-soft: #fff1e6;
            --red: #c62828;
            --red-soft: #fdecec;
            --yellow: #f9a825;
            --yellow-soft: #fff8e1;
            --gray-soft: #f1f4f8;
            --shadow: 0 8px 24px rgba(20,35,56,0.06);
        }

        .stApp {
            background: linear-gradient(180deg, #f6f8fc 0%, #eef3f9 100%);
            color: var(--text);
        }

        html, body, [class*="css"], .stApp {
            color: var(--text);
            font-family: "BIZ UDPGothic", "Yu Gothic UI", "Meiryo", sans-serif !important;
        }

        .scroll-top-anchor {
            display: block;
            height: 1px;
            width: 100%;
        }

        .app-hero {
            background: linear-gradient(135deg, #1f5fbf 0%, #3c7be0 100%);
            color: white;
            border-radius: 20px;
            padding: 22px 24px;
            margin-bottom: 16px;
            box-shadow: 0 12px 32px rgba(31,95,191,0.18);
        }

        .app-hero h1 {
            margin: 0 0 8px 0;
            font-size: 1.85rem;
            line-height: 1.25;
            color: white;
        }

        .app-hero p {
            margin: 0;
            opacity: 0.96;
            font-size: 0.98rem;
            line-height: 1.7;
            color: white;
        }

        .section-title {
            font-weight: 700;
            font-size: 1.15rem;
            margin: 12px 0 12px 0;
            color: var(--text);
        }

        .soft-panel {
            background: rgba(255,255,255,0.92);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 16px 18px;
            box-shadow: 0 6px 20px rgba(20,35,56,0.05);
            margin-bottom: 12px;
        }

        .case-card, .scene-card, .hint-card, .review-card {
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 16px 16px;
            box-shadow: var(--shadow);
            margin-bottom: 12px;
        }

        .case-main {
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 4px;
            color: var(--text);
        }

        .case-sub {
            color: var(--muted);
            font-size: 0.94rem;
            margin-bottom: 4px;
        }

        .scene-header {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }

        .scene-title {
            font-size: 1.15rem;
            font-weight: 800;
            color: var(--text);
        }

        .scene-phase, .mode-pill, .level-pill, .progress-pill {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: var(--gray-soft);
            color: var(--text);
            font-size: 0.82rem;
            font-weight: 700;
        }

        .mode-pill.random { background: #ede7f6; color: #5e35b1; }
        .mode-pill.level { background: #e3f2fd; color: #1565c0; }
        .level-pill { background: #fff8e1; color: #ef6c00; }
        .progress-pill { background: #edf9ef; color: #2e7d32; }

        .goal-box {
            border-left: 5px solid var(--blue);
            background: var(--blue-soft);
            border-radius: 12px;
            padding: 12px 14px;
            margin: 10px 0 14px 0;
        }

        .hint-box {
            border-left: 5px solid var(--yellow);
            background: var(--yellow-soft);
            border-radius: 12px;
            padding: 12px 14px;
            margin: 10px 0 14px 0;
        }

        .report-box {
            background: #eaf2ff;
            border-left: 6px solid #1f5fbf;
            border-radius: 14px;
            padding: 14px 16px;
            margin: 12px 0;
        }

        .observation-box {
            background: #fff8e1;
            border-left: 6px solid #ef6c00;
            border-radius: 14px;
            padding: 14px 16px;
            margin: 12px 0;
        }

        .report-box .label, .observation-box .label {
            font-size: 0.82rem;
            font-weight: 800;
            margin-bottom: 6px;
            letter-spacing: 0.03em;
        }

        .report-box .label { color: #1f5fbf; }
        .observation-box .label { color: #ef6c00; }

        .report-box .body, .observation-box .body {
            font-size: 1.04rem;
            font-weight: 700;
            line-height: 1.8;
            color: #162338;
            white-space: pre-wrap;
        }

        .muted {
            color: var(--muted);
            font-size: 0.92rem;
        }

        .progress-wrap {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 14px 16px;
            margin-bottom: 12px;
        }

        .progress-label {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.92rem;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 8px;
        }

        .progress-track {
            width: 100%;
            height: 12px;
            border-radius: 999px;
            background: #dfe8f4;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #1f5fbf 0%, #4d8ef2 100%);
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }

        .summary-box {
            background: #fff;
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 14px;
            text-align: center;
        }

        .summary-box .big {
            font-size: 1.35rem;
            font-weight: 800;
        }

        .summary-box .small {
            font-size: 0.86rem;
            color: var(--muted);
            margin-top: 4px;
        }

        .review-block {
            border-radius: 14px;
            padding: 12px 14px;
            margin-bottom: 10px;
            border: 1px solid var(--line);
        }

        .review-blue { background: #eef4ff; border-left: 6px solid #1f5fbf; }
        .review-green { background: #edf9ef; border-left: 6px solid #2e7d32; }
        .review-yellow { background: #fff8e6; border-left: 6px solid #f9a825; }
        .review-red { background: #fdeeee; border-left: 6px solid #c62828; }

        .review-title {
            font-weight: 800;
            margin-bottom: 6px;
            font-size: 0.95rem;
        }

        .score-chip {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: #edf3ff;
            color: #1f5fbf;
            font-size: 0.84rem;
            font-weight: 800;
        }

        .stButton > button {
            width: 100%;
            min-height: 3rem;
            border-radius: 14px;
            font-weight: 700;
            border: 1px solid #cfd8e6;
        }

        div[role="radiogroup"] label,
        div[role="group"] label,
        .stRadio label,
        .stCheckbox label,
        .stMultiSelect span,
        .stSelectbox span,
        .stButton button,
        button[kind="secondary"],
        button[kind="primary"] {
            white-space: normal !important;
            overflow-wrap: anywhere !important;
            word-break: break-word !important;
            line-height: 1.5 !important;
        }

        @media (max-width: 768px) {
            .app-hero { padding: 18px 16px; border-radius: 16px; }
            .app-hero h1 { font-size: 1.45rem; }
            .scene-title { font-size: 1.02rem; }
            .summary-grid { grid-template-columns: 1fr; }
            .case-card, .scene-card, .hint-card, .review-card { padding: 14px; border-radius: 16px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# スクロール制御
# =========================================================
def render_scroll_anchor() -> None:
    st.markdown('<div id="top-anchor" class="scroll-top-anchor"></div>', unsafe_allow_html=True)


def mark_scroll_top() -> None:
    st.session_state.pending_scroll_top = True


def trigger_scroll_top_if_needed() -> None:
    if not st.session_state.get("pending_scroll_top", False):
        return

    components.html(
        """
        <script>
        function scrollAllTheThings() {
            try {
                const parentDoc = window.parent && window.parent.document ? window.parent.document : null;
                if (parentDoc) {
                    const anchor = parentDoc.getElementById("top-anchor");
                    if (anchor && anchor.scrollIntoView) {
                        anchor.scrollIntoView({behavior: "auto", block: "start"});
                    }
                    const selectors = [
                        "section.main",
                        '[data-testid="stAppViewContainer"]',
                        ".main",
                        "body",
                        "html"
                    ];
                    selectors.forEach((sel) => {
                        const el = parentDoc.querySelector(sel);
                        if (el) {
                            el.scrollTop = 0;
                        }
                    });
                    if (window.parent.scrollTo) {
                        window.parent.scrollTo(0, 0);
                    }
                }
            } catch (e) {}

            try {
                const anchor = document.getElementById("top-anchor");
                if (anchor && anchor.scrollIntoView) {
                    anchor.scrollIntoView({behavior: "auto", block: "start"});
                }
                document.documentElement.scrollTop = 0;
                document.body.scrollTop = 0;
                window.scrollTo(0, 0);
            } catch (e) {}
        }

        const delays = [0, 80, 180, 320, 520, 760];
        delays.forEach((d) => setTimeout(scrollAllTheThings, d));
        requestAnimationFrame(scrollAllTheThings);
        </script>
        """,
        height=0,
    )
    st.session_state.pending_scroll_top = False


def rerun_with_scroll_top() -> None:
    mark_scroll_top()
    st.rerun()


# =========================================================
# Session State
# =========================================================
def init_state() -> None:
    defaults = {
        "screen": "cover",
        "selected_mode": "level",
        "selected_level_name": None,
        "selected_case_id": None,
        "level_progress_index": 0,
        "random_progress_index": 0,
        "scene_display_index": 0,
        "answers": {},
        "feedbacks": {},
        "score_total": 0.0,
        "score_max": 0.0,
        "hint_from_scene_index": None,
        "pending_scroll_top": False,
        "level_case_map": {},
        "level_case_order": {},
        "all_random_order": [],
        "free_text_scene_map": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_case_progress() -> None:
    st.session_state.scene_display_index = 0
    st.session_state.answers = {}
    st.session_state.feedbacks = {}
    st.session_state.score_total = 0.0
    st.session_state.score_max = 0.0
    st.session_state.hint_from_scene_index = None

    ranking_keys = [k for k in list(st.session_state.keys()) if str(k).startswith("ranking_order__")]
    for k in ranking_keys:
        del st.session_state[k]


# =========================================================
# JSON / Case 読み込み
# =========================================================
def safe_read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def discover_case_files() -> List[Path]:
    if not CASES_DIR.exists():
        return []
    files = []
    for p in CASES_DIR.rglob("*.json"):
        if p.name.startswith("."):
            continue
        if "media" in p.parts:
            continue
        files.append(p)
    return sorted(files)


def extract_field_from_path(path: Path) -> str:
    try:
        rel = path.relative_to(CASES_DIR)
        if len(rel.parts) >= 2:
            return rel.parts[0]
    except Exception:
        pass
    return "other"


def get_scenes_from_case(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    scenes = []

    if isinstance(data.get("scenes"), list):
        for idx, sc in enumerate(data["scenes"], start=1):
            if isinstance(sc, dict):
                x = copy.deepcopy(sc)
                x.setdefault("id", f"scene{idx}")
                scenes.append(x)

    if scenes:
        return scenes

    for i in range(1, 8):
        key = f"scene_{i}"
        if isinstance(data.get(key), dict):
            x = copy.deepcopy(data[key])
            x.setdefault("id", key)
            scenes.append(x)

    if scenes:
        return scenes

    for i in range(1, 8):
        key = f"scene{i}"
        if isinstance(data.get(key), dict):
            x = copy.deepcopy(data[key])
            x.setdefault("id", key)
            scenes.append(x)

    return scenes


def infer_chief_complaint(text: str) -> str:
    if not text:
        return "症例"
    text = str(text)
    keywords = [
        "胸痛", "呼吸困難", "意識障害", "腹痛", "頭痛", "発熱", "嘔吐", "痙攣",
        "吐血", "下血", "めまい", "しびれ", "ろれつ障害", "外傷", "背部痛",
        "動悸", "失神", "ショック", "喘鳴", "窒息", "徐脈", "頻脈",
    ]
    for kw in keywords:
        if kw in text:
            return kw
    short = text.replace("\n", " ").strip()
    return short[:18] + ("…" if len(short) > 18 else "")


def extract_age_sex(text: str) -> Tuple[str, str]:
    if not text:
        return "年齢不明", "性別不明"
    age = "年齢不明"
    sex = "性別不明"

    m_age = re.search(r"(\d{1,3})歳", text)
    if m_age:
        age = f"{m_age.group(1)}歳"

    if "男性" in text:
        sex = "男性"
    elif "女性" in text:
        sex = "女性"

    return age, sex


def extract_case_card_info(data: Dict[str, Any], path: Path) -> Dict[str, str]:
    if isinstance(data.get("list_display"), dict):
        age = str(data["list_display"].get("age", "年齢不明"))
        sex = str(data["list_display"].get("sex", "性別不明"))
        chief = str(data["list_display"].get("chief_complaint", "症例"))
        return {"age": age, "sex": sex, "chief_complaint": chief}

    patient_profile = data.get("patient_profile", {})
    if isinstance(patient_profile, dict):
        age_value = patient_profile.get("age")
        sex_value = patient_profile.get("sex")
        age = f"{age_value}歳" if isinstance(age_value, int) else "年齢不明"
        if age_value == 0:
            age = "0歳"
        sex = "性別不明"
        if str(sex_value).lower() == "male":
            sex = "男性"
        elif str(sex_value).lower() == "female":
            sex = "女性"
    else:
        age, sex = "年齢不明", "性別不明"

    candidates = [data.get("summary", ""), data.get("title", "")]
    scenes = get_scenes_from_case(data)
    if scenes:
        first = scenes[0]
        candidates.extend([
            first.get("text", ""),
            first.get("title", ""),
            first.get("prompt", ""),
            str(first.get("visible_data", "")),
        ])
    base_text = " ".join([str(x) for x in candidates if x])

    if age == "年齢不明" or sex == "性別不明":
        infer_age, infer_sex = extract_age_sex(base_text)
        if age == "年齢不明":
            age = infer_age
        if sex == "性別不明":
            sex = infer_sex

    chief = infer_chief_complaint(base_text)
    return {"age": age, "sex": sex, "chief_complaint": chief}


def build_case_payload(path: Path) -> Optional[Dict[str, Any]]:
    data = safe_read_json(path)
    if not data:
        return None

    scenes = get_scenes_from_case(data)
    if not scenes:
        return None

    field_key = data.get("category") or data.get("field") or extract_field_from_path(path)
    field_label = FIELD_LABEL_FALLBACK.get(field_key, field_key)
    card_info = extract_case_card_info(data, path)

    case_id = data.get("case_id") or data.get("id") or path.stem
    title = str(data.get("title") or path.stem)

    return {
        "case_id": str(case_id),
        "path": path,
        "field_key": field_key,
        "field_label": field_label,
        "title": title,
        "summary": str(data.get("summary", "")),
        "debriefing": data.get("debriefing", {}),
        "scenes": scenes,
        "raw": data,
        "card_info": card_info,
    }


@st.cache_data(show_spinner=False)
def load_all_cases() -> List[Dict[str, Any]]:
    cases = []
    for p in discover_case_files():
        payload = build_case_payload(p)
        if payload:
            cases.append(payload)
    return cases


def get_case_by_id(cases: List[Dict[str, Any]], case_id: str) -> Optional[Dict[str, Any]]:
    for c in cases:
        if c["case_id"] == case_id:
            return c
    return None


# =========================================================
# Level編成 / ランダム順
# =========================================================
def shuffle_cases_mixed(cases: List[Dict[str, Any]], seed: Optional[int] = None) -> List[Dict[str, Any]]:
    rnd = random.Random(seed)
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for case in cases:
        buckets.setdefault(case["field_key"], []).append(case)

    for values in buckets.values():
        rnd.shuffle(values)

    field_order = list(buckets.keys())
    rnd.shuffle(field_order)

    mixed: List[Dict[str, Any]] = []
    while True:
        added = False
        for field in field_order:
            if buckets[field]:
                mixed.append(buckets[field].pop(0))
                added = True
        if not added:
            break

    return mixed


def build_levels(cases: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    mixed_cases = shuffle_cases_mixed(cases)
    levels: Dict[str, List[str]] = {}
    for idx in range(0, len(mixed_cases), LEVEL_SIZE):
        level_num = idx // LEVEL_SIZE + 1
        levels[f"Level{level_num}"] = [c["case_id"] for c in mixed_cases[idx: idx + LEVEL_SIZE]]
    return levels


def ensure_level_data(cases: List[Dict[str, Any]]) -> None:
    if not st.session_state.level_case_map:
        st.session_state.level_case_map = build_levels(cases)

    if not st.session_state.level_case_order:
        level_case_order: Dict[str, List[str]] = {}
        for level_name, case_ids in st.session_state.level_case_map.items():
            case_order = list(case_ids)
            random.shuffle(case_order)
            level_case_order[level_name] = case_order
        st.session_state.level_case_order = level_case_order

    if not st.session_state.all_random_order:
        all_ids = [c["case_id"] for c in shuffle_cases_mixed(cases)]
        st.session_state.all_random_order = all_ids


def reshuffle_current_orders(cases: List[Dict[str, Any]]) -> None:
    st.session_state.level_case_map = build_levels(cases)
    st.session_state.level_case_order = {}
    for level_name, case_ids in st.session_state.level_case_map.items():
        order = list(case_ids)
        random.shuffle(order)
        st.session_state.level_case_order[level_name] = order
    st.session_state.all_random_order = [c["case_id"] for c in shuffle_cases_mixed(cases)]
    st.session_state.level_progress_index = 0
    st.session_state.random_progress_index = 0


def get_current_case_position(mode: str) -> Tuple[int, int]:
    if mode == "level":
        level_name = st.session_state.selected_level_name
        if not level_name:
            return (0, 0)
        case_ids = st.session_state.level_case_order.get(level_name, [])
        if not case_ids:
            return (0, 0)
        return (st.session_state.level_progress_index + 1, len(case_ids))

    case_ids = st.session_state.all_random_order
    if not case_ids:
        return (0, 0)
    return (st.session_state.random_progress_index + 1, len(case_ids))


def get_free_text_count_for_level(level_name: Optional[str]) -> int:
    if not level_name:
        return 1
    m = re.search(r"Level(\d+)", level_name)
    if not m:
        return 1
    return max(1, min(DEFAULT_SCENE_COUNT, int(m.group(1))))


def choose_free_text_scenes_for_case(case_payload: Dict[str, Any]) -> List[int]:
    mode = st.session_state.selected_mode
    if mode == "all_random":
        count = max(1, min(DEFAULT_SCENE_COUNT, 3))
    else:
        count = get_free_text_count_for_level(st.session_state.selected_level_name)

    raw_scenes = case_payload["scenes"]
    preferred: List[int] = []
    for i, scene in enumerate(raw_scenes, start=1):
        current_type = normalize_scene_type(scene)
        if current_type not in {"ranking"}:
            preferred.append(i)

    if not preferred:
        preferred = list(range(1, min(DEFAULT_SCENE_COUNT, len(raw_scenes)) + 1))

    return preferred[:count]


def ensure_case_free_text_map(case_payload: Dict[str, Any]) -> None:
    case_id = case_payload["case_id"]
    if case_id not in st.session_state.free_text_scene_map:
        st.session_state.free_text_scene_map[case_id] = choose_free_text_scenes_for_case(case_payload)


def get_free_text_scene_numbers(case_payload: Dict[str, Any]) -> List[int]:
    ensure_case_free_text_map(case_payload)
    return st.session_state.free_text_scene_map.get(case_payload["case_id"], [])


def start_selected_level_first_case(cases: List[Dict[str, Any]]) -> None:
    ensure_level_data(cases)
    level_name = st.session_state.selected_level_name
    if not level_name:
        return

    case_ids = st.session_state.level_case_order.get(level_name, [])
    if not case_ids:
        return

    st.session_state.level_progress_index = 0
    st.session_state.selected_case_id = case_ids[0]

    case_payload = get_case_by_id(cases, case_ids[0])
    if case_payload:
        ensure_case_free_text_map(case_payload)

    reset_case_progress()
    go_to("intro")


def move_to_next_case_in_level(cases: List[Dict[str, Any]]) -> None:
    level_name = st.session_state.selected_level_name
    if not level_name:
        go_to("cover")
        return

    case_ids = st.session_state.level_case_order.get(level_name, [])
    next_index = st.session_state.level_progress_index + 1

    if next_index >= len(case_ids):
        reset_case_progress()
        st.session_state.selected_case_id = None
        st.session_state.level_progress_index = 0
        go_to("level_complete")
        return

    st.session_state.level_progress_index = next_index
    st.session_state.selected_case_id = case_ids[next_index]

    case_payload = get_case_by_id(cases, case_ids[next_index])
    if case_payload:
        ensure_case_free_text_map(case_payload)

    reset_case_progress()
    go_to("intro")


def start_all_random_first_case(cases: List[Dict[str, Any]]) -> None:
    ensure_level_data(cases)
    case_ids = st.session_state.all_random_order
    if not case_ids:
        return

    st.session_state.random_progress_index = 0
    st.session_state.selected_case_id = case_ids[0]

    case_payload = get_case_by_id(cases, case_ids[0])
    if case_payload:
        ensure_case_free_text_map(case_payload)

    reset_case_progress()
    go_to("intro")


def move_to_next_case_in_random(cases: List[Dict[str, Any]]) -> None:
    case_ids = st.session_state.all_random_order
    next_index = st.session_state.random_progress_index + 1

    if next_index >= len(case_ids):
        reset_case_progress()
        st.session_state.selected_case_id = None
        st.session_state.random_progress_index = 0
        go_to("random_complete")
        return

    st.session_state.random_progress_index = next_index
    st.session_state.selected_case_id = case_ids[next_index]

    case_payload = get_case_by_id(cases, case_ids[next_index])
    if case_payload:
        ensure_case_free_text_map(case_payload)

    reset_case_progress()
    go_to("intro")


# =========================================================
# メディア
# =========================================================
def find_media_path(media_value: Any) -> Optional[Path]:
    if not media_value:
        return None

    candidates = []

    if isinstance(media_value, str):
        candidates.append(media_value)
    elif isinstance(media_value, dict):
        for k in ["path", "file", "src", "image", "filename"]:
            if media_value.get(k):
                candidates.append(str(media_value[k]))
    elif isinstance(media_value, list):
        for item in media_value:
            p = find_media_path(item)
            if p:
                return p
        return None

    for raw in candidates:
        raw = raw.strip().replace("\\", "/")
        basename = Path(raw).name
        possible = [
            REPO_ROOT / raw,
            CASES_DIR / raw,
            MEDIA_DIR / raw,
            MEDIA_DIR / basename,
            Path(raw),
        ]
        for p in possible:
            if p.exists() and p.is_file():
                return p

    return None


# =========================================================
# scene type / options
# =========================================================
def normalize_scene_type(scene: Dict[str, Any]) -> str:
    t = str(scene.get("type", "")).strip().lower()
    aliases = {
        "single": "single_choice",
        "singlechoice": "single_choice",
        "single_choice": "single_choice",
        "multiple": "multiple_choice",
        "multiplechoice": "multiple_choice",
        "multiple_choice": "multiple_choice",
        "ranking": "ranking",
        "template": "template_select",
        "template_select": "template_select",
        "freetext": "free_text",
        "free_text": "free_text",
        "text": "free_text",
    }
    return aliases.get(t, "single_choice")


def get_effective_scene_type(case_payload: Dict[str, Any], scene_number: int, scene: Dict[str, Any]) -> str:
    base_type = normalize_scene_type(scene)
    if scene_number in get_free_text_scene_numbers(case_payload):
        return "free_text"
    return base_type


def normalize_options(scene: Dict[str, Any]) -> List[Dict[str, Any]]:
    options = scene.get("options", [])
    result = []

    if isinstance(options, list) and options:
        for i, opt in enumerate(options):
            if isinstance(opt, dict):
                result.append({
                    "id": str(opt.get("id", i)),
                    "label": str(opt.get("label") or opt.get("text") or opt.get("name") or f"選択肢{i+1}"),
                    "is_correct": bool(opt.get("is_correct") or opt.get("correct") or opt.get("ideal")),
                })
            else:
                result.append({
                    "id": str(i),
                    "label": str(opt),
                    "is_correct": False,
                })

    if not any(o["is_correct"] for o in result):
        answer_index = scene.get("answer_index")
        answer_indices = scene.get("answer_indices")
        if isinstance(answer_index, int) and 0 <= answer_index < len(result):
            result[answer_index]["is_correct"] = True
        if isinstance(answer_indices, list):
            for idx in answer_indices:
                if isinstance(idx, int) and 0 <= idx < len(result):
                    result[idx]["is_correct"] = True

    return result


def normalize_templates(scene: Dict[str, Any]) -> List[Dict[str, Any]]:
    templates = scene.get("templates", [])
    result = []
    if isinstance(templates, list):
        for i, t in enumerate(templates):
            if isinstance(t, dict):
                result.append({
                    "id": str(t.get("id", i)),
                    "label": str(t.get("label") or t.get("text") or t.get("name") or f"テンプレート{i+1}"),
                    "is_correct": bool(t.get("is_correct") or t.get("correct") or t.get("ideal")),
                })
            else:
                result.append({
                    "id": str(i),
                    "label": str(t),
                    "is_correct": False,
                })

    if not any(t["is_correct"] for t in result):
        answer_index = scene.get("answer_index")
        if isinstance(answer_index, int) and 0 <= answer_index < len(result):
            result[answer_index]["is_correct"] = True

    return result


def normalize_ranking(scene: Dict[str, Any]) -> List[Dict[str, Any]]:
    ranking = scene.get("ranking", [])
    result = []
    if isinstance(ranking, list):
        for i, item in enumerate(ranking):
            if isinstance(item, dict):
                result.append({
                    "id": str(item.get("id", i)),
                    "label": str(item.get("label") or item.get("text") or item.get("name") or f"項目{i+1}"),
                    "correct_order": item.get("correct_order"),
                })
            else:
                result.append({
                    "id": str(i),
                    "label": str(item),
                    "correct_order": None,
                })
    return result


# =========================================================
# 記述式 採点補助
# =========================================================
def build_model_keywords(scene: Dict[str, Any]) -> Dict[str, List[str]]:
    scoring = scene.get("scoring_keywords", {})
    required: List[str] = []
    bonus: List[str] = []

    if isinstance(scoring, dict):
        required = [str(x) for x in scoring.get("required", []) if str(x).strip()]
        bonus = [str(x) for x in scoring.get("bonus", []) if str(x).strip()]

    if not required:
        source_chunks: List[str] = []
        source_chunks.extend(to_text_lines(scene.get("ideal_flow")))
        source_chunks.extend(to_text_lines(scene.get("action_tag")))
        source_chunks.extend(to_text_lines(scene.get("scene_goal")))
        source_chunks.extend(to_text_lines(scene.get("prompt")))
        required = extract_keywords_from_text(" ".join(source_chunks))[:5]

    if not bonus:
        source_chunks = []
        source_chunks.extend(to_text_lines(scene.get("visible_data")))
        source_chunks.extend(to_text_lines(scene.get("text")))
        bonus = [x for x in extract_keywords_from_text(" ".join(source_chunks)) if x not in required][:5]

    return {
        "required": unique_keep_order(required),
        "bonus": unique_keep_order([x for x in bonus if x not in required]),
    }


def evaluate_clarity(answer_text: str) -> Tuple[float, str]:
    text = str(answer_text or "").strip()
    if not text:
        return 0.0, "未記載。聞き手に伝わる形で、観察・判断・対応を短く整理して書くとよい。"

    sentences = re.split(r"[。．\n]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    has_order = any(x in text for x in ["まず", "次に", "その後", "続いて", "優先", "直ちに"])
    has_action = any(x in text for x in ["評価", "観察", "確認", "測定", "連絡", "搬送", "報告", "装着", "実施", "判断"])
    too_short = len(text) < 12
    too_long = len(text) > 180

    score = 0.0
    comments: List[str] = []

    if has_action:
        score += 0.5
    else:
        comments.append("何をするかを具体的にすると伝わりやすい。")

    if has_order or len(sentences) >= 2:
        score += 0.3
    else:
        comments.append("順序がわかる書き方にするとさらに良い。")

    if too_short:
        comments.append("少し短すぎる。観察・判断・対応をもう一言加えるとよい。")
    elif too_long:
        comments.append("やや長い。要点を簡潔にまとめると報告向き。")
    else:
        score += 0.2

    final_comment = " ".join(comments) if comments else "内容は比較的伝わりやすい。"
    return min(score, 1.0), final_comment


def evaluate_free_text_answer(scene: Dict[str, Any], answer_text: str) -> Dict[str, Any]:
    model = build_model_keywords(scene)
    required = model["required"]
    bonus = model["bonus"]

    answer_norm = normalize_text(answer_text)
    matched_required = [kw for kw in required if normalize_text(kw) in answer_norm]
    missed_required = [kw for kw in required if kw not in matched_required]
    matched_bonus = [kw for kw in bonus if normalize_text(kw) in answer_norm]
    weak_items = [kw for kw in bonus if kw not in matched_bonus][:3]

    content_score = 0.0
    if required:
        content_score += (len(matched_required) / len(required)) * 0.8
    if bonus:
        content_score += min(len(matched_bonus) / max(len(bonus), 1), 1.0) * 0.2

    clarity_score, clarity_comment = evaluate_clarity(answer_text)
    total = min(content_score * 0.8 + clarity_score * 0.2, 1.0)

    model_answer_parts: List[str] = []
    if required:
        model_answer_parts.append("必須: " + "、".join(required))
    if bonus:
        model_answer_parts.append("加点: " + "、".join(bonus))
    model_answer_text = " / ".join(model_answer_parts) if model_answer_parts else "理想行動を簡潔にまとめる"

    comment = (
        f"内容点: 必須キーワード {len(matched_required)}/{len(required) if required else 0}、"
        f"加点キーワード {len(matched_bonus)}/{len(bonus) if bonus else 0}。"
        f" 伝達性: {clarity_comment}"
    )

    return {
        "score": total,
        "max_score": 1.0,
        "your_answer": answer_text.strip() if str(answer_text).strip() else "未回答",
        "model_answer": model_answer_text,
        "green_items": matched_required + matched_bonus,
        "yellow_items": weak_items,
        "red_items": missed_required,
        "comment": comment,
    }


# =========================================================
# 採点
# =========================================================
def scene_max_score(case_payload: Dict[str, Any], scene_number: int, scene: Dict[str, Any]) -> float:
    scene_type = get_effective_scene_type(case_payload, scene_number, scene)
    if scene_type == "single_choice":
        return 1.0
    if scene_type == "multiple_choice":
        opts = normalize_options(scene)
        correct_count = sum(1 for o in opts if o["is_correct"])
        return float(correct_count if correct_count > 0 else 1)
    if scene_type == "ranking":
        items = normalize_ranking(scene)
        return float(len(items) if items else 1)
    if scene_type == "template_select":
        return 1.0
    if scene_type == "free_text":
        return 1.0
    return 1.0


def calculate_scene_score(case_payload: Dict[str, Any], scene_number: int, scene: Dict[str, Any], answer_payload: Any) -> float:
    scene_type = get_effective_scene_type(case_payload, scene_number, scene)
    if answer_payload is None:
        return 0.0

    if scene_type == "single_choice":
        opts = normalize_options(scene)
        for opt in opts:
            if opt["label"] == answer_payload and opt["is_correct"]:
                return 1.0
        return 0.0

    if scene_type == "multiple_choice":
        opts = normalize_options(scene)
        selected = set(answer_payload or [])
        score = 0.0
        for opt in opts:
            if opt["is_correct"] and opt["label"] in selected:
                score += 1.0
        wrong_selected = sum(1 for opt in opts if (not opt["is_correct"]) and opt["label"] in selected)
        score -= wrong_selected * 0.5
        return max(score, 0.0)

    if scene_type == "ranking":
        items = normalize_ranking(scene)
        user_order = answer_payload or []
        if not items or not user_order:
            return 0.0

        correct_map = {}
        for idx, item in enumerate(items, start=1):
            if isinstance(item.get("correct_order"), int):
                correct_map[item["label"]] = item["correct_order"]
            else:
                correct_map[item["label"]] = idx

        score = 0.0
        for user_idx, label in enumerate(user_order, start=1):
            if correct_map.get(label) == user_idx:
                score += 1.0
        return score

    if scene_type == "template_select":
        temps = normalize_templates(scene)
        for t in temps:
            if t["label"] == answer_payload and t["is_correct"]:
                return 1.0
        return 0.0

    if scene_type == "free_text":
        return evaluate_free_text_answer(scene, str(answer_payload)).get("score", 0.0)

    return 0.0


def format_correct_answer_text(scene_type: str, scene: Dict[str, Any]) -> str:
    if scene_type == "single_choice":
        opts = normalize_options(scene)
        correct = [o["label"] for o in opts if o["is_correct"]]
        return " / ".join(correct) if correct else "正解設定なし"
    if scene_type == "multiple_choice":
        opts = normalize_options(scene)
        correct = [o["label"] for o in opts if o["is_correct"]]
        return "、".join(correct) if correct else "正解設定なし"
    if scene_type == "ranking":
        items = normalize_ranking(scene)
        if not items:
            return "正解設定なし"
        ordered = sorted(
            items,
            key=lambda x: x["correct_order"] if isinstance(x["correct_order"], int) else 999
        )
        return " → ".join([x["label"] for x in ordered])
    if scene_type == "template_select":
        temps = normalize_templates(scene)
        correct = [t["label"] for t in temps if t["is_correct"]]
        return " / ".join(correct) if correct else "正解設定なし"
    return ""


def evaluate_scene(case_payload: Dict[str, Any], scene_number: int, scene: Dict[str, Any], answer_payload: Any) -> Dict[str, Any]:
    scene_type = get_effective_scene_type(case_payload, scene_number, scene)
    max_score = scene_max_score(case_payload, scene_number, scene)
    score = calculate_scene_score(case_payload, scene_number, scene, answer_payload)

    feedback = {
        "scene_title": str(scene.get("title") or f"Scene {scene_number}"),
        "effective_type": scene_type,
        "score": score,
        "max_score": max_score,
        "score_display": f"{score:.1f} / {max_score:.1f}",
        "your_answer": "未回答",
        "model_answer": "",
        "green_items": [],
        "yellow_items": [],
        "red_items": [],
        "comment": "",
    }

    if scene_type == "free_text":
        free_feedback = evaluate_free_text_answer(scene, str(answer_payload or ""))
        feedback.update(free_feedback)
        feedback["score_display"] = f"{feedback['score']:.1f} / {feedback['max_score']:.1f}"
        return feedback

    if scene_type == "single_choice":
        your = str(answer_payload) if answer_payload else "未回答"
        correct = format_correct_answer_text(scene_type, scene)
        feedback["your_answer"] = your
        feedback["model_answer"] = correct
        if score >= 1.0:
            feedback["green_items"] = [your]
            feedback["comment"] = "選択は適切。"
        else:
            if your != "未回答":
                feedback["yellow_items"] = [your]
            feedback["red_items"] = [correct]
            feedback["comment"] = "正解と自分の選択を見比べて、判断根拠を確認するとよい。"
        return feedback

    if scene_type == "multiple_choice":
        selected = answer_payload or []
        your = "、".join(selected) if selected else "未回答"
        correct_opts = [o["label"] for o in normalize_options(scene) if o["is_correct"]]
        feedback["your_answer"] = your
        feedback["model_answer"] = "、".join(correct_opts)
        feedback["green_items"] = [x for x in selected if x in correct_opts]
        feedback["yellow_items"] = [x for x in selected if x not in correct_opts]
        feedback["red_items"] = [x for x in correct_opts if x not in selected]
        feedback["comment"] = "必要な選択肢が拾えているか、不要な選択をしていないかを確認するとよい。"
        return feedback

    if scene_type == "ranking":
        your_order = answer_payload or []
        correct_text = format_correct_answer_text(scene_type, scene)
        feedback["your_answer"] = " → ".join(your_order) if your_order else "未回答"
        feedback["model_answer"] = correct_text

        items = normalize_ranking(scene)
        correct_map = {}
        for idx, item in enumerate(items, start=1):
            order = item["correct_order"] if isinstance(item.get("correct_order"), int) else idx
            correct_map[item["label"]] = order
        ordered = [x["label"] for x in sorted(items, key=lambda x: correct_map.get(x["label"], 999))]

        green, yellow, red = [], [], []
        for idx, label in enumerate(your_order, start=1):
            if correct_map.get(label) == idx:
                green.append(label)
            else:
                yellow.append(label)
        for label in ordered:
            if label not in your_order:
                red.append(label)

        feedback["green_items"] = green
        feedback["yellow_items"] = yellow
        feedback["red_items"] = red
        feedback["comment"] = "優先順位のズレに注目して、最初に何を置くべきかを確認するとよい。"
        return feedback

    if scene_type == "template_select":
        your = str(answer_payload) if answer_payload else "未回答"
        correct = format_correct_answer_text(scene_type, scene)
        feedback["your_answer"] = your
        feedback["model_answer"] = correct
        if score >= 1.0:
            feedback["green_items"] = ["報告内容は適切"]
            feedback["comment"] = "必要事項がまとまっている。"
        else:
            if your != "未回答":
                feedback["yellow_items"] = ["選択したテンプレ"]
            feedback["red_items"] = ["年齢 / 主訴 / 状態 / 疑い病態 / 依頼内容を簡潔に"]
            feedback["comment"] = "申し送りは、相手が一度で状況をつかめる内容にするとよい。"
        return feedback

    return feedback


# =========================================================
# 画面用補助
# =========================================================
def render_progress(current_index: int, total_count: int) -> None:
    ratio = 0 if total_count <= 0 else (current_index + 1) / total_count
    ratio = max(0.0, min(1.0, ratio))
    st.markdown(
        f"""
        <div class="progress-wrap">
            <div class="progress-label">
                <span>進行状況</span>
                <span>{current_index + 1} / {total_count}</span>
            </div>
            <div class="progress-track">
                <div class="progress-fill" style="width:{ratio * 100:.1f}%"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_visible_scenes(case_payload: Dict[str, Any]) -> List[Tuple[int, Dict[str, Any]]]:
    all_scenes = case_payload["scenes"]
    return [(idx, scene) for idx, scene in enumerate(all_scenes[:DEFAULT_SCENE_COUNT], start=1)]


def get_scene_key(case_id: str, scene_number: int) -> str:
    return f"{case_id}__scene_{scene_number}"


def get_feedback_key(case_id: str, scene_number: int) -> str:
    return f"{case_id}__feedback_{scene_number}"


def get_answer_for_scene(case_id: str, scene_number: int) -> Any:
    return st.session_state.answers.get(get_scene_key(case_id, scene_number))


def set_answer_for_scene(case_id: str, scene_number: int, value: Any) -> None:
    st.session_state.answers[get_scene_key(case_id, scene_number)] = value


def set_feedback_for_scene(case_id: str, scene_number: int, value: Dict[str, Any]) -> None:
    st.session_state.feedbacks[get_feedback_key(case_id, scene_number)] = value


def get_feedback_for_scene(case_id: str, scene_number: int) -> Optional[Dict[str, Any]]:
    return st.session_state.feedbacks.get(get_feedback_key(case_id, scene_number))


def recalc_total_score(case_payload: Dict[str, Any]) -> None:
    visible_scenes = get_visible_scenes(case_payload)
    total = 0.0
    total_max = 0.0
    case_id = case_payload["case_id"]

    for scene_number, scene in visible_scenes:
        answer_payload = get_answer_for_scene(case_id, scene_number)
        score = calculate_scene_score(case_payload, scene_number, scene, answer_payload)
        total += score
        total_max += scene_max_score(case_payload, scene_number, scene)
        feedback = evaluate_scene(case_payload, scene_number, scene, answer_payload)
        set_feedback_for_scene(case_id, scene_number, feedback)

    st.session_state.score_total = total
    st.session_state.score_max = total_max


def score_percent() -> float:
    if st.session_state.score_max <= 0:
        return 0.0
    return st.session_state.score_total / st.session_state.score_max * 100.0


def rank_info(percent: float) -> Tuple[str, str, str]:
    if percent >= 85:
        return "秀才", "✨", "優先順位づけがかなり良い。この調子で現場の流れを固めよう。"
    if percent >= 70:
        return "優秀", "👏", "大枠は良い。細かい判断をもう一段磨くとさらに強くなる。"
    if percent >= 50:
        return "良好", "👍", "流れは追えている。次は優先行動をもう少し整理しよう。"
    return "要復習", "📝", "最初の観察と重症度判断のつながりをもう一度確認しよう。"


def stringify_visible_data(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        vals = []
        for v in value:
            vals.extend(to_text_lines(v))
        return "\n".join([f"・{x}" for x in vals if x])
    if isinstance(value, dict):
        return "\n".join([f"{VISIBLE_DATA_LABELS.get(str(k), str(k))}：{v}" for k, v in value.items()])
    return str(value)


def first_learning_goal(case_payload: Dict[str, Any]) -> str:
    scenes = case_payload["scenes"]
    if scenes:
        first = scenes[0]
        for k in ["scene_goal", "learning_goal", "goal"]:
            if first.get(k):
                return str(first.get(k))
    return ""


def get_hint_text(scene: Dict[str, Any]) -> str:
    candidates = [
        scene.get("hint"),
        scene.get("hints"),
        scene.get("ideal_flow"),
        scene.get("action_tag"),
    ]
    for c in candidates:
        if c:
            if isinstance(c, list):
                return "\n".join([f"・{str(x)}" for x in c])
            return str(c)
    return "この場面では、重症度・緊急度と優先行動のつながりに注目して考えてみよう。"


# =========================================================
# 画面遷移
# =========================================================
def go_to(screen: str) -> None:
    st.session_state.screen = screen
    rerun_with_scroll_top()


# =========================================================
# ranking UI
# =========================================================
def get_ranking_state_key(case_id: str, scene_number: int) -> str:
    return f"ranking_order__{case_id}__{scene_number}"


def initialize_ranking_order(scene: Dict[str, Any], case_id: str, scene_number: int) -> List[str]:
    items = normalize_ranking(scene)
    default_labels = [x["label"] for x in items]
    state_key = get_ranking_state_key(case_id, scene_number)
    saved_answer = get_answer_for_scene(case_id, scene_number)

    if state_key not in st.session_state:
        if isinstance(saved_answer, list) and saved_answer:
            known = [x for x in saved_answer if x in default_labels]
            unknown = [x for x in default_labels if x not in known]
            st.session_state[state_key] = known + unknown
        else:
            st.session_state[state_key] = default_labels.copy()

    current = st.session_state[state_key]
    current = [x for x in current if x in default_labels]
    for label in default_labels:
        if label not in current:
            current.append(label)
    st.session_state[state_key] = current
    return current


def move_ranking_item(case_id: str, scene_number: int, index: int, direction: int) -> None:
    state_key = get_ranking_state_key(case_id, scene_number)
    current = list(st.session_state.get(state_key, []))
    target = index + direction
    if target < 0 or target >= len(current):
        return
    current[index], current[target] = current[target], current[index]
    st.session_state[state_key] = current
    set_answer_for_scene(case_id, scene_number, current)


# =========================================================
# Cover / Level / Random
# =========================================================
def render_cover(cases: List[Dict[str, Any]]) -> None:
    ensure_level_data(cases)

    st.markdown(
        f"""
        <div class="app-hero">
            <h1>{html_escape(APP_TITLE)}</h1>
            <p>
                症例を通して、観察 → 判断 → 優先順位づけ → 伝わる報告 を練習するシミュレーションです。<br>
                Levelが上がるほど、記述式の場面が増えます。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    total_cases = len(cases)
    level_count = len(st.session_state.level_case_map)

    cols = st.columns(3)
    cols[0].markdown(
        f"""
        <div class="summary-box">
            <div class="big">{total_cases}</div>
            <div class="small">総症例数</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols[1].markdown(
        f"""
        <div class="summary-box">
            <div class="big">{level_count}</div>
            <div class="small">Level数</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols[2].markdown(
        """
        <div class="summary-box">
            <div class="big">7</div>
            <div class="small">1症例あたり場面数</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">モードを選ぶ</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            <div class="soft-panel">
                <div class="case-main">Level選択</div>
                <div class="case-sub">10症例ごと。1症例ずつ出題。Levelが上がるほど記述式が増える。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Levelから始める", type="primary", use_container_width=True):
            st.session_state.selected_mode = "level"
            go_to("level_select")

    with col2:
        st.markdown(
            """
            <div class="soft-panel">
                <div class="case-main">全問題ランダム</div>
                <div class="case-sub">一覧なし。1症例ずつランダム出題。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("全問題ランダムで始める", use_container_width=True):
            st.session_state.selected_mode = "all_random"
            st.session_state.selected_level_name = None
            start_all_random_first_case(cases)


def render_level_select(cases: List[Dict[str, Any]]) -> None:
    ensure_level_data(cases)
    st.markdown('<div class="section-title">Levelを選択</div>', unsafe_allow_html=True)

    for level_name, case_ids in st.session_state.level_case_map.items():
        free_text_count = get_free_text_count_for_level(level_name)
        st.markdown(
            f"""
            <div class="soft-panel">
                <div class="scene-header">
                    <div class="case-main">{html_escape(level_name)}</div>
                    <div class="mode-pill level">10症例</div>
                    <div class="level-pill">記述式 {free_text_count}場面</div>
                </div>
                <div class="case-sub">カテゴリ混在で1症例ずつ出題</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"{level_name} を開始", key=f"level_{level_name}", type="primary", use_container_width=True):
            st.session_state.selected_mode = "level"
            st.session_state.selected_level_name = level_name
            start_selected_level_first_case(cases)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("症例順をシャッフルし直す", use_container_width=True):
            reshuffle_current_orders(cases)
            rerun_with_scroll_top()
    with col2:
        if st.button("表紙に戻る", use_container_width=True):
            go_to("cover")


# =========================================================
# Intro
# =========================================================
def render_intro(case_payload: Dict[str, Any]) -> None:
    card = case_payload["card_info"]
    mode = st.session_state.selected_mode

    mode_html = '<div class="mode-pill random">全問題ランダム</div>' if mode == "all_random" else f'<div class="mode-pill level">{html_escape(st.session_state.selected_level_name or "Level")}</div>'

    pos, total = get_current_case_position(mode)
    progress_html = f'<div class="progress-pill">症例 {pos} / {total}</div>' if total > 0 else ""

    st.markdown('<div class="section-title">症例開始</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="case-card">
            <div class="scene-header">
                {mode_html}
                {progress_html}
            </div>
            <div class="case-main">{html_escape(card["age"])}{html_escape(card["sex"])}、{html_escape(card["chief_complaint"])}</div>
            <div class="case-sub">{html_escape(case_payload["field_label"])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    free_text_count = len(get_free_text_scene_numbers(case_payload))
    st.markdown(
        f"""
        <div class="soft-panel">
            <b>今回の進め方</b><br>
            7場面で進行。記述式の場面数：{free_text_count}<br>
            記述式はキーワードと伝達性で採点する。
        </div>
        """,
        unsafe_allow_html=True,
    )

    goal = first_learning_goal(case_payload)
    if goal:
        st.markdown(
            f"""
            <div class="goal-box">
                <b>学習目標</b><br>
                {html_escape(goal).replace(chr(10), "<br>")}
            </div>
            """,
            unsafe_allow_html=True,
        )

    if case_payload["summary"]:
        st.markdown(
            f"""
            <div class="soft-panel">
                <b>症例概要</b><br>
                {html_escape(case_payload["summary"]).replace(chr(10), "<br>")}
            </div>
            """,
            unsafe_allow_html=True,
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("この症例を開始する", type="primary", use_container_width=True):
            go_to("scene")
    with col2:
        if mode == "level":
            if st.button("Level選択へ戻る", use_container_width=True):
                go_to("level_select")
        else:
            if st.button("表紙に戻る", use_container_width=True):
                go_to("cover")


# =========================================================
# 各入力UI
# =========================================================
def render_single_choice(scene: Dict[str, Any], case_id: str, scene_number: int) -> None:
    options = normalize_options(scene)
    labels = [o["label"] for o in options]
    saved = get_answer_for_scene(case_id, scene_number)

    default_index = None
    if saved in labels:
        default_index = labels.index(saved)

    selected = st.radio(
        "選択肢",
        labels,
        index=default_index if default_index is not None else None,
        key=f"radio_{case_id}_{scene_number}",
    )
    set_answer_for_scene(case_id, scene_number, selected)


def render_multiple_choice(scene: Dict[str, Any], case_id: str, scene_number: int) -> None:
    options = normalize_options(scene)
    saved = get_answer_for_scene(case_id, scene_number) or []

    current = []
    st.markdown("**選択肢（複数選択可）**")
    for i, opt in enumerate(options):
        checked = opt["label"] in saved
        val = st.checkbox(
            opt["label"],
            value=checked,
            key=f"multi_{case_id}_{scene_number}_{i}",
        )
        if val:
            current.append(opt["label"])

    set_answer_for_scene(case_id, scene_number, current)


def render_ranking(scene: Dict[str, Any], case_id: str, scene_number: int) -> None:
    order = initialize_ranking_order(scene, case_id, scene_number)

    st.markdown(
        """
        <div class="muted">
            優先順位順に並べる。1行目が最優先。スマホでは ↑ ↓ を押して並べ替える。
        </div>
        """,
        unsafe_allow_html=True,
    )

    for idx, label in enumerate(order):
        row1, row2, row3 = st.columns([0.14, 0.14, 0.72], vertical_alignment="center")
        with row1:
            st.markdown(f"**{idx + 1}**")
        with row2:
            up_col, down_col = st.columns(2)
            with up_col:
                if st.button("↑", key=f"rank_up_{case_id}_{scene_number}_{idx}", disabled=(idx == 0), use_container_width=True):
                    move_ranking_item(case_id, scene_number, idx, -1)
                    rerun_with_scroll_top()
            with down_col:
                if st.button("↓", key=f"rank_down_{case_id}_{scene_number}_{idx}", disabled=(idx == len(order) - 1), use_container_width=True):
                    move_ranking_item(case_id, scene_number, idx, 1)
                    rerun_with_scroll_top()
        with row3:
            st.markdown(
                f"""
                <div class="soft-panel" style="margin-bottom:6px; padding:10px 12px;">
                    {html_escape(label)}
                </div>
                """,
                unsafe_allow_html=True,
            )

    set_answer_for_scene(case_id, scene_number, st.session_state[get_ranking_state_key(case_id, scene_number)])


def render_template_select(scene: Dict[str, Any], case_id: str, scene_number: int) -> None:
    templates = normalize_templates(scene)
    labels = [t["label"] for t in templates]
    saved = get_answer_for_scene(case_id, scene_number)

    default_index = None
    if saved in labels:
        default_index = labels.index(saved)

    selected = st.radio(
        "テンプレート",
        labels,
        index=default_index if default_index is not None else None,
        key=f"template_{case_id}_{scene_number}",
    )
    set_answer_for_scene(case_id, scene_number, selected)


def render_free_text(scene: Dict[str, Any], case_id: str, scene_number: int) -> None:
    saved = get_answer_for_scene(case_id, scene_number) or ""
    answer = st.text_area(
        "回答を記載",
        value=saved,
        height=160,
        key=f"free_text_{case_id}_{scene_number}",
        placeholder="例：まず意識・呼吸・循環を初期評価し、次に...",
    )
    set_answer_for_scene(case_id, scene_number, answer)


def render_scene_input(case_payload: Dict[str, Any], scene_number: int, scene: Dict[str, Any]) -> None:
    scene_type = get_effective_scene_type(case_payload, scene_number, scene)
    prompt = scene.get("prompt") or "この場面で実施する行動を選ぶ"

    st.markdown(
        f"""
        <div class="soft-panel">
            <b>{html_escape(prompt)}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

    case_id = case_payload["case_id"]

    if scene_type == "single_choice":
        render_single_choice(scene, case_id, scene_number)
    elif scene_type == "multiple_choice":
        render_multiple_choice(scene, case_id, scene_number)
    elif scene_type == "ranking":
        render_ranking(scene, case_id, scene_number)
    elif scene_type == "template_select":
        render_template_select(scene, case_id, scene_number)
    elif scene_type == "free_text":
        render_free_text(scene, case_id, scene_number)
    else:
        render_single_choice(scene, case_id, scene_number)


# =========================================================
# Scene / Hint / Debrief
# =========================================================
def render_media(scene: Dict[str, Any]) -> None:
    media = scene.get("media")
    media_path = find_media_path(media)
    if media_path:
        st.image(str(media_path), use_container_width=True)


def render_scene(case_payload: Dict[str, Any]) -> None:
    visible_scenes = get_visible_scenes(case_payload)
    total_scenes = len(visible_scenes)
    idx = max(0, min(st.session_state.scene_display_index, total_scenes - 1))
    scene_number, scene = visible_scenes[idx]

    render_progress(idx, total_scenes)

    title = html_escape(scene.get("title") or f"Scene {scene_number}")
    phase = scene.get("phase")
    phase_html = f'<div class="scene-phase">{html_escape(phase)}</div>' if phase else ""
    level_tag = ""
    if scene_number in get_free_text_scene_numbers(case_payload):
        level_tag = '<div class="level-pill">この場面は記述式</div>'

    pos, total = get_current_case_position(st.session_state.selected_mode)
    progress_html = f'<div class="progress-pill">症例 {pos} / {total}</div>' if total > 0 else ""

    st.markdown(
        f"""
        <div class="scene-card">
            <div class="scene-header">
                <div class="scene-title">{title}</div>
                {phase_html}
                {level_tag}
                {progress_html}
            </div>
        """,
        unsafe_allow_html=True,
    )

    text = str(scene.get("text", "")).strip()
    if text:
        st.markdown(
            f"""
            <div class="report-box">
                <div class="label">通報内容 / 場面情報</div>
                <div class="body">{html_escape(text)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    visible_data_text = stringify_visible_data(scene.get("visible_data"))
    if visible_data_text:
        st.markdown(
            f"""
            <div class="observation-box">
                <div class="label">観察所見</div>
                <div class="body">{html_escape(visible_data_text)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    render_media(scene)
    st.markdown("</div>", unsafe_allow_html=True)

    col_hint, col_show = st.columns([1, 2])
    with col_hint:
        if st.button("ヒントを見る", key=f"hint_btn_{case_payload['case_id']}_{scene_number}", use_container_width=True):
            st.session_state.hint_from_scene_index = idx
            go_to("hint")
    with col_show:
        st.markdown('<div class="muted">必要なときだけヒントを見る。まずは自分で考える。</div>', unsafe_allow_html=True)

    render_scene_input(case_payload, scene_number, scene)

    nav1, nav2, nav3 = st.columns(3)
    with nav1:
        if st.button("前へ", disabled=(idx <= 0), use_container_width=True):
            st.session_state.scene_display_index -= 1
            rerun_with_scroll_top()
    with nav2:
        if st.session_state.selected_mode == "level":
            if st.button("Level選択へ戻る", use_container_width=True):
                go_to("level_select")
        else:
            if st.button("表紙に戻る", use_container_width=True):
                go_to("cover")
    with nav3:
        next_label = "ふりかえりへ" if idx >= total_scenes - 1 else "次へ"
        if st.button(next_label, type="primary", use_container_width=True):
            recalc_total_score(case_payload)
            if idx >= total_scenes - 1:
                go_to("debrief")
            else:
                st.session_state.scene_display_index += 1
                rerun_with_scroll_top()


def render_hint(case_payload: Dict[str, Any]) -> None:
    visible_scenes = get_visible_scenes(case_payload)
    idx = st.session_state.hint_from_scene_index
    if idx is None:
        idx = st.session_state.scene_display_index
    idx = max(0, min(idx, len(visible_scenes) - 1))
    scene_number, scene = visible_scenes[idx]
    title = html_escape(scene.get("title") or f"Scene {scene_number}")
    hint_text = html_escape(get_hint_text(scene)).replace(chr(10), "<br>")

    st.markdown('<div class="section-title">ヒント</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="hint-card">
            <div class="scene-title">{title}</div>
            <div class="hint-box">{hint_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("元の場面へ戻る", type="primary", use_container_width=True):
            go_to("scene")
    with col2:
        if st.session_state.selected_mode == "level":
            if st.button("Level選択へ戻る", use_container_width=True):
                go_to("level_select")
        else:
            if st.button("表紙に戻る", use_container_width=True):
                go_to("cover")


def render_review_block(title: str, css_class: str, items: List[str], empty_text: str) -> None:
    body = "<br>".join([f"・{html_escape(x)}" for x in items]) if items else html_escape(empty_text)
    st.markdown(
        f"""
        <div class="review-block {css_class}">
            <div class="review-title">{html_escape(title)}</div>
            <div>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_debrief(case_payload: Dict[str, Any], cases: List[Dict[str, Any]]) -> None:
    recalc_total_score(case_payload)
    percent = score_percent()
    rank_name, rank_icon, rank_comment = rank_info(percent)
    debrief = case_payload.get("debriefing", {}) or {}

    pos, total = get_current_case_position(st.session_state.selected_mode)
    progress_html = f'<div class="progress-pill">症例 {pos} / {total}</div>' if total > 0 else ""

    st.markdown('<div class="section-title">ふりかえり</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="case-card">
            <div class="scene-header">
                <div class="case-main">{html_escape(rank_icon)} {html_escape(rank_name)}</div>
                {progress_html}
            </div>
            <div class="summary-grid">
                <div class="summary-box">
                    <div class="big">{percent:.0f}%</div>
                    <div class="small">到達度</div>
                </div>
                <div class="summary-box">
                    <div class="big">{st.session_state.score_total:.1f}</div>
                    <div class="small">獲得スコア</div>
                </div>
                <div class="summary-box">
                    <div class="big">{st.session_state.score_max:.1f}</div>
                    <div class="small">満点</div>
                </div>
            </div>
            <div class="case-sub" style="margin-top:10px;">{html_escape(rank_comment)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if debrief.get("summary"):
        st.markdown(
            f"""
            <div class="review-block review-blue">
                <div class="review-title">今回の要点</div>
                <div>{html_escape(str(debrief["summary"])).replace(chr(10), "<br>")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">場面ごとの復習</div>', unsafe_allow_html=True)
    for scene_number, scene in get_visible_scenes(case_payload):
        feedback = get_feedback_for_scene(case_payload["case_id"], scene_number)
        if not feedback:
            feedback = evaluate_scene(case_payload, scene_number, scene, get_answer_for_scene(case_payload["case_id"], scene_number))
            set_feedback_for_scene(case_payload["case_id"], scene_number, feedback)

        title = feedback["scene_title"]
        score_display = feedback["score_display"]
        input_type_text = {
            "single_choice": "選択式",
            "multiple_choice": "複数選択",
            "ranking": "優先順位",
            "template_select": "テンプレ選択",
            "free_text": "記述式",
        }.get(feedback["effective_type"], feedback["effective_type"])

        st.markdown(
            f"""
            <div class="review-card">
                <div class="scene-header">
                    <div class="scene-title">{html_escape(title)}</div>
                    <span class="score-chip">{html_escape(score_display)}</span>
                    <span class="scene-phase">{html_escape(input_type_text)}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="review-block review-blue">
                <div class="review-title">あなたの回答</div>
                <div>{html_escape(feedback["your_answer"]).replace(chr(10), "<br>")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="review-block review-blue">
                <div class="review-title">模範の方向性</div>
                <div>{html_escape(feedback["model_answer"]).replace(chr(10), "<br>")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        render_review_block("緑：合っていた要素", "review-green", feedback.get("green_items", []), "該当なし")
        render_review_block("黄：弱い要素 / 位置ズレ", "review-yellow", feedback.get("yellow_items", []), "該当なし")
        render_review_block("赤：不足 / 優先順位ミス", "review-red", feedback.get("red_items", []), "該当なし")

        st.markdown(
            f"""
            <div class="review-block review-blue">
                <div class="review-title">コメント</div>
                <div>{html_escape(feedback.get("comment", "")).replace(chr(10), "<br>")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("同じ症例をもう一度", type="primary", use_container_width=True):
            reset_case_progress()
            go_to("intro")
    with col2:
        if st.session_state.selected_mode == "level":
            if st.button("次の症例へ", use_container_width=True):
                move_to_next_case_in_level(cases)
        else:
            if st.button("次の症例へ", use_container_width=True):
                move_to_next_case_in_random(cases)


def render_level_complete() -> None:
    level_name = st.session_state.selected_level_name or "Level"
    st.markdown(
        f"""
        <div class="section-title">{html_escape(level_name)} クリア</div>
        <div class="soft-panel">
            <div class="case-main">このLevelの症例が終わったよ。</div>
            <div class="case-sub">次のLevelに進むか、シャッフルしてもう一度挑戦できる。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Level選択へ戻る", type="primary", use_container_width=True):
            go_to("level_select")
    with col2:
        if st.button("表紙に戻る", use_container_width=True):
            go_to("cover")


def render_random_complete() -> None:
    st.markdown(
        """
        <div class="section-title">全問題ランダム クリア</div>
        <div class="soft-panel">
            <div class="case-main">ランダム出題が終わったよ。</div>
            <div class="case-sub">シャッフルしてもう一度挑戦するか、表紙へ戻れる。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("シャッフルしてもう一度", type="primary", use_container_width=True):
            st.session_state.random_progress_index = 0
            st.session_state.selected_case_id = None
            st.session_state.screen = "cover"
            rerun_with_scroll_top()
    with col2:
        if st.button("表紙に戻る", use_container_width=True):
            go_to("cover")


# =========================================================
# メイン
# =========================================================
def main() -> None:
    inject_css()
    init_state()
    render_scroll_anchor()
    trigger_scroll_top_if_needed()

    cases = load_all_cases()
    if not cases:
        st.error("cases フォルダ内に症例JSONが見つからない。")
        st.stop()

    current_case = None
    if st.session_state.selected_case_id:
        current_case = get_case_by_id(cases, st.session_state.selected_case_id)

    screen = st.session_state.screen
    if screen == "cover":
        render_cover(cases)

    elif screen == "level_select":
        render_level_select(cases)

    elif screen == "level_complete":
        render_level_complete()

    elif screen == "random_complete":
        render_random_complete()

    elif screen in {"intro", "scene", "hint", "debrief"}:
        if not current_case:
            st.warning("症例が選択されていない。")
            if st.button("表紙に戻る", use_container_width=True):
                go_to("cover")
            st.stop()

        if screen == "intro":
            render_intro(current_case)
        elif screen == "scene":
            render_scene(current_case)
        elif screen == "hint":
            render_hint(current_case)
        elif screen == "debrief":
            render_debrief(current_case, cases)
    else:
        go_to("cover")


if __name__ == "__main__":
    main()