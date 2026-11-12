"""產生「預先產好的輸出」，給無法使用檔案建立功能的學員做閱讀與查核。全部為虛構資料。
輸出（docs/prebuilt/）：
  demo_fictional_cleaning_log.csv       修正與排除紀錄
  demo_fictional_positivity_by_district.png  各區篩檢陽性率長條圖（學員版 91 列）
  demo_fictional_summary_onepage.docx   一頁式 Word 摘要
用法：先跑 make_sample_data.py，再 python3 scripts/make_prebuilt_outputs.py
"""
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from docx import Document
from docx.shared import Pt, Cm
from docx.oxml.ns import qn

SD, OUT = "docs/sample-data/", "docs/prebuilt/"
S = json.loads(open("docs/assets/data.js", encoding="utf-8").read().split("=", 1)[1].rstrip(";\n"))

# ---------- 1. 修正與排除紀錄 ----------
raw = pd.read_csv(SD + "demo_fictional_screening_dirty.csv", dtype=str)
raw["列號"] = raw.index + 2          # CSV 檔列號（標題列為第 1 列）
valid = {f"{c}區" for c in "ABCDEFGH"}
log = []
seen = set()
for _, r in raw.iterrows():
    key = tuple(r[["月份", "行政區", "人口數", "篩檢人數", "陽性數", "疫苗接種人數"]].fillna("").tolist())
    if key in seen:
        log.append((r["列號"], r["月份"], r["行政區"], "完全重複", "整列重複", "刪除（保留第一筆）", "與先前列完全相同"))
    seen.add(key)
    if r["行政區"] not in valid:
        new = r["行政區"].replace(" ", "").upper()
        log.append((r["列號"], r["月份"], r["行政區"], "行政區寫法不一", r["行政區"], f"改為 {new}", "統一為「X區」格式"))
    if "/" in r["月份"]:
        y, m = r["月份"].split("/")
        log.append((r["列號"], r["月份"], r["行政區"], "月份格式不一", r["月份"], f"改為 {y}-{int(m):02d}", "統一為 YYYY-MM"))
    if pd.isna(r["篩檢人數"]):
        log.append((r["列號"], r["月份"], r["行政區"], "缺值", "（空白）", "不補值；排除，不放入分析用資料", "篩檢人數缺值，無法計算陽性率"))
    elif int(r["陽性數"]) > int(r["篩檢人數"]):
        log.append((r["列號"], r["月份"], r["行政區"], "待查", f"陽性 {r['陽性數']} > 篩檢 {r['篩檢人數']}", "不修改；標記待查並排除", "陽性數不可能大於篩檢人數，應回頭問承辦人"))
pd.DataFrame(log, columns=["CSV列號", "月份", "行政區", "問題類型", "原值", "處理方式", "原因"]) \
  .to_csv(OUT + "demo_fictional_cleaning_log.csv", index=False, encoding="utf-8-sig")
assert len(log) == 12, len(log)   # 3 重複 + 2 寫法 + 2 月份 + 4 缺值 + 1 待查

# ---------- 2. 長條圖 ----------
zh = next(f for f in fm.findSystemFonts() if "wqy-zenhei" in f.lower() or "wenquanyi" in f.lower())
fm.fontManager.addfont(zh); plt.rcParams["font.family"] = fm.FontProperties(fname=zh).get_name()
ds = sorted(S["districts91"], key=lambda d: -d["rate"])
fig, ax = plt.subplots(figsize=(7, 4), dpi=200)
y = range(len(ds))[::-1]
cols = ["#b91c1c" if i < 2 else "#0f766e" for i in range(len(ds))]
ax.barh(list(y), [d["rate"] for d in ds], color=cols)
ax.errorbar([d["rate"] for d in ds], list(y),
            xerr=[[d["rate"] - d["lo"] for d in ds], [d["hi"] - d["rate"] for d in ds]],
            fmt="none", ecolor="#1c2430", capsize=3, lw=1.2)
