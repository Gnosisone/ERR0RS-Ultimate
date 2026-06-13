#!/usr/bin/env python3
"""QLoRA fine-tune ERR0RS on the OWNED lesson corpus.  *** RUN OFF-PI ***
Needs a CUDA GPU (~8-12 GB for a 3B). The Pi cannot run this.

  pip install -r requirements-finetune.txt
  python3 tools/train_lora.py --data data/finetune/err0rs_lessons.jsonl \
        --base unsloth/Qwen2.5-3B-Instruct --out err0rs-merged
  bash tools/deploy_tuned.sh err0rs-merged     # -> GGUF -> ollama create err0rs-tuned
"""
import argparse, json

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/finetune/err0rs_lessons.jsonl")
    ap.add_argument("--base", default="unsloth/Qwen2.5-3B-Instruct")
    ap.add_argument("--out",  default="err0rs-merged")
    ap.add_argument("--epochs",  type=float, default=2.0)
    ap.add_argument("--max-seq", type=int,   default=4096)   # longest lesson ~3k tokens
    ap.add_argument("--lr",      type=float, default=2e-4)
    a = ap.parse_args()

    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments
    from datasets import Dataset

    model, tok = FastLanguageModel.from_pretrained(
        a.base, max_seq_length=a.max_seq, load_in_4bit=True)
    model = FastLanguageModel.get_peft_model(
        model, r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
        use_gradient_checkpointing="unsloth",
        target_modules=["q_proj","k_proj","v_proj","o_proj",
                        "gate_proj","up_proj","down_proj"])

    rows  = [json.loads(l) for l in open(a.data, encoding="utf-8")]
    texts = [tok.apply_chat_template(r["messages"], tokenize=False) for r in rows]
    ds    = Dataset.from_dict({"text": texts})
    print(f"training on {len(texts)} examples, base={a.base}, max_seq={a.max_seq}")

    SFTTrainer(
        model=model, tokenizer=tok, train_dataset=ds,
        dataset_text_field="text", max_seq_length=a.max_seq,
        args=TrainingArguments(
            per_device_train_batch_size=2, gradient_accumulation_steps=4,
            warmup_steps=10, num_train_epochs=a.epochs, learning_rate=a.lr,
            fp16=True, logging_steps=5, optim="adamw_8bit",
            weight_decay=0.01, lr_scheduler_type="linear",
            output_dir="lora_out", seed=42),
    ).train()

    model.save_pretrained_merged(a.out, tok, save_method="merged_16bit")
    print(f"merged model -> {a.out}/   next: bash tools/deploy_tuned.sh {a.out}")

if __name__ == "__main__":
    main()
