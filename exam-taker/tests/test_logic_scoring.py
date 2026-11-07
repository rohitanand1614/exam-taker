import pytest
from utils.scoring import calculate_f1_score, score_to_quality

pytestmark = pytest.mark.logic


def test_f1_exact():
    assert calculate_f1_score([1], [1]) == 1.0
    assert calculate_f1_score([2, 0], [0, 2]) == 1.0


def test_f1_partial():
    # selected {0}, correct {0,2}: p=1, r=.5 -> 2/3
    assert calculate_f1_score([0], [0, 2]) == pytest.approx(2 / 3)
    # selected {0,1}, correct {0}: p=.5, r=1 -> 2/3
    assert calculate_f1_score([0, 1], [0]) == pytest.approx(2 / 3)


def test_f1_wrong():
    assert calculate_f1_score([3], [1]) == 0.0


def test_f1_empty():
    assert calculate_f1_score([], [1]) == 0.0
    assert calculate_f1_score([], []) == 1.0
    assert calculate_f1_score([1], []) == 0.0


@pytest.mark.parametrize("score,q", [
    (1.0, 5), (0.99, 4), (0.8, 4), (0.79, 3), (0.6, 3),
    (0.59, 2), (0.4, 2), (0.39, 1), (0.2, 1), (0.19, 0), (0.0, 0),
])
def test_score_to_quality(score, q):
    assert score_to_quality(score) == q
