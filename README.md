# Awesome LLM Papers for Reading

A curated reading map for large language model papers, with bilingual paper notes, formula rendering, figure captions, and reader-oriented paths for engineers, students, and teachers.

Live site: https://hugoean.github.io/papers-reader/

## What This Is

This project is not just a link list. It is a structured paper reader for learning how modern LLMs are built, trained, aligned, evaluated, and documented.

The current collection includes 35 papers and technical reports across five themes:

- Data engineering: corpus construction, filtering, deduplication, data mixture, and multilingual data.
- Continual pre-training: domain adaptation, replay, learning-rate restart, and scaling-law background.
- Post-training: RLHF, DPO, SimPO, GRPO, DAPO, distillation, and reasoning-oriented alignment.
- Technical reports: DeepSeek, Qwen, Kimi, Llama, MiniMax, GLM, MiMo, Yi, and other model reports.
- Foundations and surveys: scaling laws, Chinchilla, weak supervision, long CoT, and LLM data surveys.

## Why It Exists

LLM papers are often hard to read in isolation. A single paper may assume knowledge of data pipelines, RLHF, scaling laws, evaluation, or model architecture details. This reader organizes the papers into learning paths so the reader can understand both the paper itself and its place in the broader training stack.

The site is designed for three kinds of readers:

- Engineers who want practical ideas for training and data pipelines.
- Students preparing for LLM algorithm interviews.
- Teachers or researchers who need a coherent course-style reading sequence.

## Features

- 35 curated LLM papers and technical reports.
- Bilingual reading pages with original concepts preserved.
- Local figure assets for stable reading.
- Chinese figure explanations and paper notes.
- KaTeX support for formulas.
- Filters by theme, audience, and reading priority.
- Static HTML deployment through Hexo and GitHub Pages.

## Local Development

Install dependencies:

```bash
npm ci
```

Build the static site:

```bash
npm run build
```

Run locally:

```bash
npm run server
```

Then open the local URL printed by Hexo.

## Project Structure

```text
source/papers-reader/
├── index.html          # Reading map homepage
├── papers/             # Individual paper pages
└── figures/            # Local figure assets

paper_queue/
├── source/             # Full prepared paper source pool
├── audit/              # Per-paper audit reports
├── pool.json           # Unpublished queue
├── published.json      # Published history
└── error_pool.json     # Papers that failed audit or publishing

tools/
└── publish_next_paper.py
```

## Publishing

Build:

```bash
npm run build
```

Deploy to GitHub Pages:

```bash
npm run deploy
```

The deployment target is configured in `_config.yml`.

## Naming Note

The project name uses `Awesome LLM Papers for Reading`.

`Awesome` is commonly used on GitHub for curated collections. `Papers` is plural because this is a collection, and `for Reading` emphasizes that the project provides a guided reading experience rather than only a bibliography.

## License

This repository contains reading notes and generated static pages for personal study and educational use. Original papers and figures belong to their respective authors and publishers.
