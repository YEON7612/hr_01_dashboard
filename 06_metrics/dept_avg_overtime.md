---
metric_id: dept_avg_overtime
name: 부서별 평균 초과근무시간
formula_type: mean
table: HR_근태
value_col: 초과근무시간
groupby: 부서
time_col: null
depends_on: []
lag_months: 0
base_metric: null
valid_range: null
min_sample: 30
threshold_status: null
confidence: 중간(2026년 1분기 개인 단위 신뢰 불가, 부서 단위만)
status: 확정
owner_note: "avg_overtime(전사 시계열, groupby 없음)과는 그레인이 다른 별도 지표 — 이쪽은 부서별로 보유 기간 전체를 뭉쳐서 낸 상시 지표(time_col 없음). 개인 단위 추이 분석에는 절대 쓰지 말 것."
---

## 정의 배경

`HR_근태.초과근무시간`을 부서별로 그룹핑해 평균을 낸다. 기간 구분 없이 보유 기간(2025-01~2026-03) 전체를 뭉쳐 한 부서당 한 값을 낸다 — `지표정의서.md` 6번 항목과 동일. `기본근무시간_가정값` 같은 파생 가정 컬럼은 집계에서 제외됨(Clean 단계 규칙4).

`HR_근태`에는 부서 컬럼이 없어서, `calc_metrics.py`의 `ensure_column()`이 사번을 매개로 `HR_직원.부서`를 자동으로 조인한다 — 이 지표 전용 로직이 아니라 어떤 groupby든 공통 적용되는 일반 규칙.

## 표본 크기·신뢰도 주의 (반드시 병기)

2026년 1분기 근태 데이터는 합성 생성분이며, **개인 단위 연속성이 낮다**(Validate 8-1 검증: 상관계수 0.279) — `지표정의서.md` 6번 ⑦과 동일한 한계. 부서 단위로 뭉쳐서 볼 때만 신뢰할 수 있고, 개인별 초과근무 추이를 분석하는 용도로는 이 지표를 쓰면 안 된다.

부서별 표본 수 자체는 매우 커서(부서당 수백 건, 전체 4407건) `min_sample`(30) 미만으로 표본부족이 뜰 일은 없다 — 이 지표의 confidence가 "중간"인 이유는 표본 크기가 아니라 위 개인 단위 신뢰도 문제 때문이다.
