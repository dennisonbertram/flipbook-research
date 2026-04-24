"""Track A model recipes.

Recipes expose two optional functions:

- setup(config) -> state
- generate(input_image, config, state) -> dict

The benchmark owns preprocessing, encoding, metrics, and artifact layout.
Recipes should stay focused on the model-layer experiment.
"""
