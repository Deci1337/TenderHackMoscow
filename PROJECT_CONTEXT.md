# TenderHackMoscow - Project Context & Pitch Notes

## Core Objective
Deliver a real, working, and fast personalized smart search service for the "Portal of Suppliers" (zakupki.mos.ru).

## Key Constraints & Technical Requirements (UPDATED FROM TZ)
1. **OS & UI**: Must work on Linux and provide a web interface.
2. **NO EXTERNAL APIs**: The system must run EXCLUSIVELY on servers controlled by our team. Complete ban on:
   - External search engines (Yandex.Search, Google Search API, Bing Search API).
   - External LLM APIs (OpenAI GPT, Google Gemini, Anthropic Claude).
3. **NO LOW-CODE/NO-CODE**: Custom development only.
4. **OPEN ML MODELS ALLOWED BUT MUST BE LIGHTWEIGHT**: We can use open-source ML models and neural networks, but the choice must be rational. Preference is given to **lightweight solutions with high inference speed** under limited compute. Unjustified use of "heavy" models will reduce the final score.

## Data Sources (Dataset Structure)
- **Contracts**: Purchase name, Contract ID, STE ID, Contract date, Contract cost, Customer INN, Customer name, Customer region, Supplier INN, Supplier name, Supplier region.
- **STE (Standard Trade Unit)**: STE ID, Name, Category, Attributes.
- **Figma UI Kit**: Provided for frontend design.

## Search & ML Features
1. **Personalized Semantic & Morphological Search**: Rank results based on user history (purchases) and catalog interactions.
2. **Explainability**: 
   - Explain *why* search results differ across sessions.
   - Show *what* user actions influenced the ranking.
3. **NLP**: Show how the system corrects typos and uses synonyms for precise STE matching.
4. **Dynamic Indexing**: Real-time adaptation. E.g., after visiting a product card (or quickly returning to search - a negative signal), the subsequent search results for similar queries must change according to this behavior.

## Evaluation Criteria (100 Points Total)
1. **Working Prototype** – 40 points.
2. **Semantic & Morphological Search Accuracy** (including synonyms and typos) – 25 points.
3. **Personalization Quality** (history, behavioral factors: clicks, target actions, negative signals) – 25 points.
4. **Metrics Justification** (justifying the metrics used to evaluate personalized search quality) – 10 points.

## Defense Timeline & Deliverables
- **Stage 1**: 5-minute presentation with BPMN schema (user lane + system lane) + parallel demo of real cases. Max 100 points.
- **Stage 2**: Top-5 teams. Repo links submission. 10-minute presentation + BPMN, 10-minute Q&A.
- **Deliverables**: Working prototype, BPMN schema, justified metrics list, scalability plan.