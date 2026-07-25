-- q-001: 부서별 퇴사율 및 위험부서 판정 (기준: 퇴사율 15% 이상)
-- source: data/HR_직원.csv
-- related insight: 04_insights/위험부서_판정.md

SELECT
  부서,
  COUNT(*)                                                       AS 총인원,
  SUM(CASE WHEN 재직상태 = '퇴사' THEN 1 ELSE 0 END)             AS 퇴사인원,
  ROUND(100.0 * SUM(CASE WHEN 재직상태 = '퇴사' THEN 1 ELSE 0 END)
        / COUNT(*), 1)                                           AS 퇴사율,
  CASE WHEN 100.0 * SUM(CASE WHEN 재직상태 = '퇴사' THEN 1 ELSE 0 END)
            / COUNT(*) >= 15 THEN '위험부서' ELSE '정상' END      AS 판정
FROM HR_직원
GROUP BY 부서
ORDER BY 퇴사율 DESC;
