"""Decisions and controlled vocabularies for curated v1 (Stage 1 remediation).
All keys are *processed IDs* from data/processed/questions.csv (= data/audit/triage.csv `id`)."""

# 5 near-duplicates removed; value = ID of the stronger record that is kept
DUPLICATES_REMOVED = {
    3754: (3678, "same question as 3678 ('gradient descent'); 3678 adds the update rule"),
    3645: (3922, "same intent as 3922 (AI vs ML vs DL); 3922 is more accurate"),
    3688: (3818, "ML-vs-DL contrast is covered by 3818, which is more precise"),
    3644: (3818, "'What is deep learning?' is covered by 3818; 3644 carries historical trivia"),
    3793: (3882, "'What is overfitting?' is fully covered by 3882 (overfitting and underfitting)"),
}

# Approved records moved to the review queue after the independent factual review.
MOVED_TO_QUEUE = {
 3619: "IMPRECISE: 'or train error metrics' - training error always improves with complexity, so it cannot address R^2's flaw; better: held-out/cross-validated error (RMSE/MAE), AIC/BIC. Answer is also a lower-case fragment.",
 3671: "IMPRECISE: softmax is typically (not necessarily) the output activation for multi-class classification.",
 3680: "IMPRECISE: 'finds flat minima' and 'avoid local minima' are contested, loosely stated benefits of mini-batches.",
 3718: "IMPRECISE: the 'four main types' list is arbitrary and omits undercomplete, denoising and variational autoencoders.",
 3739: "IMPRECISE: 'weights will always converge to the optimal point regardless of the initial value' ignores separable-data logistic regression (no finite optimum) and step-size dependence.",
 3766: "IMPRECISE: the random feature subset is drawn at each split, not once per tree.",
 3737: "IMPRECISE: convolution is translation-equivariant; approximate invariance comes from pooling.",
 3941: "IMPRECISE: 'nonparametric and hence robust to outliers' is faulty reasoning; trees have several hyperparameters.",
 3875: "IMPRECISE: 'works great in practice' and 'not sensitive to irrelevant features' are overgeneral; NB probabilities are poorly calibrated.",
 3748: "IMPRECISE (second pass): 'will make the weights converge to a wrong value' is overstated.",
 3785: "IMPRECISE (second pass): 3-sigma coverage is about 99.7%, stated as about 99%.",
}

# Domain: statistics / A-B testing / analysis fundamentals live under Data Analysis;
# ML-specific statistics (MLE, log-likelihood, Bayes, VIF, heteroscedasticity, bias-variance, ...) stay in ML.
TO_DATA_ANALYSIS = [3786,3787,3788,3789,3790,3791,3814,3816,3853,3854,3855,3856,3857,3838,3900,3928,3929,3937,3938,3885,3936]
DOMAIN_OVERRIDE = {i: "Data Analysis" for i in TO_DATA_ANALYSIS}
DOMAIN_OVERRIDE.update({3678: "Machine Learning",   # gradient descent is foundational, kept as the stronger duplicate
                        3818: "Deep Learning"})     # deep-learning definition

# Difficulty: starts from the reviewer rubric in data/audit/triage.csv (proposed_difficulty); these are adjustments
# made when applying one rubric across domains. Easy = single-concept recall; Medium = comparison / mechanism /
# short code / simple application; Hard = multi-step reasoning, design with trade-offs, non-trivial implementation.
DIFF_OVERRIDE = {
 4038:"Easy",4039:"Easy",4042:"Easy",4043:"Easy",4044:"Easy",4045:"Easy",4047:"Easy",4046:"Medium",
 4063:"Easy",4068:"Easy",4078:"Easy",
 3788:"Easy",3789:"Easy",3790:"Easy",3816:"Easy",3938:"Medium",
 3672:"Easy",3673:"Easy",3682:"Easy",3683:"Easy",3716:"Easy",3750:"Medium",3749:"Medium",
 3755:"Easy",3759:"Easy",3762:"Easy",3763:"Easy",3777:"Easy",3805:"Hard",3828:"Medium",3848:"Medium",
 3880:"Easy",3902:"Easy",3905:"Easy",3942:"Medium",3999:"Medium",3792:"Easy",4004:"Hard",
}

