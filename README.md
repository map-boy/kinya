# Kinya / Wandaa Brain
One model: caller message -> `<reply>` + `<route .../>`. All behaviour is config:
- configs/policy.yaml   admin rules, limits, security, fallback route, red-team tests
- configs/taxonomy.yaml departments / issues / urgency
- configs/sources.yaml  data sources (local, hf, http)
- configs/project.yaml  stages, training, eval gates, Hugging Face repos

Laptop: `python -m kinya run` (collect, clean, corpus, synth, sft) then `python -m kinya run push`
Review: edit data/review/done.jsonl, then `python -m kinya run review`
GPU (Colab/Kaggle): open notebooks/kinya_train.ipynb  (pull -> train -> eval -> push)
Talk to it: `python -m kinya chat` (GPU)  |  Report: reports/latest.json + eval_*.md