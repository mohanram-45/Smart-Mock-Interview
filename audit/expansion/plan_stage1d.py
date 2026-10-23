#!/usr/bin/env python3
"""Stage 1D planning tables (NO questions are generated here). Single source of truth for the coverage matrix and batch plan.
Writes data/expansion/plan/{coverage_matrix.csv,batch_plan.csv,domain_summary.csv,plan.json}. Usage: python audit/expansion/plan_stage1d.py [project_root]"""
import sys, re, json, math
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")
import pandas as pd
HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE.parents[1]
OUT = ROOT / "data/expansion/plan"; OUT.mkdir(parents=True, exist_ok=True)
v5 = pd.read_csv(ROOT / "data/curated/v5/curated_questions.csv", keep_default_na=False, dtype=str)
YIELD = 0.88   # planning assumption: share of generated questions that survive review/dedup (batch 03 kept 40/40 but 19/40 needed fixes; 1B/1C saw 0 quarantines)

# verification codes: X = executed test, D = official doc / paper opened, V = derivation/hand-computed, R = reasoned design rubric only
# types: concept, scenario, coding, sql, debugging, design, evaluation, business
# cell = (domain, topic, batch, target, types, verification, time_sensitive, keyword regex over existing v5 questions, boundary note)
C = []
def cell(dom, topic, batch, target, types, ver, ts, kw, note=""): C.append(dict(domain=dom, topic=topic, batch=batch, target=target, types=types, verification=ver, time_sensitive=ts, kw=kw, note=note))
G, M, E_, CL, BI, SD = "Generative AI & RAG", "MLOps & Model Deployment", "Data Engineering & Spark", "Cloud Computing (AWS/Azure)", "Power BI & Business Intelligence", "Applied AI System Design"
# ---------------- Generative AI & RAG
cell(G,"Embeddings and similarity search (metrics, normalisation, ANN: HNSW/IVF/PQ)",1,6,"concept;coding;scenario","X,D",0,r"cosine|embedding|nearest neighbo|vector","Embedding theory (word2vec, contextual) stays in NLP/DL; here: use for retrieval")
cell(G,"Chunking and document ingestion",1,5,"concept;scenario;debugging","D,V",0,r"chunk|ingest","")
cell(G,"Retrieval strategies (dense, BM25, hybrid, RRF, query rewriting, MMR)",1,7,"concept;coding;scenario","X,D",0,r"BM25|hybrid|retriev","BM25 and RRF are implemented and tested in pure Python")
cell(G,"Reranking and context assembly",1,5,"concept;scenario","D",0,r"rerank|context window","")
cell(G,"RAG evaluation (recall@k, MRR, nDCG, faithfulness, golden sets, LLM judges)",1,7,"evaluation;coding;concept","X,D",0,r"recall@|MRR|nDCG|faithful|RAGAS","Generic IR metrics already in NLP (smi-h0003 family); new questions must be RAG-specific")
cell(G,"Vector databases and index operations (filters, freshness, updates, cost)",1,5,"scenario;concept","D",1,r"vector (database|store|index)","Product-specific limits are time-sensitive and avoided")
cell(G,"RAG failure diagnosis",1,5,"debugging;scenario","V,D",0,r"hallucinat|wrong answer|retrieval","")
cell(G,"Prompting and structured output (few-shot, CoT caveats, schemas, determinism)",2,5,"concept;scenario;coding","X,D",1,r"prompt|few-shot","")
cell(G,"Tool use and agents (function calling, loops, failure modes, action guardrails)",2,6,"concept;scenario;design","D",1,r"agent|function calling|tool use","")
cell(G,"LLM evaluation (benchmarks, contamination, LLM-as-judge bias, regression suites)",2,6,"evaluation;concept","D,V",0,r"benchmark|contaminat|judge","smi-h0012 (contamination) stays in NLP")
cell(G,"Fine-tuning vs RAG vs prompting (LoRA/QLoRA, SFT, forgetting, data needs)",2,6,"concept;scenario;business","D,V",0,r"LoRA|fine-tun|adapter","smi-h0004 (LoRA) stays in NLP; new questions are decision-oriented")
cell(G,"Safety, security and privacy (prompt injection, PII, jailbreaks, red teaming)",2,5,"scenario;concept;debugging","D",1,r"injection|PII|jailbreak|privacy","")
cell(G,"Serving, latency and cost (KV cache, batching, quantisation, caching, token budgets)",2,6,"concept;coding;scenario","X,D,V",0,r"KV cache|quantis|quantiz|latency","Training-time scaling stays in Deep Learning")
cell(G,"Hallucination, grounding and long context",2,5,"concept;scenario","D",0,r"hallucinat|grounding|long context|lost in the middle","")
cell(G,"GenAI product scenarios (support bot, document QA)",2,3,"business;scenario","R",0,r"chatbot|assistant","")
# ---------------- MLOps
cell(M,"ML lifecycle and reproducibility (data/model versioning, experiment tracking, environments)",3,6,"concept;scenario;debugging","D,V",0,r"reproduc|versioning|experiment track","")
cell(M,"CI/CD for ML (data and model tests, gating, rollback)",3,6,"concept;scenario;coding","X,D",0,r"CI/CD|pipeline test|rollback","Generic software testing stays in Python (Testing)")
cell(M,"Model registry and packaging (containers, ONNX, signatures, dependency pinning)",3,5,"concept;scenario","D",0,r"registry|ONNX|packag","")
cell(M,"Serving patterns (batch, online, streaming, REST/gRPC, autoscaling, batching)",3,7,"concept;scenario;design;coding","X,D,V",0,r"serving|online inference|batch inference|latency","")
cell(M,"Deployment strategies (shadow, canary, A/B, blue-green, rollback)",3,6,"scenario;concept;evaluation","D,V",0,r"canary|shadow|blue-green|A/B","Experiment statistics stay in Data Analysis")
cell(M,"Containers and orchestration for ML (Docker, Kubernetes basics, GPU scheduling)",3,5,"concept;scenario;debugging","D",0,r"Docker|Kubernetes|container","Cloud-vendor managed services belong to Cloud")
cell(M,"Feature stores and training-serving skew",3,6,"concept;scenario;debugging","V,D",0,r"feature store|training-serving|skew","")
cell(M,"Production monitoring and drift operations (PSI/KS, delayed labels, alert design)",4,7,"scenario;evaluation;coding","X,V",0,r"drift|monitor","Drift statistics already in ML (3 records); new ones are operational")
cell(M,"Retraining and automation (triggers, continuous training, champion/challenger)",4,5,"scenario;concept","V,D",0,r"retrain|champion","")
cell(M,"Data and model validation (schema checks, slice metrics, expectations)",4,5,"coding;debugging;concept","X",0,r"validation|slice|schema","")
cell(M,"Governance, lineage and compliance (model cards, audit trails)",4,4,"concept;scenario","D",1,r"lineage|model card|governance","")
cell(M,"Reliability, SLOs, incidents and cost",4,5,"scenario;business","V",0,r"SLO|incident|cost","")
cell(M,"LLMOps specifics (prompt versioning, eval gates, token cost)",4,4,"scenario;concept","D",1,r"LLMOps|prompt version","")
cell(M,"MLOps case studies and debugging",4,6,"debugging;business;scenario","V",0,r"production","")
# ---------------- Data Engineering & Spark
cell(E_,"Spark architecture (driver, executors, DAG, stages, lazy evaluation)",5,6,"concept;scenario","D,X",0,r"\bSpark\b|MapReduce","")
cell(E_,"Partitioning, shuffles and joins (broadcast, sort-merge, skew, salting, AQE)",5,8,"coding;scenario;debugging","X,D",0,r"shuffle|partition|skew|broadcast","SQL-engine partitioning (smi SQL 'Partitioning and scaling') stays in SQL")
cell(E_,"DataFrame and Spark SQL API (windows, UDF vs built-in, pandas UDF, nulls)",5,8,"coding;concept","X,D",0,r"DataFrame|PySpark|UDF","pandas DataFrame questions stay in Python")
cell(E_,"Performance tuning and memory (caching, spill, file sizes, config)",5,7,"scenario;debugging;concept","D,V",0,r"cache|persist|spill|small files","")
cell(E_,"Structured Streaming (watermarks, triggers, state, exactly-once)",5,6,"concept;scenario;coding","X,D",0,r"streaming|watermark|exactly-once","")
cell(E_,"Spark debugging scenarios (OOM, skew, slow stage)",5,6,"debugging;scenario","X,V",0,r"OutOfMemory|OOM","")
cell(E_,"Table formats and lakehouse basics (Delta, Iceberg, ACID on files)",5,4,"concept;scenario","D",1,r"Delta|Iceberg|lakehouse","")
cell(E_,"Batch ETL/ELT design (idempotency, incremental loads, backfills, late data)",6,7,"scenario;design;coding","X,V",0,r"ETL|ELT|backfill|incremental|idempot","")
cell(E_,"Orchestration (Airflow concepts: DAGs, retries, sensors, idempotent tasks)",6,6,"concept;debugging;coding","X,D",0,r"Airflow|orchestrat|DAG","")
cell(E_,"Streaming and messaging (Kafka partitions, consumer groups, delivery semantics, ordering)",6,7,"concept;scenario;debugging","D,V",0,r"Kafka|message queue|consumer group","")
cell(E_,"File formats and storage layout (Parquet/ORC/Avro, partition layout, compaction, schema evolution)",6,7,"concept;scenario;coding","X,D",0,r"parquet|Avro|ORC|schema evolution","")
cell(E_,"Warehouse modelling (star/snowflake, SCD types, dbt-style transformations)",6,7,"sql;concept;scenario","X,V",0,r"star schema|slowly changing|SCD|snowflake schema|data warehouse","Relational design/normalisation stays in SQL; BI-tool modelling goes to Power BI & BI")
cell(E_,"Data quality, contracts and observability",6,5,"concept;scenario;coding","X,D",0,r"data quality|data contract|lineage","")
cell(E_,"CDC and integration patterns; pipeline case studies",6,8,"scenario;business;debugging","V",0,r"CDC|change data capture|ingest","")
# ---------------- Cloud
cell(CL,"AWS identity and security (IAM roles vs users, policy evaluation, least privilege, STS)",7,7,"concept;scenario;debugging","D,V",1,r"\bIAM\b|least privilege","Policy JSON syntax validated offline; evaluation logic checked against docs")
cell(CL,"AWS storage and databases (S3 classes/lifecycle, EBS/EFS, RDS vs DynamoDB, Redshift)",7,7,"concept;scenario","D",1,r"\bS3\b|DynamoDB|Redshift|\bRDS\b","")
cell(CL,"AWS compute (EC2 purchase options, autoscaling, Lambda limits, ECS/EKS/Fargate)",7,7,"concept;scenario;design","D",1,r"EC2|Lambda|serverless|Fargate","Container/K8s concepts live in MLOps; here: service choice and limits")
cell(CL,"AWS networking (VPC, subnets, security groups vs NACLs, endpoints, load balancers)",7,6,"concept;debugging;scenario","D,V",0,r"\bVPC\b|subnet|security group|load balanc","")
cell(CL,"Data and ML on AWS (Glue, EMR, Athena, Kinesis, SageMaker, Bedrock)",7,7,"scenario;design;concept","D",1,r"SageMaker|Glue|Athena|Kinesis|Bedrock","Spark internals stay in Data Engineering")
cell(CL,"Reliability, cost and observability on AWS (multi-AZ, DR, CloudWatch, cost levers)",7,5,"scenario;business","D,V",1,r"disaster recovery|multi-AZ|CloudWatch","")
cell(CL,"AWS scenario questions",7,3,"scenario;business","D",1,r"AWS","")
cell(CL,"Azure identity and security (Entra ID, RBAC, managed identity, Key Vault)",8,6,"concept;scenario","D",1,r"\bAzure\b|Entra|Key Vault","")
cell(CL,"Azure storage and data services (Blob/ADLS, Cosmos DB, SQL Database, Data Factory, Synapse/Fabric basics)",8,7,"concept;scenario","D",1,r"Blob|ADLS|Cosmos|Data Factory|Synapse","")
cell(CL,"Azure compute and containers (VMs, Functions, AKS, App Service, Container Apps)",8,5,"concept;scenario","D",1,r"AKS|Azure Functions|App Service","")
cell(CL,"Azure ML and AI services (Azure ML, Azure OpenAI, AI Search, managed endpoints)",8,6,"scenario;design","D",1,r"Azure ML|Azure OpenAI|AI Search","")
cell(CL,"Cross-cloud concepts (AWS/Azure mapping, shared responsibility, regions/AZs, IaC)",8,7,"concept;scenario;coding","X,D",0,r"shared responsibility|infrastructure as code|Terraform|CloudFormation","IaC snippets linted offline (cfn-lint / terraform validate where possible)")
cell(CL,"Cloud architecture trade-offs, cost and case studies",8,7,"business;design;scenario","D,V",1,r"cloud","")
# ---------------- Power BI & BI
cell(BI,"BI data modelling (star schema, grain, relationships, cardinality, filter direction, role-playing dimensions)",9,8,"concept;scenario;debugging","D,V",0,r"star schema|fact table|dimension table|cardinality","Warehouse-side modelling stays in Data Engineering; here: semantic-model design")
cell(BI,"DAX fundamentals (row vs filter context, CALCULATE, measures vs columns, iterators, context transition)",9,9,"concept;coding;debugging","D,V",0,r"\bDAX\b|filter context|CALCULATE","DAX cannot be run locally: verified against Microsoft docs and hand-evaluated on tiny tables; pandas equivalents are labelled illustration only")
cell(BI,"Time intelligence and DAX patterns (YTD, rolling, prior period, % of total, ranking)",9,6,"coding;scenario","D,V",0,r"year-to-date|YTD|rolling|prior period","")
cell(BI,"Power Query / M and data preparation (query folding, merges, incremental refresh)",9,6,"concept;scenario;debugging","D",0,r"Power Query|query folding|incremental refresh","")
cell(BI,"Storage modes and performance (Import, DirectQuery, composite, aggregations, VertiPaq, Performance Analyzer)",9,6,"concept;scenario;debugging","D",1,r"DirectQuery|VertiPaq|import mode","")
cell(BI,"Power BI debugging scenarios (wrong totals, blank results, slow reports)",9,5,"debugging","V,D",0,r"wrong total|blank","")
cell(BI,"Security and governance (RLS/OLS, workspaces, sensitivity labels, certified datasets, deployment pipelines)",10,6,"concept;scenario","D",1,r"row-level security|\bRLS\b","")
cell(BI,"Service operations (gateways, refresh, dataflows, capacity and licensing concepts)",10,6,"scenario;concept","D",1,r"gateway|dataflow|refresh","Licensing and limits change often: concepts only, no price or quota numbers")
cell(BI,"Visualisation and dashboard design (chart choice, drill-through, accessibility, cognitive load)",10,6,"concept;scenario;business","V,D",0,r"visuali[sz]ation|chart (type|choice)|dashboard design","Statistical communication stays in Data Analysis")
cell(BI,"KPI and metric design (definitions, metric trees, leading vs lagging, storytelling)",10,6,"business;concept","V",0,r"\bKPI\b|metric tree|north star","Product metrics and A/B stay in Data Analysis")
cell(BI,"BI business case studies (sales, finance variance, operations SLA)",10,6,"business;sql;coding","X,V",0,r"sales dashboard|variance|SLA","SQL parts are executed; DAX parts hand-evaluated")
cell(BI,"BI tool landscape and self-service vs governed analytics",10,4,"concept;business","D",1,r"Tableau|Looker|self-service","")
# ---------------- Applied AI System Design
cell(SD,"Recommendation and ranking systems end to end",11,6,"design;evaluation","R,V",0,r"recommend","Model theory stays in ML (Recommender systems, 11 records)")
cell(SD,"Enterprise search and RAG platform design",11,4,"design;scenario","R",1,r"search","Component questions stay in GenAI & RAG; here: multi-component trade-offs")
cell(SD,"Fraud and anomaly detection with real-time scoring",11,5,"design;scenario;evaluation","R,V",0,r"fraud|anomal","")
cell(SD,"ML platform: feature store, training infrastructure, model lifecycle",11,4,"design","R",0,r"platform","")
cell(SD,"Batch vs real-time prediction architectures and latency budgets",11,4,"design;scenario","R,V",0,r"latency budget|real-time","")
cell(SD,"LLM assistant or agent platform with guardrails and cost control",11,4,"design;scenario","R",1,r"assistant|agent","")
cell(SD,"Forecasting and demand planning pipeline",11,3,"design;business","R,V",0,r"forecast|demand","")
cell(SD,"Document and vision AI pipelines (OCR, classification, human in the loop)",11,3,"design;scenario","R",0,r"OCR|document","")
cell(SD,"Capacity estimation (QPS, storage, GPU, cost)",11,3,"design;coding","X,V",0,r"QPS|capacity","Back-of-envelope arithmetic is computed and tested")
cell(SD,"Design critique and trade-off review",12,6,"design;scenario","R",0,r"trade-off","")
cell(SD,"Responsible AI, privacy and compliance in design",12,4,"design;scenario","R,D",1,r"fairness|privacy|compliance","")
cell(SD,"Failure modes, rollout plans and reliability",12,4,"design;debugging","R,V",0,r"failure mode|rollout","")
cell(SD,"Cross-domain business case studies (ROI, build vs buy, KPI linkage)",12,5,"business;design","R,V",0,r"ROI|build vs buy","")
cell(SD,"Incident retrospectives and design debugging",12,5,"debugging;design","R,V",0,r"incident|postmortem","")
# ---------------- strengthen original six domains (from gap_analysis_v5.md)
cell("Machine Learning","Missing data and outliers",13,5,"concept;scenario;coding","X,V",0,r"missing (data|value)|outlier|imput","gap: 1 question in v4")
cell("Machine Learning","Time-series forecasting (stationarity, ARIMA, validation, leakage)",13,5,"concept;scenario;coding","X,V",0,r"time series|ARIMA|stationar|forecast","gap")
cell("Machine Learning","Interpretability (SHAP, LIME, PDP, permutation importance)",13,5,"concept;scenario;coding","X,D",0,r"SHAP|LIME|interpretab|feature importance","gap: 0")
cell("Machine Learning","Anomaly detection",13,4,"concept;scenario;coding","X,V",0,r"anomaly|outlier detection|isolation forest","gap: 0")
cell("Machine Learning","Reinforcement learning basics",13,3,"concept;scenario","V,D",0,r"reinforcement|Q-learning|bandit","gap")
cell("Machine Learning","Semi- and self-supervised learning",13,3,"concept;scenario","D",0,r"semi-supervised|self-supervised|pseudo-label","gap")
cell("Machine Learning","Hyperparameter tuning (random, Bayesian, early stopping)",13,3,"concept;scenario;coding","X,D",0,r"hyperparameter|grid search|Bayesian optim","thin")
cell("Machine Learning","Class imbalance",13,3,"scenario;coding;evaluation","X,V",0,r"imbalanc|SMOTE|class weight","thin")
cell("Machine Learning","Optimisation: gradient descent variants and learning rates",13,3,"concept;coding","X,V",0,r"gradient descent|learning rate|momentum","thin")
cell("Deep Learning","Backpropagation and the chain rule",13,3,"concept;coding;debugging","X,V",0,r"backprop|chain rule|autograd","gap")
cell("Deep Learning","Framework autograd and training loops (PyTorch)",13,4,"coding;debugging","X,D",0,r"PyTorch|TensorFlow|training loop","gap; PyTorch not installed on the owner's machine: sandbox-only tests")
cell("Deep Learning","Diffusion and LLM pretraining fundamentals",13,4,"concept;evaluation","D,V",0,r"diffusion|pretraining|scaling law","gap")
cell("Deep Learning","Optimisers, normalisation and regularisation tail topics",13,3,"concept;debugging","V,D",0,r"Adam|batch norm|layer norm|dropout","thin")
cell("Deep Learning","Transfer learning and learning-curve diagnosis",13,2,"scenario;debugging","V",0,r"transfer learning|learning curve","thin")
cell("Machine Learning","Model evaluation and business case studies (cost-sensitive thresholds, metric choice, uplift)",15,6,"evaluation;business;scenario","X,V",0,r"threshold|cost-sensitive|uplift|precision-recall","Production monitoring goes to MLOps")
cell("NLP","Machine translation and seq2seq",14,3,"concept;evaluation","D,V",0,r"machine translation|seq2seq|BLEU","gap")
cell("NLP","OOV, multilingual and low-resource text",14,3,"concept;scenario","D,V",0,r"OOV|multilingual|low-resource","gap")
cell("NLP","Summarisation and question answering",14,3,"concept;evaluation","D,V",0,r"summari[sz]|question answering","thin")
cell("NLP","Topic modelling and language-model evaluation",14,2,"concept;coding","X,V",0,r"topic model|LDA|perplexity","thin")
cell("NLP","Subword tokenisation and embeddings",14,3,"concept;coding","X,D",0,r"BPE|WordPiece|subword|word2vec|GloVe","thin")
cell("Python","Profiling and optimisation",14,4,"coding;debugging","X",0,r"profil|cProfile|timeit","gap")
cell("Python","Plotting (matplotlib, seaborn)",14,3,"coding;debugging","X",0,r"matplotlib|seaborn|plot","gap")
cell("Python","Typing, dataclasses and design",14,3,"concept;coding","X,D",0,r"type hint|dataclass|typing","thin")
cell("Python","Testing (pytest, fixtures, mocking)",14,4,"coding;debugging","X",0,r"pytest|unittest|mock","thin; pytest not on owner's machine: tests use stdlib unittest where possible")
cell("Python","pandas and NumPy operations",14,4,"coding;debugging","X",0,r"pandas|NumPy|vectori[sz]","thin")
cell("Python","Concurrency (GIL, threads, processes, asyncio)",14,2,"concept;debugging","X,D",0,r"\bGIL\b|asyncio|multiprocessing","thin")
cell("Python","Packaging and command-line tools",14,2,"concept;coding","X,D",0,r"argparse|entry point|pyproject","")
cell("SQL","CASE, conditional aggregation and pivoting",14,4,"sql;concept","X",0,r"\bCASE\b|pivot|conditional aggregat","gap")
cell("SQL","ACID, isolation levels and deadlocks",14,3,"concept;scenario;debugging","D,V",0,r"ACID|isolation level|deadlock","thin")
cell("SQL","Views, stored procedures and triggers",14,2,"concept;sql","X,D",0,r"\bview\b|stored procedure|trigger","thin")
cell("SQL","Recursive CTEs and hierarchies",14,3,"sql;debugging","X",0,r"recursive|hierarch","")
cell("SQL","Query planning and optimisation",14,2,"scenario;sql","X,D",0,r"EXPLAIN|query plan|query optimi","")
cell("Data Analysis","EDA and visualisation choices",15,5,"concept;scenario;business","V",0,r"\bEDA\b|exploratory|visuali[sz]","gap")
cell("Data Analysis","Cohort, funnel and retention analysis",15,4,"scenario;sql;business","X,V",0,r"cohort|funnel|retention","gap")
cell("Data Analysis","Sampling and bias",15,3,"concept;scenario","V,D",0,r"sampling|selection bias|survivorship","thin")
cell("Data Analysis","Outlier handling in analysis",15,2,"concept;scenario","V",0,r"outlier","thin")
cell("Data Analysis","Regression for analysis and interpretation",15,3,"concept;coding;evaluation","X,V",0,r"regression coefficient|interpret|confound","thin")
cell("Data Analysis","Time-series and seasonality analysis",15,3,"concept;coding","X,V",0,r"seasonal|trend|decompos","thin")
cell("Data Analysis","Communicating findings; analytical business cases",15,4,"business;scenario","V",0,r"stakeholder|recommend|business case","thin")

