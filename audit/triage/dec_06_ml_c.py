from dec_helpers import *
P="COSMETIC_PREFIX;"   # raw answers start with 'Ans.' (stripped globally at build time)
F(3836,"M",P+"FACTUAL_ERROR","says LDA is unsupervised (it is supervised)",
  pa="PCA is unsupervised: it finds orthogonal directions of maximum variance and ignores class labels. LDA is supervised: it uses class labels to find directions that maximise between-class separation relative to within-class scatter. PCA is used for general dimensionality reduction/compression; LDA for class-separating projections and as a classifier. LDA yields at most (number of classes - 1) components.",
  state="ready_for_approval",conf="high")
F(3837,"E",P+"THIN_ANSWER","omits Euclidean (the default) and mixes in rarely used measures",
  pa="Common distance metrics for KNN: Euclidean (default; continuous features), Manhattan, Minkowski (generalises both), Hamming (categorical/binary features), cosine distance (text, high-dimensional sparse data) and Mahalanobis (accounts for feature correlation). Features should be scaled first so no single feature dominates.",
  state="ready_for_approval",conf="high")
F(3838,"E",P+"IMPRECISE","chi-square tests association/independence rather than 'measuring correlation'; omits Cramer's V",
  pa="The chi-square test of independence tests whether two categorical variables are associated; its p-value indicates evidence of association, and Cramer's V (derived from chi-square, range 0 to 1) measures the strength of the association. Mutual information is another option.",
  state="ready_for_approval",conf="high")
F(3839,"M",P+"INCORRECT_ABSOLUTE","'KNN is the only algorithm' is false",
  pa="Several methods work for both types. KNN imputation fills a missing value from the nearest neighbours (mean for continuous, mode for categorical). Others: MICE / iterative imputation with a suitable model per column, random forest imputation (missForest), and simple mean/median/mode imputation.",
  state="ready_for_approval",conf="high")
K(3840,"M",P+"THIN_ANSWER","correct but omits correlated predictors / multicollinearity as a reason")
K(3841,"E",P+"THIN_ANSWER","acceptable")
K(3842,"E",P+"","correct")
K(3843,"E",P+"THIN_ANSWER","correct")
F(3844,"M",P+"IMPRECISE;MISLEADING","'noise should be removed' and 'more epochs' are not standard remedies for high bias",
  pa="High bias means the model is too simple to capture the true pattern (underfitting): training and validation error are both high. Remedies: use a more complex model, add features or interactions, reduce regularisation, and train longer (for iterative models such as neural networks). Compare with high variance, where training error is low but validation error is high.",
  state="ready_for_approval",conf="high")
F(3845,"M",P+"TYPO","'tarin' typo",repl=[("tarin","train")],state="ready_for_approval",conf="high")
F(3846,"M",P+"FACTUAL_ERROR","VIF is not 'the percentage of variance which remains unaffected'; tolerance = 1 - R^2 is that quantity and VIF = 1/tolerance",
  pa="The variance inflation factor (VIF) measures how much the variance of a coefficient is inflated by multicollinearity: VIF_j = 1 / (1 - R_j^2), where R_j^2 comes from regressing predictor j on the other predictors. Tolerance = 1 - R_j^2 = 1 / VIF. Rule of thumb: VIF = 1 means no correlation; above about 5 (some use 10) signals problematic multicollinearity.",
  state="ready_for_approval",conf="high")
F(3847,"M",P+"UNVERIFIED_CLAIM","'its inclusion increases the performance' is unsupported",
  pa="An ordinal categorical variable can be encoded as integers and treated as continuous when the spacing between levels is roughly meaningful (e.g. rating 1-5). It saves parameters versus one-hot encoding, but assumes a linear effect per level; if the spacing is not equal, performance can suffer. Nominal categories (no order) should not be treated as continuous.",
  state="needs_review",conf="medium")
F(3848,"M",P+"IMPRECISE;MISSING_FORMULA","vague description of MLE; no log-likelihood",
  pa="Logistic regression has no closed-form solution, so coefficients are found by maximum likelihood: choose the weights that maximise the log-likelihood sum[ y*log(p) + (1-y)*log(1-p) ], where p = sigmoid(w.x + b). Maximising this is equivalent to minimising cross-entropy loss, solved iteratively (gradient descent, Newton/IRLS).",
  state="ready_for_approval",conf="high")
X(3849,"FACTUAL_ERROR;DUPLICATE","claims Hamming distance is used in KNN; covered correctly by 3837",dup_of=3837)
F(3850,"E",P+"CORRUPTED;IMPRECISE","garbled definition ('sophisticated way of writing software', 'run onto n threads')",
  pa="A pipeline chains data-processing steps (imputation, scaling, encoding, feature selection) and a final estimator into a single object (e.g. scikit-learn Pipeline). It applies the same steps in order at fit and predict time, avoids data leakage during cross-validation (preprocessing is fitted only on training folds), and makes the workflow reproducible and easy to tune and deploy.",
  state="ready_for_approval",conf="high")
