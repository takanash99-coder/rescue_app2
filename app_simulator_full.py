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
# ROGER LEVEL MAP EDITION 2026-05-18
#
# 方針：
# - 正本は app_simulator_full.py
# - Level画面は文字説明を極力少なくする
# - Level1を上、Level10を下に配置するスマホ縦スクロール型
# - クリア済みLevelは緑、現在Levelは青、未クリアLevelは灰色
# - Levelボタンを押すと、そのLevelの5症例チャレンジへ進む
# - 未クリアで未到達のLevelは押せない
# - 救急車は現在進行位置の近くに表示する
# - 症例本文・JSON構造は変更しない
# =========================================================

st.set_page_config(
    page_title="「国試から学ぶ」救急救命士臨床推論シミュレーション",
    page_icon="🚑",
    layout="wide",
)

APP_VERSION = "ROGER_LEVEL_HTML_CARDS_2026_05_18"
APP_TITLE = "「国試から学ぶ」救急救命士臨床推論シミュレーション"

REPO_ROOT = Path(__file__).resolve().parent
CASES_DIR = REPO_ROOT / "cases"
CASE_MEDIA_DIR = CASES_DIR / "media"
CASE_AUDIO_DIR = CASES_DIR / "audio"
CASE_LUNG_SOUNDS_DIR = CASES_DIR / "lung_sounds"
ROOT_MEDIA_DIR = REPO_ROOT / "media"
PLAYERS_DIR = REPO_ROOT / "players"

LEVEL_COUNT = 10
LEVEL_CANDIDATE_COUNT = 10
LEVEL_PLAY_COUNT = 5
CLEAR_PERCENT = 60.0

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

DIFFICULTY_SCORE = {
    "Easy": 1,
    "easy": 1,
    "Normal": 2,
    "normal": 2,
    "Hard": 3,
    "hard": 3,
    "": 2,
}

VISIBLE_DATA_LABELS = {
    "dispatch_information": "通報内容",
    "history": "聴取内容",
    "vitals": "バイタルサイン",
    "body_findings": "身体所見",
    "assessment": "評価",
    "location": "場所",
    "environment": "周囲環境",
    "mechanism": "受傷機転",
    "chief_complaint": "主訴",
    "consciousness": "意識",
    "mental_status": "意識状態",
    "airway": "気道",
    "breathing": "呼吸",
    "circulation": "循環",
    "respiratory_rate": "呼吸数",
    "pulse_rate": "脈拍数",
    "heart_rate": "心拍数",
    "blood_pressure": "血圧",
    "bp": "血圧",
    "spo2": "SpO₂",
    "temperature": "体温",
    "skin": "皮膚",
    "bleeding": "出血",
    "ecg": "心電図",
    "body_regions": "観察部位",
}

LEVEL_ANIMALS = {
    1: "🐥",
    2: "🐰",
    3: "🐿️",
    4: "🦊",
    5: "🐒",
    6: "🐺",
    7: "🦍",
    8: "🦏",
    9: "🐯",
    10: "🦁",
}


