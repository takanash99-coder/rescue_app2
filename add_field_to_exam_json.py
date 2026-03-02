from __future__ import annotations

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

CHAPTER_LABELS = {
    "01": "01. 人体の構造と機能",
    "02": "02. 疾患の成り立ちと薬理学",
    "03": "03. 内因性救急活動における病態生理",
    "04": "04. 外傷救急活動における病態生理と救急処置",
    "05": "05. 観察と重症度・緊急度判断",
    "06": "06. 救急医療体制と救急救命士の法律関係",
    "07": "07. 症候別アプローチ",
    "08": "08. 特殊病態",
    "09": "09. 生命倫理及び健康と社会保障",
    "10": "10. 総合問題形式",
}

# id例: exam01__q0028 / exam10__q0001 等
ID_RE = re.compile(r"^exam(?P<no>\d{2})", re.IGNORECASE)


def main() -> None:
    if not DATA_DIR.exists():
        raise SystemExit(f"data folder not found: {DATA_DIR}")

    json_files = sorted(DATA_DIR.glob("*.json"))
    if not json_files:
        raise SystemExit(f"no json files in: {DATA_DIR}")

    total_updated = 0
    total_exam = 0

    for fp in json_files:
        try:
            obj = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue

        if not isinstance(obj, dict) or not isinstance(obj.get("questions"), list):
            continue

        changed = False
        for q in obj["questions"]:
            if not isinstance(q, dict):
                continue
            if q.get("mode") != "exam":
                continue

            total_exam += 1

            # すでに field が入ってるなら尊重
            if isinstance(q.get("field"), str) and q["field"].strip():
                continue

            qid = q.get("id")
            if not isinstance(qid, str):
                q["field"] = "未分類"
                changed = True
                total_updated += 1
                continue

            m = ID_RE.match(qid)
            if not m:
                q["field"] = "未分類"
                changed = True
                total_updated += 1
                continue

            no = m.group("no")
            q["field"] = CHAPTER_LABELS.get(no, "未分類")
            changed = True
            total_updated += 1

        if changed:
            fp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"exam questions: {total_exam}")
    print(f"field updated: {total_updated}")
    print("done.")


if __name__ == "__main__":
    main()
