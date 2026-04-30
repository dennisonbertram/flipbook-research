# Track V Camera Path Diagnostic

This diagnostic asks whether generated frames are explainable as a crop/zoom of the input page. It is a proxy for camera-collapse versus actual page-preserving generation.

| run | model | frame | class | crop score | scale | crop x,y,w,h | text | layout | motion |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| 20260426T233957Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-preservation-1920x1080 | ltx-api-ltx-2-3-fast | first | near-copy | 0.743 | 1.00 | 0.00,0.00,1.00,1.00 | 0.320 | 0.974 | 0.143 |
| 20260426T233957Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-preservation-1920x1080 | ltx-api-ltx-2-3-fast | mid | not-crop-explainable | 0.233 | 1.00 | 0.00,0.00,1.00,1.00 | 0.320 | 0.974 | 0.143 |
| 20260426T233957Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-preservation-1920x1080 | ltx-api-ltx-2-3-fast | last | not-crop-explainable | 0.235 | 1.00 | 0.00,0.00,1.00,1.00 | 0.320 | 0.974 | 0.143 |
| 20260426T234547Z-ltx-api-ltx-2-fast-official-ltx2-fast-text-preservation-1920x1080 | ltx-api-ltx-2-fast | first | near-copy | 0.846 | 1.00 | 0.00,0.00,1.00,1.00 | 0.363 | 0.988 | 0.065 |
| 20260426T234547Z-ltx-api-ltx-2-fast-official-ltx2-fast-text-preservation-1920x1080 | ltx-api-ltx-2-fast | mid | not-crop-explainable | 0.316 | 1.00 | 0.00,0.00,1.00,1.00 | 0.363 | 0.988 | 0.065 |
| 20260426T234547Z-ltx-api-ltx-2-fast-official-ltx2-fast-text-preservation-1920x1080 | ltx-api-ltx-2-fast | last | not-crop-explainable | 0.255 | 1.00 | 0.00,0.00,1.00,1.00 | 0.363 | 0.988 | 0.065 |
| 20260427T235031Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-lastframe-1920x1080 | ltx-api-ltx-2-3-fast | first | near-copy | 0.854 | 1.00 | 0.00,0.00,1.00,1.00 | 0.686 | 0.990 | 0.102 |
| 20260427T235031Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-lastframe-1920x1080 | ltx-api-ltx-2-3-fast | mid | partially-crop-explainable | 0.455 | 1.00 | 0.00,0.00,1.00,1.00 | 0.686 | 0.990 | 0.102 |
| 20260427T235031Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-lastframe-1920x1080 | ltx-api-ltx-2-3-fast | last | near-copy | 0.931 | 1.00 | 0.00,0.00,1.00,1.00 | 0.686 | 0.990 | 0.102 |
| 20260428T002049Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-anchor-3s-locked-1920x1080 | ltx-api-ltx-2-3-fast | first | near-copy | 0.855 | 1.00 | 0.00,0.00,1.00,1.00 | 0.720 | 0.998 | 0.030 |
| 20260428T002049Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-anchor-3s-locked-1920x1080 | ltx-api-ltx-2-3-fast | mid | partially-crop-explainable | 0.515 | 1.00 | 0.00,0.00,1.00,1.00 | 0.720 | 0.998 | 0.030 |
| 20260428T002049Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-anchor-3s-locked-1920x1080 | ltx-api-ltx-2-3-fast | last | near-copy | 0.946 | 1.00 | 0.00,0.00,1.00,1.00 | 0.720 | 0.998 | 0.030 |
| 20260428T002056Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-anchor-2s-locked-1920x1080 | ltx-api-ltx-2-3-fast | first | near-copy | 0.856 | 1.00 | 0.00,0.00,1.00,1.00 | 0.810 | 0.999 | 0.008 |
| 20260428T002056Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-anchor-2s-locked-1920x1080 | ltx-api-ltx-2-3-fast | mid | near-copy | 0.907 | 1.00 | 0.00,0.00,1.00,1.00 | 0.810 | 0.999 | 0.008 |
| 20260428T002056Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-anchor-2s-locked-1920x1080 | ltx-api-ltx-2-3-fast | last | near-copy | 0.927 | 1.00 | 0.00,0.00,1.00,1.00 | 0.810 | 0.999 | 0.008 |
| 20260428T002253Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-anchor-2s-defaultprompt-1920x1080 | ltx-api-ltx-2-3-fast | first | near-copy | 0.856 | 1.00 | 0.00,0.00,1.00,1.00 | 0.648 | 0.999 | 0.009 |
| 20260428T002253Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-anchor-2s-defaultprompt-1920x1080 | ltx-api-ltx-2-3-fast | mid | near-copy | 0.905 | 1.00 | 0.00,0.00,1.00,1.00 | 0.648 | 0.999 | 0.009 |
| 20260428T002253Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-anchor-2s-defaultprompt-1920x1080 | ltx-api-ltx-2-3-fast | last | near-copy | 0.933 | 1.00 | 0.00,0.00,1.00,1.00 | 0.648 | 0.999 | 0.009 |
| 20260428T002259Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-noanchor-2s-locked-1920x1080 | ltx-api-ltx-2-3-fast | first | near-copy | 0.854 | 1.00 | 0.00,0.00,1.00,1.00 | 0.320 | 0.988 | 0.090 |
| 20260428T002259Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-noanchor-2s-locked-1920x1080 | ltx-api-ltx-2-3-fast | mid | not-crop-explainable | 0.346 | 1.00 | 0.00,0.00,1.00,1.00 | 0.320 | 0.988 | 0.090 |
| 20260428T002259Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-noanchor-2s-locked-1920x1080 | ltx-api-ltx-2-3-fast | last | partially-crop-explainable | 0.393 | 1.00 | 0.00,0.00,1.00,1.00 | 0.320 | 0.988 | 0.090 |
| 20260428T002306Z-ltx-api-ltx-2-3-fast-official-ltx-api-naturalist-anchor-2s-locked-1920x1080 | ltx-api-ltx-2-3-fast | first | near-copy | 0.814 | 1.00 | 0.00,0.00,1.00,1.00 | 0.050 | 0.997 | 0.038 |
| 20260428T002306Z-ltx-api-ltx-2-3-fast-official-ltx-api-naturalist-anchor-2s-locked-1920x1080 | ltx-api-ltx-2-3-fast | mid | near-copy | 0.789 | 1.00 | 0.00,0.00,1.00,1.00 | 0.050 | 0.997 | 0.038 |
| 20260428T002306Z-ltx-api-ltx-2-3-fast-official-ltx-api-naturalist-anchor-2s-locked-1920x1080 | ltx-api-ltx-2-3-fast | last | near-copy | 0.925 | 1.00 | 0.00,0.00,1.00,1.00 | 0.050 | 0.997 | 0.038 |
| 20260428T002357Z-ltx-api-ltx-2-3-fast-official-ltx-api-naturalist-anchor-2s-noshadow-1920x1080 | ltx-api-ltx-2-3-fast | first | near-copy | 0.840 | 1.00 | 0.00,0.00,1.00,1.00 | 0.077 | 0.999 | 0.011 |
| 20260428T002357Z-ltx-api-ltx-2-3-fast-official-ltx-api-naturalist-anchor-2s-noshadow-1920x1080 | ltx-api-ltx-2-3-fast | mid | near-copy | 0.912 | 1.00 | 0.00,0.00,1.00,1.00 | 0.077 | 0.999 | 0.011 |
| 20260428T002357Z-ltx-api-ltx-2-3-fast-official-ltx-api-naturalist-anchor-2s-noshadow-1920x1080 | ltx-api-ltx-2-3-fast | last | near-copy | 0.947 | 1.00 | 0.00,0.00,1.00,1.00 | 0.077 | 0.999 | 0.011 |
| 20260427T023910Z-track-b-hybrid-sweep-dense-text-f121-p1x0-5-crf23-r0-960x540 |  | first | near-copy | 0.846 | 1.00 | 0.00,0.00,1.00,1.00 | -1.000 | 0.999 | 0.008 |
| 20260427T023910Z-track-b-hybrid-sweep-dense-text-f121-p1x0-5-crf23-r0-960x540 |  | mid | near-copy | 0.837 | 1.00 | 0.00,0.00,1.00,1.00 | -1.000 | 0.999 | 0.008 |
| 20260427T023910Z-track-b-hybrid-sweep-dense-text-f121-p1x0-5-crf23-r0-960x540 |  | last | near-copy | 0.846 | 1.00 | 0.00,0.00,1.00,1.00 | -1.000 | 0.999 | 0.008 |

## Reading

- `near-copy`: frame is mostly the source plate.
- `camera-zoom-like`: frame is largely explainable as a zoom/crop of the source.
- `partially-crop-explainable`: model keeps some source geometry but also repaints or warps.
- `not-crop-explainable`: frame no longer maps cleanly to the source image.
