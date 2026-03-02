for block in blocks:
    block = block.strip()
    if not block:
        continue
    if set(block) == {"_"}:
        continue
    # ここから既存処理
