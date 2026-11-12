"""步驟 3：推論性統計（虛構資料）

問題：各區篩檢陽性率的差異，是否超過隨機波動？哪幾區之間有差？考慮月份後結論是否改變？
注意：檢定一律用「人數」（陽性數、陰性數），不能直接拿百分比做檢定。
輸出：
  表4_卡方檢定             8 區 × 陽性/陰性 的卡方獨立性檢定（含最小期望次數）
  表5_兩兩比較_Holm校正     28 對 2×2 卡方檢定，附差異的 95% 信賴區間（Wald 法），Holm 法校正
  表6_敏感度分析_考慮月份   二項式邏輯斯迴歸（行政區＋月份）；需要 statsmodels
  表7_兩兩比較_考慮月份     用上述模型重做 28 對比較（勝算比），Holm 法校正
執行方式（在成果包最上層資料夾）：python 03_程式碼/03_inferential.py
"""
import itertools
import math
from pathlib import Path
import pandas as pd
from scipy import stats

# ===== 輸入與輸出：看程式碼時先檢查這裡 =====
ROOT = Path(__file__).resolve().parents[1]
CLEAN_FILE = ROOT / "02_清理後資料" / "分析用資料.csv"   # 【輸入】分析用資料（只讀）
TABLE_DIR = ROOT / "04_結果表格"                         # 【輸出】表4–表7
TABLE_DIR.mkdir(exist_ok=True)


def holm(pvals):
    """Holm 法（逐步 Bonferroni）：p 值由小到大，第 k 個乘以 (m-k+1)，並保持單調。"""
    m = len(pvals); order = sorted(range(m), key=lambda i: pvals[i])
    adj, running = [0.0] * m, 0.0
    for k, i in enumerate(order):
        running = max(running, min(1.0, (m - k) * pvals[i]))
        adj[i] = running
    return adj


df = pd.read_csv(CLEAN_FILE)                             # 【讀取】分析用資料
df["陰性數"] = df["篩檢人數"] - df["陽性數"]
g = df.groupby("行政區")[["陽性數", "陰性數"]].sum()

# ---------- 表4：卡方獨立性檢定（8×2） ----------
chi2, p, dof, expected = stats.chi2_contingency(g.values, correction=False)
t4 = pd.DataFrame([{"檢定": "卡方獨立性檢定（行政區 × 陽性/陰性）", "卡方值": round(chi2, 2), "自由度": dof,
                    "p值": f"{p:.2e}", "最小期望次數": round(expected.min(), 1),
                    "假設檢查": "所有期望次數 ≥ 5" if expected.min() >= 5 else "有期望次數 < 5，需改用其他方法"}])
t4.to_csv(TABLE_DIR / "表4_卡方檢定.csv", index=False, encoding="utf-8-sig")       # 【寫出】
print(t4.T.to_string(header=False))

# ---------- 表5：兩兩比較 + 差異 95% CI + Holm 校正 ----------
rows = []
for a, b in itertools.combinations(g.index, 2):
    _, pp, _, _ = stats.chi2_contingency(g.loc[[a, b]].values, correction=False)
    na, nb = g.loc[a].sum(), g.loc[b].sum()
    pa, pb = g.loc[a, "陽性數"] / na, g.loc[b, "陽性數"] / nb
    se = math.sqrt(pa * (1 - pa) / na + pb * (1 - pb) / nb)
    rows.append({"區A": a, "區B": b, "區A陽性率(%)": round(pa * 100, 2), "區B陽性率(%)": round(pb * 100, 2),
                 "差(百分點)": round((pa - pb) * 100, 2),
                 "差的95%CI下限": round((pa - pb - 1.96 * se) * 100, 2), "差的95%CI上限": round((pa - pb + 1.96 * se) * 100, 2),
                 "未校正p值": pp})
t5 = pd.DataFrame(rows)
t5["Holm校正後p值"] = holm(t5["未校正p值"].tolist())
t5["校正後是否顯著(α=0.05)"] = t5["Holm校正後p值"].lt(0.05).map({True: "是", False: "否"})
for c in ["未校正p值", "Holm校正後p值"]:
    t5[c] = t5[c].map(lambda v: f"{v:.4f}")
