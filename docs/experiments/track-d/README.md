# Track D Experiments

Track D tests whether the neural canvas can become general, not just fast after overfitting one page.

Current milestone:

```text
zero-step held-out OCR >= 0.75
16-step held-out OCR >= 0.82
33 frames + encode <= 1.3s
no render-time text masks
```

First fixture suite:

```bash
python3 scripts/track_d/generate_fixtures.py --count 21
```

The generator writes a deterministic synthetic suite under `fixtures/track-d/` with train/val/test splits, template labels, text regions, semantic regions, and proposed motion programs. The immediate next model-layer task is to train an encoder or prior that predicts the Track C latent canvas initialization for held-out pages, then compare zero-step, few-step, and full-overfit compile paths.

The first suite has 21 pages: 15 train, 2 validation, and 4 test by deterministic split. Templates include article, dashboard, diagram, product grid, map labels, low-text illustration, and microtext stress pages.
