# Track B ffmpeg-drift Sweep - 20260427T023312Z-overscan-core

Rows: 54
Passed rows: 54
Target Kling motion score: 0.0149

## Fastest Aggregates

| case | frames | pan | fill | crf | median wall ms | median encode ms | motion | layout | loop |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dense-text | 33 | 3,1.5 | overscan | 23 | 61.382 | 55.156 | 0.0218 | 0.9985 | 0.0007 |
| dense-text | 33 | 2,1 | overscan | 23 | 62.134 | 55.679 | 0.0179 | 0.9988 | 0.0006 |
| dense-text | 33 | 1,0.5 | overscan | 23 | 63.712 | 57.694 | 0.0081 | 0.9990 | 0.0007 |
| naturalist | 33 | 1,0.5 | overscan | 23 | 86.365 | 80.133 | 0.0143 | 0.9988 | 0.0012 |
| naturalist | 33 | 3,1.5 | overscan | 23 | 86.670 | 79.409 | 0.0306 | 0.9981 | 0.0012 |
| naturalist | 33 | 2,1 | overscan | 23 | 88.083 | 80.809 | 0.0213 | 0.9985 | 0.0012 |
| canal | 33 | 1,0.5 | overscan | 23 | 96.980 | 90.482 | 0.0247 | 0.9975 | 0.0013 |
| canal | 33 | 2,1 | overscan | 23 | 98.070 | 91.106 | 0.0359 | 0.9971 | 0.0013 |
| canal | 33 | 3,1.5 | overscan | 23 | 99.172 | 93.167 | 0.0522 | 0.9965 | 0.0013 |
| dense-text | 121 | 3,1.5 | overscan | 23 | 112.961 | 106.599 | 0.0218 | 0.9985 | 0.0006 |
| dense-text | 121 | 2,1 | overscan | 23 | 113.010 | 106.587 | 0.0178 | 0.9988 | 0.0006 |
| dense-text | 121 | 1,0.5 | overscan | 23 | 113.600 | 107.097 | 0.0081 | 0.9990 | 0.0007 |

## Closest To Kling Motion

| case | frames | pan | fill | crf | median wall ms | median encode ms | motion | layout | loop |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| naturalist | 121 | 1,0.5 | overscan | 23 | 170.722 | 163.880 | 0.0143 | 0.9988 | 0.0012 |
| naturalist | 33 | 1,0.5 | overscan | 23 | 86.365 | 80.133 | 0.0143 | 0.9988 | 0.0012 |
| dense-text | 121 | 2,1 | overscan | 23 | 113.010 | 106.587 | 0.0178 | 0.9988 | 0.0006 |
| dense-text | 33 | 2,1 | overscan | 23 | 62.134 | 55.679 | 0.0179 | 0.9988 | 0.0006 |
| naturalist | 33 | 2,1 | overscan | 23 | 88.083 | 80.809 | 0.0213 | 0.9985 | 0.0012 |
| naturalist | 121 | 2,1 | overscan | 23 | 170.324 | 163.861 | 0.0213 | 0.9985 | 0.0012 |
| dense-text | 33 | 1,0.5 | overscan | 23 | 63.712 | 57.694 | 0.0081 | 0.9990 | 0.0007 |
| dense-text | 121 | 1,0.5 | overscan | 23 | 113.600 | 107.097 | 0.0081 | 0.9990 | 0.0007 |
| dense-text | 121 | 3,1.5 | overscan | 23 | 112.961 | 106.599 | 0.0218 | 0.9985 | 0.0006 |
| dense-text | 33 | 3,1.5 | overscan | 23 | 61.382 | 55.156 | 0.0218 | 0.9985 | 0.0007 |
| canal | 121 | 1,0.5 | overscan | 23 | 204.318 | 197.467 | 0.0246 | 0.9975 | 0.0013 |
| canal | 33 | 1,0.5 | overscan | 23 | 96.980 | 90.482 | 0.0247 | 0.9975 | 0.0013 |

## Best 121-Frame Candidate Per Case

| case | frames | pan | fill | crf | median wall ms | median encode ms | motion | layout | loop |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| canal | 121 | 1,0.5 | overscan | 23 | 204.318 | 197.467 | 0.0246 | 0.9975 | 0.0013 |
| dense-text | 121 | 2,1 | overscan | 23 | 113.010 | 106.587 | 0.0178 | 0.9988 | 0.0006 |
| naturalist | 121 | 1,0.5 | overscan | 23 | 170.722 | 163.880 | 0.0143 | 0.9988 | 0.0012 |

## Interpretation

This sweep measures deterministic page-plate drift, not generative re-layout. The useful product boundary is the fastest setting that remains visually subtle enough for a page family.
