-- q-006: t분기 초과근무 -> t+1분기 평가등급 전이 테이블
-- source: data/HR_근태.csv, data/HR_평가.csv
-- related insight: 04_insights/평가_근태_관계_예측력검증.md
-- 참고: 피어슨 상관계수(0.038, 0.028)와 회귀 R²(0.002)는 이 결과를 Python(pandas/scipy)에서 계산했습니다.

WITH quarter_seq AS (
  SELECT '2025Q1' AS 분기, 1 AS seq UNION ALL
  SELECT '2025Q2', 2 UNION ALL
  SELECT '2025Q3', 3 UNION ALL
  SELECT '2025Q4', 4
),
overtime_q AS (
  SELECT
    사번,
    LEFT(년월, 4) || 'Q' ||
      CAST(CEIL(CAST(SUBSTR(년월, 6, 2) AS INT) / 3.0) AS INT) AS 분기,
    AVG(초과근무시간) AS 분기평균초과근무
  FROM HR_근태
  GROUP BY 사번, 분기
)
SELECT
  o.사번,
  o.분기            AS 선행분기,
  o.분기평균초과근무,
  g_prev.평가등급   AS 이전등급,
  g_next.평가등급   AS 다음분기등급
FROM overtime_q o
JOIN quarter_seq qs      ON o.분기 = qs.분기
JOIN quarter_seq qs_next ON qs_next.seq = qs.seq + 1
JOIN HR_평가 g_prev ON g_prev.사번 = o.사번 AND g_prev.분기 = o.분기
JOIN HR_평가 g_next ON g_next.사번 = o.사번 AND g_next.분기 = qs_next.분기
ORDER BY o.사번, o.분기;
