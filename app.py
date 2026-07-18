# -*- coding: utf-8 -*-
"""
직원들은 왜 퇴사하는가 — 퇴사 원인 진단 대시보드 (Streamlit)

data/HR_근태.csv, HR_직원.csv, HR_퇴사이력.csv, HR_평가.csv 를
앱 실행 시마다 직접 읽어서 모든 지표를 재계산합니다 (숫자 하드코딩 없음).

실행: streamlit run app.py
"""

import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ------------------------------------------------------------------
# 0. 기본 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="조직인력 구성 퇴사가능 예측 대시보드", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

FONT = "Noto Sans CJK KR, Malgun Gothic, sans-serif"
REASON_ORDER = ["개인사유", "건강", "계약만료", "이직", "이직(경쟁사)"]
TODAY = pd.Timestamp("2026-07-18")


# ------------------------------------------------------------------
# 1. 원본 CSV 4개 직접 읽기
# ------------------------------------------------------------------
@st.cache_data
def load_data():
    attendance = pd.read_csv(os.path.join(DATA_DIR, "HR_근태.csv"), encoding="utf-8-sig")
    employee = pd.read_csv(os.path.join(DATA_DIR, "HR_직원.csv"), encoding="utf-8-sig")
    resign = pd.read_csv(os.path.join(DATA_DIR, "HR_퇴사이력.csv"), encoding="utf-8-sig")
    evaluation = pd.read_csv(os.path.join(DATA_DIR, "HR_평가.csv"), encoding="utf-8-sig")
    return attendance, employee, resign, evaluation


@st.cache_data
def build_base(_attendance, _employee, _resign, _evaluation):
    """사번 기준으로 4개 테이블을 연결한 기본 데이터프레임 생성"""
    merged = _employee.merge(_resign[["사번", "퇴사일", "퇴사사유"]], on="사번", how="left")
    merged["퇴사여부"] = merged["재직상태"] == "퇴사"

    grade_score_map = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
    ev = _evaluation.copy()
    ev["평가점수"] = ev["평가등급"].map(grade_score_map)
    emp_avg_score = ev.groupby("사번")["평가점수"].mean().reset_index()

    emp_avg_overtime = _attendance.groupby("사번")["초과근무시간"].mean().reset_index()

    merged = merged.merge(emp_avg_score, on="사번", how="left")
    merged = merged.merge(emp_avg_overtime, on="사번", how="left")

    # ⑥ 산점도용 파생 컬럼
    merged["입사일"] = pd.to_datetime(merged["입사일"])
    merged["퇴사일"] = pd.to_datetime(merged["퇴사일"])
    merged["입사연도"] = merged["입사일"].dt.year
    merged["churn_yn"] = merged["재직상태"].apply(lambda s: "퇴사" if s == "퇴사" else "재직")
    merged["기준일"] = merged["퇴사일"].fillna(TODAY)
    merged["근속기간(년)"] = ((merged["기준일"] - merged["입사일"]).dt.days / 365.25).round(1)

    overall_avg_overtime = merged["초과근무시간"].mean()
    merged["초과근무시간여부"] = merged["초과근무시간"].apply(
        lambda v: "높음" if pd.notna(v) and v > overall_avg_overtime else "낮음"
    )
    return merged


attendance, employee, resign, evaluation = load_data()
base = build_base(attendance, employee, resign, evaluation)

# ------------------------------------------------------------------
# 2. 제목
# ------------------------------------------------------------------
st.title("직원들은 왜 퇴사하는가 — 퇴사 원인 진단 대시보드(최연욱)")
st.caption("HR_근태 · HR_직원 · HR_퇴사이력 · HR_평가 데이터를 사번 기준으로 연결하여 분석합니다.")

# ------------------------------------------------------------------
# 3. 상단 KPI 3개 (가로 배치)
# ------------------------------------------------------------------
total_emp = len(base)
total_leave = int(base["퇴사여부"].sum())
overall_rate = round(total_leave / total_emp * 100, 1)
top_dept = base.groupby("부서")["퇴사여부"].mean().idxmax()

