from dec_helpers import *
K(3926,"M","IMPRECISE","'plot variable chart' is vague; overlaps 3841")
F(3927,"M","MISLEADING;IMPRECISE","rule 'non-linear -> bagging; interpretability -> SVM' is simplistic (SVMs are not interpretable)",
  pa="No algorithm is best for all data (no free lunch). Consider the problem type (regression, classification, clustering), data size, feature types, linearity, interpretability needs, training/inference cost and available labels. Start with a simple baseline (linear/logistic regression, decision tree), then try stronger models (random forest, gradient boosting, SVM, neural networks for images/text/audio) and choose using cross-validation on a suitable metric after EDA.",
  state="ready_for_approval",conf="high")
F(3928,"M","FACTUAL_ERROR;MISSING_FORMULA","says correlation 'has only three specific values 1, 0, -1' (it ranges continuously over [-1, 1]); zero correlation does not imply independence",
  pa="Covariance, cov(X,Y) = E[(X - mu_x)(Y - mu_y)], gives the direction of the linear relationship; its magnitude depends on the units of X and Y, so it is not comparable across variables. Correlation (Pearson) = cov(X,Y) / (sigma_x * sigma_y) is the standardised version, unit-free and bounded between -1 and 1. Zero correlation means no linear relationship, not necessarily independence.",
  state="ready_for_approval",conf="high")
F(3929,"E","TYPO;THIN_ANSWER","stray 'C' before 'Causality'; no illustration",
  pa="Correlation means two variables move together; causation means a change in one produces a change in the other. Correlation can arise from confounders or coincidence (ice-cream sales and drownings both rise in summer). Establishing causation needs randomised experiments (A/B tests) or careful causal inference methods that control for confounding.",
  state="ready_for_approval",conf="high")
X(3930,"MISLEADING;LOW_RELEVANCE","answer claims ML on hardware requires System Verilog on FPGA; far too narrow and not a standard interview question")
F(3931,"M","FACTUAL_ERROR","label encoding maps categories to integers, not 'to 1 and 0'",
  pa="One-hot encoding turns a categorical variable with k levels into k binary columns (one per level), so it increases dimensionality and implies no order. Label encoding maps each level to an integer (0, 1, 2, ...) in a single column, so dimensionality is unchanged, but it implies an artificial order, so it suits ordinal variables or tree-based models rather than linear models.",
  state="ready_for_approval",conf="high")
F(3932,"M","ILL_POSED_QUESTION","brain-teaser with unclear wording; relies on a normality assumption",
  pq="In a normally distributed feature, values within one standard deviation of the mean are missing. What fraction of the data remains?",
  state="needs_review",conf="medium")
K(3933,"E","IMPRECISE","ambiguous between variance of data and model variance; answer is hedged")
F(3934,"M","IMPRECISE;CORRUPTED","'high variance dataset' should be a high-variance model; description of bagging is garbled ('polling')",
  pq="How would you reduce high variance (overfitting) in a model?",
  pa="Options: get more training data; reduce model complexity (shallower trees, fewer parameters); add regularisation (L1/L2, dropout, early stopping); use feature selection or dimensionality reduction; use bagging/random forests, which average many high-variance models trained on bootstrap samples; use cross-validation to tune.",
  state="ready_for_approval",conf="high")
K(3935,"M","","good scenario question; correct")
K(3936,"M","THIN_ANSWER","correct but tool-centric")
F(3937,"E","IMPRECISE","'doesn't require any minimum or maximum time input' is filler; regular intervals are common, not required",
  pa="A time series is a sequence of observations recorded over time, usually at regular intervals (hourly, daily, monthly). Observations are time-ordered and often dependent on earlier values. Typical components: trend, seasonality, cyclical patterns and noise. Standard tasks: forecasting, anomaly detection and decomposition.",
  state="ready_for_approval",conf="high")
