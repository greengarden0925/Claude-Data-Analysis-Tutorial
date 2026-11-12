"""建置所有預先產好的教材：分析成果包、互動報告、第二堂起點包、skill，以及瀏覽頁。

步驟：
  1. 複製髒資料到成果包 01_原始資料/，依序執行成果包內 03_程式碼/01–04
  2. 確認清理結果與 docs/sample-data 的 91 列檔一致；複製互動報告與一頁 Word 摘要
  3. 執行 05_package.py 打包成果包 zip
  4. 產生講義用的推論結果 docs/assets/stats.js
  5. 產生第二堂起點包 zip、同步 skill 的 scripts 並打包 skill zip
  6. 產生瀏覽頁 docs/prebuilt/analysis_package.html
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
PRE = REPO / "docs/prebuilt"
PKG = PRE / "analysis_package/篩檢分析成果包_虛構"
SKILL = REPO / "skill/screening-positivity-analysis"


def zipdir(src: Path, dest: Path):
    if dest.exists():
        dest.unlink()
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(src.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                z.write(p, Path(src.name) / p.relative_to(src))


# 1–3 成果包
for old in (PKG / "01_原始資料").glob("*.csv"):
    old.unlink()
shutil.copy(REPO / "docs/sample-data/demo_fictional_screening_dirty.csv", PKG / "01_原始資料/")
for f in ["01_clean.py", "02_descriptive.py", "03_inferential.py", "04_report.py"]:
    subprocess.run([sys.executable, f"03_程式碼/{f}"], cwd=PKG, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
assert pd.read_csv(PKG / "02_清理後資料/分析用資料.csv").equals(
    pd.read_csv(REPO / "docs/sample-data/demo_fictional_screening_analysis_91rows.csv")), "成果包清理結果與 91 列檔不一致"
shutil.copy(PKG / "06_報告/互動報告.html", PRE / "demo_fictional_interactive_report.html")
shutil.copy(PRE / "demo_fictional_summary_onepage.docx", PKG / "06_報告/一頁摘要_課後用.docx")
subprocess.run([sys.executable, "03_程式碼/05_package.py"], cwd=PKG, check=True, stdout=subprocess.DEVNULL)
shutil.rmtree(PKG / "03_程式碼/__pycache__", ignore_errors=True)

# 4 講義用推論結果
T = PKG / "04_結果表格"
t4 = pd.read_csv(T / "表4_卡方檢定.csv").iloc[0]
t5 = pd.read_csv(T / "表5_兩兩比較_Holm校正.csv")
t6 = pd.read_csv(T / "表6_敏感度分析_考慮月份.csv")
t7 = pd.read_csv(T / "表7_兩兩比較_考慮月份.csv")
ns = t5[t5["校正後是否顯著(α=0.05)"] == "否"]
m = t5.merge(t7, on=["區A", "區B"], suffixes=("_5", "_7"))
changed = [f'{a}對{b}' for a, b, x, y in zip(m["區A"], m["區B"], m["校正後是否顯著(α=0.05)_5"], m["校正後是否顯著(α=0.05)_7"]) if x != y]
stats = {"chi2": round(float(t4["卡方值"]), 1), "dof": int(t4["自由度"]), "minExp": float(t4["最小期望次數"]),
         "nPairs": len(t5), "nSig": int(len(t5) - len(ns)), "nonsig": [f'{a}—{b}' for a, b in zip(ns["區A"], ns["區B"])],
         "phi": float(t6["模型離散參數φ"].iloc[0]), "phiDistOnly": float(t6["只看行政區時的φ"].iloc[0]),
         "glmMethod": t6["檢定方法"].iloc[0], "nSig7": int((t7["校正後是否顯著(α=0.05)"] == "是").sum()), "changed": changed}
(REPO / "docs/assets/stats.js").write_text("window.STATS = " + json.dumps(stats, ensure_ascii=False) + ";\n", encoding="utf-8")

# 5a 第二堂起點包
start = REPO / "build_tmp/第二堂起點包"
shutil.rmtree(start.parent, ignore_errors=True); start.mkdir(parents=True)
shutil.copy(PKG / "02_清理後資料/分析用資料.csv", start / "分析用資料_91列.csv")
shutil.copy(PKG / "00_分析計畫/分析計畫.md", start / "分析計畫.md")
(start / "接續說明.md").write_text("""# 第二堂起點包（虛構資料）

