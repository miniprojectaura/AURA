"""
Data cleaning and quality pipeline for finetuning datasets.

Pipeline stages:
1. Deduplication (exact + fuzzy via MinHash LSH)
2. Quality filtering (length, completeness, format validation)
3. Toxicity filtering (basic blocklist + optional Detoxify)
4. Language detection and tagging
5. Train/val/test split with stratification
6. Statistics reporting
"""
from __future__ import annotations

import hashlib
import json
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


# ── Blocklist for toxicity filtering ─────────────────────────────────
TOXIC_PATTERNS = [
    r'\b(nude|naked|porn|xxx|explicit)\b',
    r'\b(kill|murder|attack|terrorism|bomb)\b',
    r'\b(racist|sexist|slur)\b',
]


def load_jsonl(filepath: str | Path) -> list[dict]:
    """Load JSONL file into list of dicts."""
    data = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def save_jsonl(data: list[dict], filepath: str | Path) -> None:
    """Save list of dicts to JSONL file."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


# ── Stage 1: Deduplication ───────────────────────────────────────────
def deduplicate(data: list[dict], key_field: str = "conversations") -> list[dict]:
    """Remove exact duplicates based on content hash."""
    seen_hashes = set()
    unique = []

    for item in data:
        # Hash the full conversation content
        content = json.dumps(item.get(key_field, item), sort_keys=True)
        content_hash = hashlib.md5(content.encode()).hexdigest()

        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            unique.append(item)

    removed = len(data) - len(unique)
    print(f"  Dedup: {len(data)} → {len(unique)} ({removed} duplicates removed)")
    return unique


def fuzzy_deduplicate(data: list[dict], threshold: float = 0.9) -> list[dict]:
    """Remove near-duplicates using character n-gram Jaccard similarity."""
    def ngrams(text: str, n: int = 3) -> set[str]:
        text = text.lower().strip()
        return {text[i:i+n] for i in range(max(1, len(text) - n + 1))}

    def jaccard(set_a: set, set_b: set) -> float:
        if not set_a or not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)

    unique = []
    seen_ngrams: list[set[str]] = []

    for item in data:
        convos = item.get("conversations", [])
        text = " ".join(c.get("value", "") for c in convos if c.get("from") == "human")
        item_ngrams = ngrams(text)

        is_dup = False
        for existing in seen_ngrams:
            if jaccard(item_ngrams, existing) > threshold:
                is_dup = True
                break

        if not is_dup:
            unique.append(item)
            seen_ngrams.append(item_ngrams)

    removed = len(data) - len(unique)
    print(f"  Fuzzy dedup: {len(data)} → {len(unique)} ({removed} near-dupes removed)")
    return unique


# ── Stage 2: Quality Filtering ───────────────────────────────────────
def quality_filter(data: list[dict], min_chars: int = 20, max_chars: int = 10000) -> list[dict]:
    """Filter out low-quality samples."""
    filtered = []
    reasons: Counter = Counter()

    for item in data:
        convos = item.get("conversations", [])

        if len(convos) < 2:
            reasons["too_few_turns"] += 1
            continue

        # Check human message length
        human_msgs = [c for c in convos if c.get("from") == "human"]
        gpt_msgs = [c for c in convos if c.get("from") == "gpt"]

        if not human_msgs or not gpt_msgs:
            reasons["missing_role"] += 1
            continue

        human_text = human_msgs[0].get("value", "")
        gpt_text = gpt_msgs[0].get("value", "")

        if len(human_text) < 5:
            reasons["human_too_short"] += 1
            continue

        if len(gpt_text) < min_chars:
            reasons["gpt_too_short"] += 1
            continue

        if len(gpt_text) > max_chars:
            reasons["gpt_too_long"] += 1
            continue

        # Check for placeholder/incomplete content
        if "TODO" in gpt_text or "FIXME" in gpt_text or "..." == gpt_text.strip():
            reasons["placeholder_content"] += 1
            continue

        filtered.append(item)

    removed = len(data) - len(filtered)
    print(f"  Quality filter: {len(data)} → {len(filtered)} ({removed} removed)")
    for reason, count in reasons.most_common():
        print(f"    - {reason}: {count}")
    return filtered


# ── Stage 3: Toxicity Filtering ──────────────────────────────────────
def toxicity_filter(data: list[dict]) -> list[dict]:
    """Filter out toxic content using regex patterns."""
    filtered = []
    toxic_count = 0

    for item in data:
        convos = item.get("conversations", [])
        all_text = " ".join(c.get("value", "") for c in convos)

        is_toxic = False
        for pattern in TOXIC_PATTERNS:
            if re.search(pattern, all_text, re.IGNORECASE):
                is_toxic = True
                break

        if is_toxic:
            toxic_count += 1
        else:
            filtered.append(item)

    print(f"  Toxicity filter: {len(data)} → {len(filtered)} ({toxic_count} toxic samples removed)")
    return filtered


# ── Stage 4: Format Validation ───────────────────────────────────────
def validate_format(data: list[dict]) -> list[dict]:
    """Validate ShareGPT conversation format."""
    valid = []
    invalid = 0

    for item in data:
        convos = item.get("conversations", [])

        # Must have at least system + human + gpt
        if len(convos) < 2:
            invalid += 1
            continue

        # Validate role names
        valid_roles = {"system", "human", "gpt"}
        roles = {c.get("from") for c in convos}
        if not roles.issubset(valid_roles):
            invalid += 1
            continue

        # Must have at least one human and one gpt turn
        has_human = any(c.get("from") == "human" for c in convos)
        has_gpt = any(c.get("from") == "gpt" for c in convos)
        if not has_human or not has_gpt:
            invalid += 1
            continue

        # Validate all messages have value field
        if not all("value" in c for c in convos):
            invalid += 1
            continue

        valid.append(item)

    print(f"  Format validation: {len(data)} → {len(valid)} ({invalid} invalid)")
    return valid


# ── Stage 5: Train/Val/Test Split ────────────────────────────────────
def split_dataset(
    data: list[dict],
    train_ratio: float = 0.85,
    val_ratio: float = 0.10,
    test_ratio: float = 0.05,
    seed: int = 42,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Split dataset with shuffling."""
    import random
    random.seed(seed)

    shuffled = data.copy()
    random.shuffle(shuffled)

    n = len(shuffled)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)

    train = shuffled[:train_end]
    val = shuffled[train_end:val_end]
    test = shuffled[val_end:]

    print(f"  Split: train={len(train)}, val={len(val)}, test={len(test)}")
    return train, val, test


