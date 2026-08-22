"""
calc_metrics.py 기본 검증 테스트.

06_metrics/*.md 지표 정의 10건이 전부 에러 없이 로드되고, 각 지표를
get_metric_value()로 계산했을 때 예외 없이 값 또는 명확한 상태 문자열이
반환되는지만 확인한다 — 값 자체가 통계적으로 맞는지는 검증하지 않는다.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import calc_metrics

EXPECTED_METRIC_IDS = {
    "avg_overtime",
    "channel_leave_rate",
    "dept_avg_overtime",
    "dept_leave_rate",
    "eval_score",
    "high_overtime_employee_rate",
    "overall_leave_rate",
    "overtime_increase_rate_3m",
    "tenure_years",
    "vacancy_gap_days",
}

ALLOWED_STATUSES = {
    "OK",
    "OK(표본부족)",
    "유효구간 밖",
    "미지원",
    "데이터 없음",
    "데이터 없음(해당 시점 0건)",
}

# time_col이 있는 지표는 valid_range 안에 드는 시점을 골라준다.
# time_col이 없는 지표(상시 지표)는 ym이 계산에 쓰이지 않으므로 None으로 둔다.
METRIC_TEST_MONTH = {
    "avg_overtime": "2025-06",
    "channel_leave_rate": None,
    "dept_avg_overtime": None,
    "dept_leave_rate": None,
    "eval_score": "2025-06",
    "high_overtime_employee_rate": "2025-06",
    "overall_leave_rate": None,
    "overtime_increase_rate_3m": "2025-06",
    "tenure_years": None,
    "vacancy_gap_days": None,
}


@pytest.fixture(scope="module")
def metric_defs():
    return calc_metrics.load_metric_defs()


@pytest.fixture(scope="module")
def tables():
    return calc_metrics.load_tables()


def test_load_metric_defs_loads_all_10(metric_defs):
    assert len(metric_defs) == 10
    assert set(metric_defs.keys()) == EXPECTED_METRIC_IDS


@pytest.mark.parametrize("metric_id", sorted(EXPECTED_METRIC_IDS))
def test_metric_computes_without_error(metric_defs, tables, metric_id):
    assert metric_id in metric_defs, f"{metric_id} 정의 파일이 06_metrics/에 없음"

    ym = METRIC_TEST_MONTH[metric_id]
    cache = {}
    val, status, n = calc_metrics.get_metric_value(metric_id, metric_defs, tables, ym, cache)

    assert status in ALLOWED_STATUSES, f"{metric_id}: 알 수 없는 상태 문자열 '{status}'"

    if status in ("OK", "OK(표본부족)"):
        assert val is not None, f"{metric_id}: 상태는 OK인데 값이 None임"
