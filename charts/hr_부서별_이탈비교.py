# -*- coding: utf-8 -*-
"""
퇴사사유별 전체기간 비율과 부서별 퇴사사유 비중을 비교하는 막대그래프 생성 스크립트

- data/HR_근태.csv, HR_직원.csv, HR_퇴사이력.csv, HR_평가.csv 를 직접 읽어서 계산 (숫자 하드코딩 금지)
- 막대 5개: 개인사유, 건강, 계약만료, 이직, 이직(경쟁사)
- 전체기간 기준 퇴사사유 비율(%) 을 막대로 표시
- 비중이 가장 높은 막대는 강조색(빨강 계열)으로 표시
- 막대 위에 퍼센트 숫자 표시
- 한글 폰트 깨짐 방지 (Malgun Gothic 미설치 환경이므로 Noto Sans CJK KR 사용)
- 결과 이미지: charts/output/부서별이탈비교.png
"""

import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ------------------------------------------------------------------
# 0. 경로 설정
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hr_01_dashboard/
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "charts", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------------------------------------------
# 1. 한글 폰트 설정 (Malgun Gothic이 없는 리눅스 환경이므로 Noto Sans CJK KR로 대체)
# ------------------------------------------------------------------
KOREAN_FONT_CANDIDATES = ["Malgun Gothic", "Noto Sans CJK KR", "NanumGothic", "Noto Sans CJK JP"]
available_fonts = {f.name for f in fm.fontManager.ttflist}
chosen_font = next((f for f in KOREAN_FONT_CANDIDATES if f in available_fonts), None)
if chosen_font is None:
    raise RuntimeError("한글을 지원하는 폰트를 찾을 수 없습니다.")

plt.rcParams["font.family"] = chosen_font
plt.rcParams["axes.unicode_minus"] = False  # 마이너스 기호 깨짐 방지

# ------------------------------------------------------------------
# 2. 원본 CSV 4개 직접 읽기
# ------------------------------------------------------------------
attendance = pd.read_csv(os.path.join(DATA_DIR, "HR_근태.csv"), encoding="utf-8-sig")
employee = pd.read_csv(os.path.join(DATA_DIR, "HR_직원.csv"), encoding="utf-8-sig")
resign = pd.read_csv(os.path.join(DATA_DIR, "HR_퇴사이력.csv"), encoding="utf-8-sig")
evaluation = pd.read_csv(os.path.join(DATA_DIR, "HR_평가.csv"), encoding="utf-8-sig")

# ------------------------------------------------------------------
# 3. 퇴사사유별 전체기간 인원수 및 비율 계산 (HR_퇴사이력.csv 기준)
# ------------------------------------------------------------------
reason_order = ["개인사유", "건강", "계약만료", "이직", "이직(경쟁사)"]

reason_count = resign.groupby("퇴사사유").size()
reason_count = reason_count.reindex(reason_order, fill_value=0)
reason_ratio = (reason_count / reason_count.sum() * 100).round(1)

print("=== 퇴사사유별 전체기간 인원수 및 비율 ===")
print(pd.DataFrame({"인원수": reason_count, "비율(%)": reason_ratio}))

# ------------------------------------------------------------------
# 4. 부서별 퇴사자 중 사유별 비중(%) 계산 (HR_직원.csv + HR_퇴사이력.csv, 사번 기준 결합)
# ------------------------------------------------------------------
merged = employee.merge(resign[["사번", "퇴사사유"]], on="사번", how="left")
merged["퇴사여부"] = merged["재직상태"] == "퇴사"

dept_reason_pct = pd.crosstab(
    merged.loc[merged["퇴사여부"], "부서"],
    merged.loc[merged["퇴사여부"], "퇴사사유"],
    normalize="index",
) * 100
dept_reason_pct = dept_reason_pct.reindex(columns=reason_order, fill_value=0).round(1)

print("\n=== 부서별 퇴사자 중 사유별 비중(%) ===")
print(dept_reason_pct)

# 부서별 비중의 사유별 평균(부서 간 평균 비중) - 전체기간 비율과의 비교 참고용
dept_reason_pct_mean = dept_reason_pct.mean(axis=0).reindex(reason_order).round(1)

print("\n=== 사유별 부서 평균 비중(%) (참고) ===")
print(dept_reason_pct_mean)

# ------------------------------------------------------------------
# 5. 막대그래프 생성 (전체기간 비율 기준, 최고 비율 막대만 강조색)
# ------------------------------------------------------------------
values = reason_ratio.reindex(reason_order).values
max_idx = values.argmax()

bar_colors = ["#4C72B0"] * len(reason_order)  # 기본색: 블루 계열
bar_colors[max_idx] = "#D62728"  # 최고 비중 막대: 레드 계열 강조

fig, ax = plt.subplots(figsize=(9, 6))
bars = ax.bar(reason_order, values, color=bar_colors, edgecolor="black", linewidth=0.6)

# 막대 위에 퍼센트 숫자 표시
for bar, val in zip(bars, values):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.8,
        f"{val:.1f}%",
        ha="center",
        va="bottom",
        fontsize=12,
        fontweight="bold",
    )

ax.set_title("퇴사사유별 전체기간 비율\n(빨강: 최고 비중 사유)", fontsize=15, fontweight="bold")
ax.set_xlabel("퇴사사유", fontsize=12)
ax.set_ylabel("비율(%)", fontsize=12)
ax.set_ylim(0, max(values) + 10)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", linestyle="--", alpha=0.4)

plt.tight_layout()

output_path = os.path.join(OUTPUT_DIR, "부서별이탈비교.png")
plt.savefig(output_path, dpi=150)
plt.close()

print(f"\n이미지 저장 완료: {output_path}")
print(f"사용된 폰트: {chosen_font}")
