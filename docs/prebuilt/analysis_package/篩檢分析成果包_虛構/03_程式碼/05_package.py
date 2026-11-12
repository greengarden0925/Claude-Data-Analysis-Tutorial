"""步驟 5：檢查資料夾並打包成 zip

檢查 00–06 資料夾與 README.md 是否齊全，印出樹狀圖，並把成果包打包成 zip。
只打包：00–06 資料夾內常見類型的檔案，以及最上層的 README.md。
不打包：隱藏檔（. 開頭）、暫存檔（~ 開頭）、捷徑（符號連結）、__pycache__、其他類型的檔案（會列出來給你確認）。
提醒：成果包含原始資料與逐列資料；真實資料打包後，請依單位規定存放與傳遞，給主管通常只需要 06_報告。
執行方式（在成果包最上層資料夾）：python 03_程式碼/05_package.py
"""
import zipfile
from pathlib import Path

# ===== 輸入與輸出：看程式碼時先檢查這裡 =====
ROOT = Path(__file__).resolve().parents[1]                 # 【輸入】整個成果包資料夾（只讀）
ZIP = ROOT.parent / f"{ROOT.name}.zip"                      # 【寫出】zip 檔（放在成果包的上一層）

FOLDERS = ["00_分析計畫", "01_原始資料", "02_清理後資料", "03_程式碼", "04_結果表格", "05_圖表", "06_報告"]
OK_EXT = {".md", ".json", ".csv", ".py", ".png", ".html", ".docx", ".xlsx", ".pptx", ".pdf", ".txt"}


def wanted(p: Path):
    rel = p.relative_to(ROOT)
    if p.is_symlink() or any(part.startswith((".", "~")) or part == "__pycache__" for part in rel.parts):
        return False
    if rel.parts == ("README.md",):
        return True
    return rel.parts[0] in FOLDERS and p.suffix.lower() in OK_EXT


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
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:                # 【寫出】zip
    for p in keep:
        z.write(p, Path(ROOT.name) / p.relative_to(ROOT))
print(f"已打包：{ZIP.name}（{len(keep)} 個檔案）")
