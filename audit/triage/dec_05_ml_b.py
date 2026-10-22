from dec_helpers import *
F(3791,"M","FACTUAL_ERROR;QUESTION_FORMAT","Pearson's coefficient tests a linear (not monotonic) relationship; Spearman's is the monotonic one",
  repl=[("Pearson's Correlation Coefficient: Tests whether two samples have a monotonic","Pearson's Correlation Coefficient: Tests whether two samples have a linear")],
  state="ready_for_approval",conf="high")
K(3792,"M","","correct")
K(3793,"E","","correct")
K(3794,"E","IMPRECISE","'penalizing the coefficients of the cost function' is loose (a penalty term is added to the loss); acceptable")
F(3795,"M","FACTUAL_ERROR","AUC near 0 means predictions are systematically inverted, not 'poor'; a model with no skill is about 0.5",
  pa="AUC is the probability that the model ranks a random positive example above a random negative one. AUC = 1 is perfect separation; 0.5 is no better than random guessing; AUC well below 0.5 means the ranking is systematically inverted (flipping the predictions would help). Rough guide: 0.7-0.8 acceptable, 0.8-0.9 good, above 0.9 excellent, always in context of the problem.",
  state="ready_for_approval",conf="high")
K(3796,"M","","correct")
K(3797,"M","","correct")
K(3798,"M","IMPRECISE","standardised-coefficient comparison holds only for uncorrelated predictors; raw label Hard is high")
K(3799,"M","IMPRECISE","answer omits the correlated-features caveat")
F(3800,"M","IMPRECISE","parameter names min_sample_split and max_sample do not match scikit-learn (min_samples_split, max_samples)",
  repl=[("min_sample_split","min_samples_split"),("max_sample:","max_samples:")],
  state="ready_for_approval",conf="high")
K(3801,"M","THIN_ANSWER","vague ('literature suggests'); no practical advice such as tuning depth with cross-validation")
F(3802,"M","FACTUAL_ERROR","'square of the number of features' is wrong: sqrt(n_features) is the usual default for max_features, not the number of trees",
  pa="There is no fixed rule. More trees reduce variance and never overfit by themselves, but with diminishing returns and growing cost. Start with a few hundred trees, then plot out-of-bag (OOB) or validation error against n_estimators and stop when it plateaus. (The common sqrt(n_features) rule applies to max_features, the number of features tried per split.)",
  state="ready_for_approval",conf="high")
F(3803,"M","IMPRECISE;MISLEADING","'twice as likely to be picked' is an unsupported claim; 'linearly contain the same information' is loose",
  pa="In a random forest, correlated features share the importance: either one can be chosen at a split, so the importance of each is diluted and feature-importance rankings become unstable, though predictive accuracy is usually little affected. In linear models, strong multicollinearity makes coefficient estimates unstable with large variance. Remedies: drop or combine redundant features, use PCA, or use regularisation (ridge/lasso).",
  state="needs_review",conf="medium")
K(3804,"M","IMPRECISE","'tends to overfit' and 'average of other experiences' are loose; core idea correct")
K(3805,"M","","correct (implicit ALS, Hu et al.)")
K(3806,"M","","correct")
K(3807,"M","COSMETIC_PREFIX","correct; stray '. .' punctuation")
K(3808,"M","","correct")
F(3809,"M","FACTUAL_ERROR;DOMAIN_MISMATCH","gradient descent via backprop does not guarantee a global minimum; deep-learning content labelled ML (check duplicate against the DL block)",
  repl=[("towards a global minimum along the steepest","towards a (local) minimum along the steepest")],
  pd="Deep Learning",state="needs_review",conf="medium")