X(3851,"DUPLICATE","covered by 3820",dup_of=3820)
F(3852,"E",P+"IMPRECISE","'increases bias' is a trade-off, not a benefit",
  repl=[("- Increases bias","- Trades a small increase in bias for lower variance")],state="ready_for_approval",conf="high")
F(3853,"E",P+"PROVENANCE_RISK;MISSING_FORMULA","answer contains a markdown hyperlink to a third-party site; density formula absent",
  repl=[("[mean, mode and median](https://www.statisticshowto.com/probability-and-statistics/statistics-definitions/mean-median-mode/)","mean, mode and median")],
  state="ready_for_approval",conf="high")
F(3854,"E",P+"IMPRECISE","68% lies within one standard deviation of the mean, not 'around the median'",
  pa="In a normal distribution about 68% of values lie within one standard deviation of the mean, about 95% within two, and about 99.7% within three (the empirical or 68-95-99.7 rule).",
  state="ready_for_approval",conf="high")
K(3855,"M",P+"","correct")
F(3856,"E",P+"IMPRECISE","a random variable is a function mapping outcomes to numbers, not 'a set of possible values'",
  pa="A random variable is a variable whose value is a numerical outcome of a random experiment (formally a function from outcomes to numbers). Examples: the number of heads in 10 coin tosses, or the value shown when rolling a die. It can be discrete or continuous.",
  state="ready_for_approval",conf="high")
F(3857,"M",P+"IMPRECISE","vague wording",
  pa="Degrees of freedom is the number of values in a calculation that are free to vary. For a sample variance it is n - 1 (one degree is used up by estimating the mean); for a chi-square test of independence on an r x c table it is (r - 1)(c - 1). Degrees of freedom determine the shape of the t, chi-square and F distributions.",
  state="ready_for_approval",conf="high")
F(3858,"E",P+"FACTUAL_ERROR;TIME_SENSITIVE","describes user-to-user filtering and company-specific practice; the published Amazon approach is item-to-item collaborative filtering (Linden et al., 2003)",
  pq="How does item-based collaborative filtering recommend similar items?",
  pa="Item-based collaborative filtering computes similarity between items from the pattern of user interactions (e.g. cosine or Pearson over item rating/purchase vectors) and recommends items most similar to those a user has already liked or bought. It scales better than user-based filtering when there are far more users than items and similarities can be precomputed.",
  state="needs_review",conf="medium")
K(3859,"E",P+"","correct")
K(3860,"E",P+"","correct")
F(3861,"M",P+"MISSING_FORMULA;IMPRECISE","bias enters the expected squared error as bias squared",
  repl=[("bias error+variance error+ irreducible error","bias^2 + variance + irreducible error (noise)")],
  state="ready_for_approval",conf="high")
F(3862,"E",P+"CORRUPTED;MISSING_FORMULA","garbled explanation; no formula",
  pa="Adjusted R^2 is generally preferred when comparing models with different numbers of predictors. R^2 never decreases when a predictor is added, even a useless one. Adjusted R^2 = 1 - (1 - R^2)(n - 1)/(n - p - 1) penalises extra predictors and only rises if the new variable improves the fit more than chance would.",
  state="ready_for_approval",conf="high")
X(3863,"DUPLICATE;FACTUAL_ERROR","covered by 3816; hypothesis wording is incorrect",dup_of=3816)
F(3864,"M","FACTUAL_ERROR;MISSING_FORMULA","L1 does not assign weights of 'exactly 1 or 0'; it drives many weights to exactly zero",
  pa="L1 (lasso) adds lambda * sum|w| to the loss; it produces sparse solutions (many weights exactly zero), so it also performs feature selection, and corresponds to a Laplace prior. L2 (ridge) adds lambda * sum(w^2); it shrinks all weights toward zero without making them exactly zero, handles correlated features more stably, and corresponds to a Gaussian prior.",
  state="ready_for_approval",conf="high")
K(3865,"M","","reasonable comparison; generalisations are hedged")
X(3866,"DUPLICATE","covered by 3770 (3770's wording is more accurate: plots rates)",dup_of=3770)
X(3867,"DUPLICATE;LOW_VALUE","'AUC curve' is a misnomer; covered by 3795",dup_of=3795)
F(3868,"H","CORRUPTED;FACTUAL_ERROR;MISSING_FORMULA","'sum of likelihood residuals' is garbled; claims accuracy is always 100% on development data (false)",
  pa="The log-likelihood of a logistic regression is the sum over observations of y*log(p) + (1-y)*log(1-p), where p is the predicted probability. Higher (less negative) values mean a better fit. Maximum likelihood estimation maximises it; deviance = -2 * log-likelihood is used to compare nested models (likelihood-ratio test) and AIC = 2k - 2 * log-likelihood to compare models with different numbers of parameters.",
  state="ready_for_approval",conf="high")
