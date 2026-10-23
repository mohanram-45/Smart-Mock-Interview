from dec_helpers import *
K(3752,"E","THIN_ANSWER","correct; omits example tasks")
K(3753,"E","","correct")
K(3754,"M","","correct")
K(3755,"M","","correct")
K(3756,"M","","correct; raw label Hard is high for a definition")
K(3757,"E","IMPRECISE","'lazy' because it defers all computation to prediction time (no training phase); wording is loose but not wrong")
F(3758,"M","IMPRECISE;FACTUAL_ERROR","k-means needs the number of clusters k, not 'a threshold'; it assigns points to the nearest centroid (mean of the cluster), not 'the mean of the distance between points'",
  pa="KNN is supervised: it needs labelled training data and classifies (or regresses) a new point from the labels of its k nearest neighbours. K-means is unsupervised: it needs only unlabelled data and a chosen number of clusters k; it iteratively assigns points to the nearest centroid and recomputes each centroid as the mean of its assigned points. The 'k' means different things: number of neighbours in KNN, number of clusters in k-means.",
  state="ready_for_approval",conf="high")
F(3759,"M","IMPRECISE","features are assumed conditionally independent given the class, not simply 'no interdependency'",
  pa="Naive Bayes is a probabilistic supervised classifier based on Bayes' theorem. It assumes features are conditionally independent given the class, so P(class | x) is proportional to P(class) * product of P(x_i | class). The assumption is rarely true, yet the model works well for text classification and as a fast baseline.",
  state="ready_for_approval",conf="high")
K(3760,"M","IMPRECISE","'non-parametric' is debatable (linear SVM has a fixed-size weight vector); acceptable for interview use but flagged for reviewer")
K(3761,"M","QUESTION_FORMAT","grammar ('What is Kernel Functions?'); answer correct")
K(3762,"M","THIN_ANSWER","list; omits linear kernel")
K(3763,"M","","correct")
K(3764,"M","","correct")
F(3765,"M","QUESTION_FORMAT;FACTUAL_ERROR;MISSING_FORMULA","question is a fragment; answer says the split maximises 'entropy gain' (it is information gain) and gives a malformed entropy formula",
  pq="How does a decision tree choose the best feature to split on?",
  pa="At each node the tree evaluates candidate splits and picks the one that most reduces impurity. Gini impurity = 1 - sum(p_i^2). Entropy = -sum(p_i * log2(p_i)). Information gain = entropy(parent) - weighted average entropy(children). The split with the highest information gain (or largest Gini decrease) is chosen.",
  state="ready_for_approval",conf="high")
K(3766,"M","","correct")
K(3767,"M","","correct")
K(3768,"M","THIN_ANSWER","list; omits LightGBM/CatBoost")
F(3769,"M","QUESTION_TYPO;ANSWER_BLEED;MISSING_FORMULA","'Confusion Metrics' should be Matrix; answer drifts into regression metrics (RMSE, MAE, R^2) unrelated to confusion matrices; formulas absent",
  pq="What is a confusion matrix and which classification metrics are derived from it?",
  pa="A confusion matrix is an N x N table of actual vs predicted classes; for binary classification it holds TP, FP, TN and FN. Derived metrics: accuracy = (TP+TN)/(TP+TN+FP+FN); precision = TP/(TP+FP); recall (sensitivity, TPR) = TP/(TP+FN); specificity (TNR) = TN/(TN+FP); false positive rate = FP/(FP+TN) (Type I error rate); false negative rate = FN/(FN+TP) (Type II error rate); F1 = 2*precision*recall/(precision+recall).",
  state="ready_for_approval",conf="high")
K(3770,"M","THIN_ANSWER","correct; AUC not mentioned")
K(3771,"E","THIN_ANSWER","correct")
K(3772,"E","","correct")
X(3773,"LOW_VALUE","list of algorithm names; clustering covered by 3772, 3774, 3777")
K(3774,"E","","correct")
F(3775,"M","DOES_NOT_ADDRESS;QUESTION_FORMAT","question asks for the algorithm; answer lists strengths and weaknesses",
  pq="What are the strengths and weaknesses of k-means clustering?",
  pa="Strengths: simple and fast, roughly linear in the number of points (O(n * k * iterations * d)), scales to large datasets. Weaknesses: k must be chosen in advance; results depend on random initialisation (use k-means++ and multiple restarts); assumes roughly spherical, similar-sized clusters; sensitive to outliers and feature scale.",
  state="ready_for_approval",conf="high")
