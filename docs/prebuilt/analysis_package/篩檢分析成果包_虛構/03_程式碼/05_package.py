"""步驟 5：檢查資料夾並打包成 zip

檢查 00–06 資料夾與 README.md 是否齊全，印出樹狀圖，並把成果包打包成 zip。
只打包（各資料夾只收約定好的檔案）：
  00_分析計畫：分析計畫.md、報告設定.json；01_原始資料：1 個 .csv；02_清理後資料：分析用資料.csv、修正與排除紀錄.csv；
  03_程式碼：01_clean～05_package 與 _common.py；04_結果表格：表1～表7 的 .csv；05_圖表：圖1～圖n 的 .png；
  06_報告：互動報告.html、一頁摘要_課後用.docx；最上層：README.md
不打包：隱藏檔（. 開頭）、暫存檔（~ 開頭）、捷徑（符號連結）、__pycache__、.xlsx／.txt／.pdf 等其他檔案、不符合上述約定的檔案
（全部會列出來給你確認；真的需要的話，請自己決定是否另外加進去）。
提醒：成果包含原始資料與逐列資料；真實資料打包後，請依單位規定存放與傳遞，給主管通常只需要 06_報告。
執行方式（在成果包最上層資料夾）：python 03_程式碼/05_package.py
"""
import re
import zipfile
from pathlib import Path

# ===== 輸入與輸出：看程式碼時先檢查這裡 =====
ROOT = Path(__file__).resolve().parents[1]                 # 【輸入】整個成果包資料夾（只讀）
ZIP = ROOT.parent / f"{ROOT.name}.zip"                      # 【寫出】zip 檔（放在成果包的上一層）

FOLDERS = ["00_分析計畫", "01_原始資料", "02_清理後資料", "03_程式碼", "04_結果表格", "05_圖表", "06_報告"]
RULES = {"00_分析計畫": {".md", ".json"}, "01_原始資料": {".csv"}, "02_清理後資料": {".csv"}, "03_程式碼": {".py"},
         "04_結果表格": {".csv"}, "05_圖表": {".png"}, "06_報告": {".html", ".docx"}}
# 約定的檔名（01_原始資料 的 CSV 檔名由使用者決定，只限 1 個）
NAMES = {"00_分析計畫": {"分析計畫.md", "報告設定.json"},
         "02_清理後資料": {"分析用資料.csv", "修正與排除紀錄.csv"},
         "03_程式碼": {"01_clean.py", "02_descriptive.py", "03_inferential.py", "04_report.py", "05_package.py", "_common.py"},
         "06_報告": {"互動報告.html", "一頁摘要_課後用.docx"}}
PREFIX = {"04_結果表格": re.compile(r"^表[1-7]_.+\.csv$"), "05_圖表": re.compile(r"^圖[1-9]_.+\.png$")}


def wanted(p: Path):
    rel = p.relative_to(ROOT)
    if p.is_symlink() or any(part.startswith((".", "~")) or part == "__pycache__" for part in rel.parts):
        return False
    if rel.parts == ("README.md",):
        return True
    if rel.parts[0] not in RULES or p.suffix.lower() not in RULES[rel.parts[0]] or len(rel.parts) != 2:
        return False
    if rel.parts[0] in NAMES:
        return rel.name in NAMES[rel.parts[0]]
    if rel.parts[0] in PREFIX:
        return bool(PREFIX[rel.parts[0]].match(rel.name))
    return True


missing = [d for d in FOLDERS if not (ROOT / d).is_dir()] + ([] if (ROOT / "README.md").exists() else ["README.md"])
print("缺少：" + "、".join(missing) if missing else "資料夾與 README.md 齊全")
files = [p for p in sorted(ROOT.rglob("*")) if p.is_file() or p.is_symlink()]
keep = [p for p in files if wanted(p)]
skipped = [p for p in files if p not in keep]
print(f"{ROOT.name}/")
for p in keep:
    rel = p.relative_to(ROOT)
    print("    " * (len(rel.parts) - 1) + "    " + "/".join(rel.parts[-1:]) + ("" if len(rel.parts) == 1 else f"    （{rel.parts[0]}）"))
if skipped:
    print("沒有打包的檔案（請確認是否需要）：" + "、".join(str(p.relative_to(ROOT)) for p in skipped))
raws = [p for p in keep if p.relative_to(ROOT).parts[0] == "01_原始資料"]
if len(raws) != 1:
    print(f"提醒：01_原始資料 裡有 {len(raws)} 個 CSV，約定只放 1 個。")
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:                # 【寫出】zip
    for p in keep:
        z.write(p, Path(ROOT.name) / p.relative_to(ROOT))
print(f"已打包：{ZIP}（{len(keep)} 個檔案）")
if ZIP.exists():
    print("注意：如果同名 zip 原本就存在，已被這次的內容覆蓋。")
