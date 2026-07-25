-- q-005: 퇴사가능성 예측모델 학습용 피처 테이블
-- source: data/HR_직원.csv, data/HR_퇴사이력.csv, data/HR_평가.csv, data/HR_근태.csv
-- related insight: 04_insights/퇴사가능성_예측모델.md
-- 참고: 로지스틱 회귀 학습(AUC 0.838)과 표준화 자체는 Python(scikit-learn)에서 수행되었습니다.
--       이 쿼리는 그 입력이 되는 개인별 피처(근속연수·등급추세·평균등급점수·평균초과근무·초과근무변동성)를 만듭니다.

WITH tenure AS (
  SELECT
    e.사번,
    e.재직상태,
    DATE_DIFF(COALESCE(t.퇴사일, DATE '2025-12-31'), e.입사일, DAY)
      / 365.25 AS 근속연수
  FROM HR_직원 e
  LEFT JOIN HR_퇴사이력 t ON e.사번 = t.사번
),
scored AS (
  SELECT
    사번, 분기,
    CASE 평가등급
      WHEN 'S' THEN 5 WHEN 'A' THEN 4 WHEN 'B' THEN 3
      WHEN 'C' THEN 2 WHEN 'D' THEN 1
    END AS 점수
  FROM HR_평가
),
grade_trend AS (
  SELECT
    사번,
    AVG(CASE WHEN 분기 IN ('2025Q3', '2025Q4') THEN 점수 END)
      - AVG(CASE WHEN 분기 IN ('2025Q1', '2025Q2') THEN 점수 END) AS 등급추세,
    AVG(점수)                                                     AS 평균등급점수
  FROM scored
  GROUP BY 사번
),
overtime AS (
  SELECT
    사번,
    AVG(초과근무시간)    AS 평균초과근무,
    STDDEV(초과근무시간) AS 초과근무변동성
  FROM HR_근태
  GROUP BY 사번
)
SELECT
  tn.사번,
  tn.재직상태,
  tn.근속연수,
  gt.등급추세,
  gt.평균등급점수,
  ot.평균초과근무,
  ot.초과근무변동성
FROM tenure tn
JOIN grade_trend gt ON tn.사번 = gt.사번
JOIN overtime ot ON tn.사번 = ot.사번;
