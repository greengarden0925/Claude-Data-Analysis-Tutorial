"""產生 22 份【虛構】壓力測試資料，用來檢查 skill 的程式在各種狀況下是否穩健。
用法：python3 gen_stress_data.py 輸出資料夾
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "stress_data"); OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(1)


def base(districts, months, rates=None, n=(500, 1500), vacc=True):
    rows = []
    for i, d in enumerate(districts):
        pop = 20000 + i * 5000
        for m in months:
            s = int(rng.integers(*n)); r = rates[i] if rates else 0.05 + 0.01 * i
            rows.append({"月份": m, "行政區": d, "人口數": pop, "篩檢人數": s, "陽性數": int(rng.binomial(s, r)),
                         **({"疫苗接種人數": int(s * 0.2)} if vacc else {})})
    return pd.DataFrame(rows)


M12 = [f"2025-{i:02d}" for i in range(1, 13)]
D8 = [f"{c}區" for c in "ABCDEFGH"]
out = {}
out["a_two"] = base(["甲區", "乙區"], M12)                                          # 只有 2 區
out["b_equal"] = base(D8, M12, rates=[0.06] * 8)                                    # 各區陽性率相同
c = base(D8, M12); c.loc[(c.行政區 == "C區") & (c.月份 == "2025-03"), "陽性數"] = 0; c.loc[c.行政區 == "H區", "陽性數"] = 0
out["c_zero"] = c                                                                   # 某區整年陽性為 0
c2 = base(["甲區", "乙區", "丙區"], M12); c2.loc[c2.行政區.isin(["乙區", "丙區"]), "陽性數"] = 0
out["c2_bothzero"] = c2                                                             # 兩區都是 0
c3 = base(D8, M12); c3["陽性數"] = 0
out["c3_allzero"] = c3                                                              # 全部是 0（應停止）
d = base(D8, M12); out["d_onemonth"] = d[~((d.行政區 == "H區") & (d.月份 != "2025-06"))]   # 某區只有 1 個月
M18 = [str(p) for p in pd.period_range("2024-07", "2025-12", freq="M")]
e = base(D8, M18); out["e_18m_gap"] = e[e.月份 != "2025-02"]                          # 跨年 18 個月且整月缺
out["f_small"] = base(["A區", "B區", "C區", "D區"], ["2025-01", "2025-02"], rates=[.01, .02, .01, .03], n=(20, 60))  # 人數很少
g = base(D8, M12, vacc=False); g = g.rename(columns={"篩檢人數": "受檢人數"}); out["g_cols"] = g   # 欄位名稱不同（應停止）
g2 = base(D8, M12); g2["備註"] = "x"; out["g2_extra_only"] = g2                      # 多餘欄位
g3 = base(D8, M12); g3["人口數"] = g3["人口數"] + g3.groupby("行政區").cumcount() * 10; out["g3_pop_vary"] = g3   # 人口數各月不同
out["g_novacc"] = base(D8, M12, vacc=False)                                         # 沒有疫苗接種人數欄
out["h_names"] = base(["Da'an 區", "Xinyi區", "大安區", "da'an區", " 信義 區", "Beitou District"], M12)  # 不同寫法其實是不同的區（應停止）
h2 = base(D8, M12); h2["行政區"] = [d.replace("區", " 區") if k % 3 == 0 else (d.lower() if k % 3 == 1 else d) for k, d in enumerate(h2["行政區"])]; out["h2_variants"] = h2   # 空白、大小寫變化
fm = {0: lambda m: m, 1: lambda m: f"2025-{int(m[5:])}", 2: lambda m: f"2025/{m[5:]}", 3: lambda m: f"114/{m[5:]}"}
i_ = base(D8, M12); i_["月份"] = [fm[k % 4](m) for k, m in enumerate(i_["月份"])]; out["i_months"] = i_   # 月份寫法混用
i2 = base(D8, M12); i2["月份"] = i2["月份"].str.replace("2025-", "2025/"); out["i2_slash"] = i2
i3 = base(D8, M12); i3["月份"] = [f"2025-{int(m[5:])}" for m in i3["月份"]]; out["i3_dash_nopad"] = i3
i4 = base(D8, M12); i4["月份"] = [f"114/{m[5:]}" for m in i4["月份"]]; out["i4_roc"] = i4     # 民國年
b = base(["甲區", "乙區", "丙區", "丁區"], M12, n=(500, 1500))
x = b.copy(); x.loc[3, "行政區"] = ""; out["j_blank"] = x                          # 行政區空白
x = b.copy().astype({"篩檢人數": "float"}); x.loc[5, "篩檢人數"] = 250.7; x.loc[9, "人口數"] = 0; out["k_nonint"] = x   # 非整數、人口數為 0
out["m_smalldist"] = b.assign(陽性數=lambda t: np.where(t.行政區 == "丁區", 0, t.陽性數)).copy()
out["m_smalldist"].loc[(out["m_smalldist"].行政區 == "丁區") & (out["m_smalldist"].月份 == "2025-02"), "陽性數"] = 2
out["m_smalldist"].loc[(out["m_smalldist"].行政區 == "丁區") & (out["m_smalldist"].月份 == "2025-07"), "陽性數"] = 1   # 某區全期陽性 < 5
out["n_lowpos"] = b.assign(陽性數=lambda t: (t.陽性數 * 0.1).astype(int))           # 陽性率很低、人數很少
for k, v in out.items():
    v.to_csv(OUT / f"{k}.csv", index=False, encoding="utf-8-sig")
b.to_csv(OUT / "l_big5.csv", index=False, encoding="cp950")                         # Big5 編碼
print(f"已產生 {len(out) + 1} 份：", "、".join(list(out) + ["l_big5"]))
