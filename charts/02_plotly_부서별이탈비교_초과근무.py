# -*- coding: utf-8 -*-
"""
부서별 초과근무시간(막대, 왼쪽 축) x 퇴사율(꺾은선, 오른쪽 축) 결합 차트 (dual-axis)

- data/HR_근태.csv, HR_직원.csv, HR_퇴사이력.csv, HR_평가.csv 를 사번 기준으로 연결하여 계산
  (숫자 하드코딩 금지, 파일에서 직접 읽어서 재계산)
- 막대(왼쪽 축): 부서별 평균 초과근무시간
- 꺾은선(오른쪽 축): 부서별 퇴사율(%)
- 초과근무시간 낮은 순으로 정렬
- 마우스를 올리면 초과근무시간, 퇴사율 모두 툴팁으로 표시
- fig.show() 로 확인
"""

import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ------------------------------------------------------------------
# 0. 경로 설정
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hr_01_dashboard/
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "charts", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------------------------------------------
# 1. 원본 CSV 4개 직접 읽기
# ------------------------------------------------------------------
attendance = pd.read_csv(os.path.join(DATA_DIR, "HR_근태.csv"), encoding="utf-8-sig")
employee = pd.read_csv(os.path.join(DATA_DIR, "HR_직원.csv"), encoding="utf-8-sig")
resign = pd.read_csv(os.path.join(DATA_DIR, "HR_퇴사이력.csv"), encoding="utf-8-sig")
evaluation = pd.read_csv(os.path.join(DATA_DIR, "HR_평가.csv"), encoding="utf-8-sig")

# ------------------------------------------------------------------
# 2. 사번별 평균 초과근무시간 계산 -> 부서 매핑 -> 부서별 평균 초과근무시간
# ------------------------------------------------------------------
emp_avg_overtime = attendance.groupby("사번")["초과근무시간"].mean().reset_index()

emp_full = employee.merge(emp_avg_overtime, on="사번", how="left")
emp_full = emp_full.merge(resign[["사번", "퇴사일"]], on="사번", how="left")
emp_full["퇴사여부"] = emp_full["재직상태"] == "퇴사"

dept_overtime = emp_full.groupby("부서")["초과근무시간"].mean().round(2)

dept_rate = emp_full.groupby("부서").agg(
    전체인원=("사번", "count"),
    퇴사인원=("퇴사여부", "sum"),
)
dept_rate["퇴사율(%)"] = (dept_rate["퇴사인원"] / dept_rate["전체인원"] * 100).round(1)

dept_summary = pd.DataFrame({
    "초과근무시간": dept_overtime,
    "퇴사율(%)": dept_rate["퇴사율(%)"],
    "전체인원": dept_rate["전체인원"],
    "퇴사인원": dept_rate["퇴사인원"],
}).reset_index()

# ------------------------------------------------------------------
# 3. 초과근무시간 낮은 순으로 정렬
# ------------------------------------------------------------------
dept_summary = dept_summary.sort_values("초과근무시간", ascending=True).reset_index(drop=True)

print("=== 부서별 초과근무시간 x 퇴사율 (초과근무시간 낮은 순) ===")
print(dept_summary.to_string(index=False))

# ------------------------------------------------------------------
# 4. plotly 결합 차트 (dual-axis: 막대=초과근무시간, 꺾은선=퇴사율)
# ------------------------------------------------------------------
fig = make_subplots(specs=[[{"secondary_y": True}]])

fig.add_trace(
    go.Bar(
        x=dept_summary["부서"],
        y=dept_summary["초과근무시간"],
        name="초과근무시간",
        marker_color="#4C72B0",
        text=dept_summary["초과근무시간"].apply(lambda v: f"{v:.1f}h"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>평균 초과근무시간: %{y:.1f}시간<extra></extra>",
    ),
    secondary_y=False,
)

fig.add_trace(
    go.Scatter(
        x=dept_summary["부서"],
        y=dept_summary["퇴사율(%)"],
        name="퇴사율(%)",
        mode="lines+markers",
        line=dict(color="#D62728", width=3),
        marker=dict(size=9),
        hovertemplate="<b>%{x}</b><br>퇴사율: %{y:.1f}%<extra></extra>",
    ),
    secondary_y=True,
)

fig.update_layout(
    title="부서별 초과근무시간 x 퇴사율 (초과근무시간 낮은 순 정렬)",
    font=dict(family="Noto Sans CJK KR, Malgun Gothic, sans-serif", size=14),
    hovermode="x unified",
    xaxis=dict(title="부서", categoryorder="array", categoryarray=dept_summary["부서"]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    bargap=0.3,
)

fig.update_yaxes(title_text="평균 초과근무시간(h)", secondary_y=False,
                  range=[0, dept_summary["초과근무시간"].max() + 5])
fig.update_yaxes(title_text="퇴사율(%)", secondary_y=True,
                  range=[0, dept_summary["퇴사율(%)"].max() + 10])

# ------------------------------------------------------------------
# 5. 브라우저에서 열어 확인
# ------------------------------------------------------------------
fig.show()

# 참고용으로 HTML 파일도 함께 저장 (브라우저가 없는 서버 환경에서도 파일로 열람 가능)
html_path = os.path.join(OUTPUT_DIR, "부서별_초과근무_퇴사율_결합차트.html")
fig.write_html(html_path)
print(f"HTML 저장 완료: {html_path}")