ax.set_yticks(list(y)); ax.set_yticklabels([d["name"] for d in ds])
for yy, d in zip(y, ds): ax.text(d["hi"] + .15, yy, f'{d["rate"]:.2f}%', va="center", fontsize=9)
ax.set_xlabel("篩檢陽性率（%）"); ax.set_xlim(0, 12)
ax.set_title("各行政區篩檢陽性率（虛構資料，2025 年，學員版 91 列）", fontsize=11)
ax.spines[["top", "right"]].set_visible(False)
fig.text(0.01, 0.01, "橫線為 95% 信賴區間（Wilson 法）。B區納入 9 個月、A區與H區 11 個月，其餘 12 個月。篩檢對象非隨機抽樣，未年齡標準化。", fontsize=6.5, color="#5b6675")
fig.tight_layout(rect=(0, .04, 1, 1)); fig.savefig(OUT + "demo_fictional_positivity_by_district.png"); plt.close(fig)

# ---------- 3. 一頁 Word 摘要 ----------
d = {x["name"]: x for x in S["districts91"]}
H, E, B = d["H區"], d["E區"], d["B區"]
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)   # A4
sec.top_margin = sec.bottom_margin = Cm(1.6); sec.left_margin = sec.right_margin = Cm(2)
def font(run, size=10, bold=False):
    run.font.size = Pt(size); run.bold = bold; run.font.name = "Microsoft JhengHei"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
def para(text="", size=10, bold=False, space=2):
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(space); p.paragraph_format.space_before = Pt(0)
    if text: font(p.add_run(text), size, bold)
    return p
def bullet(text):
    p = doc.add_paragraph(style="List Bullet"); p.paragraph_format.space_after = Pt(1)
    font(p.add_run(text), 9.5); return p
t = para("2025 年度篩檢成果摘要（虛構資料）", 16, True, 4)
para("篩檢項目：虛構的成人健康篩檢｜對象：30 歲以上成人｜資料期間：2025 年 1–12 月｜資料截止日：2026-01-31｜資料來源：示範資料（虛構，A–H 區為代號）", 8.5, False, 6)
para("一、重點發現", 11, True, 2)
bullet(f"篩檢陽性率最高的是 H區（{H['rate']:.2f}%，{H['positive']:,}／{H['screened']:,}）與 E區（{E['rate']:.2f}%），高於整體的 {S['total91']['rate']:.2f}%。")
bullet(f"H區與 E區的 95% 信賴區間有重疊（{H['lo']:.2f}–{H['hi']:.2f}% 對 {E['lo']:.2f}–{E['hi']:.2f}%），雙比例檢定 p≈0.13，無法確認 H區高於 E區。")
bullet(f"B區篩檢陽性率最低（{B['rate']:.2f}%），但只納入 {B['months']} 個月，與其他區不能嚴格比較。")
para("二、各區篩檢陽性率", 11, True, 2)
doc.add_picture(OUT + "demo_fictional_positivity_by_district.png", width=Cm(11.5))
doc.paragraphs[-1].paragraph_format.space_after = Pt(2)
para("三、建議行動", 11, True, 2)
para("可由數據支持：", 9.5, True, 1)
bullet("持續監測 H區與 E區的篩檢陽性率，並於下一期資料更新後重新比較。")
bullet("補查 B區 2025-04 的待查資料（陽性數大於篩檢人數）與 4 筆篩檢人數缺值，補齊後重算。")
para("需進一步查證：", 9.5, True, 1)
bullet("是否調整 H區、E區的篩檢資源：需先了解各區篩檢對象來源、年齡結構與篩檢涵蓋率，目前資料無法回答。")
para("四、資料限制", 11, True, 2)
for s in [f"清理後共排除 5 列（4 列篩檢人數缺值、1 列待查），分析用資料 {S['rows_analysis']} 列；各區納入月數不同（B區 9 個月、A區與H區 11 個月，其餘 12 個月）。",
          "篩檢對象非隨機抽樣，篩檢陽性率不等於區內盛行率；陽性為初篩結果，未含確診；未做年齡標準化。",
          "實務上最近 1–2 個月可能因通報延遲偏低，應標示暫定（示範資料未模擬此現象）。",
          "本文件所有資料皆為電腦隨機產生的虛構資料，不代表任何真實地區或個案。"]:
    bullet(s)
doc.save(OUT + "demo_fictional_summary_onepage.docx")
print("done", len(log))
