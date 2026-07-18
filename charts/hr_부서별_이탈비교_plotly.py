# -*- coding: utf-8 -*-
"""
퇴사사유별 전체기간 비율을 plotly.express bar로 시각화 (인터랙티브 버전)

- data/HR_근태.csv, HR_직원.csv, HR_퇴사이력.csv, HR_평가.csv 를 직접 읽어서 계산 (숫자 하드코딩 금지)
- 막대 5개: 개인사유, 건강, 계약만료, 이직, 이직(경쟁사)
- 마우스를 올리면 부서별 퇴사인원이 툴팁으로 표시됨
- 비중이 가장 높은 막대는 강조색(빨강 계열)으로 표시
- fig.show() 로 브라우저에서 확인
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

# ------------------------------------------------------------------
# 1. 원본 CSV 4개 직접 읽기
# ------------------------------------------------------------------
attendance = pd.read_csv(os.path.join(DATA_DIR, "HR_근태.csv"), encoding="utf-8-sig")
employee = pd.read_csv(os.path.join(DATA_DIR, "HR_직원.csv"), encoding="utf-8-sig")
resign = pd.read_csv(os.path.join(DATA_DIR, "HR_퇴사이력.csv"), encoding="utf-8-sig")
evaluation = pd.read_csv(os.path.join(DATA_DIR, "HR_평가.csv"), encoding="utf-8-sig")

reason_order = ["개인사유", "건강", "계약만료", "이직", "이직(경쟁사)"]

# ------------------------------------------------------------------
# 2. 퇴사사유별 전체기간 인원수 및 비율 계산 (HR_퇴사이력.csv 기준)
# ------------------------------------------------------------------
reason_count = resign.groupby("퇴사사유").size().reindex(reason_order, fill_value=0)
reason_ratio = (reason_count / reason_count.sum() * 100).round(1)

# ------------------------------------------------------------------
# 3. 퇴사사유별 x 부서별 퇴사인원 계산 (HR_직원.csv + HR_퇴사이력.csv, 사번 기준 결합)
#    -> 툴팁에 표시할 부서별 인원 텍스트 생성
# ------------------------------------------------------------------
merged = employee.merge(resign[["사번", "퇴사사유"]], on="사번", how="left")
merged["퇴사여부"] = merged["재직상태"] == "퇴사"
leavers = merged.loc[merged["퇴사여부"]]

dept_by_reason = pd.crosstab(leavers["퇴사사유"], leavers["부서"])
dept_by_reason = dept_by_reason.reindex(reason_order, fill_value=0)

def build_hover_text(reason):
    row = dept_by_reason.loc[reason]
    row = row[row > 0].sort_values(ascending=False)
    if len(row) == 0:
        return "부서별 퇴사인원 없음"
    return "<br>".join(f"{dept}: {cnt}명" for dept, cnt in row.items())

hover_texts = [build_hover_text(r) for r in reason_order]

# ------------------------------------------------------------------
# 4. 시각화용 데이터프레임 구성
# ------------------------------------------------------------------
df = pd.DataFrame({
    "퇴사사유": reason_order,
    "비율(%)": reason_ratio.reindex(reason_order).values,
    "인원수": reason_count.reindex(reason_order).values,
    "부서별_퇴사인원": hover_texts,
})

max_reason = df.loc[df["비율(%)"].idxmax(), "퇴사사유"]
df["강조"] = df["퇴사사유"].apply(lambda r: "최고 비중" if r == max_reason else "일반")

# ------------------------------------------------------------------
# 5. plotly.express bar 로 그래프 생성
# ------------------------------------------------------------------
fig = px.bar(
    df,
    x="퇴사사유",
    y="비율(%)",
    color="강조",
    color_discrete_map={"최고 비중": "#D62728", "일반": "#4C72B0"},
    text=df["비율(%)"].apply(lambda v: f"{v:.1f}%"),
    custom_data=["부서별_퇴사인원", "인원수"],
    category_orders={"퇴사사유": reason_order},
    title="퇴사사유별 전체기간 비율 (빨강: 최고 비중 사유)",
    labels={"비율(%)": "비율(%)", "퇴사사유": "퇴사사유"},
)

fig.update_traces(
    textposition="outside",
    hovertemplate=(
        "<b>%{x}</b><br>"
        "전체 비율: %{y:.1f}%<br>"
        "전체 인원수: %{customdata[1]}명<br>"
        "----- 부서별 퇴사인원 -----<br>"
        "%{customdata[0]}"
        "<extra></extra>"
    ),
)

fig.update_layout(
    font=dict(family="Noto Sans CJK KR, Malgun Gothic, sans-serif", size=14),
    showlegend=False,
    yaxis=dict(range=[0, df["비율(%)"].max() + 10]),
    bargap=0.3,
)

# ------------------------------------------------------------------
# 6. 브라우저에서 열어 확인
# ------------------------------------------------------------------
fig.show()

# 참고용으로 HTML 파일도 함께 저장 (브라우저가 없는 서버 환경에서도 파일로 열람 가능)
html_path = os.path.join(OUTPUT_DIR, "부서별이탈비교_plotly.html")
fig.write_html(html_path)
print(f"HTML 저장 완료: {html_path}")
