"""步驟 2：描述性統計

篩檢陽性率 = 陽性數合計 ÷ 篩檢人數合計 × 100%（先加總人數再相除，不是把百分比平均）
95% 信賴區間：Wilson 法（陽性數為 0 時也能計算）
年化粗篩檢率 = 篩檢人數合計 ÷ 納入月數 × 12 ÷ 區人口數 × 100%
  注意：人口數是區總人口，不可跨月加總；各月不同時取最新月份的人口數。分母不是符合篩檢資格的人口，
  也無法排除同一人重複受檢，只能參考。
執行方式（在成果包最上層資料夾）：python 03_程式碼/02_descriptive.py
"""
import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from _common import wilson, use_chinese_font

# ===== 輸入與輸出：看程式碼時先檢查這裡 =====
ROOT = Path(__file__).resolve().parents[1]
CLEAN_FILE = ROOT / "02_清理後資料" / "分析用資料.csv"   # 【輸入】分析用資料（只讀）
CONFIG = ROOT / "00_分析計畫" / "報告設定.json"          # 【輸入】（選用）是否標示虛構資料
TABLE_DIR = ROOT / "04_結果表格"                         # 【寫出】表1–表3
FIG_DIR = ROOT / "05_圖表"                               # 【寫出】圖1–圖2
TABLE_DIR.mkdir(exist_ok=True); FIG_DIR.mkdir(exist_ok=True)

df = pd.read_csv(CLEAN_FILE)                             # 【讀取】分析用資料
all_months = list(pd.period_range(df["月份"].min(), df["月份"].max(), freq="M").strftime("%Y-%m"))
months = sorted(df["月份"].unique())                      # 至少有一區有資料的月份
empty_months = [m for m in all_months if m not in months]
period = f"{all_months[0]} 至 {all_months[-1]}"
fake = json.loads(CONFIG.read_text(encoding="utf-8")).get("虛構資料", False) if CONFIG.exists() else False
tag = f"（{'虛構資料，' if fake else ''}{period}）"
if empty_months:
    print("提醒：這些月份所有區都沒有資料：" + "、".join(empty_months))

pop_varies = [n for n, g in df.groupby("行政區") if g["人口數"].nunique() > 1]
if pop_varies:
    print("提醒：這些區的人口數各月不同，年化粗篩檢率使用最新月份的人口數：" + "、".join(pop_varies))

# ---------- 表1：各區 ----------
rows = []
for name, g in df.groupby("行政區"):
    g = g.sort_values("月份")
    s, p, pop, n_m = int(g["篩檢人數"].sum()), int(g["陽性數"].sum()), int(g["人口數"].iloc[-1]), g["月份"].nunique()
    lo, hi = wilson(p, s)
    missing = [m for m in months if m not in set(g["月份"])]
    rows.append({"行政區": name, "納入月數": n_m, "缺的月份": "、".join(missing) or "無",
                 "人口數": pop, "篩檢人數": s, "年化粗篩檢率(%)": round(s / n_m * 12 / pop * 100, 1) if pop > 0 else None,
                 "陽性數": p, "篩檢陽性率(%)": round(p / s * 100, 2), "95%CI下限(%)": round(lo, 2), "95%CI上限(%)": round(hi, 2)})
t1 = pd.DataFrame(rows)
total_s, total_p = int(df["篩檢人數"].sum()), int(df["陽性數"].sum())
lo, hi = wilson(total_p, total_s)
t1.loc[len(t1)] = {"行政區": "合計", "納入月數": len(months), "缺的月份": "—", "人口數": int(t1["人口數"].sum()),
                   "篩檢人數": total_s, "年化粗篩檢率(%)": None, "陽性數": total_p,
                   "篩檢陽性率(%)": round(total_p / total_s * 100, 2), "95%CI下限(%)": round(lo, 2), "95%CI上限(%)": round(hi, 2)}
t1.to_csv(TABLE_DIR / "表1_各區描述統計.csv", index=False, encoding="utf-8-sig")      # 【寫出】