leavers_all = base.loc[base["퇴사여부"]]
top_reason_overall = leavers_all["퇴사사유"].value_counts().idxmax()

k1, k2, k3 = st.columns(3)
k1.metric("전사 퇴사율", f"{overall_rate}%")
k2.metric("퇴사율 최고 부서", top_dept)
k3.metric("최다 퇴사사유", top_reason_overall)

st.divider()

# ------------------------------------------------------------------
# 공통: 부서별 요약 테이블 (평가점수/초과근무/퇴사인원/퇴사율/최다사유)
# ------------------------------------------------------------------
dept_score = base.groupby("부서")["평가점수"].mean().round(2)
dept_overtime = base.groupby("부서")["초과근무시간"].mean().round(2)
dept_agg = base.groupby("부서").agg(전체인원=("사번", "count"), 퇴사인원=("퇴사여부", "sum"))
dept_agg["퇴사율(%)"] = (dept_agg["퇴사인원"] / dept_agg["전체인원"] * 100).round(1)

leavers = base.loc[base["퇴사여부"]]
dept_reason_pct = pd.crosstab(leavers["부서"], leavers["퇴사사유"], normalize="index") * 100
top_reason = dept_reason_pct.idxmax(axis=1)
top_reason_pct = dept_reason_pct.max(axis=1).round(1)


def build_reason_breakdown(dept):
    row = dept_reason_pct.loc[dept].sort_values(ascending=False)
    row = row[row > 0]
    return "<br>".join(f"{reason}: {pct:.1f}%" for reason, pct in row.items())


dept_master = pd.DataFrame({
    "평가점수": dept_score,
    "초과근무시간": dept_overtime,
    "전체인원": dept_agg["전체인원"],
    "퇴사인원": dept_agg["퇴사인원"],
    "퇴사율(%)": dept_agg["퇴사율(%)"],
    "최다사유": top_reason,
    "최다사유비중(%)": top_reason_pct,
}).reset_index()
dept_master["사유breakdown"] = dept_master["부서"].apply(build_reason_breakdown)


