import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CASES_DIR = BASE_DIR / "cases"

# ---------------------------------------------------------
# 症例ごとの難易度設定
# Easy / Normal / Hard の3段階で統一
# ---------------------------------------------------------
DIFFICULTY_MAP = {
    # Easy
    "case_respiratory_anaphylaxis_exercise_food_001.json": "Easy",
    "case_toxicology_morphine_respiratory_depression_001.json": "Easy",
    "case_neuro_stroke_af_001.json": "Easy",
    "case_trauma_head_injury_anticoagulant_001.json": "Easy",

    # Normal
    "case_cardiac_arrest_acs_001.json": "Normal",
    "case_respiratory_asthma_transport_position_001.json": "Normal",
    "case_toxicology_amphetamine_001.json": "Normal",
    "case_cardiovascular_ecg_artifact_sweating_001.json": "Normal",
    "case_psychiatric_gas_suicide_001.json": "Normal",
    "case_psychiatric_dissociative_amnesia_001.json": "Normal",

    # Hard
    "case_cardiovascular_myocarditis_bradyarrhythmia_position_001.json": "Hard",
    "case_cardiovascular_torsades_cpa_001.json": "Hard",
    "case_respiratory_copd_hyperoxia_consciousness_001.json": "Hard",
    "case_trauma_cardiac_tamponade_jvd_001.json": "Hard",
    "case_trauma_necrotizing_soft_tissue_infection_septic_shock_001.json": "Hard",
}


def is_case_json(path: Path) -> bool:
    if path.suffix.lower() != ".json":
        return False
    if "media" in [p.lower() for p in path.parts]:
        return False
    return True


def main():
    if not CASES_DIR.exists():
        print(f"[NG] cases フォルダが見つかりません: {CASES_DIR}")
        return

    updated_count = 0
    skipped_files = []
    error_count = 0

    all_case_files = sorted([p for p in CASES_DIR.rglob("*.json") if is_case_json(p)])

    print("=== difficulty 一括設定開始 ===\n")

    for path in all_case_files:
        filename = path.name

        if filename not in DIFFICULTY_MAP:
            skipped_files.append(path.relative_to(BASE_DIR).as_posix())
            print(f"[SKIP] difficulty未指定: {path.relative_to(BASE_DIR).as_posix()}")
            continue

        difficulty = DIFFICULTY_MAP[filename]

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["difficulty"] = difficulty

            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            print(f"[OK] {path.relative_to(BASE_DIR).as_posix()} -> difficulty = {difficulty}")
            updated_count += 1

        except Exception as e:
            print(f"[NG] {path.relative_to(BASE_DIR).as_posix()} -> {e}")
            error_count += 1

    print("\n=== 完了 ===")
    print(f"更新件数: {updated_count}")
    print(f"エラー件数: {error_count}")
    print(f"未指定スキップ件数: {len(skipped_files)}")

    if skipped_files:
        print("\n--- difficulty未指定ファイル一覧 ---")
        for file_path in skipped_files:
            print(f"- {file_path}")


if __name__ == "__main__":
    main()