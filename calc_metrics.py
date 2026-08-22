# -*- coding: utf-8 -*-
"""
scripts/calc_metrics.py

06_metrics/*.md 의 프론트매터만 읽어서 지표를 계산하는 범용 엔진.
새 지표를 추가하려면 06_metrics/에 .md 파일 하나만 추가하면 되고,
이 스크립트는 수정할 필요가 없다 (Day4 교안의 핵심 원칙).

사용법:
    python calc_metrics.py --month 2026-01
    python calc_metrics.py --month 2026-01 --metric overtime_increase_rate_3m
    python calc_metrics.py --index          # _INDEX.md 재생성

지원하는 formula_type: ratio, mean, pct_threshold, pct_change, fifo_gap
(06_metrics/README.md의 "지원하는 formula_type" 표와 반드시 일치해야 함 — fifo_gap은
vacancy_gap_days 지표 추가 시 구현되었으나 README 표 갱신이 누락되어 있었음, 2026-08-22 동기화)
"""
import argparse
import glob
import os
import re
import sys
import pandas as pd
import yaml

# Windows 콘솔(cp949 등)은 em dash(—) 같은 문자를 인코딩하지 못해 print()에서 죽는다.
# 콘솔 코드페이지와 무관하게 항상 출력되도록 stdout/stderr를 UTF-8로 강제한다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# 2026-08-22 수정: 이 파일은 원래 scripts/calc_metrics.py로 설계돼 ../06_metrics/를 바라보게
# 되어 있었지만, 실제로는 프로젝트 루트에 위치하고 06_metrics/ 폴더도 이 저장소엔 없었다(경로가
# 어긋나 있으면 --index 실행 시 정의서 0건으로 조용히 실패함). 아래는 실제 파일 배치에 맞춘 경로다.
# ⚠️ 참고: 06_metrics/에는 현재 avg_overtime, high_overtime_employee_rate, overtime_increase_rate_3m,
# vacancy_gap_days 4개 지표 정의만 있다. _INDEX.md에 있던 나머지 6개(overall_leave_rate 등)의
# 정의 파일은 이 프로젝트 폴더 어디에도 없는 상태 — 필요하면 지표정의서.md의 해당 항목을 참고해
# 06_metrics/*.md로 새로 만들어야 한다.
METRICS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "06_metrics")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# 실제 데이터 경로 (환경에 맞게 조정 가능하도록 환경변수로도 오버라이드 허용)
PATHS = {
    "HR_직원": os.environ.get("HR_직원_PATH", os.path.join(DATA_DIR, "HR_직원.csv")),
    "HR_퇴사이력": os.environ.get("HR_퇴사이력_PATH", os.path.join(DATA_DIR, "HR_퇴사이력.csv")),
    "HR_근태": os.environ.get("HR_근태_PATH", os.path.join(DATA_DIR, "HR_근태.csv")),
    "HR_평가": os.environ.get("HR_평가_PATH", os.path.join(DATA_DIR, "HR_평가.csv")),
}

SUPPORTED_TYPES = {"ratio", "mean", "pct_threshold", "pct_change", "fifo_gap"}


def load_tables():
    tables = {}
    for name, path in PATHS.items():
        if os.path.exists(path):
            tables[name] = pd.read_csv(path, encoding="utf-8-sig")
        else:
            tables[name] = None

    # 파생 컬럼 전처리 (지표별 하드코딩이 아니라, 원본에 없는 표준 파생값을 한 곳에서 미리 만들어둠)
    if tables.get("HR_평가") is not None:
        grade_map = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
        tables["HR_평가"]["평가점수"] = tables["HR_평가"]["평가등급"].map(grade_map)

    if tables.get("HR_직원") is not None:
        emp = tables["HR_직원"].copy()
        resign = tables.get("HR_퇴사이력")
        if resign is not None:
            emp = emp.merge(resign[["사번", "퇴사일"]], on="사번", how="left")
        emp["입사일"] = pd.to_datetime(emp["입사일"])
        emp["퇴사일"] = pd.to_datetime(emp.get("퇴사일"))
        as_of = pd.Timestamp("2026-08-01")  # 워크플로우 문서의 최근 실행 시점 기준
        emp["기준일"] = emp["퇴사일"].fillna(as_of)
        emp["근속기간(년)"] = ((emp["기준일"] - emp["입사일"]).dt.days / 365.25).round(1)
        tables["HR_직원_파생"] = emp

    return tables


def load_metric_defs():
    """06_metrics/*.md (README.md 제외)에서 프론트매터를 파싱해 dict로 반환."""
    defs = {}
    for path in sorted(glob.glob(os.path.join(METRICS_DIR, "*.md"))):
        if os.path.basename(path) in ("README.md", "_INDEX.md"):
            continue
        with open(path, encoding="utf-8") as f:
            content = f.read()
        m = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
        if not m:
            print(f"⚠️ 프론트매터 없음, 건너뜀: {path}")
            continue
        fm = yaml.safe_load(m.group(1))
        fm["_path"] = path
        defs[fm["metric_id"]] = fm
    return defs


