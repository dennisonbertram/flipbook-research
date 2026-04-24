# Human Review Notes

Date: 2026-04-24

## Human-Positive / Metric-Negative Case

Run:

```text
outputs/track-c/20260424T174026078431Z-c2-lite-text-static-layout-element-frame-scale-c26-word-rect-r010-1280x736-s4500/output.mp4
```

User review:

```text
"this one looks very good"
```

Automated eval:

```text
scenario:          frame-scale-strong
anchor mode:       word
element ratio:     0.10
OCR token-F1:      0.1143
render_33_wall_ms: 3172.452
encode_ms:         526.506
segment_wall_ms:   3698.959
```

Interpretation:

- OCR is likely underrating this run because the visual output reads better than the token match suggests.
- Word-sized support regions preserve local visual context better than glyph-only alpha and may avoid dragging large unrelated illustration regions.
- The current implementation is too slow because `105` word patches are rendered sequentially for every frame.

Decision:

```text
Do not discard word anchors.
Prioritize batched word-anchor rendering.
Add human-review status to future eval summaries.
```

Next experiments:

```text
c28-word-batched-r010
c28-word-batched-moderate-r010
c28-line-batched-r005
```

