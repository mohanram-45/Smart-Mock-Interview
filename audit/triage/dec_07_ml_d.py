from dec_helpers import *
X(3881,"DUPLICATE","covered by 3826",dup_of=3826)
K(3882,"M","","correct")
K(3883,"M","IMPRECISE","'unbiased' is approximate; about 36.8% of rows (roughly one third) are out-of-bag; question wording ('how does it occur') is odd")
X(3884,"FACTUAL_ERROR;MISLEADING","premise is doubtful: boosting is generally more sensitive to noisy labels/outliers than bagging; comparison covered by 3909",dup_of=3909)
K(3885,"M","THIN_ANSWER","mixes detection (z-score, IQR, boxplots) and treatment (capping, transformation, removal)")
F(3886,"E","FACTUAL_ERROR","Random Search CV and Grid Search CV are hyperparameter-search methods, not cross-validation techniques",
  pa="K-fold, stratified K-fold (preserves class proportions), leave-one-out, leave-p-out, repeated k-fold, group k-fold (keeps groups together), time-series (forward-chaining) split, and bootstrap resampling. Grid search and random search are hyperparameter-search strategies that are usually combined with cross-validation.",
  state="ready_for_approval",conf="high")
X(3887,"DUPLICATE;LOW_VALUE","covered by 3778",dup_of=3778)
F(3888,"M","ILL_POSED_QUESTION;MISLEADING","cluster labels are pseudo-labels, not ground truth; supervised learning needs real labels",
  pq="What can you do if your dataset has no target variable but you need supervised learning?",
  pa="Supervised learning needs labels. Options: obtain labels (manual annotation, active learning to label only the most useful samples, crowdsourcing); use weak supervision or semi-supervised learning if some labels exist; use self-supervised pre-training; or fall back to unsupervised methods (clustering, anomaly detection). Cluster assignments can be used as pseudo-labels but reflect the clustering algorithm's assumptions, not ground truth, so validate them with domain knowledge.",
  state="needs_review",conf="medium")
X(3889,"LOW_VALUE","list of names; 'item-based' is a type of collaborative filtering; see 3804")
F(3890,"M","DOES_NOT_ADDRESS;IMPRECISE","RMSE is an evaluation metric, not a sparsity remedy; answer is one-sided",
  pa="Common approaches: matrix factorisation (SVD-style latent factor models, ALS) that learns dense low-dimensional user and item factors; dimensionality reduction; content-based or hybrid features so items/users with few interactions can still be scored; using implicit feedback to add signal; and regularisation. RMSE is used afterwards to evaluate prediction accuracy.",
  state="ready_for_approval",conf="high")
X(3891,"DUPLICATE","covered by 3770",dup_of=3770)
X(3892,"DUPLICATE","covered by 3880",dup_of=3880)
K(3893,"M","","correct")
K(3894,"H","IMPRECISE","VC dimension is the largest number of points that can be shattered by some arrangement; wording 'correctly' is loose")
F(3895,"M","MISLEADING","'handling incomplete data' is not an inherent strength of neural networks",
  pa="Advantages: learn complex non-linear relationships, learn features automatically from raw data, scale well with large datasets, and parallelise well on GPUs. Disadvantages: need large amounts of data and compute, act as black boxes (hard to interpret), are sensitive to hyperparameters and prone to overfitting without regularisation.",
  state="ready_for_approval",conf="high")
F(3896,"M","MISSING_FORMULA","no defining equation",
  pa="For a square matrix A, an eigenvector v is a non-zero vector whose direction is unchanged by the transformation, A v = lambda v; the eigenvalue lambda is the factor by which it is stretched. In PCA the eigenvectors of the covariance matrix are the principal directions and the eigenvalues give the variance along each.",
  state="ready_for_approval",conf="high")
X(3897,"DUPLICATE","covered by 3776",dup_of=3776)
K(3898,"E","THIN_ANSWER","omits RMSE")
X(3899,"DUPLICATE;LOW_VALUE","implementation-specific ('default'); splitting criteria covered by 3765",dup_of=3765)
F(3900,"M","FACTUAL_ERROR;MISLEADING","p-value is not the 'confidence of a model'",
  pa="The p-value is the probability, assuming the null hypothesis is true, of observing a result at least as extreme as the one found. A small p-value (below the chosen alpha, e.g. 0.05) is evidence against the null hypothesis. It is not the probability that the null hypothesis is true, and it says nothing about effect size or model quality.",
  state="ready_for_approval",conf="high")
K(3901,"M","THIN_ANSWER","omits detection (VIF) and ridge regression")
K(3902,"M","THIN_ANSWER","correct; consequences and tests not mentioned")
X(3903,"DUPLICATE","covered by 3824",dup_of=3824)
X(3904,"DUPLICATE;LOW_VALUE","covered by 3792",dup_of=3792)
K(3905,"M","","correct (hard vs soft voting not distinguished)")
K(3906,"M","","correct")
X(3907,"OUTDATED;LOW_RELEVANCE","library renamed (now ydata-profiling); tool trivia")
F(3908,"M","FACTUAL_ERROR","claim reversed: correlated variables make PCA more effective at compressing, since few components capture most variance",
  pa="Strong correlation between variables means redundant information, so PCA can capture most of the variance with few components; it is therefore more effective at dimensionality reduction. With uncorrelated variables each component carries similar variance and little compression is possible. PCA is applied to standardised data (or the correlation matrix) so that scale differences do not dominate.",
  state="ready_for_approval",conf="high")
K(3909,"M","","correct")
K(3910,"M","IMPRECISE","gamma is the reach of a single training example in the RBF kernel; wording 'support vectors' is loose; overlaps with 3906")
X(3911,"DUPLICATE","covered by 3815",dup_of=3815)
X(3912,"DUPLICATE","covered by 3759",dup_of=3759)
X(3913,"DUPLICATE","covered by 3864",dup_of=3864)
X(3914,"DUPLICATE","covered by 3821",dup_of=3821)
F(3915,"H","PLACEHOLDER;OPEN_ENDED","'our company's users' references an unspecified company",
  pq="How would you design a recommendation system for an e-commerce platform?",
  state="needs_review",conf="medium")
X(3916,"OPEN_ENDED;LOW_VALUE","company-specific behavioural question without a technical answer")
X(3917,"PLACEHOLDER;UNANSWERABLE","refers to 'our current data process' with no context")
K(3918,"M","TIME_SENSITIVE","historic case study; answer reasonable (matrix factorisation + ensembles)")
X(3919,"EDITORIAL;LOW_VALUE","answer is commentary about interview questions plus vendor recommendations")
X(3920,"EDITORIAL;OUTDATED;UNANSWERABLE","speculative, dated, with editorial lead-in")
K(3921,"H","","accurate high-level description of AlphaGo's approach")
K(3922,"E","","correct")
K(3923,"E","","correct")
X(3924,"DUPLICATE;MISLEADING","covered by 3818; answer anthropomorphises deep learning",dup_of=3818)
K(3925,"E","","correct")