def _t(domain, topic, ids): return [(i, domain, topic) for i in ids]
_T = []
_ML="Machine Learning"; _DL="Deep Learning"; _NLP="NLP"; _PY="Python"; _SQL="SQL"; _DA="Data Analysis"
# ---- Data Analysis
_T += _t(_DA,"Statistics fundamentals",[3786,3853,3854,3855,3856,3857,3838,3928,3929])
_T += _t(_DA,"Hypothesis testing and A/B testing",[3787,3788,3789,3790,3791,3814,3816,3900])
_T += _t(_DA,"Data preparation and cleaning",[3626,3885,3936,3938])
_T += _t(_DA,"Exploratory analysis and methodology",[3620,3621,3622,3623,3627,3630,3631])
_T += _t(_DA,"Time series",[3937])
_T += _t(_DA,"Product and business metrics",[4026])
_T += _t(_DA,"Analytical case studies",[3634,3635,3637,3638,3639,3640,3641,3642,3643])
# ---- Deep Learning
_T += _t(_DL,"Neural network fundamentals",[3647,3649,3653,3659,3674,3676,3677,3681,3689,3691,3695,3696,3700,3702,3710,3736,3744,3751])
_T += _t(_DL,"Activation functions",[3660,3662,3663,3664,3665,3666,3667,3670,3745])
_T += _t(_DL,"Initialisation and optimisation",[3654,3655,3679,3715,3738,3746,3747])
_T += _t(_DL,"Regularisation and hyperparameters",[3673,3701,3703,3704,3740,3742,3749])
_T += _t(_DL,"Convolutional networks",[3682,3712,3728])
_T += _t(_DL,"Sequence models and transformers",[3683,3684,3714,3716,3730,3731,3750])
_T += _t(_DL,"Autoencoders and generative models",[3672,3717,3734])
_T += _t(_DL,"Transfer learning",[3729])
_T += _t(_DL,"Deep learning overview",[3818])
# ---- NLP
_T += _t(_NLP,"NLP fundamentals",[3957,3977])
_T += _t(_NLP,"Text preprocessing and representation",[3958,3959,3976,3979,3987])
_T += _t(_NLP,"Syntax and parsing",[3960,3978,3983,3992,3970])
_T += _t(_NLP,"Semantics and pragmatics",[3969,3975])
_T += _t(_NLP,"NLP tasks and models",[3982,3984,3986,3989,3993])
# ---- Python
_T += _t(_PY,"Core language",[4059,4060,4062])
_T += _t(_PY,"Functions and decorators",[4058])
_T += _t(_PY,"Object-oriented programming and design patterns",[4072,4073,4074])
_T += _t(_PY,"Data structures and algorithms",[4063,4064,4065,4066,4067,4068,4069,4070,4071])
_T += _t(_PY,"Data science libraries",[4078,4079,4080])
_T += _t(_PY,"Testing",[4083])
_T += _t(_PY,"Generators and concurrency",[4084,4085])
# ---- SQL
_T += _t(_SQL,"SQL fundamentals",[4028,4029,4030,4031,4034,4035,4036,4037])
_T += _t(_SQL,"Joins",[4032,4033,4046])
_T += _t(_SQL,"Subqueries and CTEs",[4038,4039])
_T += _t(_SQL,"Window functions",[4048,4049])
_T += _t(_SQL,"Database design",[4040,4041,4043,4047])
_T += _t(_SQL,"Indexing and performance",[4042,4052,4053,4056,4057])
_T += _t(_SQL,"Transactions and concurrency",[4044,4045,4054])
_T += _t(_SQL,"Partitioning and scaling",[4051,4055])
# ---- Machine Learning
_T += _t(_ML,"ML foundations",[3752,3771,3922,3923,3925,3946,3825,3831,3832,3953,3927,3999,3894,3895])
_T += _t(_ML,"Linear and logistic regression",[3753,3755,3948,3949,3956,3798,3799,3848,3868,3869])
_T += _t(_ML,"Regression diagnostics",[3846,3861,3862,3901,3902,3947])
_T += _t(_ML,"Instance-based and probabilistic classifiers",[3757,3758,3759,3837,3865,3876,3877,3878,3879,3819])
_T += _t(_ML,"Support vector machines",[3760,3761,3762,3828,3870,3872,3873,3874,3906,3910])
_T += _t(_ML,"Decision trees and ensembles",[3632,3763,3764,3765,3767,3768,3800,3801,3802,3821,3826,3842,3843,3852,3883,3905,3909,3942])
_T += _t(_ML,"Clustering",[3772,3774,3775,3776,3777])
_T += _t(_ML,"Dimensionality reduction",[3778,3779,3780,3781,3836,3908,3896])
_T += _t(_ML,"Model evaluation and metrics",[3769,3770,3795,3796,3797,3822,3823,3827,3859,3860,3880,3898,3935,3998])
_T += _t(_ML,"Validation and model selection",[3792,3820,3833,3845,3850,3886,3893])
_T += _t(_ML,"Bias-variance and regularisation",[3784,3794,3864,3840,3882,3844,3933,3934])
_T += _t(_ML,"Feature engineering and data preparation",[3625,3628,3629,3808,3839,3841,3824,3926,3931,3945,3995,3996,4001])
_T += _t(_ML,"Loss functions and optimisation",[3678,3939,3782,3783,3997])
_T += _t(_ML,"Recommender systems",[3804,3805,3806,3807,3829,3890,3918,4004,4005])
_T += _t(_ML,"Probability and likelihood",[3756,3815])
_T += _t(_ML,"Advanced learning paradigms",[3811,3812,3921])
_T += _t(_ML,"Applied ML case studies",[3954,4002,4007,4008,4009,4010,4012,4022,4024,4025])
TOPIC = {}
for i,d,t in _T:
    TOPIC[i]=(d,t)