t5.to_csv(TABLE_DIR / "表5_兩兩比較_Holm校正.csv", index=False, encoding="utf-8-sig")  # 【寫出】
print(f"兩兩比較：共 {len(t5)} 對，校正後顯著 {(t5['校正後是否顯著(α=0.05)'] == '是').sum()} 對")

# ---------- 表6、表7：敏感度分析（考慮月份） ----------
try:
    import numpy as np
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
except ImportError:
    print("沒有安裝 statsmodels，略過表6、表7（敏感度分析）。")
else:
    d = df.rename(columns={"陽性數": "pos", "陰性數": "neg", "行政區": "district", "月份": "month"})
    full = smf.glm("pos + neg ~ C(district) + C(month)", data=d, family=sm.families.Binomial()).fit()
    phi = full.pearson_chi2 / full.df_resid      # 離散參數：約 1 符合二項分布；>1 變異比預期大；明顯 <1 也值得追問
    no_d = smf.glm("pos + neg ~ C(month)", data=d, family=sm.families.Binomial()).fit()
    no_m = smf.glm("pos + neg ~ C(district)", data=d, family=sm.families.Binomial()).fit()
    out = []
    for label, reduced in [("行政區（已考慮月份）", no_d), ("月份（已考慮行政區）", no_m)]:
        ddev = reduced.deviance - full.deviance
        ddf = int(round(reduced.df_resid - full.df_resid))
        if phi > 1:      # 變異比二項分布大：用 quasi-F，放大不確定性
            stat, pv, method = ddev / ddf / phi, stats.f.sf(ddev / ddf / phi, ddf, full.df_resid), "quasi-F 檢定（φ>1）"
        else:            # φ ≤ 1：不縮小不確定性，離散參數視為 1，用概似比卡方檢定
            stat, pv, method = ddev, stats.chi2.sf(ddev, ddf), "概似比卡方檢定（φ≤1，離散參數視為 1）"
        out.append({"效果": label, "檢定方法": method, "統計量": round(stat, 2), "自由度": ddf, "p值": f"{pv:.2e}"})
    t6 = pd.DataFrame(out)
    t6["模型離散參數φ"] = round(phi, 2)
    t6["只看行政區時的φ"] = round(no_m.pearson_chi2 / no_m.df_resid, 2)
    t6.to_csv(TABLE_DIR / "表6_敏感度分析_考慮月份.csv", index=False, encoding="utf-8-sig")  # 【寫出】
    print(t6.to_string(index=False))

    # 表7：考慮月份後的兩兩比較（同一模型內，用行政區係數的差做 Wald 檢定）
    params, cov = full.params, full.cov_params() * max(phi, 1.0)
    names = sorted(d["district"].unique())
    def coef_vec(name):
        v = pd.Series(0.0, index=params.index)
        key = f"C(district)[T.{name}]"
        if key in v.index:
            v[key] = 1.0
        return v
    rows = []
    for a, b in itertools.combinations(names, 2):
        c = coef_vec(a) - coef_vec(b)
        est = float(c @ params); se = math.sqrt(float(c @ cov @ c))
        z = est / se; pv = 2 * stats.norm.sf(abs(z))
        rows.append({"區A": a, "區B": b, "校正月份後勝算比": round(math.exp(est), 3),
                     "95%CI下限": round(math.exp(est - 1.96 * se), 3), "95%CI上限": round(math.exp(est + 1.96 * se), 3),
                     "未校正p值": pv})
    t7 = pd.DataFrame(rows)
    t7["Holm校正後p值"] = holm(t7["未校正p值"].tolist())
    t7["校正後是否顯著(α=0.05)"] = t7["Holm校正後p值"].lt(0.05).map({True: "是", False: "否"})
    for c in ["未校正p值", "Holm校正後p值"]:
        t7[c] = t7[c].map(lambda v: f"{v:.4f}")
    t7.to_csv(TABLE_DIR / "表7_兩兩比較_考慮月份.csv", index=False, encoding="utf-8-sig")  # 【寫出】
    print(f"考慮月份後的兩兩比較：共 {len(t7)} 對，校正後顯著 {(t7['校正後是否顯著(α=0.05)'] == '是').sum()} 對")
print("已輸出表4–表7")