K(3869,"M","QUESTION_FORMAT;TYPO","acceptable; omits precision/recall and calibration")
F(3870,"M","UNVERIFIED_CLAIM;FACTUAL_ERROR","complexity claims O(N^2 K) vs O(N^3) for logistic regression are unsupported; 'SVM is better in most cases' is an overgeneralisation",
  pa="Advantages: effective in high-dimensional spaces, including when features outnumber samples; the margin-maximising objective gives good generalisation; the kernel trick allows non-linear boundaries; the decision function depends only on the support vectors, so the model is compact. Disadvantages: training scales poorly with many samples, needs feature scaling and kernel/C tuning, and does not natively give probabilities.",
  state="ready_for_approval",conf="high")
F(3871,"M","ILL_POSED_QUESTION;INCORRECT_ABSOLUTE","assumes XGBoost always beats SVM",
  pq="When does XGBoost tend to outperform an SVM, and when might an SVM be preferable?",
  pa="XGBoost (gradient-boosted trees) usually does better on tabular data with mixed feature types, missing values and non-linear interactions, needs little scaling and scales to large datasets. SVMs can be preferable on smaller datasets, in high-dimensional sparse settings such as text, or when a good kernel is known. Neither wins universally; compare with cross-validation.",
  state="needs_review",conf="medium")
K(3872,"H","","correct; niche but relevant to search / learning-to-rank roles")
F(3873,"H","ILL_POSED_QUESTION;DOES_NOT_ADDRESS","'soft margin vs linear kernel' conflates two independent concepts; answer explains hard margin, soft margin and kernels separately",
  pq="What is the difference between hard-margin and soft-margin SVM, and what role does the kernel play?",
  pa="Hard-margin SVM requires every training point to be correctly classified outside the margin, so it only works if the data are linearly separable and is sensitive to outliers. Soft-margin SVM allows some violations, penalised by slack variables and controlled by C (large C = fewer violations, higher variance; small C = wider margin, more regularisation). The kernel is a separate choice: a linear kernel keeps a linear boundary, while kernels such as RBF or polynomial map data implicitly into a higher-dimensional space to give non-linear boundaries. Soft-margin can be used with any kernel.",
  state="ready_for_approval",conf="high")
F(3874,"H","TYPO","'linear fictions' should be 'linear functions'",repl=[("linear fictions","linear functions")],state="ready_for_approval",conf="high")
K(3875,"E","OVERSTATED","'works great in practice' and 'not sensitive to irrelevant features' are optimistic; correct overall")
F(3876,"M","FACTUAL_ERROR;QUESTION_TYPO","the binary-feature variant is Bernoulli Naive Bayes; 'Binomial' is not the standard name (Multinomial is the count-based variant)",
  pq="Is Gaussian Naive Bayes the same as Bernoulli Naive Bayes?",
  repl=[("Binomial Naive Bayes","Bernoulli Naive Bayes")],state="ready_for_approval",conf="high")
F(3877,"H","CORRUPTED;DOES_NOT_ADDRESS","garbled repeated formula; answer describes Bayesian networks rather than the Bayes classifier",
  pa="The Bayes classifier assigns x to the class with the highest posterior P(y|x); it is the theoretically optimal classifier (lowest possible error, the Bayes error) but needs the true joint distribution, which is impractical in high dimensions. Naive Bayes approximates it by assuming the features are conditionally independent given the class, so P(x|y) factorises into a product of per-feature terms that can be estimated from limited data. Bayesian networks sit in between by allowing selected dependencies.",
  state="ready_for_approval",conf="high")
K(3878,"E","IMPRECISE","face recognition is a weak example; others correct")
F(3879,"E","FACTUAL_ERROR;IMPRECISE","lists 'discriminant functions' as an attribute (Naive Bayes is a generative model); wording muddled",
  pa="Naive Bayes is a supervised learning algorithm: it is trained on labelled data. It is a family of generative classifiers based on Bayes' theorem with a conditional-independence assumption, with variants such as Gaussian, Multinomial and Bernoulli Naive Bayes depending on the feature type. It handles multi-class problems naturally.",
  state="ready_for_approval",conf="high")
F(3880,"M","CORRUPTED;MISSING_FORMULA","first sentence is garbled; no formulas",
  pa="Precision = TP / (TP + FP): of the items predicted positive, the fraction that are truly positive (positive predictive value). Recall = TP / (TP + FN): of the actual positives, the fraction found (sensitivity). Higher precision means fewer false alarms; higher recall means fewer misses; F1 combines them.",
  state="ready_for_approval",conf="high")
