from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class GoldFinding:
    case_id: str
    location: str
    category: str


def precision_recall(gold: Iterable[GoldFinding], predicted: Iterable[GoldFinding]) -> tuple[float, float, float]:
    gold_keys = {(x.case_id, x.location, x.category) for x in gold}
    pred_keys = {(x.case_id, x.location, x.category) for x in predicted}
    tp = len(gold_keys & pred_keys)
    fp = len(pred_keys - gold_keys)
    fn = len(gold_keys - pred_keys)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1
