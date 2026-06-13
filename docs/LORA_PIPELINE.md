# ERR0RS — LoRA Fine-Tune Pipeline (owned corpus)

Goal: specialize a small **open** base model on ERR0RS's owned teaching corpus
so a local Ollama model speaks in ERR0RS's voice and domain — **without** copying
any proprietary model and **without** external-license entanglement (training data
is Eros-authored lessons only).

The Pi can't train (no GPU). Flow: **export on Pi → train off-Pi (QLoRA) →
merge → GGUF → quantize → deploy back to Ollama on the Pi.**

## 1. Data (on the Pi) — DONE
`tools/export_finetune_data.py` renders the 83 owned lessons into chat-style
instruction pairs (264 examples) at `data/finetune/err0rs_lessons.jsonl`.
Each line: `{"messages":[{"role":"user",...},{"role":"assistant",...}]}`.

## 2. Base model (off-Pi)
Pick a small, permissively-licensed instruct base that also quantizes well for
the Pi:
- **Qwen2.5-3B-Instruct** (Apache-2.0) — strong coder, good default.
- **Llama-3.2-3B-Instruct** (Llama license) — solid, you already run 3.2 on the Pi.
- **Qwen2.5-1.5B-Instruct** — if you want maximum Pi headroom over quality.

## 3. Train (off-Pi GPU — your dedicated box if it has a GPU, else Colab/RunPod)
QLoRA (4-bit) keeps VRAM small (~8-12 GB for a 3B). Fastest path is `unsloth`:

```python
from unsloth import FastLanguageModel
from trl import SFTTrainer; from transformers import TrainingArguments
import json

model, tok = FastLanguageModel.from_pretrained(
    "unsloth/Qwen2.5-3B-Instruct", max_seq_length=2048, load_in_4bit=True)
model = FastLanguageModel.get_peft_model(
    model, r=16, lora_alpha=32, lora_dropout=0.05,
    target_modules=["q_proj","k_proj","v_proj","o_proj",
                    "gate_proj","up_proj","down_proj"])

rows = [json.loads(l) for l in open("err0rs_lessons.jsonl")]
def fmt(ex): return {"text": tok.apply_chat_template(ex["messages"], tokenize=False)}
ds = [fmt(r) for r in rows]

SFTTrainer(model=model, tokenizer=tok, train_dataset=ds, dataset_text_field="text",
    args=TrainingArguments(per_device_train_batch_size=2, gradient_accumulation_steps=4,
        warmup_steps=10, num_train_epochs=2, learning_rate=2e-4, fp16=True,
        logging_steps=5, output_dir="out", optim="adamw_8bit")).train()
model.save_pretrained_merged("err0rs-merged", tok, save_method="merged_16bit")
```

## 4. Deploy back to the Pi (Ollama)
Convert the merged HF model to GGUF and quantize with llama.cpp, then register:

```bash
python llama.cpp/convert_hf_to_gguf.py err0rs-merged --outfile err0rs.gguf
./llama.cpp/llama-quantize err0rs.gguf err0rs-Q4_K_M.gguf Q4_K_M
# Modelfile:  FROM ./err0rs-Q4_K_M.gguf
ollama create err0rs-tuned -f Modelfile
```

## 5. Evaluate (close the loop)
Hold out ~20 lesson Q&A pairs; compare `err0rs-tuned` vs the base on them, plus
the XBOW validation-benchmarks as a capability check. Keep the number — it's the
evidence a grant reviewer wants.

## Honest cautions
- 264 examples is small → overfit risk. Mitigate: LoRA (not full FT), low epochs
  (1-2), and optionally blend in a slice of a general instruct set so it doesn't
  forget how to converse.
- This specializes **voice + domain recall**, not raw reasoning. A 3B will not
  reason like a frontier model — pair it with the orchestration (RAG +
  reasoning/parsing split) for the heavy lifting.
- Re-run `export_finetune_data.py` whenever lessons change, and version the
  dataset so training runs are reproducible.
