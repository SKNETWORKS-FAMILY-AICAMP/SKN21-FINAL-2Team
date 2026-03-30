from evaluation.common.judge_normalization import normalize_judge_score


def test_normalize_judge_score_keeps_zero_to_one_scale():
    assert normalize_judge_score(0.82) == 0.82


def test_normalize_judge_score_converts_legacy_five_point_scale():
    assert normalize_judge_score(4.24) == 0.848
    assert normalize_judge_score(5) == 1.0


def test_normalize_judge_score_clamps_out_of_range_values():
    assert normalize_judge_score(-1) == 0.0
    assert normalize_judge_score(7) == 1.0
