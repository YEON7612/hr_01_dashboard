---
metric_id: avg_overtime
name: 전사 월별 평균 초과근무시간
formula_type: mean
table: HR_근태
value_col: 초과근무시간
groupby: null
time_col: 년월
depends_on: []
lag_months: 0
base_metric: null
valid_range:
  start: "2025-01"
  end: "2026-03"
min_sample: 30
threshold_status: null
confidence: 높음
status: 확정
owner_note: "선행지표 후보(overtime_increase_rate_3m)의 기준 지표. 이 지표 자체는 후행지표(당월 실측치)."
---

## 정의 배경

`overtime_increase_rate_3m`은 "무엇의" 증가율인지 정해져야 계산되므로, 수준 지표를 먼저 만든다(교안 6-3과 동일한 구조 — `avg_data_usage → usage_decline_rate_3m`).

`HR_근태` 병합본(2025-01~2026-03)을 시간(년월) 기준으로 전사 평균만 낸 것 — 부서 구분 없음. 부서별로 보려면 `dept_avg_overtime`(그레인 없는 버전, 이미 존재)과는 별개로 시계열 버전을 새로 만들어야 함(현재는 전사 단일값만 지원).