F(3810,"M","CORRUPTED;IMPRECISE","'linear regression either - svm' is garbled; 'sparse data' is ambiguous (many zeros vs missing values)",
  pq="How do you deal with sparse data (features that are mostly zeros)?",
  pa="Store the data in a sparse format (e.g. CSR) so memory and computation scale with non-zeros. Use models that handle sparsity well: L1-regularised linear/logistic regression (also performs feature selection), linear SVMs, Naive Bayes. Reduce dimensionality with truncated SVD or feature hashing, and drop very rare features. For high-cardinality categoricals, one-hot encoding creates sparse vectors by design.",
  state="needs_review",conf="medium")
K(3811,"M","THIN_ANSWER","correct but brief (semi-supervised technique)")
K(3812,"M","THIN_ANSWER","correct but omits teacher/student terminology")
F(3813,"M","THIN_ANSWER;UNVERIFIED_CLAIM","answer is circular; whether reduction helps an SVM depends on the data (SVMs cope well with high dimensions)",
  pa="Dimensionality reduction (e.g. PCA) before an SVM can reduce noise and redundant features, lower training and prediction cost (kernel SVM training is roughly quadratic to cubic in samples and linear in features), and reduce overfitting when features greatly outnumber samples. It is not always beneficial: SVMs often work well in high dimensions, and reduction can discard discriminative information, so validate it with cross-validation.",
  state="needs_review",conf="medium")
F(3814,"M","THIN_ANSWER","one-line answer with a typo ('accessed')",
  pa="Frame the insight as a hypothesis, choose an appropriate test and significance level, compute the test statistic and p-value, and report the effect size with a confidence interval rather than the p-value alone. Check test assumptions, correct for multiple comparisons when testing many hypotheses, and confirm practical significance.",
  state="ready_for_approval",conf="high")
F(3815,"M","MISSING_FORMULA;CORRUPTED","verbal description of the formula is garbled and no formula is given",
  pa="Bayes' theorem: P(A|B) = P(B|A) * P(A) / P(B), where P(A) is the prior, P(B|A) the likelihood and P(A|B) the posterior. In machine learning it underlies Naive Bayes classifiers, Bayesian inference/parameter estimation and MAP estimation.",
  state="ready_for_approval",conf="high")
K(3816,"M","","correct")
F(3817,"M","IMPRECISE;LOW_RELEVANCE","'symmetric functions' should read sinusoids; the audit found this topic duplicated elsewhere (resolve in duplicate pass)",
  repl=[("symmetric functions","sinusoidal (sine and cosine) functions")],
  state="needs_review",conf="medium")
F(3818,"M","FACTUAL_ERROR","claims deep learning 'represents an unsupervised learning algorithm' - false; also a likely duplicate of a DL-block definition",
  pa="Deep learning is a subfield of machine learning that uses neural networks with many layers to learn hierarchical representations directly from raw data (images, text, audio). Unlike classical ML, which usually relies on hand-engineered features, deep models learn features automatically, but they typically need more data and compute and are harder to interpret. It can be supervised, unsupervised or self-supervised.",
  state="ready_for_approval",conf="high")
F(3819,"M","IMPRECISE;INCORRECT_ABSOLUTE","'generative learns categories' is vague; 'discriminative generally outperform' is an overgeneralisation",
  pa="A generative model learns the joint distribution P(x, y) (typically P(x|y) and P(y)), so it can classify through Bayes' rule and also generate new samples; examples: Naive Bayes, Gaussian mixture models, HMMs. A discriminative model learns P(y|x) or the decision boundary directly; examples: logistic regression, SVM, neural classifiers. Discriminative models often reach lower error with plenty of data; generative models can do better with little data or when modelling missing data.",
  state="ready_for_approval",conf="high")
K(3820,"M","","correct (forward chaining / expanding window)")
K(3821,"M","","correct; raw label Hard is high")
F(3822,"M","ILL_POSED_QUESTION;IMPRECISE","'accuracy vs performance' is not a meaningful contrast; the fraud example is garbled",
  pq="Is accuracy always a good metric for evaluating a classifier? When is it misleading?",
  pa="No. On imbalanced data accuracy can be high while the model is useless: if only 1% of transactions are fraud, predicting 'no fraud' for everything gives 99% accuracy but zero recall. Use precision, recall, F1, PR-AUC or ROC-AUC chosen according to the cost of false positives versus false negatives.",
  state="ready_for_approval",conf="high")
