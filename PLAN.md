# TenderHackMoscow - Detailed Development Plan (48 Hours)

## Team Allocation
- **Dev 1 (Cursor Agent / Lead)**: Backend, Frontend, Data Engineering, Infrastructure, Integration, BPMN.
- **Dev 2 (ML Specialist)**: NLP, Semantic Search, ML Ranking, Personalization, Explainability, Metrics.

---

## Phase 1: Setup & Data Preparation (Hours 0-6)

### Dev 1 (Infra & Data)
- **Infrastructure**: Set up Docker Compose with PostgreSQL (with `pgvector` for embeddings) or self-hosted Elasticsearch/OpenSearch, and FastAPI backend.
- **Data Parsing**: Parse the provided datasets (Contracts and STE).
- **Data Modeling**: Create DB schemas for STE, Users (Customers), Contracts, and Interaction Logs (clicks, views, skips).
- **Initial Load**: Clean and load STE and Contracts data into the database.

### Dev 2 (ML / NLP Foundation)
- **Metrics Research**: Define and justify evaluation metrics (e.g., NDCG@K, MRR, MAP) for the 10-point criteria.
- **NLP Pipeline Setup**: Implement lightweight morphology (e.g., `pymorphy2` or `natasha`), typo correction (e.g., `symspell` or fastText based), and synonym dictionaries.
- **Semantic Model Selection**: Download and test a lightweight embedding model (e.g., `cointegrated/rubert-tiny2` - extremely fast inference, fits the "lightweight" constraint perfectly).

---

## Phase 2: Core Search Engine (Hours 6-18)

### Dev 1 (Backend & Search API)
- **Search API**: Create FastAPI endpoints for search queries.
- **Event Logging API**: Create endpoints to log user behavior (clicks, add to compare, quick returns/bounces).
- **Integration**: Connect the NLP pipeline (from Dev 2) to the search endpoint.

### Dev 2 (Semantic & Base Ranking)
- **Vectorization**: Generate embeddings for all STE names and attributes using the lightweight model.
- **Hybrid Search**: Combine lexical search (BM25 / TF-IDF with morphology) and semantic search (vector similarity).
- **Base Ranking**: Ensure the base search returns highly accurate results before personalization.

---

## Phase 3: Personalization & Dynamic Indexing (Hours 18-30)

### Dev 1 (Frontend & State Management)
- **UI Development**: Start building the web interface using the provided Figma UI kit.
- **Session Management**: Implement user sessions (mocking different INNs) to demonstrate personalization.
- **Frontend Tracking**: Add event listeners on the frontend to send behavioral data (clicks, dwell time, bounces) to the Event Logging API.

### Dev 2 (ML Ranking & Explainability)
- **Feature Engineering**: Extract features for Learning-to-Rank (LTR).
  - *User Features*: Past categories bought, average price, region.
  - *Item Features*: Popularity, category.
  - *Interaction Features*: Clicks, negative signals (quick returns).
- **Model Training**: Train a lightweight ranking model (e.g., CatBoost Ranker).
- **Dynamic Indexing Logic**: Implement a mechanism to adjust user profile vectors or feature weights in real-time based on the latest session events.
- **Explainability Module**: Implement logic to return *reasons* for ranking (e.g., "Ranked high because: matches your contract history in 'Stationery'", or using SHAP values for feature importance).

---

## Phase 4: Integration & Refinement (Hours 30-38)

### Dev 1 (Full Stack Integration)
- **UI Polish**: Ensure the UI clearly shows typo corrections ("Showing results for X instead of Y") and explainability tags on product cards.
- **System Testing**: End-to-end testing of the search flow.
- **BPMN Schema**: Draft the BPMN schema showing the User Lane (search, click, bounce) and System Lane (NLP, Vector Search, CatBoost Ranking, Profile Update).

### Dev 2 (ML Tuning)
- **Model Optimization**: Ensure inference time is extremely low (caching embeddings, optimizing CatBoost inference).
- **Edge Cases**: Handle homographs (words with multiple meanings) by using user context (e.g., if user INN is a hospital, "ручка" means door handle, if school, "ручка" means pen).

---

## Phase 5: Final Polish & Presentation (Hours 38-48)

### Dev 1 & Dev 2 Together
- **Real Case Scenarios**: Prepare specific demo scripts.
  - *Scenario 1*: Typo & Synonym handling.
  - *Scenario 2*: Personalization (User A sees item X first, User B sees item Y first).
  - *Scenario 3*: Dynamic Indexing (User clicks item, returns quickly -> negative signal -> next search ranks similar items lower).
- **Presentation**: Finalize the 5-minute pitch, BPMN schema, and metrics justification.
- **Deployment**: Ensure everything runs smoothly on the Ubuntu server via Docker.