F(3938,"H","MISSING_FORMULA;IMPRECISE","no formula; requires positive data; transforms towards normality rather than guaranteeing it",
  pa="Box-Cox is a power transformation for strictly positive data: y(lambda) = (y^lambda - 1) / lambda for lambda != 0 and y(lambda) = ln(y) for lambda = 0. Lambda is chosen by maximum likelihood to make the data as close to normal (and variance as stable) as possible. For data with zeros or negatives, use Yeo-Johnson.",
  state="ready_for_approval",conf="high")
K(3939,"M","IMPRECISE","mini-batch gradient descent not mentioned; may duplicate a DL-block record (check in duplicate pass)")
X(3940,"DUPLICATE","covered by 3715",dup_of=3715)
K(3941,"M","IMPRECISE","'nonparametric and hence robust to outliers' conflates two properties")
F(3942,"H","CORRUPTED;UNVERIFIED_CLAIM","'combine decision trees but at the beginning of the process' is garbled; claims about multiclass detection and imbalanced data are unsupported",
  pa="Random forest builds many deep trees independently on bootstrap samples with random feature subsets and averages them, reducing variance; it is easy to tune and hard to overfit. Gradient boosting builds shallow trees sequentially, each fitted to the errors (negative gradient of the loss) of the ensemble so far, mainly reducing bias; it often reaches higher accuracy but needs careful tuning (learning rate, trees, depth) and is more sensitive to noisy labels and outliers.",
  state="ready_for_approval",conf="high")
X(3943,"DUPLICATE","covered by 3769",dup_of=3769)
X(3944,"DUPLICATE","covered by 3779",dup_of=3779)
F(3945,"E","IMPRECISE;MISLEADING","'outliers are lost' is wrong (min-max normalisation is distorted by outliers); 'standardization recommended for most applications' is a blanket claim",
  pa="Normalisation (min-max scaling) rescales values to a fixed range, usually [0, 1]: x' = (x - min) / (max - min). Standardisation (z-score) rescales to mean 0 and standard deviation 1: z = (x - mu) / sigma. Min-max is sensitive to outliers because they set the min and max; standardisation is less affected and is preferred for algorithms that assume centred data (e.g. linear models, SVM, PCA). Fit the scaler on training data only.",
  state="ready_for_approval",conf="high")
K(3946,"E","","correct")
F(3947,"M","IMPRECISE","'multivariate normality' applies to the residuals (needed for inference), not the variables; independence of errors is listed as 'no auto-correlation'",
  pa="Main assumptions: (1) linear relationship between predictors and target; (2) independent errors (no autocorrelation); (3) homoscedasticity (constant error variance); (4) approximately normal residuals, needed for confidence intervals and tests; (5) no severe multicollinearity among predictors.",
  state="ready_for_approval",conf="high")
F(3948,"M","ILL_POSED_QUESTION;IMPRECISE","line does not 'rotate'; best fit is where squared error is minimised",
  pq="How is the best-fit line determined in linear regression?",
  pa="The line is chosen to minimise the sum of squared residuals (ordinary least squares). This has a closed-form solution (the normal equations) and can also be reached with gradient descent. For a given dataset, minimising squared error is equivalent to maximising R^2.",
  state="ready_for_approval",conf="high")
F(3949,"M","CORRUPTED;FACTUAL_ERROR","'derived from cost function' is wrong; logistic regression is based on the logit (log-odds) / sigmoid function",
  pq="Why is logistic regression a classification technique despite its name, and which function does it use?",
  pa="Logistic regression models the probability of a class with the sigmoid (logistic) function, P(y=1|x) = 1 / (1 + exp(-(w.x + b))); equivalently, it models the log-odds as a linear function of the features. Because the output is a probability that is thresholded (e.g. at 0.5) to assign a class, it is used for classification, even though it is a regression on the log-odds.",
  state="ready_for_approval",conf="high")
