"""步驟 2：描述性統計（虛構資料）

輸入：02_清理後資料/分析用資料.csv
輸出：
  04_結果表格/表1_各區描述統計.csv
  04_結果表格/表2_全市每月描述統計.csv
  04_結果表格/表3_各區每月篩檢陽性率.csv
  05_圖表/圖1_各區篩檢陽性率.png
  05_圖表/圖2_全市每月篩檢陽性率.png

篩檢陽性率 = 陽性數 ÷ 篩檢人數 × 100%（用人數加總後再相除，不是把百分比平均）
95% 信賴區間：Wilson 法
執行方式（在成果包最上層資料夾）：python 03_程式碼/02_descriptive.py
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from _common import CLEAN_FILE, TABLE_DIR, FIG_DIR, wilson, use_chinese_font

df = pd.read_csv(CLEAN_FILE)
months = [f"2025-{m:02d}" for m in range(1, 13)]

# ---------- 表1：各區 ----------
rows = []
for name, g in df.groupby("行政區"):
    s, p = int(g["篩檢人數"].sum()), int(g["陽性數"].sum())
    lo, hi = wilson(p, s)
    missing = [f"{int(m[5:])}月" for m in months if m not in set(g["月份"])]
    rows.append({"行政區": name, "納入月數": g["月份"].nunique(), "缺的月份": "、".join(missing) or "無",
                 "篩檢人數": s, "陽性數": p, "篩檢陽性率(%)": round(p / s * 100, 2),
                 "95%CI下限(%)": round(lo, 2), "95%CI上限(%)": round(hi, 2)})
t1 = pd.DataFrame(rows)
total_s, total_p = int(df["篩檢人數"].sum()), int(df["陽性數"].sum())
lo, hi = wilson(total_p, total_s)
t1.loc[len(t1)] = {"行政區": "合計", "納入月數": df["月份"].nunique(), "缺的月份": "—", "篩檢人數": total_s,
                   "陽性數": total_p, "篩檢陽性率(%)": round(total_p / total_s * 100, 2),
                   "95%CI下限(%)": round(lo, 2), "95%CI上限(%)": round(hi, 2)}
t1.to_csv(TABLE_DIR / "表1_各區描述統計.csv", index=False, encoding="utf-8-sig")

# ---------- 表2：全市每月 ----------
t2 = df.groupby("月份").agg(納入區數=("行政區", "nunique"), 篩檢人數=("篩檢人數", "sum"), 陽性數=("陽性數", "sum")).reset_index()
t2["篩檢陽性率(%)"] = (t2["陽性數"] / t2["篩檢人數"] * 100).round(2)
t2.to_csv(TABLE_DIR / "表2_全市每月描述統計.csv", index=False, encoding="utf-8-sig")

# ---------- 表3：各區每月（空白＝該月被排除） ----------
t3 = df.assign(率=(df["陽性數"] / df["篩檢人數"] * 100).round(2)).pivot(index="行政區", columns="月份", values="率")
t3.reindex(columns=months).to_csv(TABLE_DIR / "表3_各區每月篩檢陽性率.csv", encoding="utf-8-sig")

print(t1.to_string(index=False))

# ---------- 圖1、圖2 ----------
use_chinese_font()
d = t1[t1["行政區"] != "合計"]
fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
ax.bar(d["行政區"], d["篩檢陽性率(%)"], color="#0f766e")
ax.errorbar(d["行政區"], d["篩檢陽性率(%)"],
            yerr=[d["篩檢陽性率(%)"] - d["95%CI下限(%)"], d["95%CI上限(%)"] - d["篩檢陽性率(%)"]],
            fmt="none", ecolor="#1c2430", capsize=4)
ax.set_title("各區篩檢陽性率（虛構資料，2025 年）")
ax.set_xlabel("行政區（依代碼排序）"); ax.set_ylabel("篩檢陽性率（%）"); ax.set_ylim(0, 12)
ax.spines[["top", "right"]].set_visible(False)
fig.text(0.01, 0.01, "誤差線為 95% 信賴區間（Wilson 法）。顏色不代表風險等級。", fontsize=7, color="#5b6675")
fig.tight_layout(rect=(0, .04, 1, 1)); fig.savefig(FIG_DIR / "圖1_各區篩檢陽性率.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 3.6), dpi=150)
ax.plot([int(m[5:]) for m in t2["月份"]], t2["篩檢陽性率(%)"], marker="o", color="#0f766e")
ax.set_xticks(range(1, 13)); ax.set_ylim(0, 10)
ax.set_title("全市每月篩檢陽性率（虛構資料，2025 年）")
ax.set_xlabel("月份"); ax.set_ylabel("篩檢陽性率（%）")
ax.spines[["top", "right"]].set_visible(False)
fig.text(0.01, 0.01, "各月納入的區數不同（7–8 區）；只描述，不推論原因。", fontsize=7, color="#5b6675")
fig.tight_layout(rect=(0, .05, 1, 1)); fig.savefig(FIG_DIR / "圖2_全市每月篩檢陽性率.png"); plt.close(fig)
print("已輸出表1–表3、圖1–圖2")
