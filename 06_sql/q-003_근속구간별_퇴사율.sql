-- q-003a: 근속구간별 퇴사율 (재직자는 2025-12-31, 퇴사자는 실제 퇴사일 기준)
-- source: data/HR_직원.csv, data/HR_퇴사이력.csv
-- related insight: 04_insights/근속구간별_퇴사율_실측결과.md

WITH tenure AS (
  SELECT
    e.사번,
    e.재직상태,
    DATE_DIFF(COALESCE(t.퇴사일, DATE '2025-12-31'), e.입사일, DAY)
      / 365.25                                                   AS 근속연수
  FROM HR_직원 e
  LEFT JOIN HR_퇴사이력 t ON e.사번 = t.사번
)
SELECT
  CASE
    WHEN 근속연수 < 1  THEN '1년 미만'
    WHEN 근속연수 < 3  THEN '1~3년'
    WHEN 근속연수 < 5  THEN '3~5년'
    WHEN 근속연수 < 10 THEN '5~10년'
    ELSE '10년 이상'
  END                                                             AS 근속구간,
  COUNT(*)                                                       AS 총인원,
  SUM(CASE WHEN 재직상태 = '퇴사' THEN 1 ELSE 0 END)             AS 퇴사인원,
  ROUND(100.0 * SUM(CASE WHEN 재직상태 = '퇴사' THEN 1 ELSE 0 END)
        / COUNT(*), 1)                                           AS 퇴사율
FROM tenure
GROUP BY 근속구간
ORDER BY MIN(근속연수);

-- q-003b: 연도별 퇴사 인원 추이
-- source: data/HR_퇴사이력.csv
-- related insight: 04_insights/퇴사이력_트렌드_사유_연도_계절성.md

SELECT EXTRACT(YEAR FROM 퇴사일) AS 연도, COUNT(*) AS 퇴사인원
FROM HR_퇴사이력
GROUP BY 연도
ORDER BY 연도;

-- q-003c: 월별(계절성) 퇴사 분포

SELECT EXTRACT(MONTH FROM 퇴사일) AS 월, COUNT(*) AS 퇴사인원
FROM HR_퇴사이력
GROUP BY 월
ORDER BY 월;
