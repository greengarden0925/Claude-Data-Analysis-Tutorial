"""產生【虛構】示範資料：某縣市 8 個行政區 2025 年每月篩檢統計。
資料為隨機模擬，不代表任何真實地區或個案。刻意加入常見的髒資料供課堂清理示範。
用法：python3 scripts/make_sample_data.py
"""
import json, random
import pandas as pd

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
clean.to_csv("docs/sample-data/screening_clean_answer.csv", index=False, encoding="utf-8-sig")

# ---- 製造髒資料 ----
dirty = clean.copy()
dirty.loc[5, "行政區"] = "F 區"          # 多餘空白
dirty.loc[17, "行政區"] = "a區"          # 大小寫
dirty.loc[40, "月份"] = "2025/5"         # 月份格式不一
dirty.loc[62, "月份"] = "2025/8"
for i in (9, 33, 71, 80):                # 缺值
    dirty.loc[i, "篩檢人數"] = None
dirty.loc[25, "陽性數"] = int(dirty.loc[25, "篩檢人數"]) + 120   # 陽性 > 篩檢（輸入錯誤）
dirty = pd.concat([dirty, dirty.iloc[[3, 28, 55]]], ignore_index=True)  # 3 筆重複
dirty = dirty.sample(frac=1, random_state=7).reset_index(drop=True)
dirty.to_csv("docs/sample-data/screening_demo.csv", index=False, encoding="utf-8-sig")

# ---- 解答摘要（供講義 dashboard 顯示「預期結果」）----
tot_s, tot_p = int(clean["篩檢人數"].sum()), int(clean["陽性數"].sum())
by_d = clean.groupby("行政區").agg(s=("篩檢人數", "sum"), p=("陽性數", "sum"))
by_d["rate"] = (by_d.p / by_d.s * 100).round(2)
by_m = clean.groupby("月份").agg(s=("篩檢人數", "sum"), p=("陽性數", "sum"))
by_m["rate"] = (by_m.p / by_m.s * 100).round(2)
summary = dict(
    rows_dirty=len(dirty), rows_clean=len(clean),
    total_screened=tot_s, total_positive=tot_p, overall_rate=round(tot_p / tot_s * 100, 2),
    districts=[dict(name=k, rate=float(v.rate), screened=int(v.s), positive=int(v.p)) for k, v in by_d.iterrows()],
    months=[dict(name=k, rate=float(v.rate)) for k, v in by_m.iterrows()],
    defects=dict(duplicates=3, missing_screened=4, name_variants=2, month_format=2, pos_gt_screened=1),
)
open("docs/assets/data.js", "w", encoding="utf-8").write("window.SUMMARY = " + json.dumps(summary, ensure_ascii=False) + ";\n")
print(json.dumps(summary, ensure_ascii=False, indent=1)[:900])
print(dirty.isna().sum().to_dict(), dirty.duplicated().sum())