df = pd.DataFrame(C)
df["existing_v5_questions_matching"] = [int(v5.question.str.contains(k, flags=re.I, regex=True).sum()) for k in df.kw]
df["min"] = (df.target * 0.7).apply(math.floor); df["max"] = (df.target * 1.2).apply(math.ceil)
CODE = {G: "GEN", M: "MLO", E_: "DEN", CL: "CLD", BI: "BIZ", SD: "ASD", "Machine Learning": "ML", "Deep Learning": "DL", "NLP": "NLP", "Python": "PY", "SQL": "SQL", "Data Analysis": "DA"}
df["cell_id"] = df.domain.map(CODE) + "-" + df.groupby("domain").cumcount().add(1).astype(str).str.zfill(2)
BATCH = {1: "Generative AI & RAG A: retrieval, chunking, evaluation", 2: "Generative AI & RAG B: LLM applications, agents, safety, serving", 3: "MLOps A: lifecycle, CI/CD, serving, deployment, feature stores",
         4: "MLOps B: monitoring, retraining, governance, LLMOps, case studies", 5: "Data Engineering A: Spark core, tuning, streaming", 6: "Data Engineering B: pipelines, orchestration, Kafka, formats, warehouse modelling",
         7: "Cloud A: AWS", 8: "Cloud B: Azure and cross-cloud", 9: "Power BI A: modelling, DAX, Power Query, performance", 10: "Power BI B: governance, service, design, KPI and BI case studies",
         11: "Applied AI System Design A: scenario families", 12: "Applied AI System Design B: critique, responsibility, reliability, case studies", 13: "Strengthen ML and Deep Learning",
         14: "Strengthen NLP, Python and SQL", 15: "Strengthen Data Analysis; ML evaluation and business case studies"}
