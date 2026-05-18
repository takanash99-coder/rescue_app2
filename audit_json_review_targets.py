import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES_DIR = ROOT / "cases"
OUT = ROOT / "json_review_targets.csv"

FREE_TEXT_KEYWORDS = [
    "記述", "書いて", "入力", "まとめ", "説明", "述べ", "要約",
    "申し送り", "病院連絡", "指示要請", "自由記載", "自由入力"
]

def load_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), ""
    except Exception as e:
        return None, str(e)

def get_scenes(data):
    if isinstance(data.get("scenes"), list):
        return data["scenes"]
    scenes = []
    for i in range(1, 15):
        for key in (f"scene{i}", f"scene_{i}"):
            if isinstance(data.get(key), dict):
                scenes.append(data[key])
                break
    return scenes

def text_of(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(text_of(v) for v in value)
    if isinstance(value, dict):
        return " ".join(text_of(v) for v in value.values())
    return str(value)

def has_body_map(scene):
    vd = scene.get("visible_data", {})
    if isinstance(vd, dict):
        if isinstance(vd.get("body_regions"), list) and vd.get("body_regions"):
            return True
        if vd.get("body_map_template"):
            return True
    media_text = text_of(scene.get("media"))
    return "neutral_mannequin_body_diagram_template" in media_text or "body" in media_text.lower()

def is_free_text_like(scene):
    t = str(scene.get("type", "")).strip().lower()
    if t in ["free_text", "freetext", "text", "written", "description", "descriptive", "記述", "記述式"]:
        return True
    if isinstance(scene.get("dialogue_rules"), list):
        # 対話式は別扱いしたい場合もあるが、自由入力系として拾う
        return True
    prompt_blob = " ".join([
        text_of(scene.get("title")),
        text_of(scene.get("prompt")),
        text_of(scene.get("scene_goal")),
        text_of(scene.get("action_tag")),
    ])
    options = scene.get("options", [])
    has_options = isinstance(options, list) and len(options) > 0
    return (not has_options) and any(k in prompt_blob for k in FREE_TEXT_KEYWORDS)

def main():
    rows = []
    total_json = 0

    for path in sorted(CASES_DIR.rglob("*.json")):
        if "media" in [p.lower() for p in path.parts]:
            continue

        total_json += 1
        data, err = load_json(path)
        if err:
            rows.append({
                "review_type": "ERROR",
                "category": path.parent.name,
                "file": str(path.relative_to(ROOT)),
                "case_id": "",
                "title": "",
                "scene_id": "",
                "scene_title": "",
                "scene_type": "",
                "reason": err,
            })
            continue

        scenes = get_scenes(data)
        case_id = data.get("case_id", path.stem)
        title = data.get("title", path.stem)

        for i, scene in enumerate(scenes, start=1):
            if not isinstance(scene, dict):
                continue

            scene_id = scene.get("id", f"scene{i}")
            scene_title = scene.get("title", f"Scene {i}")
            scene_type = scene.get("type", "")

            reasons = []
            review_types = []

            if is_free_text_like(scene):
                review_types.append("記述・自由入力")
                reasons.append("free_text/dialogue_input相当、または選択肢なし＋記述系文言")

            if has_body_map(scene):
                review_types.append("人体図")
                reasons.append("visible_data.body_regions/body_map_template または人体図mediaあり")

            if review_types:
                rows.append({
                    "review_type": " / ".join(review_types),
                    "category": data.get("category", path.parent.name),
                    "file": str(path.relative_to(ROOT)),
                    "case_id": case_id,
                    "title": title,
                    "scene_id": scene_id,
                    "scene_title": scene_title,
                    "scene_type": scene_type,
                    "reason": " / ".join(reasons),
                })

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "review_type", "category", "file", "case_id", "title",
            "scene_id", "scene_title", "scene_type", "reason"
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"JSON総数: {total_json}")
    print(f"見直し対象Scene数: {len(rows)}")
    print(f"出力: {OUT}")

if __name__ == "__main__":
    main()
