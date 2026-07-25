-- q-002a: 부서별 분기 평균/표준편차 초과근무시간
-- source: data/HR_근태.csv, data/HR_직원.csv
-- related insight: 04_insights/부서별_근태현황.md, 04_insights/퇴사사유_강조_부서별_초과근무_추이.md

SELECT
  e.부서,
  LEFT(a.년월, 4) || 'Q' ||
    CAST(CEIL(CAST(SUBSTR(a.년월, 6, 2) AS INT) / 3.0) AS INT)   AS 분기,
  ROUND(AVG(a.초과근무시간), 2)                                   AS 평균초과근무,
  ROUND(STDDEV(a.초과근무시간), 2)                                AS 표준편차
FROM HR_근태 a
JOIN HR_직원 e ON a.사번 = e.사번
GROUP BY e.부서, 분기
ORDER BY e.부서, 분기;

-- q-002b: 퇴사사유별 인원 — 시기 구분(2022년 이전 vs 2023~2025년)
-- source: data/HR_퇴사이력.csv

SELECT
  퇴사사유,
  CASE WHEN EXTRACT(YEAR FROM 퇴사일) <= 2022
       THEN '2022년 이전' ELSE '2023~2025년' END                 AS 시기,
  COUNT(*)                                                       AS 인원수
FROM HR_퇴사이력
GROUP BY 퇴사사유, 시기
ORDER BY 시기, 인원수 DESC;