X(3950,"DUPLICATE","covered by 3757",dup_of=3757)
X(3951,"DUPLICATE","covered by 3888",dup_of=3888)
X(3952,"DUPLICATE;LOW_VALUE","compound question; recommender types covered by 3804 and 3807",dup_of=3804)
F(3953,"E","QUESTION_ANSWER_MISMATCH","question asks for three stages; answer lists six steps",
  pq="What are the main steps in building a machine learning model?",state="ready_for_approval",conf="high")
K(3954,"M","THIN_ANSWER","generic lifecycle applied to spam; no features, metrics or class-imbalance discussion")
X(3955,"DUPLICATE;DOES_NOT_ADDRESS","answer is a copy of the 'SVM advantages' text; kernel SVM covered by 3828",dup_of=3828)
K(3956,"M","THIN_ANSWER","generic three-stage description")
F(3957,"E","FACTUAL_ERROR","says NLP extracts data 'from audio'; NLP handles text (speech is a separate front end)",
  pa="Natural Language Processing is the field of AI and linguistics concerned with enabling computers to process, understand and generate human language. Typical tasks: tokenisation, part-of-speech tagging, parsing, named entity recognition, sentiment analysis, machine translation, question answering and summarisation. Speech is handled by a speech-recognition front end that produces text.",
  state="ready_for_approval",conf="high")
F(3958,"M","IMPRECISE;OVERSTATED","'useless data' and 'one of the most important tasks' are overstatements; removal is task-dependent",
  pa="Stop words are very common words (the, is, a, of) that carry little discriminative meaning for many tasks, so they are often removed to reduce noise and feature space in search and bag-of-words models. They should not always be removed: negations and function words matter for sentiment, and modern transformer models use them.",
  state="ready_for_approval",conf="high")
F(3959,"M","MISSING_FORMULA;FACTUAL_ERROR","IDF is a corpus-level measure, not 'the importance of the term in a document'; no formula",
  pa="TF-IDF weights a term by how frequent it is in a document (TF) and how rare it is across the corpus (IDF): tf-idf(t,d) = tf(t,d) * log(N / df(t)), where N is the number of documents and df(t) the number containing t (libraries add smoothing variants). Words common in one document but rare overall get high weights; words in nearly every document get low weights. Used for search ranking, keyword extraction and text-classification features.",
  state="ready_for_approval",conf="high")
F(3960,"E","FACTUAL_ERROR;IMPRECISE","syntactic analysis recovers sentence structure; extracting meaning is semantic analysis",
  pa="Syntactic analysis (parsing) determines the grammatical structure of a sentence - how words group into phrases and how they relate (constituency or dependency trees) - using grammar rules or statistical models. It deals with structure, not meaning, which is the job of semantic analysis.",
  state="ready_for_approval",conf="high")
F(3961,"M","IMPRECISE","NLG is generation, not a semantic-analysis technique; NER is usually information extraction",
  pa="Semantic analysis determines the meaning of words and sentences. Typical techniques: word sense disambiguation (which sense a word has in context), semantic role labelling (who did what to whom), relation extraction and distributional/embedding-based representations. Named entity recognition is often used as a supporting step.",
  state="needs_review",conf="medium")
X(3962,"DUPLICATE;LOW_VALUE","tool trivia; covered by 3985",dup_of=3985)
F(3963,"E","DOES_NOT_ADDRESS;REQUIRES_CODE","asks how to tokenize with NLTK; answer only defines tokenization",
  pa="import nltk; nltk.download('punkt') (a one-off download). Then: from nltk.tokenize import sent_tokenize, word_tokenize; text = 'Hello, world! NLP is fun.'; sent_tokenize(text) -> ['Hello, world!', 'NLP is fun.']; word_tokenize('Hello, world!') -> ['Hello', ',', 'world', '!'].",
  state="needs_code_test",conf="medium",code="import nltk\nfrom nltk.tokenize import word_tokenize\nassert word_tokenize('Hello, world!')==['Hello', ',', 'world', '!']")
