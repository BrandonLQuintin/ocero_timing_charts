# Timing Charts

English | [日本語](README.ja.md)

**A timechart maker for people who don't have AI coding tools at work — just a
browser chatbot (Copilot web, ChatGPT, ...) and Python 3.10+ installed.**

Timing diagrams (digital waveforms + analog curves) written by AI, previewed and
exported to CSV locally. Describe a chart to the chatbot using the prompt in
`chatbot.md`, drop the generated `.py` file into `timing_charts/`, and use
`charts.py` to preview it and save CSVs.

## Layout

| File/folder      | Purpose                                              |
|------------------|------------------------------------------------------|
| `chatbot.md`     | The prompt to paste into Copilot (see its header)    |
| `timing_charts/` | One `timingchart_<name>.py` per chart (gitignored)   |
| `charts.py`      | Lists charts, opens preview, saves CSVs              |
| `chartlib.py`    | Chart builder + rendering + CSV engine               |

## One-time setup (Windows, Python 3.10 or newer)

From the repo root.

**In cmd:**
```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**In PowerShell:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Notes:
- Prefer the `py` launcher? Use `py -3.10 -m venv .venv` (any installed version
  works; nothing here requires exactly 3.10).
- Tested with Python 3.14 on Windows and Fedora Linux.
- PowerShell only: if `Activate.ps1` is blocked with a script-execution error,
  run this once, then retry:
  `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- The venv is active when your prompt starts with `(.venv)`. If it doesn't,
  STOP — the install steps above would go into your global Python instead.

Verify the setup: `python charts.py` should list your charts and open a preview
window when you select one. (A fresh copy of this repo has no charts yet —
generate your first one via `chatbot.md`.)

## Daily usage

1. Open `chatbot.md` and follow its header: describe your chart to Copilot,
   paste the prompt, save the result as `timing_charts/timingchart_<name>.py`.
2. Run `python charts.py`.
3. Enter the chart's number to open the preview window.
4. Answer `y` at the prompt to save `timing_charts/<name>.csv`.

## CSV format

Wide table: a `time` column plus one column per signal — no matter how many
signals the chart has, each one gets its own column. One row per time point
(the union of all transition/sample times); values hold forward until the
signal's next change, so every column plots directly against `time` in Excel.
Before a signal's first transition its first value is repeated backwards, and
after its last transition its last value repeats to the end of the range.

```csv
time,clk,sin
0,1,0.0
0.002,1,0.125333
0.004,1,0.24869
...
0.02,0,0.951057
```

## Troubleshooting

- **A chart shows an ✗ error in the list** — the file is malformed. Paste the
  exact error message into your Copilot chat and ask it to regenerate the
  complete file.
- **`python` is not recognized** — use the `py` launcher, or reinstall Python
  with "Add to PATH" enabled.
- **Preview window doesn't appear** — make sure the venv is activated
  (`(.venv)` in your prompt) and you ran `pip install -r requirements.txt`.
  If there's a warning about a non-interactive backend, Python was installed
  without tkinter: reinstall it with the "tcl/tk and IDLE" option ticked.
- **Piped/redirected output shows `?` instead of ✓/✗** — Python ≤3.14 falls
  back to the ANSI codepage when output isn't a real console. Set
  `PYTHONUTF8=1`, or use Python 3.15+ where UTF-8 is the default.
