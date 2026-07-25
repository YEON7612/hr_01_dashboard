-- q-007: S/A 등급 이력 보유 여부에 따른 퇴사율 비교 (기저율 대조)
-- source: data/HR_직원.csv, data/HR_평가.csv
-- related insight: 04_insights/평가_퇴사이력_비율.md

WITH sa_history AS (
  SELECT
    사번,
    MAX(CASE WHEN 평가등급 IN ('S', 'A') THEN 1 ELSE 0 END) AS SA이력보유
  FROM HR_평가
  GROUP BY 사번
)
SELECT
  s.SA이력보유,
  COUNT(*)                                                   AS 인원,
  SUM(CASE WHEN e.재직상태 = '퇴사' THEN 1 ELSE 0 END)       AS 퇴사인원,
  ROUND(100.0 * SUM(CASE WHEN e.재직상태 = '퇴사' THEN 1 ELSE 0 END)
        / COUNT(*), 1)                                       AS 퇴사율
FROM HR_직원 e
JOIN sa_history s ON e.사번 = s.사번
GROUP BY s.SA이력보유;
