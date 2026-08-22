# 06_metrics/README.md — 지표 정의서 프론트매터 작성 규칙

이 폴더의 각 `.md` 파일은 지표 하나를 정의합니다. `scripts/calc_metrics.py`는 이 프론트매터(YAML)만 읽어서 계산합니다 — **새 지표를 추가해도 `calc_metrics.py` 코드를 고칠 필요가 없어야 합니다.** 이게 이 구조의 존재 이유입니다.

---

## 프론트매터 필드

```yaml
---
metric_id: dept_avg_overtime        # 필수. 영문 snake_case, 유일해야 함
name: 부서별 평균 초과근무시간        # 필수. 한글 표시명
formula_type: mean                  # 필수. 아래 "지원하는 formula_type" 참고
table: HR_근태                       # formula_type이 원본 테이블을 직접 쓸 때 필수
value_col: 초과근무시간               # mean/ratio에서 집계할 값 컬럼
time_col: 년월                       # 시계열 지표면 필수(YYYY-MM). 없으면 null(상시 지표)
groupby: 부서                        # 그룹 단위. 없으면 null(전사 단일값)
filter: null                        # 분자 등에 적용할 조건 (pandas query 문자열)
depends_on: []                      # 이 지표가 참조하는 다른 metric_id 목록
lag_months: 0                       # 시차. pct_change류에서만 사용
base_metric: null                   # pct_change류일 때, 시차 비교할 기준 지표의 metric_id
valid_range:                        # 계산 가능한 시점 범위. null이면 상시 유효
  start: "2025-01"
  end: "2026-03"
min_sample: 30                      # 이 인원 수 미만이면 status를 "표본부족"으로 표시
threshold_status: null              # 임계값을 쓰는 지표만: "확정" 또는 "잠정"
confidence: 높음                     # 높음/중간/낮음 — Day4 confidence 판정과 동일한 기준
status: 확정                         # 확정/잠정/폐기
owner_note: ""                      # 왜 이렇게 정의했는지 한 줄 근거
---

(본문에는 정의 배경, 채택하지 않은 대안, 근거를 자유롭게 서술)
```

## 지원하는 formula_type

| formula_type | 계산 방식 | 필요 필드 |
|---|---|---|
| `ratio` | `filter` 만족 행 수 ÷ `groupby` 내 전체 행 수 × 100 | `table`, `filter`, `groupby`(선택) |
| `mean` | `value_col`의 평균 (`groupby`·`time_col` 있으면 그 기준으로) | `table`, `value_col` |
| `pct_threshold` | 당월 `value_col`이 임계값 조건(`threshold_value`, `direction`)을 만족하는 비율 | `table`, `value_col`, `threshold_value`, `direction`(`above`/`below`), `time_col` |
| `pct_change` | `base_metric`의 (당월 값 − `lag_months`개월 전 값) ÷ `lag_months`개월 전 값 × 100 | `base_metric`, `lag_months` |
| `fifo_gap` | 그룹별 퇴사 이벤트를 이후 채용 이벤트와 FIFO(선입선출)로 1:1 매칭해 평균 공백 일수 계산 | `resign_table`, `hire_table`, `date_col_resign`, `date_col_hire`, `groupby` |

## 유효구간·최소표본 판정 규칙

- 요청한 `--month`(또는 `--quarter`)가 `valid_range` 밖이면 값은 **"유효구간 밖"** — `0`이 아님. "계산 안 됨"과 "값이 0"은 다른 의미이므로 절대 혼동하지 않는다.
- `pct_change`류는 `lag_months`만큼 이전 시점 데이터가 `base_metric`의 `valid_range` 안에 있어야만 계산됨. 없으면 마찬가지로 "유효구간 밖".
- 계산에 쓰인 표본 수가 `min_sample` 미만이면 값은 계산하되 status에 **"표본부족"**을 같이 표시한다(값 자체를 숨기지는 않음 — 참고용으로 보여주되 신뢰도가 낮음을 명시).

## 지표 목록

| metric_id | name | formula_type | status | confidence |
|---|---|---|---|---|
| overall_leave_rate | 전사 퇴사율 | ratio | 확정 | 높음 |
| dept_leave_rate | 부서별 퇴사율 | ratio | 확정 | 높음 |
| tenure_years | 근속기간(년) | mean | 확정 | 높음 |
| eval_score | 평가점수 | mean | 확정 | 중간(2025년 한정) |
| channel_leave_rate | 채용경로별 퇴사율 | ratio | 확정 | 중간(추천 27명·헤드헌팅 11명 표본 작음) |
| dept_avg_overtime | 부서별 평균 초과근무시간 | mean | 확정 | 중간(2026Q1 개인단위 신뢰불가, 부서단위만) |
| retention_target_rate | 목표 잔류율 달성률 | pct_change 아님(파생) | **확인 필요** | 낮음(목표값 90% 출처 불명) |
| top_leave_reason | 최다 퇴사사유 | 최빈값(미지원 타입) | 확정 | 중간 |
| overtime_increase_rate_3m | 초과근무 3개월 증가율 (신규) | pct_change | 잠정 | 중간 |
| avg_overtime | 전사 월별 평균 초과근무시간 (신규, 기준지표) | mean | 확정 | 높음 |
| high_overtime_employee_rate | 고초과근무자 비율 (신규) | pct_threshold | 잠정 | 낮음(임계값 순환논리) |

`retention_target_rate`, `top_leave_reason`은 현재 엔진이 지원하는 4개 formula_type에 안 맞아 `calc_metrics.py`가 아직 계산 못 함(표에는 존재를 남기되 "미지원"으로 표시) — 필요해지면 formula_type을 새로 추가해야 함.
