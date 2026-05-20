# LLM Benchmark Results

**Date:** 2026-05-20T16:02:29
**CPU governor:** `ondemand` @ 2400 MHz
**Baseline temp:** 38.0°C
**Throttle state:** `throttled=0x0`
**Kernel:** 6.12.75+rpt-rpi-2712

## Results matrix

| Config | Runs | TTFT (med) | Prompt eval | Generation | Total | Peak temp |
|---|---|---|---|---|---|---|
| gemma3:1b small | 1/1 | 86.5s | 13.7 tok/s | 0.6 tok/s | 974.2s | 50.1°C |

## Notes

- TTFT = time-to-first-token (UX-critical; what the user feels as 'wait')
- Prompt eval tok/s = how fast the model chews input. Dominant cost on Pi 5.
- Generation tok/s = how fast the model emits output. Steady-state speed.
- Median of N runs is reported. Min/max are in `results.json`.
