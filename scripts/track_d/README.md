# Track D Scripts

Track D moves from one-page renderer overfitting to a general neural canvas compiler.

## Fixture Generator

Generate a deterministic synthetic identity suite:

```bash
python3 scripts/track_d/generate_fixtures.py --count 21
```

Outputs:

- `fixtures/track-d/manifest.jsonl`
- `fixtures/track-d/summary.json`
- `fixtures/track-d/pages/*.png`
- `fixtures/track-d/metadata/*.json`

Each metadata file includes the expected text string, text regions, semantic regions, split, template, seed, and a proposed motion program. These fixtures are for held-out generalization pressure, not final product quality.
