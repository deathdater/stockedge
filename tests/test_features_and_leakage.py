from project.apps.features.services import compute_leakage_safe_rolling_features


def test_rolling_features_use_only_prior_observations(deterministic_feature_rows):
    outputs = compute_leakage_safe_rolling_features(deterministic_feature_rows, window=3)

    assert outputs[0].values["obs_count"] == 0.0
    # day2 lag should use day1 close only
    assert round(outputs[1].values["ret_1d_lag"], 6) == round((102 / 100) - 1, 6)
    # rolling mean at index 3 should use returns from indices 0..2 only (pre-update)
    expected = [
        0.0,
        (102 / 100) - 1,
        (104 / 102) - 1,
    ]
    assert round(outputs[3].values["ret_mean_3"], 6) == round(sum(expected) / len(expected), 6)


def test_rolling_window_is_bounded(deterministic_feature_rows):
    outputs = compute_leakage_safe_rolling_features(deterministic_feature_rows, window=2)
    assert outputs[-1].values["obs_count"] == 2.0
