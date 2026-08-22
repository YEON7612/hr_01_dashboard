# 06_metrics/_INDEX.md — 지표 색인 (자동 생성, 손으로 고치지 말 것)

생성 시점: calc_metrics.py --index 실행 결과. 총 4건.

| metric_id | name | formula_type | depends_on | valid_range | status |
|---|---|---|---|---|---|
| avg_overtime | 전사 월별 평균 초과근무시간 | mean | - | 2025-01~2026-03 | 확정 |
| high_overtime_employee_rate | 고초과근무자 비율 | pct_threshold | - | 2025-01~2026-03 | 검증 불가(데이터 부족, 선행지표 용도 한정) |
| overtime_increase_rate_3m | 초과근무 3개월 증가율 | pct_change | avg_overtime | 2025-04~2026-03 | 검증 불가(데이터 부족) |
| vacancy_gap_days | 부서별 평균 공석 기간(일) | fifo_gap | - | 상시 | 확정(방법론 한계 명시) |

## 의존 그래프

- `overtime_increase_rate_3m` ← `avg_overtime`
