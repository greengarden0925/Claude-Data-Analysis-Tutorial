# Claude 辦公實戰：讓資料分析與報告製作更快、更簡單

給公共衛生師的 60 分鐘實作課講義，以 Dashboard 網頁呈現，Step by step 操作。

網站：https://greengarden0925.github.io/Claude-Data-Analysis-Tutorial/

## 內容
- `docs/index.html`：學員講義 Dashboard（提示詞可一鍵複製）
- `docs/instructor.html`：講師頁（逐分鐘腳本、預期故障、設計取捨、優化建議）
- `docs/assets/`：共用樣式與預先計算的示範結果
- `docs/sample-data/`（全部為虛構資料）
  - `demo_fictional_screening_dirty.csv`：髒資料 99 列（學員上傳用）
  - `demo_fictional_screening_analysis_91rows.csv`：依講義規則清理後的分析用資料 91 列
  - `demo_fictional_screening_clean_96rows.csv`：汙染前的原始 96 列（解答）
- `docs/prebuilt/`：預先產好的輸出（修正與排除紀錄 CSV、長條圖 PNG、一頁 Word 摘要 DOCX），給無法使用檔案建立功能的學員
- `scripts/make_sample_data.py`：資料產生腳本（固定亂數種子，可重現）
- `scripts/make_prebuilt_outputs.py`：預先產好輸出的腳本（需 python-docx、matplotlib）
- `review/reviewers.md`：教材 AI 審查小組設計（五種審查角色，可重複使用）

## 本機預覽
直接用瀏覽器開啟 `docs/index.html`。

## 發佈
GitHub Pages：Settings → Pages → Source 選 Deploy from a branch，Branch 選 `main`，資料夾選 `/docs`，按 Save。

## 注意
所有資料皆為電腦隨機產生的虛構資料（A–H 區為代號），不代表任何真實地區或個案。工具介面與功能以開課當天實際畫面與官方說明為準。
