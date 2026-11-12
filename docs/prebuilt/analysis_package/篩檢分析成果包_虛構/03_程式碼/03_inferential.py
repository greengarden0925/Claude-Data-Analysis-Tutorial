"""步驟 3：推論性統計（虛構資料）

問題：各區篩檢陽性率的差異，是否超過隨機波動？哪幾區之間有差？考慮月份後結論是否改變？
輸入：02_清理後資料/分析用資料.csv
輸出：
  04_結果表格/表4_卡方檢定.csv              8 區 × 陽性/陰性 的卡方獨立性檢定
  04_結果表格/表5_兩兩比較_Holm校正.csv      28 對兩兩比較，Holm 法校正多重比較
  04_結果表格/表6_敏感度分析_考慮月份.csv    二項式邏輯斯迴歸（行政區＋月份），需要 statsmodels

注意：檢定一律用「人數」（陽性數、陰性數），不能直接拿百分比做檢定。
執行方式（在成果包最上層資料夾）：python 03_程式碼/03_inferential.py
"""
import itertools
import pandas as pd
from scipy import stats
from _common import CLEAN_FILE, TABLE_DIR

df = pd.read_csv(CLEAN_FILE)
df["陰性數"] = df["篩檢人數"] - df["陽性數"]
g = df.groupby("行政區")[["陽性數", "陰性數"]].sum()

# ---------- 表4：卡方獨立性檢定（8×2） ----------
chi2, p, dof, expected = stats.chi2_contingency(g.values, correction=False)
t4 = pd.DataFrame([{"檢定": "卡方獨立性檢定（行政區 × 陽性/陰性）", "卡方值": round(chi2, 2), "自由度": dof,
                    "p值": f"{p:.2e}", "最小期望次數": round(expected.min(), 1),
                    "假設檢查": "所有期望次數 ≥ 5" if expected.min() >= 5 else "有期望次數 < 5，需改用其他方法"}])
t4.to_csv(TABLE_DIR / "表4_卡方檢定.csv", index=False, encoding="utf-8-sig")
print(t4.T.to_string(header=False))

# ---------- 表5：兩兩比較 + Holm 校正 ----------
rows = []
for a, b in itertools.combinations(g.index, 2):
    sub = g.loc[[a, b]].values
    _, pp, _, _ = stats.chi2_contingency(sub, correction=False)
    ra = g.loc[a, "陽性數"] / g.loc[a].sum() * 100
    rb = g.loc[b, "陽性數"] / g.loc[b].sum() * 100
    rows.append({"區A": a, "區B": b, "區A陽性率(%)": round(ra, 2), "區B陽性率(%)": round(rb, 2),
                 "差(百分點)": round(ra - rb, 2), "未校正p值": pp})
t5 = pd.DataFrame(rows)
# Holm 法（逐步 Bonferroni）：p 值由小到大，第 k 個乘以 (m-k+1)，並保持單調
m = len(t5); order = t5["未校正p值"].sort_values().index
adj, running = pd.Series(index=t5.index, dtype=float), 0.0
for k, idx in enumerate(order):
    running = max(running, min(1.0, (m - k) * t5.loc[idx, "未校正p值"]))
    adj[idx] = running
t5["Holm校正後p值"] = adj
t5["校正後是否顯著(α=0.05)"] = t5["Holm校正後p值"].lt(0.05).map({True: "是", False: "否"})
t5["未校正p值"] = t5["未校正p值"].map(lambda v: f"{v:.4f}")
t5["Holm校正後p值"] = t5["Holm校正後p值"].map(lambda v: f"{v:.4f}")
t5.to_csv(TABLE_DIR / "表5_兩兩比較_Holm校正.csv", index=False, encoding="utf-8-sig")
print(f"兩兩比較：共 {m} 對，校正後顯著 {(t5['校正後是否顯著(α=0.05)'] == '是').sum()} 對")

# ---------- 表6：敏感度分析（考慮月份） ----------
try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
except ImportError:
    print("沒有安裝 statsmodels，略過表6（敏感度分析）。")
else:
    d = df.rename(columns={"陽性數": "pos", "陰性數": "neg", "行政區": "district", "月份": "month"})
    full = smf.glm("pos + neg ~ C(district) + C(month)", data=d, family=sm.families.Binomial()).fit()
    phi = full.pearson_chi2 / full.df_resid                       # 離散參數：約 1 表示符合二項分布
    no_d = smf.glm("pos + neg ~ C(month)", data=d, family=sm.families.Binomial()).fit()
    no_m = smf.glm("pos + neg ~ C(district)", data=d, family=sm.families.Binomial()).fit()
    out = []
    for label, reduced in [("行政區（已考慮月份）", no_d), ("月份（已考慮行政區）", no_m)]:
        ddev = reduced.deviance - full.deviance
        ddf = int(round(reduced.df_resid - full.df_resid))
        f = ddev / ddf / max(phi, 1.0)                            # 離散參數 > 1 時才放大不確定性
        pf = stats.f.sf(f, ddf, full.df_resid)
        out.append({"效果": label, "偏差差異": round(ddev, 1), "自由度": ddf, "F值": round(f, 2), "p值": f"{pf:.2e}"})
    t6 = pd.DataFrame(out)
    t6["模型離散參數φ"] = round(phi, 2)
    t6["只看行政區時的φ"] = round(no_m.pearson_chi2 / no_m.df_resid, 2)
    t6.to_csv(TABLE_DIR / "表6_敏感度分析_考慮月份.csv", index=False, encoding="utf-8-sig")
    print(t6.to_string(index=False))
print("已輸出表4–表6")
