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
真實資料：請把設定檔的「提供下載逐列資料」改成 false，並先確認報告內嵌的資料可以被看到的人看到。
執行方式（在成果包最上層資料夾）：python 03_程式碼/04_report.py
"""
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
OUT = ROOT / "06_報告" / "互動報告.html"                      # 【輸出】互動報告
OUT.parent.mkdir(exist_ok=True)

cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
df = pd.read_csv(CLEAN_FILE)
log = pd.read_csv(LOG_FILE)
t1 = pd.read_csv(T / "表1_各區描述統計.csv")
t4 = pd.read_csv(T / "表4_卡方檢定.csv").iloc[0]
t5 = pd.read_csv(T / "表5_兩兩比較_Holm校正.csv", dtype={"未校正p值": str, "Holm校正後p值": str})
t6 = pd.read_csv(T / "表6_敏感度分析_考慮月份.csv", dtype={"p值": str}) if (T / "表6_敏感度分析_考慮月份.csv").exists() else None
t7 = pd.read_csv(T / "表7_兩兩比較_考慮月份.csv", dtype={"未校正p值": str, "Holm校正後p值": str}) if (T / "表7_兩兩比較_考慮月份.csv").exists() else None

rows = [[r["月份"], r["行政區"], int(r["篩檢人數"]), int(r["陽性數"]), int(r["人口數"])] for _, r in df.iterrows()]
months = list(pd.period_range(df["月份"].min(), df["月份"].max(), freq="M").strftime("%Y-%m"))
dist = t1[t1["行政區"] != "合計"].copy()
tot = t1[t1["行政區"] == "合計"].iloc[0]


def ptxt(p):
    p = float(p)
    return "p < 0.001" if p < 0.001 else f"p ≈ {p:.3f}"


def mnote(r):
    return f"，只納入 {int(r['納入月數'])} 個月" if int(r["納入月數"]) < len(months) else ""


def wilson_hi(x, n, z=1.96):
    p = x / n; d = 1 + z * z / n
    return ((p + z * z / (2 * n)) + z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d * 100


# ---------- 依資料產生的文字 ----------
by_rate = dist.sort_values("篩檢陽性率(%)", ascending=False)
top2, low = by_rate.head(2), by_rate.iloc[-1]
by_cnt = dist.sort_values("陽性數", ascending=False).head(2)
smallest = dist.sort_values("篩檢人數").iloc[0]
chi_sig = float(t4["p值"]) < 0.05
a, b = top2.iloc[0]["行政區"], top2.iloc[1]["行政區"]
pair = t5[((t5["區A"] == a) & (t5["區B"] == b)) | ((t5["區A"] == b) & (t5["區B"] == a))].iloc[0]
pair_sig = pair["校正後是否顯著(α=0.05)"] == "是"
glm_dist = t6[t6["效果"].str.startswith("行政區")].iloc[0] if t6 is not None else None
glm_sig = glm_dist is not None and float(glm_dist["p值"]) < 0.05
n_sig5 = int((t5["校正後是否顯著(α=0.05)"] == "是").sum())
n_sig7 = int((t7["校正後是否顯著(α=0.05)"] == "是").sum()) if t7 is not None else None
changed = []
if t7 is not None:
    m = t5.merge(t7, on=["區A", "區B"], suffixes=("_5", "_7"))
    changed = [f'{r["區A"]}對{r["區B"]}（{"有差→沒有足夠證據" if r["校正後是否顯著(α=0.05)_5"] == "是" else "沒有足夠證據→有差"}）'
               for _, r in m.iterrows() if r["校正後是否顯著(α=0.05)_5"] != r["校正後是否顯著(α=0.05)_7"]]
sig = t5[t5["校正後是否顯著(α=0.05)"] == "是"].assign(ad=lambda x: x["差(百分點)"].abs()).sort_values("ad")
ns = t5[t5["校正後是否顯著(α=0.05)"] == "否"].assign(ad=lambda x: x["差(百分點)"].abs()).sort_values("ad", ascending=False)
contrast = None
if len(sig) and len(ns):
    s1, n1 = sig.iloc[0], ns.iloc[0]
    contrast = (f'{s1["區A"]}對{s1["區B"]}相差 {abs(s1["差(百分點)"]):.2f} 個百分點，校正後有差（{ptxt(s1["Holm校正後p值"])}）；'
                f'{n1["區A"]}對{n1["區B"]}相差 {abs(n1["差(百分點)"]):.2f} 個百分點，校正後沒有足夠證據（{ptxt(n1["Holm校正後p值"])}）。')
phi = float(t6["模型離散參數φ"].iloc[0]) if t6 is not None else None
if phi is None:
    phi_txt = ""
elif phi > 1.2:
    phi_txt = f"模型離散參數 φ ≈ {phi:.2f}，變異比二項分布預期大，已用 quasi-F 檢定放大不確定性。"
elif phi >= 0.8:
    phi_txt = f"模型離散參數 φ ≈ {phi:.2f}，接近 1，符合二項分布的預期。"
else:
    phi_txt = (f"模型離散參數 φ ≈ {phi:.2f}，明顯小於 1：變異比二項分布預期小，沒有過度離散；"
               "但這也值得追問資料是否經過平滑或不是逐人計數。檢定時不縮小不確定性。")
phi_only = f"只看行政區、不考慮月份時 φ ≈ {float(t6['只看行政區時的φ'].iloc[0]):.2f}。" if t6 is not None else ""
logc = log["問題類型"].value_counts()
n_ex = int(logc.get("缺值", 0) + logc.get("待查", 0))
n_raw = int(len(df) + n_ex + logc.get("完全重複", 0))

summary = [
    f"整體篩檢陽性率 {tot['篩檢陽性率(%)']:.2f}%（{int(tot['陽性數']):,} ／ {int(tot['篩檢人數']):,} 人）。",
    f"篩檢陽性率較高：{a}（{top2.iloc[0]['篩檢陽性率(%)']:.2f}%{mnote(top2.iloc[0])}）、{b}（{top2.iloc[1]['篩檢陽性率(%)']:.2f}%{mnote(top2.iloc[1])}）；"
    f"最低：{low['行政區']}（{low['篩檢陽性率(%)']:.2f}%{mnote(low)}）。",
    f"陽性人數最多的是 {by_cnt.iloc[0]['行政區']}（{int(by_cnt.iloc[0]['陽性數']):,} 人）與 {by_cnt.iloc[1]['行政區']}（{int(by_cnt.iloc[1]['陽性數']):,} 人）：率和人數要一起看。",
    (f"各區差異{'不太可能只是剛好' if chi_sig else '可能只是隨機波動'}（卡方檢定 {ptxt(t4['p值'])}）"
     + (f"，考慮月份後整體差異{'仍然存在' if glm_sig else '不再明顯'}" if glm_dist is not None else "")
     + f"；{a}與{b}之間{'也有差' if pair_sig else '沒有足夠證據說誰比較高'}（校正後 {ptxt(pair['Holm校正後p值'])}）。"),
    "這是「有來篩檢的人」的初篩陽性率，不是盛行率，也不能說明原因；資源配置還需要其他資料。",
]
can = [
    f"每季更新全部 {len(dist)} 區的篩檢陽性率、陽性人數與信賴區間，以整體 {tot['篩檢陽性率(%)']:.2f}% 為參考線比較。",
    f"補查本期被排除的 {n_ex} 列（缺值 {int(logc.get('缺值', 0))} 列、待查 {int(logc.get('待查', 0))} 列），補齊後重算。",
    f"在資料彙整流程加入重複、缺值、寫法不一、陽性數大於篩檢人數的檢查（本期共發現 {len(log)} 筆問題）。",
]
need = [
    f"<b>各區篩檢資源是否調整：</b>率最高的是 {a}、{b}，陽性人數最多的是 {by_cnt.iloc[0]['行政區']}、{by_cnt.iloc[1]['行政區']}，兩者都要考慮；"
    "還需要符合篩檢資格人口的涵蓋率、篩檢對象來源（主動邀約或自行前來）、年齡結構。",
    "<b>各區差異的原因：</b>需要年齡、性別、篩檢管道等變項，以及複檢與確診資料。",
    "<b>月份差異是否為真實季節現象：</b>需要多年資料比較。",
]
uses = [
    "<b>給主管（決策會議）：</b>用「重點摘要」開場，並說清楚「已回答」與「部分回答」的範圍。",
    f"<b>給資料承辦同仁（資料品質）：</b>回饋 {n_ex} 列被排除的資料，請查明原因並補正。",
    "<b>給業務同仁（持續監測）：</b>把各區篩檢陽性率、陽性人數與信賴區間當作每季追蹤指標。",
    "<b>下一期報告：</b>沿用 03_程式碼 與資料夾結構，換上新的原始資料重跑，數字可以前後比較。",
]
read_bar = [
    f"<b>代表：</b>{a}、{b} 有來篩檢的人中，初篩陽性的比例較高；{low['行政區']} 較低。",
    "<b>不代表：</b>某區居民比較容易生病，或某區是「高風險區」。篩檢對象不是隨機抽樣，也沒有年齡資料可以校正。",
    f"<b>要一起看：</b>篩檢人數最少的 {smallest['行政區']}（{int(smallest['篩檢人數']):,} 人）信賴區間較寬；陽性人數與粗篩檢率也不同；各區納入的月數不同。",
]
stats = {"chi2": float(t4["卡方值"]), "dof": int(t4["自由度"]), "pchi": ptxt(t4["p值"]), "minExp": float(t4["最小期望次數"]),
         "pairs": t5.to_dict(orient="records"), "nPairs": len(t5), "nSig": n_sig5,
         "nonsig": [f'{r["區A"]}—{r["區B"]}' for _, r in t5[t5["校正後是否顯著(α=0.05)"] == "否"].iterrows()],
         "glm": None if glm_dist is None else {"method": glm_dist["檢定方法"], "p": ptxt(glm_dist["p值"]), "sig": glm_sig},
         "nSig7": n_sig7, "changed": changed, "pairsAdj": None if t7 is None else t7.to_dict(orient="records"),
         "phiTxt": phi_txt + phi_only, "contrast": contrast, "pair": f"{a}與{b}", "pairSig": pair_sig,
         "pairP": ptxt(pair["Holm校正後p值"]), "log": logc.to_dict(), "nRaw": n_raw, "nDedup": len(df) + n_ex}
ymax = int(math.ceil(max(wilson_hi(r[3], r[2]) for r in rows) / 2.0) * 2)
li = lambda xs: "".join(f"<li>{x}</li>" for x in xs)
qrows = "".join(f'<tr><td>{q}</td><td>{m_}</td><td><span class="chip {"ok" if s == "已回答" else "part"}">{s}</span></td></tr>' for q, m_, s in cfg["問題"])
notes = "".join(f"<li>{x}</li>" for x in cfg.get("補充說明", []))

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
<p class="note">清理時發現：<span id="logtxt"></span>。缺值與待查的列沒有補值或修改，直接排除，所以部分行政區少了幾個月。</p>

<h2 id="desc">描述性統計 <small>各區差多少？</small></h2>
<div class="card">
<div class="row"><b>各區篩檢陽性率</b>
<label>排序 <select id="ord"><option value="code">依區代碼</option><option value="rate">依陽性率由高到低</option></select></label>
<label><input type="checkbox" id="ci" checked> 顯示 95% 信賴區間</label></div>
<div id="bars"></div>
<p class="note">滑鼠移到長條上（手機點一下）看細節；點長條會切換下方的每月趨勢。長條顏色不代表風險等級。區名後的「（9個月）」表示該區只納入幾個月。</p>
<div class="read"><b class="h">怎麼解讀</b><ul>__READBAR__</ul></div>
</div>
<div class="card">
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
<p class="note">粗篩檢率＝納入月份的篩檢人數合計 ÷ 區人口數。人口數是區總人口，不是符合篩檢資格的人口；也無法排除同一人重複受檢；納入月數較少的區會偏低。只能參考。</p></details>
<details class="card"><summary>完整數字：各區每月篩檢陽性率（表3，空白＝該月被排除）</summary><div class="tw"><table id="t3"></table></div>
<p class="row" id="dlrow"><button type="button" class="dl" id="dlcsv">下載圖表用資料（月份、行政區、篩檢人數、陽性數）</button></p></details>

<h2 id="inf">推論性統計 <small>差異是真的，還是只是剛好？</small></h2>
<div class="g2">
<div class="card"><h3>各區是否全部一樣？</h3>
<p>卡方獨立性檢定（各區 × 陽性／陰性）：χ² = <b id="chi"></b>，自由度 <span id="dof"></span>，<span id="pchi"></span>。</p>
<p class="note">假設檢查：最小期望次數 <span id="minexp"></span>（需 ≥ 5）。</p>
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
<div class="warn"><b>資料限制</b><ul>
<li>篩檢對象非隨機抽樣；篩檢陽性率不等於區內盛行率。</li>
<li>陽性為初篩結果，未含確診，也沒有陽性預測值或偽陽性資訊。</li>
<li>資料沒有年齡欄，無法做年齡標準化。</li>
<li>粗篩檢率的分母是區總人口，不是符合篩檢資格的人口，也無法排除重複受檢。</li>
<li>各區納入月數與缺的月份不同；若缺月不是隨機發生，仍可能影響比較。</li>
<li>這是各區的彙總資料，不能用來推論個人（例如「住在某區的人比較容易陽性」）。</li>
<li>只有一年資料，無法判斷長期趨勢；未分析的欄位（例如疫苗接種人數）與本次問題無關，所以沒有使用。</li>
</ul></div>
<details class="card"><summary>方法說明（點開）</summary><ul>
<li><b>篩檢陽性率</b>：陽性數合計 ÷ 篩檢人數合計（先加總人數再相除，不平均百分比）。</li>
<li><b>95% 信賴區間</b>：Wilson 法；未考慮月別群聚，其他方法的數字會略有不同。</li>
<li><b>卡方獨立性檢定</b>：檢定各區陽性率是否全部相同；用人數計算，不用百分比。</li>
<li><b>兩兩比較</b>：2×2 卡方檢定，以 Holm 法校正多重比較，α = 0.05；差異的 95% 信賴區間為 Wald 法（未校正）。</li>
<li><b>敏感度分析</b>：二項式邏輯斯迴歸（行政區＋月份）。離散參數 φ ≤ 1 時用概似比卡方檢定（不縮小不確定性），φ &gt; 1 時用 quasi-F 檢定。考慮月份後的兩兩比較用模型係數做 Wald 檢定，再以 Holm 法校正。</li>
<li><b>對應檔案</b>：程式在 03_程式碼，結果在 04_結果表格（表1–表7）、05_圖表。</li>
</ul></details>

<footer>__FOOTER__</footer>
</main>
<div id="tip" role="status"></div>
<script>
var DATA=__DATA__; /* [月份, 行政區, 篩檢人數, 陽性數, 人口數] */
var STATS=__STATS__;
var YMAX=__YMAX__, ALLOW_DL=__ALLOWDL__, MONTHS=__MONTHS__;
(function(){
 var $=function(s){return document.querySelector(s)},NS="http://www.w3.org/2000/svg";
 function el(n,a,t){var e=document.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;return e}
 function wilson(x,n){var z=1.96,p=x/n,d=1+z*z/n,c=(p+z*z/(2*n))/d,h=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return [(c-h)*100,(c+h)*100]}
 var fmt=function(v){return v.toLocaleString()};
 /* 注意：部分內容以 innerHTML 組字串，目前只放程式算出的數字與固定文字。
    若改成讓使用者匯入任意資料，請先對字串做 HTML 跳脫（escape）。 */
 var months=MONTHS,multiY=months[0].slice(0,4)!==months[months.length-1].slice(0,4),ml=function(k){return multiY?k.slice(2):parseInt(k.slice(5),10)+"月"};
 var by={},tot={s:0,p:0};
 DATA.forEach(function(r){var d=by[r[1]]||(by[r[1]]={name:r[1],s:0,p:0,pop:r[4],m:{}});d.s+=r[2];d.p+=r[3];d.m[r[0]]={s:r[2],p:r[3]};tot.s+=r[2];tot.p+=r[3]});
 var ds=Object.keys(by).sort().map(function(k){var d=by[k];d.rate=d.p/d.s*100;var w=wilson(d.p,d.s);d.lo=w[0];d.hi=w[1];d.months=Object.keys(d.m).length;d.miss=months.filter(function(k){return !d.m[k]}).map(ml);d.cov=d.s/d.pop*100;return d});
 $("#flow").textContent=STATS.nRaw+" → "+STATS.nDedup+" → "+DATA.length;
 $("#c1").textContent=fmt(tot.s);$("#c2").textContent=fmt(tot.p);$("#c3").textContent=(tot.p/tot.s*100).toFixed(2)+"%";
 var L=STATS.log;$("#logtxt").textContent=Object.keys(L).map(function(k){return k+" "+L[k]+" 筆"}).join("、");
 $("#chi").textContent=STATS.chi2.toFixed(1);$("#dof").textContent=STATS.dof;$("#pchi").textContent=STATS.pchi;$("#minexp").textContent=STATS.minExp;
 $("#chiread").textContent=/</.test(STATS.pchi)||parseFloat(STATS.pchi.replace(/[^0-9.]/g,""))<0.05?"各區的篩檢陽性率不太可能全部相同。但這只說明「有差」，不說明哪一區比較嚴重。":"沒有足夠證據說各區不同，差異可能只是隨機波動。";
 $("#np").textContent=STATS.nPairs;$("#nsig").textContent=STATS.nSig;$("#nns").textContent=STATS.nonsig.length;$("#nslist").textContent=STATS.nonsig.join("、")||"（無）";
 $("#pairread").textContent="例如 "+STATS.pair+"："+(STATS.pairSig?"校正後也有差（"+STATS.pairP+"）。":"雖然數字有高低，但差異可能只是隨機波動（校正後 "+STATS.pairP+"）。");
 if(STATS.glm){$("#glmtxt").textContent="敏感度分析（二項式邏輯斯迴歸：行政區＋月份，"+STATS.glm.method+"）：考慮月份後，各區整體差異"+(STATS.glm.sig?"仍然存在":"不再明顯")+"（"+STATS.glm.p+"）。"+(STATS.nSig7!=null?"兩兩比較重做後 "+STATS.nSig7+" 對有差"+(STATS.changed.length?"，結論改變的有："+STATS.changed.join("、"):"，結論與未考慮月份時相同")+"。":"");
  $("#phitxt").textContent=STATS.phiTxt;
  $("#glmread").textContent=STATS.glm.sig?"各區缺的月份不同，但考慮月份後整體差異仍在；個別比較可能略有不同，所以要看表7。若缺月不是隨機發生，仍可能有影響。":"考慮月份後整體差異不再明顯，解讀時要更保守。";}
 else{$("#glmcard").style.display="none";$("#t7wrap").style.display="none";}
 if(STATS.contrast){$("#contrast").textContent=STATS.contrast}else{$("#ctcard").style.display="none"}
 var h="<tr><th>行政區</th><th>納入月數</th><th>缺的月份</th><th>篩檢人數</th><th>粗篩檢率</th><th>陽性數</th><th>篩檢陽性率</th><th>95% 信賴區間</th></tr>";
 ds.forEach(function(d){h+="<tr><td>"+d.name+"</td><td class='n'>"+d.months+"</td><td>"+(d.miss.join("、")||"無")+"</td><td class='n'>"+fmt(d.s)+"</td><td class='n'>"+d.cov.toFixed(1)+"%</td><td class='n'>"+fmt(d.p)+"</td><td class='n'>"+d.rate.toFixed(2)+"%</td><td class='n'>"+d.lo.toFixed(2)+"–"+d.hi.toFixed(2)+"%</td></tr>"});
 var tw=wilson(tot.p,tot.s),pop=ds.reduce(function(a,d){return a+d.pop},0);h+="<tr><td><b>合計</b></td><td class='n'>"+months.length+"</td><td>—</td><td class='n'>"+fmt(tot.s)+"</td><td class='n'>"+(tot.s/pop*100).toFixed(1)+"%</td><td class='n'>"+fmt(tot.p)+"</td><td class='n'>"+(tot.p/tot.s*100).toFixed(2)+"%</td><td class='n'>"+tw[0].toFixed(2)+"–"+tw[1].toFixed(2)+"%</td></tr>";
 $("#t1").innerHTML=h;
 h="<tr><th>行政區</th>"+months.map(function(k){return "<th>"+ml(k)+"</th>"}).join("")+"</tr>";
 ds.forEach(function(d){h+="<tr><td>"+d.name+"</td>"+months.map(function(k){var v=d.m[k];return "<td class='n'>"+(v?(v.p/v.s*100).toFixed(2):"")+"</td>"}).join("")+"</tr>"});
 $("#t3").innerHTML=h;
 h="<tr><th>比較</th><th>差（百分點）</th><th>差的 95% 信賴區間</th><th>未校正 p</th><th>Holm 校正後 p</th><th>校正後有差？</th></tr>";
 STATS.pairs.forEach(function(p){h+="<tr><td>"+p["區A"]+" vs "+p["區B"]+"</td><td class='n'>"+Number(p["差(百分點)"]).toFixed(2)+"</td><td class='n'>"+Number(p["差的95%CI下限"]).toFixed(2)+" 至 "+Number(p["差的95%CI上限"]).toFixed(2)+"</td><td class='n'>"+p["未校正p值"]+"</td><td class='n'>"+p["Holm校正後p值"]+"</td><td>"+p["校正後是否顯著(α=0.05)"]+"</td></tr>"});
 $("#t5").innerHTML=h;
 if(STATS.pairsAdj){h="<tr><th>比較</th><th>校正月份後勝算比</th><th>95% 信賴區間</th><th>未校正 p</th><th>Holm 校正後 p</th><th>校正後有差？</th></tr>";
  STATS.pairsAdj.forEach(function(p){h+="<tr><td>"+p["區A"]+" vs "+p["區B"]+"</td><td class='n'>"+Number(p["校正月份後勝算比"]).toFixed(3)+"</td><td class='n'>"+Number(p["95%CI下限"]).toFixed(3)+"–"+Number(p["95%CI上限"]).toFixed(3)+"</td><td class='n'>"+p["未校正p值"]+"</td><td class='n'>"+p["Holm校正後p值"]+"</td><td>"+p["校正後是否顯著(α=0.05)"]+"</td></tr>"});
  $("#t7").innerHTML=h;}
 if(ALLOW_DL){$("#dlcsv").addEventListener("click",function(){var csv="﻿月份,行政區,篩檢人數,陽性數\n"+DATA.map(function(r){return r.slice(0,4).join(",")}).join("\n");
  var a=document.createElement("a");a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));a.download="chart_data_4cols.csv";document.body.appendChild(a);a.click();a.remove()})}
 else{$("#dlrow").style.display="none"}
 /* 互動圖表：滑鼠用 pointer 事件顯示／隱藏；觸控點一下顯示，點其他地方才收起 */
 var tip=$("#tip"),rebuilding=false;
 function showTip(html,x,y){tip.innerHTML=html;tip.style.display="block";var w=tip.offsetWidth,hh=tip.offsetHeight;
  var left=Math.max(8,Math.min(innerWidth-w-8,x+12)),top=y+14;if(top+hh>innerHeight-8)top=Math.max(8,y-hh-14);tip.style.left=left+"px";tip.style.top=top+"px"}
 function hideTip(){tip.style.display="none"}
 function hover(node,html){node.addEventListener("pointermove",function(e){if(e.pointerType==="mouse")showTip(html,e.clientX,e.clientY)});
  node.addEventListener("pointerleave",function(e){if(e.pointerType==="mouse")hideTip()})}
 var sel=$("#sel");ds.forEach(function(d){var o=document.createElement("option");o.value=d.name;o.textContent=d.name;sel.appendChild(o)});
 var cur=sel.value=ds.slice().sort(function(a,b){return b.rate-a.rate})[0].name;
 var cw=function(id){return Math.max(240,Math.floor($(id).clientWidth||600))};
 function pick(name,x,y,html){cur=name;sel.value=cur;rebuilding=true;bars();line();rebuilding=false;if(x!=null)showTip(html,x,y)}
 function bars(){
  var W=cw("#bars"),small=W<520,Lm=small?112:128,rowH=small?38:36,order=$("#ord").value;
  var arr=ds.slice().sort(order==="rate"?function(a,b){return b.rate-a.rate}:function(a,b){return a.name<b.name?-1:1});
  var H=arr.length*rowH+34,svg=el("svg",{viewBox:"0 0 "+W+" "+H,width:W,height:H,role:"img","aria-label":"各行政區篩檢陽性率長條圖"});
  var showCI=$("#ci").checked,max=Math.max.apply(null,ds.map(function(d){return showCI?d.hi:d.rate}))*1.15,sc=(W-Lm-52)/max;
  for(var t=0;t<=Math.floor(max);t+=2){svg.appendChild(el("line",{x1:Lm+sc*t,x2:Lm+sc*t,y1:4,y2:H-24,"class":"ax"}));svg.appendChild(el("text",{x:Lm+sc*t-8,y:H-6},t+"%"))}
  arr.forEach(function(d,i){var y=6+i*rowH,g=el("g",{"class":"b",tabindex:0,role:"button","aria-label":d.name+" 篩檢陽性率 "+d.rate.toFixed(2)+"%，納入 "+d.months+" 個月"});
   g.appendChild(el("rect",{x:0,y:y-3,width:W,height:rowH-2,"class":"rowhit"}));
   g.appendChild(el("text",{x:2,y:y+rowH/2+3},d.name+(d.months<months.length?"（"+d.months+"個月）":"")));
   g.appendChild(el("rect",{x:Lm,y:y,width:Math.max(1,sc*d.rate),height:rowH-8,rx:3,"class":"bar"+(d.name===cur?" sel":"")}));
   if(showCI)g.appendChild(el("line",{x1:Lm+sc*d.lo,x2:Lm+sc*d.hi,y1:y+(rowH-8)/2,y2:y+(rowH-8)/2,"class":"err"}));
   g.appendChild(el("text",{x:Lm+6+sc*(showCI?d.hi:d.rate),y:y+rowH/2+3},d.rate.toFixed(2)+"%"));
   var html="<b>"+d.name+"</b><br>篩檢人數 "+fmt(d.s)+"<br>陽性數 "+fmt(d.p)+"<br>篩檢陽性率 "+d.rate.toFixed(2)+"%<br>95% 信賴區間 "+d.lo.toFixed(2)+"–"+d.hi.toFixed(2)+"%<br>粗篩檢率 "+d.cov.toFixed(1)+"%<br>納入月數 "+d.months+(d.miss.length?"（缺 "+d.miss.join("、")+"）":"");
   hover(g,html);
   g.addEventListener("focus",function(){var r=g.getBoundingClientRect();showTip(html,r.left+20,r.top)});
   g.addEventListener("blur",function(){if(!rebuilding)hideTip()});
   g.addEventListener("click",function(e){pick(d.name,e.clientX,e.clientY,html)});
   g.addEventListener("keydown",function(e){if(e.key==="Enter"||e.key===" "){e.preventDefault();var r=g.getBoundingClientRect();pick(d.name,r.left+20,r.top,html);var n=document.querySelectorAll("#bars g.b");for(var k=0;k<n.length;k++){if(n[k].getAttribute("aria-label").indexOf(d.name)===0){n[k].focus();break}}}});
   svg.appendChild(g)});
  $("#bars").innerHTML="";$("#bars").appendChild(svg)}
 function line(){
  var d=by[cur],W=cw("#line"),H=260,Lm=44,B=28,n=months.length,svg=el("svg",{viewBox:"0 0 "+W+" "+H,width:W,height:H,role:"img","aria-label":cur+" 每月篩檢陽性率折線圖"});
  var pts=months.map(function(k){var v=d.m[k];if(!v)return null;var w=wilson(v.p,v.s);return {k:k,s:v.s,p:v.p,rate:v.p/v.s*100,lo:w[0],hi:w[1]}});
  var showCI=$("#ci").checked,step=YMAX>10?4:2,small=W<520;
  var X=function(i){return Lm+i*(W-Lm-16)/Math.max(1,n-1)},Y=function(v){return 10+(H-B-10)*(1-v/YMAX)};
  for(var v=0;v<=YMAX;v+=step){svg.appendChild(el("line",{x1:Lm,x2:W-6,y1:Y(v),y2:Y(v),"class":"ax"}));svg.appendChild(el("text",{x:2,y:Y(v)+4},v+"%"))}
  var seg=[];pts.forEach(function(p,i){if(p){seg.push(X(i)+","+Y(p.rate))}else{if(seg.length>1)svg.appendChild(el("polyline",{points:seg.join(" "),"class":"ln"}));seg=[]}});
  if(seg.length>1)svg.appendChild(el("polyline",{points:seg.join(" "),"class":"ln"}));
  pts.forEach(function(p,i){if(!small||i%3===0||i===n-1)svg.appendChild(i===n-1?el("text",{x:W-2,y:H-8,"text-anchor":"end"},ml(months[i])):el("text",{x:X(i)-9,y:H-8},ml(months[i])));
   if(!p){svg.appendChild(el("text",{x:X(i)-5,y:Y(0)-8,style:"font-weight:700"},"×"));return}
   if(showCI)svg.appendChild(el("line",{x1:X(i),x2:X(i),y1:Y(p.lo),y2:Y(Math.min(p.hi,YMAX)),"class":"err"}));
   svg.appendChild(el("circle",{cx:X(i),cy:Y(p.rate),r:5,"class":"dot"}));
   var html="<b>"+cur+"　"+p.k+"</b><br>篩檢人數 "+fmt(p.s)+"<br>陽性數 "+fmt(p.p)+"<br>篩檢陽性率 "+p.rate.toFixed(2)+"%<br>95% 信賴區間 "+p.lo.toFixed(2)+"–"+p.hi.toFixed(2)+"%";
   var c=el("circle",{cx:X(i),cy:Y(p.rate),r:15,"class":"hit",tabindex:0,role:"img","aria-label":cur+" "+p.k+" 篩檢陽性率 "+p.rate.toFixed(2)+"%"});
   hover(c,html);
   c.addEventListener("click",function(e){showTip(html,e.clientX,e.clientY)});
   c.addEventListener("focus",function(){var r=c.getBoundingClientRect();showTip(html,r.left+10,r.top)});c.addEventListener("blur",hideTip);
   svg.appendChild(c)});
  $("#line").innerHTML="";$("#line").appendChild(svg);
  $("#meta").textContent=cur+"：納入 "+d.months+" 個月"+(d.miss.length?"（缺 "+d.miss.join("、")+"）":"")+"，合計篩檢 "+fmt(d.s)+" 人、陽性 "+fmt(d.p)+" 人（"+d.rate.toFixed(2)+"%）"}
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

out = (HTML.replace("__TITLE__", cfg["標題"]).replace("__BANNER__", cfg["頁首註記"]).replace("__STORY__", cfg["情境"])
       .replace("__QROWS__", qrows).replace("__SUMMARY__", li(summary)).replace("__READBAR__", li(read_bar))
       .replace("__NOTES__", notes).replace("__USES__", li(uses)).replace("__CAN__", li(can)).replace("__NEED__", li(need))
       .replace("__FOOTER__", cfg.get("頁尾", "")).replace("__YMAX__", str(ymax))
       .replace("__ALLOWDL__", "true" if cfg.get("提供下載逐列資料", False) else "false")
       .replace("__MONTHS__", json.dumps(months)).replace("__DATA__", json.dumps(rows, ensure_ascii=False))
       .replace("__STATS__", json.dumps(stats, ensure_ascii=False)))
OUT.write_text(out, encoding="utf-8")                       # 【寫出】互動報告
print(f"已輸出 {OUT.relative_to(ROOT)}（{len(out):,} 字元）")
for s in summary:
    print("  ・", s)
