"""產生【虛構】示範資料：甲縣（虛構） 8 個行政區（A–H 為代號）2025 年每月篩檢統計。
資料為隨機模擬，不代表任何真實地區或個案。刻意加入常見的髒資料供課堂清理示範。
2025 年 1、2、12 月的陽性率乘上 1.25 的季節因子（模擬用，非真實現象）。
用法：python3 scripts/make_sample_data.py
輸出（docs/sample-data/）：
  demo_fictional_screening_dirty.csv        髒資料 99 列（學員上傳用）
  demo_fictional_screening_clean_96rows.csv 汙染前的原始 96 列（解答用）
  demo_fictional_screening_analysis_91rows.csv 學員依規則清理後的分析用資料 91 列
"""
import json, math, random
import pandas as pd

OUT = "docs/sample-data/"
random.seed(2025)
districts = {"A區": 52000, "B區": 38000, "C區": 27000, "D區": 61000,
             "E區": 19000, "F區": 44000, "G區": 33000, "H區": 15000}
base_rate = {"A區": .062, "B區": .048, "C區": .071, "D區": .055,
             "E區": .083, "F區": .050, "G區": .058, "H區": .090}
rows = []
for m in range(1, 13):
    season = 1 + 0.25 * (1 if m in (1, 2, 12) else 0)
    for d, pop in districts.items():
        screened = int(pop * random.uniform(.025, .04))
        pos = int(screened * base_rate[d] * season * random.uniform(.85, 1.15))
        vacc = int(pop * random.uniform(.004, .009))
        rows.append(dict(月份=f"2025-{m:02d}", 行政區=d, 人口數=pop,
                         篩檢人數=screened, 陽性數=pos, 疫苗接種人數=vacc))
clean = pd.DataFrame(rows)
clean.to_csv(OUT + "demo_fictional_screening_clean_96rows.csv", index=False, encoding="utf-8-sig")

# ---- 製造髒資料 ----
dirty = clean.copy()
dirty.loc[5, "行政區"] = "F 區"
dirty.loc[17, "行政區"] = "b區"      # 只改寫法（原為 B區）
dirty.loc[40, "月份"] = "2025/6"      # 只改格式（原為 2025-06）
dirty.loc[62, "月份"] = "2025/8"
for i in (9, 33, 71, 80):
    dirty.loc[i, "篩檢人數"] = None
dirty.loc[25, "陽性數"] = int(dirty.loc[25, "篩檢人數"]) + 120
dirty = pd.concat([dirty, dirty.iloc[[3, 28, 55]]], ignore_index=True)
dirty = dirty.sample(frac=1, random_state=7).reset_index(drop=True)
dirty["篩檢人數"] = dirty["篩檢人數"].astype("Int64")   # 避免輸出 664.0
dirty.to_csv(OUT + "demo_fictional_screening_dirty.csv", index=False, encoding="utf-8-sig")

# ---- 學員版：依講義規則清理（去重、統一寫法/格式；缺值與待查列排除分析）----
s = dirty.copy()
s["行政區"] = s["行政區"].str.replace(" ", "").str.upper()
s["月份"] = s["月份"].str.replace("/", "-").str.replace(r"-(\d)$", r"-0\1", regex=True)
s = s.drop_duplicates()
assert len(s) == 96
trap = s.copy()                                   # 沒排除時的結果（教學警訊用）
ana = s[s["篩檢人數"].notna() & (s["陽性數"] <= s["篩檢人數"])].copy()
assert len(ana) == 91
assert not ana.duplicated(["月份", "行政區"]).any(), "分析用資料不得有重複的月份×行政區"
assert dirty.duplicated().sum() == 3 and dirty["篩檢人數"].isna().sum() == 4
assert (dirty["陽性數"] > dirty["篩檢人數"]).sum() == 1
ana = ana.sort_values(["月份", "行政區"]).reset_index(drop=True)
ana.to_csv(OUT + "demo_fictional_screening_analysis_91rows.csv", index=False, encoding="utf-8-sig")

def wilson(p, n, z=1.96):
    ph = p / n; den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return round((c - h) * 100, 2), round((c + h) * 100, 2)

def by_district(df):
    g = df.groupby("行政區").agg(s=("篩檢人數", "sum"), p=("陽性數", "sum"))
    out = []
    for k, v in g.iterrows():
        lo, hi = wilson(int(v.p), int(v.s))
        out.append(dict(name=k, screened=int(v.s), positive=int(v.p), months=int(df[df["行政區"] == k]["月份"].nunique()),
                        rate=round(v.p / v.s * 100, 2), lo=lo, hi=hi))
    return out

def by_month(df):
    g = df.groupby("月份").agg(s=("篩檢人數", "sum"), p=("陽性數", "sum"))
    n = df.groupby("月份")["行政區"].nunique()
    return [dict(name=k, rate=round(v.p / v.s * 100, 2), screened=int(v.s), districts=int(n[k])) for k, v in g.iterrows()]

tot = lambda df: (int(df["篩檢人數"].sum()), int(df["陽性數"].sum()))
t96, t91 = tot(clean), tot(ana)
tr = {d["name"]: d["rate"] for d in by_district(trap.dropna(subset=["篩檢人數"]))}
summary = dict(
    rows_dirty=len(dirty), rows_clean=len(clean), rows_analysis=len(ana),
    total96=dict(screened=t96[0], positive=t96[1], rate=round(t96[1] / t96[0] * 100, 2)),
    total91=dict(screened=t91[0], positive=t91[1], rate=round(t91[1] / t91[0] * 100, 2)),
    districts96=by_district(clean), districts91=by_district(ana), months91=by_month(ana),
    trap_B=tr["B區"],
    defects=dict(duplicates=3, missing_screened=4, name_variants=2, month_format=2, pos_gt_screened=1),
)
open("docs/assets/data.js", "w", encoding="utf-8").write("window.SUMMARY = " + json.dumps(summary, ensure_ascii=False) + ";\n")
print(json.dumps({k: summary[k] for k in ("total96", "total91", "trap_B")}, ensure_ascii=False))
for d in summary["districts91"]: print(d)
print("months/district(clean):", {d["name"]: d["months"] for d in summary["districts91"]})
print("districts per month:", [m["districts"] for m in summary["months91"]])
print("month min/max", min(m["screened"] for m in summary["months91"]), max(m["screened"] for m in summary["months91"]))
print(dirty.dtypes.to_dict())
