# Timing Charts（タイミングチャート）

[English](README.md) | 日本語

**職場にAIコーディングツールがなくても使えるタイミングチャートメーカー — 必要なのはブラウザのチャットボット（Copilot web、ChatGPTなど）とPython 3.10以上だけ。**

AIが生成したタイミングチャート（デジタル波形＋アナログ曲線）をローカルでプレビューし、CSVに書き出します。`chatbot.md` のプロンプトを使ってチャットボットにチャートを説明してもらい、生成された `.py` ファイルを `timing_charts/` に保存すれば、`charts.py` でプレビューとCSV保存ができます。

## 構成

| ファイル/フォルダ | 役割 |
|------------------|------|
| `chatbot.md`     | Copilotに貼り付けるプロンプト（冒頭の説明を参照） |
| `timing_charts/` | チャートごとに `timingchart_<名前>.py` を1つ（.gitignoreで除外） |
| `charts.py`      | チャートの一覧表示・プレビュー・CSV保存 |
| `chartlib.py`    | チャートビルダー＋描画＋CSVエンジン |

## 初回セットアップ（Windows、Python 3.10以上）

リポジトリのルートで実行します。

**cmd の場合：**
```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**PowerShell の場合：**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

メモ：
- `py` ランチャーを使う場合は `py -3.10 -m venv .venv`（インストール済みのどのバージョンでも動作します。3.10ぴったりである必要はありません）。
- PowerShell のみ：`Activate.ps1` がスクリプト実行ポリシーでブロックされた場合は、次を一度だけ実行してから再試行してください：
  `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- プロンプトの先頭が `(.venv)` になっていれば仮想環境は有効です。なっていない場合は、そこで中止してください — このまま続けるとインストール先がグローバルPythonになってしまいます。

セットアップの確認：`python charts.py` でチャート一覧が表示され、番号を選ぶとプレビューウィンドウが開けばOKです。（新規クローン直後はチャートが1つもありません — まず `chatbot.md` に従って最初の1つを作成してください。）

## 日常の使い方

1. `chatbot.md` の冒頭に従います：Copilotにチャートを説明し、プロンプトを貼り付け、結果を `timing_charts/timingchart_<名前>.py` として保存します。
2. `python charts.py` を実行します。
3. チャートの番号を入力するとプレビューウィンドウが開きます。
4. `Save to CSV? (y/n)` で `y` を入力すると `timing_charts/<名前>.csv` が保存されます。

## CSVフォーマット

ワイド形式：`time` 列＋信号ごとの列 — 信号が何個あっても各信号に1列ずつです。行はすべての遷移/サンプル時刻の和集合で、各値は信号が次に変化するまで保持される（ホールド）ため、どの列も `time` に対してExcelでそのままプロットできます。信号の最初の遷移より前は最初の値がさかのぼって繰り返され、最後の遷移より後は最後の値が範囲の終わりまで繰り返されます。

```csv
time,clk,sin
0,1,0.0
0.002,1,0.125333
0.004,1,0.24869
...
0.02,0,0.951057
```

## トラブルシューティング

- **一覧でチャートに ✗ エラーが表示される** — ファイルが不正です。エラーメッセージをそのままCopilotのチャットに貼り、ファイル全体の再生成を依頼してください。
- **`python` が認識されない** — `py` ランチャーを使うか、「Add to PATH」を有効にしてPythonを再インストールしてください。
- **プレビューウィンドウが表示されない** — venvが有効か（プロンプト先頭の `(.venv)`）と、`pip install -r requirements.txt` の実行を確認してください。非対話バックエンドに関する警告が出る場合は、tkinterなしでPythonがインストールされています。「tcl/tk and IDLE」オプションにチェックを入れて再インストールしてください。
