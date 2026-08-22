---
metric_id: tenure_years
name: 근속기간(년)
formula_type: mean
table: HR_직원_파생
value_col: 근속기간(년)
groupby: null
time_col: null
depends_on: []
lag_months: 0
base_metric: null
valid_range: null
min_sample: 30
threshold_status: null
confidence: 높음
status: 확정
owner_note: "HR_직원_파생은 calc_metrics.py의 load_tables()가 자동 생성하는 파생 테이블(원본 CSV에 없음) — 06_metrics/*.md에 새 지표를 추가할 필요는 없지만, table 값을 HR_직원으로 잘못 적으면 KeyError가 난다는 점에 주의."
---

## 정의 배경

(기준일 − 입사일) ÷ 365.25, 소수 1자리 반올림. 재직자는 기준일=오늘(코드상 2026-08-01), 퇴사자는 기준일=퇴사일 — `지표정의서.md` 3번 항목과 동일한 정의.

## 왜 table이 HR_직원이 아니라 HR_직원_파생인가

근속기간(년)은 원본 CSV 어디에도 없는 파생 컬럼이다. `calc_metrics.py`의 `load_tables()`가 `HR_직원`에 `HR_퇴사이력.퇴사일`을 조인하고 365.25일 기준으로 근속기간을 계산해 `HR_직원_파생`이라는 별도 키로 저장해둔다(코드를 새로 고칠 필요 없이, 프론트매터만으로 이 파생 테이블을 그대로 참조하면 됨).

전 직원(재직·퇴사 무관) 300명을 대상으로 하며, 366.25일이 아니라 365.25일을 쓰는 이유는 윤년 보정 때문 — `지표정의서.md` 3번 ⑤와 동일.
