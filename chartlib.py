"""chartlib: Chart builder, validation, rendering, and CSV export for timing charts.

Chart files in timing_charts/ describe a chart as data using the Chart class
below. charts.py imports those files, validates them with validate_chart(),
opens a preview with render_chart(), and writes wide-format CSVs
(time + one column per signal) with save_csv().

The builder API documented in chatbot.md must stay in sync with this module:
chatbot.md is the prompt users paste into their LLM, and it documents exactly
the methods below.
"""

from __future__ import annotations

import csv
import importlib.util
import math
import os

import matplotlib.pyplot as plt

ALLOWED_STATES = ("0", "1", "x", "z")
_ANALOG_DECIMALS = 6  # decimal places for analog values in CSV output
_EPS = 1e-9


class ChartError(ValueError):
    """Raised when a chart definition is invalid. Messages are user-facing."""


def _is_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:  # ints too large for float: not a usable time/value
        return False


def _collapse(pairs):
    """Sort by time; later entry wins at identical times; drop no-change repeats."""
    out = []
    for t, state in sorted(pairs, key=lambda p: p[0]):
        if out and out[-1][0] == t:
            out[-1] = (t, state)
        elif out and out[-1][1] == state:
            continue
        else:
            out.append((t, state))
    return out


class Chart:
    """Builder for one timing chart. Chart files use this inside chart()."""

    def __init__(self, title, time_unit=None):
        if time_unit is not None:
            raise ChartError(
                "time_unit was removed; all times are in seconds now "
                "(0.001 = 1 ms, 0.000001 = 1 us)"
            )
        self.title = str(title)
        self._signals = []

    # -- builder methods (documented in chatbot.md; keep both in sync) ------

    def clock(self, name, period, until, start=0, duty=50):
        """Digital clock: starts HIGH at `start`, toggles every period/2 until `until`."""
        self._check_new_name(name)
        p = self._num_arg("clock", name, "period", period)
        u = self._num_arg("clock", name, "until", until)
        s = self._num_arg("clock", name, "start", start)
        d = self._num_arg("clock", name, "duty", duty)
        if p <= 0:
            raise ChartError(f"clock {name!r}: period must be > 0")
        if not 0 < d < 100:
            raise ChartError(f"clock {name!r}: duty must be between 0 and 100 (percent high)")
        if u <= s + _EPS:
            raise ChartError(f"clock {name!r}: until must be greater than start")
        high = p * d / 100.0
        low = p - high
        transitions = [(s, "1")]
        t, level = s, "1"
        while True:
            nxt = t + (high if level == "1" else low)
            if nxt >= u - _EPS:
                break
            level = "0" if level == "1" else "1"
            transitions.append((nxt, level))
            t = nxt
        self._signals.append({"name": str(name), "kind": "digital", "transitions": transitions})

    def digital(self, name, fn, t0=0, t1=0.1, dt=0.005):
        """Digital signal: sample fn(t) -> bool every dt; True -> "1", False -> "0"."""
        self._check_new_name(name)
        if not callable(fn):
            raise ChartError(f"digital {name!r}: fn must be callable")
        values = []
        for t in self._time_grid("digital", name, t0, t1, dt):
            try:
                v = fn(t)
            except Exception as exc:
                raise ChartError(
                    f"digital {name!r}: fn raised {type(exc).__name__} at t={t:g}: {exc}"
                ) from None
            if isinstance(v, bool):
                state = "1" if v else "0"
            elif isinstance(v, (int, float)) and v in (0, 1):
                state = "1" if v else "0"
            else:
                raise ChartError(
                    f"digital {name!r}: fn must return True or False (or 0/1)"
                    f" (got {v!r} at t={t:g})"
                )
            values.append((t, state))
        self._signals.append({"name": str(name), "kind": "digital", "transitions": values})

    def analog(self, name, fn, t0=0, t1=0.1, dt=0.002):
        """Analog signal: sample fn(t) -> number every dt; drawn as a curve."""
        self._check_new_name(name)
        if not callable(fn):
            raise ChartError(f"analog {name!r}: fn must be callable")
        samples = []
        for t in self._time_grid("analog", name, t0, t1, dt):
            try:
                v = fn(t)
            except Exception as exc:
                raise ChartError(
                    f"analog {name!r}: fn raised {type(exc).__name__} at t={t:g}: {exc}"
                ) from None
            if not _is_number(v):
                raise ChartError(
                    f"analog {name!r}: fn must return a number (got {v!r} at t={t:g})"
                )
            samples.append((t, float(v)))
        self._signals.append({"name": str(name), "kind": "analog", "samples": samples})

    def add(self, name, transitions):
        """Raw digital signal from (time, state) pairs; state in "0"/"1"/"x"/"z"."""
        self._check_new_name(name)
        try:
            pairs = list(transitions)
        except TypeError:
            raise ChartError(
                f"signal {name!r}: transitions must be a list of (time, state) pairs"
            ) from None
        if not pairs:
            raise ChartError(f"signal {name!r}: transitions must not be empty")
        clean = []
        for item in pairs:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise ChartError(
                    f"signal {name!r}: transitions must be (time, state) pairs, got {item!r}"
                )
            t, state = item
            t = self._num_arg("signal", name, "time", t)
            if state not in ALLOWED_STATES:
                raise ChartError(
                    f"signal {name!r}: state {state!r} is not one of {list(ALLOWED_STATES)}"
                )
            clean.append((t, state))
        self._signals.append({"name": str(name), "kind": "digital", "transitions": clean})

    # -- internals ------------------------------------------------------------

    def _check_new_name(self, name):
        if not isinstance(name, str) or not name.strip():
            raise ChartError("signal name must be a non-empty string")
        if any(sig["name"] == name for sig in self._signals):
            raise ChartError(f"duplicate signal name: {name!r}")

    @staticmethod
    def _num_arg(where, name, arg, value):
        if not _is_number(value):
            raise ChartError(f"{where} {name!r}: {arg} must be a number (got {value!r})")
        return float(value)

    @staticmethod
    def _time_grid(where, name, t0, t1, dt):
        t0 = Chart._num_arg(where, name, "t0", t0)
        t1 = Chart._num_arg(where, name, "t1", t1)
        dt = Chart._num_arg(where, name, "dt", dt)
        if dt <= 0:
            raise ChartError(f"{where} {name!r}: dt must be > 0")
        if t1 <= t0:
            raise ChartError(f"{where} {name!r}: t1 must be greater than t0")
        n = int(math.floor((t1 - t0) / dt + _EPS)) + 1
        # canonicalize so fn() sees exactly the times that will be printed
        return [_canon(t0 + i * dt) for i in range(n)]

    def build(self):
        """Validate the chart and return it as a plain data dict."""
        if not self._signals:
            raise ChartError("chart has no signals; call at least one builder method")
        signals = []
        for s in self._signals:
            if s["kind"] == "digital":
                signals.append({
                    "name": s["name"],
                    "kind": "digital",
                    "transitions": _collapse(s["transitions"]),
                })
            else:
                signals.append({"name": s["name"], "kind": "analog", "samples": list(s["samples"])})
        data = {"title": self.title, "signals": signals}
        return validate_chart(data)


