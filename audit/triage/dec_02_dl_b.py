from dec_helpers import *
X(3661,"LOW_VALUE","bare list of seven names; 'how many types' has no defined answer; covered by specific activation items")
K(3662,"E","","adequate; niche but correct")
K(3663,"E","IMPRECISE","'values much larger than 1.0 are transformed to 1.0' is loose (asymptotic); omits saturation / vanishing-gradient drawback")
K(3664,"E","","correct")
F(3665,"E","THIN_ANSWER;DOES_NOT_ADDRESS","never states what ReLU computes",
  pa="ReLU is f(x) = max(0, x): positive inputs pass through unchanged and negative inputs become 0. It is cheap to compute, does not saturate for x > 0 (which eases vanishing gradients) and produces sparse activations; its drawback is the 'dying ReLU' problem, where a unit stuck in the negative region outputs 0 and gets no gradient.",
  state="ready_for_approval",conf="high")
F(3666,"M","THIN_ANSWER","does not give the function or the purpose",
  pa="Leaky ReLU outputs x for x > 0 and alpha*x for x <= 0, where alpha is a small constant (e.g. 0.01). Negative inputs therefore still produce a small non-zero gradient, which reduces the 'dying ReLU' problem.",
  state="ready_for_approval",conf="high")
K(3667,"E","","correct")
X(3668,"LOW_RELEVANCE","niche activation; answer says 'new' and claims Google found it outperforms ReLU - dated and over-stated")
X(3669,"TIME_SENSITIVE;LOW_VALUE","'most used' changes over time (GELU/SwiGLU in transformers); answer oversimplified")
F(3670,"M","INCORRECT_ABSOLUTE","'ReLU has to be used in hidden layers' is overgeneralised",
  pa="Usually not for classification outputs (use sigmoid for binary and softmax for multi-class). ReLU, or a similar non-negative activation, can be used on the output of a regression model whose target is non-negative. ReLU is mainly used in hidden layers.",
  state="ready_for_approval",conf="high")
K(3671,"E","THIN_ANSWER","correct for multi-class classification output")
F(3672,"M","TYPO","'internet representation' should be 'internal representation'",
  repl=[("typically,internet representation","typically, the internal representation")],state="ready_for_approval",conf="high")
F(3673,"M","TYPO","'regulation technique' should be 'regularisation'; otherwise correct",
  repl=[("cheap regulation technique","cheap regularization technique")],state="ready_for_approval",conf="high")
K(3674,"E","","adequate")
X(3675,"LOW_RELEVANCE","Boltzmann machines are a legacy topic for junior roles; three near-duplicate items (3675, 3708, 3719)")
F(3676,"M","IMPRECISE","'model capacity can approximate any given function' is misleading",
  pa="Capacity is the range of functions a model can represent; it grows with the number and size of layers and parameters. Too little capacity underfits; too much relative to the amount of data overfits. It is managed through architecture size, regularisation and early stopping.",
  state="ready_for_approval",conf="high")
K(3677,"E","","correct")
F(3678,"M","MISSING_FORMULA","formula is referenced ('via the following formula') but absent",
  repl=[("via the following formula: Where, Θ - is the parameter vector","via theta := theta - alpha * grad J(theta), where theta is the parameter vector")],state="ready_for_approval",conf="high")
K(3679,"M","","correct")
K(3680,"M","","commonly cited benefits; flat-minima claim is widely repeated but debated")
F(3681,"E","DOES_NOT_ADDRESS","asks for an example; none given",
  pa="Element-wise (Hadamard) multiplication multiplies corresponding entries of two matrices of the same shape. Example: [[1,2],[3,4]] * [[5,6],[7,8]] = [[5,12],[21,32]]. In NumPy this is a * b (not a @ b, which is matrix multiplication).",
  state="needs_code_test",conf="high",code="import numpy as np; a=np.array([[1,2],[3,4]]); b=np.array([[5,6],[7,8]]); assert (a*b==np.array([[5,12],[21,32]])).all()")
F(3682,"M","ANSWER_BLEED","answer continues into '43) Explain the different layers of CNN...'",
  trim=" 43) Explain the different layers of CNN",state="ready_for_approval",conf="high")
F(3683,"M","MISLEADING","'RNNs use backpropagation because of their internal memory' is a wrong causal claim",
  pa="An RNN is a neural network for sequential data (text, speech, time series). It processes one element at a time and carries a hidden state forward, so earlier inputs can influence later outputs; the same weights are reused at every time step. It is trained with backpropagation through time and suffers from vanishing/exploding gradients, which LSTM and GRU cells were designed to reduce.",
  state="ready_for_approval",conf="high")
F(3684,"M","ANSWER_BLEED;TYPO","answer continues into '46) Explain the importance of LSTM'; 'BTT' should be BPTT",
  trim=" 46) Explain the importance of LSTM",repl=[("Back-propagation Through Time (BTT)","Back-propagation Through Time (BPTT)")],state="ready_for_approval",conf="high")
X(3685,"REDUNDANT;IMPRECISE","autoencoder items repeat (3672, 3685, 3686, 3699, 3723); wording sloppy ('distorted version')",dup_of=3672)
X(3686,"LOW_RELEVANCE;OUTDATED","frames deep autoencoders as stacked deep-belief networks (legacy); duplicate of 3723",dup_of=3723)
X(3687,"CORRUPTED;MEANINGLESS","question and answer are meaningless ('assumption structure')")
K(3688,"E","","adequate")
K(3689,"E","","adequate")
X(3690,"LOW_QUALITY;DUPLICATE","loaded question; vague answer; covered by 3688",dup_of=3688)
K(3691,"E","THIN_ANSWER","list answer; canonical copy of the 'applications' question")
X(3692,"DUPLICATE","overfitting asked three times; 3793 kept",dup_of=3793)
X(3693,"DUPLICATE","covered by 3660",dup_of=3660)
X(3694,"CORRUPTED;LOW_RELEVANCE","incoherent answer about a Fourier 'package'")
F(3695,"M","QUESTION_TYPO","'perception' should be 'perceptron'; steps are a simplified training loop",pq="What are the steps involved in training a perceptron in Deep Learning?",state="ready_for_approval",conf="high")
F(3696,"E","FACTUAL_ERROR","says loss compares the training dataset to the testing dataset (it compares predictions with targets)",
  pa="The loss function measures how far the network's predictions are from the true targets for a training example or batch. Training minimises it with gradient-based optimisation (e.g. cross-entropy for classification, mean squared error for regression). Tracking loss on training and validation data shows convergence and over/under-fitting.",
  state="ready_for_approval",conf="high")
X(3697,"DUPLICATE;OUTDATED;EDITORIAL","same question as 3652; contains advice to the candidate",dup_of=3652)
X(3698,"LOW_RELEVANCE;OVERSTATED","claims Swish outperforms all activations in efficiency; niche")
X(3699,"DUPLICATE","covered by 3672",dup_of=3672)
F(3700,"M","ANSWER_BLEED","answer ends with '14. Differentiate between a single-layer perceptron and a multi-layer perceptron.'",
  trim=" 14. Differentiate between a single-layer perceptron",state="ready_for_approval",conf="high")
