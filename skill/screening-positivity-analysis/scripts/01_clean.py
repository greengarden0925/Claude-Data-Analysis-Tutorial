"""步驟 1：資料體檢與清理

輸入：01_原始資料/ 裡唯一的 CSV 檔（不會被修改）
輸出：02_清理後資料/分析用資料.csv、02_清理後資料/修正與排除紀錄.csv

必要欄位：月份、行政區、人口數、篩檢人數、陽性數（其他欄位保留，不分析）
清理規則（預設；使用者要不同規則時修改這支程式）：
  1. 完全重複的列只保留一筆
  2. 行政區統一寫法：全形轉半形、刪除中文字旁的空白、其他空白縮成一個、英文字母大寫
  3. 月份統一為 YYYY-MM（可辨識 2025-3、2025/03、2025.3、114/03 民國年）；無法辨識就停止並列出列號
  4. 篩檢人數缺值、為 0、或數值無法辨識：不補值，排除
  5. 陽性數 > 篩檢人數、或出現負數：不修改，標記「待查」，排除
執行方式（在成果包最上層資料夾）：python 03_程式碼/01_clean.py
"""
import re
import sys
import unicodedata
from pathlib import Path
import pandas as pd

# ===== 輸入與輸出：看程式碼時先檢查這裡 =====
ROOT = Path(__file__).resolve().parents[1]                              # 成果包最上層資料夾
_raw = sorted((ROOT / "01_原始資料").glob("*.csv"))
if len(_raw) != 1:
    sys.exit(f"【停止】01_原始資料 裡應該剛好有 1 個 CSV 檔，目前有 {len(_raw)} 個。")
RAW_FILE = _raw[0]                                                       # 【輸入】原始資料（只讀，不修改）
CLEAN_FILE = ROOT / "02_清理後資料" / "分析用資料.csv"                     # 【寫出】分析用資料
LOG_FILE = ROOT / "02_清理後資料" / "修正與排除紀錄.csv"                   # 【寫出】修正與排除紀錄
CLEAN_FILE.parent.mkdir(exist_ok=True)

REQUIRED = ["月份", "行政區", "人口數", "篩檢人數", "陽性數"]
NUM = ["人口數", "篩檢人數", "陽性數"]


def norm_text(s):
    return unicodedata.normalize("NFKC", str(s)).strip()


def norm_district(s):
    """全形轉半形、中文字旁的空白刪掉、其他連續空白縮成一個、英文字母大寫。"""
    t = re.sub(r"\s+", " ", norm_text(s))
    t = re.sub(r"(?<=[\u3400-\u9fff]) | (?=[\u3400-\u9fff])", "", t)
    return t.upper()


def parse_month(s):
    """回傳 YYYY-MM；無法辨識回傳 None。年份 < 1911 視為民國年（加 1911）。"""
    m = re.match(r"^(\d{2,4})\s*[-/.年]\s*(\d{1,2})\s*月?$", norm_text(s))
    if not m:
        return None
    y, mm = int(m.group(1)), int(m.group(2))
    if y < 1911:
        y += 1911
    if not 1 <= mm <= 12 or not 1950 <= y <= 2100:
        return None
    return f"{y}-{mm:02d}"


raw = pd.read_csv(RAW_FILE, dtype=str, keep_default_na=False)          # 【讀取】原始資料
raw.columns = [norm_text(c) for c in raw.columns]
missing_cols = [c for c in REQUIRED if c not in raw.columns]
if missing_cols:
    sys.exit("【停止】缺少必要欄位：" + "、".join(missing_cols) + "。目前的欄位是：" + "、".join(raw.columns)
             + "。請確認欄位對應後改名再執行。")
extra = [c for c in raw.columns if c not in REQUIRED]
raw["CSV列號"] = raw.index + 2                                           # 標題列是第 1 列
print(f"讀取：{RAW_FILE.name}，原始列數：{len(raw)}")
if extra:
    print("其他欄位（保留，不分析）：" + "、".join(extra))

# ---------- 體檢：只檢查、不修改原始資料 ----------
log = []
df = raw.copy()
bad_month = []
for i, r in raw.iterrows():
    nd = norm_district(r["行政區"])
    if nd != r["行政區"]:
        log.append((r["CSV列號"], r["月份"], r["行政區"], "行政區寫法不一", r["行政區"], f"改為 {nd}", "統一寫法（全形轉半形、去空白、大寫）"))
    df.at[i, "行政區"] = nd
    pm = parse_month(r["月份"])
    if pm is None:
        bad_month.append(int(r["CSV列號"]))
    elif pm != r["月份"]:
        reason = "民國年轉西元、統一為 YYYY-MM" if int(re.match(r"\D*(\d+)", norm_text(r["月份"])).group(1)) < 1911 else "統一為 YYYY-MM"
        log.append((r["CSV列號"], r["月份"], r["行政區"], "月份格式不一", r["月份"], f"改為 {pm}", reason))
    df.at[i, "月份"] = pm