第一堂沒做完、或第二堂要開新對話時使用。

1. 開新對話，上傳這個資料夾裡的 `分析用資料_91列.csv` 與 `分析計畫.md`。
2. 貼上講義「第二堂・模組 4」的「接續提示詞」（重新講好背景與工作規則）。
3. 從描述性統計開始。

注意：本資料為電腦隨機產生的虛構資料，甲縣、A–H 區皆為代號。
""", encoding="utf-8")
zipdir(start, PRE / "第二堂起點包.zip")
shutil.rmtree(start.parent)

# 5b skill：同步程式並打包
for p in (SKILL / "scripts").glob("*.py"):
    p.unlink()
for p in (PKG / "03_程式碼").glob("*.py"):
    shutil.copy(p, SKILL / "scripts" / p.name)
(PRE / "skill").mkdir(exist_ok=True)
zipdir(SKILL, PRE / "skill/screening-positivity-analysis.zip")

# 6 瀏覽頁
desc = {"00_分析計畫": "分析計畫、報告設定", "01_原始資料": "原始資料（永遠不修改）",
        "02_清理後資料": "分析用資料（91 列）、修正與排除紀錄", "03_程式碼": "依編號順序執行的程式碼（最上方寫明輸入與輸出）",
        "04_結果表格": "表1–表7", "05_圖表": "圖1–圖2", "06_報告": "互動報告、一頁 Word 摘要（課後用）"}
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
<body><header class="top"><div class="top-in"><b>分析成果包</b><a href="../index.html">← 回講義</a><a href="#tree">資料夾</a><a href="#code">怎麼看程式碼</a><a href="#plan">分析計畫</a></div></header>
<main><section class="hero"><h1>篩檢分析成果包（虛構資料）</h1>
<p>示範一次完整分析的檔案怎麼分資料夾擺放。所有資料皆為電腦隨機產生，甲縣、A–H 區皆為代號。</p>
<p><a class="btn" href="analysis_package/{PKG.name}.zip" download>⬇ 下載整包（zip）</a>
<a class="btn alt" href="demo_fictional_interactive_report.html" target="_blank" rel="noopener">▶ 開啟互動報告</a></p>
<p class="see">若解壓縮後中文檔名變成亂碼，請改用支援 UTF-8 檔名的解壓縮工具。本包含原始與逐列資料：換成真實資料時，傳遞前請依單位規定處理。</p></section>
<h2 id="tree">資料夾與檔案</h2><div class="card"><ul class="tree">{''.join(tree)}<li><a href="analysis_package/{PKG.name}/README.md">README.md</a>　<span class="m">資料夾說明與執行順序</span></li></ul></div>
<h2 id="code">怎麼看程式碼（不用會寫程式）</h2><div class="card">
<p>打開 <a href="analysis_package/{PKG.name}/03_程式碼/01_clean.py">01_clean.py</a>，只看三件事：</p>
<ol><li><b>讀哪個檔</b>：最上方標著【輸入】的那幾行。</li><li><b>有沒有改原始檔</b>：標著【寫出】的那幾行，路徑都不是 01_原始資料。</li><li><b>存到哪裡</b>：【寫出】後面的資料夾名稱。</li></ol>
<p class="see">統計方法對不對，不用從程式碼判斷；請 Claude 用白話回答「這段程式用人數還是百分比做檢定？有沒有做多重比較校正？」</p></div>
<h2>README</h2><div class="card md tw">{readme_html}</div>
<h2 id="plan">分析計畫</h2><div class="card md tw">{plan_html}</div>
<footer>教學用途。資料皆為虛構。<a href="../index.html">回講義</a></footer></main></body></html>"""
(PRE / "analysis_package.html").write_text(page, encoding="utf-8")
print("done;", json.dumps(stats, ensure_ascii=False))
