# LLM Benchmark Results

**Date:** 2026-05-20T16:48:38
**CPU governor:** `ondemand` @ 2400 MHz
**Baseline temp:** 33.1°C
**Throttle state:** `throttled=0x0`
**Kernel:** 6.12.75+rpt-rpi-2712

## Results matrix

| Config | Runs | TTFT (med) | Prompt eval | Generation | Total | Peak temp |
|---|---|---|---|---|---|---|
| gemma3:1b small | 3/3 | 34.2s | 28.6 tok/s | 10.0 tok/s | 85.0s | 53.5°C |
| gemma3:1b medium | 3/3 | 76.4s | 27.7 tok/s | 10.9 tok/s | 122.7s | 55.6°C |
| gemma3:1b large | 3 | ❌ all failed | — | — | — | — |

## Notes

- TTFT = time-to-first-token (UX-critical; what the user feels as 'wait')
- Prompt eval tok/s = how fast the model chews input. Dominant cost on Pi 5.
- Generation tok/s = how fast the model emits output. Steady-state speed.
- Median of N runs is reported. Min/max are in `results.json`.