if bad_month:
    sys.exit("【停止】這些列的月份無法辨識（CSV 列號）：" + "、".join(map(str, bad_month[:30]))
             + "。請確認月份寫法（例如 2025-03 或 114/03）。")

for c in NUM:
    df[c + "_數值"] = pd.to_numeric(df[c].map(lambda v: norm_text(v).replace(",", "")), errors="coerce")

# 完全重複（統一寫法之後仍完全相同的列）
key_cols = REQUIRED + extra
dup_mask = df.duplicated(subset=key_cols, keep="first")
for _, r in df[dup_mask].iterrows():
    log.append((r["CSV列號"], r["月份"], r["行政區"], "完全重複", "整列重複", "刪除（保留第一筆）", "與先前列完全相同"))
df = df[~dup_mask].copy()
print(f"去除重複後：{len(df)} 列")

exclude = pd.Series(False, index=df.index)
for i, r in df.iterrows():
    s, p, pop = r["篩檢人數_數值"], r["陽性數_數值"], r["人口數_數值"]
    if r["篩檢人數"].strip() == "":
        log.append((r["CSV列號"], r["月份"], r["行政區"], "缺值", "（空白）", "不補值；排除，不放入分析用資料", "篩檢人數缺值，無法計算陽性率"))
        exclude[i] = True
    elif pd.isna(s) or pd.isna(p) or pd.isna(pop):
        log.append((r["CSV列號"], r["月份"], r["行政區"], "數值無法辨識", f"篩檢 {r['篩檢人數']}／陽性 {r['陽性數']}／人口 {r['人口數']}",
                    "不修改；排除", "數值欄位不是數字，應回頭問承辦人"))
        exclude[i] = True
    elif s == 0:
        log.append((r["CSV列號"], r["月份"], r["行政區"], "篩檢人數為 0", "0", "排除，不放入分析用資料", "沒有受檢者，無法計算陽性率"))
        exclude[i] = True
    elif p > s or p < 0 or s < 0:
        log.append((r["CSV列號"], r["月份"], r["行政區"], "待查", f"陽性 {r['陽性數']} > 篩檢 {r['篩檢人數']}" if p > s else "出現負數",
                    "不修改；標記待查並排除", "數值不合理，應回頭問承辦人"))
        exclude[i] = True

log_df = pd.DataFrame(log, columns=["CSV列號", "月份", "行政區", "問題類型", "原值", "處理方式", "原因"]).sort_values("CSV列號", kind="stable")
print("體檢結果（各類問題筆數）：")
print(log_df["問題類型"].value_counts().to_string() if len(log_df) else "  沒有發現問題")

ana = df[~exclude].copy()
for c in NUM:
    ana[c] = ana[c + "_數值"].astype(int)
ana = ana[REQUIRED + extra].sort_values(["月份", "行政區"]).reset_index(drop=True)
print(f"排除後（分析用資料）：{len(ana)} 列，排除 {int(exclude.sum())} 列")
print("清理後的行政區（請確認沒有同一區被拆成兩個名稱）：" + "、".join(sorted(ana["行政區"].unique())))

# 安全檢查：同一個「月份 × 行政區」只能有一列
dupkey = ana.duplicated(["月份", "行政區"], keep=False)
if dupkey.any():
    k = df[~exclude][df[~exclude].duplicated(["月份", "行政區"], keep=False)]
    merged = {n: sorted(set(raw.loc[raw["CSV列號"].isin(k[k["行政區"] == n]["CSV列號"]), "行政區"])) for n in k["行政區"].unique()}
    sys.exit("【停止】同一個月份 × 行政區出現多列，可能是不同寫法其實是不同的區，或原始資料重複登錄。\n"
             + "\n".join(f"  {n}：由這些原始寫法合併而來 → " + "、".join(repr(x) for x in v) for n, v in merged.items())
             + "\n請確認後修改原始資料或清理規則。相關 CSV 列號：" + "、".join(map(str, k["CSV列號"].tolist()[:30])))
if ana.empty or ana["行政區"].nunique() < 2:
    sys.exit("【停止】分析用資料少於 2 個行政區，無法比較各區。")

ana.to_csv(CLEAN_FILE, index=False, encoding="utf-8-sig")       # 【寫出】分析用資料（不是原始檔）
log_df.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")      # 【寫出】修正與排除紀錄
print(f"已輸出：{CLEAN_FILE.name}、{LOG_FILE.name}")
