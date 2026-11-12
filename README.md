# Claude 辦公實戰：讓資料分析與報告製作更快、更簡單

給公共衛生師的 60 分鐘實作課講義，以 Dashboard 網頁呈現，Step by step 操作。
從一個小故事出發：先想清楚為什麼要分析 → 請 AI 建議從描述性到推論性的分析計畫並確認方法 → 每一步先看程式碼再執行 → 產出互動報告 → 所有檔案分資料夾歸檔。

網站：https://greengarden0925.github.io/Claude-Data-Analysis-Tutorial/

## 內容
- `docs/index.html`：學員講義 Dashboard（提示詞可一鍵複製）
- `docs/instructor.html`：講師頁（逐分鐘腳本、預期故障、設計取捨、優化建議）
- `docs/prebuilt/demo_fictional_interactive_report.html`：互動報告範例（單一 HTML、資料內嵌、不連外部網路）
- `docs/prebuilt/analysis_package.html`：分析成果包瀏覽頁；成果包本體與 zip 在 `docs/prebuilt/analysis_package/`
  - `00_分析計畫`、`01_原始資料`、`02_清理後資料`、`03_程式碼`、`04_結果表格`、`05_圖表`、`06_報告`、`README.md`
  - `03_程式碼` 內是可實際執行的 Python 程式（清理、描述性統計、推論性統計）
- `docs/prebuilt/`：其他預先產好的輸出（修正與排除紀錄、長條圖、一頁 Word 摘要）
- `docs/sample-data/`（全部為虛構資料）：髒資料 99 列、分析用 91 列、汙染前原始 96 列
- `docs/assets/`：共用樣式、講義用的預先計算結果（data.js、stats.js）
- `scripts/`：產生上述檔案的程式（固定亂數種子，可重現）
- `review/reviewers.md`：教材 AI 審查小組設計（五種審查角色，可重複使用）

## 重新產生所有檔案
需要 Python 3 與 pandas、scipy、statsmodels、matplotlib、python-docx、markdown。在 repo 最上層依序執行：
```
python3 scripts/make_sample_data.py
python3 scripts/make_prebuilt_outputs.py
python3 scripts/make_analysis_package.py   # 會執行成果包內的程式、產生互動報告、zip 與瀏覽頁
```

## 發佈
GitHub Pages：Settings → Pages → Source 選 Deploy from a branch，Branch 選 `main`，資料夾選 `/docs`。`docs/.nojekyll` 讓檔案原樣提供（不經 Jekyll 轉換）。

## 注意
所有資料皆為電腦隨機產生的虛構資料（A–H 區為代號），故事中的人物與機關皆為虛構，不代表任何真實地區、機關或個案。工具介面與功能以開課當天實際畫面與官方說明為準。
