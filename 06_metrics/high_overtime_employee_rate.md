---
metric_id: high_overtime_employee_rate
name: 고초과근무자 비율
formula_type: pct_threshold
table: HR_근태
value_col: 초과근무시간
threshold_value: 20
direction: above
groupby: null
time_col: 년월
depends_on: []
lag_months: 0
base_metric: null
valid_range:
  start: "2025-01"
  end: "2026-03"
min_sample: 30
threshold_status: 잠정
confidence: 낮음
status: 검증 불가(데이터 부족, 선행지표 용도 한정)
owner_note: "현재 시점 지표(당월 상태)로는 계산·사용 가능. '선행지표'로서의 검증은 overtime_increase_rate_3m과 같은 이유로 불가."
---

## 정의 배경

2025년 사번별 평균 초과근무시간을 구간으로 나눠 퇴사율을 비교한 결과(2026-08-01 실행):

| 임계값 | 미만 | 이상 |
|---|---|---|
| 20시간 | 224명, 퇴사율 8.0% | 76명, 퇴사율 17.1% |

20시간을 경계로 퇴사율이 2.1배 차이 나서 이 값을 채택. 다만 **같은 데이터로 임계값을 정하고 그 임계값을 검증하면 순환 논리**이므로(교안 6-2와 동일한 한계), `threshold_status: 잠정`으로 표시함.

## 용도 구분 (중요)

- **"현재 이 달 기준 고초과근무자가 몇 %인가"** — 이건 계산 가능하고 신뢰할 수 있음(당월 실측치, 후행지표로서는 유효)
- **"이 지표가 퇴사를 미리 알려주는 선행지표인가"** — 이건 `overtime_increase_rate_3m`과 동일한 이유(근태-퇴사 겹침 표본 9명뿐)로 **검증 불가**

## 확인 필요

기간을 나눠(예: 2025년 상반기로 임계값 정하고 하반기로 검증) 순환논리를 없애는 재검증 필요. 선행지표 검증은 근태 이력 확장 후 재시도.
