---
metric_id: overall_leave_rate
name: 전사 퇴사율
formula_type: ratio
table: HR_직원
groupby: null
time_col: null
filter: "재직상태 == '퇴사'"
depends_on: []
lag_months: 0
base_metric: null
valid_range: null
min_sample: 30
threshold_status: null
confidence: 높음
status: 확정
owner_note: "대시보드 KPI 카드의 기준 지표. 재직상태 값은 '재직'/'퇴사' 두 가지뿐이라 필터가 단순함."
---

## 정의 배경

전체 300명 중 재직상태가 '퇴사'인 인원의 비율. 기간 구분 없이 누적 기준 한 값(전사 전체)으로 계산한다 — `지표정의서.md` 1번 항목과 동일한 정의.

실제 데이터 기준 값: 재직 269명, 퇴사 31명 → 전사 퇴사율 10.3%(2026-08-22 확인). 부서·채용경로별로 갈라보면 3.1%~19.2%대로 분산돼 있어 변별력은 이미 확인됨(`지표정의서.md` 1번 ⑥).

표본 크기는 전사 300명 기준이라 `min_sample` 문제는 없음.
