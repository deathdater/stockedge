from project.apps.labels.services import build_future_return_labels


def test_label_generation_by_horizon(deterministic_label_rows):
    labels = build_future_return_labels(deterministic_label_rows, horizon_days=2)
    assert len(labels) == len(deterministic_label_rows) - 2
    first = labels[0]
    assert round(first.future_return, 6) == round((102 / 100) - 1, 6)
    assert first.direction == 1


def test_label_generation_skips_when_horizon_unavailable(deterministic_label_rows):
    labels = build_future_return_labels(deterministic_label_rows, horizon_days=20)
    assert labels == []