X(3964,"DUPLICATE;ANSWER_BLEED;FACTUAL_ERROR","conflates parsing with n-grams and ends with diagram/code placeholder; covered by 3978",dup_of=3978)
F(3965,"M","REQUIRES_CODE;FACTUAL_ERROR","example output ('flying' -> 'fly') does not match Porter stemmer behaviour (nltk gives 'fli'); code lines run together",
  pa="Stemming reduces a word to a root form by stripping suffixes with heuristic rules, so the result need not be a real word. Example with NLTK's PorterStemmer: from nltk.stem import PorterStemmer; p = PorterStemmer(); [p.stem(w) for w in ['running', 'cookies', 'flying', 'stemming']] -> ['run', 'cooki', 'fli', 'stem']. Lemmatisation (dictionary-based) would give real words, e.g. 'flying' -> 'fly' with the verb POS.",
  state="needs_review",conf="medium",code="from nltk.stem import PorterStemmer\np=PorterStemmer()\nassert [p.stem(w) for w in ['running','cookies','flying','stemming']]==['run','cooki','fli','stem']")
X(3966,"DUPLICATE;ANSWER_BLEED","covered by 3992; answer ends with placeholder text about 'stop words'",dup_of=3992)
F(3967,"E","DOES_NOT_ADDRESS;REQUIRES_CODE;REQUIRES_DATA","asks how with spaCy; answer gives no code; needs a model with word vectors; similarity is cosine and can be negative",
  state="needs_code_test",conf="low")
X(3968,"CORRUPTED;MEANINGLESS","word-salad list, not an answer")
K(3969,"M","TIME_SENSITIVE","correct but classical technique; modest interview relevance")
F(3970,"M","CORRUPTED;IMPRECISE","answer recites formal-language definitions rather than how regular expressions are used in NLP",
  pa="A regular expression (regex) is a pattern language for matching and extracting strings, e.g. r'\\d+' matches digits and r'\\b[A-Z][a-z]+\\b' matches capitalised words. In NLP they are used for tokenisation, cleaning (removing URLs and punctuation), pattern-based extraction (emails, dates) and rule-based tagging. Formally, regular expressions describe regular languages and are equivalent to finite automata.",
  state="ready_for_approval",conf="high")
X(3971,"LOW_RELEVANCE","formal-language theory; not a typical NLP interview question")
X(3972,"DUPLICATE","covered by 3983",dup_of=3983)
F(3973,"E","MISSING_TABLE","answer ends 'The below table shows...' with no table",
  pq="What is the difference between NLP and NLU?",
  pa="NLP (Natural Language Processing) is the broad field covering all computational handling of human language, including understanding and generation (NLG) as well as tasks like tokenisation and translation. NLU (Natural Language Understanding) is the subset focused on comprehension - intent detection, entity extraction, meaning and context. NLU = reading comprehension; NLP = understanding plus generation.",
  state="needs_review",conf="medium")
F(3974,"E","MISSING_TABLE","answer ends 'The below table shows...' with no table",
  pq="What is the difference between NLP and a conversational interface (CI)?",
  pa="NLP is the underlying technology that processes and understands language. A conversational interface (chatbot or voice assistant) is an application that lets users interact through natural dialogue and uses NLP, dialogue management and often speech components to do so. NLP can exist without a CI (e.g. search, translation); a CI depends on NLP.",
  state="needs_review",conf="medium")
K(3975,"M","IMPRECISE","vague but conceptually acceptable")
K(3976,"E","IMPRECISE","'parse' is used loosely for reading n tokens at a time")
K(3977,"M","TIME_SENSITIVE","workflow reasonable; 'embed using word2vec' is dated")
F(3978,"E","ANSWER_BLEED","answer ends with diagram reference",
  trim=" To understand parsing, refer to the below diagram",state="ready_for_approval",conf="high")
F(3979,"M","DOES_NOT_ADDRESS;CORRUPTED","answer describes recommender-system behaviour rather than text feature extraction",
  pa="Feature extraction converts raw text into numerical features a model can use: bag of words, n-grams, TF-IDF, word embeddings (word2vec, GloVe, contextual embeddings from transformers), plus linguistic features such as POS tags, named entities and sentence length.",
  state="ready_for_approval",conf="high")