rows = []
for b, g in df.groupby("batch"):
    t = int(g.target.sum()); gen = math.ceil(t / YIELD)
    rows.append(dict(batch=b, name=BATCH[b], domains="; ".join(sorted(g.domain.unique())), cells=len(g), accepted_target=t, accepted_min=int(g["min"].sum()), accepted_max=int(g["max"].sum()), generate_cap=min(60, gen), verified_by_execution_cells=int(g.verification.str.contains("X").sum()), time_sensitive_cells=int(g.time_sensitive.sum())))
bp = pd.DataFrame(rows)
assert (bp.generate_cap <= 60).all() and (bp.accepted_target.map(lambda t: math.ceil(t / YIELD)) <= 60).all(), bp
dom = df.groupby("domain").agg(cells=("topic", "count"), planned_min=("min", "sum"), planned_target=("target", "sum"), planned_max=("max", "sum")).reset_index()
cur = v5.domain.value_counts().rename("v5_records")
dom = dom.merge(cur, left_on="domain", right_index=True, how="left").fillna({"v5_records": 0}); dom["v5_records"] = dom.v5_records.astype(int)
dom["total_target"] = dom.v5_records + dom.planned_target; dom["total_min"] = dom.v5_records + dom.planned_min; dom["total_max"] = dom.v5_records + dom.planned_max
RES = 40   # reserve batch 16: only used if the coverage matrix shows holes after batch 15, or to replace quarantined cells
tot = dict(v5=int(len(v5)), new_min=int(df["min"].sum()), new_target=int(df.target.sum()), new_max=int(df["max"].sum()), reserve_max=RES)
tot.update(total_min=tot["v5"] + tot["new_min"], total_target=tot["v5"] + tot["new_target"], total_max=tot["v5"] + tot["new_max"] + RES)
tm = {}
for _, r in df.iterrows():
    ts = r.types.split(";")
    for t in ts: tm[t] = tm.get(t, 0) + r.target / len(ts)
tot["type_mix_estimate"] = {k: round(v) for k, v in sorted(tm.items(), key=lambda x: -x[1])}
df.drop(columns=["kw"]).assign(kw=df.kw).to_csv(OUT / "coverage_matrix.csv", index=False)
bp.to_csv(OUT / "batch_plan.csv", index=False); dom.to_csv(OUT / "domain_summary.csv", index=False)
(OUT / "plan.json").write_text(json.dumps(dict(yield_assumption=YIELD, totals=tot, batches=bp.to_dict("records"), domains=dom.to_dict("records")), indent=1), encoding="utf-8")
print(bp.to_string()); print(dom.to_string()); print(tot)
