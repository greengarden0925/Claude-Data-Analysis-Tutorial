"""建置「篩檢分析成果包（虛構）」並產生瀏覽頁與 zip。

步驟：
  1. 複製髒資料到成果包 01_原始資料/
  2. 依序執行成果包內 03_程式碼/01_clean.py、02_descriptive.py、03_inferential.py
  3. 產生互動報告（scripts/make_interactive_report.py），複製一頁 Word 摘要到 06_報告/
  4. 產生講義用的推論結果 docs/assets/stats.js
  5. 產生瀏覽頁 docs/prebuilt/analysis_package.html 與 zip
需要：pandas、scipy、matplotlib、statsmodels、python-docx、markdown
用法（repo 最上層）：先跑 make_sample_data.py、make_prebuilt_outputs.py，再跑本程式。
"""
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
import markdown
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs/prebuilt/analysis_package/篩檢分析成果包_虛構"
ZIP = REPO / "docs/prebuilt/analysis_package/篩檢分析成果包_虛構.zip"
BROWSE = REPO / "docs/prebuilt/analysis_package.html"

shutil.copy(REPO / "docs/sample-data/demo_fictional_screening_dirty.csv", PKG / "01_原始資料/")
for f in ["01_clean.py", "02_descriptive.py", "03_inferential.py"]:
    subprocess.run([sys.executable, f"03_程式碼/{f}"], cwd=PKG, check=True, stdout=subprocess.DEVNULL)
shutil.rmtree(PKG / "03_程式碼/__pycache__", ignore_errors=True)
assert pd.read_csv(PKG / "02_清理後資料/分析用資料.csv").equals(
    pd.read_csv(REPO / "docs/sample-data/demo_fictional_screening_analysis_91rows.csv")), "成果包清理結果與 91 列檔不一致"
subprocess.run([sys.executable, "scripts/make_interactive_report.py"], cwd=REPO, check=True)
shutil.copy(REPO / "docs/prebuilt/demo_fictional_summary_onepage.docx", PKG / "06_報告/一頁摘要_課後用.docx")

# 講義用的推論結果
T = PKG / "04_結果表格"
t4 = pd.read_csv(T / "表4_卡方檢定.csv").iloc[0]
t5 = pd.read_csv(T / "表5_兩兩比較_Holm校正.csv")
t6 = pd.read_csv(T / "表6_敏感度分析_考慮月份.csv")
ns = t5[t5["校正後是否顯著(α=0.05)"] == "否"]
stats = {"chi2": round(float(t4["卡方值"]), 1), "dof": int(t4["自由度"]), "minExp": float(t4["最小期望次數"]),
         "nPairs": len(t5), "nSig": int(len(t5) - len(ns)),
         "nonsig": [f'{a}—{b}' for a, b in zip(ns["區A"], ns["區B"])],
         "phi": float(t6["模型離散參數φ"].iloc[0]), "phiDistOnly": float(t6["只看行政區時的φ"].iloc[0])}
(REPO / "docs/assets/stats.js").write_text("window.STATS = " + json.dumps(stats, ensure_ascii=False) + ";\n", encoding="utf-8")

# zip（含 UTF-8 檔名）
if ZIP.exists():
    ZIP.unlink()
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(PKG.rglob("*")):
        if p.is_file():
            z.write(p, Path(PKG.name) / p.relative_to(PKG))

# 瀏覽頁
desc = {"00_分析計畫": "分析計畫：情境、問題、方法、假設檢查、不能回答的問題、結果摘要",
        "01_原始資料": "原始資料（永遠不修改）", "02_清理後資料": "分析用資料（91 列）、修正與排除紀錄",
        "03_程式碼": "依編號順序執行的程式碼", "04_結果表格": "表1–表6", "05_圖表": "圖1–圖2",
        "06_報告": "互動報告、一頁 Word 摘要（課後用）"}
tree = []
for d in sorted(p for p in PKG.iterdir() if p.is_dir()):
    items = "".join(f'<li><a href="analysis_package/{PKG.name}/{d.name}/{f.name}">{f.name}</a></li>'
                    for f in sorted(d.iterdir()) if f.is_file())
    tree.append(f"<li><b>{d.name}/</b>　<span class='m'>{desc.get(d.name, '')}</span><ul>{items}</ul></li>")
readme_html = markdown.markdown((PKG / "README.md").read_text(encoding="utf-8"), extensions=["tables", "fenced_code"])
plan_html = markdown.markdown((PKG / "00_分析計畫/分析計畫.md").read_text(encoding="utf-8"), extensions=["tables"])
page = f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>分析成果包（虛構資料）</title><link rel="stylesheet" href="../assets/style.css">
<style>.m{{color:var(--mute);font-size:14px}} ul.tree ul{{margin:4px 0 10px}} .md table{{margin:8px 0}} .md td,.md th{{white-space:normal}}</style></head>
<body><header class="top"><div class="top-in"><b>分析成果包</b><a href="../index.html">← 回講義</a><a href="#tree">資料夾</a><a href="#plan">分析計畫</a></div></header>
<main><section class="hero"><h1>篩檢分析成果包（虛構資料）</h1>
<p>示範一次完整分析的檔案怎麼分資料夾擺放。所有資料皆為電腦隨機產生，A–H 區為代號。</p>
<p><a class="btn" href="analysis_package/{ZIP.name}" download>⬇ 下載整包（zip）</a>
<a class="btn alt" href="demo_fictional_interactive_report.html" target="_blank" rel="noopener">▶ 開啟互動報告</a></p>
<p class="see">若解壓縮後中文檔名變成亂碼，請改用支援 UTF-8 檔名的解壓縮工具。</p></section>
<h2 id="tree">資料夾與檔案</h2><div class="card"><ul class="tree">{''.join(tree)}<li><a href="analysis_package/{PKG.name}/README.md">README.md</a>　<span class="m">資料夾說明與執行順序</span></li></ul></div>
<h2>README</h2><div class="card md tw">{readme_html}</div>
<h2 id="plan">分析計畫</h2><div class="card md tw">{plan_html}</div>
<footer>教學用途。資料皆為虛構。<a href="../index.html">回講義</a></footer></main></body></html>"""
BROWSE.write_text(page, encoding="utf-8")
print("done:", ZIP.name, ZIP.stat().st_size, "bytes;", json.dumps(stats, ensure_ascii=False))
