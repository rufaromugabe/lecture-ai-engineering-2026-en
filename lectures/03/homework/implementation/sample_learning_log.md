# LoRA vs QLoRA

## 2026-11-05 00:42

- **LoRA (Low-Rank Adaptation):** Freezes the pretrained base model weights and trains only small low-rank matrices (adapters) to represent weight updates. This drastically reduces the number of trainable parameters and saves storage.
- **QLoRA (Quantized LoRA):** Combines LoRA with weight quantization (e.g., quantizing the base model weights to 4 bits). This further reduces memory consumption, enabling larger models to be fine-tuned on smaller GPUs.

## 2026-11-05 00:42

- **LoRA (Low-Rank Adaptation):** Freezes the pretrained base model weights and trains only small low-rank matrices (adapters) to represent weight updates. This drastically reduces the number of trainable parameters and saves memory.
- **QLoRA (Quantized LoRA):** Builds upon LoRA by quantizing the base model weights to a lower precision (such as 4 bits). This further reduces memory consumption, allowing larger models to be fine-tuned on smaller GPUs.
