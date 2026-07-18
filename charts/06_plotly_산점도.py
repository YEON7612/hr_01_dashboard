# -*- coding: utf-8 -*-
"""
입사연도 코호트별 퇴사율 산점도 (plotly.express scatter)

- data/HR_근태.csv, HR_직원.csv, HR_퇴사이력.csv, HR_평가.csv 를 사번 기준으로 연결하여 계산
  (숫자 하드코딩 금지, 파일에서 직접 읽어서 재계산)
- X축: 연도 (입사연도 기준 코호트)
- Y축: 해당 입사연도 코호트의 퇴사율(%)
- color: churn_yn (퇴사여부: 재직 / 퇴사)
- 점 하나 = 직원 한 명
- 마우스를 올리면 부서, 근속기간, 퇴사율(코호트 기준), 초과근무시간여부 모두 툴팁으로 표시
- fig.show() 로 확인

[참고] HR_퇴사이력.csv에는 퇴사자의 퇴사일만 있고 재직자는 퇴사일이 없어서,
"연도"를 퇴사연도로 잡으면 재직자를 표시할 축이 없습니다. 그래서 재직자/퇴사자 모두에게
공통으로 존재하는 "입사연도"를 X축 기준으로 사용했고, Y축은 같은 입사연도에 입사한
사람들 중 몇 %가 퇴사했는지(코호트 퇴사율)로 계산했습니다.
"""

import os
import pandas as pd
import plotly.express as px

# ------------------------------------------------------------------
# 0. 경로 설정
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hr_01_dashboard/
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "charts", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TODAY = pd.Timestamp("2026-07-18")

# ------------------------------------------------------------------
# 1. 원본 CSV 4개 직접 읽기
# ------------------------------------------------------------------
attendance = pd.read_csv(os.path.join(DATA_DIR, "HR_근태.csv"), encoding="utf-8-sig")
employee = pd.read_csv(os.path.join(DATA_DIR, "HR_직원.csv"), encoding="utf-8-sig")
resign = pd.read_csv(os.path.join(DATA_DIR, "HR_퇴사이력.csv"), encoding="utf-8-sig")
evaluation = pd.read_csv(os.path.join(DATA_DIR, "HR_평가.csv"), encoding="utf-8-sig")

# ------------------------------------------------------------------
# 2. 사번 기준으로 4개 테이블 연결
# ------------------------------------------------------------------
merged = employee.merge(resign[["사번", "퇴사일"]], on="사번", how="left")
merged["입사일"] = pd.to_datetime(merged["입사일"])
merged["퇴사일"] = pd.to_datetime(merged["퇴사일"])
merged["입사연도"] = merged["입사일"].dt.year
merged["churn_yn"] = merged["재직상태"].apply(lambda s: "퇴사" if s == "퇴사" else "재직")

# 근속기간(년) = 퇴사자는 (퇴사일-입사일), 재직자는 (오늘-입사일)
merged["기준일"] = merged["퇴사일"].fillna(TODAY)
merged["근속기간(년)"] = ((merged["기준일"] - merged["입사일"]).dt.days / 365.25).round(1)

# 사번별 평균 초과근무시간 계산 후, 전체 평균 대비 "높음/낮음" 여부로 변환
emp_avg_overtime = attendance.groupby("사번")["초과근무시간"].mean().reset_index()
merged = merged.merge(emp_avg_overtime, on="사번", how="left")
overall_avg_overtime = merged["초과근무시간"].mean()
merged["초과근무시간여부"] = merged["초과근무시간"].apply(
    lambda v: "높음" if pd.notna(v) and v > overall_avg_overtime else "낮음"
)

# ------------------------------------------------------------------
# 3. 입사연도 코호트별 퇴사율(%) 계산
# ------------------------------------------------------------------
cohort_rate = merged.groupby("입사연도").agg(
    전체인원=("사번", "count"),
    퇴사인원=("churn_yn", lambda s: (s == "퇴사").sum()),
)
cohort_rate["퇴사율(%)"] = (cohort_rate["퇴사인원"] / cohort_rate["전체인원"] * 100).round(1)

merged = merged.merge(cohort_rate[["퇴사율(%)"]], on="입사연도", how="left")

print("=== 입사연도 코호트별 퇴사율 ===")
print(cohort_rate.reset_index().to_string(index=False))

# ------------------------------------------------------------------
# 4. plotly.express scatter 로 시각화
# ------------------------------------------------------------------
fig = px.scatter(
    merged,
    x="입사연도",
    y="퇴사율(%)",
    color="churn_yn",
    color_discrete_map={"퇴사": "#D62728", "재직": "#4C72B0"},
    hover_data={
        "부서": True,
        "근속기간(년)": True,
        "퇴사율(%)": ":.1f",
        "초과근무시간여부": True,
        "입사연도": False,
    },
    title="입사연도 코호트별 퇴사율 (색상: 재직/퇴사 여부)",
    labels={"입사연도": "연도(입사연도)", "퇴사율(%)": "퇴사율(%)", "churn_yn": "퇴사여부"},
)

fig.update_traces(marker=dict(size=10, opacity=0.75, line=dict(width=0.5, color="white")))
fig.update_layout(
    font=dict(family="Noto Sans CJK KR, Malgun Gothic, sans-serif", size=14),
    legend_title_text="퇴사여부(churn_yn)",
)

# ------------------------------------------------------------------
# 5. 브라우저에서 열어 확인
# ------------------------------------------------------------------
fig.show()

# 참고용으로 HTML 파일도 함께 저장 (브라우저가 없는 서버 환경에서도 파일로 열람 가능)
html_path = os.path.join(OUTPUT_DIR, "산점도_연도별_퇴사율.html")
fig.write_html(html_path)
print(f"HTML 저장 완료: {html_path}")