F(3823,"M","MISSING_FORMULA;FACTUAL_ERROR","F1 is the harmonic, not a 'weighted', average; no formula",
  pa="F1 = 2 * precision * recall / (precision + recall), the harmonic mean of precision and recall (range 0 to 1). It is useful for classification with imbalanced classes where both false positives and false negatives matter and true negatives are not informative. F-beta weights recall more or less than precision.",
  state="ready_for_approval",conf="high")
F(3824,"M","THIN_ANSWER","three generic bullets; omits class weights, suitable metrics and SMOTE",
  pa="Options: (1) use suitable metrics (precision, recall, F1, PR-AUC) instead of accuracy; (2) resample - oversample the minority class (e.g. SMOTE) or undersample the majority class; (3) use class weights or cost-sensitive learning; (4) tune the decision threshold; (5) try algorithms/ensembles that handle imbalance (e.g. balanced random forest); (6) collect more minority-class data if possible. Always resample only the training folds.",
  state="ready_for_approval",conf="high")
K(3825,"E","IMPRECISE","wording garbled ('datasets to strict categories') but meaning correct")
F(3826,"M","DOES_NOT_ADDRESS","asks for an example; answer defines ensembles",
  pq="What are ensemble methods and when are they useful?",
  pa="Ensemble methods combine several models to get better predictions than any one alone. Bagging (e.g. random forest) reduces variance, boosting (e.g. gradient boosting) reduces bias, and stacking combines different model types through a meta-learner. They are useful when single models overfit or are unstable, and in tabular-data competitions; the cost is extra compute and reduced interpretability.",
  state="ready_for_approval",conf="high")
K(3827,"M","","correct")
F(3828,"M","CORRUPTED;IMPRECISE","garbled first sentence ('can enable in higher-dimension spaces'), typos ('thanthe', 'products.Using'), and 'calculating the coordinates of higher dimensions' is inaccurate",
  pa="The kernel trick lets an algorithm that depends only on inner products (SVM, kernel PCA, kernel ridge regression) work as if the data were mapped to a high-dimensional feature space, without computing that mapping. A kernel function k(x, y) returns the inner product of the mapped points directly (e.g. RBF or polynomial kernel), which is much cheaper than constructing the coordinates and makes non-linear decision boundaries possible.",
  state="ready_for_approval",conf="high")
F(3829,"M","THIN_ANSWER;MISSING_FORMULA","asks to name and define; answer only names two measures",
  pa="Cosine similarity = (A . B) / (||A|| * ||B||), the angle between two rating/feature vectors. Pearson correlation is cosine similarity after mean-centring each vector, which corrects for users who rate systematically high or low. Others: Jaccard similarity (for binary/set data) and Euclidean distance.",
  state="ready_for_approval",conf="high")
X(3830,"LOW_RELEVANCE;CORRUPTED","obscure textbook topic with garbled text ('basic functions', reversed separability statement)")
K(3831,"M","","correct")
K(3832,"M","","correct")
F(3833,"M","IMPRECISE;MISSING_RATIONALE","reason (data leakage) not stated; 'closely packed' caveat is unsupported",
  pa="Scale after splitting. Fit the scaler (mean/standard deviation or min/max) on the training set only and apply it to the validation and test sets; fitting on all data leaks test-set statistics into training and gives optimistic estimates. In cross-validation, put the scaler inside a pipeline so it is refit within each fold.",
  state="ready_for_approval",conf="high")
F(3834,"M","UNVERIFIED_CLAIM;LOW_RELEVANCE","niche RL topic; claims such as 'works in continuous environments' and 'sensitive to initialization' need a source",
  state="needs_source",conf="low")
X(3835,"DUPLICATE","covered by 3819",dup_of=3819)
