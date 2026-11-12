"""步驟 4：產生互動報告（單一 HTML 檔，資料內嵌、不連外部網路）

讀取：
  00_分析計畫/報告設定.json         標題、頁首註記、情境、要回答的問題、補充說明
  02_清理後資料/分析用資料.csv       描述性數字在瀏覽器端由這份資料計算
  02_清理後資料/修正與排除紀錄.csv
  04_結果表格/表1、表4–表7           推論性結果（表6、表7 不存在時自動略過）
寫出：
  06_報告/互動報告.html
報告結構：目的 → 重點摘要 → 資料概況 → 描述性統計 → 推論性統計 → 如何應用 → 實務建議（兩類）→ 限制與方法
重點摘要與實務建議依資料自動產生，不寫死區名；不使用「高風險」等字眼。
報告資料細節（設定檔「報告資料細節」）：
  "逐月"：內嵌各區每月的人數，可看每月折線（適合虛構或已核可公開的資料）
  "只含各區合計"：只內嵌各區合計，不畫每月折線、不提供下載（真實資料建議用這個）
逐月模式下若有陽性數 1–4 的格子，報告會顯示小格子提醒。
執行方式（在成果包最上層資料夾）：python 03_程式碼/04_report.py
"""
import html as _html
import json
import math
from pathlib import Path
import pandas as pd

# ===== 輸入與輸出：看程式碼時先檢查這裡 =====
ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "00_分析計畫" / "報告設定.json"            # 【輸入】
CLEAN_FILE = ROOT / "02_清理後資料" / "分析用資料.csv"       # 【輸入】
LOG_FILE = ROOT / "02_清理後資料" / "修正與排除紀錄.csv"     # 【輸入】
T = ROOT / "04_結果表格"                                      # 【輸入】表1、表4–表7
OUT = ROOT / "06_報告" / "互動報告.html"                      # 【寫出】互動報告
OUT.parent.mkdir(exist_ok=True)

cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
esc = lambda x: _html.escape(str(x))


def jd(o):
    """內嵌進 <script> 的 JSON：把 < > & 與行分隔字元轉成 \\u 跳脫，區名含 </script> 也不會跑出程式。"""
    t = json.dumps(o, ensure_ascii=False)
    for ch, code in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"), ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        t = t.replace(ch, code)
    return t

MODE = cfg.get("報告資料細節", "只含各區合計")
_ph = [kk for kk, v in cfg.items() if isinstance(v, str) and "〔" in v] + \
      [f"問題[{i}]" for i, q in enumerate(cfg.get("問題", [])) if any("〔" in str(x) for x in q)]
if _ph:
    raise SystemExit("【停止】報告設定.json 還有沒填的〔 〕：" + "、".join(_ph) + "。請先填好（或請 Claude 先問你），再產生報告。")
SMALL = int(cfg.get("小格子門檻", 5))
df = pd.read_csv(CLEAN_FILE)
log = pd.read_csv(LOG_FILE)
t1 = pd.read_csv(T / "表1_各區描述統計.csv")
t4 = pd.read_csv(T / "表4_卡方檢定.csv", dtype={"p值": str, "模擬p值": str}).iloc[0]
t5 = pd.read_csv(T / "表5_兩兩比較_Holm校正.csv", dtype={"未校正p值": str, "Holm校正後p值": str})
t6 = pd.read_csv(T / "表6_敏感度分析_考慮月份.csv", dtype={"p值": str}) if (T / "表6_敏感度分析_考慮月份.csv").exists() else None
t7 = pd.read_csv(T / "表7_兩兩比較_考慮月份.csv", dtype={"未校正p值": str, "Holm校正後p值": str}) if (T / "表7_兩兩比較_考慮月份.csv").exists() else None

REQ = ["月份", "行政區", "人口數", "篩檢人數", "陽性數"]
all_months = list(pd.period_range(df["月份"].min(), df["月份"].max(), freq="M").strftime("%Y-%m"))
months = sorted(df["月份"].unique())
empty_months = [m for m in all_months if m not in months]
years = sorted({m[:4] for m in months})
unused = [c for c in df.columns if c not in REQ]
dist = t1[t1["行政區"] != "合計"].copy()
tot = t1[t1["行政區"] == "合計"].iloc[0]
k = len(dist)
small_cells = int(((df["陽性數"] > 0) & (df["陽性數"] < SMALL)).sum())
small_dist = dist[(dist["陽性數"] > 0) & (dist["陽性數"] < SMALL)]["行政區"].tolist()
MASK = set(small_dist) if MODE != "逐月" else set()   # 合計模式：全期陽性數過少的區不顯示確切陽性數與率
EXTRA_MASK = []
if len(MASK) == 1:     # 只遮 1 區時，整體合計減其他區就能還原；多遮陽性數次少的一區，讓單一區無法反推
    _cand = dist[~dist["行政區"].isin(MASK)].sort_values(["陽性數", "行政區"])
    if len(_cand):
        EXTRA_MASK = [_cand.iloc[0]["行政區"]]
        MASK |= set(EXTRA_MASK)
if MASK and k - len(MASK) < 2:
    raise SystemExit("【停止】陽性數少於 " + str(SMALL) + " 人的區太多，遮蔽後剩下不到 2 個區可以呈現。"
                     "請先和使用者討論是否合併區域，或改用其他方式呈現。")
masked_note = ("陽性數少於 " + str(SMALL) + " 人的區（" + "、".join(sorted(small_dist)) + "）"
               + ("，以及為了避免由合計反推而一併遮蔽的「" + "、".join(EXTRA_MASK) + "」，" if EXTRA_MASK else "")
               + "在報告中只顯示「< " + str(SMALL) + "」，不顯示確切陽性數與率。") if MASK else ""


def pnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def ptxt(p):
    p = pnum(p)
    return "p < 0.001" if p < 0.001 else f"p ≈ {p:.3f}"


def mnote(r):
    return f"，只納入 {int(r['納入月數'])} 個月" if int(r["納入月數"]) < len(months) else ""


