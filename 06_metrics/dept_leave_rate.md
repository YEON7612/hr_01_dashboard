---
metric_id: dept_leave_rate
name: 부서별 퇴사율
formula_type: ratio
table: HR_직원
groupby: 부서
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
owner_note: "overall_leave_rate와 같은 필터를 부서 단위로 그룹핑한 것. 대시보드의 '퇴사율 최고 부서' KPI 카드가 이 값의 idxmax()."
---

## 정의 배경

`overall_leave_rate`와 동일한 필터(재직상태 == '퇴사')를 부서별로 그룹핑해 계산한다. 6개 부서(CS/개발/생산/영업/인사/재무) 전부 포함 — `지표정의서.md` 2번 항목과 동일.

실제 데이터 기준(2026-08-22 확인) 부서별 인원과 퇴사율:

| 부서 | 전체인원 | 퇴사인원 | 퇴사율 |
|---|---|---|---|
| 개발 | 52 | 10 | 19.2% |
| CS | 52 | 7 | 13.5% |
| 영업 | 52 | 6 | 11.5% |
| 생산 | 37 | 3 | 8.1% |
| 인사 | 43 | 3 | 7.0% |
| 재무 | 64 | 2 | 3.1% |

부서당 최소 37명(생산)~최대 64명(재무)으로 전 부서가 `min_sample`(30) 이상이라 표본부족 경고 없이 신뢰할 수 있음.
