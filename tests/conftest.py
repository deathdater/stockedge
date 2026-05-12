from datetime import date, timedelta

import pytest

from project.apps.features.contracts import FeatureInputRow
from project.apps.labels.contracts import LabelInputRow


@pytest.fixture
def deterministic_feature_rows():
    base = date(2026, 1, 1)
    return [
        FeatureInputRow(symbol="ABC", date=base + timedelta(days=i), close=100 + (i * 2), volume=1_000 + i * 10)
        for i in range(8)
    ]


@pytest.fixture
def deterministic_label_rows():
    base = date(2026, 1, 1)
    closes = [100, 103, 102, 106, 109, 108, 111]
    return [LabelInputRow(symbol="ABC", date=base + timedelta(days=i), close=close) for i, close in enumerate(closes)]
