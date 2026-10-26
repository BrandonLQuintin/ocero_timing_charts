# Copilot prompt for generating timing charts

English | [日本語](chatbot.ja.md)

## How to use this file (for humans — do not paste this section)

1. Open a chat with Copilot.
2. Start your message with a short description of the timing chart you want
   (signals, timings, relationships between them).
3. Copy everything BELOW the horizontal line and paste it after your description.
4. Save the single code block Copilot returns as:
   `timing_charts/timingchart_<short_name>.py`
5. Run `python charts.py`. If your chart is listed with an error, paste the
   error message back into the same Copilot chat and ask it to regenerate
   the complete file.

---

You generate timing-chart definition files for a digital timing diagram tool.
Your output must be EXACTLY ONE Python file in ONE code block, with no
explanatory text before or after it.

## Required structure

Every file must follow this structure exactly:

```python
"""<one-line description of what the chart shows>"""
import math
from chartlib import Chart

def chart():
    c = Chart("<chart title>")
    # one builder call per signal
    return c.build()
```

All times are in SECONDS. Use decimals for smaller units: 0.001 is 1 ms,
0.000001 is 1 us, 0.000000001 is 1 ns.

## Builder API (the only chartlib features you may use)

### Chart(title)
Creates a chart.

### c.clock(name, period, until, start=0, duty=50)
Digital clock: toggles every `period/2`, starts HIGH at `start`, runs until `until`.
Example: `c.clock("clk", period=0.04, until=0.1)`  # high 0-0.02, low 0.02-0.04, ...

### c.digital(name, fn, t0=0, t1=0.1, dt=0.005)
Digital signal sampled every `dt`. `fn(t)` must return a bool: True -> "1", False -> "0".
Example: `c.digital("ready", fn=lambda t: t >= 0.025, t0=0, t1=0.1, dt=0.005)`

### c.analog(name, fn, t0=0, t1=0.1, dt=0.002)
Analog waveform sampled every `dt`. `fn(t)` must return a number; it is drawn
as a curve and exported to CSV as real values.
Example: `c.analog("vsense", fn=lambda t: math.sin(2 * math.pi * t / 0.1), t0=0, t1=0.1, dt=0.002)`

### c.dac(name, fn, t0=0, t1=0.1, dt=0.005)
DAC output: sampled like `analog`, but drawn as discrete steps (zero-order
hold) — use it for a DAC's output or any value that holds between updates.
Example: `c.dac("vdac", fn=lambda t: 2.5 * (t / 0.1), t0=0, t1=0.1, dt=0.005)`

### c.add(name, transitions)
Raw digital signal from explicit transitions: a list of `(time, state)` tuples,
where state is one of "0", "1", "x" (don't care), "z" (high impedance).
Example: `c.add("en", [(0, "0"), (0.005, "1"), (0.035, "0")])`

## Hard rules

- Exactly one function `chart()` returning `c.build()`. No other top-level code.
- Only stdlib imports (`math`, `random`, ...) plus `from chartlib import Chart`.
  NEVER import matplotlib, numpy, or pandas.
- Use syntax compatible with Python 3.10.
- No `print`, no file I/O, no plotting. The function only builds data.
- If you use randomness, seed it (`random.seed(0)`) so the chart is reproducible.
- Signal names must be unique within a chart.
- Always include the one-line docstring describing the chart's intent.
- All times are in SECONDS — decimals like 0.001 (1 ms) or 0.000001 (1 us).

## Complete example of a correct file

```python
"""Sine vs clock - clk: 0.04 s period. sin: analog sine, period 0.1 s."""
import math
from chartlib import Chart

def chart():
    c = Chart("Sine vs clock")
    c.clock("clk", period=0.04, until=0.1)
    c.analog("sin", fn=lambda t: math.sin(2 * math.pi * t / 0.1), t0=0, t1=0.1, dt=0.002)
    return c.build()
```

All output is automatically validated. If the user reports a validation error,
regenerate the COMPLETE file with the problem fixed.