F(3776,"M","QUESTION_FORMAT;IMPRECISE","blog-style title; elbow method is 'look for the bend', not 'as small as possible'",
  pq="How do you choose the number of clusters k in k-means?",
  pa="Elbow method: plot within-cluster sum of squares against k and pick the point where the improvement flattens (the 'elbow'). Silhouette method: choose the k with the highest average silhouette width. Gap statistic: compare the within-cluster dispersion with its expectation under a null reference distribution and pick the k with the largest gap. Domain knowledge and cluster stability also matter.",
  state="ready_for_approval",conf="high")
K(3777,"M","QUESTION_FORMAT;THIN_ANSWER","fine; omits agglomerative vs divisive")
F(3778,"M","QUESTION_FORMAT;THIN_ANSWER","fragment question; the two-way taxonomy is one source's framing",
  pq="What are common dimensionality reduction techniques?",
  pa="Linear: PCA (maximises retained variance), LDA (supervised, maximises class separation), truncated SVD. Non-linear: t-SNE and UMAP (mainly for visualisation), kernel PCA, autoencoders. Alternative: feature selection (filter, wrapper, embedded methods).",
  state="ready_for_approval",conf="high")
K(3779,"M","QUESTION_FORMAT","question is a title ending in a colon; answer broadly correct (PCA is also the eigendecomposition of the covariance matrix)")
K(3780,"M","QUESTION_FORMAT","correct")
K(3781,"M","OVERSTATED;TIME_SENSITIVE","'novel' and relative-performance claims are source-era wording")
F(3782,"M","MISSING_FORMULA;QUESTION_FORMAT","no formula given",
  pq="What is cross-entropy (log loss)?",
  pa="Cross-entropy measures the difference between the true distribution and the predicted distribution. For binary classification: L = -(1/N) * sum[ y*log(p) + (1-y)*log(1-p) ]; for multi-class: L = -sum over classes of y_c * log(p_c). It penalises confident wrong predictions heavily and is the standard loss for classification with probabilistic outputs.",
  state="ready_for_approval",conf="high")
F(3783,"M","IMPRECISE","reason given ('confusing to compare') is weak; the real reason is that log p <= 0 and minimising -log p equals maximising likelihood",
  pq="Why does log loss have a negative sign?",
  pa="Probabilities lie in (0, 1], so log p is zero or negative. The minus sign makes the loss non-negative (0 for perfect predictions, growing as predictions worsen) and turns maximum-likelihood estimation into loss minimisation, which is what gradient-based optimisers do.",
  state="ready_for_approval",conf="high")
K(3784,"M","","correct; raw label Hard is high")
K(3785,"M","IMPRECISE","3-sigma rule is about 99.7%, stated as 99%; two topics in one question")
F(3786,"M","IMPRECISE;INCORRECT_ABSOLUTE","'no matter what the shape' needs finite variance; 'over 30' is a rule of thumb",
  pa="The Central Limit Theorem says that, for independent samples from a population with finite mean and variance, the sampling distribution of the sample mean approaches a normal distribution as the sample size grows, whatever the population shape. A common rule of thumb is n >= 30, but heavily skewed populations may need more.",
  state="ready_for_approval",conf="high")
F(3787,"M","IMPRECISE","definition is vague and lacks the correct interpretation",
  pq="What is a confidence interval and how should it be interpreted?",
  pa="A confidence interval is a range of plausible values for a population parameter, computed from sample data (estimate +/- margin of error). A 95% interval means that if the procedure were repeated on many samples, about 95% of the resulting intervals would contain the true parameter; it does not mean there is a 95% probability that this specific interval contains it.",
  state="ready_for_approval",conf="high")
F(3788,"M","IMPRECISE;CORRUPTED","step list is garbled ('state your null hypothesis'; 'support the null')",
  pa="Hypothesis testing uses sample data to decide whether there is enough evidence against a default claim. Steps: state the null (H0) and alternative (H1) hypotheses; choose the significance level alpha and a suitable test; compute the test statistic and p-value; reject H0 if p < alpha, otherwise fail to reject H0 (which is not proof that H0 is true).",
  state="ready_for_approval",conf="high")
K(3789,"M","IMPRECISE","alpha is the probability of rejecting H0 when it is true (Type I error rate); wording acceptable")
K(3790,"M","THIN_ANSWER","correct")
