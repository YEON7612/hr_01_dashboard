# -*- coding: utf-8 -*-
"""
부서별 퇴사율(막대, 왼쪽 축) x 최다 퇴사사유 비중(꺾은선, 오른쪽 축) 결합 차트 (dual-axis)

- data/HR_근태.csv, HR_직원.csv, HR_퇴사이력.csv, HR_평가.csv 를 사번 기준으로 연결하여 계산
  (숫자 하드코딩 금지, 파일에서 직접 읽어서 재계산)
- X축: 부서
- 막대(왼쪽 축): 부서별 퇴사율(%)
- 꺾은선(오른쪽 축): 부서별 최다 퇴사사유 비중(%)
  * '퇴사사유'는 문자(범주)라 그 자체로 선 그래프의 y값이 될 수 없어서,
    각 부서의 퇴사자 중 "가장 많이 나온 퇴사사유가 차지하는 비중(%)"으로 환산했습니다.
- 퇴사율 낮은 순으로 정렬
- 마우스를 올리면 퇴사율과 (최다) 퇴사사유 모두 툴팁으로 표시
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
# 2. 사번 기준으로 직원-퇴사이력 연결 -> 부서별 퇴사율 계산
# ------------------------------------------------------------------
merged = employee.merge(resign[["사번", "퇴사사유"]], on="사번", how="left")
merged["퇴사여부"] = merged["재직상태"] == "퇴사"

dept_rate = merged.groupby("부서").agg(
    전체인원=("사번", "count"),
    퇴사인원=("퇴사여부", "sum"),
)
dept_rate["퇴사율(%)"] = (dept_rate["퇴사인원"] / dept_rate["전체인원"] * 100).round(1)

# ------------------------------------------------------------------
# 3. 부서별 최다 퇴사사유 및 그 비중(%) 계산
# ------------------------------------------------------------------
leavers = merged.loc[merged["퇴사여부"]]
dept_reason_pct = pd.crosstab(leavers["부서"], leavers["퇴사사유"], normalize="index") * 100
top_reason = dept_reason_pct.idxmax(axis=1)
top_reason_pct = dept_reason_pct.max(axis=1).round(1)

# 전체 사유 분포 텍스트(툴팁용)
def build_reason_breakdown(dept):
    row = dept_reason_pct.loc[dept].sort_values(ascending=False)
    row = row[row > 0]
    return "<br>".join(f"{reason}: {pct:.1f}%" for reason, pct in row.items())

dept_summary = pd.DataFrame({
    "퇴사율(%)": dept_rate["퇴사율(%)"],
    "최다사유": top_reason,
    "최다사유비중(%)": top_reason_pct,
}).reset_index()
dept_summary["사유breakdown"] = dept_summary["부서"].apply(build_reason_breakdown)

# ------------------------------------------------------------------
# 4. 퇴사율 낮은 순으로 정렬
# ------------------------------------------------------------------
dept_summary = dept_summary.sort_values("퇴사율(%)", ascending=True).reset_index(drop=True)

print("=== 부서별 퇴사율 x 최다 퇴사사유 비중 (퇴사율 낮은 순) ===")
print(dept_summary[["부서", "퇴사율(%)", "최다사유", "최다사유비중(%)"]].to_string(index=False))

# ------------------------------------------------------------------
# 5. plotly 결합 차트 (dual-axis: 막대=퇴사율, 꺾은선=최다 퇴사사유 비중)
# ------------------------------------------------------------------
fig = make_subplots(specs=[[{"secondary_y": True}]])

fig.add_trace(
    go.Bar(
        x=dept_summary["부서"],
        y=dept_summary["퇴사율(%)"],
        name="퇴사율(%)",
        marker_color="#4C72B0",
        text=dept_summary["퇴사율(%)"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
        customdata=dept_summary["사유breakdown"],
        hovertemplate="<b>%{x}</b><br>퇴사율: %{y:.1f}%<br>----- 퇴사사유 분포 -----<br>%{customdata}<extra></extra>",
    ),
    secondary_y=False,
)

fig.add_trace(
    go.Scatter(
        x=dept_summary["부서"],
        y=dept_summary["최다사유비중(%)"],
        name="최다 퇴사사유 비중(%)",
        mode="lines+markers",
        line=dict(color="#D62728", width=3),
        marker=dict(size=9),
        customdata=dept_summary["최다사유"],
        hovertemplate="<b>%{x}</b><br>최다 퇴사사유: %{customdata}<br>비중: %{y:.1f}%<extra></extra>",
    ),
    secondary_y=True,
)

fig.update_layout(
    title="부서별 퇴사율 x 최다 퇴사사유 비중 (퇴사율 낮은 순 정렬)",
    font=dict(family="Noto Sans CJK KR, Malgun Gothic, sans-serif", size=14),
    hovermode="x unified",
    xaxis=dict(title="부서", categoryorder="array", categoryarray=dept_summary["부서"]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    bargap=0.3,
)

fig.update_yaxes(title_text="퇴사율(%)", secondary_y=False,
                  range=[0, dept_summary["퇴사율(%)"].max() + 10])
fig.update_yaxes(title_text="최다 퇴사사유 비중(%)", secondary_y=True,
                  range=[0, 110])

# ------------------------------------------------------------------
# 6. 브라우저에서 열어 확인
# ------------------------------------------------------------------
fig.show()

# 참고용으로 HTML 파일도 함께 저장 (브라우저가 없는 서버 환경에서도 파일로 열람 가능)
html_path = os.path.join(OUTPUT_DIR, "부서별_퇴사율_퇴사사유_결합차트.html")
fig.write_html(html_path)
print(f"HTML 저장 완료: {html_path}")