def wilson_hi(x, n, z=1.96):
    p = x / n; d = 1 + z * z / n
    return ((p + z * z / (2 * n)) + z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d * 100


t5_show = t5[~(t5["區A"].isin(MASK) | t5["區B"].isin(MASK))]
t7_show = None if t7 is None else t7[~(t7["區A"].isin(MASK) | t7["區B"].isin(MASK))]
# ---------- 推論結果 ----------
min_exp = float(t4["最小期望次數"])
sim_p = pnum(t4.get("模擬p值", "")) if str(t4.get("模擬p值", "")).strip() not in ("", "nan") else None
p_overall = sim_p if (min_exp < 5 and sim_p is not None) else pnum(t4["p值"])
chi_sig = p_overall < 0.05
by_rate = dist.sort_values("篩檢陽性率(%)", ascending=False)
show = dist[~dist["行政區"].isin(MASK)] if MODE != "逐月" else dist
by_rate_show = show.sort_values("篩檢陽性率(%)", ascending=False)
by_cnt = show.sort_values("陽性數", ascending=False)
smallest = show.sort_values("篩檢人數").iloc[0]
smaller_masked = bool(MASK) and bool((dist[dist["行政區"].isin(MASK)]["篩檢人數"] < smallest["篩檢人數"]).any())
glm_dist = t6[t6["效果"].str.startswith("行政區")].iloc[0] if t6 is not None else None
glm_sig = glm_dist is not None and pnum(glm_dist["p值"]) < 0.05
n_sig5 = int((t5_show["校正後是否顯著(α=0.05)"] == "是").sum())
n_sig7 = int((t7_show["校正後是否顯著(α=0.05)"] == "是").sum()) if t7_show is not None else None
changed = []
if t7_show is not None:
    m_ = t5_show.merge(t7_show, on=["區A", "區B"], suffixes=("_5", "_7"))
    changed = [f'{r["區A"]}對{r["區B"]}（{"有差→沒有足夠證據" if r["校正後是否顯著(α=0.05)_5"] == "是" else "沒有足夠證據→有差"}）'
               for _, r in m_.iterrows() if r["校正後是否顯著(α=0.05)_7"] in ("是", "否") and r["校正後是否顯著(α=0.05)_5"] != r["校正後是否顯著(α=0.05)_7"]]
pair = None
if len(by_rate_show) >= 3:
    a2, b2 = by_rate_show.iloc[0]["行政區"], by_rate_show.iloc[1]["行政區"]
    pair = t5_show[((t5_show["區A"] == a2) & (t5_show["區B"] == b2)) | ((t5_show["區A"] == b2) & (t5_show["區B"] == a2))].iloc[0]
sig = t5_show[t5_show["校正後是否顯著(α=0.05)"] == "是"].assign(ad=lambda x: x["差(百分點)"].abs()).sort_values("ad")
ns = t5_show[t5_show["校正後是否顯著(α=0.05)"] == "否"].assign(ad=lambda x: x["差(百分點)"].abs()).sort_values("ad", ascending=False)
contrast = None
if len(sig) and len(ns) and abs(ns.iloc[0]["差(百分點)"]) >= abs(sig.iloc[0]["差(百分點)"]) * 0.5:
    s1, n1 = sig.iloc[0], ns.iloc[0]
    contrast = (f'{s1["區A"]}對{s1["區B"]}相差 {abs(s1["差(百分點)"]):.2f} 個百分點，校正後有差（{ptxt(s1["Holm校正後p值"])}）；'
                f'{n1["區A"]}對{n1["區B"]}相差 {abs(n1["差(百分點)"]):.2f} 個百分點，校正後沒有足夠證據（{ptxt(n1["Holm校正後p值"])}）。')
phi = float(t6["模型離散參數φ"].iloc[0]) if t6 is not None else None
if phi is None:
    phi_txt = ""
elif phi > 1:
    phi_txt = (f"模型離散參數 φ ≈ {phi:.2f}，{'略' if phi < 1.2 else ''}大於 1：變異比二項分布預期大，已用 quasi-F 檢定放大不確定性。")
elif phi >= 0.8:
    phi_txt = f"模型離散參數 φ ≈ {phi:.2f}，接近 1，符合二項分布的預期；用概似比卡方檢定。"
else:
    phi_txt = (f"模型離散參數 φ ≈ {phi:.2f}，明顯小於 1：沒有過度離散；但這也值得追問資料是否經過平滑或不是逐人計數。"
               "檢定時不縮小不確定性（用概似比卡方檢定）。")
if t6 is not None and pd.notna(t6["只看行政區時的φ"].iloc[0]):
    phi_txt += f"只看行政區、不考慮月份時 φ ≈ {float(t6['只看行政區時的φ'].iloc[0]):.2f}。"
if glm_dist is None:
    glm_txt, glm_read = "", ""
else:
    combo = {(True, True): "考慮月份後，各區整體差異仍然存在", (True, False): "考慮月份後，各區整體差異不再明顯",
             (False, True): "未考慮月份時沒有足夠證據說各區不同，但考慮月份後出現差異", (False, False): "考慮月份後，仍沒有足夠證據說各區不同"}[(chi_sig, glm_sig)]
    glm_txt = (f"敏感度分析（二項式邏輯斯迴歸：行政區＋月份，{glm_dist['檢定方法']}）：{combo}（{ptxt(glm_dist['p值'])}）。"
               + (f"兩兩比較重做後 {n_sig7} 對有差" + (f"，結論改變的有：{'、'.join(changed)}" if changed else "，結論與未考慮月份時相同") + "。" if n_sig7 is not None else ""))
    glm_read = {(True, True): "考慮月份後整體差異仍在；個別比較可能略有不同，所以要看表7。若缺月不是隨機發生，仍可能有影響。",
                (True, False): "考慮月份後整體差異不再明顯，原本的差異可能和月份組成不同有關，解讀時要更保守。",
                (False, True): "兩種做法結論不同，表示結果不穩定，不宜據此下結論。",
                (False, False): "兩種做法都沒有足夠證據說各區不同。"}[(chi_sig, glm_sig)]
logc = log["問題類型"].value_counts()
n_ex = int(sum(v for kk, v in logc.items() if kk not in ("完全重複", "行政區寫法不一", "月份格式不一")))
n_dup = int(logc.get("完全重複", 0))
n_raw = len(df) + n_ex + n_dup
months_differ = dist["納入月數"].nunique() > 1

# ---------- 重點摘要 ----------
summary = [f"整體篩檢陽性率 {tot['篩檢陽性率(%)']:.2f}%（{int(tot['陽性數']):,} ／ {int(tot['篩檢人數']):,} 人）。"]
hi_s, lo_s = by_rate_show.iloc[0], by_rate_show.iloc[-1]
_solid = by_rate_show[by_rate_show["陽性數"] >= SMALL]
if len(_solid) >= 2 and lo_s["行政區"] not in set(_solid["行政區"]):
    lo_s = _solid.iloc[-1]          # 陽性數太少的區不當比較基準（避免拿雜訊當基準）
LOW = "最低"
if MASK:
    LOW = "列出的區中最低"
elif lo_s["行政區"] != by_rate_show.iloc[-1]["行政區"]:
    LOW = "陽性數足夠的區中最低"


def sig_vs(a_, b_):
    """兩區（校正後）是否有差：回傳 True／False／None（找不到）。"""
    q = t5_show[((t5_show["區A"] == a_) & (t5_show["區B"] == b_)) | ((t5_show["區A"] == b_) & (t5_show["區B"] == a_))]
    return None if q.empty else q.iloc[0]["校正後是否顯著(α=0.05)"] == "是"


# 只把「和最低區有顯著差異」的區列為較高
higher = [r_ for _, r_ in by_rate_show.iterrows() if r_["行政區"] != lo_s["行政區"] and sig_vs(r_["行政區"], lo_s["行政區"])]
if len(MASK):
    summary.append(f"有 {len(MASK)} 區的陽性數少於 {SMALL} 人，已不列出該區的率（隱私與穩定性考量）。")
if chi_sig and higher:
    names_ = "、".join(f"{r_['行政區']}（{r_['篩檢陽性率(%)']:.2f}%{mnote(r_)}）" for r_ in higher[:2])
    summary.append(f"篩檢陽性率較高：{names_}；{LOW}：{lo_s['行政區']}（{lo_s['篩檢陽性率(%)']:.2f}%{mnote(lo_s)}）。"
                   + ("" if len(higher) <= 2 else f"另有 {len(higher) - 2} 區也高於最低區。"))
elif chi_sig:
    summary.append(f"{'列出的' if MASK else ''}各區篩檢陽性率介於 {lo_s['篩檢陽性率(%)']:.2f}%（{lo_s['行政區']}）到 {hi_s['篩檢陽性率(%)']:.2f}%（{hi_s['行政區']}）之間；整體檢定有差異，"
                   "但兩兩比較沒有足夠證據指出是哪幾區不同。")
else:
    summary.append(f"{'列出的' if MASK else ''}各區篩檢陽性率介於 {lo_s['篩檢陽性率(%)']:.2f}%（{lo_s['行政區']}）到 {hi_s['篩檢陽性率(%)']:.2f}%（{hi_s['行政區']}）之間，"
                   "但沒有足夠證據說各區不同，數字的高低可能只是隨機波動。")
top_c = by_cnt.iloc[0]
if len(by_cnt) >= 3:
    sec_c = by_cnt.iloc[1]
    same = top_c["行政區"] == hi_s["行政區"]
    summary.append(f"陽性人數最多的是 {top_c['行政區']}（{int(top_c['陽性數']):,} 人）與 {sec_c['行政區']}（{int(sec_c['陽性數']):,} 人）"
                   + ("；率最高的區也是陽性人數最多的區。" if same else "：率和人數要一起看。"))
else:
    summary.append(f"陽性人數：{top_c['行政區']} {int(top_c['陽性數']):,} 人、{by_cnt.iloc[1]['行政區']} {int(by_cnt.iloc[1]['陽性數']):,} 人；率和人數要一起看。")
inf = f"各區差異{'不太可能只是剛好' if chi_sig else '可能只是隨機波動'}（{'模擬 ' if min_exp < 5 and sim_p is not None else '卡方檢定 '}{ptxt(p_overall)}）"
if glm_dist is not None:
    inf += "，" + {(True, True): "考慮月份後整體差異仍然存在", (True, False): "但考慮月份後整體差異不再明顯",
                  (False, True): "但考慮月份後出現差異，結果不穩定", (False, False): "考慮月份後仍沒有足夠證據"}[(chi_sig, glm_sig)]
if pair is not None and chi_sig:
    inf += f"；{pair['區A']}與{pair['區B']}之間{'也有差' if pair['校正後是否顯著(α=0.05)'] == '是' else '沒有足夠證據說誰比較高'}（校正後 {ptxt(pair['Holm校正後p值'])}）"
summary.append(inf + "。")
if min_exp < 5:
    summary.append(f"部分格子人數很少（最小期望次數 {min_exp:.1f}，低於 5），已改用模擬 p 值與 Fisher 精確檢定，結果僅供參考，建議和使用者討論是否合併區域。")
if tot["陽性數"] < 100 or (dist["陽性數"] < 30).any():
    summary.append("陽性人數偏少（全期 " + f"{int(tot['陽性數']):,}" + " 人；有區少於 30 人），檢定力有限，各區的估計比較不穩定（信賴區間較寬）。"
                   + ("" if chi_sig else "沒有發現差異，不代表各區真的相同。"))
if float(tot["篩檢陽性率(%)"]) > 30:
    summary.append("整體篩檢陽性率超過 30%，請先向資料承辦確認「陽性」的定義（例如是否為初篩陽性、分母是否為首次受檢者），再解讀。")
if MODE != "逐月" and glm_dist is not None:
    summary.append("（考慮月份的分析使用逐月資料計算，此版本報告不呈現逐月數字。）")
summary.append("這是「有來篩檢的人」的初篩陽性率，不是盛行率，也不能說明原因；資源配置還需要其他資料。")

# ---------- 建議、應用、解讀 ----------
can = [f"每季更新全部 {k} 區的篩檢陽性率、陽性人數與信賴區間，以整體 {tot['篩檢陽性率(%)']:.2f}% 為參考線比較。"]
if n_ex:
    can.append(f"補查本期被排除的 {n_ex} 列（" + "、".join(f"{kk} {int(v)} 列" for kk, v in logc.items() if kk not in ("完全重複", "行政區寫法不一", "月份格式不一")) + "），補齊後重算。")
can.append(f"在資料彙整流程加入重複、缺值、寫法不一、數值不合理的檢查（本期共發現 {len(log)} 筆問題）。" if len(log)
           else "本期資料沒有發現格式或邏輯問題；仍建議在彙整流程保留這些檢查。")
need = ["<b>各區篩檢資源是否調整：</b>"
        + (f"率最高的是 {esc(hi_s['行政區'])}，陽性人數最多的是 {esc(top_c['行政區'])}，兩者都要考慮；" if chi_sig else "目前沒有足夠證據說各區不同；")
        + "還需要符合篩檢資格人口的涵蓋率、篩檢對象來源（主動邀約或自行前來）、年齡結構。",
        "<b>各區差異的原因：</b>需要年齡、性別、篩檢管道等變項，以及複檢與確診資料。",
        (("<b>月份差異是否為真實季節現象：</b>需要多年資料比較。" if len(years) < 3 else "<b>長期趨勢：</b>需要以年為單位比較，並考慮篩檢政策是否改變。")
         if MODE == "逐月" else "<b>月份差異：</b>本報告未呈現逐月資料，月份差異請另外查看。")]
uses = ["<b>給主管（決策會議）：</b>用「重點摘要」開場，並說清楚「已回答」與「部分回答」的範圍。",
        (f"<b>給資料承辦同仁（資料品質）：</b>回饋 {n_ex} 列被排除的資料，請查明原因並補正。" if n_ex else "<b>給資料承辦同仁（資料品質）：</b>本期沒有被排除的列，可維持目前的彙整方式。"),
        "<b>給業務同仁（持續監測）：</b>把各區篩檢陽性率、陽性人數與信賴區間當作每季追蹤指標。",
        "<b>下一期報告：</b>沿用 03_程式碼 與資料夾結構，換上新的原始資料重跑，數字可以前後比較。"]
if chi_sig:
    read_bar = [f"<b>代表：</b>{esc(hi_s['行政區'])} 有來篩檢的人中，初篩陽性的比例較高；{esc(lo_s['行政區'])} 較低。"]
else:
    read_bar = ["<b>代表：</b>各區數字有高低，但沒有足夠證據說各區真的不同。"]
read_bar.append("<b>不代表：</b>某區居民比較容易生病，或某區是「高風險區」。篩檢對象不是隨機抽樣。")
read_bar.append(f"<b>要一起看：</b>篩檢人數最少的 {esc(smallest['行政區'])}（{int(smallest['篩檢人數']):,} 人）信賴區間較寬" + ("（另有被遮蔽的區人數更少）" if smaller_masked else "") + "；陽性人數與粗篩檢率也不同"
                + ("；各區納入的月數不同。" if months_differ else "。"))

# ---------- 資料限制（依資料產生） ----------
lims = ["篩檢對象非隨機抽樣；篩檢陽性率不等於區內盛行率。",
        "陽性為初篩結果，未含確診，也沒有陽性預測值或偽陽性資訊。",
        cfg.get("年齡說明", "資料沒有年齡欄，無法做年齡標準化。"),
        "年化粗篩檢率的分母是區總人口，不是符合篩檢資格的人口，也無法排除重複受檢。"]
if months_differ:
    lims.append("各區納入月數與缺的月份不同；若缺月不是隨機發生，仍可能影響比較。")
if empty_months:
    lims.append("這些月份所有區都沒有資料：" + ("、".join(empty_months) if len(empty_months) <= 6 else f"共 {len(empty_months)} 個月（最早 {empty_months[0]}、最晚 {empty_months[-1]}）") + "。")
lims.append("這是各區的彙總資料，不能用來推論個人（例如「住在某區的人比較容易陽性」）。")
lims.append(f"資料涵蓋 {all_months[0]} 至 {all_months[-1]}（有資料的月份共 {len(months)} 個，橫跨 {len(years)} 個年度），"
            + ("無法判斷長期趨勢。" if len(years) < 3 else "長期趨勢請另外分析。"))
if unused:
    lims.append("未分析的欄位：" + "、".join(unused) + "（與本次問題無關）。")
if MODE == "逐月" and small_cells:
    lims.append(f"有 {small_cells} 個「月份 × 區」格子的陽性數為 1–{SMALL - 1} 人；真實資料請改用「只含各區合計」模式，並確認是否需要合併或遮蔽。")
if MASK:
    lims.append("遮蔽的限制：整體合計仍會顯示，若只遮一區就可能由「合計減其他區」反推，所以程式會多遮陽性數次少的一區；但這不是完整的去識別化，真實資料發布前請依單位規定確認。")
if small_dist:
    lims.append("這些區的全期陽性數少於 " + str(SMALL) + " 人：" + "、".join(small_dist) + "；真實資料發布前請合併或遮蔽。" + (masked_note if masked_note else ""))
if cfg.get("虛構資料"):
    lims.append("本頁為電腦隨機產生的虛構資料，不代表任何真實地區或個案。")

# ---------- 要放進頁面的資料 ----------
DS = []
for _, r in dist.sort_values("行政區").iterrows():
    DS.append({"name": r["行政區"], "s": int(r["篩檢人數"]), "p": None if r["行政區"] in MASK else int(r["陽性數"]), "pop": int(r["人口數"]),
               "months": int(r["納入月數"]), "miss": [] if r["缺的月份"] == "無" else str(r["缺的月份"]).split("、"),
               "cov": None if pd.isna(r["年化粗篩檢率(%)"]) else float(r["年化粗篩檢率(%)"])})
rows = [[r["月份"], r["行政區"], int(r["篩檢人數"]), int(r["陽性數"])] for _, r in df.iterrows()] if MODE == "逐月" else []
TOT = {"s": int(tot["篩檢人數"]), "p": int(tot["陽性數"])}
ymax = int(math.ceil(max([wilson_hi(r[3], r[2]) for r in rows] + [10]) / 2.0) * 2)
stats = {"chi2": float(t4["卡方值"]), "dof": int(t4["自由度"]), "pchi": ptxt(t4["p值"]), "minExp": min_exp,
         "simP": None if sim_p is None else ptxt(sim_p), "chiSig": bool(chi_sig),
         "pairs": t5_show.to_dict(orient="records"), "nPairs": len(t5_show), "nSig": n_sig5,
         "nonsig": [f'{r["區A"]}—{r["區B"]}' for _, r in t5_show[t5_show["校正後是否顯著(α=0.05)"] == "否"].iterrows()],
         "nMasked": len(MASK),
         "glmTxt": glm_txt, "glmRead": glm_read, "pairsAdj": None if t7_show is None else t7_show.where(pd.notna(t7_show), None).to_dict(orient="records"),
         "phiTxt": phi_txt, "contrast": contrast,
         "pairRead": (f"例如 {pair['區A']}與{pair['區B']}：" + ("校正後也有差（" + ptxt(pair['Holm校正後p值']) + "）。" if pair['校正後是否顯著(α=0.05)'] == '是'
                       else "雖然數字有高低，但差異可能只是隨機波動（校正後 " + ptxt(pair['Holm校正後p值']) + "）。")) if pair is not None else "",
         "log": logc.to_dict(), "nRaw": int(n_raw), "nDedup": int(n_raw - n_dup), "nAna": len(df)}
li = lambda xs: "".join(f"<li>{x}</li>" for x in xs)
qrows = "".join(f'<tr><td>{esc(q)}</td><td>{esc(m_)}</td><td><span class="chip {"ok" if s == "已回答" else "part"}">{esc(s)}</span></td></tr>' for q, m_, s in cfg["問題"])
notes = "".join(f"<li>{esc(x)}</li>" for x in cfg.get("補充說明", []))

HTML = r"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1c2430;--mute:#5b6675;--line:#e3e7ed;--brand:#0f766e;--brand2:#e0f2f1;--warnbg:#fef3c7;--warn:#92400e;--ok:#15803d;--part:#b45309}
@media (prefers-color-scheme:dark){:root{--bg:#10151b;--card:#18202a;--ink:#e8edf3;--mute:#9aa6b5;--line:#2a3441;--brand:#2dd4bf;--brand2:#12332f;--warnbg:#3a2e10;--warn:#fcd34d;--ok:#4ade80;--part:#fbbf24}}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:56px}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 -apple-system,"Noto Sans TC","Microsoft JhengHei",system-ui,sans-serif;overflow-wrap:anywhere}
nav.toc{position:sticky;top:0;z-index:4;background:var(--card);border-bottom:1px solid var(--line)}
nav.toc div{max-width:980px;margin:auto;padding:6px 12px;display:flex;gap:4px;overflow-x:auto;white-space:nowrap}
@media(max-width:700px){nav.toc div{-webkit-mask-image:linear-gradient(to right,#000 85%,transparent);mask-image:linear-gradient(to right,#000 85%,transparent);padding-right:40px}}
nav.toc a{color:var(--mute);text-decoration:none;font-size:14px;padding:6px 10px;border-radius:6px}
nav.toc a:hover{background:var(--brand2);color:var(--ink)}
main{max-width:980px;margin:auto;padding:16px}
h1{font-size:clamp(21px,4vw,30px);margin:10px 0 6px;line-height:1.3}
h2{font-size:21px;margin:32px 0 10px;padding-top:4px}
h2 small{font-weight:400;color:var(--mute);font-size:14px;margin-left:6px}
h3{font-size:17px;margin:0 0 6px}
.banner{background:var(--warnbg);color:var(--warn);border-radius:10px;padding:8px 12px;font-size:14px;font-weight:600;margin:0 0 10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
.g2{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))}
.big b{display:block;font-size:26px;color:var(--brand);line-height:1.2}
.big span{color:var(--mute);font-size:13px}
.story{border-left:4px solid var(--brand);background:var(--card);border-radius:0 12px 12px 0;padding:12px 16px;margin-bottom:12px}
.story p{margin:4px 0}
.chip{display:inline-block;border-radius:99px;padding:1px 10px;font-size:13px;font-weight:700;white-space:nowrap}
.chip.ok{background:var(--brand2);color:var(--ok)}.chip.part{background:var(--warnbg);color:var(--part)}
.sum li{margin:4px 0}
.read{background:var(--brand2);border-radius:10px;padding:10px 14px;font-size:15px;margin-top:10px}
.read b.h{display:block;margin-bottom:2px}
.read ul{margin:4px 0 0;padding-left:20px}
.row{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;margin:0 0 8px;font-size:14px}
.row label{display:inline-flex;align-items:center;gap:8px;min-height:44px;cursor:pointer}
input[type=checkbox]{width:22px;height:22px;accent-color:var(--brand)}
select,button.dl{font:inherit;min-height:44px;padding:4px 12px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
svg{display:block;width:100%;height:auto}
svg text{fill:var(--ink);font-size:13px;font-family:inherit}
.ax{stroke:var(--line)}
.bar{fill:var(--brand);cursor:pointer}.bar.sel{stroke:var(--ink);stroke-width:2}.rowhit{fill:transparent;cursor:pointer}
g.b:focus{outline:none}g.b:focus .bar{stroke:var(--ink);stroke-width:2}
.ln{fill:none;stroke:var(--brand);stroke-width:2.5}.dot{fill:var(--brand)}
.hit{fill:transparent;cursor:pointer}.hit:focus{outline:none;stroke:var(--ink);stroke-width:2}
.err{stroke:var(--ink);stroke-width:1.3}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--bg);border-radius:8px;padding:6px 10px;font-size:13px;line-height:1.5;display:none;z-index:5;max-width:240px}
.note{color:var(--mute);font-size:13px;margin:6px 0 0}
details{margin-top:10px}
details>summary{cursor:pointer;font-weight:700;min-height:36px;padding-top:4px}
.tw{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;white-space:nowrap}
th{background:var(--brand2)}
td.n{text-align:right;font-variant-numeric:tabular-nums}
table.wrap th,table.wrap td{white-space:normal}
.two .card h3{display:flex;gap:8px;align-items:center}
.warn{background:var(--warnbg);color:var(--warn);border-radius:10px;padding:10px 14px;font-size:14px}
.warn ul{margin:4px 0 0;padding-left:20px}
footer{color:var(--mute);font-size:13px;margin:28px 0 8px;border-top:1px solid var(--line);padding-top:12px}
</style>
</head>
<body>
<nav class="toc" aria-label="報告目錄"><div>
<a href="#goal">目的</a><a href="#sum">重點摘要</a><a href="#data">資料概況</a><a href="#desc">描述性統計</a><a href="#inf">推論性統計</a><a href="#use">如何應用</a><a href="#rec">實務建議</a><a href="#lim">限制與方法</a>
</div></nav>
<main>
<h1>__TITLE__</h1>
<p class="banner">__BANNER__</p>

<h2 id="goal">這份報告要回答什麼</h2>
<div class="story"><p><b>情境</b>：__STORY__</p></div>
<div class="card tw"><table class="wrap"><tr><th>要回答的問題</th><th>我們做的分析</th><th>回答程度</th></tr>__QROWS__</table></div>

<h2 id="sum">重點摘要</h2>
<div class="card"><ul class="sum">__SUMMARY__</ul></div>

<h2 id="data">資料概況</h2>
<div class="grid">
<div class="card big"><b id="flow">–</b><span>原始列數 → 去除重複 → 排除缺值與待查（分析用）</span></div>
<div class="card big"><b id="c1">–</b><span>總篩檢人數</span></div>
<div class="card big"><b id="c2">–</b><span>總陽性數</span></div>
<div class="card big"><b id="c3">–</b><span>整體篩檢陽性率</span></div>
</div>
<p class="note" id="lognote">清理時發現：<span id="logtxt"></span>。缺值與待查的列沒有補值或修改，直接排除，所以部分行政區少了幾個月。</p>

<h2 id="desc">描述性統計 <small>各區差多少？</small></h2>
<div class="card">
<div class="row"><b>各區篩檢陽性率</b>
<label>排序 <select id="ord"><option value="code">依區代碼</option><option value="rate">依陽性率由高到低</option></select></label>
<label><input type="checkbox" id="ci" checked> 顯示 95% 信賴區間</label></div>
<div id="bars"></div>
<p class="note">滑鼠移到長條上（手機點一下）看細節<span id="monthly1">；點長條會切換下方的每月趨勢</span>。長條顏色不代表風險等級。<span id="monthly2">區名後的「（○個月）」表示該區只納入幾個月。</span></p>
<div class="read"><b class="h">怎麼解讀</b><ul>__READBAR__</ul></div>
</div>
<div class="card" id="linecard">
<div class="row"><b>每月趨勢</b><label>行政區 <select id="sel"></select></label></div>
<p id="meta" class="note" style="margin:0 0 6px"></p>
<div id="line"></div>
<p class="note">× ＝ 該月無有效資料（缺值或待查而被排除，不是 0，也未補值）。各區縱軸一致（0–__YMAX__%），避免把雜訊誤看成趨勢。點折線上的點可看該月數字。</p>
<div class="read"><b class="h">怎麼解讀</b><ul>
<li><b>代表：</b>各區各月的篩檢陽性率；縱軸一致，可以互相比較。</li>
<li><b>不代表：</b>單月的上下起伏就是「上升」或「下降」的趨勢；每月人數較少，多數起伏只是隨機波動。</li>__NOTES__
</ul></div>
</div>
<details class="card"><summary>完整數字：各區描述統計（表1）</summary><div class="tw"><table id="t1"></table></div>
<p class="note">年化粗篩檢率＝篩檢人數合計 ÷ 納入月數 × 12 ÷ 區人口數。人口數是區總人口，不是符合篩檢資格的人口；也無法排除同一人重複受檢。只能參考。</p></details>
<details class="card" id="t3wrap"><summary>完整數字：各區每月篩檢陽性率（表3，空白＝該月被排除）</summary><div class="tw"><table id="t3"></table></div>
__DLROW__</details>

<h2 id="inf">推論性統計 <small>差異是真的，還是只是剛好？</small></h2>
<div class="g2">
<div class="card"><h3>各區是否全部一樣？</h3>
<p>卡方獨立性檢定（各區 × 陽性／陰性）：χ² = <b id="chi"></b>，自由度 <span id="dof"></span>，<span id="pchi"></span>。</p>
<p class="note">假設檢查：最小期望次數 <span id="minexp"></span>（需 ≥ 5）<span id="simp"></span>。</p>
<div class="read"><b class="h">白話</b><span id="chiread"></span></div></div>
<div class="card"><h3>哪幾區之間有差？</h3>
<p>兩兩比較共 <span id="np"></span> 對，用 Holm 法校正多重比較後，<b id="nsig"></b> 對有差；以下 <span id="nns"></span> 對<b>沒有足夠證據</b>說有差：</p>
<p id="nslist" style="margin:4px 0"></p>
<div class="read"><b class="h">白話</b><span id="pairread"></span></div></div>
<div class="card" id="glmcard"><h3>考慮月份後，結論會變嗎？</h3>
<p id="glmtxt"></p>
<p class="note" id="phitxt"></p>
<div class="read"><b class="h">白話</b><span id="glmread"></span></div></div>
<div class="card" id="ctcard"><h3>顯著 ≠ 重要 ≠ 高風險</h3>
<p id="contrast"></p>
<div class="read"><b class="h">白話</b>差距差不多，結論卻可能不同，因為人數不同。人數很多時，很小的差異也可能「顯著」；要同時看差多少、差異的信賴區間，以及這個差距在實務上重不重要。</div></div>
</div>
<details class="card"><summary>完整數字：兩兩比較（表5，含差異的 95% 信賴區間）</summary><div class="tw"><table id="t5"></table></div></details>
<details class="card" id="t7wrap"><summary>完整數字：考慮月份後的兩兩比較（表7，勝算比）</summary><div class="tw"><table id="t7"></table></div></details>

<h2 id="use">如何應用這份報告</h2>
<div class="card"><ul>__USES__</ul></div>

<h2 id="rec">實務建議</h2>
<div class="g2 two">
<div class="card"><h3><span class="chip ok">可由數據支持</span></h3><ul>__CAN__</ul></div>
<div class="card"><h3><span class="chip part">需進一步查證</span></h3><ul>__NEED__</ul></div>
</div>

<h2 id="lim">資料限制與方法說明</h2>
<div class="warn"><b>資料限制</b><ul>__LIMS__</ul></div>
<details class="card"><summary>方法說明（點開）</summary><ul>
<li><b>篩檢陽性率</b>：陽性數合計 ÷ 篩檢人數合計（先加總人數再相除，不平均百分比）。</li>
<li><b>95% 信賴區間</b>：Wilson 法（陽性數為 0 時也能計算）；未考慮月別群聚，其他方法的數字會略有不同。</li>
<li><b>卡方獨立性檢定</b>：檢定各區陽性率是否全部相同；用人數計算，不用百分比。</li>
<li><b>整體檢定</b>：最小期望次數 &lt; 5 時，另以固定邊際總數的蒙地卡羅模擬計算 p 值。</li><li><b>兩兩比較</b>：期望次數皆 ≥ 5 用 2×2 卡方檢定，否則用 Fisher 精確檢定；以 Holm 法校正多重比較，α = 0.05；差異的 95% 信賴區間為 Newcombe 法（未校正）。</li>
<li><b>敏感度分析</b>：二項式邏輯斯迴歸（行政區＋月份）。離散參數 φ ≤ 1 時用概似比卡方檢定（不縮小不確定性），φ &gt; 1 時用 quasi-F 檢定。考慮月份後的兩兩比較用模型係數做 Wald 檢定，再以 Holm 法校正。</li>
<li><b>對應檔案</b>：程式在 03_程式碼，結果在 04_結果表格（表1–表7）、05_圖表。</li>
</ul></details>

<footer>__FOOTER__</footer>
</main>
<div id="tip" role="status"></div>
<script>
var DATA=__DATA__; /* 逐月模式：[月份, 行政區, 篩檢人數, 陽性數]；只含各區合計模式：空陣列 */
var DS=__DS__; /* 各區合計（由 Python 算好；陽性數過少的區 p 為 null，不放進頁面） */
var TOT=__TOT__;
var STATS=__STATS__;
var YMAX=__YMAX__, ALLOW_DL=__ALLOWDL__, MONTHS=__MONTHS__, MONTHLY=__MONTHLY__, NPRESENT=__NPRESENT__, MASKED=__MASKED__, SMALL=__SMALL__;
(function(){
 var $=function(s){return document.querySelector(s)},NS="http://www.w3.org/2000/svg";
 function el(n,a,t){var e=document.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;return e}
 function wilson(x,n){var z=1.96,p=x/n,d=1+z*z/n,c=(p+z*z/(2*n))/d,h=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return [(c-h)*100,(c+h)*100]}
 var fmt=function(v){return v.toLocaleString()};
 /* 注意：部分內容以 innerHTML 組字串，目前只放程式算出的數字與固定文字。
    若改成讓使用者匯入任意資料，請先對字串做 HTML 跳脫（escape）。 */
 var E=function(x){return String(x).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]})};
 var months=MONTHS,multiY=months[0].slice(0,4)!==months[months.length-1].slice(0,4),ml=function(k){return multiY?k.slice(2):parseInt(k.slice(5),10)+"月"};
 var by={},tot={s:0,p:0};
 tot.s=TOT.s;tot.p=TOT.p;DS.forEach(function(d){by[d.name]={name:d.name,m:{}}});
 DATA.forEach(function(r){by[r[1]].m[r[0]]={s:r[2],p:r[3]}});
 var ds=DS.map(function(d){d.masked=d.p==null;if(d.masked){d.rate=0;d.lo=0;d.hi=0}else{d.rate=d.p/d.s*100;var w=wilson(d.p,d.s);d.lo=w[0];d.hi=w[1]}return d});
 if(!MONTHLY){["#linecard","#t3wrap","#monthly1"].forEach(function(s){$(s).style.display="none"})}
 var anyShort=ds.some(function(d){return d.months<NPRESENT});if(!MONTHLY||!anyShort){$("#monthly2").style.display="none"}

 $("#flow").textContent=STATS.nRaw+" → "+STATS.nDedup+" → "+STATS.nAna;
 $("#c1").textContent=fmt(tot.s);$("#c2").textContent=fmt(tot.p);$("#c3").textContent=(tot.p/tot.s*100).toFixed(2)+"%";
 var L=STATS.log,LK=Object.keys(L);
 if(LK.length){$("#logtxt").textContent=LK.map(function(k){return k+" "+L[k]+" 筆"}).join("、")}else{$("#lognote").textContent="本期資料沒有發現缺值、重複或格式問題，沒有排除任何列。"}
 $("#chi").textContent=STATS.chi2.toFixed(1);$("#dof").textContent=STATS.dof;$("#pchi").textContent=STATS.pchi;$("#minexp").textContent=STATS.minExp;
 $("#chiread").textContent=STATS.chiSig?"各區的篩檢陽性率不太可能全部相同。但這只說明「有差」，不說明哪一區比較嚴重。":"沒有足夠證據說各區不同，差異可能只是隨機波動。";
 if(STATS.simP)$("#simp").textContent="；有期望次數 < 5，另以蒙地卡羅模擬：模擬 "+STATS.simP;
 $("#np").textContent=STATS.nPairs;$("#nsig").textContent=STATS.nSig;$("#nns").textContent=STATS.nonsig.length;$("#nslist").textContent=STATS.nonsig.join("、")||"（無）";
 $("#pairread").textContent=STATS.pairRead||"區數較少或整體沒有差異，請直接看下方表5。";
 if(STATS.glmTxt){$("#glmtxt").textContent=STATS.glmTxt;
  $("#phitxt").textContent=STATS.phiTxt;
  $("#glmread").textContent=STATS.glmRead;}
 else{$("#glmcard").style.display="none";$("#t7wrap").style.display="none";}
 if(STATS.contrast){$("#contrast").textContent=STATS.contrast}else{$("#ctcard").style.display="none"}
 var h="<tr><th>行政區</th><th>納入月數</th><th>缺的月份</th><th>篩檢人數</th><th>年化粗篩檢率</th><th>陽性數</th><th>篩檢陽性率</th><th>95% 信賴區間</th></tr>";
 ds.forEach(function(d){h+="<tr><td>"+E(d.name)+"</td><td class='n'>"+d.months+"</td><td>"+(d.miss.join("、")||"無")+"</td><td class='n'>"+fmt(d.s)+"</td><td class='n'>"+(d.cov==null?"—":d.cov.toFixed(1)+"%")+"</td><td class='n'>"+(d.masked?"&lt; "+SMALL:fmt(d.p))+"</td><td class='n'>"+(d.masked?"—":d.rate.toFixed(2)+"%")+"</td><td class='n'>"+(d.masked?"—":d.lo.toFixed(2)+"–"+d.hi.toFixed(2)+"%")+"</td></tr>"});
 var tw=wilson(tot.p,tot.s);h+="<tr><td><b>合計</b></td><td class='n'>"+NPRESENT+"</td><td>—</td><td class='n'>"+fmt(tot.s)+"</td><td class='n'>—</td><td class='n'>"+fmt(tot.p)+"</td><td class='n'>"+(tot.p/tot.s*100).toFixed(2)+"%</td><td class='n'>"+tw[0].toFixed(2)+"–"+tw[1].toFixed(2)+"%</td></tr>";
 $("#t1").innerHTML=h;
 h="<tr><th>行政區</th>"+months.map(function(k){return "<th>"+ml(k)+"</th>"}).join("")+"</tr>";
 ds.forEach(function(d){h+="<tr><td>"+E(d.name)+"</td>"+months.map(function(k){var v=by[d.name].m[k];return "<td class='n'>"+(v?(v.p/v.s*100).toFixed(2):"")+"</td>"}).join("")+"</tr>"});
 $("#t3").innerHTML=h;
 h="<tr><th>比較</th><th>差（百分點）</th><th>差的 95% 信賴區間</th><th>檢定方法</th><th>未校正 p</th><th>Holm 校正後 p</th><th>校正後有差？</th></tr>";
 STATS.pairs.forEach(function(p){h+="<tr><td>"+E(p["區A"])+" vs "+E(p["區B"])+"</td><td class='n'>"+Number(p["差(百分點)"]).toFixed(2)+"</td><td class='n'>"+Number(p["差的95%CI下限"]).toFixed(2)+" 至 "+Number(p["差的95%CI上限"]).toFixed(2)+"</td><td>"+p["檢定方法"]+"</td><td class='n'>"+p["未校正p值"]+"</td><td class='n'>"+p["Holm校正後p值"]+"</td><td>"+p["校正後是否顯著(α=0.05)"]+"</td></tr>"});
 $("#t5").innerHTML=h;
 if(STATS.pairsAdj){h="<tr><th>比較</th><th>校正月份後勝算比</th><th>95% 信賴區間</th><th>未校正 p</th><th>Holm 校正後 p</th><th>校正後有差？</th></tr>";
  STATS.pairsAdj.forEach(function(p){h+="<tr><td>"+E(p["區A"])+" vs "+E(p["區B"])+"</td><td class='n'>"+(p["校正月份後勝算比"]==null?"無法估計":Number(p["校正月份後勝算比"]).toFixed(3))+"</td><td class='n'>"+(p["95%CI下限"]==null?"—":Number(p["95%CI下限"]).toFixed(3)+"–"+Number(p["95%CI上限"]).toFixed(3))+"</td><td class='n'>"+p["未校正p值"]+"</td><td class='n'>"+p["Holm校正後p值"]+"</td><td>"+p["校正後是否顯著(α=0.05)"]+"</td></tr>"});
  $("#t7").innerHTML=h;}
 if(ALLOW_DL&&MONTHLY&&$("#dlcsv")){$("#dlcsv").addEventListener("click",function(){var csv="﻿月份,行政區,篩檢人數,陽性數\n"+DATA.map(function(r){return r.join(",")}).join("\n");
  var a=document.createElement("a");a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));a.download="chart_data_4cols.csv";document.body.appendChild(a);a.click();a.remove()})}
 else if($("#dlrow")){$("#dlrow").style.display="none"}
 /* 互動圖表：滑鼠用 pointer 事件顯示／隱藏；觸控點一下顯示，點其他地方才收起 */
 var tip=$("#tip"),rebuilding=false;
 function showTip(html,x,y){tip.innerHTML=html;tip.style.display="block";var w=tip.offsetWidth,hh=tip.offsetHeight;
  var left=Math.max(8,Math.min(innerWidth-w-8,x+12)),top=y+14;if(top+hh>innerHeight-8)top=Math.max(8,y-hh-14);tip.style.left=left+"px";tip.style.top=top+"px"}
 function hideTip(){tip.style.display="none"}
 function hover(node,html){node.addEventListener("pointermove",function(e){if(e.pointerType==="mouse")showTip(html,e.clientX,e.clientY)});
  node.addEventListener("pointerleave",function(e){if(e.pointerType==="mouse")hideTip()})}
 var sel=$("#sel");ds.forEach(function(d){var o=document.createElement("option");o.value=d.name;o.textContent=d.name;sel.appendChild(o)});
 var cur=sel.value=ds.filter(function(d){return !d.masked}).sort(function(a,b){return b.rate-a.rate})[0].name;
 var cw=function(id){return Math.max(240,Math.floor($(id).clientWidth||600))};
 function pick(name,x,y,html){cur=name;sel.value=cur;rebuilding=true;bars();line();rebuilding=false;if(x!=null)showTip(html,x,y)}
 function bars(){
  var W=cw("#bars"),small=W<520,Lm=small?112:128,rowH=small?38:36,order=$("#ord").value;
  var arr=ds.slice().sort(order==="rate"?function(a,b){return b.rate-a.rate}:function(a,b){return a.name<b.name?-1:1});
  var H=arr.length*rowH+34,svg=el("svg",{viewBox:"0 0 "+W+" "+H,width:W,height:H,role:"img","aria-label":"各行政區篩檢陽性率長條圖"});
  var showCI=$("#ci").checked,max=Math.max.apply(null,ds.map(function(d){return showCI?d.hi:d.rate}).concat([1]))*1.15,sc=(W-Lm-52)/max;
  for(var t=0;t<=Math.floor(max);t+=2){svg.appendChild(el("line",{x1:Lm+sc*t,x2:Lm+sc*t,y1:4,y2:H-24,"class":"ax"}));svg.appendChild(el("text",{x:Lm+sc*t-8,y:H-6},t+"%"))}
  arr.forEach(function(d,i){var y=6+i*rowH,g=el("g",{"class":"b",tabindex:0,role:"button","aria-label":d.masked?d.name+" 陽性數少於 "+SMALL+" 人，不顯示":d.name+" 篩檢陽性率 "+d.rate.toFixed(2)+"%，納入 "+d.months+" 個月"});
   g.appendChild(el("rect",{x:0,y:y-3,width:W,height:rowH-2,"class":"rowhit"}));
   g.appendChild(el("text",{x:2,y:y+rowH/2+3},d.name+(d.months<NPRESENT?"（"+d.months+"個月）":"")));
   if(d.masked){g.appendChild(el("text",{x:Lm+6,y:y+rowH/2+3},"陽性數 < "+SMALL+" 人，不顯示"));svg.appendChild(g);return}
   g.appendChild(el("rect",{x:Lm,y:y,width:Math.max(1,sc*d.rate),height:rowH-8,rx:3,"class":"bar"+(d.name===cur?" sel":"")}));
   if(showCI)g.appendChild(el("line",{x1:Lm+sc*d.lo,x2:Lm+sc*d.hi,y1:y+(rowH-8)/2,y2:y+(rowH-8)/2,"class":"err"}));
   g.appendChild(el("text",{x:Lm+6+sc*(showCI?d.hi:d.rate),y:y+rowH/2+3},d.rate.toFixed(2)+"%"));
   var html="<b>"+E(d.name)+"</b><br>篩檢人數 "+fmt(d.s)+"<br>陽性數 "+fmt(d.p)+"<br>篩檢陽性率 "+d.rate.toFixed(2)+"%<br>95% 信賴區間 "+d.lo.toFixed(2)+"–"+d.hi.toFixed(2)+"%<br>年化粗篩檢率 "+(d.cov==null?"—":d.cov.toFixed(1)+"%")+"<br>納入月數 "+d.months+(d.miss.length?"（缺 "+d.miss.join("、")+"）":"");
   hover(g,html);
   g.addEventListener("focus",function(){var r=g.getBoundingClientRect();showTip(html,r.left+20,r.top)});
   g.addEventListener("blur",function(){if(!rebuilding)hideTip()});
   g.addEventListener("click",function(e){pick(d.name,e.clientX,e.clientY,html)});
   g.addEventListener("keydown",function(e){if(e.key==="Enter"||e.key===" "){e.preventDefault();var r=g.getBoundingClientRect();pick(d.name,r.left+20,r.top,html);var n=document.querySelectorAll("#bars g.b");for(var k=0;k<n.length;k++){if(n[k].getAttribute("aria-label").indexOf(d.name)===0){n[k].focus();break}}}});
   svg.appendChild(g)});
  $("#bars").innerHTML="";$("#bars").appendChild(svg)}
 function line(){
  var d=by[cur],dd=ds.filter(function(x){return x.name===cur})[0],W=cw("#line"),H=260,Lm=44,B=28,n=months.length,svg=el("svg",{viewBox:"0 0 "+W+" "+H,width:W,height:H,role:"img","aria-label":cur+" 每月篩檢陽性率折線圖"});
  var pts=months.map(function(k){var v=by[d.name].m[k];if(!v)return null;var w=wilson(v.p,v.s);return {k:k,s:v.s,p:v.p,rate:v.p/v.s*100,lo:w[0],hi:w[1]}});
  var showCI=$("#ci").checked,step=YMAX>10?4:2,small=W<520;
  var X=function(i){return Lm+i*(W-Lm-16)/Math.max(1,n-1)},Y=function(v){return 10+(H-B-10)*(1-v/YMAX)};
  for(var v=0;v<=YMAX;v+=step){svg.appendChild(el("line",{x1:Lm,x2:W-6,y1:Y(v),y2:Y(v),"class":"ax"}));svg.appendChild(el("text",{x:2,y:Y(v)+4},v+"%"))}
  var seg=[];pts.forEach(function(p,i){if(p){seg.push(X(i)+","+Y(p.rate))}else{if(seg.length>1)svg.appendChild(el("polyline",{points:seg.join(" "),"class":"ln"}));seg=[]}});
  if(seg.length>1)svg.appendChild(el("polyline",{points:seg.join(" "),"class":"ln"}));
  pts.forEach(function(p,i){if(!small||i%3===0||i===n-1)svg.appendChild(i===n-1?el("text",{x:W-2,y:H-8,"text-anchor":"end"},ml(months[i])):el("text",{x:X(i)-9,y:H-8},ml(months[i])));
   if(!p){svg.appendChild(el("text",{x:X(i)-5,y:Y(0)-8,style:"font-weight:700"},"×"));return}
   if(showCI)svg.appendChild(el("line",{x1:X(i),x2:X(i),y1:Y(p.lo),y2:Y(Math.min(p.hi,YMAX)),"class":"err"}));
   svg.appendChild(el("circle",{cx:X(i),cy:Y(p.rate),r:5,"class":"dot"}));
   var html="<b>"+E(cur)+"　"+p.k+"</b><br>篩檢人數 "+fmt(p.s)+"<br>陽性數 "+fmt(p.p)+"<br>篩檢陽性率 "+p.rate.toFixed(2)+"%<br>95% 信賴區間 "+p.lo.toFixed(2)+"–"+p.hi.toFixed(2)+"%";
   var c=el("circle",{cx:X(i),cy:Y(p.rate),r:15,"class":"hit",tabindex:0,role:"img","aria-label":cur+" "+p.k+" 篩檢陽性率 "+p.rate.toFixed(2)+"%"});
   hover(c,html);
   c.addEventListener("click",function(e){showTip(html,e.clientX,e.clientY)});
   c.addEventListener("focus",function(){var r=c.getBoundingClientRect();showTip(html,r.left+10,r.top)});c.addEventListener("blur",hideTip);
   svg.appendChild(c)});
  $("#line").innerHTML="";$("#line").appendChild(svg);
  $("#meta").textContent=cur+"：納入 "+dd.months+" 個月"+(dd.miss.length?"（缺 "+dd.miss.join("、")+"）":"")+"，合計篩檢 "+fmt(dd.s)+" 人、陽性 "+fmt(dd.p)+" 人（"+dd.rate.toFixed(2)+"%）"}
 sel.addEventListener("change",function(){cur=sel.value;bars();line()});
 $("#ci").addEventListener("change",function(){bars();line()});
 $("#ord").addEventListener("change",bars);
 document.addEventListener("click",function(e){if(!e.target.closest||!e.target.closest("g.b,circle"))hideTip()});
 var rt,lastW=innerWidth;window.addEventListener("resize",function(){if(innerWidth===lastW)return;lastW=innerWidth;clearTimeout(rt);rt=setTimeout(function(){bars();line()},120)});
 bars();line();
})();
</script>
</body>
</html>
"""

out = (HTML.replace("__TITLE__", esc(cfg["標題"])).replace("__BANNER__", esc(cfg["頁首註記"])).replace("__STORY__", esc(cfg["情境"]))
       .replace("__QROWS__", qrows).replace("__SUMMARY__", li(esc(x) for x in summary)).replace("__READBAR__", li(read_bar))
       .replace("__NOTES__", notes).replace("__USES__", li(uses)).replace("__CAN__", li(esc(x) for x in can)).replace("__NEED__", li(need))
       .replace("__LIMS__", li(esc(x) for x in lims)).replace("__FOOTER__", esc(cfg.get("頁尾", ""))).replace("__YMAX__", str(ymax))
       .replace("__ALLOWDL__", "true" if (cfg.get("提供下載逐列資料", False) and MODE == "逐月") else "false")
       .replace("__DLROW__", '<p class="row" id="dlrow"><button type="button" class="dl" id="dlcsv">下載圖表用資料（月份、行政區、篩檢人數、陽性數）</button></p>' if (cfg.get("提供下載逐列資料", False) and MODE == "逐月") else "").replace("__MONTHLY__", "true" if MODE == "逐月" else "false").replace("__NPRESENT__", str(len(months))).replace("__MASKED__", json.dumps(sorted(MASK), ensure_ascii=False)).replace("__SMALL__", str(SMALL))
       .replace("__MONTHS__", jd(all_months)).replace("__DATA__", jd(rows))
       .replace("__DS__", jd(DS)).replace("__TOT__", jd(TOT)).replace("__STATS__", jd(stats)))
OUT.write_text(out, encoding="utf-8")                       # 【寫出】互動報告
print(f"已輸出 {OUT.relative_to(ROOT)}（{len(out):,} 字元）")
for s in summary:
    print("  ・", s)
