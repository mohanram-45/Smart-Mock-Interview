from dec_helpers import *
# ---- Data Analysis block 3619-3643
K(3619,"E","THIN_ANSWER","correct but terse; lower-case fragments")
K(3620,"M","","correct; ML/stat concept, keep domain (secondary: ML)")
K(3621,"M","OPEN_ENDED","reasoned discussion answer")
F(3622,"E","QUESTION_CORRUPTED","question has PDF hyphen break 'per- forming'; answer acceptable",
  pq="What are the advantages of plotting your data before performing analysis?",state="ready_for_approval",conf="high")
K(3623,"M","OPEN_ENDED","opinion-style answer; uses nonstandard 'exploitatory' (usual term: confirmatory)")
X(3624,"MISLEADING;LOW_RELEVANCE","philosophy-of-science question; answer calls hypothesis testing 'eminently inductive' (it is hypothetico-deductive); not a standard junior interview question")
F(3625,"M","DOMAIN_MISMATCH;THIN_ANSWER","feature importance via GBM/RF is a modelling question",pd="Machine Learning",state="ready_for_approval",conf="medium")
K(3626,"M","","handles deletion / model-based imputation / tree models; acceptable")
F(3627,"M","THIN_ANSWER;MISLEADING","answer lists 'leave the model as is' and 'principal component regression' without naming cause clearly; garbled",
  pa="Most likely multicollinearity (or a suppressor effect): a coefficient measures a predictor's effect holding the others fixed, so its sign can differ from its marginal correlation with the response. Check the correlation matrix / VIF. Options: drop or combine correlated predictors, use ridge/lasso, or principal component regression; if the goal is prediction rather than interpretation the model can be left as is.",
  state="ready_for_approval",conf="high")
F(3628,"E","TOO_SHORT;DOMAIN_MISMATCH","answer is '- PCA' (2 words); modelling question",
  pa="Reduce dimensionality: PCA or other projections, feature selection (filter methods, L1/lasso), dropping low-variance or highly correlated features, using domain knowledge, or using regularised models / more data.",
  pd="Machine Learning",state="ready_for_approval",conf="high")
F(3629,"M","MISLEADING;DOMAIN_MISMATCH","lists ridge as feature selection; ridge shrinks coefficients but does not set them to zero",
  pa="Filter methods (univariate statistical tests per feature), wrapper methods (recursive feature elimination: train, drop the weakest ~10% of features, retrain, stop when accuracy drops sharply), and embedded methods (lasso / elastic net, which can zero out coefficients; tree-based importances). Ridge shrinks coefficients but does not remove features.",
  pd="Machine Learning",state="ready_for_approval",conf="high")
K(3630,"M","THIN_ANSWER","correct causes (p>n, perfect multicollinearity)")
K(3631,"M","OPEN_ENDED;THIN_ANSWER","gives heterogeneity only; other causes (multicollinearity, small subsets, outliers) not mentioned")
F(3632,"M","DOMAIN_MISMATCH","ensemble learning answer is good; domain should be ML",pd="Machine Learning",state="ready_for_approval",conf="medium")
F(3633,"M","QUESTION_CORRUPTED;OPEN_ENDED;THIN_ANSWER","lost 'fi' ligatures: 'wi' = 'wifi', 'o ce' = 'office'; answer weak",
  pq="Given that you have wifi data in your office, how would you determine which rooms and areas are underutilized and overutilized?",
  pa="Aggregate WiFi connection logs (connected devices per access point / room by hour) and normalise by room capacity and opening hours; compare utilisation distributions (average vs peak) and flag rooms persistently below or above agreed thresholds. Caveats: devices are not people, one person may have several devices, and access-point coverage overlaps rooms.",
  state="needs_review",conf="medium")
K(3634,"M","OPEN_ENDED;THIN_ANSWER","names concrete features (speeding, harsh braking, acceleration, route)")
K(3635,"H","OPEN_ENDED;THIN_ANSWER;REQUIRES_DATA","states modelling + constrained-optimisation framing only")
F(3636,"H","OPEN_ENDED;THIN_ANSWER;REQUIRES_DATA","answer only restates the question",state="needs_review",conf="low")
K(3637,"M","OPEN_ENDED;THIN_ANSWER","PageRank-style influence; acceptable sketch")
K(3638,"H","OPEN_ENDED;THIN_ANSWER;REQUIRES_DATA","names approach (predict landing distribution, minimise expected strokes)")
K(3639,"M","OPEN_ENDED","mean vs median rank for ordinal data; sound")
K(3640,"H","OPEN_ENDED;THIN_ANSWER;REQUIRES_DATA","similarity / centroid approach; acceptable sketch")
K(3641,"M","OPEN_ENDED;THIN_ANSWER","fingerprinting / bag-of-words + similarity")
K(3642,"M","OPEN_ENDED;THIN_ANSWER","k-means + elbow; terse but correct")
K(3643,"H","OPEN_ENDED;THIN_ANSWER","hybrid CF + content-based recommender")
# ---- Deep Learning 3644-3660
K(3644,"E","","fine; historical aside about Ivakhnenko is accurate in outline")
F(3645,"E","ANSWER_BLEED","answer ends with text of the next numbered question ('3) Differentiate supervised and unsupervised...')",
  trim=" 3) Differentiate",state="ready_for_approval",conf="high")
X(3646,"DUPLICATE","same question as 3691",dup_of=3691)
K(3647,"M","","universal-approximation point correct; efficiency argument sound")
X(3648,"CORRUPTED;DUPLICATE","answer is spun/garbled ('apprehends the sound of specific data'); overfitting asked 3x - keep 3793",dup_of=3793)
K(3649,"M","","backprop steps correct; awkward grammar")
X(3650,"CORRUPTED;ANSWER_BLEED;LOW_RELEVANCE","incoherent answer with embedded next question; Fourier transform not a standard DL interview topic")
X(3651,"CORRUPTED;FACTUAL_ERROR","spun text; calls 'CNN' a 'complex neural network'; vague question")
F(3652,"E","OUTDATED;CORRUPTED","lists Theano/Caffe2/CNTK/Chainer as current and run-together 'DyNetGensim'",
  pa="Mainstream frameworks today: PyTorch, TensorFlow with Keras (Keras 3 can run on TensorFlow, JAX or PyTorch) and JAX. Older or discontinued: Theano, CNTK, Caffe/Caffe2, Chainer. Hugging Face Transformers is a higher-level library built on top of these. (Verify against current documentation before ingestion: the landscape changes.)",
  state="needs_review",conf="medium")
K(3653,"E","THIN_ANSWER","correct but omits interpretability, compute cost, data hunger")
F(3654,"M","ANSWER_BLEED","answer ends with text of the next numbered question ('14) Explain Data Normalization')",
  trim=" 14) Explain Data Normalization",state="ready_for_approval",conf="high")
K(3655,"M","","symmetry-breaking explanation correct")
X(3656,"LOW_RELEVANCE","not a technical interview question; list of three words")
X(3657,"LOW_VALUE;DUPLICATE","mixes architectures with learning paradigms; near-duplicate of 3725",dup_of=3725)
X(3658,"LOW_VALUE;DUPLICATE","mixes architectures with learning paradigms; near-duplicate of 3726",dup_of=3726)
F(3659,"E","DOES_NOT_ADDRESS","question 'how many layers' is ill-posed; existing answer describes the three layer types",
  pq="What are the main types of layers in a neural network?",state="ready_for_approval",conf="high")
K(3660,"E","","non-linearity explanation correct")
