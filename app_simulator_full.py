import re
import json
import copy
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

DIFFICULTY_ORDER = ["Easy", "Normal", "Hard"]
DIFFICULTY_LABELS = {
    "Easy": "Easy（入門）",
    "Normal": "Normal（標準）",
    "Hard": "Hard（実践）",
}

SCENE_MAP = {
    "Easy": [1, 3, 5, 7],
    "Normal": [1, 2, 3, 4, 5, 6, 7],
    "Hard": [1, 2, 3, 4, 5, 6, 7],
}

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


# =========================================================
# HTMLエスケープ
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

        .field-card, .case-card, .scene-card, .hint-card, .debrief-card {
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 16px 16px;
            box-shadow: var(--shadow);
            margin-bottom: 12px;
        }

        .field-card {
            min-height: 108px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
        }

        .field-title {
            font-size: 1.08rem;
            font-weight: 700;
            margin-bottom: 6px;
            color: var(--text);
        }

        .field-sub {
            color: var(--muted);
            font-size: 0.92rem;
        }

        .difficulty-pill {
            display: inline-block;
            border-radius: 999px;
            padding: 5px 11px;
            font-size: 0.82rem;
            font-weight: 700;
            margin-bottom: 10px;
            color: white;
        }

        .difficulty-pill.easy { background: var(--green); }
        .difficulty-pill.normal { background: var(--orange); }
        .difficulty-pill.hard { background: var(--red); }

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

        .caution-box {
            border-left: 5px solid var(--red);
            background: var(--red-soft);
            border-radius: 12px;
            padding: 12px 14px;
            margin: 10px 0 14px 0;
        }

        .good-box {
            border-left: 5px solid var(--green);
            background: var(--green-soft);
            border-radius: 12px;
            padding: 12px 14px;
            margin: 10px 0 14px 0;
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

        .scene-phase {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: var(--gray-soft);
            color: var(--text);
            font-size: 0.82rem;
            font-weight: 700;
        }

        .report-box {
            background: #eaf2ff;
            border-left: 6px solid #1f5fbf;
            border-radius: 14px;
            padding: 14px 16px;
            margin: 12px 0;
        }

        .report-box .label {
            font-size: 0.82rem;
            font-weight: 800;
            color: #1f5fbf;
            margin-bottom: 6px;
            letter-spacing: 0.03em;
        }

        .report-box .body {
            font-size: 1.08rem;
            font-weight: 700;
            line-height: 1.8;
            color: #162338;
            white-space: pre-wrap;
        }

        .observation-box {
            background: #fff8e1;
            border-left: 6px solid #ef6c00;
            border-radius: 14px;
            padding: 14px 16px;
            margin: 12px 0;
        }

        .observation-box .label {
            font-size: 0.82rem;
            font-weight: 800;
            color: #ef6c00;
            margin-bottom: 6px;
            letter-spacing: 0.03em;
        }

        .observation-box .body {
            font-size: 1.04rem;
            font-weight: 700;
            line-height: 1.85;
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

        .ranking-help {
            font-size: 0.92rem;
            color: var(--muted);
            margin-bottom: 8px;
        }

        .ranking-row {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 10px 12px;
            margin-bottom: 8px;
            box-shadow: 0 4px 14px rgba(20,35,56,0.04);
        }

        .ranking-number {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            border-radius: 999px;
            background: var(--blue-soft);
            color: var(--blue);
            font-weight: 800;
            font-size: 0.95rem;
        }

        .ranking-label {
            font-weight: 700;
            line-height: 1.5;
            color: var(--text);
        }

        .rank-btn > button {
            min-height: 2.6rem !important;
            padding: 0.25rem 0.5rem !important;
            font-size: 1.1rem !important;
            border-radius: 12px !important;
        }

        .debrief-wrap {
            font-family: "Hiragino Sans", "BIZ UDPGothic", "Yu Gothic UI", "Meiryo", sans-serif !important;
        }

        .debrief-rank-card {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 24px;
            padding: 22px 20px;
            box-shadow: 0 16px 40px rgba(20,35,56,0.10);
            margin-bottom: 14px;
            position: relative;
            overflow: hidden;
        }

        .debrief-rank-card::after {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(120deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.35) 50%, rgba(255,255,255,0) 100%);
            transform: translateX(-120%);
            animation: shineSweep 3.8s ease-in-out infinite;
            pointer-events: none;
        }

        .debrief-rank-card.rank-shusai {
            border-top: 6px solid #2e7d32;
            animation: trophyPop 0.9s ease-out;
        }

        .debrief-rank-card.rank-yushu {
            border-top: 6px solid #1f5fbf;
            animation: floatFade 0.8s ease-out;
        }

        .debrief-rank-card.rank-ryoko {
            border-top: 6px solid #ef6c00;
            animation: softRise 0.7s ease-out;
        }

        .debrief-rank-card.rank-review {
            border-top: 6px solid #c62828;
            animation: gentleShake 0.55s ease-out;
        }

        .debrief-rank-top {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 10px;
        }

        .debrief-rank-icon {
            font-size: 2.2rem;
            line-height: 1;
        }

        .debrief-rank-name {
            font-size: 1.45rem;
            font-weight: 900;
            line-height: 1.2;
        }

        .debrief-rank-comment {
            margin-top: 8px;
            font-size: 1.02rem;
            line-height: 1.8;
            color: var(--text);
            font-weight: 700;
        }

        .debrief-blue-panel,
        .debrief-green-panel,
        .debrief-red-panel,
        .debrief-orange-panel {
            border-radius: 18px;
            padding: 16px 18px;
            margin-bottom: 12px;
            border: 1px solid var(--line);
            box-shadow: var(--shadow);
            font-family: "Hiragino Sans", "BIZ UDPGothic", "Yu Gothic UI", "Meiryo", sans-serif !important;
        }

        .debrief-blue-panel {
            background: var(--blue-soft);
            border-left: 6px solid var(--blue);
        }

        .debrief-green-panel {
            background: var(--green-soft);
            border-left: 6px solid var(--green);
        }

        .debrief-red-panel {
            background: var(--red-soft);
            border-left: 6px solid var(--red);
        }

        .debrief-orange-panel {
            background: var(--orange-soft);
            border-left: 6px solid var(--orange);
        }

        .debrief-panel-title {
            font-size: 0.9rem;
            font-weight: 900;
            letter-spacing: 0.03em;
            margin-bottom: 7px;
        }

        .debrief-panel-body {
            font-size: 1.02rem;
            line-height: 1.85;
            font-weight: 700;
            white-space: pre-wrap;
        }

        @keyframes trophyPop {
            0% { transform: scale(0.92) translateY(10px); opacity: 0; }
            55% { transform: scale(1.03) translateY(0); opacity: 1; }
            100% { transform: scale(1.00) translateY(0); opacity: 1; }
        }

        @keyframes floatFade {
            0% { transform: translateY(16px); opacity: 0; }
            100% { transform: translateY(0); opacity: 1; }
        }

        @keyframes softRise {
            0% { transform: translateY(10px); opacity: 0; }
            100% { transform: translateY(0); opacity: 1; }
        }

        @keyframes gentleShake {
            0% { transform: translateX(0); }
            20% { transform: translateX(-4px); }
            40% { transform: translateX(4px); }
            60% { transform: translateX(-3px); }
            80% { transform: translateX(3px); }
            100% { transform: translateX(0); }
        }

        @keyframes shineSweep {
            0% { transform: translateX(-120%); }
            35% { transform: translateX(120%); }
            100% { transform: translateX(120%); }
        }

        div[data-testid="stRadio"] label,
        div[data-testid="stCheckbox"] label,
        div[data-testid="stMultiSelect"] label,
        .stRadio label,
        .stCheckbox label,
        .stMarkdown,
        p, li, span {
            color: var(--text) !important;
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

        .stButton > button {
            width: 100%;
            min-height: 3rem;
            border-radius: 14px;
            font-weight: 700;
            border: 1px solid #cfd8e6;
        }

        .tiny-space {
            height: 4px;
        }

        @media (max-width: 768px) {
            .app-hero {
                padding: 18px 16px;
                border-radius: 16px;
            }

            .app-hero h1 {
                font-size: 1.45rem;
            }

            .scene-title {
                font-size: 1.02rem;
            }

            .summary-grid {
                grid-template-columns: 1fr;
            }

            .field-card, .case-card, .scene-card, .hint-card, .debrief-card {
                padding: 14px;
                border-radius: 16px;
            }

            .report-box .body {
                font-size: 1.02rem;
            }

            .observation-box .body {
                font-size: 1.0rem;
            }

            .debrief-rank-name {
                font-size: 1.2rem;
            }

            .debrief-rank-comment,
            .debrief-panel-body {
                font-size: 0.98rem;
            }

            .ranking-number {
                width: 28px;
                height: 28px;
                font-size: 0.88rem;
            }

            .rank-btn > button {
                min-height: 2.8rem !important;
                font-size: 1rem !important;
            }
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
        "selected_field": None,
        "selected_difficulty": "Normal",
        "selected_case_id": None,
        "scene_display_index": 0,
        "answers": {},
        "score_total": 0.0,
        "score_max": 0.0,
        "hint_from_scene_index": None,
        "pending_scroll_top": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_case_progress() -> None:
    st.session_state.scene_display_index = 0
    st.session_state.answers = {}
    st.session_state.score_total = 0.0
    st.session_state.score_max = 0.0
    st.session_state.hint_from_scene_index = None

    ranking_keys = [k for k in list(st.session_state.keys()) if str(k).startswith("ranking_order__")]
    for k in ranking_keys:
        del st.session_state[k]


# =========================================================
# JSON / Case 読み込み
# =========================================================
def normalize_difficulty(value: Any) -> str:
    if not value:
        return "Normal"
    text = str(value).strip().lower()
    if text in {"easy", "beginner", "入門"}:
        return "Easy"
    if text in {"hard", "expert", "実践"}:
        return "Hard"
    return "Normal"


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

    candidates = [
        data.get("summary", ""),
        data.get("title", ""),
    ]

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

    difficulty = normalize_difficulty(data.get("difficulty"))
    if difficulty not in DIFFICULTY_ORDER:
        difficulty = "Normal"

    card_info = extract_case_card_info(data, path)

    case_id = data.get("case_id") or data.get("id") or path.stem
    title = str(data.get("title") or path.stem)

    return {
        "case_id": str(case_id),
        "path": path,
        "field_key": field_key,
        "field_label": field_label,
        "difficulty": difficulty,
        "difficulty_label": DIFFICULTY_LABELS[difficulty],
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
# 選択肢・採点
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
    }
    return aliases.get(t, "single_choice")


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


def scene_max_score(scene: Dict[str, Any]) -> float:
    scene_type = normalize_scene_type(scene)

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
    return 1.0


def calculate_scene_score(scene: Dict[str, Any], answer_payload: Any) -> float:
    scene_type = normalize_scene_type(scene)

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

    return 0.0


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


def get_visible_scene_numbers(difficulty: str) -> List[int]:
    return SCENE_MAP.get(difficulty, [1, 2, 3, 4, 5, 6, 7])


def get_visible_scenes(case_payload: Dict[str, Any], difficulty: str) -> List[Tuple[int, Dict[str, Any]]]:
    all_scenes = case_payload["scenes"]
    wanted = get_visible_scene_numbers(difficulty)
    visible = []
    for n in wanted:
        idx = n - 1
        if 0 <= idx < len(all_scenes):
            visible.append((n, all_scenes[idx]))
    return visible


def field_counts(cases: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {}
    for c in cases:
        counts[c["field_key"]] = counts.get(c["field_key"], 0) + 1
    return counts


def get_scene_key(case_id: str, scene_number: int) -> str:
    return f"{case_id}__scene_{scene_number}"


def get_answer_for_scene(case_id: str, scene_number: int) -> Any:
    return st.session_state.answers.get(get_scene_key(case_id, scene_number))


def set_answer_for_scene(case_id: str, scene_number: int, value: Any) -> None:
    st.session_state.answers[get_scene_key(case_id, scene_number)] = value


def recalc_total_score(case_payload: Dict[str, Any], difficulty: str) -> None:
    visible_scenes = get_visible_scenes(case_payload, difficulty)
    total = 0.0
    total_max = 0.0
    case_id = case_payload["case_id"]

    for scene_number, scene in visible_scenes:
        answer_payload = get_answer_for_scene(case_id, scene_number)
        total += calculate_scene_score(scene, answer_payload)
        total_max += scene_max_score(scene)

    st.session_state.score_total = total
    st.session_state.score_max = total_max


def score_percent() -> float:
    if st.session_state.score_max <= 0:
        return 0.0
    return st.session_state.score_total / st.session_state.score_max * 100.0


def rank_info(percent: float) -> Tuple[str, str, str, str, str]:
    if percent >= 85:
        return "秀才", "✨", "#2e7d32", "rank-shusai", "優先順位づけがかなり良い。この調子で現場の流れを固めよう。"
    if percent >= 70:
        return "優秀", "👏", "#1f5fbf", "rank-yushu", "大枠は良い。細かい判断をもう一段磨くとさらに強くなる。"
    if percent >= 50:
        return "良好", "👍", "#ef6c00", "rank-ryoko", "流れは追えている。次は優先行動をもう少し整理しよう。"
    return "要復習", "📝", "#c62828", "rank-review", "最初の観察と重症度判断のつながりをもう一度確認しよう。"


def render_case_card(case_payload: Dict[str, Any]) -> None:
    diff_class = case_payload["difficulty"].lower()
    age = html_escape(case_payload["card_info"]["age"])
    sex = html_escape(case_payload["card_info"]["sex"])
    chief = html_escape(case_payload["card_info"]["chief_complaint"])
    field_label = html_escape(case_payload["field_label"])
    diff_label = html_escape(case_payload["difficulty_label"])

    st.markdown(
        f"""
        <div class="case-card">
            <div class="difficulty-pill {diff_class}">{diff_label}</div>
            <div class="case-main">{age}{sex}、{chief}</div>
            <div class="case-sub">{field_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_media(scene: Dict[str, Any]) -> None:
    media = scene.get("media")
    media_path = find_media_path(media)
    if media_path:
        st.image(str(media_path), use_container_width=True)


def format_visible_label(key: str) -> str:
    return VISIBLE_DATA_LABELS.get(key, key)


def format_visible_value(value: Any) -> str:
    if isinstance(value, bool):
        return BOOL_JA[value]
    if value is None:
        return ""
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            label = format_visible_label(str(k))
            val = format_visible_value(v)
            if val != "":
                lines.append(f"{label}：{val}")
        return "\n".join(lines)
    if isinstance(value, list):
        vals = [format_visible_value(v) for v in value]
        vals = [v for v in vals if v != ""]
        return "\n".join([f"・{v}" for v in vals])
    return str(value)


def stringify_visible_data(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        vals = [format_visible_value(v) for v in value]
        vals = [v for v in vals if v != ""]
        return "\n".join([f"・{v}" for v in vals])
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            label = format_visible_label(str(k))
            val = format_visible_value(v)
            if val != "":
                lines.append(f"{label}：{val}")
        return "\n".join(lines)
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
# 各画面
# =========================================================
def render_cover(cases: List[Dict[str, Any]]) -> None:
    st.markdown(
        f"""
        <div class="app-hero">
            <h1>{html_escape(APP_TITLE)}</h1>
            <p>
                症例を通して、観察 → 判断 → 優先順位づけ を練習するシミュレーションです。<br>
                Easy（入門）は短め、Normal（標準）とHard（実践）は標準の流れで進みます。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    counts = field_counts(cases)
    st.markdown('<div class="section-title">収録状況</div>', unsafe_allow_html=True)

    cols = st.columns(3)
    total_cases = len(cases)
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
            <div class="big">{len(counts)}</div>
            <div class="small">分野数</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols[2].markdown(
        """
        <div class="summary-box">
            <div class="big">7 / 4</div>
            <div class="small">標準 / 入門の場面数</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">はじめる</div>', unsafe_allow_html=True)
    if st.button("症例を選ぶ", type="primary", use_container_width=True):
        st.session_state.selected_field = None
        st.session_state.selected_difficulty = "Normal"
        go_to("case_filter")


def render_case_filter(cases: List[Dict[str, Any]]) -> None:
    st.markdown('<div class="section-title">分野と難易度を選択</div>', unsafe_allow_html=True)

    counts = field_counts(cases)
    field_keys = sorted(counts.keys(), key=lambda x: FIELD_LABEL_FALLBACK.get(x, x))

    st.markdown('<div class="muted">まず分野を選ぶ。</div>', unsafe_allow_html=True)
    cols = st.columns(2 if len(field_keys) <= 4 else 3)

    for i, fk in enumerate(field_keys):
        with cols[i % len(cols)]:
            label = FIELD_LABEL_FALLBACK.get(fk, fk)
            st.markdown(
                f"""
                <div class="field-card">
                    <div class="field-title">{html_escape(label)}</div>
                    <div class="field-sub">{counts[fk]}症例</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"{label}を選ぶ", key=f"field_{fk}", use_container_width=True):
                st.session_state.selected_field = fk
                rerun_with_scroll_top()

    st.markdown('<div class="tiny-space"></div>', unsafe_allow_html=True)

    st.markdown('<div class="muted">次に難易度を選ぶ。</div>', unsafe_allow_html=True)
    diff_display = [DIFFICULTY_LABELS[d] for d in DIFFICULTY_ORDER]
    current_idx = DIFFICULTY_ORDER.index(st.session_state.selected_difficulty)

    selected_disp = st.radio(
        "難易度",
        diff_display,
        index=current_idx,
        horizontal=True,
    )
    reverse_map = {v: k for k, v in DIFFICULTY_LABELS.items()}
    st.session_state.selected_difficulty = reverse_map[selected_disp]

    selected_field = st.session_state.selected_field
    if selected_field:
        field_label = FIELD_LABEL_FALLBACK.get(selected_field, selected_field)
        st.markdown(
            f"""
            <div class="soft-panel">
                <b>選択中</b><br>
                分野：{html_escape(field_label)}<br>
                難易度：{html_escape(DIFFICULTY_LABELS[st.session_state.selected_difficulty])}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("症例を見る", type="primary", use_container_width=True):
            go_to("case_list")
    else:
        st.info("分野を選ぶと、次に症例一覧へ進める。")

    if st.button("表紙に戻る", use_container_width=True):
        go_to("cover")


def render_case_list(cases: List[Dict[str, Any]]) -> None:
    selected_field = st.session_state.selected_field
    difficulty = st.session_state.selected_difficulty

    filtered = [
        c for c in cases
        if c["field_key"] == selected_field and c["difficulty"] == difficulty
    ]

    field_label = FIELD_LABEL_FALLBACK.get(selected_field, selected_field)

    st.markdown(
        f'<div class="section-title">{html_escape(field_label)} / {html_escape(DIFFICULTY_LABELS[difficulty])} の症例</div>',
        unsafe_allow_html=True,
    )

    if not filtered:
        st.warning("この条件に合う症例がまだない。別の難易度か分野を選んでみよう。")
    else:
        for case_payload in filtered:
            col1, col2 = st.columns([5, 2], vertical_alignment="center")
            with col1:
                render_case_card(case_payload)
            with col2:
                if st.button("この症例を開始", key=f"start_{case_payload['case_id']}", type="primary", use_container_width=True):
                    st.session_state.selected_case_id = case_payload["case_id"]
                    reset_case_progress()
                    go_to("intro")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("分野と難易度の選択へ戻る", use_container_width=True):
            go_to("case_filter")
    with col_b:
        if st.button("表紙に戻る", use_container_width=True):
            go_to("cover")


def render_intro(case_payload: Dict[str, Any]) -> None:
    difficulty = st.session_state.selected_difficulty
    card = case_payload["card_info"]

    st.markdown('<div class="section-title">症例開始</div>', unsafe_allow_html=True)

    diff_class = difficulty.lower()
    st.markdown(
        f"""
        <div class="case-card">
            <div class="difficulty-pill {diff_class}">{html_escape(DIFFICULTY_LABELS[difficulty])}</div>
            <div class="case-main">{html_escape(card["age"])}{html_escape(card["sex"])}、{html_escape(card["chief_complaint"])}</div>
            <div class="case-sub">{html_escape(case_payload["field_label"])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    guide_text = {
        "Easy": "要点を絞った短めの流れで進む。",
        "Normal": "標準的な流れで進む。",
        "Hard": "実践に近い流れで、情報整理と判断の質が求められる。",
    }[difficulty]

    st.markdown(
        f"""
        <div class="soft-panel">
            <b>今回の進め方</b><br>
            {html_escape(guide_text)}<br>
            表示される場面数：{len(get_visible_scene_numbers(difficulty))}場面
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
        if st.button("症例一覧へ戻る", use_container_width=True):
            go_to("case_list")


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
        <div class="ranking-help">
            優先順位順に並べる。1行目が最優先のイメージ。スマホでは ↑ ↓ を押して並べ替える。
        </div>
        """,
        unsafe_allow_html=True,
    )

    for idx, label in enumerate(order):
        row1, row2, row3 = st.columns([0.14, 0.14, 0.72], vertical_alignment="center")
        with row1:
            st.markdown(f'<div class="ranking-number">{idx + 1}</div>', unsafe_allow_html=True)
        with row2:
            up_col, down_col = st.columns(2)
            with up_col:
                st.markdown('<div class="rank-btn">', unsafe_allow_html=True)
                if st.button("↑", key=f"rank_up_{case_id}_{scene_number}_{idx}", disabled=(idx == 0), use_container_width=True):
                    move_ranking_item(case_id, scene_number, idx, -1)
                    rerun_with_scroll_top()
                st.markdown('</div>', unsafe_allow_html=True)
            with down_col:
                st.markdown('<div class="rank-btn">', unsafe_allow_html=True)
                if st.button("↓", key=f"rank_down_{case_id}_{scene_number}_{idx}", disabled=(idx == len(order) - 1), use_container_width=True):
                    move_ranking_item(case_id, scene_number, idx, 1)
                    rerun_with_scroll_top()
                st.markdown('</div>', unsafe_allow_html=True)
        with row3:
            st.markdown(
                f"""
                <div class="ranking-row">
                    <div class="ranking-label">{html_escape(label)}</div>
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


def render_scene_input(scene: Dict[str, Any], case_id: str, scene_number: int) -> None:
    scene_type = normalize_scene_type(scene)
    prompt = scene.get("prompt") or "この場面で実施する行動を選ぶ"

    st.markdown(
        f"""
        <div class="soft-panel">
            <b>{html_escape(prompt)}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if scene_type == "single_choice":
        render_single_choice(scene, case_id, scene_number)
    elif scene_type == "multiple_choice":
        render_multiple_choice(scene, case_id, scene_number)
    elif scene_type == "ranking":
        render_ranking(scene, case_id, scene_number)
    elif scene_type == "template_select":
        render_template_select(scene, case_id, scene_number)
    else:
        render_single_choice(scene, case_id, scene_number)


def render_scene(case_payload: Dict[str, Any]) -> None:
    difficulty = st.session_state.selected_difficulty
    visible_scenes = get_visible_scenes(case_payload, difficulty)
    total_scenes = len(visible_scenes)

    idx = st.session_state.scene_display_index
    idx = max(0, min(idx, total_scenes - 1))
    scene_number, scene = visible_scenes[idx]

    render_progress(idx, total_scenes)

    title = html_escape(scene.get("title") or f"Scene {scene_number}")
    phase = scene.get("phase")
    phase_html = f'<div class="scene-phase">{html_escape(phase)}</div>' if phase else ""

    st.markdown(
        f"""
        <div class="scene-card">
            <div class="scene-header">
                <div class="scene-title">{title}</div>
                {phase_html}
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
        st.markdown(
            """
            <div class="muted">必要なときだけヒントを見る。まずは自分で考える。</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="tiny-space"></div>', unsafe_allow_html=True)
    render_scene_input(scene, case_payload["case_id"], scene_number)

    nav1, nav2, nav3 = st.columns(3)
    with nav1:
        prev_disabled = idx <= 0
        if st.button("前へ", disabled=prev_disabled, use_container_width=True):
            st.session_state.scene_display_index -= 1
            rerun_with_scroll_top()
    with nav2:
        if st.button("症例一覧へ戻る", use_container_width=True):
            go_to("case_list")
    with nav3:
        next_label = "ふりかえりへ" if idx >= total_scenes - 1 else "次へ"
        if st.button(next_label, type="primary", use_container_width=True):
            recalc_total_score(case_payload, difficulty)
            if idx >= total_scenes - 1:
                go_to("debrief")
            else:
                st.session_state.scene_display_index += 1
                rerun_with_scroll_top()


def render_hint(case_payload: Dict[str, Any]) -> None:
    difficulty = st.session_state.selected_difficulty
    visible_scenes = get_visible_scenes(case_payload, difficulty)

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
            <div class="hint-box">
                {hint_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("元の場面へ戻る", type="primary", use_container_width=True):
            go_to("scene")
    with col2:
        if st.button("症例一覧へ戻る", use_container_width=True):
            go_to("case_list")


def render_debrief(case_payload: Dict[str, Any]) -> None:
    difficulty = st.session_state.selected_difficulty
    recalc_total_score(case_payload, difficulty)
    percent = score_percent()
    rank_name, rank_icon, rank_color, rank_class, rank_comment = rank_info(percent)

    debrief = case_payload.get("debriefing", {}) or {}
    summary = debrief.get("summary") or case_payload.get("summary", "")
    ideal_actions = debrief.get("ideal_actions") or []
    good_points = debrief.get("good_points") or []
    cautions = debrief.get("cautions") or []

    def list_or_text(value: Any) -> str:
        if not value:
            return ""
        if isinstance(value, list):
            return "<br>".join([f"・{html_escape(str(x))}" for x in value])
        return html_escape(str(value)).replace(chr(10), "<br>")

    summary_body = html_escape(summary).replace(chr(10), "<br>") if summary else ""
    ideal_body = list_or_text(ideal_actions)
    good_body = list_or_text(good_points)
    caution_body = list_or_text(cautions)

    st.markdown('<div class="section-title">ふりかえり</div>', unsafe_allow_html=True)
    st.markdown('<div class="debrief-wrap">', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="debrief-rank-card {rank_class}">
            <div class="debrief-rank-top">
                <div class="debrief-rank-icon">{html_escape(rank_icon)}</div>
                <div class="debrief-rank-name" style="color:{rank_color};">{html_escape(rank_name)}</div>
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
            <div class="debrief-rank-comment">{html_escape(rank_comment)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if summary_body:
        st.markdown(
            f"""
            <div class="debrief-blue-panel">
                <div class="debrief-panel-title" style="color:#1f5fbf;">今回の要点</div>
                <div class="debrief-panel-body">{summary_body}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if ideal_body:
        st.markdown(
            f"""
            <div class="debrief-orange-panel">
                <div class="debrief-panel-title" style="color:#ef6c00;">優先行動の整理</div>
                <div class="debrief-panel-body">{ideal_body}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if good_body:
        st.markdown(
            f"""
            <div class="debrief-green-panel">
                <div class="debrief-panel-title" style="color:#2e7d32;">できたこと</div>
                <div class="debrief-panel-body">{good_body}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if caution_body:
        st.markdown(
            f"""
            <div class="debrief-red-panel">
                <div class="debrief-panel-title" style="color:#c62828;">次に直すこと</div>
                <div class="debrief-panel-body">{caution_body}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("自分の回答を見る"):
        visible_scenes = get_visible_scenes(case_payload, difficulty)
        for scene_number, scene in visible_scenes:
            ans = get_answer_for_scene(case_payload["case_id"], scene_number)
            title = scene.get("title") or f"Scene {scene_number}"
            st.markdown(f"**{title}**")
            if ans is None or ans == []:
                st.write("未回答")
            elif isinstance(ans, list):
                for a in ans:
                    st.write(f"・{a}")
            else:
                st.write(str(ans))
            st.markdown("---")

    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("同じ症例をもう一度", type="primary", use_container_width=True):
            reset_case_progress()
            go_to("intro")
    with col2:
        if st.button("症例一覧へ戻る", use_container_width=True):
            reset_case_progress()
            go_to("case_list")


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

    elif screen == "case_filter":
        render_case_filter(cases)

    elif screen == "case_list":
        render_case_list(cases)

    elif screen in {"intro", "scene", "hint", "debrief"}:
        if not current_case:
            st.warning("症例が選択されていない。症例一覧へ戻る。")
            if st.button("症例一覧へ戻る", use_container_width=True):
                go_to("case_list")
            st.stop()

        if screen == "intro":
            render_intro(current_case)
        elif screen == "scene":
            render_scene(current_case)
        elif screen == "hint":
            render_hint(current_case)
        elif screen == "debrief":
            render_debrief(current_case)

    else:
        go_to("cover")


if __name__ == "__main__":
    main()