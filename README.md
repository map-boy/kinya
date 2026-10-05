# Kinya / Wandaa Brain
One model: caller message -> `<reply>` + `<route .../>`. All behaviour is config:
- configs/policy.yaml   admin rules, limits, security, fallback route, red-team tests
- configs/taxonomy.yaml departments / issues / urgency
- configs/sources.yaml  data sources (local, hf, http)
- configs/project.yaml  stages, training, eval gates, Hugging Face repos

Laptop: `python -m kinya run` (collect, clean, corpus, synth, sft) then `python -m kinya run push`
Review: edit data/review/done.jsonl, then `python -m kinya run review`
GPU (Colab/Kaggle): open `/home/runner/work/kinya/kinya/notebooks/kinya_train.ipynb` (production preflight + pull -> train -> eval -> push)
Talk to it: `python -m kinya chat` (GPU)  |  Report: reports/latest.json + eval_*.md

## Secrets vault
- Secrets are resolved in this order: environment variables -> Colab Secrets -> Kaggle Secrets.
- Required for Hugging Face sync: `HF_TOKEN` (or `HUGGINGFACE_HUB_TOKEN`).
- Required for synthetic dialogue generation: `MISTRAL_API_KEY`.
- If a secret is missing, stages fail/skip with explicit messages instead of silent errors.