# =========================================================
# CSS
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
            --blue: #0ea5e9;
            --blue2: #0284c7;
            --green: #22c55e;
            --green2: #16a34a;
            --gray: #9ca3af;
            --gray2: #6b7280;
            --red: #dc2626;
            --red2: #991b1b;
            --yellow: #facc15;
            --shadow: 0 10px 28px rgba(20, 35, 56, 0.08);
        }

        html, body, [class*="css"], .stApp {
            font-family: "BIZ UDPGothic", "Yu Gothic UI", "Meiryo", sans-serif !important;
            color: var(--text);
        }

        .stApp {
            background: linear-gradient(180deg, #f8fbff 0%, #edf3fa 100%);
        }

        .app-title {
            font-size: 1.2rem;
            font-weight: 900;
            margin: 0.4rem 0 0.6rem 0;
            line-height: 1.4;
        }

        .tiny-muted {
            color: var(--muted);
            font-size: 0.82rem;
            line-height: 1.5;
        }

        .card {
            background: white;
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 16px;
            box-shadow: var(--shadow);
            margin-bottom: 12px;
        }

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
            margin-bottom: 6px;
        }

        .scene-text {
            font-size: 1.04rem;
            line-height: 1.9;
            white-space: pre-wrap;
        }

        .pill {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: #eef3fb;
            color: #1f3558;
            font-size: 0.78rem;
            font-weight: 800;
            margin-right: 4px;
            margin-bottom: 4px;
        }

        .pill-green { background: #dcfce7; color: #166534; }
        .pill-blue { background: #e0f2fe; color: #075985; }
        .pill-gray { background: #f3f4f6; color: #4b5563; }
        .pill-red { background: #fee2e2; color: #991b1b; }

        .good-box {
            background: #ecfdf5;
            border-left: 6px solid #22c55e;
            border-radius: 14px;
            padding: 13px 15px;
            margin: 12px 0;
        }

        .bad-box {
            background: #fef2f2;
            border-left: 6px solid #ef4444;
            border-radius: 14px;
            padding: 13px 15px;
            margin: 12px 0;
        }

        .warn-box {
            background: #fffbeb;
            border-left: 6px solid #f59e0b;
            border-radius: 14px;
            padding: 13px 15px;
            margin: 12px 0;
        }

        .hero-title {
            max-width: 760px;
            margin: 0.5rem auto 0.95rem auto;
            padding: 18px 18px;
            border-radius: 26px;
            background:
                radial-gradient(circle at top left, rgba(56,189,248,0.28), transparent 36%),
                radial-gradient(circle at bottom right, rgba(34,197,94,0.26), transparent 34%),
                linear-gradient(135deg, #ffffff 0%, #eff8ff 100%);
            border: 1px solid rgba(14,165,233,0.20);
            box-shadow: 0 14px 36px rgba(14, 45, 80, 0.12);
            text-align: center;
        }

        .hero-main {
            font-size: clamp(1.45rem, 4vw, 2.35rem);
            font-weight: 1000;
            line-height: 1.22;
            letter-spacing: 0.02em;
            color: #0f172a;
            text-shadow: 0 2px 0 rgba(255,255,255,0.9);
        }

        .hero-main .blue {
            color: #0284c7;
        }

        .hero-main .green {
            color: #16a34a;
        }

        .hero-sub {
            display: inline-block;
            margin-top: 8px;
            padding: 5px 12px;
            border-radius: 999px;
            background: linear-gradient(90deg, #0ea5e9, #22c55e);
            color: white;
            font-weight: 900;
            font-size: 0.82rem;
            letter-spacing: 0.06em;
        }

        .level-map-wrap {
            position: relative;
            width: min(520px, 96vw);
            height: 1380px;
            margin: 0 auto 18px auto;
            border-radius: 28px;
            background:
                radial-gradient(circle at 12% 9%, rgba(34,197,94,0.13), transparent 12%),
                radial-gradient(circle at 85% 78%, rgba(14,165,233,0.10), transparent 16%),
                linear-gradient(180deg, #ecffc9 0%, #dff5ad 100%);
            border: 1px solid rgba(120, 160, 90, 0.25);
            box-shadow: 0 14px 38px rgba(53, 91, 45, 0.10);
            overflow: hidden;
        }

        .level-map-svg {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            z-index: 0;
            pointer-events: none;
        }

        .map-deco {
            position: absolute;
            z-index: 1;
            font-size: 1.9rem;
            opacity: 0.85;
            filter: drop-shadow(0 3px 5px rgba(0,0,0,0.10));
            user-select: none;
        }

        .level-node {
            position: absolute;
            width: 78px;
            height: 78px;
            transform: translate(-50%, -50%);
            z-index: 5;
        }

        .level-node.boss {
            width: 96px;
            height: 96px;
            z-index: 7;
        }

        .level-node div[data-testid="stButton"] > button {
            width: 78px !important;
            height: 78px !important;
            min-height: 78px !important;
            padding: 0 !important;
            border-radius: 999px !important;
            font-size: 1.7rem !important;
            font-weight: 1000 !important;
            border: 5px solid #ffffff !important;
            box-shadow: 0 10px 22px rgba(0,0,0,0.18) !important;
            line-height: 1 !important;
        }

        .level-node.boss div[data-testid="stButton"] > button {
            width: 96px !important;
            height: 96px !important;
            min-height: 96px !important;
            font-size: 1.95rem !important;
            box-shadow: 0 0 0 8px rgba(239,68,68,0.20), 0 14px 32px rgba(153,27,27,0.34) !important;
        }

        .level-node.completed div[data-testid="stButton"] > button {
            background: linear-gradient(180deg, #34d399 0%, #16a34a 100%) !important;
            color: white !important;
        }

        .level-node.current div[data-testid="stButton"] > button {
            background: linear-gradient(180deg, #38bdf8 0%, #0284c7 100%) !important;
            color: white !important;
            box-shadow: 0 0 0 8px rgba(14,165,233,0.21), 0 11px 25px rgba(2,132,199,0.27) !important;
        }

        .level-node.locked div[data-testid="stButton"] > button {
            background: linear-gradient(180deg, #d1d5db 0%, #6b7280 100%) !important;
            color: white !important;
            opacity: 0.92;
        }

        .level-node.boss div[data-testid="stButton"] > button {
            background: linear-gradient(180deg, #ef4444 0%, #991b1b 100%) !important;
            color: white !important;
        }

        .level-animal {
            position: absolute;
            z-index: 6;
            transform: translate(-50%, -50%);
            font-size: 2.55rem;
            filter: drop-shadow(0 5px 7px rgba(0,0,0,0.15));
            user-select: none;
            pointer-events: none;
        }

        .level-animal.boss {
            font-size: 3.75rem;
            z-index: 8;
        }

        .ambulance-map {
            position: absolute;
            z-index: 9;
            transform: translate(-50%, -50%);
            font-size: 2.45rem;
            filter: drop-shadow(0 6px 8px rgba(0,0,0,0.18));
            animation: ambulance-bounce 1.3s ease-in-out infinite;
            pointer-events: none;
            user-select: none;
        }

        @keyframes ambulance-bounce {
            0%, 100% { transform: translate(-50%, -50%) translateY(0); }
            50% { transform: translate(-50%, -50%) translateY(-6px); }
        }

        .boss-aura-map {
            position: absolute;
            width: 150px;
            height: 150px;
            transform: translate(-50%, -50%);
            border-radius: 999px;
            background: radial-gradient(circle, rgba(239,68,68,0.32), rgba(168,85,247,0.14), rgba(0,0,0,0));
            z-index: 2;
            animation: boss-pulse 1.8s ease-in-out infinite;
            pointer-events: none;
        }

        @keyframes boss-pulse {
            0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.8; }
            50% { transform: translate(-50%, -50%) scale(1.10); opacity: 1; }
        }


        .history-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 10px;
        }

        .history-item {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 12px;
            box-shadow: 0 7px 18px rgba(20,35,56,0.06);
        }

        div[data-testid="stButton"] > button {
            border-radius: 999px;
            min-height: 64px;
            font-size: 1.65rem;
            font-weight: 950;
            border: 4px solid #ffffff;
            box-shadow: 0 8px 18px rgba(0,0,0,0.16);
            white-space: normal !important;
        }







        .login-box {
            max-width: 520px;
            margin: 0 auto;
        }

        .result-card {
            background: linear-gradient(135deg, #ffffff, #f8fbff);
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 18px;
            box-shadow: var(--shadow);
            margin-bottom: 14px;
        }

        .score-big {
            font-size: 2.1rem;
            font-weight: 950;
            line-height: 1.2;
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
            .block-container {
                padding-left: 0.8rem !important;
                padding-right: 0.8rem !important;
                padding-top: 0.7rem !important;
            }

            .app-title {
                font-size: 1.02rem;
            }

            .hero-title { padding: 15px 12px; border-radius: 22px; }
            .hero-main { font-size: 1.34rem; }
            .level-map-wrap { width: 96vw; height: 1320px; border-radius: 22px; }
            .level-node { width: 70px; height: 70px; }
            .level-node div[data-testid="stButton"] > button { width: 70px !important; height: 70px !important; min-height: 70px !important; font-size: 2.05rem !important; }
            .level-node.boss { width: 88px; height: 88px; }
            .level-node.boss div[data-testid="stButton"] > button { width: 88px !important; height: 88px !important; min-height: 88px !important; }
            .level-animal { font-size: 2.55rem; }
            .level-animal.boss { font-size: 3.35rem; }
            .ambulance-map { font-size: 2.55rem; }

            .scene-card, .card {
                padding: 14px;
                border-radius: 16px;
            }
        }

        /* =========================================================
           Simple vertical level buttons: stable smartphone UI
           ========================================================= */
        .simple-level-wrap {
            max-width: 520px;
            margin: 0 auto 18px auto;
            padding: 14px 10px 20px 10px;
            border-radius: 26px;
            background:
                radial-gradient(circle at 14% 8%, rgba(34,197,94,0.16), transparent 18%),
                radial-gradient(circle at 85% 92%, rgba(239,68,68,0.10), transparent 18%),
                linear-gradient(180deg, #f1ffd6 0%, #e4f7bd 100%);
            border: 1px solid rgba(120, 160, 90, 0.25);
            box-shadow: 0 14px 38px rgba(53, 91, 45, 0.10);
        }

        .simple-level-row {
            display: grid;
            grid-template-columns: 0.45fr minmax(300px, 430px) 0.45fr;
            align-items: center;
            min-height: 132px;
            column-gap: 8px;
        }

        .simple-level-animal {
            font-size: 2.85rem;
            text-align: center;
            filter: drop-shadow(0 5px 8px rgba(0,0,0,0.14));
            user-select: none;
            line-height: 1;
        }

        .simple-level-animal.boss {
            font-size: 3.75rem;
        }

        .simple-level-ambulance {
            font-size: 2.55rem;
            text-align: center;
            filter: drop-shadow(0 5px 8px rgba(0,0,0,0.14));
            animation: simple-ambulance-bounce 1.3s ease-in-out infinite;
            user-select: none;
            line-height: 1;
        }

        @keyframes simple-ambulance-bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }

        .simple-level-row div[data-testid="stButton"] > button {
            width: 100% !important;
            min-height: 126px !important;
            border-radius: 42px !important;
            font-size: 2.05rem !important;
            font-weight: 1000 !important;
            border: 4px solid #ffffff !important;
            box-shadow: 0 10px 22px rgba(0,0,0,0.13) !important;
            letter-spacing: 0.02em !important;
        }

        .simple-level-row.completed div[data-testid="stButton"] > button {
            background: linear-gradient(180deg, #34d399 0%, #16a34a 100%) !important;
            color: #ffffff !important;
        }

        .simple-level-row.current div[data-testid="stButton"] > button {
            background: linear-gradient(180deg, #38bdf8 0%, #0284c7 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 0 0 7px rgba(14,165,233,0.18), 0 12px 26px rgba(2,132,199,0.25) !important;
        }

        .simple-level-row.locked div[data-testid="stButton"] > button {
            background: linear-gradient(180deg, #d1d5db 0%, #6b7280 100%) !important;
            color: #ffffff !important;
            opacity: 0.92 !important;
        }

        .simple-level-row.boss div[data-testid="stButton"] > button {
            min-height: 124px !important;
            border-radius: 42px !important;
            background: linear-gradient(180deg, #ef4444 0%, #991b1b 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 0 0 8px rgba(239,68,68,0.18), 0 14px 34px rgba(153,27,27,0.28) !important;
        }

        .simple-level-spacer {
            width: 4px;
            height: 38px;
            margin: 0 auto;
            border-radius: 999px;
            background: rgba(75,85,99,0.30);
        }

        .simple-level-spacer.completed {
            background: rgba(34,197,94,0.62);
        }

        @media (max-width: 768px) {
            .simple-level-wrap {
                max-width: 100%;
                padding: 12px 6px 18px 6px;
                border-radius: 22px;
            }

            .simple-level-row {
                grid-template-columns: 0.28fr minmax(260px, 2.4fr) 0.28fr;
                min-height: 126px;
                column-gap: 4px;
            }

            .simple-level-row div[data-testid="stButton"] > button {
                min-height: 126px !important;
                font-size: 1.88rem !important;
                border-radius: 38px !important;
            }

            .simple-level-row.boss div[data-testid="stButton"] > button {
                min-height: 126px !important;
                font-size: 1.58rem !important;
            }

            .simple-level-animal {
                font-size: 2.55rem;
            }

            .simple-level-animal.boss {
                font-size: 3.35rem;
            }
        }


        @media (max-width: 768px) {
            .simple-level-row > div:nth-child(2) {
                min-width: 74vw !important;
            }

            .simple-level-row div[data-testid="stButton"] > button {
                width: 100% !important;
                min-height: 126px !important;
                font-size: 1.88rem !important;
                border-radius: 38px !important;
                border-width: 5px !important;
            }

            .simple-level-row.boss div[data-testid="stButton"] > button {
                min-height: 138px !important;
                font-size: 1.72rem !important;
                border-radius: 42px !important;
            }

            .simple-level-animal {
                font-size: 2.35rem !important;
            }

            .simple-level-animal.boss {
                font-size: 3.1rem !important;
            }

            .simple-level-ambulance {
                font-size: 2.35rem !important;
            }
        }


        /* =========================================================
           Level selection bar UI: button only, mobile-first
           ========================================================= */
        .level-bar-wrap {
            max-width: 560px;
            margin: 0 auto 20px auto;
            padding: 10px 6px 18px 6px;
        }

        .level-bar-row {
            margin: 12px 0;
        }

        .level-bar-row div[data-testid="stButton"] > button {
            width: 100% !important;
            min-height: 96px !important;
            border-radius: 999px !important;
            border: 5px solid #ffffff !important;
            font-size: 1.85rem !important;
            font-weight: 1000 !important;
            letter-spacing: 0.03em !important;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.14) !important;
        }

        .level-bar-row.completed div[data-testid="stButton"] > button {
            background: linear-gradient(180deg, #34d399 0%, #16a34a 100%) !important;
            color: #ffffff !important;
        }

        .level-bar-row.current div[data-testid="stButton"] > button {
            background: linear-gradient(180deg, #38bdf8 0%, #0284c7 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 0 0 8px rgba(14,165,233,0.18), 0 14px 30px rgba(2,132,199,0.24) !important;
        }

        .level-bar-row.locked div[data-testid="stButton"] > button {
            background: linear-gradient(180deg, #d1d5db 0%, #6b7280 100%) !important;
            color: #ffffff !important;
            opacity: 0.92 !important;
        }

        .level-bar-row.boss div[data-testid="stButton"] > button {
            min-height: 112px !important;
            background: linear-gradient(180deg, #ef4444 0%, #991b1b 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 0 0 8px rgba(239,68,68,0.18), 0 16px 34px rgba(153,27,27,0.30) !important;
        }

        @media (max-width: 768px) {
            .level-bar-wrap {
                max-width: 100%;
                padding-left: 0;
                padding-right: 0;
            }

            .level-bar-row {
                margin: 13px 0;
            }

            .level-bar-row div[data-testid="stButton"] > button {
                min-height: 104px !important;
                font-size: 1.78rem !important;
                border-radius: 999px !important;
                border-width: 5px !important;
            }

            .level-bar-row.boss div[data-testid="stButton"] > button {
                min-height: 122px !important;
                font-size: 1.72rem !important;
            }
        }


        /* =========================================================
           Huge center level cards: smartphone-first final override
           ========================================================= */
        .level-bar-wrap {
            max-width: 620px !important;
            width: min(96vw, 620px) !important;
            margin: 0 auto 22px auto !important;
            padding: 4px 0 18px 0 !important;
        }

        .level-bar-row {
            width: 100% !important;
            margin: 16px auto !important;
        }

        .level-bar-row div[data-testid="stButton"] > button {
            width: 100% !important;
            min-height: 150px !important;
            border-radius: 34px !important;
            border: 6px solid #ffffff !important;
            font-size: 2.35rem !important;
            font-weight: 1000 !important;
            letter-spacing: 0.04em !important;
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.16) !important;
        }

        .level-bar-row.completed div[data-testid="stButton"] > button {
            background: linear-gradient(180deg, #34d399 0%, #16a34a 100%) !important;
            color: #ffffff !important;
        }

        .level-bar-row.current div[data-testid="stButton"] > button {
            background: linear-gradient(180deg, #38bdf8 0%, #0284c7 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 0 0 10px rgba(14,165,233,0.18), 0 18px 40px rgba(2,132,199,0.28) !important;
        }

        .level-bar-row.locked div[data-testid="stButton"] > button {
            background: linear-gradient(180deg, #d1d5db 0%, #6b7280 100%) !important;
            color: #ffffff !important;
            opacity: 0.92 !important;
        }

        .level-bar-row.boss div[data-testid="stButton"] > button {
            min-height: 175px !important;
            border-radius: 40px !important;
            background: linear-gradient(180deg, #ef4444 0%, #991b1b 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 0 0 11px rgba(239,68,68,0.18), 0 20px 46px rgba(153,27,27,0.32) !important;
        }

        @media (max-width: 768px) {
            .level-bar-wrap {
                width: 94vw !important;
                max-width: 94vw !important;
                padding-left: 0 !important;
                padding-right: 0 !important;
            }

            .level-bar-row {
                margin: 17px auto !important;
            }

            .level-bar-row div[data-testid="stButton"] > button {
                min-height: 31vh !important;
                max-height: 240px !important;
                border-radius: 34px !important;
                font-size: clamp(2.05rem, 8vw, 2.75rem) !important;
                border-width: 6px !important;
            }

            .level-bar-row.boss div[data-testid="stButton"] > button {
                min-height: 34vh !important;
                max-height: 260px !important;
                font-size: clamp(1.95rem, 7vw, 2.55rem) !important;
                border-radius: 40px !important;
            }
        }


        /* =========================================================
           HTML Level cards: true huge tappable cards
           Streamlit st.button is not used here because markdown divs
           cannot reliably wrap Streamlit widgets.
           ========================================================= */
        .html-level-wrap {
            width: min(94vw, 760px);
            margin: 0 auto 24px auto;
            padding: 4px 0 18px 0;
        }

        .html-level-card,
        .html-level-card-disabled {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            min-height: 150px;
            margin: 18px auto;
            border-radius: 34px;
            border: 6px solid #ffffff;
            box-shadow: 0 16px 34px rgba(15, 23, 42, 0.16);
            text-decoration: none !important;
            font-size: clamp(2.0rem, 6vw, 3.0rem);
            font-weight: 1000;
            letter-spacing: 0.04em;
            line-height: 1.1;
            user-select: none;
            box-sizing: border-box;
        }

        .html-level-card.completed {
            background: linear-gradient(180deg, #34d399 0%, #16a34a 100%);
            color: #ffffff !important;
        }

        .html-level-card.current {
            background: linear-gradient(180deg, #38bdf8 0%, #0284c7 100%);
            color: #ffffff !important;
            box-shadow: 0 0 0 10px rgba(14,165,233,0.18), 0 18px 42px rgba(2,132,199,0.28);
        }

        .html-level-card.boss {
            min-height: 178px;
            border-radius: 42px;
            background: linear-gradient(180deg, #ef4444 0%, #991b1b 100%);
            color: #ffffff !important;
            box-shadow: 0 0 0 11px rgba(239,68,68,0.18), 0 22px 48px rgba(153,27,27,0.32);
        }

        .html-level-card-disabled {
            background: linear-gradient(180deg, #d1d5db 0%, #6b7280 100%);
            color: #ffffff !important;
            opacity: 0.72;
            cursor: not-allowed;
        }

        .html-level-card:hover {
            transform: translateY(-2px);
            filter: brightness(1.03);
        }

        @media (max-width: 768px) {
            .html-level-wrap {
                width: 94vw;
            }

            .html-level-card,
            .html-level-card-disabled {
                min-height: 31vh;
                max-height: 260px;
                margin: 18px auto;
                border-radius: 34px;
                font-size: clamp(2.1rem, 8.2vw, 3.0rem);
                border-width: 6px;
            }

            .html-level-card.boss {
                min-height: 34vh;
                max-height: 290px;
                font-size: clamp(2.0rem, 7.4vw, 2.8rem);
                border-radius: 42px;
            }
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


def request_scroll_to_top() -> None:
    st.session_state["_scroll_to_top_requested"] = True


def render_pending_scroll_to_top() -> None:
    if st.session_state.get("_scroll_to_top_requested"):
        components.html(
            """
            <script>
            function forceScrollTop() {
                try {
                    const w = window.parent;
                    const d = w.document;
                    w.scrollTo({ top: 0, left: 0, behavior: "auto" });
                    [d.documentElement, d.body,
                     d.querySelector("section.main"),
                     d.querySelector('[data-testid="stAppViewContainer"]'),
                     d.querySelector('[data-testid="stMain"]')]
                    .forEach(function(el){ if(el){ el.scrollTop = 0; }});
                } catch(e) {}
            }
            forceScrollTop();
            setTimeout(forceScrollTop, 80);
            setTimeout(forceScrollTop, 220);
            setTimeout(forceScrollTop, 520);
            </script>
            """,
            height=0,
        )
        st.session_state["_scroll_to_top_requested"] = False


def rerun_top() -> None:
    request_scroll_to_top()
    st.rerun()


# =========================================================
# Utility
# =========================================================
def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_str(value: Any) -> str:
    return str(value or "").strip()


def normalize_lower(value: Any) -> str:
    text = normalize_str(value).lower().replace("　", " ")
    return re.sub(r"\s+", " ", text)


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
        return "\n".join([as_text(v) for v in value if as_text(v)])
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            label = VISIBLE_DATA_LABELS.get(str(k), str(k))
            body = as_text(v)
            if body:
                lines.append(f"{label}：{body}")
        return "\n".join(lines)
    return str(value)


def short_text(text: Any, n: int = 80) -> str:
    s = as_text(text).strip().replace("\r", "\n")
    s = re.sub(r"\n{2,}", "\n", s)
    return s if len(s) <= n else s[:n].rstrip() + "…"


def get_category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category or "その他")


def safe_image(path: Path, caption: str = "") -> None:
    try:
        st.image(str(path), caption=caption if caption else None, width="stretch")
    except TypeError:
        st.image(str(path), caption=caption if caption else None, use_container_width=True)


def player_file_key(name: str) -> str:
    raw = normalize_str(name)[:40] or "player"
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]
    safe = re.sub(r"[^a-zA-Z0-9_\-ぁ-んァ-ヶー一-龥]", "_", raw)[:24] or "player"
    return f"{safe}_{digest}.json"


# =========================================================
# Case loading
# =========================================================
def is_case_json(path: Path) -> bool:
    if path.suffix.lower() != ".json":
        return False
    parts = [p.lower() for p in path.parts]
    return "media" not in parts and "audio" not in parts and not path.name.startswith(".")


def read_json(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, str(e)


def get_scenes(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if isinstance(data.get("scenes"), list):
        out = []
        for i, sc in enumerate(data["scenes"], start=1):
            if isinstance(sc, dict):
                s = dict(sc)
                s.setdefault("id", f"scene{i}")
                s.setdefault("title", f"Scene {i}")
                out.append(s)
        return out

    out = []
    for i in range(1, 15):
        for key in (f"scene{i}", f"scene_{i}"):
            if isinstance(data.get(key), dict):
                s = dict(data[key])
                s.setdefault("id", f"scene{i}")
                s.setdefault("title", f"Scene {i}")
                out.append(s)
                break
    return out


def infer_category(data: Dict[str, Any], path: Path) -> str:
    c = normalize_str(data.get("category") or data.get("field"))
    if c:
        return c
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

    case_id = normalize_str(data.get("case_id") or data.get("id") or path.stem)
    category = infer_category(data, path)
    text_source = " ".join([
        normalize_str(data.get("title")),
        as_text(scenes[0].get("text")),
        as_text(scenes[0].get("visible_data")),
    ])
    age, sex = infer_age_sex(text_source)

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
            errors.append({"file": str(path.relative_to(REPO_ROOT)), "error": err or "JSON読込エラー"})
            continue
        payload = build_case_payload(path, data)
        if not payload:
            errors.append({"file": str(path.relative_to(REPO_ROOT)), "error": "scenesなし"})
            continue
        cases.append(payload)

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
# Player
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
    if player_data.get("is_guest"):
        return
    try:
        PLAYERS_DIR.mkdir(parents=True, exist_ok=True)
        with player_path(player_data.get("player_name", "guest")).open("w", encoding="utf-8") as f:
            json.dump(player_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"保存失敗：{e}")


def get_player() -> Optional[Dict[str, Any]]:
    return st.session_state.get("player_data")


def set_player(player_data: Dict[str, Any]) -> None:
    st.session_state.player_data = player_data


def reset_guest_session() -> None:
    player = default_player_data("guest")
    player["is_guest"] = True
    set_player(player)
    reset_play_state()
    st.session_state.mode = "single"
    st.session_state.selected_case_id = None
    st.session_state.selected_level_name = ""
    st.session_state.challenge_case_ids = []
    st.session_state.challenge_index = 0
    st.session_state.challenge_results = []


def mark_case_played(case: Dict[str, Any], percent: float, mode: str, level_name: str = "") -> None:
    player = get_player()
    if not player:
        return

    cid = case["case_id"]
    played = player.setdefault("played_case_ids", [])
    if cid not in played:
        played.append(cid)

    history = player.setdefault("case_history", {})
    old = history.get(cid, {})
    best = max(float(old.get("best_percent", 0.0)), percent)

    history[cid] = {
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
        n = int(level_name.replace("Level", ""))
        player["current_level"] = max(int(player.get("current_level", 1)), min(n + 1, LEVEL_COUNT))
    except Exception:
        pass

    save_player(player)


# =========================================================
# Level
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
    for sc in case.get("scenes", []):
        t = normalize_scene_type(sc)
        score += {
            "single_choice": 0,
            "multiple_choice": 1,
            "ranking": 4,
            "template_select": 3,
            "dialogue_input": 6,
            "body_map_select": 6,
            "free_text": 5,
        }.get(t, 0)
    if len(case.get("scenes", [])) >= 7:
        score += 2
    joined = " ".join([case.get("title", ""), " ".join(case.get("keywords", []))])
    if any(x in joined for x in ["ボス", "ラスボス", "重症", "ショック", "CPA", "心停止", "指示要請", "病院連絡"]):
        score += 4
    return score


@st.cache_data(show_spinner=False)
def build_level_candidates_cached(pairs: Tuple[Tuple[str, int], ...]) -> Dict[str, List[str]]:
    items = sorted(pairs, key=lambda x: x[1])
    usable = items[: LEVEL_COUNT * LEVEL_CANDIDATE_COUNT]
    levels: Dict[str, List[str]] = {}
    for i in range(LEVEL_COUNT):
        start = i * LEVEL_CANDIDATE_COUNT
        end = start + LEVEL_CANDIDATE_COUNT
        levels[f"Level{i+1}"] = [cid for cid, _ in usable[start:end]]
    return levels


def build_level_candidates(cases: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    return build_level_candidates_cached(tuple((c["case_id"], case_complexity(c)) for c in cases))


def choose_level_challenge_cases(level_name: str, candidate_ids: List[str], player: Dict[str, Any]) -> List[str]:
    played = set(player.get("played_case_ids", []))
    not_played = [cid for cid in candidate_ids if cid not in played]
    already = [cid for cid in candidate_ids if cid in played]
    rng = random.Random()
    rng.shuffle(not_played)
    rng.shuffle(already)
    return (not_played + already)[:LEVEL_PLAY_COUNT]


def can_play_level(player: Dict[str, Any], level_num: int) -> bool:
    current = int(player.get("current_level", 1))
    completed = set(player.get("completed_levels", []))
    return level_num <= current or f"Level{level_num}" in completed


def level_state(player: Dict[str, Any], level_num: int) -> str:
    completed = set(player.get("completed_levels", []))
    current = int(player.get("current_level", 1))
    if f"Level{level_num}" in completed:
        return "completed"
    if level_num == current:
        return "current"
    return "locked"


def start_level_challenge(cases: List[Dict[str, Any]], level_name: str) -> None:
    player = get_player()
    if not player:
        return

    level_map = build_level_candidates(cases)
    candidate_ids = level_map.get(level_name, [])
    chosen = choose_level_challenge_cases(level_name, candidate_ids, player)

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


# =========================================================
# Media / audio
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
    name = raw.split("/")[-1]
    candidates = [
        REPO_ROOT / raw,
        CASES_DIR / raw,
        CASE_MEDIA_DIR / raw,
        CASE_MEDIA_DIR / name,
        ROOT_MEDIA_DIR / raw,
        ROOT_MEDIA_DIR / name,
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def resolve_audio_path(raw: str) -> Optional[Path]:
    if not raw:
        return None
    raw = raw.strip().replace("\\", "/")
    name = raw.split("/")[-1]
    candidates = [
        REPO_ROOT / raw,
        CASES_DIR / raw,
        CASE_AUDIO_DIR / raw,
        CASE_AUDIO_DIR / name,
        CASE_LUNG_SOUNDS_DIR / raw,
        CASE_LUNG_SOUNDS_DIR / name,
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def render_scene_media(scene: Dict[str, Any]) -> None:
    for raw in iter_media_values(scene.get("media")):
        p = resolve_media_path(raw)
        if p:
            safe_image(p)
    for raw in iter_media_values(scene.get("audio")):
        p = resolve_audio_path(raw)
        if p:
            st.audio(str(p))


# =========================================================
# Scoring
# =========================================================
def scene_max_score(scene: Dict[str, Any]) -> float:
    if scene.get("ideal_score_delta") is not None:
        try:
            return float(scene.get("ideal_score_delta"))
        except Exception:
            pass
    return 10.0


def option_is_correct(opt: Dict[str, Any]) -> bool:
    return bool(
        opt.get("is_correct")
        or opt.get("correct")
        or opt.get("is_answer")
        or opt.get("answer")
        or opt.get("score_delta", 0) > 0
    )


def option_id(opt: Dict[str, Any], idx: int) -> str:
    return str(opt.get("option_id") or opt.get("id") or opt.get("value") or f"opt{idx}")


def option_text(opt: Dict[str, Any]) -> str:
    return as_text(opt.get("text") or opt.get("label") or opt.get("content") or opt.get("title"))


def evaluate_scene(scene: Dict[str, Any], answer: Any) -> Dict[str, Any]:
    t = normalize_scene_type(scene)
    max_score = scene_max_score(scene)
    score = 0.0
    correct = False
    message = ""

    if t == "single_choice":
        opts = scene.get("options", []) if isinstance(scene.get("options"), list) else []
        correct_ids = [option_id(o, i) for i, o in enumerate(opts) if isinstance(o, dict) and option_is_correct(o)]
        correct = str(answer) in correct_ids
        score = max_score if correct else 0.0
        message = "OK" if correct else "もう一度確認"

    elif t == "multiple_choice":
        opts = scene.get("options", []) if isinstance(scene.get("options"), list) else []
        correct_ids = set(option_id(o, i) for i, o in enumerate(opts) if isinstance(o, dict) and option_is_correct(o))
        selected = set(answer or [])
        correct = selected == correct_ids
        if correct_ids:
            score = max_score * (len(selected & correct_ids) / len(correct_ids))
            wrong = len(selected - correct_ids)
            if wrong:
                score = max(0.0, score - max_score * 0.25 * wrong)
        correct = score >= max_score * 0.99
        message = "OK" if correct else "選択を確認"

    elif t == "ranking":
        ranking = scene.get("ranking") or scene.get("options") or []
        if isinstance(ranking, dict):
            items = ranking.get("items") or ranking.get("options") or []
        else:
            items = ranking if isinstance(ranking, list) else []
        ideal = []
        for i, item in enumerate(items):
            if isinstance(item, dict):
                iid = option_id(item, i)
                rank = item.get("ideal_rank") or item.get("rank") or item.get("order")
                if rank is not None:
                    ideal.append((int(rank), iid))
        ideal_order = [x[1] for x in sorted(ideal)]
        ans = answer or []
        correct = bool(ideal_order) and ans == ideal_order
        if ideal_order and ans:
            points = sum(1 for a, b in zip(ans, ideal_order) if a == b)
            score = max_score * points / len(ideal_order)
        message = "OK" if correct else "順番を確認"

    elif t == "body_map_select":
        cfg = scene.get("body_map_select") if isinstance(scene.get("body_map_select"), dict) else scene
        correct_ids = set(cfg.get("correct_part_ids") or cfg.get("correct_regions") or [])
        selected = set(answer or [])
        correct = bool(correct_ids) and selected == correct_ids
        if correct_ids:
            score = max_score * len(selected & correct_ids) / len(correct_ids)
            wrong = len(selected - correct_ids)
            if wrong:
                score = max(0.0, score - max_score * 0.25 * wrong)
        message = "OK" if correct else "観察部位を確認"

    elif t == "dialogue_input":
        # short_chat は入力ごとに加点済みにするため、最終評価はセッション保存の達成数で見る
        state = answer if isinstance(answer, dict) else {}
        required = scene.get("required_intents") or []
        achieved = set(state.get("achieved_intents", []))
        if required:
            score = max_score * len(achieved & set(required)) / len(required)
            correct = set(required).issubset(achieved)
        else:
            score = float(state.get("score", 0.0))
            correct = score > 0
        message = "OK" if correct else "不足あり"

    else:
        score = max_score if answer else 0.0
        correct = bool(answer)
        message = "OK" if correct else "未回答"

    return {
        "score": round(float(score), 2),
        "max_score": round(float(max_score), 2),
        "correct": correct,
        "message": message,
    }


def score_percent() -> float:
    max_s = float(st.session_state.get("score_max", 0.0))
    if max_s <= 0:
        return 0.0
    return float(st.session_state.get("score_total", 0.0)) / max_s * 100.0


def rank_info(percent: float) -> Tuple[str, str]:
    if percent >= 85:
        return "Excellent", "✨"
    if percent >= 70:
        return "Good", "👏"
    if percent >= 50:
        return "Keep Going", "👍"
    return "Review", "📝"


def recalc_total_score(case: Dict[str, Any]) -> None:
    total = 0.0
    max_total = 0.0
    cid = case["case_id"]
    for idx, scene in enumerate(case["scenes"], start=1):
        key = f"{cid}__scene_{idx}"
        feedback = evaluate_scene(scene, st.session_state.answers.get(key))
        st.session_state.scene_feedback[key] = feedback
        total += feedback["score"]
        max_total += feedback["max_score"]
    st.session_state.score_total = total
    st.session_state.score_max = max_total


# =========================================================
# State / navigation
# =========================================================
def init_state() -> None:
    defaults = {
        "screen": "login",
        "mode": "single",
        "selected_case_id": None,
        "selected_level_name": "",
        "challenge_case_ids": [],
        "challenge_index": 0,
        "challenge_results": [],
        "scene_index": 0,
        "answers": {},
        "scene_feedback": {},
        "score_total": 0.0,
        "score_max": 0.0,
        "_scroll_to_top_requested": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_play_state() -> None:
    st.session_state.scene_index = 0
    st.session_state.answers = {}
    st.session_state.scene_feedback = {}
    st.session_state.score_total = 0.0
    st.session_state.score_max = 0.0
    for k in [x for x in list(st.session_state.keys()) if str(x).startswith(("rank__", "chat__", "body__"))]:
        del st.session_state[k]


def go(screen: str) -> None:
    st.session_state.screen = screen
    rerun_top()



def get_query_param_first(name: str) -> str:
    try:
        value = st.query_params.get(name, "")
        if isinstance(value, list):
            return str(value[0]) if value else ""
        return str(value)
    except Exception:
        try:
            params = st.experimental_get_query_params()
            value = params.get(name, [""])
            return str(value[0]) if isinstance(value, list) and value else str(value)
        except Exception:
            return ""


def clear_query_params() -> None:
    try:
        st.query_params.clear()
    except Exception:
        try:
            st.experimental_set_query_params()
        except Exception:
            pass


def handle_level_query(cases: List[Dict[str, Any]]) -> None:
    player = get_player()
    if not player:
        return
    raw = get_query_param_first("go_level")
    if not raw:
        return
    try:
        level_num = int(raw)
    except Exception:
        clear_query_params()
        return
    clear_query_params()
    if 1 <= level_num <= LEVEL_COUNT and can_play_level(player, level_num):
        start_level_challenge(cases, f"Level{level_num}")
    else:
        st.warning("このLevelはまだ選択できません。")


def html_level_label(level_num: int, state: str) -> str:
    if level_num == 10:
        if state == "completed":
            return "✅ Final 10"
        if state == "current":
            return "🚑 Final 10"
        return "🔒 Final 10"

    if state == "completed":
        return f"✅ Level {level_num}"
    if state == "current":
        return f"🚑 Level {level_num}"
    return f"🔒 Level {level_num}"


# =========================================================
# Render: login / home / level map
# =========================================================
def screen_login() -> None:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="hero-title">
            <div class="hero-main">🚑 <span class="blue">救急救命士</span><br><span class="green">臨床推論クエスト</span></div>
            <div class="hero-sub">PARAMEDIC SIMULATION</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    name = st.text_input("Name", placeholder="名前を入力", label_visibility="collapsed")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("START", type="primary", width="stretch"):
            if not normalize_str(name):
                st.warning("名前を入力してね")
            else:
                player = load_player(normalize_str(name))
                player["is_guest"] = False
                set_player(player)
                go("home")
    with col2:
        if st.button("GUEST", width="stretch"):
            reset_guest_session()
            go("home")

    st.markdown("</div>", unsafe_allow_html=True)



def render_top_bar(cases: List[Dict[str, Any]]) -> None:
    player = get_player()
    name = player.get("player_name", "guest") if player else "guest"
    current = int(player.get("current_level", 1)) if player else 1
    completed = len(player.get("completed_levels", [])) if player else 0

    c1, c2, c3, c4 = st.columns([1.3, 0.8, 0.8, 0.8])
    c1.markdown(f'<div class="app-title">🚑 {name}</div>', unsafe_allow_html=True)
    c2.markdown(f'<span class="pill pill-blue">Lv {current}</span>', unsafe_allow_html=True)
    c3.markdown(f'<span class="pill pill-green">CLEAR {completed}</span>', unsafe_allow_html=True)
    c4.markdown(f'<span class="pill pill-gray">{len(cases)} cases</span>', unsafe_allow_html=True)



LEVEL_POINTS = {
    1: {"x": 50, "y": 72, "animal_x": 31, "animal_y": 70},
    2: {"x": 53, "y": 205, "animal_x": 73, "animal_y": 202},
    3: {"x": 48, "y": 333, "animal_x": 70, "animal_y": 335},
    4: {"x": 55, "y": 460, "animal_x": 73, "animal_y": 462},
    5: {"x": 45, "y": 585, "animal_x": 66, "animal_y": 583},
    6: {"x": 54, "y": 705, "animal_x": 74, "animal_y": 706},
    7: {"x": 44, "y": 825, "animal_x": 65, "animal_y": 828},
    8: {"x": 54, "y": 950, "animal_x": 74, "animal_y": 952},
    9: {"x": 46, "y": 1080, "animal_x": 66, "animal_y": 1082},
    10: {"x": 50, "y": 1240, "animal_x": 72, "animal_y": 1248},
}


def map_path_d() -> str:
    points = [LEVEL_POINTS[i] for i in range(1, LEVEL_COUNT + 1)]
    d = f"M {points[0]['x']} {points[0]['y']}"
    for i in range(1, len(points)):
        p0 = points[i - 1]
        p1 = points[i]
        mid_y = (p0["y"] + p1["y"]) / 2
        d += f" C {p0['x']} {mid_y}, {p1['x']} {mid_y}, {p1['x']} {p1['y']}"
    return d


def completed_path_d(player: Dict[str, Any]) -> str:
    current = int(player.get("current_level", 1))
    completed_count = max(1, min(current, LEVEL_COUNT))
    # クリア済みは現在地点の直前まで色を伸ばす。現在Level4なら1→4手前まで緑。
    points = [LEVEL_POINTS[i] for i in range(1, completed_count + 1)]
    if len(points) <= 1:
        return ""
    d = f"M {points[0]['x']} {points[0]['y']}"
    for i in range(1, len(points)):
        p0 = points[i - 1]
        p1 = points[i]
        mid_y = (p0["y"] + p1["y"]) / 2
        d += f" C {p0['x']} {mid_y}, {p1['x']} {mid_y}, {p1['x']} {p1['y']}"
    return d


def ambulance_position(player: Dict[str, Any]) -> Tuple[float, float]:
    current = int(player.get("current_level", 1))
    n = max(1, min(current, LEVEL_COUNT))
    if n == 1:
        return LEVEL_POINTS[1]["x"] - 15, LEVEL_POINTS[1]["y"] + 30
    if n >= 10:
        return LEVEL_POINTS[10]["x"] + 20, LEVEL_POINTS[10]["y"] + 70
    prev_p = LEVEL_POINTS[max(1, n - 1)]
    cur_p = LEVEL_POINTS[n]
    return (prev_p["x"] * 0.35 + cur_p["x"] * 0.65, prev_p["y"] * 0.35 + cur_p["y"] * 0.65)


def render_map_svg(player: Dict[str, Any]) -> None:
    base = map_path_d()
    done = completed_path_d(player)
    done_path = f'<path d="{done}" fill="none" stroke="#22c55e" stroke-width="12" stroke-linecap="round"/>' if done else ""
    dash_done = f'<path d="{done}" fill="none" stroke="rgba(255,255,255,0.72)" stroke-width="2.5" stroke-dasharray="5 7" stroke-linecap="round"/>' if done else ""
    html = f"""
    <svg class="level-map-svg" viewBox="0 0 100 1320" preserveAspectRatio="none">
      <path d="{base}" fill="none" stroke="#4b5563" stroke-width="18" stroke-linecap="round"/>
      <path d="{base}" fill="none" stroke="rgba(255,255,255,0.72)" stroke-width="3" stroke-dasharray="5 8" stroke-linecap="round"/>
      {done_path}
      {dash_done}
    </svg>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_level_decorations() -> None:
    decorations = [
        ("🌲", 15, 95), ("🌳", 84, 170), ("🌲", 17, 365), ("🌿", 81, 420),
        ("🌳", 18, 650), ("🪨", 82, 740), ("🌲", 85, 850), ("🌿", 20, 1030),
    ]
    for emoji, x, y in decorations:
        st.markdown(f'<div class="map-deco" style="left:{x}%; top:{y}px;">{emoji}</div>', unsafe_allow_html=True)

def level_button_label(level_num: int, state: str) -> str:
    return html_level_label(level_num, state)


def render_level_map(cases: List[Dict[str, Any]]) -> None:
    player = get_player()
    if not player:
        return

    st.markdown('<div class="html-level-wrap">', unsafe_allow_html=True)

    for n in range(1, LEVEL_COUNT + 1):
        state = level_state(player, n)
        playable = can_play_level(player, n)
        label = html_level_label(n, state)

        if playable:
            cls = f"html-level-card {state}"
            if n == 10:
                cls += " boss"
            href = f"?go_level={n}"
            st.markdown(f'<a class="{cls}" href="{href}" target="_self">{label}</a>', unsafe_allow_html=True)
        else:
            cls = "html-level-card-disabled"
            if n == 10:
                cls += " boss"
            st.markdown(f'<div class="{cls}">{label}</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)



def render_case_select(cases: List[Dict[str, Any]]) -> None:
    with st.expander("単症例", expanded=False):
        categories = ["すべて"] + [get_category_label(c) for c in sorted(set(x["category"] for x in cases))]
        label_to_cat = {"すべて": "すべて"}
        for c in sorted(set(x["category"] for x in cases)):
            label_to_cat[get_category_label(c)] = c

        col1, col2 = st.columns(2)
        with col1:
            cat_label = st.selectbox("カテゴリ", categories, key="single_cat")
        with col2:
            q = st.text_input("検索", placeholder="キーワード", key="single_q")

        filtered = cases
        cat = label_to_cat.get(cat_label, "すべて")
        if cat != "すべて":
            filtered = [c for c in filtered if c["category"] == cat]
        if normalize_str(q):
            ql = normalize_lower(q)
            filtered = [c for c in filtered if ql in normalize_lower(c["title"] + " " + " ".join(c.get("keywords", [])))]

        for c in filtered[:80]:
            cols = st.columns([0.72, 0.28])
            with cols[0]:
                st.write(f"{c['title']}")
            with cols[1]:
                if st.button("▶", key=f"single_{c['case_id']}"):
                    start_single_case(c["case_id"])


def screen_home(cases: List[Dict[str, Any]], errors: List[Dict[str, str]]) -> None:
    st.markdown(
        """
        <div class="hero-title">
            <div class="hero-main">🚑 <span class="blue">救急救命士</span> <span class="green">臨床推論クエスト</span></div>
            <div class="hero-sub">LEVEL ROAD</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_top_bar(cases)

    if not cases:
        st.error("症例JSONが読み込めません。casesフォルダを確認してね。")
        if errors:
            with st.expander("errors"):
                st.json(errors[:20])
        return

    render_level_map(cases)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("履歴", width="stretch"):
            st.session_state["_open_history_once"] = True
    with col2:
        if st.button("🔄", help="画面更新", width="stretch"):
            load_cases.clear()
            rerun_top()
    with col3:
        if st.button("ログアウト", width="stretch"):
            st.session_state.clear()
            st.rerun()

    render_history_panel()
    render_case_select(cases)



def render_history_panel() -> None:
    player = get_player()
    if not player:
        return

    with st.expander("履歴", expanded=False):
        completed = player.get("completed_levels", [])
        st.markdown(
            f"""
            <div class="history-grid">
              <div class="history-item"><b>Level</b><br>{player.get("current_level", 1)}</div>
              <div class="history-item"><b>Clear</b><br>{len(completed)}</div>
              <div class="history-item"><b>Play</b><br>{player.get("total_play_count", 0)}</div>
              <div class="history-item"><b>Best</b><br>{float(player.get("best_total_score_percent", 0.0)):.1f}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        case_history = player.get("case_history", {})
        if case_history:
            st.markdown("#### 最近の症例")
            recent = sorted(case_history.items(), key=lambda kv: kv[1].get("last_played_at", ""), reverse=True)[:10]
            for _cid, h in recent:
                st.markdown(
                    f"""
                    <div class="history-item">
                        <b>{h.get("title", "")}</b><br>
                        <span class="tiny-muted">{h.get("last_played_at", "")}　{float(h.get("last_percent", 0.0)):.1f}%</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        level_history = player.get("level_history", {})
        if level_history:
            st.markdown("#### Level")
            for lv in sorted(level_history.keys(), key=lambda x: int(str(x).replace("Level", "") or 0)):
                h = level_history[lv]
                st.markdown(
                    f'<span class="pill pill-green">{lv}</span> <span class="tiny-muted">{float(h.get("best_percent", 0.0)):.1f}%</span>',
                    unsafe_allow_html=True,
                )


# =========================================================
# Render: case intro / scene
# =========================================================
def selected_case(cases: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return find_case(cases, st.session_state.get("selected_case_id", ""))


def screen_intro(cases: List[Dict[str, Any]]) -> None:
    case = selected_case(cases)
    if not case:
        st.error("症例が見つかりません。")
        if st.button("HOME"):
            go("home")
        return

    mode = st.session_state.get("mode", "single")
    if mode == "level":
        idx = int(st.session_state.get("challenge_index", 0)) + 1
        total = len(st.session_state.get("challenge_case_ids", []))
        st.markdown(f'<span class="pill pill-blue">{st.session_state.get("selected_level_name")}</span> <span class="pill pill-gray">{idx}/{total}</span>', unsafe_allow_html=True)

    st.markdown(f'<div class="card"><div class="scene-title">{case["title"]}</div><span class="pill pill-gray">{case["category_label"]}</span></div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("START", type="primary", width="stretch"):
            reset_play_state()
            go("scene")
    with c2:
        if st.button("HOME", width="stretch"):
            go("home")


def current_scene(case: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    idx = int(st.session_state.get("scene_index", 0))
    idx = max(0, min(idx, len(case["scenes"]) - 1))
    return idx, case["scenes"][idx]


def answer_key(case: Dict[str, Any], scene_index: int) -> str:
    return f"{case['case_id']}__scene_{scene_index + 1}"


def render_options(scene: Dict[str, Any], key: str) -> Any:
    t = normalize_scene_type(scene)
    opts = scene.get("options", []) if isinstance(scene.get("options"), list) else []

    if t == "single_choice":
        labels = []
        ids = []
        for i, opt in enumerate(opts):
            if isinstance(opt, dict):
                ids.append(option_id(opt, i))
                labels.append(option_text(opt))
            else:
                ids.append(f"opt{i}")
                labels.append(as_text(opt))
        selected = st.radio(scene.get("prompt", "選択してください"), labels, index=None, key=f"radio_{key}")
        if selected is None:
            return None
        return ids[labels.index(selected)]

    if t == "multiple_choice":
        selected_ids = []
        st.markdown(as_text(scene.get("prompt") or "選択してください"))
        for i, opt in enumerate(opts):
            if not isinstance(opt, dict):
                oid, txt = f"opt{i}", as_text(opt)
            else:
                oid, txt = option_id(opt, i), option_text(opt)
            if st.checkbox(txt, key=f"check_{key}_{oid}"):
                selected_ids.append(oid)
        return selected_ids

    return None


def render_ranking(scene: Dict[str, Any], key: str) -> Any:
    ranking = scene.get("ranking") or scene.get("options") or []
    if isinstance(ranking, dict):
        items = ranking.get("items") or ranking.get("options") or []
    else:
        items = ranking if isinstance(ranking, list) else []

    entries = []
    for i, item in enumerate(items):
        if isinstance(item, dict):
            entries.append((option_id(item, i), option_text(item)))
        else:
            entries.append((f"item{i}", as_text(item)))

    st.markdown(as_text(scene.get("prompt") or "優先順位を選択"))
    order: List[str] = []
    remaining = entries[:]
    for rank in range(1, len(entries) + 1):
        labels = ["未選択"] + [txt for _id, txt in remaining]
        choice = st.selectbox(f"{rank}", labels, key=f"rank_{key}_{rank}", label_visibility="collapsed")
        if choice != "未選択":
            picked = next((x for x in remaining if x[1] == choice), None)
            if picked:
                order.append(picked[0])
                remaining = [x for x in remaining if x[0] != picked[0]]
    return order


def render_body_map(scene: Dict[str, Any], key: str) -> Any:
    cfg = scene.get("body_map_select") if isinstance(scene.get("body_map_select"), dict) else scene
    parts = cfg.get("parts") or cfg.get("body_regions") or []
    max_select = int(cfg.get("max_select") or cfg.get("max_regions") or 3)
    min_select = int(cfg.get("min_select") or 1)

    st.markdown(as_text(scene.get("prompt") or "観察部位を選択"))
    selected: List[str] = []

    for i, part in enumerate(parts):
        if isinstance(part, dict):
            pid = str(part.get("part_id") or part.get("region_id") or part.get("id") or f"part{i}")
            label = as_text(part.get("label") or part.get("name") or pid)
            finding = as_text(part.get("finding") or part.get("result") or part.get("text"))
        else:
            pid = f"part{i}"
            label = as_text(part)
            finding = ""

        checked = st.checkbox(label, key=f"body_{key}_{pid}", disabled=(len(selected) >= max_select and pid not in selected))
        if checked:
            selected.append(pid)
            if finding:
                st.caption(finding)

    if len(selected) < min_select:
        st.caption(f"{min_select}か所以上選択")
    if len(selected) > max_select:
        st.caption(f"{max_select}か所まで")
    return selected


def match_dialogue_rule(text: str, rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    normalized = normalize_lower(text)
    for rule in rules:
        keys = rule.get("keywords") or rule.get("acceptable_inputs") or []
        if isinstance(keys, str):
            keys = [keys]
        if any(normalize_lower(k) and normalize_lower(k) in normalized for k in keys):
            return rule
    return None


def render_short_chat(scene: Dict[str, Any], key: str) -> Any:
    rules = scene.get("dialogue_rules", []) if isinstance(scene.get("dialogue_rules"), list) else []
    required = scene.get("required_intents") or []
    fallback = as_text(scene.get("fallback_reply") or "それでは判断できません。もう少し具体的にお願いします。")
    opening = as_text(scene.get("opening_message") or "")

    state_key = f"chat__{key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = {
            "messages": [],
            "achieved_intents": [],
            "score": 0.0,
        }
        if opening:
            st.session_state[state_key]["messages"].append(("相手", opening))

    state = st.session_state[state_key]

    for role, msg in state.get("messages", []):
        with st.chat_message("assistant" if role == "相手" else "user"):
            st.write(msg)

    user_text = st.chat_input("入力", key=f"chat_input_{key}")
    if user_text:
        state["messages"].append(("あなた", user_text))
        rule = match_dialogue_rule(user_text, rules)
        if rule:
            intent_id = str(rule.get("intent_id") or rule.get("id") or "")
            if intent_id and intent_id not in state["achieved_intents"]:
                state["achieved_intents"].append(intent_id)
                state["score"] = float(state.get("score", 0.0)) + float(rule.get("score_delta", 1))
            reply = as_text(rule.get("reply") or "確認しました。")
        else:
            reply = fallback
        state["messages"].append(("相手", reply))
        st.session_state[state_key] = state
        st.rerun()

    if required:
        done = len(set(state.get("achieved_intents", [])) & set(required))
        st.caption(f"{done}/{len(required)}")
    return state


def render_template_select(scene: Dict[str, Any], key: str) -> Any:
    templates = scene.get("templates") or scene.get("options") or []
    if isinstance(templates, dict):
        templates = templates.get("items") or templates.get("templates") or []
    labels = []
    ids = []
    for i, t in enumerate(templates if isinstance(templates, list) else []):
        if isinstance(t, dict):
            ids.append(str(t.get("template_id") or t.get("id") or f"tpl{i}"))
            labels.append(as_text(t.get("label") or t.get("title") or t.get("text") or t))
        else:
            ids.append(f"tpl{i}")
            labels.append(as_text(t))
    selected = st.radio(scene.get("prompt", "選択してください"), labels, index=None, key=f"tpl_{key}")
    if selected is None:
        return None
    return ids[labels.index(selected)]


def render_answer_area(case: Dict[str, Any], scene_index: int, scene: Dict[str, Any]) -> Any:
    key = answer_key(case, scene_index)
    t = normalize_scene_type(scene)

    if t in ("single_choice", "multiple_choice"):
        return render_options(scene, key)
    if t == "ranking":
        return render_ranking(scene, key)
    if t == "body_map_select":
        return render_body_map(scene, key)
    if t == "dialogue_input":
        return render_short_chat(scene, key)
    if t == "template_select":
        return render_template_select(scene, key)

    return st.text_area(scene.get("prompt", "入力"), key=f"text_{key}")


def screen_scene(cases: List[Dict[str, Any]]) -> None:
    case = selected_case(cases)
    if not case:
        st.error("症例が見つかりません。")
        return

    idx, scene = current_scene(case)
    total = len(case["scenes"])
    key = answer_key(case, idx)

    st.markdown(f'<span class="pill pill-blue">{idx + 1}/{total}</span>', unsafe_allow_html=True)
    st.markdown('<div class="scene-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="scene-title">{as_text(scene.get("title") or f"Scene {idx+1}")}</div>', unsafe_allow_html=True)
    if scene.get("text"):
        st.markdown(f'<div class="scene-text">{as_text(scene.get("text"))}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    render_scene_media(scene)

    answer = render_answer_area(case, idx, scene)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("BACK", disabled=idx == 0, width="stretch"):
            st.session_state.scene_index = max(0, idx - 1)
            rerun_top()
    with col2:
        label = "RESULT" if idx >= total - 1 else "NEXT"
        if st.button(label, type="primary", width="stretch"):
            st.session_state.answers[key] = answer
            if idx >= total - 1:
                recalc_total_score(case)
                percent = score_percent()
                mode = st.session_state.get("mode", "single")
                level_name = st.session_state.get("selected_level_name", "")
                mark_case_played(case, percent, mode, level_name)

                if mode == "level":
                    st.session_state.challenge_results.append({
                        "case_id": case["case_id"],
                        "title": case["title"],
                        "score": st.session_state.score_total,
                        "max_score": st.session_state.score_max,
                        "percent": percent,
                    })
                go("result")
            else:
                st.session_state.scene_index = idx + 1
                rerun_top()


# =========================================================
# Results
# =========================================================
def render_debriefing(case: Dict[str, Any]) -> None:
    debrief = case.get("debriefing") or {}

    with st.expander("振り返り・解説", expanded=True):
        if debrief:
            labels = {
                "summary": "まとめ",
                "ideal_actions": "理想行動",
                "good_points": "良かった点",
                "cautions": "注意点",
                "model_answer": "模範例",
                "learning_points": "学習ポイント",
            }
            for key in ("summary", "ideal_actions", "good_points", "cautions", "model_answer", "learning_points"):
                value = debrief.get(key)
                if value:
                    st.markdown(f"**{labels.get(key, key)}**")
                    st.write(as_text(value))
        else:
            st.write("この症例の解説データは未登録です。")

        st.markdown("**Scene別チェック**")
        for idx, scene in enumerate(case.get("scenes", []), start=1):
            key = f"{case['case_id']}__scene_{idx}"
            fb = st.session_state.scene_feedback.get(key)
            if not fb:
                continue
            title = as_text(scene.get("title") or f"Scene {idx}")
            mark = "✅" if fb.get("correct") else "🔎"
            st.markdown(f"{mark} **{idx}. {title}**　{fb.get('score', 0):.1f}/{fb.get('max_score', 0):.1f}")

            # 選択肢解説・短文チャット模範例
            if scene.get("explanation"):
                st.caption(as_text(scene.get("explanation")))
            if scene.get("short_chat_model_flow"):
                flow = scene.get("short_chat_model_flow")
                st.caption("模範チャット例")
                st.write(as_text(flow))
            elif scene.get("model_answer"):
                st.caption("模範例")
                st.write(as_text(scene.get("model_answer")))


def move_after_case_result(cases: List[Dict[str, Any]]) -> None:
    if st.session_state.get("mode") != "level":
        go("home")
        return

    ids = st.session_state.get("challenge_case_ids", [])
    next_i = int(st.session_state.get("challenge_index", 0)) + 1
    if next_i >= len(ids):
        go("level_result")
        return

    st.session_state.challenge_index = next_i
    st.session_state.selected_case_id = ids[next_i]
    reset_play_state()
    go("intro")


def screen_result(cases: List[Dict[str, Any]]) -> None:
    case = selected_case(cases)
    if not case:
        st.error("症例が見つかりません。")
        return

    percent = score_percent()
    rank, icon = rank_info(percent)

    st.markdown(
        f"""
        <div class="result-card">
            <div class="score-big">{icon} {percent:.1f}%</div>
            <span class="pill pill-blue">{rank}</span>
            <span class="pill pill-gray">{st.session_state.score_total:.1f}/{st.session_state.score_max:.1f}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_debriefing(case)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("NEXT", type="primary", width="stretch"):
            move_after_case_result(cases)
    with c2:
        if st.button("HOME", width="stretch"):
            go("home")


def screen_level_result(cases: List[Dict[str, Any]]) -> None:
    level_name = st.session_state.get("selected_level_name", "")
    results = st.session_state.get("challenge_results", [])
    if not results:
        st.warning("結果がありません。")
        if st.button("HOME"):
            go("home")
        return

    avg = sum(float(r.get("percent", 0.0)) for r in results) / len(results)
    cleared = avg >= CLEAR_PERCENT

    if cleared:
        mark_level_completed(level_name, st.session_state.get("challenge_case_ids", []), avg)

    st.markdown(
        f"""
        <div class="result-card">
            <div class="score-big">{'✅' if cleared else '🔁'} {avg:.1f}%</div>
            <span class="pill {'pill-green' if cleared else 'pill-red'}">{'CLEAR' if cleared else 'RETRY'}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("5 cases", expanded=False):
        for r in results:
            st.write(f"{float(r.get('percent', 0)):.1f}%　{r.get('title')}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("RETRY", width="stretch"):
            start_level_challenge(cases, level_name)
    with c2:
        if st.button("HOME", type="primary", width="stretch"):
            go("home")


# =========================================================
# Main
# =========================================================
def main() -> None:
    inject_css()
    init_state()
    render_pending_scroll_to_top()

    cases, errors = load_cases()

    # HTML Levelカードのクリックを受け取る
    if get_player():
        handle_level_query(cases)

    screen = st.session_state.get("screen", "login")

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
