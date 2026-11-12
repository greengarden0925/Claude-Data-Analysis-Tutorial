"""步驟 3：推論性統計

問題：各區篩檢陽性率的差異，是否超過隨機波動？哪幾區之間有差？考慮月份後結論是否改變？
注意：檢定一律用「人數」（陽性數、陰性數），不能直接拿百分比做檢定。
輸出：
  表4_卡方檢定             各區 × 陽性/陰性 的卡方獨立性檢定；最小期望次數 < 5 時另附蒙地卡羅模擬 p 值
  表5_兩兩比較_Holm校正     兩兩比較（期望次數皆 ≥ 5 用卡方，否則用 Fisher 精確檢定），差異 95% CI（Newcombe 法），Holm 校正
  表6_敏感度分析_考慮月份   二項式邏輯斯迴歸（行政區＋月份）；φ ≤ 1 用概似比卡方，φ > 1 用 quasi-F；需要 statsmodels
  表7_兩兩比較_考慮月份     用上述模型重做兩兩比較（勝算比；φ>1 用 t 分配，否則用常態），Holm 校正
有區的陽性數為 0、或模型無法估計時，表6、表7 會略過並說明原因。
執行方式（在成果包最上層資料夾）：python 03_程式碼/03_inferential.py
"""
import itertools
import math
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from _common import newcombe_diff

warnings.filterwarnings("ignore")   # 模型完全分離等情況的英文警告，改由程式用中文說明

# ===== 輸入與輸出：看程式碼時先檢查這裡 =====
ROOT = Path(__file__).resolve().parents[1]
CLEAN_FILE = ROOT / "02_清理後資料" / "分析用資料.csv"   # 【輸入】分析用資料（只讀）
TABLE_DIR = ROOT / "04_結果表格"                         # 【寫出】表4–表7
TABLE_DIR.mkdir(exist_ok=True)
for old in ["表6_敏感度分析_考慮月份.csv", "表7_兩兩比較_考慮月份.csv"]:
    if (TABLE_DIR / old).exists():
        (TABLE_DIR / old).unlink()                       # 先清掉上次的結果，避免這次略過時沿用舊檔


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
if g["陽性數"].sum() == 0 or g["陰性數"].sum() == 0:
    sys.exit("【停止】所有區的陽性數都是 0（或都是陽性），無法做比較檢定。描述性統計仍然有效。")

# ---------- 表4：卡方獨立性檢定 ----------
chi2, p, dof, expected = stats.chi2_contingency(g.values, correction=False)
min_exp = float(expected.min())
row = {"檢定": "卡方獨立性檢定（行政區 × 陽性/陰性）", "卡方值": round(chi2, 2), "自由度": dof, "p值": f"{p:.2e}",
       "最小期望次數": round(min_exp, 1), "假設檢查": "所有期望次數 ≥ 5" if min_exp >= 5 else "有期望次數 < 5：卡方近似不可靠，請看模擬 p 值",
       "模擬p值": ""}
if min_exp < 5:
    rng = np.random.default_rng(2025)
    n_row, n_pos, sims = g.sum(axis=1).values, int(g["陽性數"].sum()), 20000
    exp_pos = n_row * n_pos / n_row.sum()
    def stat(pos):
        e = np.vstack([exp_pos, n_row - exp_pos]).T; o = np.vstack([pos, n_row - pos]).T
        return ((o - e) ** 2 / np.where(e > 0, e, 1)).sum()
    obs = stat(g["陽性數"].values)
    sim = np.array([stat(rng.multivariate_hypergeometric(n_row, n_pos)) for _ in range(sims)])
    row["模擬p值"] = f"{(np.sum(sim >= obs - 1e-9) + 1) / (sims + 1):.4f}"
    row["檢定"] += "（另附蒙地卡羅模擬，固定邊際總數）"
t4 = pd.DataFrame([row])
t4.to_csv(TABLE_DIR / "表4_卡方檢定.csv", index=False, encoding="utf-8-sig")       # 【寫出】
print(t4.T.to_string(header=False))

# ---------- 表5：兩兩比較 ----------
rows = []
for a, b in itertools.combinations(g.index, 2):
    sub = g.loc[[a, b]].values
    na, nb = int(sub[0].sum()), int(sub[1].sum())
    xa, xb = int(sub[0, 0]), int(sub[1, 0])
    col0 = sub[:, 0].sum(); col1 = sub[:, 1].sum()
    if col0 == 0 or col1 == 0:
        pp, method = 1.0, "兩區陽性數皆為 0（或皆為陽性），無差異可檢定"
    else:
        exp2 = stats.contingency.expected_freq(sub)
        if exp2.min() >= 5:
            _, pp, _, _ = stats.chi2_contingency(sub, correction=False); method = "卡方檢定"
        else:
            _, pp = stats.fisher_exact(sub); method = "Fisher 精確檢定（期望次數 < 5）"
    lo, hi = newcombe_diff(xa, na, xb, nb)
    rows.append({"區A": a, "區B": b, "區A陽性率(%)": round(xa / na * 100, 2), "區B陽性率(%)": round(xb / nb * 100, 2),
                 "差(百分點)": round((xa / na - xb / nb) * 100, 2), "差的95%CI下限": round(lo, 2), "差的95%CI上限": round(hi, 2),
                 "檢定方法": method, "未校正p值": pp})
t5 = pd.DataFrame(rows)
t5["Holm校正後p值"] = holm(t5["未校正p值"].tolist())
t5["校正後是否顯著(α=0.05)"] = t5["Holm校正後p值"].lt(0.05).map({True: "是", False: "否"})
for c in ["未校正p值", "Holm校正後p值"]:
    t5[c] = t5[c].map(lambda v: f"{v:.4f}")
