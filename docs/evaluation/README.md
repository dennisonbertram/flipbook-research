# Evaluation

This directory defines how Flipbook-style neural canvas experiments are judged.

The core evaluation principle is:

```text
same world representation -> many views/times -> stable identity and fast pixels
```

Every model or renderer experiment should write artifacts that can be compared against this contract.

