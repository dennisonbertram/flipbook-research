# Track C Autoresearch Status

Updated UTC: `2026-04-24T18:20:43+00:00`

## Active Sessions

- `track-c-autoresearch`
- `track-c-c27-line-rect-r005-pad6`
- `track-c-c27-responsive-018`

## Queue

- `c27-line-rect-r0025`: done - Line anchor ratio sweep below current best 0.05.
- `c27-line-rect-r0075`: done - Line anchor ratio sweep above current best 0.05 but below previous 0.10.
- `c27-line-rect-r005-pad2`: done - Current best ratio with tighter support boxes to reduce unrelated illustration capture.
- `c27-line-rect-r005-pad6`: pending/running - Current best ratio with wider support boxes to check whether extra local context improves OCR.
- `c27-responsive-018`: pending/running - Responsive-squeeze boundary between strong 0.16 pass and xstrong 0.22 fail.
- `c26-word-rect-r010`: done - Word-level support rectangles: preserve text background while avoiding large line boxes that can catch illustration pixels.
- `c26-word-rect-moderate-r010`: done - Moderate stress word-level support rectangle control.
- `c26-line-rect-r005`: done - Line anchor scale-ratio refinement below the current best 0.10.
- `c26-responsive-xstrong`: done - Very strong responsive-squeeze boundary after the strong run still passed.
- `c25-alpha-r000`: done - Relaunch text-alpha strong stress ratio 0.00 after run-id collision fix.
- `c25-alpha-r025`: done - Relaunch text-alpha strong stress ratio 0.25 after run-id collision fix.
- `c25-alpha-moderate-r010`: done - Check whether text-alpha only fails under strong stress or also moderate stress.
- `c25-rectangle-r010`: done - Rectangle anchor ratio 0.10 control to separate alpha-mask failure from scale-ratio behavior.
- `c25-responsive-strong`: done - Stronger responsive-squeeze boundary after the first responsive-squeeze pass.
