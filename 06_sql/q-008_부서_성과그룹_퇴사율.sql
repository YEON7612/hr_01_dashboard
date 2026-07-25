-- q-008: 부서 x 성과그룹(고성과/중간/저성과)별 퇴사율
-- source: data/HR_직원.csv, data/HR_평가.csv
-- related insight: 04_insights/부서_성과그룹_퇴사율.md

WITH scored AS (
  SELECT
    사번,
    CASE 평가등급
      WHEN 'S' THEN 5 WHEN 'A' THEN 4 WHEN 'B' THEN 3
      WHEN 'C' THEN 2 WHEN 'D' THEN 1
    END AS 점수
  FROM HR_평가
),
perf AS (
  SELECT 사번, AVG(점수) AS 평균등급점수
  FROM scored
  GROUP BY 사번
),
grouped AS (
  SELECT
    사번,
    CASE
      WHEN 평균등급점수 >= 3.5 THEN '고성과'
      WHEN 평균등급점수 >= 2.5 THEN '중간'
      ELSE '저성과'
    END AS 성과그룹
  FROM perf
)
SELECT
  e.부서,
  g.성과그룹,
  COUNT(*)                                                   AS 총인원,
  SUM(CASE WHEN e.재직상태 = '퇴사' THEN 1 ELSE 0 END)       AS 퇴사인원,
  ROUND(100.0 * SUM(CASE WHEN e.재직상태 = '퇴사' THEN 1 ELSE 0 END)
        / COUNT(*), 1)                                       AS 퇴사율
FROM HR_직원 e
JOIN grouped g ON e.사번 = g.사번
GROUP BY e.부서, g.성과그룹
ORDER BY e.부서, g.성과그룹;
