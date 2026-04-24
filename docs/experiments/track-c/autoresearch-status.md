# Track C Autoresearch Status

Updated UTC: `2026-04-24T18:31:17+00:00`

## Active Sessions

- `track-c-autoresearch`

## Queue

- `c28-word-batched-r010`: done - Human-positive word anchors with batched patch rendering to recover latency.
- `c28-word-batched-moderate-r010`: done - Human-positive word anchors batched under moderate stress.
- `c28-line-batched-r005`: done - Batched line-anchor control should match C2.6 quality while confirming batching does not change pixels.
- `c27-line-rect-r0025`: done - Line anchor ratio sweep below current best 0.05.
- `c27-line-rect-r0075`: done - Line anchor ratio sweep above current best 0.05 but below previous 0.10.
- `c27-line-rect-r005-pad2`: done - Current best ratio with tighter support boxes to reduce unrelated illustration capture.
- `c27-line-rect-r005-pad6`: done - Current best ratio with wider support boxes to check whether extra local context improves OCR.
- `c27-responsive-018`: done - Responsive-squeeze boundary between strong 0.16 pass and xstrong 0.22 fail.
- `c26-word-rect-r010`: done - Word-level support rectangles: preserve text background while avoiding large line boxes that can catch illustration pixels.
- `c26-word-rect-moderate-r010`: done - Moderate stress word-level support rectangle control.
- `c26-line-rect-r005`: done - Line anchor scale-ratio refinement below the current best 0.10.
- `c26-responsive-xstrong`: done - Very strong responsive-squeeze boundary after the strong run still passed.
- `c25-alpha-r000`: done - Relaunch text-alpha strong stress ratio 0.00 after run-id collision fix.
- `c25-alpha-r025`: done - Relaunch text-alpha strong stress ratio 0.25 after run-id collision fix.
- `c25-alpha-moderate-r010`: done - Check whether text-alpha only fails under strong stress or also moderate stress.
- `c25-rectangle-r010`: done - Rectangle anchor ratio 0.10 control to separate alpha-mask failure from scale-ratio behavior.
- `c25-responsive-strong`: done - Stronger responsive-squeeze boundary after the first responsive-squeeze pass.
