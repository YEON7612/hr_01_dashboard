-- q-004: 재직자 vs 퇴사자 평균 평가등급점수 비교
-- source: data/HR_직원.csv, data/HR_평가.csv
-- related insight: 04_insights/퇴사자_재직자_평가차이.md
-- 참고: 아래는 집계까지만 수행합니다. Welch's t-검정(t=0.318, p=0.752)은
--       이 결과를 Python(scipy.stats.ttest_ind, equal_var=False)에 넣어 별도로 계산했습니다.

WITH scored AS (
  SELECT
    사번,
    CASE 평가등급
      WHEN 'S' THEN 5 WHEN 'A' THEN 4 WHEN 'B' THEN 3
      WHEN 'C' THEN 2 WHEN 'D' THEN 1
    END AS 점수
  FROM HR_평가
),
per_emp AS (
  SELECT 사번, AVG(점수) AS 평균등급점수
  FROM scored
  GROUP BY 사번
)
SELECT
  e.재직상태,
  COUNT(*)                          AS 인원,
  ROUND(AVG(p.평균등급점수), 3)     AS 평균등급점수,
  ROUND(STDDEV(p.평균등급점수), 3)  AS 표준편차
FROM HR_직원 e
JOIN per_emp p ON e.사번 = p.사번
GROUP BY e.재직상태;