t5.to_csv(TABLE_DIR / "表5_兩兩比較_Holm校正.csv", index=False, encoding="utf-8-sig")  # 【寫出】
print(f"兩兩比較：共 {len(t5)} 對，校正後顯著 {(t5['校正後是否顯著(α=0.05)'] == '是').sum()} 對")

# ---------- 表6、表7：敏感度分析（考慮月份） ----------
def skip(reason):
    print("略過表6、表7（敏感度分析）：" + reason)


zero = g.index[(g["陽性數"] == 0) | (g["陰性數"] == 0)].tolist()
try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
except ImportError:
    skip("沒有安裝 statsmodels。")
else:
    if zero:
        skip("這些區的陽性數為 0（或全部陽性），邏輯斯迴歸無法估計：" + "、".join(zero) + "。")
    elif df["月份"].nunique() < 2:
        skip("只有 1 個月份，無法考慮月份差異。")
    else:
        try:
            d = df.rename(columns={"陽性數": "pos", "陰性數": "neg", "行政區": "district", "月份": "month"})
            full = smf.glm("pos + neg ~ C(district) + C(month)", data=d, family=sm.families.Binomial()).fit()
            no_d = smf.glm("pos + neg ~ C(month)", data=d, family=sm.families.Binomial()).fit()
            no_m = smf.glm("pos + neg ~ C(district)", data=d, family=sm.families.Binomial()).fit()
            if full.df_resid <= 0:
                raise ValueError("資料筆數不足（每區每月幾乎只有一列，沒有剩餘自由度）")
            phi = full.pearson_chi2 / full.df_resid   # 離散參數：約 1 符合二項分布；>1 變異比預期大；明顯 <1 也值得追問
        except Exception as e:  # 模型無法收斂或估計
            skip(f"模型無法估計（{type(e).__name__}：{e}）。")
        else:
            out = []
            for label, reduced in [("行政區（已考慮月份）", no_d), ("月份（已考慮行政區）", no_m)]:
                ddev = reduced.deviance - full.deviance
                ddf = int(round(reduced.df_resid - full.df_resid))
                if phi > 1:      # 變異比二項分布大：用 quasi-F，放大不確定性
                    stat_, pv, method = ddev / ddf / phi, stats.f.sf(ddev / ddf / phi, ddf, full.df_resid), "quasi-F 檢定（φ>1）"
                else:            # φ ≤ 1：不縮小不確定性，離散參數視為 1，用概似比卡方檢定
                    stat_, pv, method = ddev, stats.chi2.sf(ddev, ddf), "概似比卡方檢定（φ≤1，離散參數視為 1）"
                out.append({"效果": label, "檢定方法": method, "統計量": round(stat_, 2), "自由度": ddf, "p值": f"{pv:.2e}"})
            t6 = pd.DataFrame(out)
            t6["模型離散參數φ"] = round(phi, 2)
            t6["只看行政區時的φ"] = round(no_m.pearson_chi2 / no_m.df_resid, 2) if no_m.df_resid > 0 else None
            t6.to_csv(TABLE_DIR / "表6_敏感度分析_考慮月份.csv", index=False, encoding="utf-8-sig")  # 【寫出】
            print(t6.to_string(index=False))

            params, cov = full.params, full.cov_params() * max(phi, 1.0)
            names = sorted(map(str, d["district"].unique()))
            def coef_vec(name):
                v = pd.Series(0.0, index=params.index)
                key = f"C(district)[T.{name}]"
                if key in v.index:
                    v[key] = 1.0
                return v
            rows = []
            for a, b in itertools.combinations(names, 2):
                c = coef_vec(a) - coef_vec(b)
                est = float(c @ params); se = math.sqrt(max(float(c @ cov @ c), 0.0))
                if se == 0 or abs(est) > 20 or se > 20:
                    rows.append({"區A": a, "區B": b, "校正月份後勝算比": None, "95%CI下限": None, "95%CI上限": None,
                                 "未校正p值": 1.0, "備註": "無法估計"})
                    continue
                z = est / se
                pv = 2 * stats.t.sf(abs(z), full.df_resid) if phi > 1 else 2 * stats.norm.sf(abs(z))
                crit = stats.t.ppf(0.975, full.df_resid) if phi > 1 else 1.96
                rows.append({"區A": a, "區B": b, "校正月份後勝算比": round(math.exp(est), 3),
                             "95%CI下限": round(math.exp(est - crit * se), 3), "95%CI上限": round(math.exp(est + crit * se), 3),
                             "未校正p值": pv, "備註": ""})
            t7 = pd.DataFrame(rows)
            t7["Holm校正後p值"] = holm(t7["未校正p值"].tolist())
            t7["校正後是否顯著(α=0.05)"] = [("—" if n == "無法估計" else ("是" if v < 0.05 else "否")) for n, v in zip(t7["備註"], t7["Holm校正後p值"])]
            for c in ["未校正p值", "Holm校正後p值"]:
                t7[c] = t7[c].map(lambda v: f"{v:.4f}")
            t7.to_csv(TABLE_DIR / "表7_兩兩比較_考慮月份.csv", index=False, encoding="utf-8-sig")  # 【寫出】
            print(f"考慮月份後的兩兩比較：共 {len(t7)} 對，校正後顯著 {(t7['校正後是否顯著(α=0.05)'] == '是').sum()} 對")
print("已輸出推論性統計表格")