def validate_chart(data):
    """Check a chart dict (as returned by Chart.build()). Raises ChartError."""
    if not isinstance(data, dict):
        raise ChartError("chart() must return c.build() (expected a dict)")
    for key in ("title", "signals"):
        if key not in data:
            raise ChartError(f"chart is missing {key!r}")
    signals = data["signals"]
    if not isinstance(signals, list) or not signals:
        raise ChartError("chart must have at least one signal")
    seen = set()
    for sig in signals:
        if not isinstance(sig, dict):
            raise ChartError("each signal must be a dict")
        name = sig.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ChartError("every signal needs a non-empty name")
        if name in seen:
            raise ChartError(f"duplicate signal name: {name!r}")
        seen.add(name)
        kind = sig.get("kind")
        if kind == "digital":
            pairs = sig.get("transitions")
            if not isinstance(pairs, list) or not pairs:
                raise ChartError(f"digital signal {name!r}: transitions must be a non-empty list")
            for item in pairs:
                if not isinstance(item, (tuple, list)) or len(item) != 2:
                    raise ChartError(
                        f"digital signal {name!r}: transitions must be (time, state) pairs"
                    )
                t, state = item
                if not _is_number(t):
                    raise ChartError(f"digital signal {name!r}: time {t!r} must be a number")
                if state not in ALLOWED_STATES:
                    raise ChartError(
                        f"digital signal {name!r}: state {state!r} must be one of "
                        f"{list(ALLOWED_STATES)}"
                    )
        elif kind == "analog":
            pairs = sig.get("samples")
            if not isinstance(pairs, list) or not pairs:
                raise ChartError(f"analog signal {name!r}: samples must be a non-empty list")
            for item in pairs:
                if not isinstance(item, (tuple, list)) or len(item) != 2:
                    raise ChartError(
                        f"analog signal {name!r}: samples must be (time, value) pairs"
                    )
                t, v = item
                if not _is_number(t) or not _is_number(v):
                    raise ChartError(
                        f"analog signal {name!r}: (time, value) must be numbers, got {item!r}"
                    )
        else:
            raise ChartError(f"signal {name!r}: unknown kind {kind!r}")
    return data


