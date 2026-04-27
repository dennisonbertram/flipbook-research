# Track V Camera Path Diagnostic

This diagnostic asks whether generated frames are explainable as a crop/zoom of the input page. It is a proxy for camera-collapse versus actual page-preserving generation.

| run | model | frame | class | crop score | scale | crop x,y,w,h | text | layout | motion |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| 20260426T234547Z-ltx-api-ltx-2-fast-official-ltx2-fast-text-preservation-1920x1080 | ltx-api-ltx-2-fast | first | near-copy | 0.846 | 1.00 | 0.00,0.00,1.00,1.00 | 0.363 | 0.988 | 0.065 |
| 20260426T234547Z-ltx-api-ltx-2-fast-official-ltx2-fast-text-preservation-1920x1080 | ltx-api-ltx-2-fast | mid | not-crop-explainable | 0.316 | 1.00 | 0.00,0.00,1.00,1.00 | 0.363 | 0.988 | 0.065 |
| 20260426T234547Z-ltx-api-ltx-2-fast-official-ltx2-fast-text-preservation-1920x1080 | ltx-api-ltx-2-fast | last | not-crop-explainable | 0.255 | 1.00 | 0.00,0.00,1.00,1.00 | 0.363 | 0.988 | 0.065 |
| 20260426T233957Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-preservation-1920x1080 | ltx-api-ltx-2-3-fast | first | near-copy | 0.743 | 1.00 | 0.00,0.00,1.00,1.00 | 0.320 | 0.974 | 0.143 |
| 20260426T233957Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-preservation-1920x1080 | ltx-api-ltx-2-3-fast | mid | not-crop-explainable | 0.233 | 1.00 | 0.00,0.00,1.00,1.00 | 0.320 | 0.974 | 0.143 |
| 20260426T233957Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-preservation-1920x1080 | ltx-api-ltx-2-3-fast | last | not-crop-explainable | 0.235 | 1.00 | 0.00,0.00,1.00,1.00 | 0.320 | 0.974 | 0.143 |
| 20260426T234111Z-ltx-api-ltx-2-3-fast-official-ltx-api-naturalist-1920x1080 | ltx-api-ltx-2-3-fast | first | near-copy | 0.771 | 1.00 | 0.00,0.00,1.00,1.00 | 0.063 | 0.984 | 0.095 |
| 20260426T234111Z-ltx-api-ltx-2-3-fast-official-ltx-api-naturalist-1920x1080 | ltx-api-ltx-2-3-fast | mid | partially-crop-explainable | 0.351 | 1.00 | 0.00,0.00,1.00,1.00 | 0.063 | 0.984 | 0.095 |
| 20260426T234111Z-ltx-api-ltx-2-3-fast-official-ltx-api-naturalist-1920x1080 | ltx-api-ltx-2-3-fast | last | partially-crop-explainable | 0.355 | 1.10 | 0.04,0.04,0.91,0.91 | 0.063 | 0.984 | 0.095 |
| 20260427T235031Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-lastframe-1920x1080 | ltx-api-ltx-2-3-fast | first | near-copy | 0.854 | 1.00 | 0.00,0.00,1.00,1.00 | 0.686 | 0.990 | 0.102 |
| 20260427T235031Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-lastframe-1920x1080 | ltx-api-ltx-2-3-fast | mid | partially-crop-explainable | 0.455 | 1.00 | 0.00,0.00,1.00,1.00 | 0.686 | 0.990 | 0.102 |
| 20260427T235031Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-lastframe-1920x1080 | ltx-api-ltx-2-3-fast | last | near-copy | 0.931 | 1.00 | 0.00,0.00,1.00,1.00 | 0.686 | 0.990 | 0.102 |
| 20260425T144658Z-fal-kling-fal-kling-naturalist-etching-960x540-960x540 | kling | first | near-copy | 0.997 | 1.00 | 0.00,0.00,1.00,1.00 | 0.038 | 0.999 | 0.015 |
| 20260425T144658Z-fal-kling-fal-kling-naturalist-etching-960x540-960x540 | kling | mid | near-copy | 0.916 | 1.00 | 0.00,0.00,1.00,1.00 | 0.038 | 0.999 | 0.015 |
| 20260425T144658Z-fal-kling-fal-kling-naturalist-etching-960x540-960x540 | kling | last | near-copy | 0.939 | 1.00 | 0.00,0.00,1.00,1.00 | 0.038 | 0.999 | 0.015 |
| 20260427T004208Z-track-b-hybrid-naturalist-ffmpeg-drift-121-klingish-prefit-copy-960x540 |  | first | near-copy | 0.998 | 1.00 | 0.00,0.00,1.00,1.00 | 0.070 | 1.000 | 0.017 |
| 20260427T004208Z-track-b-hybrid-naturalist-ffmpeg-drift-121-klingish-prefit-copy-960x540 |  | mid | near-copy | 0.785 | 1.00 | 0.00,0.00,1.00,1.00 | 0.070 | 1.000 | 0.017 |
| 20260427T004208Z-track-b-hybrid-naturalist-ffmpeg-drift-121-klingish-prefit-copy-960x540 |  | last | near-copy | 0.999 | 1.00 | 0.00,0.00,1.00,1.00 | 0.070 | 1.000 | 0.017 |

## Reading

- `near-copy`: frame is mostly the source plate.
- `camera-zoom-like`: frame is largely explainable as a zoom/crop of the source.
- `partially-crop-explainable`: model keeps some source geometry but also repaints or warps.
- `not-crop-explainable`: frame no longer maps cleanly to the source image.
