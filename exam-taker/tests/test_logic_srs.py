import datetime
import pytest
from utils.srs import get_initial_srs, update_srs

pytestmark = pytest.mark.logic

TODAY = datetime.date.today()


def test_initial():
    s = get_initial_srs()
    assert s == {"repetitions": 0, "interval_days": 0, "ef": 2.5,
                 "next_due": TODAY.isoformat()}


@pytest.mark.parametrize("q,reps,interval,ef", [
    (0, 0, 1, 1.7),
    (1, 0, 1, 1.96),
    (2, 0, 1, 2.18),
    (3, 1, 1, 2.36),
    (4, 1, 1, 2.5),
    (5, 1, 1, 2.6),
])
def test_update_from_initial(q, reps, interval, ef):
    out = update_srs(get_initial_srs(), q)
    assert out["repetitions"] == reps
    assert out["interval_days"] == interval
    assert out["ef"] == pytest.approx(ef)
    assert out["next_due"] == (TODAY + datetime.timedelta(days=interval)).isoformat()


def test_second_and_third_pass_intervals():
    s = update_srs(get_initial_srs(), 5)
    s = update_srs(s, 5)
    assert (s["repetitions"], s["interval_days"]) == (2, 6)
    s = update_srs(s, 5)
    assert s["repetitions"] == 3
    assert s["interval_days"] == int(6 * 2.7 + 0.5)  # 16


def test_failure_resets_repetitions():
    s = {"repetitions": 5, "interval_days": 30, "ef": 2.5, "next_due": "x"}
    out = update_srs(s, 2)
    assert out["repetitions"] == 0 and out["interval_days"] == 1


def test_ef_floor():
    s = {"repetitions": 0, "interval_days": 0, "ef": 1.3, "next_due": "x"}
    assert update_srs(s, 0)["ef"] == 1.3