def load_chart_file(path):
    """Import a chart file and run its chart() function.

    Returns (chart_dict_or_None, error_or_None). The error string is meant to
    be shown to the user (and pasted back into their LLM chat).
    """
    stem = os.path.splitext(os.path.basename(path))[0]
    modname = f"tc_{stem}"  # never registered in sys.modules, so reuse is fine
    spec = importlib.util.spec_from_file_location(modname, path)
    if spec is None or spec.loader is None:
        return None, "could not load module"
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    chart_fn = getattr(module, "chart", None)
    if not callable(chart_fn):
        return None, "file must define a chart() function"
    try:
        data = chart_fn()
        validate_chart(data)
    except ChartError as exc:
        return None, str(exc)
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    return data, None


def time_span(data):
    """Return (tmin, tmax) across all signals in a validated chart dict."""
    times = []
    for sig in data["signals"]:
        pairs = sig.get("transitions") or sig.get("samples") or []
        times.extend(float(t) for t, _ in pairs)
    return (min(times), max(times)) if times else (0.0, 0.0)


def format_time(t):
    """Format a time in seconds as a plain decimal: no scientific notation,
    no trailing zeros ('0', '0.7', '0.0000001')."""
    s = f"{float(t):.12f}".rstrip("0").rstrip(".")
    if s == "-0":
        s = "0"
    return s or "0"


def _canon(t):
    """Collapse float noise to the exact value that will be printed."""
    return float(f"{float(t):.12f}")


def _held_values(pairs, grid):
    """Sample a sorted (time, value) list at each grid time, holding forward.

    Times before the first pair take the first value (Excel-friendly bfill).
    """
    out = []
    i, cur = 0, pairs[0][1]
    for t in grid:
        while i < len(pairs) and pairs[i][0] <= t:
            cur = pairs[i][1]
            i += 1
        out.append(cur)
    return out


