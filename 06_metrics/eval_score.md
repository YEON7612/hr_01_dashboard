---
metric_id: eval_score
name: 평가점수
formula_type: mean
table: HR_평가
value_col: 평가점수
groupby: null
time_col: 분기
depends_on: []
lag_months: 0
base_metric: null
valid_range:
  start: "2025Q1"
  end: "2025Q4"
min_sample: 30
threshold_status: null
confidence: 중간(2025년 한정)
status: 확정
owner_note: "2025년 이전 평가 이력이 데이터에 아예 없음(Profile 단계에서 이미 확인됨) — 장기 추이 분석 시 이 커버리지 한계를 반드시 병기할 것."
---

## 정의 배경

평가등급(S/A/B/C/D)을 S=5, A=4, B=3, C=2, D=1로 환산한 뒤 평균을 낸다 — `지표정의서.md` 4번 항목과 동일. 환산은 `calc_metrics.py`의 `load_tables()`가 `HR_평가.평가등급`을 매핑해 `평가점수` 컬럼을 자동 생성해두므로, 이 정의서는 `HR_평가` 테이블을 그대로 참조하면 된다.

## 왜 time_col이 분기인가

`HR_평가`는 사번당 여러 분기(2025Q1~2025Q4) 평가를 갖고 있어 시계열 지표다. `calc_metrics.py`의 `resolve_time_key()`는 `time_col: 분기`인 지표를 만나면 요청받은 `YYYY-MM` 월을 자동으로 `YYYY-Qn` 분기로 변환해 매칭하므로, `--month` 인자를 그대로 써도 된다.

## 커버리지 한계 (반드시 병기)

2025년 4개 분기 데이터만 존재하고, 그 이전 평가 이력은 데이터에 없다. 실제 평가등급 분포(2026-08-22 확인, 총 1200건): B 404건, A 207건, D 204건, C 195건, S 190건 — 1~5점 사이에 골고루 분산돼 있어 변별력 자체는 확인됨(`지표정의서.md` 4번 ⑥). 다만 "장기 추이"를 봐야 하는 분석에는 2025년 한 해분밖에 없다는 한계를 항상 함께 표기해야 한다.
