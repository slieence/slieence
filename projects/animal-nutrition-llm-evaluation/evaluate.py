
#!/usr/bin/env python3
"""Summarize human-assigned scores in the demo evaluation dataset."""

import argparse
import csv
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SCORE_FIELDS = (
    "accuracy_score",
    "reasoning_score",
    "task_fit_score",
    "calibration_score",
)

REQUIRED_FIELDS = {
    "case_id",
    "topic",
    "review_note",
    *SCORE_FIELDS,
}


def classify(total_score: int) -> str:
    """Classify a case using the 8-point scoring rubric."""
    if total_score >= 7:
        return "较好"
    if total_score >= 5:
        return "建议复核"
    return "重点复核"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="汇总动物营养大模型回答评测的人工评分。"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=BASE_DIR / "data" / "evaluation_cases.csv",
        help="输入案例 CSV 文件路径",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BASE_DIR / "results" / "evaluation_summary.csv",
        help="输出评分汇总 CSV 文件路径",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"找不到输入文件：{args.input}")

    results = []
    seen_case_ids = set()

    with args.input.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)

        missing_fields = REQUIRED_FIELDS - set(
            reader.fieldnames or []
        )
        if missing_fields:
            missing = "、".join(sorted(missing_fields))
            raise SystemExit(f"输入文件缺少必要字段：{missing}")

        for line_number, row in enumerate(reader, start=2):
            if not any(
                (value or "").strip()
                for value in row.values()
            ):
                continue

            case_id = (row.get("case_id") or "").strip()

            if not case_id:
                raise SystemExit(
                    f"第 {line_number} 行缺少 case_id。"
                )

            if case_id in seen_case_ids:
                raise SystemExit(
                    f"发现重复 case_id：{case_id}"
                )

            seen_case_ids.add(case_id)

            scores = {}

            for field in SCORE_FIELDS:
                raw_value = (row.get(field) or "").strip()

                try:
                    score = int(raw_value)
                except ValueError:
                    raise SystemExit(
                        f"第 {line_number} 行的 {field} "
                        f"不是有效整数：{raw_value!r}"
                    )

                if score not in (0, 1, 2):
                    raise SystemExit(
                        f"第 {line_number} 行的 {field} "
                        "必须为 0、1 或 2。"
                    )

                scores[field] = score

            total_score = sum(scores.values())

            result = {
                "case_id": case_id,
                "topic": (row.get("topic") or "").strip(),
            }

            # 保留每个维度的原始人工评分
            result.update(scores)

            result.update({
                "total_score": total_score,
                "max_score": 8,
                "score_percent": (
                    f"{total_score / 8 * 100:.1f}"
                ),
                "review_status": classify(total_score),
                "review_note": (
                    row.get("review_note") or ""
                ).strip(),
            })

            results.append(result)

    if not results:
        raise SystemExit("输入文件中没有可评测的案例。")

    args.output.parent.mkdir(
        parents=True, exist_ok=True
    )

    output_fields = [
        "case_id",
        "topic",
        *SCORE_FIELDS,
        "total_score",
        "max_score",
        "score_percent",
        "review_status",
        "review_note",
    ]

    with args.output.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=output_fields
        )
        writer.writeheader()
        writer.writerows(results)

    status_counts = Counter(
        row["review_status"] for row in results
    )
    average_score = (
        sum(row["total_score"] for row in results)
        / len(results)
    )

    print(f"评测案例数：{len(results)}")
    print(
        f"平均得分：{average_score:.2f}/8 "
        f"（{average_score / 8 * 100:.1f}%）"
    )
    print("复核等级统计：")

    for status in ("较好", "建议复核", "重点复核"):
        print(
            f"  {status}："
            f"{status_counts.get(status, 0)}"
        )

    print(f"结果已保存至：{args.output}")


if __name__ == "__main__":
    main()