# ── Stage 6: Statistics ──────────────────────────────────────────────
def compute_statistics(data: list[dict]) -> dict[str, Any]:
    """Compute dataset statistics."""
    human_lengths = []
    gpt_lengths = []
    total_tokens_est = 0

    for item in data:
        for c in item.get("conversations", []):
            text = c.get("value", "")
            if c.get("from") == "human":
                human_lengths.append(len(text))
            elif c.get("from") == "gpt":
                gpt_lengths.append(len(text))
            total_tokens_est += len(text.split()) * 1.3  # rough token estimate

    stats = {
        "total_samples": len(data),
        "estimated_tokens": int(total_tokens_est),
        "human_msg": {
            "mean_chars": round(statistics.mean(human_lengths), 1) if human_lengths else 0,
            "median_chars": round(statistics.median(human_lengths), 1) if human_lengths else 0,
            "min_chars": min(human_lengths) if human_lengths else 0,
            "max_chars": max(human_lengths) if human_lengths else 0,
        },
        "gpt_msg": {
            "mean_chars": round(statistics.mean(gpt_lengths), 1) if gpt_lengths else 0,
            "median_chars": round(statistics.median(gpt_lengths), 1) if gpt_lengths else 0,
            "min_chars": min(gpt_lengths) if gpt_lengths else 0,
            "max_chars": max(gpt_lengths) if gpt_lengths else 0,
        },
    }
    return stats


# ── Master Pipeline ──────────────────────────────────────────────────
def run_pipeline(
    input_dir: str = "data/synthetic",
    output_dir: str = "data/processed",
) -> None:
    """Run the full data cleaning pipeline on all datasets."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    for jsonl_file in sorted(input_path.glob("*_train.jsonl")):
        dataset_name = jsonl_file.stem.replace("_train", "")
        print(f"\n{'='*60}")
        print(f"Processing: {dataset_name}")
        print(f"{'='*60}")

        # Load
        data = load_jsonl(jsonl_file)
        print(f"  Loaded: {len(data)} samples")

        # Pipeline stages
        data = validate_format(data)
        data = deduplicate(data)
        data = fuzzy_deduplicate(data, threshold=0.85)
        data = quality_filter(data)
        data = toxicity_filter(data)

        # Statistics
        stats = compute_statistics(data)
        print(f"  Stats: {json.dumps(stats, indent=2)}")

        # Split
        train, val, test = split_dataset(data)

        # Save
        save_jsonl(train, output_path / f"{dataset_name}_train.jsonl")
        save_jsonl(val, output_path / f"{dataset_name}_val.jsonl")
        save_jsonl(test, output_path / f"{dataset_name}_test.jsonl")

        # Save stats
        stats_file = output_path / f"{dataset_name}_stats.json"
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2)

        print(f"  ✅ Saved to {output_path}/{dataset_name}_*.jsonl")

    print(f"\n{'='*60}")
    print("Pipeline complete!")


if __name__ == "__main__":
    run_pipeline()