# ---------- 表2：全縣每月 ----------
t2 = df.groupby("月份").agg(納入區數=("行政區", "nunique"), 篩檢人數=("篩檢人數", "sum"), 陽性數=("陽性數", "sum")).reset_index()
t2["篩檢陽性率(%)"] = (t2["陽性數"] / t2["篩檢人數"] * 100).round(2)
t2.to_csv(TABLE_DIR / "表2_全縣每月描述統計.csv", index=False, encoding="utf-8-sig")  # 【寫出】

# ---------- 表3：各區每月（空白＝該月被排除或沒有資料） ----------
t3 = df.assign(率=(df["陽性數"] / df["篩檢人數"] * 100).round(2)).pivot(index="行政區", columns="月份", values="率")
t3.reindex(columns=all_months).to_csv(TABLE_DIR / "表3_各區每月篩檢陽性率.csv", encoding="utf-8-sig")  # 【寫出】

hi_cov = t1[(t1["年化粗篩檢率(%)"].notna()) & (t1["年化粗篩檢率(%)"] > 100)]["行政區"].tolist()
if hi_cov:
    print("提醒：這些區的年化粗篩檢率超過 100%（篩檢人數大於區人口數），請確認人口數或篩檢人數是否登錄錯誤：" + "、".join(hi_cov))
print(t1.to_string(index=False))

# ---------- 圖1、圖2 ----------
use_chinese_font()
d = t1[t1["行政區"] != "合計"]
fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
ax.bar(d["行政區"], d["篩檢陽性率(%)"], color="#0f766e")
ax.errorbar(d["行政區"], d["篩檢陽性率(%)"],
            yerr=[d["篩檢陽性率(%)"] - d["95%CI下限(%)"], d["95%CI上限(%)"] - d["篩檢陽性率(%)"]],
            fmt="none", ecolor="#1c2430", capsize=4)
ax.set_title("各區篩檢陽性率" + tag)
ax.set_xlabel("行政區（依名稱排序）"); ax.set_ylabel("篩檢陽性率（%）")
ax.set_ylim(0, max(1, float(d["95%CI上限(%)"].max()) * 1.15))
ax.spines[["top", "right"]].set_visible(False)
fig.text(0.01, 0.01, "誤差線為 95% 信賴區間（Wilson 法）。顏色不代表風險等級。", fontsize=7, color="#5b6675")
fig.tight_layout(rect=(0, .04, 1, 1)); fig.savefig(FIG_DIR / "圖1_各區篩檢陽性率.png"); plt.close(fig)  # 【寫出】

fig, ax = plt.subplots(figsize=(7, 3.6), dpi=150)
t2f = t2.set_index("月份").reindex(all_months)          # 整月沒有資料時留空，折線不連過去
ax.plot(range(len(t2f)), t2f["篩檢陽性率(%)"], marker="o", color="#0f766e")
ax.set_xticks(range(len(t2f))); ax.set_xticklabels([m[2:] for m in t2f.index], rotation=45, fontsize=8)
ax.set_ylim(0, max(1, float(t2["篩檢陽性率(%)"].max()) * 1.3))
ax.set_title("全縣每月篩檢陽性率" + tag)
ax.set_xlabel("月份"); ax.set_ylabel("篩檢陽性率（%）")
ax.spines[["top", "right"]].set_visible(False)
fig.text(0.01, 0.01, (f"各月納入 {t2['納入區數'].min()} 區" if t2['納入區數'].min() == t2['納入區數'].max() else f"各月納入的區數為 {t2['納入區數'].min()}–{t2['納入區數'].max()} 區") + "；只描述，不推論原因。", fontsize=7, color="#5b6675")
fig.tight_layout(rect=(0, .05, 1, 1)); fig.savefig(FIG_DIR / "圖2_全縣每月篩檢陽性率.png"); plt.close(fig)  # 【寫出】
print("已輸出表1–表3、圖1–圖2")