def save_csv(data, path):
    """Write the wide-format CSV: a time column plus one column per signal.

    Rows are the union of all transition/sample times; each value holds
    forward until the signal's next change, so every column plots directly
    against `time` in Excel. Returns path.
    """
    times = set()
    for sig in data["signals"]:
        pairs = sig["transitions"] if sig["kind"] == "digital" else sig["samples"]
        times.update(_canon(t) for t, _ in pairs)
    if not times:
        raise ChartError("chart has no data points to export")
    grid = sorted(times)

    columns = []
    for sig in data["signals"]:
        pairs = sig["transitions"] if sig["kind"] == "digital" else sig["samples"]
        pairs = sorted((_canon(float(t)), v) for t, v in pairs)
        columns.append(_held_values(pairs, grid))

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["time"] + [sig["name"] for sig in data["signals"]])
        for i, t in enumerate(grid):
            row = [format_time(t)]
            for sig, column in zip(data["signals"], columns):
                v = column[i]
                if sig["kind"] == "analog":
                    v = round(float(v), _ANALOG_DECIMALS) + 0.0  # normalize -0.0 to 0.0
                row.append(v)
            writer.writerow(row)
    return path


# -- rendering -----------------------------------------------------------------

def render_chart(data, save_path=None):
    """Draw the chart and open an interactive preview window (or save to a file).

    Digital signals are drawn as step-waveform lanes; analog signals as curves.
    All lanes share the same time axis. save_path is a test hook for headless
    rendering; the menu itself never writes image files.
    """
    signals = data["signals"]
    n = len(signals)
    t_start, t_end = time_span(data)
    pad = max((t_end - t_start) * 0.02, _EPS)
    fig, axes = plt.subplots(
        n, 1, sharex=True, figsize=(10, 1.1 * n + 0.8),
        layout="constrained",
    )
    axes = [axes] if n == 1 else list(axes)
    for ax, sig in zip(axes, signals):
        if sig["kind"] == "digital":
            _draw_digital(ax, sig, t_start, t_end + pad)
        else:
            _draw_analog(ax, sig)
        ax.set_ylabel(sig["name"], rotation=0, ha="right", va="center")
        ax.set_yticks([])
        ax.grid(axis="x", color="0.90", linewidth=0.8)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
    axes[-1].set_xlabel("time (s)")
    axes[-1].set_xlim(t_start - pad, t_end + pad)
    fig.suptitle(str(data["title"]))
    if save_path:
        fig.savefig(save_path, dpi=110)
        plt.close(fig)
    else:
        plt.show()


def _level_y(state):
    return float(state) if state in ("0", "1") else 0.5


def _draw_digital(ax, sig, t_start, t_end):
    transitions = sig["transitions"]
    # no data before the first transition (e.g. a clock with start > t0):
    # render the region as don't-care so it doesn't read as missing data
    first_t = transitions[0][0]
    if first_t > t_start + _EPS:
        ax.axvspan(t_start, first_t, color="0.88", zorder=0)
        ax.plot([t_start, first_t], [0.5, 0.5], color="0.4", lw=1.4, ls=":", zorder=2)
    for i, (t_from, state) in enumerate(transitions):
        t_to = transitions[i + 1][0] if i + 1 < len(transitions) else t_end
        if state == "x":
            ax.axvspan(t_from, t_to, color="0.88", zorder=0)
            ax.plot([t_from, t_to], [0.5, 0.5], color="0.4", lw=1.4, ls=":", zorder=2)
        elif state == "z":
            ax.plot([t_from, t_to], [0.5, 0.5], color="tab:blue", lw=1.4, ls="--", zorder=2)
        else:
            y = float(state)
            ax.plot([t_from, t_to], [y, y], color="0.05", lw=1.8,
                    solid_capstyle="butt", zorder=2)
    # vertical connectors wherever consecutive levels differ
    for (t_left, s_left), (t_right, s_right) in zip(transitions, transitions[1:]):
        y_left, y_right = _level_y(s_left), _level_y(s_right)
        if y_left != y_right:
            solid = s_left in ("0", "1") and s_right in ("0", "1")
            ax.plot([t_right, t_right], [y_left, y_right],
                    color="0.05" if solid else "0.45",
                    lw=1.8 if solid else 1.2, zorder=2)


def _draw_analog(ax, sig):
    ts = [t for t, _ in sig["samples"]]
    vs = [v for _, v in sig["samples"]]
    ax.plot(ts, vs, color="tab:red", lw=1.6, zorder=2)
