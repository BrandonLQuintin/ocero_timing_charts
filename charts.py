#!/usr/bin/env python
"""charts.py: list, preview, and export timing charts from timing_charts/.

Run:  python charts.py
"""

import os
import sys

import chartlib

HERE = os.path.dirname(os.path.abspath(__file__))
CHART_DIR = os.path.join(HERE, "timing_charts")
PREFIX = "timingchart_"


def discover():
    """Load every timingchart_*.py in timing_charts/. Returns a list of dicts."""
    if not os.path.isdir(CHART_DIR):
        return []
    names = sorted(
        f for f in os.listdir(CHART_DIR)
        if f.lower().startswith(PREFIX) and f.lower().endswith(".py")
    )
    entries = []
    for name in names:
        path = os.path.join(CHART_DIR, name)
        data, error = chartlib.load_chart_file(path)
        entries.append({"path": path, "name": name, "data": data, "error": error})
    return entries


def _fmt(value):
    return chartlib.format_time(value)


def print_menu(entries):
    if not entries:
        print(f"No timing charts found in {CHART_DIR}")
        print("Save a Copilot-generated chart there as timingchart_<name>.py (see chatbot.md).")
        return
    print(f"Timing charts in {os.path.basename(CHART_DIR)}/  ({len(entries)} found)\n")
    width = max(len(e["name"]) for e in entries)
    for i, entry in enumerate(entries, 1):
        if entry["error"] is None:
            data = entry["data"]
            t0, t1 = chartlib.time_span(data)
            desc = (f'"{data["title"]}"  ·  {len(data["signals"])} signals  ·  '
                    f"{_fmt(t0)}\u2013{_fmt(t1)} s")
            print(f"  [{i}] {entry['name']:<{width}}   {desc}   ✓")
        else:
            print(f"  [{i}] {entry['name']:<{width}}   ✗ error: {entry['error']}")
    print()


def _ask(prompt):
    try:
        return input(prompt)
    except EOFError:
        return ""
    except KeyboardInterrupt:
        print()
        raise SystemExit(0)


def main():
    # Windows: when stdout/stderr is piped or redirected (not a real console),
    # it defaults to the ANSI codepage (e.g. cp1252) and the menu's ✓/✗ would
    # raise UnicodeEncodeError. Interactive consoles are unaffected; "replace"
    # degrades non-encodable characters to '?' instead of crashing.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass
    entries = discover()
    print_menu(entries)
    if not entries:
        return
    while True:
        choice = _ask("Preview a chart — enter a number (or press Enter to quit): ").strip()
        if not choice:
            return
        if not choice.isdigit() or not 1 <= int(choice) <= len(entries):
            print(f"  Please enter a number between 1 and {len(entries)}.\n")
            continue
        entry = entries[int(choice) - 1]
        if entry["error"] is not None:
            print("  This chart has errors and cannot be previewed.\n")
            continue
        try:
            chartlib.render_chart(entry["data"])
        except Exception as exc:
            print(f"  Could not render chart: {type(exc).__name__}: {exc}\n")
            continue
        answer = _ask("Save to CSV? (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            csv_path = os.path.splitext(entry["path"])[0] + ".csv"
            try:
                chartlib.save_csv(entry["data"], csv_path)
                print(f"  Saved {csv_path}\n")
            except PermissionError:
                print(f"  Could not save {csv_path} — is it open in Excel? Close it and retry.\n")
            except Exception as exc:
                print(f"  Could not save CSV: {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
