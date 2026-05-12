from datetime import date, timedelta

from project.apps.ml_models.services import make_walk_forward_folds


def test_walk_forward_folds_have_strict_time_order_and_no_overlap():
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(80)]
    folds = make_walk_forward_folds(dates, train_size=30, val_size=10, step=10)
    assert folds

    for fold in folds:
        assert fold.train_start <= fold.train_end < fold.val_start <= fold.val_end


def test_walk_forward_uses_sorted_unique_dates_not_random_order():
    d1 = date(2026, 1, 3)
    d2 = date(2026, 1, 1)
    d3 = date(2026, 1, 2)
    folds = make_walk_forward_folds([d1, d2, d3, d1], train_size=2, val_size=1, step=1)
    assert folds[0].train_start == d2
    assert folds[0].train_end == d3
    assert folds[0].val_start == d1
