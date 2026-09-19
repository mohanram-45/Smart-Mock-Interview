# Smart Mock Interview

An adaptive AI-powered technical interview system that evaluates candidate answers using multiple NLP and deep-learning scoring approaches and dynamically adjusts interview difficulty based on performance.

The system supports technical interview preparation across **Machine Learning, Deep Learning, NLP, Python, SQL and Data Analysis** using a curated knowledge base of **4,085 interview questions**.

## Key Features

- Adaptive Easy → Medium → Hard interview progression
- Role-based and custom-domain interviews
- Three interchangeable answer-scoring models
- Performance-based question progression
- Automatic feedback generation
- Question skipping and repetition handling
- Session-level performance tracking
- Automated interview report generation
- PDF and email report delivery
- Modular data ingestion, cleaning and transformation pipeline

## Answer Scoring Models

The system provides three independent scoring approaches through a unified model registry.

### 1. Siamese Bi-LSTM

Custom neural network trained on the project's interview dataset for answer similarity scoring.

### 2. Sentence-BERT

Uses the pretrained `all-MiniLM-L6-v2` sentence-transformer model to measure semantic similarity between candidate and reference answers.

This allows semantically correct answers to receive appropriate scores even when their wording differs from the reference answer.

### 3. TF-IDF + Grammar

Traditional machine-learning approach based on textual similarity with additional grammar analysis.

It provides a lightweight baseline against which the neural approaches can be compared.

## System Architecture

```text
                 Candidate
                     │
                     ▼
             Interview Session
                     │
          Role / Domain Selection
                     │
                     ▼
              Question Engine
                     │
              Easy → Medium → Hard
                     │
                     ▼
               Model Registry
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
 Siamese Bi-LSTM  Sentence-BERT  TF-IDF
        │            │            │
        └────────────┼────────────┘
                     ▼
              Answer Score
                 0 – 100%
                     │
                     ▼
            Feedback Generator
                     │
                     ▼
          Adaptive Progression
                     │
                     ▼
             Interview Report
                     │
              ┌──────┴──────┐
              ▼             ▼
             PDF           Email
```

## Adaptive Interview Engine

For Sentence-BERT and TF-IDF sessions, interview progression responds to candidate performance.

The system:

1. Starts with an Easy question batch.
2. Calculates performance across answered questions.
3. Compares the average score against the configured threshold.
4. Progresses when the threshold is reached.
5. Adds additional questions when more evidence is required.
6. Uses fallback behaviour when the extra-question limit is reached.
7. Continues through Medium and Hard rounds.

The Siamese Bi-LSTM mode uses a fixed Easy → Medium → Hard curriculum.

## Dataset

The current processed knowledge base contains **4,085 questions**.

| Domain | Questions |
|---|---:|
| Machine Learning | 851 |
| Deep Learning | 710 |
| NLP | 649 |
| Python | 628 |
| SQL | 642 |
| Data Analysis | 605 |

### Difficulty Distribution

| Difficulty | Questions |
|---|---:|
| Easy | 1,226 |
| Medium | 1,838 |
| Hard | 1,021 |

Dataset validation currently reports:

```text
Duplicate questions:        0
Missing answers:            0
Invalid difficulty labels:  0
```

## Data Pipeline

```text
Raw Interview Data
        │
        ▼
   Data Ingestion
        │
        ▼
    Data Cleaning
        │
        ▼
 Data Transformation
        │
        ▼
     Validation
        │
        ▼
Processed Knowledge Base
        │
        ▼
 Interview Application
```

## Project Structure

```text
SMART-MOCK-INTERVIEW/
│
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
│
├── src/
│   ├── components/
│   │   ├── data_ingestion.py
│   │   ├── data_cleaner.py
│   │   ├── data_transformation.py
│   │   ├── interview_session.py
│   │   ├── feedback_generator.py
│   │   └── report_generator.py
│   │
│   └── model/
│       ├── SiameseBiLSTM.py
│       ├── Pretrained_NEURALN.py
│       ├── TraditionalMLScorer.py
│       └── model_registry.py
│
├── frontend/
├── report_delivery/
├── scripts/
├── notebooks/
├── requirements.txt
└── README.md
```

## Technology Stack

**Machine Learning & NLP**

- Python
- PyTorch
- Sentence-BERT / Sentence Transformers
- TF-IDF
- Siamese Bi-LSTM
- Scikit-learn
- Pandas
- NumPy

**Application**

- Python backend
- HTML / JavaScript frontend

**Reporting**

- Automated interview reports
- PDF generation
- Email delivery

**Engineering**

- Git / GitHub
- Modular Python architecture
- Model registry and reusable scoring interface

## Future Development

The next major version will extend the answer-evaluation architecture with:

- Retrieval-Augmented Generation (RAG)
- Vector embeddings and semantic retrieval
- FAISS vector search
- LLM-based structured evaluation
- FastAPI API layer
- Docker containerisation
- Experiment tracking and evaluation

These components are part of the development roadmap and are not presented as current production features.

## Author

**Mohan Ramamurthy**

MSc Data Science  
University of Hertfordshire

## License

Licensed under the MIT License.