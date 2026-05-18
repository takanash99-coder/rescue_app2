import hashlib
import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components


# =========================================================
# 救急救命士向け 臨床推論シミュレーション
# ROGER LEVEL PLAYER EDITION 2026-05-13
#
# 目的：
# - 100症例運用を前提に、Level1〜10制で動かす
# - 各Level候補10症例から5症例をランダム提示
# - プレイヤー名ごとに進捗・既出症例・スコア履歴を保存
# - JSON構造・症例本文・画像パスは変更しない
# =========================================================

st.set_page_config(
    page_title="臨床推論シミュレーション",
    page_icon="🚑",
    layout="wide",
)

APP_VERSION = "ROGER_LEVEL_PLAYER_2026_05_13"
APP_TITLE = "救急救命士向け 臨床推論シミュレーション"

REPO_ROOT = Path(__file__).resolve().parent
CASES_DIR = REPO_ROOT / "cases"
CASE_MEDIA_DIR = CASES_DIR / "media"
ROOT_MEDIA_DIR = REPO_ROOT / "media"
PLAYERS_DIR = REPO_ROOT / "players"

LEVEL_COUNT = 10
LEVEL_CANDIDATE_COUNT = 10
LEVEL_PLAY_COUNT = 5

CATEGORY_LABELS = {
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

DIFFICULTY_LABELS = {
    "Easy": "Easy",
    "Normal": "Normal",
    "Hard": "Hard",
    "": "未設定",
}

DIFFICULTY_SCORE = {
    "Easy": 1,
    "Normal": 2,
    "Hard": 3,
    "": 2,
}

VISIBLE_DATA_LABELS = {
    "dispatch_information": "通報内容",
    "history": "病歴・聴取内容",
    "vitals": "バイタルサイン",
    "body_findings": "身体所見",
    "assessment": "評価",
    "location": "場所",
    "environment": "周囲環境",
    "mechanism": "受傷機転",
    "chief_complaint": "主訴",
    "consciousness": "意識",
    "awareness": "意識",
    "mental_status": "意識状態",
    "airway": "気道",
    "breathing": "呼吸",
    "circulation": "循環",
    "respiratory_rate": "呼吸数",
    "respiration_rate": "呼吸数",
    "pulse_rate": "脈拍数",
    "heart_rate": "心拍数",
    "blood_pressure": "血圧",
    "bp": "血圧",
    "spo2": "SpO₂",
    "temperature": "体温",
    "body_temperature": "体温",
    "skin": "皮膚",
    "skin_color": "皮膚色",
    "bleeding": "出血",
    "external_bleeding": "外出血",
    "external_injury": "外表外傷",
    "trauma_sign": "外傷所見",
    "ecg": "心電図",
    "ecg_impression": "心電図所見",
    "suspected_condition": "疑う病態",
    "suspected_shock_type": "疑うショック",
    "transport_priority": "搬送優先度",
    "concern": "懸念",
    "goal": "目標",
    "body_map_template": "人体図テンプレート",
    "body_regions": "観察部位",
}

SCENE_TYPE_LABELS = {
    "single_choice": "単一選択",
    "multiple_choice": "複数選択",
    "ranking": "優先順位",
    "template_select": "テンプレート選択",
    "dialogue_input": "対話入力",
    "body_map_select": "人体図観察",
    "free_text": "記述式",
}

LEVEL_DESCRIPTIONS = {
    "Level1": "初級：通報内容・初期評価の基本",
    "Level2": "初級：観察と優先順位",
    "Level3": "初級：基本処置と搬送判断",
    "Level4": "中級：情報収集と再判断",
    "Level5": "中級：病態推論と処置選択",
    "Level6": "中級：複数所見からの判断",
    "Level7": "上級：重症度判断とプロトコル切替",
    "Level8": "上級：画像・所見の統合",
    "Level9": "上級：複雑症例・搬送先判断",
    "Level10": "ラスボス：対話・人体図・優先順位を含む総合判断",
}


# =========================================================
# CSS / UI
# =========================================================
def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #f3f6fb;
            --card: #ffffff;
            --text: #14233b;
            --muted: #607086;
            --line: #dbe5f2;
            --blue: #2563eb;
            --blue2: #1d4ed8;
            --soft-blue: #eaf2ff;
            --green: #2e7d32;
            --soft-green: #e9f7ef;
            --orange: #ef6c00;
            --soft-orange: #fff3e6;
            --red: #c62828;
            --soft-red: #fdecec;
            --yellow: #f9a825;
            --soft-yellow: #fff8e1;
            --purple: #6d28d9;
            --soft-purple: #f1eafe;
            --shadow: 0 10px 28px rgba(20, 35, 56, 0.07);
        }

        html, body, [class*="css"], .stApp {
            font-family: "BIZ UDPGothic", "Yu Gothic UI", "Meiryo", sans-serif !important;
            color: var(--text);
        }

        .stApp {
            background: linear-gradient(180deg, #f7f9fd 0%, #edf3fa 100%);
        }

        .hero {
            background: linear-gradient(135deg, #1e5cc8 0%, #3b7be8 100%);
            color: white;
            border-radius: 22px;
            padding: 24px 26px;
            margin: 10px 0 18px 0;
            box-shadow: 0 14px 36px rgba(31, 95, 191, 0.20);
        }

        .hero h1 {
            font-size: 1.9rem;
            line-height: 1.25;
            margin: 0 0 10px 0;
            color: white;
        }

        .hero p {
            font-size: 1rem;
            line-height: 1.75;
            margin: 0;
            color: white;
            opacity: 0.98;
        }

        .version {
            display: inline-block;
            margin-top: 10px;
            padding: 5px 10px;
            border-radius: 999px;
            background: rgba(255,255,255,0.18);
            font-size: 0.82rem;
            font-weight: 700;
        }

        .card {
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 16px 18px;
            box-shadow: var(--shadow);
            margin-bottom: 12px;
        }

        .metric-card {
            background: white;
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 18px;
            text-align: center;
            box-shadow: 0 6px 18px rgba(20, 35, 56, 0.05);
        }

        .metric-card .big {
            font-size: 1.55rem;
            font-weight: 800;
        }

        .metric-card .small {
            color: var(--muted);
            font-size: 0.88rem;
            margin-top: 4px;
        }

        .section-title {
            font-size: 1.18rem;
            font-weight: 800;
            margin: 14px 0 10px 0;
        }

        .case-title {
            font-size: 1.12rem;
            font-weight: 800;
            margin-bottom: 6px;
        }

        .muted {
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.7;
        }

        .pill {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: #eef3fb;
            color: #1f3558;
            font-size: 0.82rem;
            font-weight: 700;
            margin-right: 4px;
            margin-bottom: 4px;
        }

        .pill-blue { background: var(--soft-blue); color: var(--blue2); }
        .pill-green { background: var(--soft-green); color: var(--green); }
        .pill-orange { background: var(--soft-orange); color: var(--orange); }
        .pill-red { background: var(--soft-red); color: var(--red); }
        .pill-purple { background: var(--soft-purple); color: var(--purple); }

        .scene-card {
            background: white;
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 18px;
            box-shadow: var(--shadow);
            margin: 10px 0 14px 0;
        }

        .scene-title {
            font-size: 1.25rem;
            font-weight: 900;
            margin-bottom: 4px;
        }

        .scene-text {
            font-size: 1.04rem;
            line-height: 1.9;
            white-space: pre-wrap;
        }

        .info-box {
            background: #f8fbff;
            border-left: 6px solid var(--blue);
            border-radius: 14px;
            padding: 13px 15px;
            margin: 12px 0;
        }

        .warn-box {
            background: var(--soft-yellow);
            border-left: 6px solid var(--yellow);
            border-radius: 14px;
            padding: 13px 15px;
            margin: 12px 0;
        }

        .good-box {
            background: var(--soft-green);
            border-left: 6px solid var(--green);
            border-radius: 14px;
            padding: 13px 15px;
            margin: 12px 0;
        }

        .bad-box {
            background: var(--soft-red);
            border-left: 6px solid var(--red);
            border-radius: 14px;
            padding: 13px 15px;
            margin: 12px 0;
        }

        .level-box {
            background: white;
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 16px;
            box-shadow: var(--shadow);
            margin-bottom: 10px;
        }

        .label {
            font-size: 0.84rem;
            font-weight: 900;
            color: var(--muted);
            margin-bottom: 5px;
            letter-spacing: 0.03em;
        }

        .progress-wrap {
            background: white;
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 13px 15px;
            margin-bottom: 12px;
        }

        .progress-line {
            height: 12px;
            border-radius: 999px;
            background: #dfe8f4;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #1e5cc8 0%, #4b8cf0 100%);
        }

        .stButton > button {
            border-radius: 14px;
            min-height: 3rem;
            font-weight: 800;
            border: 1px solid #cfd8e6;
            white-space: normal !important;
            line-height: 1.5 !important;
        }

        div[role="radiogroup"] label,
        div[role="group"] label,
        .stRadio label,
        .stCheckbox label {
            white-space: normal !important;
            overflow-wrap: anywhere !important;
            word-break: break-word !important;
            line-height: 1.55 !important;
        }

        @media (max-width: 768px) {
            .hero { padding: 18px 16px; border-radius: 18px; }
            .hero h1 { font-size: 1.45rem; }
            .scene-card, .card { padding: 14px; border-radius: 16px; }
            .scene-title { font-size: 1.08rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def scroll_to_top() -> None:
    components.html(
        """
        <script>
        setTimeout(function() {
            try {
                window.parent.scrollTo(0, 0);
                const main = window.parent.document.querySelector('section.main');
                if (main) { main.scrollTop = 0; }
                const app = window.parent.document.querySelector('[data-testid="stAppViewContainer"]');
                if (app) { app.scrollTop = 0; }
            } catch(e) {}
        }, 80);
        </script>
        """,
        height=0,
    )


def safe_image(path: Path, caption: str = "") -> None:
    try:
        st.image(str(path), caption=caption if caption else None, width="stretch")
    except TypeError:
        st.image(str(path), caption=caption if caption else None, use_container_width=True)


# =========================================================
# 基本ユーティリティ
# =========================================================
def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "あり" if value else "なし"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        lines = []
        for v in value:
            t = as_text(v)
            if t:
                lines.append(t)
        return "\n".join(lines)
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            label = VISIBLE_DATA_LABELS.get(str(k), str(k))
            body = as_text(v)
            if body:
                lines.append(f"{label}：{body}")
        return "\n".join(lines)
    return str(value)


def normalize_str(value: Any) -> str:
    return str(value or "").strip()


def normalize_lower(value: Any) -> str:
    text = normalize_str(value).lower()
    text = text.replace("　", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def get_category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category or "その他")


def get_difficulty(case: Dict[str, Any]) -> str:
    d = normalize_str(case.get("difficulty"))
    return d if d else ""


def get_case_id(data: Dict[str, Any], path: Path) -> str:
    return normalize_str(data.get("case_id") or data.get("id") or path.stem)


def sanitize_player_name(name: str) -> str:
    name = normalize_str(name)
    if not name:
        return ""
    return name[:40]


def player_file_key(name: str) -> str:
    raw = sanitize_player_name(name)
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]
    safe = re.sub(r"[^a-zA-Z0-9_\-ぁ-んァ-ヶー一-龥]", "_", raw)
    safe = safe[:24] if safe else "player"
    return f"{safe}_{digest}.json"


def read_json(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, str(e)


def is_case_json(path: Path) -> bool:
    if path.suffix.lower() != ".json":
        return False
    parts = [p.lower() for p in path.parts]
    if "media" in parts:
        return False
    if path.name.startswith("."):
        return False
    return True


def get_scenes(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    scenes = data.get("scenes")
    if isinstance(scenes, list):
        out = []
        for i, sc in enumerate(scenes, start=1):
            if isinstance(sc, dict):
                sc2 = dict(sc)
                sc2.setdefault("id", f"scene{i}")
                sc2.setdefault("title", f"Scene {i}")
                out.append(sc2)
        return out

    # 旧形式救済
    out = []
    for i in range(1, 15):
        for key in (f"scene{i}", f"scene_{i}"):
            if isinstance(data.get(key), dict):
                sc2 = dict(data[key])
                sc2.setdefault("id", f"scene{i}")
                sc2.setdefault("title", f"Scene {i}")
                out.append(sc2)
                break
    return out


def infer_category(data: Dict[str, Any], path: Path) -> str:
    category = normalize_str(data.get("category") or data.get("field"))
    if category:
        return category
    try:
        rel = path.relative_to(CASES_DIR)
        if len(rel.parts) >= 2:
            return rel.parts[0]
    except Exception:
        pass
    return "other"


def infer_age_sex(text: str) -> Tuple[str, str]:
    age = "年齢不明"
    sex = "性別不明"
    m = re.search(r"(\d{1,3})歳", text)
    if m:
        age = f"{m.group(1)}歳"
    if "男性" in text:
        sex = "男性"
    elif "女性" in text:
        sex = "女性"
    elif "男児" in text:
        sex = "男児"
    elif "女児" in text:
        sex = "女児"
    elif "新生児" in text:
        sex = "新生児"
    return age, sex


def build_case_payload(path: Path, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    scenes = get_scenes(data)
    if not scenes:
        return None

    text_source = " ".join([
        normalize_str(data.get("title")),
        normalize_str(data.get("summary")),
        normalize_str(data.get("overview")),
        as_text(scenes[0].get("text") if scenes else ""),
        as_text(scenes[0].get("visible_data") if scenes else ""),
    ])
    age, sex = infer_age_sex(text_source)

    category = infer_category(data, path)
    case_id = get_case_id(data, path)

    return {
        "case_id": case_id,
        "path": path,
        "title": normalize_str(data.get("title") or path.stem),
        "category": category,
        "category_label": get_category_label(category),
        "difficulty": normalize_str(data.get("difficulty")),
        "estimated_time": data.get("estimated_time", ""),
        "keywords": data.get("keywords", []) if isinstance(data.get("keywords"), list) else [],
        "age": age,
        "sex": sex,
        "scenes": scenes,
        "debriefing": data.get("debriefing", {}) if isinstance(data.get("debriefing"), dict) else {},
        "raw": data,
        "path_text": str(path),
    }


@st.cache_data(show_spinner=False)
def load_cases() -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    cases: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    if not CASES_DIR.exists():
        return [], [{"file": str(CASES_DIR), "error": "casesフォルダが見つかりません。"}]

    for path in sorted(CASES_DIR.rglob("*.json")):
        if not is_case_json(path):
            continue

        data, err = read_json(path)
        if err or not data:
            errors.append({"file": str(path.relative_to(REPO_ROOT)), "error": err or "JSONを読めません。"})
            continue

        payload = build_case_payload(path, data)
        if not payload:
            errors.append({"file": str(path.relative_to(REPO_ROOT)), "error": "scenesが見つからないため読み込み対象外。"})
            continue

        cases.append(payload)

    # case_id重複があっても落とさず、画面用に一意化する
    seen: Dict[str, int] = {}
    for c in cases:
        base = c["case_id"]
        seen[base] = seen.get(base, 0) + 1
        if seen[base] > 1:
            c["case_id"] = f"{base}__dup{seen[base]}"
            c["duplicate_base_id"] = base

    return cases, errors


def find_case(cases: List[Dict[str, Any]], case_id: str) -> Optional[Dict[str, Any]]:
    for c in cases:
        if c["case_id"] == case_id:
            return c
    return None


# =========================================================
# Player persistence
# =========================================================
def default_player_data(player_name: str) -> Dict[str, Any]:
    return {
        "player_name": player_name,
        "is_guest": False,
        "created_at": now_text(),
        "last_login_at": now_text(),
        "current_level": 1,
        "completed_levels": [],
        "played_case_ids": [],
        "case_history": {},
        "level_history": {},
        "total_play_count": 0,
        "best_total_score_percent": 0.0,
    }


def player_path(player_name: str) -> Path:
    PLAYERS_DIR.mkdir(parents=True, exist_ok=True)
    return PLAYERS_DIR / player_file_key(player_name)


def load_player(player_name: str) -> Dict[str, Any]:
    path = player_path(player_name)
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("player_name", player_name)
                data.setdefault("is_guest", False)
                data.setdefault("created_at", now_text())
                data["last_login_at"] = now_text()
                data.setdefault("current_level", 1)
                data.setdefault("completed_levels", [])
                data.setdefault("played_case_ids", [])
                data.setdefault("case_history", {})
                data.setdefault("level_history", {})
                data.setdefault("total_play_count", 0)
                data.setdefault("best_total_score_percent", 0.0)
                save_player(data)
                return data
        except Exception:
            pass

    data = default_player_data(player_name)
    save_player(data)
    return data


def save_player(player_data: Dict[str, Any]) -> None:
    # Guestモードは毎回リセットするため、履歴ファイルへ保存しない。
    # 通常ログインしたプレイヤーのみ players フォルダに履歴を保存する。
    if player_data.get("is_guest"):
        return

    try:
        PLAYERS_DIR.mkdir(parents=True, exist_ok=True)
        path = player_path(player_data.get("player_name", "guest"))
        with path.open("w", encoding="utf-8") as f:
            json.dump(player_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"プレイヤーデータの保存に失敗しました：{e}")


def get_player() -> Optional[Dict[str, Any]]:
    return st.session_state.get("player_data")


def set_player(player_data: Dict[str, Any]) -> None:
    st.session_state.player_data = player_data


def mark_case_played(case: Dict[str, Any], percent: float, mode: str, level_name: str = "") -> None:
    player = get_player()
    if not player:
        return

    case_id = case["case_id"]
    played = player.setdefault("played_case_ids", [])
    if case_id not in played:
        played.append(case_id)

    history = player.setdefault("case_history", {})
    old = history.get(case_id, {})
    best = max(float(old.get("best_percent", 0.0)), percent)

    history[case_id] = {
        "title": case["title"],
        "category": case["category"],
        "difficulty": case["difficulty"],
        "last_percent": percent,
        "best_percent": best,
        "last_played_at": now_text(),
        "play_count": int(old.get("play_count", 0)) + 1,
        "mode": mode,
        "level": level_name,
    }

    player["total_play_count"] = int(player.get("total_play_count", 0)) + 1
    player["best_total_score_percent"] = max(float(player.get("best_total_score_percent", 0.0)), percent)
    save_player(player)


def mark_level_completed(level_name: str, challenge_case_ids: List[str], percent: float) -> None:
    player = get_player()
    if not player:
        return

    completed = player.setdefault("completed_levels", [])
    if level_name not in completed:
        completed.append(level_name)

    level_history = player.setdefault("level_history", {})
    old = level_history.get(level_name, {})
    best = max(float(old.get("best_percent", 0.0)), percent)

    level_history[level_name] = {
        "cleared": True,
        "played_cases": challenge_case_ids,
        "last_percent": percent,
        "best_percent": best,
        "last_played_at": now_text(),
        "challenge_count": int(old.get("challenge_count", 0)) + 1,
    }

    try:
        num = int(level_name.replace("Level", ""))
        player["current_level"] = max(int(player.get("current_level", 1)), min(num + 1, LEVEL_COUNT))
    except Exception:
        pass

    save_player(player)


# =========================================================
# Level build / challenge
# =========================================================
def normalize_scene_type(scene: Dict[str, Any]) -> str:
    t = normalize_lower(scene.get("type"))
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
        "dialogue": "dialogue_input",
        "dialogue_input": "dialogue_input",
        "body_map": "body_map_select",
        "body_map_select": "body_map_select",
        "free_text": "free_text",
        "freetext": "free_text",
        "text": "free_text",
    }
    return aliases.get(t, "single_choice")


def case_complexity(case: Dict[str, Any]) -> int:
    score = DIFFICULTY_SCORE.get(case.get("difficulty", ""), 2) * 10
    types = [normalize_scene_type(sc) for sc in case.get("scenes", [])]

    for t in types:
        if t == "multiple_choice":
            score += 1
        elif t == "ranking":
            score += 4
        elif t == "template_select":
            score += 3
        elif t == "dialogue_input":
            score += 6
        elif t == "body_map_select":
            score += 6
        elif t == "free_text":
            score += 5

    if len(case.get("scenes", [])) >= 7:
        score += 2

    joined = " ".join([case.get("title", ""), " ".join(case.get("keywords", []))])
    if any(x in joined for x in ["ボス", "ラスボス", "重症", "ショック", "CPA", "心停止", "指示要請", "病院連絡"]):
        score += 4

    return score


@st.cache_data(show_spinner=False)
def build_level_candidates_cached(case_ids_and_scores: Tuple[Tuple[str, int], ...]) -> Dict[str, List[str]]:
    sorted_items = sorted(case_ids_and_scores, key=lambda x: x[1])

    # 100症例運用を優先。101件以上ある場合は、複雑度順で100件をLevelに割り当てる。
    usable = sorted_items[: LEVEL_COUNT * LEVEL_CANDIDATE_COUNT]

    levels: Dict[str, List[str]] = {}
    for i in range(LEVEL_COUNT):
        start = i * LEVEL_CANDIDATE_COUNT
        end = start + LEVEL_CANDIDATE_COUNT
        levels[f"Level{i+1}"] = [case_id for case_id, _score in usable[start:end]]

    return levels


def build_level_candidates(cases: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    pairs = tuple((c["case_id"], case_complexity(c)) for c in cases)
    return build_level_candidates_cached(pairs)


def choose_level_challenge_cases(
    level_name: str,
    candidate_ids: List[str],
    player_data: Dict[str, Any],
    count: int = LEVEL_PLAY_COUNT,
) -> List[str]:
    played = set(player_data.get("played_case_ids", []))
    not_played = [cid for cid in candidate_ids if cid not in played]
    already_played = [cid for cid in candidate_ids if cid in played]

    rng = random.Random()
    rng.shuffle(not_played)
    rng.shuffle(already_played)

    chosen = (not_played + already_played)[:count]

    # 候補が足りない場合でも落とさない
    if len(chosen) < count:
        rest = [cid for cid in candidate_ids if cid not in chosen]
        rng.shuffle(rest)
        chosen.extend(rest[: count - len(chosen)])

    return chosen


def start_level_challenge(cases: List[Dict[str, Any]], level_name: str) -> None:
    player = get_player()
    if not player:
        return

    level_map = build_level_candidates(cases)
    candidate_ids = level_map.get(level_name, [])
    chosen = choose_level_challenge_cases(level_name, candidate_ids, player, LEVEL_PLAY_COUNT)

    if not chosen:
        st.error("このLevelに出題できる症例がありません。")
        return

    st.session_state.mode = "level"
    st.session_state.selected_level_name = level_name
    st.session_state.challenge_case_ids = chosen
    st.session_state.challenge_index = 0
    st.session_state.challenge_results = []
    st.session_state.selected_case_id = chosen[0]
    reset_play_state()
    go("intro")


def start_single_case(case_id: str) -> None:
    st.session_state.mode = "single"
    st.session_state.selected_level_name = ""
    st.session_state.challenge_case_ids = []
    st.session_state.challenge_index = 0
    st.session_state.challenge_results = []
    st.session_state.selected_case_id = case_id
    reset_play_state()
    go("intro")


def move_after_case_result(cases: List[Dict[str, Any]]) -> None:
    if st.session_state.get("mode") != "level":
        go("home")
        return

    challenge_ids = st.session_state.get("challenge_case_ids", [])
    next_index = int(st.session_state.get("challenge_index", 0)) + 1

    if next_index >= len(challenge_ids):
        go("level_result")
        return

    st.session_state.challenge_index = next_index
    st.session_state.selected_case_id = challenge_ids[next_index]
    reset_play_state()
    go("intro")


# =========================================================
# Media
# =========================================================
def iter_media_values(value: Any) -> List[str]:
    out: List[str] = []
    if not value:
        return out
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for k in ("path", "file", "src", "image", "filename", "url"):
            if value.get(k):
                out.append(str(value[k]))
    elif isinstance(value, list):
        for item in value:
            out.extend(iter_media_values(item))
    return out


def resolve_media_path(raw: str) -> Optional[Path]:
    if not raw:
        return None
    raw = raw.strip().replace("\\", "/")
    name = Path(raw).name

    candidates = [
        REPO_ROOT / raw,
        CASES_DIR / raw,
        CASE_MEDIA_DIR / name,
        ROOT_MEDIA_DIR / raw,
        ROOT_MEDIA_DIR / name,
        Path(raw),
    ]

    for p in candidates:
        try:
            if p.exists() and p.is_file():
                return p
        except Exception:
            continue
    return None


def render_media(scene: Dict[str, Any]) -> None:
    media_values = iter_media_values(scene.get("media"))
    if not media_values:
        return

    st.markdown('<div class="section-title">画像・資料</div>', unsafe_allow_html=True)
    for raw in media_values:
        path = resolve_media_path(raw)
        if path:
            safe_image(path, caption=Path(raw).name)
        else:
            st.warning(f"画像ファイルが見つかりません：{raw}")


# =========================================================
# Scene type / 選択肢
# =========================================================
def normalize_options(scene: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_options = scene.get("options", [])
    options: List[Dict[str, Any]] = []

    if isinstance(raw_options, list):
        for i, opt in enumerate(raw_options, start=1):
            if isinstance(opt, dict):
                oid = normalize_str(opt.get("option_id") or opt.get("id") or str(i))
                text = normalize_str(opt.get("text") or opt.get("label") or opt.get("name") or f"選択肢{i}")
                is_correct = bool(opt.get("is_correct") or opt.get("correct") or opt.get("ideal"))
                options.append({
                    "option_id": oid,
                    "text": text,
                    "is_correct": is_correct,
                    "score_delta": opt.get("score_delta", None),
                    "life_delta": opt.get("life_delta", 0),
                    "rationale": normalize_str(opt.get("rationale") or opt.get("explanation") or opt.get("feedback")),
                    "raw": opt,
                })
            else:
                options.append({
                    "option_id": str(i),
                    "text": normalize_str(opt),
                    "is_correct": False,
                    "score_delta": None,
                    "life_delta": 0,
                    "rationale": "",
                    "raw": opt,
                })

    # answer_index / answer_indices救済
    if options and not any(o["is_correct"] for o in options):
        answer_index = scene.get("answer_index")
        answer_indices = scene.get("answer_indices")
        answer = scene.get("answer")

        if isinstance(answer_index, int):
            idx = answer_index if 0 <= answer_index < len(options) else answer_index - 1
            if 0 <= idx < len(options):
                options[idx]["is_correct"] = True

        if isinstance(answer_indices, list):
            for a in answer_indices:
                if isinstance(a, int):
                    idx = a if 0 <= a < len(options) else a - 1
                    if 0 <= idx < len(options):
                        options[idx]["is_correct"] = True

        if isinstance(answer, str):
            for o in options:
                if answer == o["option_id"] or answer == o["text"]:
                    o["is_correct"] = True

    return options


def normalize_templates(scene: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_templates = scene.get("templates", [])
    templates: List[Dict[str, Any]] = []

    if isinstance(raw_templates, list):
        for i, t in enumerate(raw_templates, start=1):
            if isinstance(t, dict):
                tid = normalize_str(t.get("template_id") or t.get("id") or str(i))
                text = normalize_str(t.get("text") or t.get("label") or t.get("name") or f"テンプレート{i}")
                is_correct = bool(t.get("is_correct") or t.get("correct") or t.get("ideal"))
                templates.append({
                    "template_id": tid,
                    "text": text,
                    "is_correct": is_correct,
                    "score_delta": t.get("score_delta", None),
                    "life_delta": t.get("life_delta", 0),
                    "rationale": normalize_str(t.get("rationale") or t.get("explanation") or t.get("feedback")),
                    "raw": t,
                })
            else:
                templates.append({
                    "template_id": str(i),
                    "text": normalize_str(t),
                    "is_correct": False,
                    "score_delta": None,
                    "life_delta": 0,
                    "rationale": "",
                    "raw": t,
                })

    return templates


def normalize_ranking_items(scene: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = scene.get("ranking")
    if raw is None:
        raw = scene.get("options", [])

    items: List[Dict[str, Any]] = []
    if isinstance(raw, list):
        for i, item in enumerate(raw, start=1):
            if isinstance(item, dict):
                iid = normalize_str(item.get("item_id") or item.get("option_id") or item.get("id") or str(i))
                text = normalize_str(item.get("text") or item.get("label") or item.get("name") or f"項目{i}")
                correct_order = item.get("correct_order", item.get("order", i))
                try:
                    correct_order = int(correct_order)
                except Exception:
                    correct_order = i
                items.append({
                    "item_id": iid,
                    "text": text,
                    "correct_order": correct_order,
                    "rationale": normalize_str(item.get("rationale") or item.get("explanation") or item.get("feedback")),
                    "raw": item,
                })
            else:
                items.append({
                    "item_id": str(i),
                    "text": normalize_str(item),
                    "correct_order": i,
                    "rationale": "",
                    "raw": item,
                })
    return items


# =========================================================
# 採点
# =========================================================
def default_scene_score(scene: Dict[str, Any]) -> float:
    try:
        v = float(scene.get("ideal_score_delta", 10))
        if v == 0:
            return 10.0
        return v
    except Exception:
        return 10.0


def option_score(option: Optional[Dict[str, Any]], scene: Dict[str, Any]) -> float:
    if not option:
        return 0.0
    if option.get("score_delta") is not None:
        try:
            return float(option.get("score_delta"))
        except Exception:
            pass
    return default_scene_score(scene) if option.get("is_correct") else 0.0


def option_life(option: Optional[Dict[str, Any]]) -> float:
    if not option:
        return 0.0
    try:
        return float(option.get("life_delta", 0))
    except Exception:
        return 0.0


def scene_max_score(scene: Dict[str, Any]) -> float:
    stype = normalize_scene_type(scene)
    if stype == "single_choice":
        options = normalize_options(scene)
        positives = [option_score(o, scene) for o in options if o.get("is_correct")]
        return max(positives) if positives else default_scene_score(scene)

    if stype == "multiple_choice":
        options = normalize_options(scene)
        positives = [max(option_score(o, scene), 0.0) for o in options if o.get("is_correct")]
        return sum(positives) if positives else default_scene_score(scene)

    if stype == "template_select":
        temps = normalize_templates(scene)
        positives = [option_score(t, scene) for t in temps if t.get("is_correct")]
        return max(positives) if positives else default_scene_score(scene)

    if stype == "ranking":
        items = normalize_ranking_items(scene)
        return float(len(items) * 2) if items else default_scene_score(scene)

    if stype in ("dialogue_input", "body_map_select", "free_text"):
        return default_scene_score(scene)

    return default_scene_score(scene)


def score_single(scene: Dict[str, Any], selected_text: str) -> Dict[str, Any]:
    options = normalize_options(scene)
    selected = next((o for o in options if o["text"] == selected_text), None)

    score = option_score(selected, scene)
    life = option_life(selected)
    correct = bool(selected and selected.get("is_correct"))
    correct_text = " / ".join([o["text"] for o in options if o.get("is_correct")]) or "正解設定なし"

    return {
        "score": score,
        "life": life,
        "is_correct": correct,
        "your_answer": selected_text or "未回答",
        "model_answer": correct_text,
        "rationale": selected.get("rationale", "") if selected else "",
        "details": [],
    }


def score_multiple(scene: Dict[str, Any], selected_texts: List[str]) -> Dict[str, Any]:
    options = normalize_options(scene)
    selected_set = set(selected_texts or [])
    score = 0.0
    life = 0.0
    details = []

    for o in options:
        if o["text"] in selected_set:
            score += option_score(o, scene)
            life += option_life(o)
            details.append(f"{'○' if o.get('is_correct') else '△'} {o['text']}：{o.get('rationale','')}")

    correct_texts = [o["text"] for o in options if o.get("is_correct")]
    missed = [t for t in correct_texts if t not in selected_set]
    wrong = [o["text"] for o in options if (o["text"] in selected_set and not o.get("is_correct"))]
    is_correct = bool(correct_texts) and not missed and not wrong

    return {
        "score": max(score, 0.0),
        "life": life,
        "is_correct": is_correct,
        "your_answer": "、".join(selected_texts) if selected_texts else "未回答",
        "model_answer": "、".join(correct_texts) if correct_texts else "正解設定なし",
        "rationale": "必要な選択肢を拾えているか、不要な選択をしていないかを確認しよう。",
        "details": details,
    }


def score_template(scene: Dict[str, Any], selected_text: str) -> Dict[str, Any]:
    temps = normalize_templates(scene)
    selected = next((t for t in temps if t["text"] == selected_text), None)
    score = option_score(selected, scene)
    life = option_life(selected)
    correct = bool(selected and selected.get("is_correct"))
    correct_text = " / ".join([t["text"] for t in temps if t.get("is_correct")]) or "正解設定なし"

    return {
        "score": score,
        "life": life,
        "is_correct": correct,
        "your_answer": selected_text or "未回答",
        "model_answer": correct_text,
        "rationale": selected.get("rationale", "") if selected else "",
        "details": [],
    }


def score_ranking(scene: Dict[str, Any], ordered_texts: List[str]) -> Dict[str, Any]:
    items = normalize_ranking_items(scene)
    correct_order = [x["text"] for x in sorted(items, key=lambda x: x["correct_order"])]

    score = 0.0
    details = []
    for idx, text in enumerate(ordered_texts, start=1):
        expected_idx = correct_order.index(text) + 1 if text in correct_order else None
        if expected_idx == idx:
            score += 2.0
            details.append(f"○ {idx}番目：{text}")
        else:
            details.append(f"△ {idx}番目：{text}（理想は{expected_idx}番目）")

    is_correct = ordered_texts == correct_order

    return {
        "score": score,
        "life": 0.0,
        "is_correct": is_correct,
        "your_answer": " → ".join(ordered_texts) if ordered_texts else "未回答",
        "model_answer": " → ".join(correct_order) if correct_order else "正解設定なし",
        "rationale": "優先順位は、生命危機・安全・早期搬送につながる順で見直そう。",
        "details": details,
    }


def score_dialogue(scene: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    text = normalize_lower(user_text)
    rules = scene.get("dialogue_rules", [])
    matched = []
    score = 0.0
    replies = []

    if isinstance(rules, list):
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            keywords = rule.get("keywords", [])
            if isinstance(keywords, str):
                keywords = [keywords]
            if any(normalize_lower(k) and normalize_lower(k) in text for k in keywords):
                matched.append(rule)
                try:
                    score += float(rule.get("score_delta", 5))
                except Exception:
                    score += 5.0
                reply = normalize_str(rule.get("reply"))
                if reply:
                    replies.append(reply)

    fallback = normalize_str(scene.get("fallback_reply") or "入力内容を確認しました。必要な情報が不足していないか振り返りましょう。")
    if not replies:
        replies = [fallback]

    model_parts = []
    if isinstance(rules, list):
        for rule in rules:
            if isinstance(rule, dict):
                q = rule.get("acceptable_questions") or rule.get("keywords") or rule.get("intent_id")
                model_parts.append(as_text(q))
    model_answer = " / ".join([x for x in model_parts if x]) or "必要情報を簡潔に確認する"

    return {
        "score": score,
        "life": 0.0,
        "is_correct": score > 0,
        "your_answer": user_text or "未回答",
        "model_answer": model_answer,
        "rationale": "\n".join(replies),
        "details": [f"一致ルール：{normalize_str(r.get('intent_id') or r.get('reply'))}" for r in matched],
    }


def score_body_map(scene: Dict[str, Any], selected_regions: List[str]) -> Dict[str, Any]:
    visible = scene.get("visible_data", {})
    regions = []
    if isinstance(visible, dict) and isinstance(visible.get("body_regions"), list):
        regions = visible.get("body_regions", [])

    important = []
    for r in regions:
        if not isinstance(r, dict):
            continue
        if r.get("is_correct") or r.get("important") or r.get("priority"):
            important.append(normalize_str(r.get("label") or r.get("region_id")))

    if not important:
        score = default_scene_score(scene) if selected_regions else 0.0
        is_correct = bool(selected_regions)
    else:
        score = 0.0
        for label in selected_regions:
            if label in important:
                score += default_scene_score(scene) / max(len(important), 1)
        is_correct = set(important).issubset(set(selected_regions))

    return {
        "score": score,
        "life": 0.0,
        "is_correct": is_correct,
        "your_answer": "、".join(selected_regions) if selected_regions else "未回答",
        "model_answer": "、".join(important) if important else "必要部位を観察する",
        "rationale": "身体所見を部位ごとに確認し、病態推論につなげよう。",
        "details": [],
    }


def score_free_text(scene: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    text = normalize_str(user_text)
    score = default_scene_score(scene) if len(text) >= 8 else 0.0
    return {
        "score": score,
        "life": 0.0,
        "is_correct": bool(score),
        "your_answer": text or "未回答",
        "model_answer": as_text(scene.get("model_answer") or scene.get("ideal_flow") or "観察・判断・対応を簡潔に整理する"),
        "rationale": "自由記述は現段階では簡易採点です。内容の妥当性は振り返りで確認してください。",
        "details": [],
    }


def evaluate_scene(scene: Dict[str, Any], answer: Any) -> Dict[str, Any]:
    stype = normalize_scene_type(scene)

    if stype == "single_choice":
        return score_single(scene, normalize_str(answer))
    if stype == "multiple_choice":
        return score_multiple(scene, answer if isinstance(answer, list) else [])
    if stype == "ranking":
        return score_ranking(scene, answer if isinstance(answer, list) else [])
    if stype == "template_select":
        return score_template(scene, normalize_str(answer))
    if stype == "dialogue_input":
        return score_dialogue(scene, normalize_str(answer))
    if stype == "body_map_select":
        return score_body_map(scene, answer if isinstance(answer, list) else [])
    if stype == "free_text":
        return score_free_text(scene, normalize_str(answer))

    return score_single(scene, normalize_str(answer))


# =========================================================
# Session
# =========================================================
def init_state() -> None:
    defaults = {
        "screen": "login",
        "player_data": None,
        "mode": "single",
        "selected_case_id": None,
        "selected_level_name": "",
        "challenge_case_ids": [],
        "challenge_index": 0,
        "challenge_results": [],
        "scene_index": 0,
        "answers": {},
        "feedbacks": {},
        "score_total": 0.0,
        "score_max": 0.0,
        "life_total": 100.0,
        "random_seed": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_play_state() -> None:
    st.session_state.scene_index = 0
    st.session_state.answers = {}
    st.session_state.feedbacks = {}
    st.session_state.score_total = 0.0
    st.session_state.score_max = 0.0
    st.session_state.life_total = 100.0


def go(screen: str) -> None:
    st.session_state.screen = screen
    scroll_to_top()
    st.rerun()


def answer_key(case_id: str, scene_index: int) -> str:
    return f"{case_id}__scene_{scene_index}__answer"


def feedback_key(case_id: str, scene_index: int) -> str:
    return f"{case_id}__scene_{scene_index}__feedback"


def set_answer(case_id: str, scene_index: int, answer: Any) -> None:
    st.session_state.answers[answer_key(case_id, scene_index)] = answer


def get_answer(case_id: str, scene_index: int) -> Any:
    return st.session_state.answers.get(answer_key(case_id, scene_index))


def set_feedback(case_id: str, scene_index: int, feedback: Dict[str, Any]) -> None:
    st.session_state.feedbacks[feedback_key(case_id, scene_index)] = feedback


def get_feedback(case_id: str, scene_index: int) -> Optional[Dict[str, Any]]:
    return st.session_state.feedbacks.get(feedback_key(case_id, scene_index))


def recompute_scores(case: Dict[str, Any]) -> None:
    total = 0.0
    max_total = 0.0
    life = 100.0
    case_id = case["case_id"]

    for idx, scene in enumerate(case["scenes"]):
        max_total += scene_max_score(scene)
        ans = get_answer(case_id, idx)
        if ans is not None:
            fb = evaluate_scene(scene, ans)
            total += float(fb.get("score", 0))
            life += float(fb.get("life", 0))
            set_feedback(case_id, idx, fb)

    st.session_state.score_total = total
    st.session_state.score_max = max_total
    st.session_state.life_total = max(0.0, min(100.0, life))


# =========================================================
# Rendering helpers
# =========================================================
def render_hero() -> None:
    player = get_player()
    if player and player.get("is_guest"):
        player_line = "プレイヤー：guest（履歴保存なし）"
    elif player:
        player_line = f"プレイヤー：{player.get('player_name')}"
    else:
        player_line = "プレイヤー未設定"
    st.markdown(
        f"""
        <div class="hero">
            <h1>{APP_TITLE}</h1>
            <p>
            Level1〜10制。各Level候補10症例から5症例をランダム提示します。<br>
            プレイヤーごとに進捗・既出症例・スコア履歴を保存し、同じ症例が連続しにくい構成です。
            </p>
            <span class="version">{APP_VERSION}</span>
            <span class="version">{player_line}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(cases: List[Dict[str, Any]], errors: List[Dict[str, str]]) -> None:
    categories = sorted(set(c["category"] for c in cases))
    player = get_player() or {}
    played_count = len(player.get("played_case_ids", []))
    completed_count = len(player.get("completed_levels", []))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="big">{len(cases)}</div><div class="small">読込成功症例</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="big">{played_count}</div><div class="small">既出症例</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="big">{completed_count}</div><div class="small">クリアLevel</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="big">{len(errors)}</div><div class="small">読込エラー</div></div>', unsafe_allow_html=True)


def render_case_card(case: Dict[str, Any]) -> None:
    diff = DIFFICULTY_LABELS.get(case["difficulty"], case["difficulty"] or "未設定")
    complexity = case_complexity(case)
    kw = " ".join([f'<span class="pill">{k}</span>' for k in case.get("keywords", [])[:5]])
    st.markdown(
        f"""
        <div class="card">
            <div class="case-title">{case["title"]}</div>
            <div>
                <span class="pill pill-blue">{case["category_label"]}</span>
                <span class="pill pill-green">{diff}</span>
                <span class="pill pill-orange">{len(case["scenes"])} Scene</span>
                <span class="pill pill-purple">Complexity {complexity}</span>
                <span class="pill">{case["age"]} / {case["sex"]}</span>
            </div>
            <div style="margin-top:6px;">{kw}</div>
            <div class="muted" style="margin-top:8px;">ID: {case["case_id"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_progress(scene_index: int, total: int) -> None:
    ratio = 0 if total <= 0 else (scene_index + 1) / total
    st.markdown(
        f"""
        <div class="progress-wrap">
            <div style="display:flex;justify-content:space-between;font-weight:800;margin-bottom:8px;">
                <span>Scene進行</span><span>{scene_index + 1} / {total}</span>
            </div>
            <div class="progress-line"><div class="progress-fill" style="width:{ratio*100:.1f}%"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_challenge_progress() -> None:
    if st.session_state.get("mode") != "level":
        return
    challenge_ids = st.session_state.get("challenge_case_ids", [])
    if not challenge_ids:
        return
    idx = int(st.session_state.get("challenge_index", 0))
    level_name = st.session_state.get("selected_level_name", "")
    ratio = (idx + 1) / max(len(challenge_ids), 1)
    st.markdown(
        f"""
        <div class="progress-wrap">
            <div style="display:flex;justify-content:space-between;font-weight:800;margin-bottom:8px;">
                <span>{level_name} チャレンジ</span><span>{idx + 1} / {len(challenge_ids)} 症例</span>
            </div>
            <div class="progress-line"><div class="progress-fill" style="width:{ratio*100:.1f}%"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_visible_data(value: Any) -> None:
    if not value:
        return

    if isinstance(value, dict):
        normal_items = {k: v for k, v in value.items() if k not in ("body_regions",)}
        if normal_items:
            st.markdown('<div class="section-title">表示情報</div>', unsafe_allow_html=True)
            for k, v in normal_items.items():
                label = VISIBLE_DATA_LABELS.get(str(k), str(k))
                body = as_text(v)
                if body:
                    st.markdown(
                        f"""
                        <div class="info-box">
                            <div class="label">{label}</div>
                            <div style="white-space:pre-wrap;line-height:1.8;">{body}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        return

    text = as_text(value)
    if text:
        st.markdown(
            f"""
            <div class="info-box">
                <div class="label">表示情報</div>
                <div style="white-space:pre-wrap;line-height:1.8;">{text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_feedback(feedback: Dict[str, Any], max_score: float) -> None:
    is_correct = feedback.get("is_correct", False)
    box_class = "good-box" if is_correct else "warn-box"
    title = "いい判断！" if is_correct else "振り返りポイント"

    st.markdown(
        f"""
        <div class="{box_class}">
            <div class="label">{title}</div>
            <div style="line-height:1.8;">
                得点：{float(feedback.get("score", 0)):.1f} / {max_score:.1f}<br>
                あなたの回答：{feedback.get("your_answer", "未回答")}<br>
                理想回答：{feedback.get("model_answer", "")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if feedback.get("rationale"):
        st.info(feedback["rationale"])

    details = feedback.get("details", [])
    if details:
        with st.expander("詳細フィードバック"):
            for d in details:
                st.write(d)


# =========================================================
# Scene renderers
# =========================================================
def render_single_choice(case: Dict[str, Any], scene: Dict[str, Any], scene_index: int, disabled: bool) -> Any:
    options = normalize_options(scene)
    labels = [o["text"] for o in options]
    key = f"single_{case['case_id']}_{scene_index}"
    if not labels:
        st.warning("選択肢がありません。")
        return None
    return st.radio("選択してください", labels, key=key, disabled=disabled)


def get_required_select_count(scene: Dict[str, Any]) -> Optional[int]:
    """設問文から「2つ選べ」「3つ選択」などの指定数を読み取る。"""
    prompt = normalize_str(scene.get("prompt"))
    if not prompt:
        return None

    # 半角・全角数字の両方に対応
    table = str.maketrans("０１２３４５６７８９", "0123456789")
    prompt = prompt.translate(table)

    m = re.search(r"(\d+)\s*つ\s*(?:選べ|選択)", prompt)
    if not m:
        return None

    try:
        return int(m.group(1))
    except Exception:
        return None


def render_multiple_choice(case: Dict[str, Any], scene: Dict[str, Any], scene_index: int, disabled: bool) -> Any:
    options = normalize_options(scene)
    key_base = f"multi_{case['case_id']}_{scene_index}"

    if not options:
        st.warning("選択肢がありません。")
        return []

    required_count = get_required_select_count(scene)

    if required_count:
        st.caption(f"{required_count}つ選択してください。")
    else:
        st.caption("該当するものを選択してください。")

    selected: List[str] = []
    for i, opt in enumerate(options, start=1):
        label = opt["text"]
        checked = st.checkbox(
            label,
            key=f"{key_base}_{i}",
            disabled=disabled,
        )
        if checked:
            selected.append(label)

    if required_count and not disabled:
        if len(selected) > required_count:
            st.warning(f"{required_count}つまで選択してください。現在 {len(selected)}つ 選択されています。")
        elif 0 < len(selected) < required_count:
            st.info(f"あと {required_count - len(selected)}つ 選択してください。")

    return selected


def render_template_select(case: Dict[str, Any], scene: Dict[str, Any], scene_index: int, disabled: bool) -> Any:
    templates = normalize_templates(scene)
    labels = [t["text"] for t in templates]
    key = f"template_{case['case_id']}_{scene_index}"
    if not labels:
        st.warning("テンプレートがありません。")
        return None
    return st.radio("テンプレートを選択してください", labels, key=key, disabled=disabled)


def render_ranking(case: Dict[str, Any], scene: Dict[str, Any], scene_index: int, disabled: bool) -> Any:
    items = normalize_ranking_items(scene)
    labels = [x["text"] for x in items]
    if not labels:
        st.warning("ランキング項目がありません。")
        return []

    st.caption("上から順に優先順位を選んでください。同じ項目は選ばないでください。")
    selected: List[str] = []
    for rank in range(1, len(labels) + 1):
        remaining = [""] + [x for x in labels if x not in selected]
        key = f"ranking_{case['case_id']}_{scene_index}_{rank}"
        choice = st.selectbox(f"{rank}番目", remaining, key=key, disabled=disabled)
        if choice:
            selected.append(choice)

    return selected


def render_dialogue_input(case: Dict[str, Any], scene: Dict[str, Any], scene_index: int, disabled: bool) -> Any:
    key = f"dialogue_{case['case_id']}_{scene_index}"
    target = normalize_str(scene.get("target"))
    if target:
        st.markdown(f'<span class="pill pill-blue">対話相手：{target}</span>', unsafe_allow_html=True)
    return st.text_area("入力してください", key=key, height=140, disabled=disabled)


def render_free_text(case: Dict[str, Any], scene: Dict[str, Any], scene_index: int, disabled: bool) -> Any:
    key = f"free_{case['case_id']}_{scene_index}"
    return st.text_area("記述してください", key=key, height=150, disabled=disabled)


def render_body_map_select(case: Dict[str, Any], scene: Dict[str, Any], scene_index: int, disabled: bool) -> Any:
    visible = scene.get("visible_data", {})
    regions = []
    template = ""

    if isinstance(visible, dict):
        template = normalize_str(visible.get("body_map_template"))
        if isinstance(visible.get("body_regions"), list):
            regions = visible.get("body_regions")

    if template:
        path = resolve_media_path(template)
        if path:
            safe_image(path, caption="人体図")
        else:
            st.warning(f"人体図テンプレートが見つかりません：{template}")

    labels = []
    region_map = {}
    for r in regions:
        if isinstance(r, dict):
            label = normalize_str(r.get("label") or r.get("region_id") or "部位")
            labels.append(label)
            region_map[label] = r

    key = f"bodymap_{case['case_id']}_{scene_index}"
    selected = st.multiselect("観察したい部位を選択してください", labels, key=key, disabled=disabled)

    for label in selected:
        r = region_map.get(label, {})
        finding = normalize_str(r.get("finding"))
        meaning = normalize_str(r.get("clinical_meaning"))
        st.markdown(
            f"""
            <div class="info-box">
                <div class="label">{label}</div>
                <div style="line-height:1.8;">
                    {finding if finding else "所見の記載なし"}<br>
                    {meaning if meaning else ""}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return selected


def render_answer_ui(case: Dict[str, Any], scene: Dict[str, Any], scene_index: int, disabled: bool) -> Any:
    stype = normalize_scene_type(scene)

    if stype == "single_choice":
        return render_single_choice(case, scene, scene_index, disabled)
    if stype == "multiple_choice":
        return render_multiple_choice(case, scene, scene_index, disabled)
    if stype == "ranking":
        return render_ranking(case, scene, scene_index, disabled)
    if stype == "template_select":
        return render_template_select(case, scene, scene_index, disabled)
    if stype == "dialogue_input":
        return render_dialogue_input(case, scene, scene_index, disabled)
    if stype == "body_map_select":
        return render_body_map_select(case, scene, scene_index, disabled)
    if stype == "free_text":
        return render_free_text(case, scene, scene_index, disabled)

    return render_single_choice(case, scene, scene_index, disabled)


# =========================================================
# Screens
# =========================================================
def screen_login() -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>{APP_TITLE}</h1>
            <p>
            プレイヤー名を入力すると、進捗・既出症例・スコア履歴を保存します。<br>
            試作版の簡易ログインなので、パスワード認証はありません。
            </p>
            <span class="version">{APP_VERSION}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    name = st.text_input("プレイヤー名", placeholder="例：toshikun / 学生A / 001")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("ログイン", type="primary"):
            clean = sanitize_player_name(name)
            if not clean:
                st.warning("プレイヤー名を入力してください。")
            else:
                player = load_player(clean)
                set_player(player)
                go("home")
    with col2:
        if st.button("ゲストで開始"):
            # Guestは既存の players/guest_*.json を読まず、毎回まっさらな状態で開始する。
            # さらに save_player() 側で保存もスキップするため、他ユーザーと履歴が混ざりにくい。
            player = default_player_data("guest")
            player["is_guest"] = True
            set_player(player)
            go("home")

    st.info("通常ログインでは players フォルダに履歴JSONを保存します。Guestモードは毎回リセットされ、履歴保存しません。Streamlit Cloudでは永続保存が保証されないため、正式運用では外部DB化が必要です。")


def screen_home(cases: List[Dict[str, Any]], errors: List[Dict[str, str]]) -> None:
    render_hero()
    render_metrics(cases, errors)

    if errors:
        with st.expander("読込エラーを確認"):
            for e in errors:
                st.error(f"{e['file']}：{e['error']}")

    if not cases:
        st.error("症例JSONが読み込めません。casesフォルダとJSON配置を確認してください。")
        return

    tab1, tab2, tab3, tab4 = st.tabs(["Levelチャレンジ", "症例を選ぶ", "全症例ランダム", "プレイヤー履歴"])

    with tab1:
        render_level_select(cases)

    with tab2:
        render_case_select(cases)

    with tab3:
        render_random_start(cases)

    with tab4:
        render_player_history(cases)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("ログアウト"):
            st.session_state.player_data = None
            st.session_state.screen = "login"
            st.rerun()
    with col2:
        if st.button("症例読み込みキャッシュを更新"):
            load_cases.clear()
            build_level_candidates_cached.clear()
            st.rerun()


def render_level_select(cases: List[Dict[str, Any]]) -> None:
    player = get_player() or default_player_data("guest")
    level_map = build_level_candidates(cases)
    played = set(player.get("played_case_ids", []))
    completed = set(player.get("completed_levels", []))

    st.markdown('<div class="section-title">Levelを選ぶ</div>', unsafe_allow_html=True)
    st.caption(f"各Levelは候補{LEVEL_CANDIDATE_COUNT}症例。その中から未プレイ症例を優先して{LEVEL_PLAY_COUNT}症例をランダム提示します。")

    for i in range(1, LEVEL_COUNT + 1):
        level_name = f"Level{i}"
        ids = level_map.get(level_name, [])
        not_played = [cid for cid in ids if cid not in played]
        done_mark = "クリア済み" if level_name in completed else "未クリア"
        desc = LEVEL_DESCRIPTIONS.get(level_name, level_name)

        with st.container():
            st.markdown(
                f"""
                <div class="level-box">
                    <div class="case-title">{level_name}：{desc}</div>
                    <div>
                        <span class="pill pill-blue">候補 {len(ids)}症例</span>
                        <span class="pill pill-green">未プレイ {len(not_played)}症例</span>
                        <span class="pill pill-orange">{done_mark}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns([1, 2])
            with col1:
                if st.button(f"{level_name}開始", key=f"start_{level_name}", type="primary" if i == int(player.get("current_level", 1)) else "secondary"):
                    start_level_challenge(cases, level_name)
            with col2:
                with st.expander(f"{level_name}候補を見る"):
                    for cid in ids:
                        case = find_case(cases, cid)
                        if case:
                            mark = "✅" if cid in played else "・"
                            st.write(f"{mark} [{case['category_label']}] {case['title']}")


def render_case_select(cases: List[Dict[str, Any]]) -> None:
    st.markdown('<div class="section-title">単症例プレイ</div>', unsafe_allow_html=True)

    categories = ["すべて"] + [get_category_label(c) for c in sorted(set(x["category"] for x in cases))]
    label_to_category = {"すべて": "すべて"}
    for c in sorted(set(x["category"] for x in cases)):
        label_to_category[get_category_label(c)] = c

    col1, col2, col3 = st.columns([1.2, 1.0, 1.0])
    with col1:
        category_label = st.selectbox("カテゴリ", categories, key="case_select_category")
    with col2:
        difficulties = ["すべて"] + sorted(set(DIFFICULTY_LABELS.get(x["difficulty"], x["difficulty"] or "未設定") for x in cases))
        difficulty_label = st.selectbox("難易度", difficulties, key="case_select_difficulty")
    with col3:
        sort_mode = st.selectbox("並び順", ["ファイル順", "カテゴリ順", "複雑度順", "ランダム"], key="case_select_sort")

    filtered = cases
    selected_category = label_to_category.get(category_label, "すべて")
    if selected_category != "すべて":
        filtered = [c for c in filtered if c["category"] == selected_category]

    if difficulty_label != "すべて":
        filtered = [c for c in filtered if DIFFICULTY_LABELS.get(c["difficulty"], c["difficulty"] or "未設定") == difficulty_label]

    if sort_mode == "カテゴリ順":
        filtered = sorted(filtered, key=lambda x: (x["category"], x["title"]))
    elif sort_mode == "複雑度順":
        filtered = sorted(filtered, key=lambda x: case_complexity(x))
    elif sort_mode == "ランダム":
        rng = random.Random(st.session_state.random_seed)
        filtered = list(filtered)
        rng.shuffle(filtered)
    else:
        filtered = sorted(filtered, key=lambda x: str(x["path"]))

    st.markdown(f'<div class="muted">表示中：{len(filtered)}症例</div>', unsafe_allow_html=True)

    if not filtered:
        st.warning("条件に合う症例がありません。")
        return

    case_options = {
        f"{i+1:03d}. [{c['category_label']}] {c['title']}": c["case_id"]
        for i, c in enumerate(filtered)
    }
    selected_label = st.selectbox("症例一覧", list(case_options.keys()), key="case_select_list")
    selected_case = find_case(cases, case_options[selected_label])

    if selected_case:
        render_case_card(selected_case)
        if st.button("この症例を開始", type="primary", key="case_select_start"):
            start_single_case(selected_case["case_id"])


def render_random_start(cases: List[Dict[str, Any]]) -> None:
    st.markdown('<div class="section-title">全症例ランダム</div>', unsafe_allow_html=True)
    player = get_player() or default_player_data("guest")
    played = set(player.get("played_case_ids", []))
    unplayed = [c for c in cases if c["case_id"] not in played]

    st.write(f"未プレイ症例：{len(unplayed)} / {len(cases)}")
    if st.button("未プレイ優先でランダム1症例を開始", type="primary"):
        pool = unplayed if unplayed else cases
        selected = random.choice(pool)
        start_single_case(selected["case_id"])


def render_player_history(cases: List[Dict[str, Any]]) -> None:
    player = get_player() or {}
    st.markdown('<div class="section-title">プレイヤー履歴</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総プレイ回数", player.get("total_play_count", 0))
    with col2:
        st.metric("既出症例", len(player.get("played_case_ids", [])))
    with col3:
        st.metric("クリアLevel", len(player.get("completed_levels", [])))

    level_history = player.get("level_history", {})
    if level_history:
        st.markdown("#### Level履歴")
        for level_name, hist in sorted(level_history.items()):
            st.write(f"- {level_name}: best {float(hist.get('best_percent', 0)):.1f}% / last {float(hist.get('last_percent', 0)):.1f}% / {hist.get('last_played_at', '')}")

    case_history = player.get("case_history", {})
    if case_history:
        with st.expander("症例履歴を見る"):
            for cid, hist in sorted(case_history.items(), key=lambda x: x[1].get("last_played_at", ""), reverse=True):
                st.write(f"- {hist.get('last_played_at', '')}｜{hist.get('best_percent', 0):.1f}%｜{hist.get('title', cid)}")


def screen_intro(cases: List[Dict[str, Any]]) -> None:
    case = find_case(cases, st.session_state.selected_case_id)
    if not case:
        st.error("選択中の症例が見つかりません。")
        if st.button("トップへ戻る"):
            go("home")
        return

    render_challenge_progress()
    render_case_card(case)

    raw = case.get("raw", {})
    overview = as_text(raw.get("overview") or raw.get("summary"))
    if overview:
        st.markdown(
            f"""
            <div class="info-box">
                <div class="label">症例概要</div>
                <div style="white-space:pre-wrap;line-height:1.8;">{overview}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("開始する", type="primary"):
            st.session_state.scene_index = 0
            go("scene")
    with col2:
        if st.button("ホームへ戻る"):
            go("home")


def screen_scene(cases: List[Dict[str, Any]]) -> None:
    case = find_case(cases, st.session_state.selected_case_id)
    if not case:
        st.error("症例が見つかりません。")
        if st.button("トップへ戻る"):
            go("home")
        return

    scenes = case["scenes"]
    if not scenes:
        st.error("この症例にはSceneがありません。")
        return

    scene_index = st.session_state.scene_index
    if scene_index >= len(scenes):
        recompute_scores(case)
        go("result")
        return

    render_challenge_progress()

    scene = scenes[scene_index]
    case_id = case["case_id"]
    stype = normalize_scene_type(scene)
    submitted = get_feedback(case_id, scene_index) is not None

    render_progress(scene_index, len(scenes))

    st.markdown(
        f"""
        <div class="scene-card">
            <div>
                <span class="pill pill-blue">{SCENE_TYPE_LABELS.get(stype, stype)}</span>
                <span class="pill pill-green">{case["category_label"]}</span>
                <span class="pill">{case["difficulty"] or "難易度未設定"}</span>
            </div>
            <div class="scene-title">{normalize_str(scene.get("title") or f"Scene {scene_index+1}")}</div>
            <div class="muted">{normalize_str(scene.get("phase"))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    goal = normalize_str(scene.get("scene_goal"))
    if goal:
        st.markdown(
            f"""
            <div class="warn-box">
                <div class="label">このSceneの目標</div>
                <div style="line-height:1.8;">{goal}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    text = as_text(scene.get("text"))
    if text:
        st.markdown(
            f"""
            <div class="card">
                <div class="label">状況</div>
                <div class="scene-text">{text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    render_media(scene)
    render_visible_data(scene.get("visible_data"))

    prompt = normalize_str(scene.get("prompt"))
    if prompt:
        st.markdown(
            f"""
            <div class="card">
                <div class="label">設問</div>
                <div class="scene-text">{prompt}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    answer = render_answer_ui(case, scene, scene_index, disabled=submitted)

    if not submitted:
        if st.button("回答する", type="primary"):
            set_answer(case_id, scene_index, answer)
            feedback = evaluate_scene(scene, answer)
            set_feedback(case_id, scene_index, feedback)
            recompute_scores(case)
            st.rerun()
    else:
        feedback = get_feedback(case_id, scene_index)
        if feedback:
            render_feedback(feedback, scene_max_score(scene))

        col1, col2 = st.columns(2)
        with col1:
            if scene_index < len(scenes) - 1:
                if st.button("次のSceneへ", type="primary"):
                    st.session_state.scene_index += 1
                    go("scene")
            else:
                if st.button("結果を見る", type="primary"):
                    recompute_scores(case)
                    go("result")
        with col2:
            if st.button("ホームへ戻る"):
                go("home")


def rank_from_percent(percent: float) -> Tuple[str, str]:
    if percent >= 85:
        return "Excellent", "現場判断の流れがかなり良いです。"
    if percent >= 70:
        return "Good", "大枠は良好です。細部の優先順位を確認しましょう。"
    if percent >= 50:
        return "Normal", "流れは追えています。初期評価と再判断を復習しましょう。"
    return "Review", "要復習です。観察→判断→優先行動のつながりを見直しましょう。"


def render_debriefing(case: Dict[str, Any]) -> None:
    debrief = case.get("debriefing", {}) or {}

    summary = as_text(debrief.get("summary"))
    ideal_actions = debrief.get("ideal_actions", [])
    good_points = debrief.get("good_points", [])
    cautions = debrief.get("cautions", [])

    st.markdown('<div class="section-title">症例まとめ</div>', unsafe_allow_html=True)
    if summary:
        st.markdown(
            f"""
            <div class="info-box">
                <div style="white-space:pre-wrap;line-height:1.8;">{summary}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="card"><div class="label">理想対応</div>', unsafe_allow_html=True)
        for x in ideal_actions if isinstance(ideal_actions, list) else [ideal_actions]:
            st.write(f"- {as_text(x)}")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card"><div class="label">良かった点</div>', unsafe_allow_html=True)
        for x in good_points if isinstance(good_points, list) else [good_points]:
            st.write(f"- {as_text(x)}")
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="card"><div class="label">注意点</div>', unsafe_allow_html=True)
        for x in cautions if isinstance(cautions, list) else [cautions]:
            st.write(f"- {as_text(x)}")
        st.markdown('</div>', unsafe_allow_html=True)


def record_current_case_result(case: Dict[str, Any], percent: float) -> None:
    mode = st.session_state.get("mode", "single")
    level_name = st.session_state.get("selected_level_name", "")

    # 二重記録防止
    result_key = f"{case['case_id']}__recorded__{mode}__{level_name}__{st.session_state.get('challenge_index', 0)}"
    if st.session_state.get(result_key):
        return
    st.session_state[result_key] = True

    mark_case_played(case, percent, mode, level_name)

    if mode == "level":
        results = st.session_state.setdefault("challenge_results", [])
        results.append({
            "case_id": case["case_id"],
            "title": case["title"],
            "score": st.session_state.score_total,
            "max_score": st.session_state.score_max,
            "percent": percent,
            "life": st.session_state.life_total,
        })


def screen_result(cases: List[Dict[str, Any]]) -> None:
    case = find_case(cases, st.session_state.selected_case_id)
    if not case:
        st.error("症例が見つかりません。")
        if st.button("トップへ戻る"):
            go("home")
        return

    recompute_scores(case)

    percent = 0.0
    if st.session_state.score_max > 0:
        percent = st.session_state.score_total / st.session_state.score_max * 100

    record_current_case_result(case, percent)

    rank, comment = rank_from_percent(percent)

    st.markdown(
        f"""
        <div class="hero">
            <h1>結果：{rank}</h1>
            <p>{comment}</p>
            <span class="version">Score {st.session_state.score_total:.1f} / {st.session_state.score_max:.1f} ｜ {percent:.1f}% ｜ Life {st.session_state.life_total:.0f}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_challenge_progress()
    render_case_card(case)

    st.markdown('<div class="section-title">Scene別ふりかえり</div>', unsafe_allow_html=True)
    for idx, scene in enumerate(case["scenes"]):
        fb = get_feedback(case["case_id"], idx)
        title = normalize_str(scene.get("title") or f"Scene {idx+1}")
        with st.expander(f"Scene {idx+1}: {title}", expanded=False):
            if fb:
                render_feedback(fb, scene_max_score(scene))
            else:
                st.warning("未回答")

    render_debriefing(case)

    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.get("mode") == "level":
            challenge_ids = st.session_state.get("challenge_case_ids", [])
            idx = int(st.session_state.get("challenge_index", 0))
            label = "次の症例へ" if idx < len(challenge_ids) - 1 else "Level結果を見る"
            if st.button(label, type="primary"):
                move_after_case_result(cases)
        else:
            if st.button("同じ症例をもう一度", type="primary"):
                reset_play_state()
                go("intro")
    with col2:
        if st.button("ホームへ戻る"):
            reset_play_state()
            st.session_state.selected_case_id = None
            go("home")


def screen_level_result(cases: List[Dict[str, Any]]) -> None:
    level_name = st.session_state.get("selected_level_name", "")
    results = st.session_state.get("challenge_results", [])
    challenge_ids = st.session_state.get("challenge_case_ids", [])

    total_score = sum(float(r.get("score", 0)) for r in results)
    total_max = sum(float(r.get("max_score", 0)) for r in results)
    percent = (total_score / total_max * 100) if total_max else 0.0
    rank, comment = rank_from_percent(percent)

    mark_level_completed(level_name, challenge_ids, percent)

    st.markdown(
        f"""
        <div class="hero">
            <h1>{level_name} 結果：{rank}</h1>
            <p>{comment}</p>
            <span class="version">Total {total_score:.1f} / {total_max:.1f} ｜ {percent:.1f}%</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">今回の5症例</div>', unsafe_allow_html=True)
    for i, r in enumerate(results, start=1):
        st.markdown(
            f"""
            <div class="card">
                <div class="case-title">{i}. {r.get("title")}</div>
                <span class="pill pill-blue">{float(r.get("percent", 0)):.1f}%</span>
                <span class="pill pill-green">Score {float(r.get("score", 0)):.1f} / {float(r.get("max_score", 0)):.1f}</span>
                <span class="pill">Life {float(r.get("life", 100)):.0f}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("同じLevelを再挑戦", type="primary"):
            start_level_challenge(cases, level_name)
    with col2:
        if st.button("ホームへ戻る"):
            st.session_state.mode = "single"
            st.session_state.selected_case_id = None
            st.session_state.challenge_case_ids = []
            st.session_state.challenge_results = []
            go("home")


# =========================================================
# Main
# =========================================================
def main() -> None:
    inject_css()
    init_state()

    cases, errors = load_cases()

    screen = st.session_state.screen

    if screen != "login" and not get_player():
        st.session_state.screen = "login"
        st.rerun()

    if screen == "login":
        screen_login()
    elif screen == "home":
        screen_home(cases, errors)
    elif screen == "intro":
        screen_intro(cases)
    elif screen == "scene":
        screen_scene(cases)
    elif screen == "result":
        screen_result(cases)
    elif screen == "level_result":
        screen_level_result(cases)
    else:
        st.session_state.screen = "home"
        st.rerun()


if __name__ == "__main__":
    main()