X(3980,"DUPLICATE","covered by 3880",dup_of=3880)
X(3981,"DUPLICATE;MISSING_FORMULA;ANSWER_BLEED","covered by 3823; answer ends 'Let us look at the formula' without one",dup_of=3823)
K(3982,"M","IMPRECISE","'perfect for... data that changes frequently' is an overstatement; correct use cases listed")
F(3983,"M","IMPRECISE","ambiguity explanation is loose; algorithms and relations not mentioned",
  pq="Explain dependency parsing in NLP.",
  pa="Dependency parsing analyses the grammatical structure of a sentence as directed, labelled relations between a head word and its dependents (e.g. nsubj, dobj), producing a tree rooted at the main verb. Parsers are transition-based or graph-based and trained on treebanks (Universal Dependencies). Uses: information extraction, relation extraction, question answering and grammar checking.",
  state="ready_for_approval",conf="high")
F(3984,"M","THIN_ANSWER;OVERSTATED","promotional wording; omits extractive vs abstractive",
  pa="Text summarisation produces a shorter version of a text that keeps its key information. Extractive summarisation selects the most important sentences from the source (e.g. TextRank, TF-IDF scoring); abstractive summarisation generates new sentences, typically with sequence-to-sequence or transformer models, and can hallucinate. Evaluated with ROUGE and human judgement.",
  state="ready_for_approval",conf="high")
F(3985,"M","OUTDATED;UNVERIFIED_CLAIM","'spaCy supports only 7 languages' is a dated figure; other comparison points are loosely worded",
  pa="NLTK is a teaching and research toolkit with many algorithms and corpora, mostly string-based and good for experimentation. spaCy is production-oriented: fast, object-oriented pipelines (tokenisation, tagging, parsing, NER), pretrained models, word vectors and transformer integration, and offers one well-chosen implementation per task. Language coverage differs and changes over time.",
  state="needs_review",conf="medium")
F(3986,"M","IMPRECISE","list of 'modules' includes sentiment and classification, which are not information extraction",
  pa="Information extraction automatically turns unstructured text into structured data. Main tasks: named entity recognition, relation extraction (e.g. person-works-for-company), event extraction, coreference resolution and template filling. Output is typically stored in a database or knowledge graph.",
  state="ready_for_approval",conf="high")
K(3987,"M","THIN_ANSWER","correct; drawbacks (no order, sparsity) not mentioned")
F(3988,"M","FACTUAL_ERROR","describes lexical ambiguity; pragmatic ambiguity depends on context, speaker intent and world knowledge",
  pa="Pragmatic ambiguity arises when a sentence is syntactically and lexically clear but its intended meaning depends on context or speaker intent, e.g. 'Can you pass the salt?' (a request, not a question about ability) or 'I saw him at the bank' only when context resolves it. Lexical ambiguity concerns a single word with multiple senses; pragmatic ambiguity concerns the sentence in context.",
  state="needs_review",conf="medium")
F(3989,"M","CORRUPTED;THIN_ANSWER","'taking an output from the corrupt input' is garbled",
  pa="A masked language model hides (masks) a fraction of the input tokens (about 15% in BERT) and trains the model to predict them from the surrounding bidirectional context. This pre-training objective yields deep contextual representations that are then fine-tuned for downstream tasks.",
  state="ready_for_approval",conf="high")
X(3990,"DUPLICATE;MISSING_TABLE","covered by 3974",dup_of=3974)
X(3991,"LOW_VALUE;OUTDATED","opinion list of tools")
K(3992,"E","","correct; clear on context dependence")
F(3993,"E","QUESTION_TYPO","'NES' should be NER; 'Name entity recognition' should be 'Named entity recognition'",
  pq="What is Named Entity Recognition (NER)?",repl=[("Name entity recognition","Named entity recognition")],
  state="ready_for_approval",conf="high")
