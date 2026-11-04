| Var | Q | run | tool calls in order (S=search_glossary, L=get_lecture_summary) | #calls | requests | input tok | 'not in glossary' | ends with Lecture NN | ends with '?' |
|---|---|---|---|---|---|---|---|---|---|
| V0 | Q1 | 1 | S(LoRA) → S(QLoRA) | 2 | 2 | 1369 | no | yes | no |
| V0 | Q1 | 2 | S(LoRA) → S(QLoRA) | 2 | 2 | 1369 | no | yes | no |
| V0 | Q2 | 1 | S(PEFT) → S(LoRA) → S(rank) → S(quantization) | 4 | 2 | 1628 | no | yes | no |
| V0 | Q2 | 2 | S(PEFT) → S(LoRA) → S(rank) → S(quantization) | 4 | 2 | 1628 | no | yes | no |
| V0 | Q3 | 1 | S(RLHF) | 1 | 2 | 893 | yes | no | no |
| V0 | Q3 | 2 | S(RLHF) | 1 | 2 | 893 | yes | yes | no |
| V0 | Q4 | 1 | L(3) → S(harness) | 2 | 2 | 1394 | no | yes | no |
| V0 | Q4 | 2 | L(3) → S(harness) | 2 | 2 | 1394 | no | yes | no |
| V1 | Q1 | 1 | S(LoRA) → S(QLoRA) | 2 | 2 | 1327 | no | yes | no |
| V1 | Q1 | 2 | S(LoRA) → S(QLoRA) | 2 | 2 | 1327 | no | yes | no |
| V1 | Q2 | 1 | S(PEFT) → S(LoRA) → S(rank) → S(quantization) | 4 | 2 | 1586 | no | yes | no |
| V1 | Q2 | 2 | S(PEFT) → S(LoRA) → S(rank) → S(quantization) | 4 | 2 | 1586 | no | yes | no |
| V1 | Q3 | 1 | S(RLHF) → L(12) → L(5) → L(3) → L(2) → L(1) | 6 | 7 | 8091 | yes | yes | no |
| V1 | Q3 | 2 | S(RLHF) → L(1) → L(2) → S(Reinforcement Learning from Human Feedback) → L(7) → L(5) | 6 | 7 | 7889 | yes | yes | no |
| V1 | Q4 | 1 | L(3) → S(harness) | 2 | 2 | 1352 | no | yes | no |
| V1 | Q4 | 2 | L(3) → S(harness) | 2 | 2 | 1352 | no | yes | no |
| V2 | Q1 | 1 | S(LoRA QLoRA) | 1 | 2 | 1086 | no | yes | no |
| V2 | Q1 | 2 | S(LoRA QLoRA) | 1 | 2 | 1086 | no | yes | no |
| V2 | Q2 | 1 | S(PEFT LoRA rank quantization) → S(quantization QLoRA) | 2 | 3 | 2120 | no | yes | no |
| V2 | Q2 | 2 | S(PEFT LoRA rank quantization) → S(quantization) | 2 | 3 | 1922 | no | yes | no |
| V2 | Q3 | 1 | S(RLHF) | 1 | 2 | 901 | yes | no | no |
| V2 | Q3 | 2 | S(RLHF) | 1 | 2 | 901 | yes | no | no |
| V2 | Q4 | 1 | L(3) → S(harness) | 2 | 2 | 1402 | no | yes | no |
| V2 | Q4 | 2 | L(3) → S(harness) | 2 | 2 | 1402 | no | yes | no |
| V3 | Q1 | 1 | S(LoRA) → S(QLoRA) | 2 | 2 | 1369 | no | no | no |
| V3 | Q1 | 2 | S(LoRA) → S(QLoRA) | 2 | 2 | 1369 | no | no | yes |
| V3 | Q2 | 1 | S(PEFT) → S(LoRA) → S(rank) → S(quantization) | 4 | 2 | 1628 | no | no | yes |
| V3 | Q2 | 2 | S(PEFT) → S(LoRA) → S(rank) → S(quantization) | 4 | 2 | 1628 | no | no | yes |
| V3 | Q3 | 1 | S(RLHF) | 1 | 2 | 893 | yes | no | yes |
| V3 | Q3 | 2 | S(RLHF) | 1 | 2 | 893 | yes | no | yes |
| V3 | Q4 | 1 | L(3) → S(harness) | 2 | 2 | 1394 | no | no | yes |
| V3 | Q4 | 2 | L(3) → S(harness) | 2 | 2 | 1394 | no | no | yes |
| V4 | Q1 | 1 | S(LoRA) → S(QLoRA) | 2 | 2 | 1315 | no | yes | no |
| V4 | Q1 | 2 | S(LoRA) → S(QLoRA) | 2 | 2 | 1315 | no | yes | no |
| V4 | Q2 | 1 | S(PEFT) → S(LoRA) → S(rank) → S(quantization) | 4 | 2 | 1574 | no | yes | no |
| V4 | Q2 | 2 | S(PEFT) → S(LoRA) → S(quantization) → S(rank) | 4 | 2 | 1574 | no | yes | no |
| V4 | Q3 | 1 | S(RLHF) → S(Reinforcement Learning from Human Feedback) → L(7) → L(5) → L(3) → L(2) → L(1) | 7 | 8 | 8817 | no | no | no |
| V4 | Q3 | 2 | S(RLHF) → S(Reinforcement Learning from Human Feedback) → L(7) → L(1) → L(2) → L(3) → L(5) | 7 | 8 | 8597 | no | yes | no |
| V4 | Q4 | 1 | L(3) → S(harness) | 2 | 2 | 1340 | no | yes | no |
| V4 | Q4 | 2 | L(3) → S(harness) | 2 | 2 | 1340 | no | yes | no |
| V5 | Q1 | 1 | S(LoRA) → S(QLoRA) | 2 | 2 | 1325 | no | yes | no |
| V5 | Q1 | 2 | S(LoRA) → S(QLoRA) | 2 | 2 | 1325 | no | yes | no |
| V5 | Q2 | 1 | S(PEFT) → S(LoRA) → S(rank) → S(quantization) | 4 | 2 | 1584 | no | no | no |
| V5 | Q2 | 2 | S(PEFT) → S(LoRA) → S(rank) → S(quantization) | 4 | 2 | 1584 | no | yes | no |
| V5 | Q3 | 1 | S(RLHF) | 1 | 2 | 849 | yes | no | no |
| V5 | Q3 | 2 | S(RLHF) | 1 | 2 | 849 | yes | no | no |
| V5 | Q4 | 1 | L(3) → S(harness) | 2 | 2 | 1350 | no | yes | no |
| V5 | Q4 | 2 | L(3) → S(harness) | 2 | 2 | 1350 | no | yes | no |
| V6 | Q1 | 1 | S(LoRA) → S(QLoRA) | 2 | 2 | 1283 | no | yes | no |
| V6 | Q1 | 2 | S(LoRA) → S(QLoRA) | 2 | 2 | 1283 | no | yes | no |
| V6 | Q2 | 1 | S(PEFT) → S(rank) → S(quantization) | 3 | 4 | 2610 | no | yes | no |
| V6 | Q2 | 2 | S(PEFT) → S(LoRA) → S(rank) → S(quantization) | 4 | 2 | 1542 | no | yes | no |
| V6 | Q3 | 1 | S(RLHF) | 1 | 2 | 807 | yes | no | no |
| V6 | Q3 | 2 | S(RLHF) → L(1) → L(2) → L(3) → L(4) → L(5) | 6 | 7 | 8836 | yes | yes | no |
| V6 | Q4 | 1 | L(3) → S(harness) | 2 | 2 | 1308 | no | yes | no |
| V6 | Q4 | 2 | L(3) → S(harness) | 2 | 2 | 1308 | no | yes | no |
