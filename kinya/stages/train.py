from ..registry import stage

CHAT_TEMPLATE = r"""{% for m in messages %}{% if m['role'] == 'system' %}{{ m['content'] + '\n\n' }}{% elif m['role'] == 'user' %}{{ '[INST] ' + m['content'] + ' [/INST]' }}{% else %}{{ ' ' + m['content'] + eos_token }}{% endif %}{% endfor %}"""

@stage("train")
def run(proj):
    """GPU machine only. Needs: pip install unsloth trl datasets"""
    import torch
    from unsloth import FastLanguageModel
    from datasets import load_dataset
    from trl import SFTTrainer, SFTConfig
    c = proj.stage_cfg("train"); data = proj.path("data")
    files = ({"train": str(data / "corpus/cpt_train.jsonl"), "validation": str(data / "corpus/cpt_val.jsonl")}
             if c["mode"] == "cpt" else
             {"train": str(data / "sft/sft_train.jsonl"), "validation": str(data / "sft/sft_val.jsonl")})
    ds = load_dataset("json", data_files=files)
    model, tok = FastLanguageModel.from_pretrained(c["base_model"], max_seq_length=c["max_seq"], load_in_4bit=c.get("load_in_4bit", True))
    if not getattr(tok, "chat_template", None):
        tok.chat_template = CHAT_TEMPLATE
    model = FastLanguageModel.get_peft_model(model, r=c["lora_r"], lora_alpha=c["lora_alpha"], target_modules=c["target_modules"],
                                             lora_dropout=0, bias="none", use_gradient_checkpointing="unsloth")
    out = proj.path("models") / c["run_name"]
    args = SFTConfig(output_dir=str(out / "ckpt"), per_device_train_batch_size=c["batch_size"], gradient_accumulation_steps=c["grad_accum"],
                     learning_rate=c["lr"], num_train_epochs=c["epochs"], logging_steps=c["logging_steps"], save_steps=c["save_steps"],
                     eval_strategy="steps", eval_steps=c["save_steps"], bf16=torch.cuda.is_bf16_supported(), fp16=not torch.cuda.is_bf16_supported(),
                     report_to="none", **({"dataset_text_field": "text"} if c["mode"] == "cpt" else {}))
    tr = SFTTrainer(model=model, tokenizer=tok, train_dataset=ds["train"], eval_dataset=ds["validation"], args=args)
    ckpts = list((out / "ckpt").glob("checkpoint-*")) if (out / "ckpt").exists() else []
    tr.train(resume_from_checkpoint=bool(ckpts))
    model.save_pretrained(str(out)); tok.save_pretrained(str(out))
    if c.get("hub_repo"):
        model.push_to_hub(c["hub_repo"]); tok.push_to_hub(c["hub_repo"])
    return {"saved": str(out), "train_rows": len(ds["train"])}