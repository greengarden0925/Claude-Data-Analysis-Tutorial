"""步驟 1：資料體檢與清理（虛構資料）

輸入：01_原始資料/demo_fictional_screening_dirty.csv（不會被修改）
輸出：02_清理後資料/分析用資料.csv、02_清理後資料/修正與排除紀錄.csv

清理規則（由使用者決定，不是 AI 決定）：
  1. 完全重複的列只保留一筆
  2. 行政區統一為「X區」格式（去空白、大寫）
  3. 月份統一為 YYYY-MM
  4. 篩檢人數缺值：不補值，也不放進分析用資料
  5. 陽性數 > 篩檢人數：不修改，標記「待查」，也不放進分析用資料（缺值列不算待查）

執行方式（在成果包最上層資料夾）：python 03_程式碼/01_clean.py
"""
import pandas as pd
from _common import RAW_FILE, CLEAN_FILE, LOG_FILE

raw = pd.read_csv(RAW_FILE, dtype=str)
raw["CSV列號"] = raw.index + 2                     # 標題列是第 1 列
cols = ["月份", "行政區", "人口數", "篩檢人數", "陽性數", "疫苗接種人數"]
valid_names = {f"{c}區" for c in "ABCDEFGH"}
print(f"原始列數：{len(raw)}")

# ---------- 體檢：只檢查、不修改 ----------
log, seen = [], set()
for _, r in raw.iterrows():
    key = tuple(r[cols].fillna("").tolist())
    if key in seen:
        log.append((r["CSV列號"], r["月份"], r["行政區"], "完全重複", "整列重複", "刪除（保留第一筆）", "與先前列完全相同"))
    seen.add(key)
    if r["行政區"] not in valid_names:
        new = r["行政區"].replace(" ", "").upper()
        log.append((r["CSV列號"], r["月份"], r["行政區"], "行政區寫法不一", r["行政區"], f"改為 {new}", "統一為「X區」格式"))
    if "/" in r["月份"]:
        y, m = r["月份"].split("/")
        log.append((r["CSV列號"], r["月份"], r["行政區"], "月份格式不一", r["月份"], f"改為 {y}-{int(m):02d}", "統一為 YYYY-MM"))
    if pd.isna(r["篩檢人數"]):
        log.append((r["CSV列號"], r["月份"], r["行政區"], "缺值", "（空白）", "不補值；排除，不放入分析用資料", "篩檢人數缺值，無法計算陽性率"))
    elif int(r["陽性數"]) > int(r["篩檢人數"]):
        log.append((r["CSV列號"], r["月份"], r["行政區"], "待查", f"陽性 {r['陽性數']} > 篩檢 {r['篩檢人數']}",
                    "不修改；標記待查並排除", "陽性數不可能大於篩檢人數，應回頭問承辦人"))
log_df = pd.DataFrame(log, columns=["CSV列號", "月份", "行政區", "問題類型", "原值", "處理方式", "原因"])
print("體檢結果（各類問題筆數）：")
print(log_df["問題類型"].value_counts().to_string())

# ---------- 清理：依規則 1–5 ----------
df = raw[cols].copy()
df["行政區"] = df["行政區"].str.replace(" ", "", regex=False).str.upper()
df["月份"] = df["月份"].str.replace("/", "-", regex=False).str.replace(r"-(\d)$", r"-0\1", regex=True)
df = df.drop_duplicates()
print(f"去除重複後：{len(df)} 列")
for c in ["人口數", "篩檢人數", "陽性數", "疫苗接種人數"]:
    df[c] = pd.to_numeric(df[c])
keep = df["篩檢人數"].notna() & (df["陽性數"] <= df["篩檢人數"])
ana = df[keep].copy()
ana["篩檢人數"] = ana["篩檢人數"].astype(int)
ana = ana.sort_values(["月份", "行政區"]).reset_index(drop=True)
print(f"排除缺值與待查後（分析用資料）：{len(ana)} 列，排除 {int((~keep).sum())} 列")

# 安全檢查：分析用資料不應有重複的「月份×行政區」
assert not ana.duplicated(["月份", "行政區"]).any(), "分析用資料出現重複的月份×行政區，請檢查"

ana.to_csv(CLEAN_FILE, index=False, encoding="utf-8-sig")
log_df.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
print(f"已輸出：{CLEAN_FILE.name}、{LOG_FILE.name}")