def shift_month(ym, n):
    """'2026-01' 에서 n개월 전(또는 후, n음수)을 'YYYY-MM'으로."""
    year, month = map(int, ym.split("-"))
    total = year * 12 + (month - 1) - n
    return f"{total // 12}-{total % 12 + 1:02d}"


def month_to_quarter(ym):
    year, month = map(int, ym.split("-"))
    q = (month - 1) // 3 + 1
    return f"{year}Q{q}"


def in_valid_range(target, valid_range):
    if valid_range is None:
        return True
    start, end = valid_range.get("start"), valid_range.get("end")
    if start and target < start:
        return False
    if end and target > end:
        return False
    return True


def resolve_time_key(fm, ym):
    """metric의 time_col 성격(월/분기)에 맞춰 요청 시점을 변환."""
    if fm.get("time_col") == "분기":
        return month_to_quarter(ym)
    return ym


def ensure_column(df, col, tables):
    """groupby 대상 컬럼이 df에 없으면, 사번을 매개로 HR_직원에서 끌어온다.
    (특정 지표에 하드코딩된 로직이 아니라, 어떤 groupby든 공통 적용되는 일반 규칙)"""
    if col is None or col in df.columns:
        return df
    emp = tables.get("HR_직원")
    if emp is not None and "사번" in df.columns and col in emp.columns:
        return df.merge(emp[["사번", col]], on="사번", how="left")
    raise KeyError(f"컬럼 '{col}'을 찾을 수 없고, HR_직원을 통한 자동 조인도 불가능함")


def compute_ratio(fm, tables, ym):
    df = tables.get(fm["table"])
    if df is None:
        return None, "데이터 없음", 0
    df = ensure_column(df, fm.get("groupby"), tables)
    sub = df.query(fm["filter"]) if fm.get("filter") else df
    if fm.get("groupby"):
        total = df.groupby(fm["groupby"]).size()
        part = sub.groupby(fm["groupby"]).size().reindex(total.index, fill_value=0)
        rate = (part / total * 100).round(1)
        return rate, "OK", int(total.min())
    else:
        n = len(df)
        rate = round(len(sub) / n * 100, 1) if n > 0 else None
        return rate, "OK", n


def compute_mean(fm, tables, ym):
    df = tables.get(fm["table"])
    if df is None:
        return None, "데이터 없음", 0
    if fm.get("time_col"):
        key = resolve_time_key(fm, ym)
        col = fm["time_col"]
        df = df[df[col] == key]
    df = ensure_column(df, fm.get("groupby"), tables)
    if fm.get("groupby"):
        g = df.groupby(fm["groupby"])[fm["value_col"]]
        return g.mean().round(2), "OK", int(g.size().min()) if len(g) else 0
    n = len(df)
    if n == 0:
        return None, "데이터 없음(해당 시점 0건)", 0
    return round(df[fm["value_col"]].mean(), 2), "OK", n


def compute_pct_threshold(fm, tables, ym):
    df = tables.get(fm["table"])
    if df is None:
        return None, "데이터 없음", 0
    key = resolve_time_key(fm, ym)
    df = df[df[fm["time_col"]] == key]
    n = len(df)
    if n == 0:
        return None, "데이터 없음(해당 시점 0건)", 0
    if fm["direction"] == "above":
        hit = (df[fm["value_col"]] >= fm["threshold_value"]).sum()
    else:
        hit = (df[fm["value_col"]] < fm["threshold_value"]).sum()
    return round(hit / n * 100, 1), "OK", n


def compute_fifo_gap(fm, tables):
    """퇴사 이벤트를 같은 그룹(예: 부서) 내 이후 채용 이벤트와 FIFO로 1:1 매칭해
    평균 공백 일수를 계산. 같은 채용이 여러 퇴사에 중복 매칭되는 걸 방지한다."""
    resign = tables.get(fm["resign_table"])
    hire = tables.get(fm["hire_table"])
    if resign is None or hire is None:
        return None, "데이터 없음", 0

    dept_col = fm["groupby"]
    if dept_col not in resign.columns:
        resign = ensure_column(resign, dept_col, tables)

    resign = resign.copy()
    hire = hire.copy()
    resign[fm["date_col_resign"]] = pd.to_datetime(resign[fm["date_col_resign"]])
    hire[fm["date_col_hire"]] = pd.to_datetime(hire[fm["date_col_hire"]])

    gaps, n_matched = {}, 0
    for dept in hire[dept_col].dropna().unique():
        d_resigns = resign[resign[dept_col] == dept].sort_values(fm["date_col_resign"])
        d_hires = hire[hire[dept_col] == dept].sort_values(fm["date_col_hire"])[fm["date_col_hire"]].tolist()
        used = [False] * len(d_hires)
        dept_gaps = []
        for _, r in d_resigns.iterrows():
            r_date = r[fm["date_col_resign"]]
            for i, h_date in enumerate(d_hires):
                if not used[i] and h_date > r_date:
                    used[i] = True
                    dept_gaps.append((h_date - r_date).days)
                    n_matched += 1
                    break
        if dept_gaps:
            gaps[dept] = round(sum(dept_gaps) / len(dept_gaps), 1)

    if not gaps:
        return None, "데이터 없음", 0
    return pd.Series(gaps), "OK", n_matched


