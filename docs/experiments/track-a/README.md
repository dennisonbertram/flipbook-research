# Track A Experiment Logs

Track A experiment rows should be logged as TSV so descriptions can contain commas without breaking parsing.

Create `results.tsv` with this header when the first benchmark harness exists:

```text
run_id	commit	resolution	wall_time_ms	model_ms	decode_ms	encode_ms	peak_vram_gb	text_score	layout_score	motion_score	loop_error	status	description
```

Large videos, generated frames, and raw metric JSON should live under `outputs/`, with only compact summaries kept here.