def make_dual_axis(df, x, bar_col, line_col, bar_title, line_title,
                    bar_hover, line_hover, sort_col, chart_title):
    df_sorted = df.sort_values(sort_col, ascending=True).reset_index(drop=True)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=df_sorted[x], y=df_sorted[bar_col], name=bar_title,
        marker_color="#4C72B0", textposition="outside",
        text=df_sorted[bar_col].apply(lambda v: f"{v:.1f}" if isinstance(v, float) else str(v)),
        hovertemplate=bar_hover,
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=df_sorted[x], y=df_sorted[line_col], name=line_title,
        mode="lines+markers", line=dict(color="#D62728", width=3), marker=dict(size=9),
        hovertemplate=line_hover,
    ), secondary_y=True)
    fig.update_layout(
        title=chart_title, font=dict(family=FONT, size=14), hovermode="x unified",
        xaxis=dict(title=x, categoryorder="array", categoryarray=df_sorted[x]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        bargap=0.3,
    )
    fig.update_yaxes(title_text=bar_title, secondary_y=False)
    fig.update_yaxes(title_text=line_title, secondary_y=True)
    return fig, df_sorted


# ------------------------------------------------------------------
# ① 퇴사 사유별 이탈
# ------------------------------------------------------------------
st.subheader("① 퇴사유별 이탈")

reason_count = resign.groupby("퇴사사유").size().reindex(REASON_ORDER, fill_value=0)
reason_ratio = (reason_count / reason_count.sum() * 100).round(1)

leavers_t1 = base.loc[base["퇴사여부"]]
dept_by_reason = pd.crosstab(leavers_t1["퇴사사유"], leavers_t1["부서"]).reindex(REASON_ORDER, fill_value=0)


def build_hover_text(reason):
    row = dept_by_reason.loc[reason]
    row = row[row > 0].sort_values(ascending=False)
    return "<br>".join(f"{d}: {c}명" for d, c in row.items()) if len(row) else "부서별 퇴사인원 없음"


df1 = pd.DataFrame({
    "퇴사사유": REASON_ORDER,
    "비율(%)": reason_ratio.reindex(REASON_ORDER).values,
    "인원수": reason_count.reindex(REASON_ORDER).values,
    "부서별_퇴사인원": [build_hover_text(r) for r in REASON_ORDER],
})
max_reason = df1.loc[df1["비율(%)"].idxmax(), "퇴사사유"]
df1["강조"] = df1["퇴사사유"].apply(lambda r: "최고 비중" if r == max_reason else "일반")

colors1 = df1["강조"].map({"최고 비중": "#D62728", "일반": "#4C72B0"})
fig1 = go.Figure(go.Bar(
    x=df1["퇴사사유"], y=df1["비율(%)"], marker_color=colors1,
    text=df1["비율(%)"].apply(lambda v: f"{v:.1f}%"), textposition="outside",
    customdata=df1[["부서별_퇴사인원", "인원수"]],
    hovertemplate="<b>%{x}</b><br>전체 비율: %{y:.1f}%<br>전체 인원수: %{customdata[1]}명<br>"
                  "----- 부서별 퇴사인원 -----<br>%{customdata[0]}<extra></extra>",
))
fig1.update_layout(
    title="퇴사사유별 전체기간 비율 (빨강: 최고 비중 사유)",
    font=dict(family=FONT, size=14),
    xaxis_title="퇴사사유", yaxis_title="비율(%)",
    yaxis=dict(range=[0, df1["비율(%)"].max() + 10]),
)
st.plotly_chart(fig1, use_container_width=True)

st.divider()

# ------------------------------------------------------------------
# ② 평가점수별 이탈
# ------------------------------------------------------------------
st.subheader("② 평가점수별 이탈")
st.caption("평가등급(S/A/B/C/D)은 S=5, A=4, B=3, C=2, D=1 점으로 환산했습니다.")
fig2, df2 = make_dual_axis(
    dept_master, "부서", "평가점수", "퇴사율(%)",
    "평가점수(5점 만점)", "퇴사율(%)",
    "<b>%{x}</b><br>평가점수: %{y:.2f}점<extra></extra>",
    "<b>%{x}</b><br>퇴사율: %{y:.1f}%<extra></extra>",
    "평가점수", "부서별 평가점수 x 퇴사율 (평가점수 낮은 순 정렬)",
)
st.plotly_chart(fig2, use_container_width=True)
st.dataframe(df2[["부서", "평가점수", "퇴사율(%)", "전체인원", "퇴사인원"]], hide_index=True)

st.divider()

# ------------------------------------------------------------------
# ③ 초과 근무시간 이탈
# ------------------------------------------------------------------
st.subheader("③ 초과 근무시간 이탈")
fig3, df3 = make_dual_axis(
    dept_master, "부서", "초과근무시간", "퇴사율(%)",
    "평균 초과근무시간(h)", "퇴사율(%)",
    "<b>%{x}</b><br>평균 초과근무시간: %{y:.1f}시간<extra></extra>",
    "<b>%{x}</b><br>퇴사율: %{y:.1f}%<extra></extra>",
    "초과근무시간", "부서별 초과근무시간 x 퇴사율 (초과근무시간 낮은 순 정렬)",
)
st.plotly_chart(fig3, use_container_width=True)
st.dataframe(df3[["부서", "초과근무시간", "퇴사율(%)", "전체인원", "퇴사인원"]], hide_index=True)

st.divider()

# ------------------------------------------------------------------
# ④ 부서별 퇴사율
# ------------------------------------------------------------------
st.subheader("④ 부서별 퇴사율")
fig4, df4 = make_dual_axis(
    dept_master, "부서", "퇴사인원", "퇴사율(%)",
    "퇴사인원(명)", "퇴사율(%)",
    "<b>%{x}</b><br>퇴사인원: %{y}명<extra></extra>",
    "<b>%{x}</b><br>퇴사율: %{y:.1f}%<extra></extra>",
    "퇴사인원", "부서별 퇴사인원 x 퇴사율 (퇴사인원 낮은 순 정렬)",
)
st.plotly_chart(fig4, use_container_width=True)
st.dataframe(df4[["부서", "전체인원", "퇴사인원", "퇴사율(%)"]], hide_index=True)

st.divider()

# ------------------------------------------------------------------
# ⑤ 부서별&퇴사율 퇴사사유별
# ------------------------------------------------------------------
st.subheader("⑤ 부서별&퇴사율 퇴사사유별")
st.caption("퇴사사유는 범주형이라, 각 부서 퇴사자 중 가장 많이 나온 사유의 비중(%)으로 환산했습니다.")

df5_sorted = dept_master.sort_values("퇴사율(%)", ascending=True).reset_index(drop=True)
fig5 = make_subplots(specs=[[{"secondary_y": True}]])
fig5.add_trace(go.Bar(
    x=df5_sorted["부서"], y=df5_sorted["퇴사율(%)"], name="퇴사율(%)",
    marker_color="#4C72B0", text=df5_sorted["퇴사율(%)"].apply(lambda v: f"{v:.1f}%"),
    textposition="outside", customdata=df5_sorted["사유breakdown"],
    hovertemplate="<b>%{x}</b><br>퇴사율: %{y:.1f}%<br>----- 퇴사사유 분포 -----<br>%{customdata}<extra></extra>",
), secondary_y=False)
fig5.add_trace(go.Scatter(
    x=df5_sorted["부서"], y=df5_sorted["최다사유비중(%)"], name="최다 퇴사사유 비중(%)",
    mode="lines+markers", line=dict(color="#D62728", width=3), marker=dict(size=9),
    customdata=df5_sorted["최다사유"],
    hovertemplate="<b>%{x}</b><br>최다 퇴사사유: %{customdata}<br>비중: %{y:.1f}%<extra></extra>",
), secondary_y=True)
fig5.update_layout(
    title="부서별 퇴사율 x 최다 퇴사사유 비중 (퇴사율 낮은 순 정렬)",
    font=dict(family=FONT, size=14), hovermode="x unified",
    xaxis=dict(title="부서", categoryorder="array", categoryarray=df5_sorted["부서"]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    bargap=0.3,
)
fig5.update_yaxes(title_text="퇴사율(%)", secondary_y=False)
fig5.update_yaxes(title_text="최다 퇴사사유 비중(%)", secondary_y=True, range=[0, 110])
st.plotly_chart(fig5, use_container_width=True)
st.dataframe(df5_sorted[["부서", "퇴사율(%)", "최다사유", "최다사유비중(%)"]], hide_index=True)

st.divider()

# ------------------------------------------------------------------
# ⑥ 연도별 퇴사율
# ------------------------------------------------------------------
st.subheader("⑥ 연도별 퇴사율")
st.caption(
    "퇴사자만 퇴사일이 있어 '연도'를 퇴사연도로 잡으면 재직자를 표시할 축이 없습니다. "
    "그래서 재직자·퇴사자 모두 공통으로 갖는 '입사연도'를 X축으로 사용했고, "
    "Y축은 같은 해에 입사한 사람들 중 몇 %가 퇴사했는지(코호트 퇴사율)로 계산했습니다."
)

cohort_rate = base.groupby("입사연도").agg(
    전체인원=("사번", "count"),
    퇴사인원=("churn_yn", lambda s: (s == "퇴사").sum()),
)
cohort_rate["퇴사율(%)"] = (cohort_rate["퇴사인원"] / cohort_rate["전체인원"] * 100).round(1)

scatter_df = base.merge(cohort_rate[["퇴사율(%)"]], on="입사연도", how="left")

fig6 = px.scatter(
    scatter_df,
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
fig6.update_traces(marker=dict(size=10, opacity=0.75, line=dict(width=0.5, color="white")))
fig6.update_layout(font=dict(family=FONT, size=14), legend_title_text="퇴사여부(churn_yn)")

st.plotly_chart(fig6, use_container_width=True)
st.dataframe(cohort_rate.reset_index(), hide_index=True)

st.divider()
st.caption("주의: HR_평가·HR_근태 데이터는 2025년치만 존재하여, 2025년 이전 퇴사자는 퇴사 전 평가/근태 기록이 없을 수 있습니다.")
