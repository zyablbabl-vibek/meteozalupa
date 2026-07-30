import math

from app.statistics.core import agreement, circular_mean, numeric_consensus


def test_numeric_statistics_and_sources():
    result = numeric_consensus({"ECMWF": 1.0, "GFS": 3.0, "ICON": 8.0})
    assert result["mean"] == 4
    assert result["median"] == 3
    assert result["minimum"] == 1
    assert result["minimum_source"] == "ECMWF"
    assert result["maximum"] == 8
    assert result["maximum_source"] == "ICON"
    assert result["range"] == 7
    assert math.isclose(result["standard_deviation"], math.sqrt(26 / 3))


def test_missing_one_model_is_partial_but_valid():
    result = numeric_consensus({"ECMWF": 1.0, "GFS": 3.0, "ICON": None})
    assert result["count"] == 2
    assert result["complete"] is False
    assert result["consensus_available"] is True


def test_one_model_has_no_consensus():
    result = numeric_consensus({"ECMWF": 1.0, "GFS": None, "ICON": None})
    assert result == {"count": 1, "complete": False, "consensus_available": False}


def test_circular_mean_wraps_north():
    result = circular_mean([350, 10])
    assert result is not None and min(result, 360 - result) < 1e-9


def test_circular_mean_can_be_undefined():
    assert circular_mean([0, 180]) is None


def test_agreement_thresholds():
    assert agreement("temperature_2m", 2) == "высокое"
    assert agreement("temperature_2m", 3) == "среднее"
    assert agreement("temperature_2m", 6) == "низкое"