def compute_pct_change(fm, tables, defs, ym, cache):
    base_id = fm["base_metric"]
    base_fm = defs[base_id]
    lag = fm["lag_months"]
    prev_ym = shift_month(ym, lag)

    cur_val, cur_status, cur_n = get_metric_value(base_id, defs, tables, ym, cache)
    prev_val, prev_status, prev_n = get_metric_value(base_id, defs, tables, prev_ym, cache)

    if cur_status != "OK" or prev_status != "OK" or prev_val in (None, 0):
        return None, "유효구간 밖", 0
    change = round((cur_val - prev_val) / prev_val * 100, 2)
    return change, "OK", min(cur_n, prev_n)


def get_metric_value(metric_id, defs, tables, ym, cache):
    """의존관계를 고려해 재귀적으로 계산(+캐시)."""
    cache_key = (metric_id, ym)
    if cache_key in cache:
        return cache[cache_key]

    fm = defs[metric_id]

    if fm["formula_type"] not in SUPPORTED_TYPES:
        result = (None, "미지원", 0)
        cache[cache_key] = result
        return result

    if not in_valid_range(resolve_time_key(fm, ym) if fm.get("time_col") else ym, fm.get("valid_range")):
        result = (None, "유효구간 밖", 0)
        cache[cache_key] = result
        return result

    if fm["formula_type"] == "ratio":
        val, status, n = compute_ratio(fm, tables, ym)
    elif fm["formula_type"] == "mean":
        val, status, n = compute_mean(fm, tables, ym)
    elif fm["formula_type"] == "pct_threshold":
        val, status, n = compute_pct_threshold(fm, tables, ym)
    elif fm["formula_type"] == "pct_change":
        val, status, n = compute_pct_change(fm, tables, defs, ym, cache)
    elif fm["formula_type"] == "fifo_gap":
        val, status, n = compute_fifo_gap(fm, tables)
    else:
        val, status, n = None, "미지원", 0

    if status == "OK" and fm.get("min_sample") and n < fm["min_sample"]:
        status = "OK(표본부족)"

    result = (val, status, n)
    cache[cache_key] = result
    return result


def build_index_md(defs):
    lines = ["# 06_metrics/_INDEX.md — 지표 색인 (자동 생성, 손으로 고치지 말 것)\n"]
    lines.append(f"생성 시점: calc_metrics.py --index 실행 결과. 총 {len(defs)}건.\n")
    lines.append("| metric_id | name | formula_type | depends_on | valid_range | status |")
    lines.append("|---|---|---|---|---|---|")
    for mid, fm in sorted(defs.items()):
        deps = ", ".join(fm.get("depends_on") or []) or "-"
        vr = fm.get("valid_range")
        vr_str = f"{vr['start']}~{vr['end']}" if vr else "상시"
        lines.append(f"| {mid} | {fm['name']} | {fm['formula_type']} | {deps} | {vr_str} | {fm['status']} |")

    lines.append("\n## 의존 그래프\n")
    for mid, fm in sorted(defs.items()):
        deps = fm.get("depends_on") or []
        if deps:
            lines.append(f"- `{mid}` ← {', '.join(f'`{d}`' for d in deps)}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", help="YYYY-MM 형식")
    ap.add_argument("--metric", help="특정 metric_id만 계산")
    ap.add_argument("--index", action="store_true", help="_INDEX.md 재생성")
    args = ap.parse_args()

    defs = load_metric_defs()
    print(f"정의서 {len(defs)}건 로드됨: {', '.join(sorted(defs))}\n")

    if args.index:
        out = os.path.join(METRICS_DIR, "_INDEX.md")
        with open(out, "w", encoding="utf-8") as f:
            f.write(build_index_md(defs))
        print(f"_INDEX.md 재생성 완료: {out}")
        return

    if not args.month and not args.index:
        args.month = None  # 시간 무관 지표(fifo_gap 등)만 계산할 수 있게 허용

    tables = load_tables()
    cache = {}
    targets = [args.metric] if args.metric else sorted(defs)

    print(f"{'metric_id':<28}{'값':<20}{'상태':<16}{'표본수'}")
    print("-" * 74)
    for mid in targets:
        if mid not in defs:
            print(f"{mid:<28} 정의 없음")
            continue
        fm = defs[mid]
        if fm.get("time_col") and args.month is None:
            print(f"{mid:<28}{'-':<20}{'--month 필요':<16}0")
            continue
        val, status, n = get_metric_value(mid, defs, tables, args.month, cache)
        if isinstance(val, pd.Series):
            print(f"{mid:<28}{'(그룹별 — 아래 참고)':<20}{status:<16}{n}")
            for k, v in val.items():
                print(f"    - {k}: {v}")
        else:
            val_str = f"{val}" if val is not None else "-"
            print(f"{mid:<28}{val_str:<20}{status:<16}{n}")


if __name__ == "__main__":
    main()
