# Proposed corrections

174 FIX records. Nothing here has been applied. Grouped by review state; IDs are processed IDs, `raw_id` is the id in `questions_seed.csv`. Proposed answers are drafts written for review: "ready_for_approval" means the change uses well-established facts or a mechanical edit, not that it is approved.

## A. Ready for approval (139)

### 3622  (raw 4; Data Analysis; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** QUESTION_CORRUPTED
* **Issue:** question has PDF hyphen break 'per- forming'; answer acceptable
* **Original question:** What are advantages of plotting your data before per- forming analysis?
* **Proposed question:** What are the advantages of plotting your data before performing analysis?
* **Original answer:** Data sets have errors. You won't find them all but you might find some. That 212 year old man. That 9 foot tall woman. Variables can have skewness, outliers etc. Then the arithmetic mean might not be useful. Which means the standard deviation isn't useful. Variables can be multimodal! If a variable is multimodal then anything based on its mean or median is going to be suspect.
* **Proposed answer:** none proposed (answer unchanged)

### 3625  (raw 7; Data Analysis; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** medium; **flags:** DOMAIN_MISMATCH;THIN_ANSWER
* **Issue:** feature importance via GBM/RF is a modelling question
* **Proposed difficulty:** Medium
* **Proposed domain:** Machine Learning
* **Original question:** How can you determine which features are the most important in your model?
* **Original answer:** run the features though a Gradient Boosting Machine or Random Forest to generate plots of relative importance and information gain for each feature in the ensembles. Look at the variables added in forward variable selection
* **Proposed answer:** none proposed (answer unchanged)

### 3627  (raw 9; Data Analysis; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** THIN_ANSWER;MISLEADING
* **Issue:** answer lists 'leave the model as is' and 'principal component regression' without naming cause clearly; garbled
* **Proposed difficulty:** Medium
* **Original question:** You have several variables that are positively correlated with your response, and you think combining all of the variables could give you a good prediction of your response. However, you see that in the multiple linear regression, one of the weights on the predictors is negative. What could be the issue?
* **Original answer:** Multicollinearity refers to a situation in which two or more explanatory variables in a model are highly linearly related. Leave the model as is, despite multicollinearity. The presence of multicollinearity doesn't affect the efficiency of extrapolating the fitted model to new data provided that the predictor variables follow the same pattern of multicollinearity in the new data as in the data on which the regression model is based. principal component regression
* **Proposed answer (rewritten_answer):** Most likely multicollinearity (or a suppressor effect): a coefficient measures a predictor's effect holding the others fixed, so its sign can differ from its marginal correlation with the response. Check the correlation matrix / VIF. Options: drop or combine correlated predictors, use ridge/lasso, or principal component regression; if the goal is prediction rather than interpretation the model can be left as is.

### 3628  (raw 10; Data Analysis; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** TOO_SHORT;DOMAIN_MISMATCH
* **Issue:** answer is '- PCA' (2 words); modelling question
* **Proposed domain:** Machine Learning
* **Original question:** Let’s say you’re given an unfeasible amount of predictors in a predictive modeling task. What are some ways to make the prediction more feasible?
* **Original answer:** - PCA
* **Proposed answer (rewritten_answer):** Reduce dimensionality: PCA or other projections, feature selection (filter methods, L1/lasso), dropping low-variance or highly correlated features, using domain knowledge, or using regularised models / more data.

### 3629  (raw 11; Data Analysis; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** MISLEADING;DOMAIN_MISMATCH
* **Issue:** lists ridge as feature selection; ridge shrinks coefficients but does not set them to zero
* **Proposed difficulty:** Medium
* **Proposed domain:** Machine Learning
* **Original question:** Now you have a feasible amount of predictors, but you’re fairly sure that you don’t need all of them. How would you perform feature selection on the dataset?
* **Original answer:** ridge / lasso / elastic net regression Univariate Feature Selection where a statistical test is applied to each feature individually. You retain only the best features according to the test outcome scores "Recursive Feature Elimination": First, train a model with all the feature and evaluate its performance on held out data. Then drop let say the 10% weakest features (e.g. the feature with least absolute coefficients in a linear model) and retrain on the remaining features. Iterate until you observe a sharp drop in the predictive accuracy of the model.
* **Proposed answer (rewritten_answer):** Filter methods (univariate statistical tests per feature), wrapper methods (recursive feature elimination: train, drop the weakest ~10% of features, retrain, stop when accuracy drops sharply), and embedded methods (lasso / elastic net, which can zero out coefficients; tree-based importances). Ridge shrinks coefficients but does not remove features.

### 3632  (raw 14; Data Analysis; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** medium; **flags:** DOMAIN_MISMATCH
* **Issue:** ensemble learning answer is good; domain should be ML
* **Proposed difficulty:** Medium
* **Proposed domain:** Machine Learning
* **Original question:** What is the main idea behind ensemble learning? If I had many different models that predicted the same response variable, what might I want to do to incorporate all of the models? Would you expect this to perform better than an individual model or worse?
* **Original answer:** The assumption is that a group of weak learners can be combined to form a strong learner. Hence the combined model is expected to perform better than an individual model. Assumptions: average out biases reduce variance Bagging works because some underlying learning algorithms are unstable: slightly different inputs leads to very different outputs. If you can take advantage of this instability by running multiple instances, it can be shown that the reduced instability leads to lower error. Boosting works because of the focus on better defining the "decision edge". By reweighting examples near the margin (the positive and negative examples) you get a reduced error. Use the outputs of your models as inputs to a meta-model. For example, if you're doing binary classification, you can use all the probability outputs of your individual models as inputs to a final logistic regression (or any model, really) that can combine the probability estimates. One very important point is to make sure that the output of your models are out-of-sample predictions. This means that the predicted value for any row in your dataframe should NOT depend on the actual value for that row.
* **Proposed answer:** none proposed (answer unchanged)

### 3645  (raw 27; Deep Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ANSWER_BLEED
* **Issue:** answer ends with text of the next numbered question ('3) Differentiate supervised and unsupervised...')
* **Proposed difficulty:** Easy
* **Original question:** What are the main differences between AI, Machine Learning, and Deep Learning?
* **Original answer:** AI stands for Artificial Intelligence. It is a technique which enables machines to mimic human behavior. Machine Learning is a subset of AI which uses statistical methods to enable machines to improve with experiences. Deep learning is a part of Machine learning, which makes the computation of multi-layer neural networks feasible. It takes advantage of neural networks to simulate human-like decision making. 3) Differentiate supervised and unsupervised deep learning procedures. Supervised learning is a system in which both input and desired output data are provided. Input and output data are labeled to provide a learning basis for future data processing. Unsupervised procedure does not need labeling information explicitly, and the operations can be carried out without the same. The common unsupervised learning method is cluster analysis. It is used for exploratory data analysis to find hidden patterns or grouping in data.
* **Proposed answer (trim):** AI stands for Artificial Intelligence. It is a technique which enables machines to mimic human behavior. Machine Learning is a subset of AI which uses statistical methods to enable machines to improve with experiences. Deep learning is a part of Machine learning, which makes the computation of multi-layer neural networks feasible. It takes advantage of neural networks to simulate human-like decision making.

### 3654  (raw 36; Deep Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ANSWER_BLEED
* **Issue:** answer ends with text of the next numbered question ('14) Explain Data Normalization')
* **Proposed difficulty:** Medium
* **Original question:** What is the meaning of term weight initialization in neural networks?
* **Original answer:** In neural networking, weight initialization is one of the essential factors. A bad weight initialization prevents a network from learning. On the other side, a good weight initialization helps in giving a quicker convergence and a better overall error. Biases can be initialized to zero. The standard rule for setting the weights is to be close to zero without being too small. 14) Explain Data Normalization. Data normalization is an essential preprocessing step, which is used to rescale values to fit in a specific range. It assures better convergence during backpropagation. In general, data normalization boils down to subtracting the mean of each data point and dividing by its standard deviation.
* **Proposed answer (trim):** In neural networking, weight initialization is one of the essential factors. A bad weight initialization prevents a network from learning. On the other side, a good weight initialization helps in giving a quicker convergence and a better overall error. Biases can be initialized to zero. The standard rule for setting the weights is to be close to zero without being too small.

### 3659  (raw 41; Deep Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOES_NOT_ADDRESS
* **Issue:** question 'how many layers' is ill-posed; existing answer describes the three layer types
* **Original question:** How many layers in the neural network?
* **Proposed question:** What are the main types of layers in a neural network?
* **Original answer:** Input Layer The input layer contains input neurons which send information to the hidden layer. Hidden Layer The hidden layer is used to send data to the output layer. Output Layer The data is made available at the output layer.
* **Proposed answer:** none proposed (answer unchanged)

### 3665  (raw 47; Deep Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** THIN_ANSWER;DOES_NOT_ADDRESS
* **Issue:** never states what ReLU computes
* **Original question:** What is ReLU function?
* **Original answer:** A node or unit which implements the activation function is referred to as a rectified linear activation unit or ReLU for short. Generally, networks that use the rectifier function for the hidden layers are referred to as rectified networks. Adoption of ReLU may easily be considered one of the few milestones in the deep learning revolution.
* **Proposed answer (rewritten_answer):** ReLU is f(x) = max(0, x): positive inputs pass through unchanged and negative inputs become 0. It is cheap to compute, does not saturate for x > 0 (which eases vanishing gradients) and produces sparse activations; its drawback is the 'dying ReLU' problem, where a unit stuck in the negative region outputs 0 and gets no gradient.

### 3666  (raw 48; Deep Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** THIN_ANSWER
* **Issue:** does not give the function or the purpose
* **Proposed difficulty:** Medium
* **Original question:** What is the use of leaky ReLU function?
* **Original answer:** The Leaky ReLU (LReLU or LReL) manages the function to allow small negative values when the input is less than zero.
* **Proposed answer (rewritten_answer):** Leaky ReLU outputs x for x > 0 and alpha*x for x <= 0, where alpha is a small constant (e.g. 0.01). Negative inputs therefore still produce a small non-zero gradient, which reduces the 'dying ReLU' problem.

### 3670  (raw 52; Deep Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** INCORRECT_ABSOLUTE
* **Issue:** 'ReLU has to be used in hidden layers' is overgeneralised
* **Proposed difficulty:** Medium
* **Original question:** Can Relu function be used in output layer?
* **Original answer:** No, Relu function has to be used in hidden layers.
* **Proposed answer (rewritten_answer):** Usually not for classification outputs (use sigmoid for binary and softmax for multi-class). ReLU, or a similar non-negative activation, can be used on the output of a regression model whose target is non-negative. ReLU is mainly used in hidden layers.

### 3672  (raw 54; Deep Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** TYPO
* **Issue:** 'internet representation' should be 'internal representation'
* **Proposed difficulty:** Medium
* **Original question:** What do you understand by Autoencoder?
* **Original answer:** Autoencoder is an artificial neural network. It can learn representation for a set of data without any supervision. The network automatically learns by copying its input to the output; typically,internet representation consists of smaller dimensions than the input vector. As a result, they can learn efficient ways of representing the data. Autoencoder consists of two parts; an encoder tries to fit the inputs to the internal representation, and a decoder converts the internal state to the outputs.
* **Proposed answer (replace):** Autoencoder is an artificial neural network. It can learn representation for a set of data without any supervision. The network automatically learns by copying its input to the output; typically, the internal representation consists of smaller dimensions than the input vector. As a result, they can learn efficient ways of representing the data. Autoencoder consists of two parts; an encoder tries to fit the inputs to the internal representation, and a decoder converts the internal state to the outputs.

### 3673  (raw 55; Deep Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** TYPO
* **Issue:** 'regulation technique' should be 'regularisation'; otherwise correct
* **Proposed difficulty:** Medium
* **Original question:** What do you mean by Dropout?
* **Original answer:** Dropout is a cheap regulation technique used for reducing overfitting in neural networks. We randomly drop out a set of nodes at each training step. As a result, we create a different model for each training case, and all of these models share weights. It's a form of model averaging.
* **Proposed answer (replace):** Dropout is a cheap regularization technique used for reducing overfitting in neural networks. We randomly drop out a set of nodes at each training step. As a result, we create a different model for each training case, and all of these models share weights. It's a form of model averaging.

### 3676  (raw 58; Deep Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE
* **Issue:** 'model capacity can approximate any given function' is misleading
* **Proposed difficulty:** Medium
* **Original question:** What is Model Capacity?
* **Original answer:** The capacity of a deep learning neural network controls the scope of the types of mapping functions that it can learn. Model capacity can approximate any given function. When there is a higher model capacity, it means that the larger amount of information can be stored in the network.
* **Proposed answer (rewritten_answer):** Capacity is the range of functions a model can represent; it grows with the number and size of layers and parameters. Too little capacity underfits; too much relative to the amount of data overfits. It is managed through architecture size, regularisation and early stopping.

### 3678  (raw 60; Deep Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** MISSING_FORMULA
* **Issue:** formula is referenced ('via the following formula') but absent
* **Proposed difficulty:** Medium
* **Original question:** Explain gradient descent?
* **Original answer:** An optimization algorithm that is used to minimize some function by repeatedly moving in the direction of steepest descent as specified by the negative of the gradient is known as gradient descent. It's an iteration algorithm, in every iteration algorithm, we compute the gradient of a cost function, concerning each parameter and update the parameter of the function via the following formula: Where, Θ - is the parameter vector, α - learning rate, J(Θ) - is a cost function In machine learning, it is used to update the parameters of our model. Parameters represent the coefficients in linear regression and weights in neural networks.
* **Proposed answer (replace):** An optimization algorithm that is used to minimize some function by repeatedly moving in the direction of steepest descent as specified by the negative of the gradient is known as gradient descent. It's an iteration algorithm, in every iteration algorithm, we compute the gradient of a cost function, concerning each parameter and update the parameter of the function via theta := theta - alpha * grad J(theta), where theta is the parameter vector, α - learning rate, J(Θ) - is a cost function In machine learning, it is used to update the parameters of our model. Parameters represent the coefficients in linear regression and weights in neural networks.

### 3681  (raw 63; Deep Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOES_NOT_ADDRESS
* **Issue:** asks for an example; none given
* **Original question:** What is matrix element-wise multiplication? Explain with an example.
* **Original answer:** Element-wise matrix multiplication is used to take two matrices of the same dimensions. It further produces another combined matrix with the elements that are a product of corresponding elements of matrix a and b.
* **Proposed answer (rewritten_answer):** Element-wise (Hadamard) multiplication multiplies corresponding entries of two matrices of the same shape. Example: [[1,2],[3,4]] * [[5,6],[7,8]] = [[5,12],[21,32]]. In NumPy this is a * b (not a @ b, which is matrix multiplication).
* **Code test:** PASS

### 3682  (raw 64; Deep Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ANSWER_BLEED
* **Issue:** answer continues into '43) Explain the different layers of CNN...'
* **Proposed difficulty:** Medium
* **Original question:** What do you understand by a convolutional neural network?
* **Original answer:** A convolutional neural network, often called CNN, is a feedforward neural network. It uses convolution in at least one of its layers. The convolutional layer contains a set of filter (kernels). This filter is sliding across the entire input image, computing the dot product between the weights of the filter and the input image. As a result of training, the network automatically learns filters that can detect specific features. 43) Explain the different layers of CNN. There are four layered concepts that we should understand in CNN (Convolutional Neural Network): Convolution This layer comprises of a set of independent filters. All these filters are initialized randomly. These filters then become our parameters which will be learned by the network subsequently. ReLU The ReLu layer is used with the convolutional layer. Pooling It reduces the spatial size of the representation to lower the number of parameters and computation in the network. This layer operates on each feature map independently. Full Collectedness Neurons in a completely connected layer have complete connections to all activations in the previous layer, as seen in regular Neural Networks. Their activations can be easily computed with a matrix multiplication followed by a bias offset.
* **Proposed answer (trim):** A convolutional neural network, often called CNN, is a feedforward neural network. It uses convolution in at least one of its layers. The convolutional layer contains a set of filter (kernels). This filter is sliding across the entire input image, computing the dot product between the weights of the filter and the input image. As a result of training, the network automatically learns filters that can detect specific features.

### 3683  (raw 65; Deep Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** MISLEADING
* **Issue:** 'RNNs use backpropagation because of their internal memory' is a wrong causal claim
* **Proposed difficulty:** Medium
* **Original question:** What is an RNN?
* **Original answer:** RNN stands for Recurrent Neural Networks. These are the artificial neural networks which are designed to recognize patterns in sequences of data such as handwriting, text, the spoken word, genomes, and numerical time series data. RNN use backpropagation algorithm for training because of their internal memory. RNN can remember important things about the input they received, which enables them to be very precise in predicting what's coming next.
* **Proposed answer (rewritten_answer):** An RNN is a neural network for sequential data (text, speech, time series). It processes one element at a time and carries a hidden state forward, so earlier inputs can influence later outputs; the same weights are reused at every time step. It is trained with backpropagation through time and suffers from vanishing/exploding gradients, which LSTM and GRU cells were designed to reduce.

### 3684  (raw 66; Deep Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ANSWER_BLEED;TYPO
* **Issue:** answer continues into '46) Explain the importance of LSTM'; 'BTT' should be BPTT
* **Proposed difficulty:** Medium
* **Original question:** What are the issues faced while training in Recurrent Networks?
* **Original answer:** Recurrent Neural Network uses backpropagation algorithm for training, but it is applied on every timestamp. It is usually known as Back-propagation Through Time (BTT). There are two significant issues with Back-propagation, such as: Vanishing Gradient When we perform Back-propagation, the gradients tend to get smaller and smaller because we keep on moving backward in the Network. As a result, the neurons in the earlier layer learn very slowly if we compare it with the neurons in the later layers.Earlier layers are more valuable because they are responsible for learning and detecting simple patterns. They are the building blocks of the network. If they provide improper or inaccurate results, then how can we expect the next layers and complete network to perform nicely and provide accurate results. The training procedure tales long, and the prediction accuracy of the model decreases. Exploding Gradient Exploding gradients are the main problem when large error gradients accumulate. They provide result in very large updates to neural network model weights during training. Gradient Descent process works best when updates are small and controlled. When the magnitudes of the gradient accumulate, an unstable network is likely to occur. It can cause poor prediction of results or even a model that reports nothing useful. 46) Explain the importance of LSTM. LSTM stands for Long short-term memory. It is an artificial RNN (Recurrent Neural Network) architecture, which is used in the field of deep learning. LSTM has feedback connections which makes it a "general purpose computer." It can process not only a single data point but also entire sequences of data. They are a special kind of RNN which are capable of learning long-term dependencies.
* **Proposed answer (trim+replace):** Recurrent Neural Network uses backpropagation algorithm for training, but it is applied on every timestamp. It is usually known as Back-propagation Through Time (BPTT). There are two significant issues with Back-propagation, such as: Vanishing Gradient When we perform Back-propagation, the gradients tend to get smaller and smaller because we keep on moving backward in the Network. As a result, the neurons in the earlier layer learn very slowly if we compare it with the neurons in the later layers.Earlier layers are more valuable because they are responsible for learning and detecting simple patterns. They are the building blocks of the network. If they provide improper or inaccurate results, then how can we expect the next layers and complete network to perform nicely and provide accurate results. The training procedure tales long, and the prediction accuracy of the model decreases. Exploding Gradient Exploding gradients are the main problem when large error gradients accumulate. They provide result in very large updates to neural network model weights during training. Gradient Descent process works best when updates are small and controlled. When the magnitudes of the gradient accumulate, an unstable network is likely to occur. It can cause poor prediction of results or even a model that reports nothing useful.

### 3695  (raw 77; Deep Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** QUESTION_TYPO
* **Issue:** 'perception' should be 'perceptron'; steps are a simplified training loop
* **Proposed difficulty:** Medium
* **Original question:** What are the steps involved in training a perception in Deep Learning?
* **Proposed question:** What are the steps involved in training a perceptron in Deep Learning?
* **Original answer:** There are five main steps that determine the learning of a perceptron: Initialize thresholds and weights Provide inputs Calculate outputs Update weights in each step Repeat steps 2 to 4
* **Proposed answer:** none proposed (answer unchanged)

### 3696  (raw 78; Deep Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR
* **Issue:** says loss compares the training dataset to the testing dataset (it compares predictions with targets)
* **Original question:** What is the use of the loss function?
* **Original answer:** The loss function is used as a measure of accuracy to see if a neural network has learned accurately from the training data or not. This is done by comparing the training dataset to the testing dataset. The loss function is a primary measure of the performance of the neural network. In Deep Learning, a good performing network will have a low loss function at all times when training.
* **Proposed answer (rewritten_answer):** The loss function measures how far the network's predictions are from the true targets for a training example or batch. Training minimises it with gradient-based optimisation (e.g. cross-entropy for classification, mean squared error for regression). Tracking loss on training and validation data shows convergence and over/under-fitting.

### 3700  (raw 82; Deep Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ANSWER_BLEED
* **Issue:** answer ends with '14. Differentiate between a single-layer perceptron and a multi-layer perceptron.'
* **Proposed difficulty:** Medium
* **Original question:** What are the steps to be followed to use the gradient descent algorithm?
* **Original answer:** There are five main steps that are used to initialize and use the gradient descent algorithm: Initialize biases and weights for the network Send input data through the network (the input layer) Calculate the difference (the error) between expected and predicted values Change values in neurons to minimize the loss function Multiple iterations to determine the best weights for efficient working 14. Differentiate between a single-layer perceptron and a multi-layer perceptron.
* **Proposed answer (trim):** There are five main steps that are used to initialize and use the gradient descent algorithm: Initialize biases and weights for the network Send input data through the network (the input layer) Calculate the difference (the error) between expected and predicted values Change values in neurons to minimize the loss function Multiple iterations to determine the best weights for efficient working

### 3703  (raw 85; Deep Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE
* **Issue:** 'used to understand parameters' is garbled
* **Original question:** What are hyperparameters in Deep Learning?
* **Original answer:** Hyperparameters are variables used to determine the structure of a neural network. They are also used to understand parameters, such as the learning rate and the number of hidden layers and more, present in the neural network.
* **Proposed answer (rewritten_answer):** Hyperparameters are settings chosen before training that control the model structure and the training process, e.g. learning rate, number of layers and units, batch size, number of epochs, dropout rate and optimiser. Unlike parameters (weights and biases), they are not learned by gradient descent.

### 3704  (raw 86; Deep Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ILL_POSED_QUESTION;MISLEADING
* **Issue:** hyperparameters are tuned, not 'trained'; the answer lists batch size/epochs/momentum/learning rate as 'four components'
* **Proposed difficulty:** Medium
* **Original question:** How can hyperparameters be trained in neural networks?
* **Proposed question:** How are hyperparameters tuned in neural networks?
* **Original answer:** Hyperparameters can be trained using four components as shown below: Batch size: This is used to denote the size of the input chunk. Batch sizes can be varied and cut into sub-batches based on the requirement. Epochs: An epoch denotes the number of times the training data is visible to the neural network so that it can train. Since the process is iterative, the number of epochs will vary based on the data. Momentum: Momentum is used to understand the next consecutive steps that occur with the current data being executed at hand. It is used to avoid oscillations when training. Learning rate: Learning rate is used as a parameter to denote the time required for the network to update the parameters and learn.
* **Proposed answer (rewritten_answer):** Hyperparameters are not learned by backpropagation; they are tuned using performance on a validation set. Common approaches: manual tuning, grid search, random search (often more efficient than grid search), Bayesian optimisation (e.g. with Optuna or Hyperopt) and early-stopping-based schemes such as Hyperband. Use a held-out validation set (or cross-validation when affordable) and keep the test set untouched.

### 3710  (raw 92; Deep Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** EDITORIAL;PROVENANCE_RISK
* **Issue:** answer ends with a promotion for a named vendor's course
* **Proposed difficulty:** Medium
* **Original question:** What is a computational graph in Deep Learning?
* **Original answer:** A computation graph is a series of operations that are performed to take in inputs and arrange them as nodes in a graph structure. It can be considered as a way of implementing mathematical calculations into a graph. This helps in parallel processing and provides high performance in terms of computational capability. If you are looking forward to becoming an expert in Deep Learning, make sure to check out Intellipaat’s AI Engineer Course.
* **Proposed answer (trim):** A computation graph is a series of operations that are performed to take in inputs and arrange them as nodes in a graph structure. It can be considered as a way of implementing mathematical calculations into a graph. This helps in parallel processing and provides high performance in terms of computational capability.

### 3712  (raw 94; Deep Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR;CORRUPTED
* **Issue:** pooling described as maintaining image size (it reduces spatial size); 'Connectedness' = fully connected layer
* **Proposed difficulty:** Medium
* **Original question:** What are the various layers present in a CNN?
* **Original answer:** There are four main layers that form a convolutional neural network: Convolution: These are layers consisting of entities called filters that are used as parameters to train the network. ReLu: It is used as the activation function and used always with the convolution layer. Pooling: Pooling is the concept of shrinking the complex data entities that form after convolution and is primarily used to maintain the size of an image after shrinkage. Connectedness: This is used to ensure that all of the layers in the neural network are fully connected and activation can be computed using the bias easily.
* **Proposed answer (rewritten_answer):** A typical CNN stacks convolutional layers (learnable filters/kernels that detect local features), a non-linearity such as ReLU, pooling layers (max or average pooling that reduce spatial size and add some translation tolerance), and finally one or more fully connected layers (often ending in softmax) that produce the output.

### 3715  (raw 97; Deep Learning; current Medium, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ILL_POSED_QUESTION;CORRUPTED
* **Issue:** 'exploding gradient descent' is not a term; answer is muddled
* **Original question:** What is exploding gradient descent in Deep Learning?
* **Proposed question:** What is the exploding gradient problem in deep learning?
* **Original answer:** Exploding gradients are an issue causing a scenario that clumps up the gradients. This creates a large number of updates of the weights in the model when training. The working of gradient descent is based on the condition that the updates are small and controlled. Controlling the updates will directly affect the efficiency of the model.
* **Proposed answer (rewritten_answer):** Exploding gradients occur when gradients grow exponentially as they are backpropagated through many layers or time steps, producing very large weight updates and unstable or diverging training (loss becomes NaN). Typical remedies: gradient clipping, careful weight initialisation, a smaller learning rate, normalisation layers, and gated architectures such as LSTM/GRU.

### 3716  (raw 98; Deep Learning; current Easy, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** CORRUPTED;THIN_ANSWER
* **Issue:** 'used to sequence a string of data' / 'general-purpose computational entity' is garbled
* **Proposed difficulty:** Medium
* **Original question:** What is the use of LSTM?
* **Original answer:** LSTM stands for long short-term memory. It is a type of RNN that is used to sequence a string of data. It consists of feedback chains that give it the ability to perform like a general-purpose computational entity.
* **Proposed answer (rewritten_answer):** LSTM (Long Short-Term Memory) is a recurrent architecture with a memory cell and input, forget and output gates that control what to store, discard and expose. It can learn long-range dependencies and mitigates the vanishing-gradient problem of plain RNNs. Used for sequence tasks such as language modelling, speech recognition and time-series forecasting.

### 3717  (raw 99; Deep Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE;THIN_ANSWER
* **Issue:** 'feature removal and variation' is unclear; omits anomaly detection
* **Proposed difficulty:** Medium
* **Original question:** Where are autoencoders used?
* **Original answer:** Autoencoders have a wide variety of usage in the real world. The following are some of the popular ones: Adding color to black–white images Removing noise from images Dimensionality reduction Feature removal and variation
* **Proposed answer (rewritten_answer):** Typical uses: denoising (denoising autoencoders), dimensionality reduction / compression, anomaly detection (unusually high reconstruction error), unsupervised feature learning or pre-training, and generative modelling with variational autoencoders.

### 3728  (raw 110; Deep Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR
* **Issue:** says padding is added 'around the output matrix'; it is added around the input
* **Proposed difficulty:** Medium
* **Original question:** What is the meaning of valid padding and same padding in CNN?
* **Original answer:** Valid padding: It is used when there is no requirement for padding. The output matrix will have the dimensions (n – f + 1) X (n – f + 1) after convolution. Same padding: Here, padding elements are added all around the output matrix. It will have the same dimensions as the input matrix.
* **Proposed answer (rewritten_answer):** Valid padding: no padding is added, so with stride 1 the output has size n - f + 1 in each dimension (it shrinks). Same padding: zeros are added around the input so that, with stride 1, the output has the same height and width as the input (padding p = (f - 1) / 2 for an odd filter size f).

### 3729  (raw 111; Deep Learning; current Easy, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOES_NOT_ADDRESS
* **Issue:** asks for applications; answer lists model names
* **Proposed difficulty:** Medium
* **Original question:** What are some of the applications of transfer learning in Deep Learning?
* **Proposed question:** What is transfer learning and when is it used?
* **Original answer:** Transfer learning is a scenario where a large model is trained on a dataset with a large amount of data and this model is used on simpler datasets, thereby resulting in extremely efficient and accurate neural networks. The popular examples of transfer learning are in the case of: BERT ResNet GPT-2 VGG-16
* **Proposed answer (rewritten_answer):** Transfer learning reuses a model pre-trained on a large dataset (e.g. ResNet on ImageNet, BERT on large text corpora) for a related task that has less data, either as a fixed feature extractor or by fine-tuning some or all layers. It cuts training time and data requirements. Typical uses: image classification and object detection with small datasets, and NLP tasks such as text classification and NER. It works best when the source and target domains are similar.

### 3730  (raw 112; Deep Learning; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** CORRUPTED;THIN_ANSWER
* **Issue:** garbled phrasing; does not state the parallelism / long-range-dependency advantages clearly
* **Proposed difficulty:** Medium
* **Original question:** How is the transformer architecture better than RNNs in Deep Learning?
* **Original answer:** With the use of sequential processing, programmers were up against: The usage of high processing power The difficulty of parallel execution This caused the rise of the transformer architecture. Here, there is a mechanism called attention mechanism, which is used to map all of the dependencies between sentences, thereby making huge progress in the case of NLP models.
* **Proposed answer (rewritten_answer):** RNNs process tokens one after another, which prevents parallelisation across time steps and makes long-range dependencies hard to learn (vanishing gradients). Transformers use self-attention: every token can attend directly to every other token, all positions are computed in parallel (much faster training on GPUs) and long-range dependencies are easier to capture. Costs: attention is O(n^2) in sequence length and word-order information must be added via positional encodings.

### 3736  (raw 118; Deep Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ANSWER_BLEED;COSMETIC_PREFIX
* **Issue:** answer starts mid-sentence ('otherwise...') and continues into '2. Describe two ways of dealing with the vanishing gradient problem...'
* **Proposed difficulty:** Medium
* **Original question:** Why is it necessary to introduce non-linearities in a neural network?
* **Original answer:** Solution: otherwise, we would have a composition of linear functions, which is also a linear function, giving a linear model. A linear model has a much smaller number of parameters, and is therefore limited in the complexity it can model. 2. Describe two ways of dealing with the vanishing gradient problem in a neural network. Solution: Using ReLU activation instead of sigmoid. Using Xavier initialization.
* **Proposed answer (rewritten_answer):** Without non-linear activation functions, a stack of layers is just a composition of linear functions, which is itself a linear function, so the whole network would behave like a single linear model with limited expressive power. Non-linearities let the network learn complex, non-linear decision boundaries.

### 3737  (raw 119; Deep Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ANSWER_BLEED;COSMETIC_PREFIX;IMPRECISE
* **Issue:** bleed into '4. Describe two ways to visualize features of a CNN...'; 'translation invariant' is loosely used (convolution is translation-equivariant; pooling adds approximate invariance)
* **Proposed difficulty:** Medium
* **Original question:** What are some advantages in using a CNN (convolutional neural network) rather than a DNN (dense neural network) in an image classification task?
* **Original answer:** Solution: while both models can capture the relationship between close pixels, CNNs have the following properties: It is translation invariant — the exact location of the pixel is irrelevant for the filter. It is less likely to overfit — the typical number of parameters in a CNN is much smaller than that of a DNN. Gives us a better understanding of the model — we can look at the filters’ weights and visualize what the network “learned”. Hierarchical nature — learns patterns in by describing complex patterns using simpler ones. 4. Describe two ways to visualize features of a CNN in an image classification task. Solution: Input occlusion — cover a part of the input image and see which part affect the classification the most. For instance, given a trained image classification model, give the images below as input. If, for instance, we see that the 3rd image is classified with 98% probability as a dog, while the 2nd image only with 65% accuracy, it means that the part covered in the 2nd image is more important. Activation Maximization — the idea is to create an artificial input image that maximize the target response (gradient ascent).
* **Proposed answer (trim):** While both models can capture the relationship between close pixels, CNNs have the following properties: It is translation invariant — the exact location of the pixel is irrelevant for the filter. It is less likely to overfit — the typical number of parameters in a CNN is much smaller than that of a DNN. Gives us a better understanding of the model — we can look at the filters’ weights and visualize what the network “learned”. Hierarchical nature — learns patterns in by describing complex patterns using simpler ones.

### 3739  (raw 121; Deep Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ANSWER_BLEED;COSMETIC_PREFIX
* **Issue:** answer continues into questions 7 and 8
* **Proposed difficulty:** Medium
* **Original question:** Suppose you have a NN with 3 layers and ReLU activations. What will happen if we initialize all the weights with the same value? what if we only had 1 layer (i.e linear/logistic regression?)
* **Original answer:** Solution: If we initialize all the weights to be the same we would not be able to break the symmetry; i.e, all gradients will be updated the same and the network will not be able to learn. In the 1-layers scenario, however, the cost function is convex (linear/sigmoid) and thus the weights will always converge to the optimal point, regardless of the initial value (convergence may be slower). 7. Explain the idea behind the Adam optimizer. Solution: Adam, or adaptive momentum, combines two ideas to improve convergence: per-parameter updates which give faster convergence, and momentum which helps to avoid getting stuck in saddle point. 8. Compare batch, mini-batch and stochastic gradient descent. Solution: batch refers to estimating the data by taking the entire data, mini-batch by sampling a few datapoints, and SGD refers to update the gradient one datapoint at each epoch. The tradeoff here is between how precise the calculation of the gradient is versus what size of batch we can keep in memory. Moreover, taking mini-batch rather than the entire batch has a regularizing effect by adding random noise at each epoch.
* **Proposed answer (trim):** If we initialize all the weights to be the same we would not be able to break the symmetry; i.e, all gradients will be updated the same and the network will not be able to learn. In the 1-layers scenario, however, the cost function is convex (linear/sigmoid) and thus the weights will always converge to the optimal point, regardless of the initial value (convergence may be slower).

### 3748  (raw 130; Deep Learning; current Medium, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ANSWER_BLEED;COSMETIC_PREFIX
* **Issue:** answer continues into '18. Describe some hyperparameters for transfer learning.'
* **Original question:** When using mini batch gradient descent, why is it important to shuffle the data?
* **Original answer:** Solution: otherwise, suppose we train a NN classifier and have two classes — A and B, and that all samples of one class come before the other class. Not shuffling the data will make the weights converge to a wrong value. 18. Describe some hyperparameters for transfer learning. Solution: How many layers to keep, how many layers to add, how many to freeze.
* **Proposed answer (trim):** Otherwise, suppose we train a NN classifier and have two classes — A and B, and that all samples of one class come before the other class. Not shuffling the data will make the weights converge to a wrong value.

### 3749  (raw 131; Deep Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ANSWER_BLEED;COSMETIC_PREFIX;THIN_ANSWER
* **Issue:** answer continues into questions 20-21; trimmed answer omits inference-time scaling
* **Proposed difficulty:** Medium
* **Original question:** Is dropout used on the test set?
* **Original answer:** Solution: No! only in the train set. Dropout is a regularization technique that is applied in the training process. 20. Explain why dropout in a neural network acts as a regularizer. Solution: There are several (related) explanations to why dropout works. It can be seen as a form of model averaging — at each step we “turn off” a part of the model and average the models we get. It also adds noise, which naturally has a regularizing effect. It also leads to more sparsity of the weights and essentially prevents co-adaptation of neurons in the network. 21. Give examples in which a many-to-one RNN architecture is appropriate. Solution: A few examples are: sentiment analysis, gender recognition from speech, .
* **Proposed answer (trim):** No! only in the train set. Dropout is a regularization technique that is applied in the training process.

### 3750  (raw 132; Deep Learning; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ANSWER_BLEED;COSMETIC_PREFIX
* **Issue:** answer continues into '23. True/false...'
* **Original question:** When can’t we use BiLSTM? Explain what assumption has to be made.
* **Original answer:** Solution: in any bi-directional model, we assume that we have access to the next elements of the sequence in a given “time”. This is the case for text data (i.e sentiment analysis, translation etc.), but not the case for time-series data. 23. True/false: adding L2 regularization to a RNN can help with the vanishing gradient problem. Solution: false! Adding L2 regularization will shrink the weights towards zero, which can actually make the vanishing gradients worse in some cases.
* **Proposed answer (trim):** In any bi-directional model, we assume that we have access to the next elements of the sequence in a given “time”. This is the case for text data (i.e sentiment analysis, translation etc.), but not the case for time-series data.

### 3751  (raw 133; Deep Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ANSWER_BLEED;COSMETIC_PREFIX
* **Issue:** answer continues into '25. Describe how L2 regularization...'
* **Proposed difficulty:** Medium
* **Original question:** Suppose the training error/cost is high and that the validation cost/error is almost equal to it. What does it mean? What should be done?
* **Original answer:** Solution: this indicates underfitting. One can add more parameters, increase the complexity of the model, or lower the regularization. 25. Describe how L2 regularization can be explained as a sort of a weight decay. Solution: Suppose our cost function is C(w), and that we add a penalization c|w|2 . When using gradient descent, the iterations will look like w = w -grad(C)(w) — 2cw = (1–2c)w — grad(C)(w) In this equation, the weight is multiplied by a factor < 1.
* **Proposed answer (trim):** This indicates underfitting. One can add more parameters, increase the complexity of the model, or lower the regularization.

### 3758  (raw 140; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE;FACTUAL_ERROR
* **Issue:** k-means needs the number of clusters k, not 'a threshold'; it assigns points to the nearest centroid (mean of the cluster), not 'the mean of the distance between points'
* **Proposed difficulty:** Medium
* **Original question:** How is KNN different from k-means clustering?
* **Original answer:** K-Nearest Neighbors is a supervised classification algorithm, while k-means clustering is an unsupervised clustering algorithm. KNN needs labeled data to classify an unlabeled point, while k-means requires only a set of unlabeled points and a threshold: it learns how to cluster them into groups by computing the mean of the distance between different points. The critical difference is that KNN needs labeled points and is thus supervised learning, while k-means doesn't — and is thus unsupervised learning.
* **Proposed answer (rewritten_answer):** KNN is supervised: it needs labelled training data and classifies (or regresses) a new point from the labels of its k nearest neighbours. K-means is unsupervised: it needs only unlabelled data and a chosen number of clusters k; it iteratively assigns points to the nearest centroid and recomputes each centroid as the mean of its assigned points. The 'k' means different things: number of neighbours in KNN, number of clusters in k-means.

### 3759  (raw 141; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE
* **Issue:** features are assumed conditionally independent given the class, not simply 'no interdependency'
* **Proposed difficulty:** Medium
* **Original question:** What is Naive Bayes?
* **Original answer:** It is a supervised learning algorithm based on bayes theorem. It classifies different instances into predefined classes, assuming there is no interdependency of features.
* **Proposed answer (rewritten_answer):** Naive Bayes is a probabilistic supervised classifier based on Bayes' theorem. It assumes features are conditionally independent given the class, so P(class | x) is proportional to P(class) * product of P(x_i | class). The assumption is rarely true, yet the model works well for text classification and as a fast baseline.

### 3765  (raw 147; Machine Learning; current Easy, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** QUESTION_FORMAT;FACTUAL_ERROR;MISSING_FORMULA
* **Issue:** question is a fragment; answer says the split maximises 'entropy gain' (it is information gain) and gives a malformed entropy formula
* **Proposed difficulty:** Medium
* **Original question:** Finding the variable/feature for best split?
* **Proposed question:** How does a decision tree choose the best feature to split on?
* **Original answer:** Gini Index is a measure of variance across all classes of the data and measures the impurity of the data. Entropy is a measure of randomness — more random data means higher entropy (E = -p*log(p); p - probability). Information Gain is the decrease in entropy; the difference between entropy before the split and average entropy after split is used to decide when to split, and the variable which provides maximum entropy gain is chosen.
* **Proposed answer (rewritten_answer):** At each node the tree evaluates candidate splits and picks the one that most reduces impurity. Gini impurity = 1 - sum(p_i^2). Entropy = -sum(p_i * log2(p_i)). Information gain = entropy(parent) - weighted average entropy(children). The split with the highest information gain (or largest Gini decrease) is chosen.

### 3769  (raw 151; Machine Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** QUESTION_TYPO;ANSWER_BLEED;MISSING_FORMULA
* **Issue:** 'Confusion Metrics' should be Matrix; answer drifts into regression metrics (RMSE, MAE, R^2) unrelated to confusion matrices; formulas absent
* **Proposed difficulty:** Medium
* **Original question:** What is Confusion Metrics
* **Proposed question:** What is a confusion matrix and which classification metrics are derived from it?
* **Original answer:** Confusion Matrix is an NxN matrix where N is the no. of classes, that summarizes how successful a classification model's predictions are. Accuracy is the fraction of predictions our model got right. Recall or Sensitivity or True Positive Rate is the number of items correctly identified as positive out of total true positives. Precision is the number of items correctly identified as positive out of total items identified as positive. True Negative Rate or Specificity is the number of items correctly identified as negative out of total true negatives. Type 1 Error or False Positive Rate is the number of items wrongly identified as positive out of total true negatives. Type 2 Error or False Negative Rate is the number of items wrongly identified as negative out of total true positives. RMSE represents the sample standard deviation of the differences between predicted values and observed values. MAE is the average of the absolute difference between the predicted values and observed value. R Squared & Adjusted R Squared (goodness of fit measure) explain how well your selected independent variable(s) explain the variability in your dependent variable(s).
* **Proposed answer (rewritten_answer):** A confusion matrix is an N x N table of actual vs predicted classes; for binary classification it holds TP, FP, TN and FN. Derived metrics: accuracy = (TP+TN)/(TP+TN+FP+FN); precision = TP/(TP+FP); recall (sensitivity, TPR) = TP/(TP+FN); specificity (TNR) = TN/(TN+FP); false positive rate = FP/(FP+TN) (Type I error rate); false negative rate = FN/(FN+TP) (Type II error rate); F1 = 2*precision*recall/(precision+recall).

### 3775  (raw 157; Machine Learning; current Medium, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOES_NOT_ADDRESS;QUESTION_FORMAT
* **Issue:** question asks for the algorithm; answer lists strengths and weaknesses
* **Original question:** K-Means Clustering Algorithm?
* **Proposed question:** What are the strengths and weaknesses of k-means clustering?
* **Original answer:** K-Means is fast with a linear complexity O(n), as all we're really doing is computing the distances between points and group centers. However, you have to select how many groups/classes there are. K-means also starts with a random choice of cluster centers and therefore it may yield different clustering results on different runs, so results may not be repeatable and lack consistency.
* **Proposed answer (rewritten_answer):** Strengths: simple and fast, roughly linear in the number of points (O(n * k * iterations * d)), scales to large datasets. Weaknesses: k must be chosen in advance; results depend on random initialisation (use k-means++ and multiple restarts); assumes roughly spherical, similar-sized clusters; sensitive to outliers and feature scale.

### 3776  (raw 158; Machine Learning; current Easy, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** QUESTION_FORMAT;IMPRECISE
* **Issue:** blog-style title; elbow method is 'look for the bend', not 'as small as possible'
* **Proposed difficulty:** Medium
* **Original question:** Determining The Optimal Number Of Clusters: 3 Must Know Methods?
* **Proposed question:** How do you choose the number of clusters k in k-means?
* **Original answer:** Elbow method (within-cluster sum of square vs number of clusters): we want it to be as small as possible. Average silhouette method (average silhouette of observations vs number of clusters): high average silhouette width indicates a good clustering. Gap statistic method: compares the total intracluster variation for different values of k with their expected values under null reference distribution of the data.
* **Proposed answer (rewritten_answer):** Elbow method: plot within-cluster sum of squares against k and pick the point where the improvement flattens (the 'elbow'). Silhouette method: choose the k with the highest average silhouette width. Gap statistic: compare the within-cluster dispersion with its expectation under a null reference distribution and pick the k with the largest gap. Domain knowledge and cluster stability also matter.

### 3778  (raw 160; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** QUESTION_FORMAT;THIN_ANSWER
* **Issue:** fragment question; the two-way taxonomy is one source's framing
* **Proposed difficulty:** Medium
* **Original question:** Dimensionality Reduction Technique?
* **Proposed question:** What are common dimensionality reduction techniques?
* **Original answer:** Mainly there are two types of dimension reduction technique: Matrix Factorization (PCA) and Neighbour Graphs (UMAP, T-SNE).
* **Proposed answer (rewritten_answer):** Linear: PCA (maximises retained variance), LDA (supervised, maximises class separation), truncated SVD. Non-linear: t-SNE and UMAP (mainly for visualisation), kernel PCA, autoencoders. Alternative: feature selection (filter, wrapper, embedded methods).

### 3782  (raw 164; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** MISSING_FORMULA;QUESTION_FORMAT
* **Issue:** no formula given
* **Proposed difficulty:** Medium
* **Original question:** Cross Entropy or Log Loss?
* **Proposed question:** What is cross-entropy (log loss)?
* **Original answer:** Cross-entropy is commonly used to quantify the difference between two probability distributions. Cross-entropy loss measures how close the predicted distribution is to the true distribution.
* **Proposed answer (rewritten_answer):** Cross-entropy measures the difference between the true distribution and the predicted distribution. For binary classification: L = -(1/N) * sum[ y*log(p) + (1-y)*log(1-p) ]; for multi-class: L = -sum over classes of y_c * log(p_c). It penalises confident wrong predictions heavily and is the standard loss for classification with probabilistic outputs.

### 3783  (raw 165; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE
* **Issue:** reason given ('confusing to compare') is weak; the real reason is that log p <= 0 and minimising -log p equals maximising likelihood
* **Proposed difficulty:** Medium
* **Original question:** Why the Negative Sign in log loss?
* **Proposed question:** Why does log loss have a negative sign?
* **Original answer:** Log Loss uses negative log to provide an easy metric for comparison. It takes this approach because the positive log of numbers < 1 returns negative values, which is confusing to work with when comparing the performance of two models.
* **Proposed answer (rewritten_answer):** Probabilities lie in (0, 1], so log p is zero or negative. The minus sign makes the loss non-negative (0 for perfect predictions, growing as predictions worsen) and turns maximum-likelihood estimation into loss minimisation, which is what gradient-based optimisers do.

### 3786  (raw 168; Machine Learning; current Easy, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE;INCORRECT_ABSOLUTE
* **Issue:** 'no matter what the shape' needs finite variance; 'over 30' is a rule of thumb
* **Proposed difficulty:** Medium
* **Original question:** Central Limit Theorem in brief.
* **Original answer:** The Central Limit Theorem states that the sampling distribution of the sample means approaches a normal distribution as the sample size gets larger — no matter what the shape of the population distribution. This fact holds especially true for sample sizes over 30.
* **Proposed answer (rewritten_answer):** The Central Limit Theorem says that, for independent samples from a population with finite mean and variance, the sampling distribution of the sample mean approaches a normal distribution as the sample size grows, whatever the population shape. A common rule of thumb is n >= 30, but heavily skewed populations may need more.

### 3787  (raw 169; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE
* **Issue:** definition is vague and lacks the correct interpretation
* **Proposed difficulty:** Medium
* **Original question:** What is Confidence Intervals?
* **Proposed question:** What is a confidence interval and how should it be interpreted?
* **Original answer:** A confidence interval is how much uncertainty there is with any particular statistic. Confidence intervals are often used with a margin of error. It tells you how confident you can be that the results from a poll or survey reflect what you would expect to find if it were possible to survey the entire population.
* **Proposed answer (rewritten_answer):** A confidence interval is a range of plausible values for a population parameter, computed from sample data (estimate +/- margin of error). A 95% interval means that if the procedure were repeated on many samples, about 95% of the resulting intervals would contain the true parameter; it does not mean there is a 95% probability that this specific interval contains it.

### 3788  (raw 170; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE;CORRUPTED
* **Issue:** step list is garbled ('state your null hypothesis'; 'support the null')
* **Proposed difficulty:** Medium
* **Original question:** What is Hypothesis Testing?
* **Original answer:** Hypothesis testing in statistics is a way for you to test the results of a survey or experiment to see if you have meaningful results. Steps: Figure out your null hypothesis, state your null hypothesis, choose what kind of test you need to perform, either support or reject the null hypothesis.
* **Proposed answer (rewritten_answer):** Hypothesis testing uses sample data to decide whether there is enough evidence against a default claim. Steps: state the null (H0) and alternative (H1) hypotheses; choose the significance level alpha and a suitable test; compute the test statistic and p-value; reject H0 if p < alpha, otherwise fail to reject H0 (which is not proof that H0 is true).

### 3791  (raw 173; Machine Learning; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR;QUESTION_FORMAT
* **Issue:** Pearson's coefficient tests a linear (not monotonic) relationship; Spearman's is the monotonic one
* **Proposed difficulty:** Medium
* **Original question:** What are different Statistical Hypothesis Tests.
* **Original answer:** Normality Tests — Shapiro-Wilk Test: Tests whether a data sample has a Gaussian distribution. Correlation Tests — Pearson's Correlation Coefficient: Tests whether two samples have a monotonic relationship. Spearman's Rank Correlation: Tests whether two samples have a monotonic relationship. Chi-Squared Test: Tests whether two categorical variables are related or independent. Parametric Statistical Hypothesis Tests — Student's t-test: Tests whether the means of two independent samples are significantly different. Paired Student's t-test: Tests whether the means of two paired samples are significantly different. ANOVA: Tests whether the means of two or more independent samples are significantly different. Repeated Measures ANOVA Test: Tests whether the means of two or more paired samples are significantly different.
* **Proposed answer (replace):** Normality Tests — Shapiro-Wilk Test: Tests whether a data sample has a Gaussian distribution. Correlation Tests — Pearson's Correlation Coefficient: Tests whether two samples have a linear relationship. Spearman's Rank Correlation: Tests whether two samples have a monotonic relationship. Chi-Squared Test: Tests whether two categorical variables are related or independent. Parametric Statistical Hypothesis Tests — Student's t-test: Tests whether the means of two independent samples are significantly different. Paired Student's t-test: Tests whether the means of two paired samples are significantly different. ANOVA: Tests whether the means of two or more independent samples are significantly different. Repeated Measures ANOVA Test: Tests whether the means of two or more paired samples are significantly different.

### 3795  (raw 177; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR
* **Issue:** AUC near 0 means predictions are systematically inverted, not 'poor'; a model with no skill is about 0.5
* **Proposed difficulty:** Medium
* **Original question:** How to interpret the AU ROC score?
* **Original answer:** An excellent model has AUC near to 1 which means it has good measure of separability. A poor model has AUC near to 0. When AUC score is 0.5, it means model has no class separation capacity whatsoever.
* **Proposed answer (rewritten_answer):** AUC is the probability that the model ranks a random positive example above a random negative one. AUC = 1 is perfect separation; 0.5 is no better than random guessing; AUC well below 0.5 means the ranking is systematically inverted (flipping the predictions would help). Rough guide: 0.7-0.8 acceptable, 0.8-0.9 good, above 0.9 excellent, always in context of the problem.

### 3800  (raw 182; Machine Learning; current Medium, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE
* **Issue:** parameter names min_sample_split and max_sample do not match scikit-learn (min_samples_split, max_samples)
* **Original question:** What are the main parameters of the random forest model?
* **Original answer:** max_depth: Longest path between root node and the leaf. min_sample_split: The minimum number of observations needed to split a given node. max_leaf_nodes: Conditions the splitting of the tree and hence, limits the growth of the trees. min_samples_leaf: Minimum number of samples in the leaf node. n_estimators: Number of trees. max_sample: Fraction of original dataset given to any individual tree in the given model. max_features: Limits the maximum number of features provided to trees in random forest model.
* **Proposed answer (replace+replace):** Max_depth: Longest path between root node and the leaf. min_samples_split: The minimum number of observations needed to split a given node. max_leaf_nodes: Conditions the splitting of the tree and hence, limits the growth of the trees. min_samples_leaf: Minimum number of samples in the leaf node. n_estimators: Number of trees. max_samples: Fraction of original dataset given to any individual tree in the given model. max_features: Limits the maximum number of features provided to trees in random forest model.

### 3802  (raw 184; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR
* **Issue:** 'square of the number of features' is wrong: sqrt(n_features) is the usual default for max_features, not the number of trees
* **Proposed difficulty:** Medium
* **Original question:** How do we know how many trees we need in random forest?
* **Original answer:** There is no fixed thumb rule to decide the number of trees. It is fine tuned with the data, typically starting off by taking the square of the number of features (n) present in the data followed by tuning until we get the optimal results.
* **Proposed answer (rewritten_answer):** There is no fixed rule. More trees reduce variance and never overfit by themselves, but with diminishing returns and growing cost. Start with a few hundred trees, then plot out-of-bag (OOB) or validation error against n_estimators and stop when it plateaus. (The common sqrt(n_features) rule applies to max_features, the number of features tried per split.)

### 3814  (raw 196; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** THIN_ANSWER
* **Issue:** one-line answer with a typo ('accessed')
* **Proposed difficulty:** Medium
* **Original question:** How will you assess the statistical significance of an insight?
* **Original answer:** Statistical importance of an insight can be accessed using Hypothesis Testing.
* **Proposed answer (rewritten_answer):** Frame the insight as a hypothesis, choose an appropriate test and significance level, compute the test statistic and p-value, and report the effect size with a confidence interval rather than the p-value alone. Check test assumptions, correct for multiple comparisons when testing many hypotheses, and confirm practical significance.

### 3815  (raw 197; Machine Learning; current Easy, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** MISSING_FORMULA;CORRUPTED
* **Issue:** verbal description of the formula is garbled and no formula is given
* **Proposed difficulty:** Medium
* **Original question:** What is Bayes' Theorem? How is it useful in a machine learning context?
* **Original answer:** Bayes' Theorem gives you the posterior probability of an event given what is known as prior knowledge. It is expressed as the true positive rate of a condition sample divided by the sum of the false positive rate of the population and the true positive rate of a condition. Bayes' Theorem is the basis behind a branch of machine learning that most notably includes the Naive Bayes classifier.
* **Proposed answer (rewritten_answer):** Bayes' theorem: P(A|B) = P(B|A) * P(A) / P(B), where P(A) is the prior, P(B|A) the likelihood and P(A|B) the posterior. In machine learning it underlies Naive Bayes classifiers, Bayesian inference/parameter estimation and MAP estimation.

### 3818  (raw 200; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR
* **Issue:** claims deep learning 'represents an unsupervised learning algorithm' - false; also a likely duplicate of a DL-block definition
* **Proposed difficulty:** Medium
* **Original question:** What is deep learning, and how does it contrast with other machine learning algorithms?
* **Original answer:** Deep learning is a subset of machine learning that is concerned with neural networks: how to use backpropagation and certain principles from neuroscience to more accurately model large sets of unlabelled or semi-structured data. In that sense, deep learning represents an unsupervised learning algorithm that learns representations of data through the use of neural nets.
* **Proposed answer (rewritten_answer):** Deep learning is a subfield of machine learning that uses neural networks with many layers to learn hierarchical representations directly from raw data (images, text, audio). Unlike classical ML, which usually relies on hand-engineered features, deep models learn features automatically, but they typically need more data and compute and are harder to interpret. It can be supervised, unsupervised or self-supervised.

### 3819  (raw 201; Machine Learning; current Easy, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE;INCORRECT_ABSOLUTE
* **Issue:** 'generative learns categories' is vague; 'discriminative generally outperform' is an overgeneralisation
* **Proposed difficulty:** Medium
* **Original question:** What's the difference between a generative and discriminative model?
* **Original answer:** A generative model will learn categories of data while a discriminative model will simply learn the distinction between different categories of data. Discriminative models will generally outperform generative models on classification tasks.
* **Proposed answer (rewritten_answer):** A generative model learns the joint distribution P(x, y) (typically P(x|y) and P(y)), so it can classify through Bayes' rule and also generate new samples; examples: Naive Bayes, Gaussian mixture models, HMMs. A discriminative model learns P(y|x) or the decision boundary directly; examples: logistic regression, SVM, neural classifiers. Discriminative models often reach lower error with plenty of data; generative models can do better with little data or when modelling missing data.

### 3822  (raw 204; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ILL_POSED_QUESTION;IMPRECISE
* **Issue:** 'accuracy vs performance' is not a meaningful contrast; the fraud example is garbled
* **Proposed difficulty:** Medium
* **Original question:** Which is more important to you — model accuracy, or model performance?
* **Proposed question:** Is accuracy always a good metric for evaluating a classifier? When is it misleading?
* **Original answer:** Model accuracy is only a subset of model performance, and at that, a sometimes misleading one. For example, if you wanted to detect fraud in a massive dataset, a more accurate model would most likely predict no fraud at all if only a vast minority of cases were fraud — which would be useless for a predictive model.
* **Proposed answer (rewritten_answer):** No. On imbalanced data accuracy can be high while the model is useless: if only 1% of transactions are fraud, predicting 'no fraud' for everything gives 99% accuracy but zero recall. Use precision, recall, F1, PR-AUC or ROC-AUC chosen according to the cost of false positives versus false negatives.

### 3823  (raw 205; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** MISSING_FORMULA;FACTUAL_ERROR
* **Issue:** F1 is the harmonic, not a 'weighted', average; no formula
* **Proposed difficulty:** Medium
* **Original question:** What's the F1 score? How would you use it?
* **Original answer:** The F1 score is a measure of a model's performance. It is a weighted average of the precision and recall of a model, with results tending to 1 being the best, and those tending to 0 being the worst. You would use it in classification tests where true negatives don't matter much.
* **Proposed answer (rewritten_answer):** F1 = 2 * precision * recall / (precision + recall), the harmonic mean of precision and recall (range 0 to 1). It is useful for classification with imbalanced classes where both false positives and false negatives matter and true negatives are not informative. F-beta weights recall more or less than precision.

### 3824  (raw 206; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** THIN_ANSWER
* **Issue:** three generic bullets; omits class weights, suitable metrics and SMOTE
* **Proposed difficulty:** Medium
* **Original question:** How would you handle an imbalanced dataset?
* **Original answer:** 1. Collect more data to even the imbalances in the dataset. 2. Resample the dataset to correct for imbalances. 3. Try a different algorithm altogether on your dataset.
* **Proposed answer (rewritten_answer):** Options: (1) use suitable metrics (precision, recall, F1, PR-AUC) instead of accuracy; (2) resample - oversample the minority class (e.g. SMOTE) or undersample the majority class; (3) use class weights or cost-sensitive learning; (4) tune the decision threshold; (5) try algorithms/ensembles that handle imbalance (e.g. balanced random forest); (6) collect more minority-class data if possible. Always resample only the training folds.

### 3826  (raw 208; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOES_NOT_ADDRESS
* **Issue:** asks for an example; answer defines ensembles
* **Proposed difficulty:** Medium
* **Original question:** Name an example where ensemble techniques might be useful.
* **Proposed question:** What are ensemble methods and when are they useful?
* **Original answer:** Ensemble techniques use a combination of learning algorithms to optimize better predictive performance. They typically reduce overfitting and make the model more robust. Methods include bagging, boosting, and a bucket of models approach.
* **Proposed answer (rewritten_answer):** Ensemble methods combine several models to get better predictions than any one alone. Bagging (e.g. random forest) reduces variance, boosting (e.g. gradient boosting) reduces bias, and stacking combines different model types through a meta-learner. They are useful when single models overfit or are unstable, and in tabular-data competitions; the cost is extra compute and reduced interpretability.

### 3828  (raw 210; Machine Learning; current Medium, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** CORRUPTED;IMPRECISE
* **Issue:** garbled first sentence ('can enable in higher-dimension spaces'), typos ('thanthe', 'products.Using'), and 'calculating the coordinates of higher dimensions' is inaccurate
* **Original question:** What's the 'kernel trick' and how is it useful?
* **Original answer:** The Kernel trick involves kernel functions that can enable in higher-dimension spaces without explicitly calculating the coordinates of points within that dimension: instead, kernel functions compute the inner products between the images of all pairs of data in a feature space. This allows them the very useful attribute of calculating the coordinates of higher dimensions while being computationally cheaper thanthe explicit calculation of said coordinates. Many algorithms can be expressed in terms of inner products.Using the kernel trick enables us effectively run algorithms in a high-dimensional space with lower-dimensional data.
* **Proposed answer (rewritten_answer):** The kernel trick lets an algorithm that depends only on inner products (SVM, kernel PCA, kernel ridge regression) work as if the data were mapped to a high-dimensional feature space, without computing that mapping. A kernel function k(x, y) returns the inner product of the mapped points directly (e.g. RBF or polynomial kernel), which is much cheaper than constructing the coordinates and makes non-linear decision boundaries possible.

### 3829  (raw 211; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** THIN_ANSWER;MISSING_FORMULA
* **Issue:** asks to name and define; answer only names two measures
* **Proposed difficulty:** Medium
* **Original question:** Name and define techniques used to find similarities in the recommendation system.
* **Original answer:** Pearson correlation and Cosine correlation are techniques used to find similarities in recommendation systems.
* **Proposed answer (rewritten_answer):** Cosine similarity = (A . B) / (||A|| * ||B||), the angle between two rating/feature vectors. Pearson correlation is cosine similarity after mean-centring each vector, which corrects for users who rate systematically high or low. Others: Jaccard similarity (for binary/set data) and Euclidean distance.

### 3833  (raw 215; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE;MISSING_RATIONALE
* **Issue:** reason (data leakage) not stated; 'closely packed' caveat is unsupported
* **Proposed difficulty:** Medium
* **Original question:** Keeping train and test split criteria in mind, is it good to perform scaling before the split or after the split?
* **Original answer:** Scaling should be done post-train and test split ideally. If the data is closely packed, then scaling post or pre-split should not make much difference.
* **Proposed answer (rewritten_answer):** Scale after splitting. Fit the scaler (mean/standard deviation or min/max) on the training set only and apply it to the validation and test sets; fitting on all data leaks test-set statistics into training and gives optimistic estimates. In cross-validation, put the scaler inside a pipeline so it is refit within each fold.

### 3836  (raw 218; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;FACTUAL_ERROR
* **Issue:** says LDA is unsupervised (it is supervised)
* **Proposed difficulty:** Medium
* **Original question:** How is PCA different from LDA?
* **Original answer:** Ans. PCA is unsupervised. LDA is unsupervised. PCA takes into consideration the variance. LDA takes into account the distribution of classes.
* **Proposed answer (rewritten_answer):** PCA is unsupervised: it finds orthogonal directions of maximum variance and ignores class labels. LDA is supervised: it uses class labels to find directions that maximise between-class separation relative to within-class scatter. PCA is used for general dimensionality reduction/compression; LDA for class-separating projections and as a classifier. LDA yields at most (number of classes - 1) components.

### 3837  (raw 219; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;THIN_ANSWER
* **Issue:** omits Euclidean (the default) and mixes in rarely used measures
* **Original question:** What distance metrics can be used in KNN?
* **Original answer:** Ans. Following distance metrics can be used in KNN. - Manhattan - Minkowski - Tanimoto - Jaccard - Mahalanobis
* **Proposed answer (rewritten_answer):** Common distance metrics for KNN: Euclidean (default; continuous features), Manhattan, Minkowski (generalises both), Hamming (categorical/binary features), cosine distance (text, high-dimensional sparse data) and Mahalanobis (accounts for feature correlation). Features should be scaled first so no single feature dominates.

### 3838  (raw 220; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;IMPRECISE
* **Issue:** chi-square tests association/independence rather than 'measuring correlation'; omits Cramer's V
* **Original question:** Which metrics can be used to measure correlation of categorical data?
* **Original answer:** Ans. Chi square test can be used for doing so. It gives the measure of correlation between categorical predictors.
* **Proposed answer (rewritten_answer):** The chi-square test of independence tests whether two categorical variables are associated; its p-value indicates evidence of association, and Cramer's V (derived from chi-square, range 0 to 1) measures the strength of the association. Mutual information is another option.

### 3839  (raw 221; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;INCORRECT_ABSOLUTE
* **Issue:** 'KNN is the only algorithm' is false
* **Proposed difficulty:** Medium
* **Original question:** Which algorithm can be used in value imputation in both categorical and continuous categories of data?
* **Original answer:** Ans. KNN is the only algorithm that can be used for imputation of both categorical and continuous variables.
* **Proposed answer (rewritten_answer):** Several methods work for both types. KNN imputation fills a missing value from the nearest neighbours (mean for continuous, mode for categorical). Others: MICE / iterative imputation with a suitable model per column, random forest imputation (missForest), and simple mean/median/mode imputation.

### 3844  (raw 226; Machine Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;IMPRECISE;MISLEADING
* **Issue:** 'noise should be removed' and 'more epochs' are not standard remedies for high bias
* **Proposed difficulty:** Medium
* **Original question:** If we have a high bias error what does it mean? How to treat it?
* **Original answer:** Ans. High bias error means that that model we are using is ignoring all the important trends in the model and the model is underfitting. To reduce underfitting: - We need to increase the complexity of the model - Number of features need to be increased Sometimes it also gives the impression that the data is noisy. Hence noise from data should be removed so that most important signals are found by the model to make effective predictions. Increasing the number of epochs results in increasing the duration of training of the model. It’s helpful in reducing the error.
* **Proposed answer (rewritten_answer):** High bias means the model is too simple to capture the true pattern (underfitting): training and validation error are both high. Remedies: use a more complex model, add features or interactions, reduce regularisation, and train longer (for iterative models such as neural networks). Compare with high variance, where training error is low but validation error is high.

### 3845  (raw 227; Machine Learning; current Medium, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;TYPO
* **Issue:** 'tarin' typo
* **Original question:** Which type of sampling is better for a classification model and why?
* **Original answer:** Ans. Stratified sampling is better in case of classification problems because it takes into account the balance of classes in train and test sets. The proportion of classes is maintained and hence the model performs better. In case of random sampling of data, the data is divided into two parts without taking into consideration the balance classes in the train and test sets. Hence some classes might be present only in tarin sets or validation sets. Hence the results of the resulting model are poor in this case.
* **Proposed answer (replace):** Stratified sampling is better in case of classification problems because it takes into account the balance of classes in train and test sets. The proportion of classes is maintained and hence the model performs better. In case of random sampling of data, the data is divided into two parts without taking into consideration the balance classes in the train and test sets. Hence some classes might be present only in train sets or validation sets. Hence the results of the resulting model are poor in this case.

### 3846  (raw 228; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;FACTUAL_ERROR
* **Issue:** VIF is not 'the percentage of variance which remains unaffected'; tolerance = 1 - R^2 is that quantity and VIF = 1/tolerance
* **Proposed difficulty:** Medium
* **Original question:** What is a good metric for measuring the level of multicollinearity?
* **Original answer:** Ans. VIF or 1/tolerance is a good measure of measuring multicollinearity in models. VIF is the percentage of the variance of a predictor which remains unaffected by other predictors. So higher the VIF value, greater is the multicollinearity amongst the predictors. A rule of thumb for interpreting the variance inflation factor: - 1 = not correlated. - Between 1 and 5 = moderately correlated. - Greater than 5 = highly correlated.
* **Proposed answer (rewritten_answer):** The variance inflation factor (VIF) measures how much the variance of a coefficient is inflated by multicollinearity: VIF_j = 1 / (1 - R_j^2), where R_j^2 comes from regressing predictor j on the other predictors. Tolerance = 1 - R_j^2 = 1 / VIF. Rule of thumb: VIF = 1 means no correlation; above about 5 (some use 10) signals problematic multicollinearity.

### 3848  (raw 230; Machine Learning; current Easy, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;IMPRECISE;MISSING_FORMULA
* **Issue:** vague description of MLE; no log-likelihood
* **Proposed difficulty:** Medium
* **Original question:** What is the role of maximum likelihood in logistic regression.
* **Original answer:** Ans. Maximum likelihood equation helps in estimation of most probable values of the estimator’s predictor variable coefficients which produces results which are the most likely or most probable and are quite close to the truth values.
* **Proposed answer (rewritten_answer):** Logistic regression has no closed-form solution, so coefficients are found by maximum likelihood: choose the weights that maximise the log-likelihood sum[ y*log(p) + (1-y)*log(1-p) ], where p = sigmoid(w.x + b). Maximising this is equivalent to minimising cross-entropy loss, solved iteratively (gradient descent, Newton/IRLS).

### 3850  (raw 232; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;CORRUPTED;IMPRECISE
* **Issue:** garbled definition ('sophisticated way of writing software', 'run onto n threads')
* **Original question:** What is a pipeline?
* **Original answer:** Ans. A pipeline is a sophisticated way of writing software such that each intended action while building a model can be serialized and the process calls the individual functions for the individual tasks. The tasks are carried out in sequence for a given sequence of data points and the entire process can be run onto n threads by use of composite estimators in scikit learn.
* **Proposed answer (rewritten_answer):** A pipeline chains data-processing steps (imputation, scaling, encoding, feature selection) and a final estimator into a single object (e.g. scikit-learn Pipeline). It applies the same steps in order at fit and predict time, avoids data leakage during cross-validation (preprocessing is fitted only on training folds), and makes the workflow reproducible and easy to tune and deploy.

### 3852  (raw 234; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;IMPRECISE
* **Issue:** 'increases bias' is a trade-off, not a benefit
* **Original question:** What are the benefits of pruning?
* **Original answer:** Ans. Pruning helps in the following: - Reduces overfitting - Shortens the size of the tree - Reduces complexity of the model - Increases bias
* **Proposed answer (replace):** Pruning helps in the following: - Reduces overfitting - Shortens the size of the tree - Reduces complexity of the model - Trades a small increase in bias for lower variance

### 3853  (raw 235; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;PROVENANCE_RISK;MISSING_FORMULA
* **Issue:** answer contains a markdown hyperlink to a third-party site; density formula absent
* **Original question:** What is normal distribution?
* **Original answer:** Ans. The distribution having the below properties is called normal distribution. - The [mean, mode and median](https://www.statisticshowto.com/probability-and-statistics/statistics-definitions/mean-median-mode/) are all equal. - The curve is symmetric at the center (i.e. around the mean, μ). - Exactly half of the values are to the left of center and exactly half the values are to the right. - The total area under the curve is 1.
* **Proposed answer (replace):** The distribution having the below properties is called normal distribution. - The mean, mode and median are all equal. - The curve is symmetric at the center (i.e. around the mean, μ). - Exactly half of the values are to the left of center and exactly half the values are to the right. - The total area under the curve is 1.

### 3854  (raw 236; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;IMPRECISE
* **Issue:** 68% lies within one standard deviation of the mean, not 'around the median'
* **Original question:** What is the 68 per cent rule in normal distribution?
* **Original answer:** Ans. The normal distribution is a bell-shaped curve. Most of the data points are around the median. Hence approximately 68 per cent of the data is around the median. Since there is no skewness and its bell-shaped.
* **Proposed answer (rewritten_answer):** In a normal distribution about 68% of values lie within one standard deviation of the mean, about 95% within two, and about 99.7% within three (the empirical or 68-95-99.7 rule).

### 3856  (raw 238; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;IMPRECISE
* **Issue:** a random variable is a function mapping outcomes to numbers, not 'a set of possible values'
* **Original question:** What is a random variable?
* **Original answer:** Ans. A Random Variable is a set of possible values from a random experiment. Example: Tossing a coin: we could get Heads or Tails. Rolling of a dice: we get 6 values
* **Proposed answer (rewritten_answer):** A random variable is a variable whose value is a numerical outcome of a random experiment (formally a function from outcomes to numbers). Examples: the number of heads in 10 coin tosses, or the value shown when rolling a die. It can be discrete or continuous.

### 3857  (raw 239; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;IMPRECISE
* **Issue:** vague wording
* **Proposed difficulty:** Medium
* **Original question:** What is the degree of freedom?
* **Original answer:** Ans. It is the number of independent values or quantities which can be assigned to a statistical distribution. It is used in Hypothesis testing and chi-square test.
* **Proposed answer (rewritten_answer):** Degrees of freedom is the number of values in a calculation that are free to vary. For a sample variance it is n - 1 (one degree is used up by estimating the mean); for a chi-square test of independence on an r x c table it is (r - 1)(c - 1). Degrees of freedom determine the shape of the t, chi-square and F distributions.

### 3861  (raw 243; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;MISSING_FORMULA;IMPRECISE
* **Issue:** bias enters the expected squared error as bias squared
* **Proposed difficulty:** Medium
* **Original question:** What is the error term composed of in regression?
* **Original answer:** Ans. Error is a sum of bias error+variance error+ irreducible error in regression. Bias and variance error can be reduced but not the irreducible error.
* **Proposed answer (replace):** Error is a sum of bias^2 + variance + irreducible error (noise) in regression. Bias and variance error can be reduced but not the irreducible error.

### 3862  (raw 244; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** COSMETIC_PREFIX;CORRUPTED;MISSING_FORMULA
* **Issue:** garbled explanation; no formula
* **Original question:** Which performance metric is better R2 or adjusted R2?
* **Original answer:** Ans. Adjusted R2 because the performance of predictors impacts it. R2 is independent of predictors and shows performance improvement through increase if the number of predictors is increased.
* **Proposed answer (rewritten_answer):** Adjusted R^2 is generally preferred when comparing models with different numbers of predictors. R^2 never decreases when a predictor is added, even a useless one. Adjusted R^2 = 1 - (1 - R^2)(n - 1)/(n - p - 1) penalises extra predictors and only rises if the new variable improves the fit more than chance would.

### 3864  (raw 246; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR;MISSING_FORMULA
* **Issue:** L1 does not assign weights of 'exactly 1 or 0'; it drives many weights to exactly zero
* **Proposed difficulty:** Medium
* **Original question:** What do you understand by L1 and L2 regularization?
* **Original answer:** L2 regularization: It tries to spread error among all the terms. L2 corresponds to a Gaussian prior. L1 regularization: It is more binary/sparse, with many variables either being assigned a 1 or 0 in weighting. L1 corresponds to setting a Laplacean prior on the terms.
* **Proposed answer (rewritten_answer):** L1 (lasso) adds lambda * sum|w| to the loss; it produces sparse solutions (many weights exactly zero), so it also performs feature selection, and corresponds to a Laplace prior. L2 (ridge) adds lambda * sum(w^2); it shrinks all weights toward zero without making them exactly zero, handles correlated features more stably, and corresponds to a Gaussian prior.

### 3868  (raw 250; Machine Learning; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** CORRUPTED;FACTUAL_ERROR;MISSING_FORMULA
* **Issue:** 'sum of likelihood residuals' is garbled; claims accuracy is always 100% on development data (false)
* **Original question:** What is log likelihood in logistic regression?
* **Original answer:** It is the sum of the likelihood residuals. At record level, the natural log of the error (residual) is calculated for each record, multiplied by minus one, and those values are totaled. That total is then used as the basis for deviance (2 x ll) and likelihood (exp(ll)). The same calculation can be applied to a naive model that assumes absolutely no predictive power, and a saturated model assuming perfect predictions. The likelihood values are used to compare different models, while the deviances (test, naive, and saturated) can be used to determine the predictive power and accuracy. Logistic regression accuracy of the model will always be 100 percent for the development data set, but that is not the case once a model is applied to another data set.
* **Proposed answer (rewritten_answer):** The log-likelihood of a logistic regression is the sum over observations of y*log(p) + (1-y)*log(1-p), where p is the predicted probability. Higher (less negative) values mean a better fit. Maximum likelihood estimation maximises it; deviance = -2 * log-likelihood is used to compare nested models (likelihood-ratio test) and AIC = 2k - 2 * log-likelihood to compare models with different numbers of parameters.

### 3870  (raw 252; Machine Learning; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** UNVERIFIED_CLAIM;FACTUAL_ERROR
* **Issue:** complexity claims O(N^2 K) vs O(N^3) for logistic regression are unsupported; 'SVM is better in most cases' is an overgeneralisation
* **Proposed difficulty:** Medium
* **Original question:** What are the advantages of SVM algorithms?
* **Original answer:** SVM algorithms have basically advantages in terms of complexity. First I would like to clear that both Logistic regression as well as SVM can form non linear decision surfaces and can be coupled with the kernel trick. If Logistic regression can be coupled with kernel then why use SVM? ● SVM is found to have better performance practically in most cases. ● SVM is computationally cheaper O(N^2K) where K is no of support vectors (support vectors are those points that lie on the class margin) where as logistic regression is O(N^3) ● Classifier in SVM depends only on a subset of points . Since we need to maximize distance between closest points of two classes (aka margin) we need to care about only a subset of points unlike logistic regression.
* **Proposed answer (rewritten_answer):** Advantages: effective in high-dimensional spaces, including when features outnumber samples; the margin-maximising objective gives good generalisation; the kernel trick allows non-linear boundaries; the decision function depends only on the support vectors, so the model is compact. Disadvantages: training scales poorly with many samples, needs feature scaling and kernel/C tuning, and does not natively give probabilities.

### 3873  (raw 255; Machine Learning; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ILL_POSED_QUESTION;DOES_NOT_ADDRESS
* **Issue:** 'soft margin vs linear kernel' conflates two independent concepts; answer explains hard margin, soft margin and kernels separately
* **Original question:** What is the difference between the normal soft margin SVM and SVM with a linear kernel?
* **Proposed question:** What is the difference between hard-margin and soft-margin SVM, and what role does the kernel play?
* **Original answer:** Hard-margin You have the basic SVM – hard margin. This assumes that data is very well behaved, and you can find a perfect classifier – which will have 0 error on train data. Soft-margin Data is usually not well behaved, so SVM hard margins may not have a solution at all. So we allow for a little bit of error on some points. So the training error will not be 0, but average error over all points is minimized. Kernels The above assume that the best classifier is a straight line. But what is it is not a straight line. (e.g. it is a circle, inside a circle is one class, outside is another class). If we are able to map the data into higher dimensions – the higher dimension may give us a straight line.
* **Proposed answer (rewritten_answer):** Hard-margin SVM requires every training point to be correctly classified outside the margin, so it only works if the data are linearly separable and is sensitive to outliers. Soft-margin SVM allows some violations, penalised by slack variables and controlled by C (large C = fewer violations, higher variance; small C = wider margin, more regularisation). The kernel is a separate choice: a linear kernel keeps a linear boundary, while kernels such as RBF or polynomial map data implicitly into a higher-dimensional space to give non-linear boundaries. Soft-margin can be used with any kernel.

### 3874  (raw 256; Machine Learning; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** TYPO
* **Issue:** 'linear fictions' should be 'linear functions'
* **Original question:** How is linear classifier relevant to SVM?
* **Original answer:** An svm is a type of linear classifier. If you don’t mess with kernels, it’s arguably the most simple type of linear classifier. Linear classifiers (all?) learn linear fictions from your data that map your input to scores like so: scores = Wx + b. Where W is a matrix of learned weights, b is a learned bias vector that shifts your scores, and x is your input data. This type of function may look familiar to you if you remember y = mx + b from high school. A typical svm loss function ( the function that tells you how good your calculated scores are in relation to the correct labels ) would be hinge loss. It takes the form: Loss = sum over all scores except the correct score of max(0, scores – scores(correct class) + 1).
* **Proposed answer (replace):** An svm is a type of linear classifier. If you don’t mess with kernels, it’s arguably the most simple type of linear classifier. Linear classifiers (all?) learn linear functions from your data that map your input to scores like so: scores = Wx + b. Where W is a matrix of learned weights, b is a learned bias vector that shifts your scores, and x is your input data. This type of function may look familiar to you if you remember y = mx + b from high school. A typical svm loss function ( the function that tells you how good your calculated scores are in relation to the correct labels ) would be hinge loss. It takes the form: Loss = sum over all scores except the correct score of max(0, scores – scores(correct class) + 1).

### 3876  (raw 258; Machine Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR;QUESTION_TYPO
* **Issue:** the binary-feature variant is Bernoulli Naive Bayes; 'Binomial' is not the standard name (Multinomial is the count-based variant)
* **Proposed difficulty:** Medium
* **Original question:** Are Gaussian Naive Bayes the same as binomial Naive Bayes?
* **Proposed question:** Is Gaussian Naive Bayes the same as Bernoulli Naive Bayes?
* **Original answer:** Binomial Naive Bayes: It assumes that all our features are binary such that they take only two values. Means 0s can represent “word does not occur in the document” and 1s as “word occurs in the document”. Gaussian Naive Bayes: Because of the assumption of the normal distribution, Gaussian Naive Bayes is used in cases when all our features are continuous. For example in Iris dataset features are sepal width, petal width, sepal length, petal length. So its features can have different values in the data set as width and length can vary. We can’t represent features in terms of their occurrences. This means data is continuous. Hence we use Gaussian Naive Bayes here.
* **Proposed answer (replace):** Bernoulli Naive Bayes: It assumes that all our features are binary such that they take only two values. Means 0s can represent “word does not occur in the document” and 1s as “word occurs in the document”. Gaussian Naive Bayes: Because of the assumption of the normal distribution, Gaussian Naive Bayes is used in cases when all our features are continuous. For example in Iris dataset features are sepal width, petal width, sepal length, petal length. So its features can have different values in the data set as width and length can vary. We can’t represent features in terms of their occurrences. This means data is continuous. Hence we use Gaussian Naive Bayes here.

### 3877  (raw 259; Machine Learning; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** CORRUPTED;DOES_NOT_ADDRESS
* **Issue:** garbled repeated formula; answer describes Bayesian networks rather than the Bayes classifier
* **Original question:** What is the difference between the Naive Bayes Classifier and the Bayes classifier?
* **Original answer:** Naive Bayes assumes conditional independence, P(X|Y, Z)=P(X|Z) P(X|Y,Z)=P(X|Z) P(X|Y,Z)=P(X|Z), Whereas more general Bayes Nets (sometimes called Bayesian Belief Networks), will allow the user to specify which attributes are, in fact, conditionally independent. For the Bayesian network as a classifier, the features are selected based on some scoring functions like Bayesian scoring function and minimal description length(the two are equivalent in theory to each other given that there is enough training data). The scoring functions mainly restrict the structure (connections and directions) and the parameters(likelihood) using the data. After the structure has been learned the class is only determined by the nodes in the Markov blanket(its parents, its children, and the parents of its children), and all variables given the Markov blanket are discarded.
* **Proposed answer (rewritten_answer):** The Bayes classifier assigns x to the class with the highest posterior P(y|x); it is the theoretically optimal classifier (lowest possible error, the Bayes error) but needs the true joint distribution, which is impractical in high dimensions. Naive Bayes approximates it by assuming the features are conditionally independent given the class, so P(x|y) factorises into a product of per-feature terms that can be estimated from limited data. Bayesian networks sit in between by allowing selected dependencies.

### 3879  (raw 261; Machine Learning; current Medium, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR;IMPRECISE
* **Issue:** lists 'discriminant functions' as an attribute (Naive Bayes is a generative model); wording muddled
* **Proposed difficulty:** Easy
* **Original question:** Is naive Bayes supervised or unsupervised?
* **Original answer:** First, Naive Bayes is not one algorithm but a family of Algorithms that inherits the following attributes: 1.Discriminant Functions 2.Probabilistic Generative Models 3.Bayesian Theorem 4.Naive Assumptions of Independence and Equal Importance of feature vectors. Moreover, it is a special type of Supervised Learning algorithm that could do simultaneous multi-class predictions (as depicted by standing topics in many news apps). Since these are generative models, so based upon the assumptions of the random variable mapping of each feature vector these may even be classified as Gaussian Naive Bayes, Multinomial Naive Bayes, Bernoulli Naive Bayes, etc.
* **Proposed answer (rewritten_answer):** Naive Bayes is a supervised learning algorithm: it is trained on labelled data. It is a family of generative classifiers based on Bayes' theorem with a conditional-independence assumption, with variants such as Gaussian, Multinomial and Bernoulli Naive Bayes depending on the feature type. It handles multi-class problems naturally.

### 3880  (raw 262; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** CORRUPTED;MISSING_FORMULA
* **Issue:** first sentence is garbled; no formulas
* **Proposed difficulty:** Medium
* **Original question:** What do you understand by Precision and Recall?
* **Original answer:** In pattern recognition, The information retrieval and classification in machine learning are part of precision. It is also called as positive predictive value which is the fraction of relevant instances among the retrieved instances. Recall is also known as sensitivity and the fraction of the total amount of relevant instances which were actually retrieved. Both precision and recall are therefore based on an understanding and measure of relevance.
* **Proposed answer (rewritten_answer):** Precision = TP / (TP + FP): of the items predicted positive, the fraction that are truly positive (positive predictive value). Recall = TP / (TP + FN): of the actual positives, the fraction found (sensitivity). Higher precision means fewer false alarms; higher recall means fewer misses; F1 combines them.

### 3886  (raw 268; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR
* **Issue:** Random Search CV and Grid Search CV are hyperparameter-search methods, not cross-validation techniques
* **Original question:** List popular cross-validation techniques.
* **Original answer:** K-Fold, Stratified K-Fold, Leave-One-Out, Bootstrapping, Random Search CV, and Grid Search CV.
* **Proposed answer (rewritten_answer):** K-fold, stratified K-fold (preserves class proportions), leave-one-out, leave-p-out, repeated k-fold, group k-fold (keeps groups together), time-series (forward-chaining) split, and bootstrap resampling. Grid search and random search are hyperparameter-search strategies that are usually combined with cross-validation.

### 3890  (raw 272; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOES_NOT_ADDRESS;IMPRECISE
* **Issue:** RMSE is an evaluation metric, not a sparsity remedy; answer is one-sided
* **Proposed difficulty:** Medium
* **Original question:** How do recommendation systems handle sparsity issues?
* **Original answer:** Singular Value Decomposition (SVD) is commonly used to reduce sparsity. RMSE is used to evaluate prediction accuracy.
* **Proposed answer (rewritten_answer):** Common approaches: matrix factorisation (SVD-style latent factor models, ALS) that learns dense low-dimensional user and item factors; dimensionality reduction; content-based or hybrid features so items/users with few interactions can still be scored; using implicit feedback to add signal; and regularisation. RMSE is used afterwards to evaluate prediction accuracy.

### 3895  (raw 277; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** MISLEADING
* **Issue:** 'handling incomplete data' is not an inherent strength of neural networks
* **Proposed difficulty:** Medium
* **Original question:** What are the advantages and disadvantages of neural networks?
* **Original answer:** Advantages include parallel processing and handling incomplete data. Disadvantages include high computational cost and lack of interpretability.
* **Proposed answer (rewritten_answer):** Advantages: learn complex non-linear relationships, learn features automatically from raw data, scale well with large datasets, and parallelise well on GPUs. Disadvantages: need large amounts of data and compute, act as black boxes (hard to interpret), are sensitive to hyperparameters and prone to overfitting without regularisation.

### 3896  (raw 278; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** MISSING_FORMULA
* **Issue:** no defining equation
* **Proposed difficulty:** Medium
* **Original question:** Explain Eigenvectors and Eigenvalues.
* **Original answer:** Eigenvectors represent directions of data transformation, while Eigenvalues represent the magnitude of transformation along those directions.
* **Proposed answer (rewritten_answer):** For a square matrix A, an eigenvector v is a non-zero vector whose direction is unchanged by the transformation, A v = lambda v; the eigenvalue lambda is the factor by which it is stretched. In PCA the eigenvectors of the covariance matrix are the principal directions and the eigenvalues give the variance along each.

### 3900  (raw 282; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR;MISLEADING
* **Issue:** p-value is not the 'confidence of a model'
* **Proposed difficulty:** Medium
* **Original question:** How is p-value useful?
* **Original answer:** P-value helps determine the statistical significance of results and the confidence of a model.
* **Proposed answer (rewritten_answer):** The p-value is the probability, assuming the null hypothesis is true, of observing a result at least as extreme as the one found. A small p-value (below the chosen alpha, e.g. 0.05) is evidence against the null hypothesis. It is not the probability that the null hypothesis is true, and it says nothing about effect size or model quality.

### 3908  (raw 290; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR
* **Issue:** claim reversed: correlated variables make PCA more effective at compressing, since few components capture most variance
* **Proposed difficulty:** Medium
* **Original question:** What impact does correlation have on PCA?
* **Original answer:** Highly correlated variables reduce effective variance, making PCA less effective.
* **Proposed answer (rewritten_answer):** Strong correlation between variables means redundant information, so PCA can capture most of the variance with few components; it is therefore more effective at dimensionality reduction. With uncorrelated variables each component carries similar variance and little compression is possible. PCA is applied to standardised data (or the correlation matrix) so that scale differences do not dominate.

### 3927  (raw 309; Machine Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** MISLEADING;IMPRECISE
* **Issue:** rule 'non-linear -> bagging; interpretability -> SVM' is simplistic (SVMs are not interpretable)
* **Proposed difficulty:** Medium
* **Original question:** There are many machine learning algorithms till now. If given a data set, how can one determine which algorithm to be used for that?
* **Original answer:** Machine Learning algorithm to be used purely depends on the type of data in a given dataset. If data is linear then, we use linear regression. If data shows non-linearity then, the bagging algorithm would do better. If the data is to be analyzed/interpreted for some business purposes then we can use decision trees or SVM. If the dataset consists of images, videos, audios then, neural networks would be helpful to get the solution accurately. So, there is no certain metric to decide which algorithm to be used for a given situation or a data set. We need to explore the data using EDA (Exploratory Data Analysis) and understand the purpose of using the dataset to come up with the best fit algorithm. So, it is important to study all the algorithms in detail.
* **Proposed answer (rewritten_answer):** No algorithm is best for all data (no free lunch). Consider the problem type (regression, classification, clustering), data size, feature types, linearity, interpretability needs, training/inference cost and available labels. Start with a simple baseline (linear/logistic regression, decision tree), then try stronger models (random forest, gradient boosting, SVM, neural networks for images/text/audio) and choose using cross-validation on a suitable metric after EDA.

### 3928  (raw 310; Machine Learning; current Hard, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR;MISSING_FORMULA
* **Issue:** says correlation 'has only three specific values 1, 0, -1' (it ranges continuously over [-1, 1]); zero correlation does not imply independence
* **Proposed difficulty:** Medium
* **Original question:** How are covariance and correlation different from one another?
* **Original answer:** Covariance measures how two variables are related to each other and how one would vary with respect to changes in the other variable. If the value is positive it means there is a direct relationship between the variables and one would increase or decrease with an increase or decrease in the base variable respectively, given that all other conditions remain constant. Correlation quantifies the relationship between two random variables and has only three specific values, i.e., 1, 0, and -1. 1 denotes a positive relationship, -1 denotes a negative relationship, and 0 denotes that the two variables are independent of each other.
* **Proposed answer (rewritten_answer):** Covariance, cov(X,Y) = E[(X - mu_x)(Y - mu_y)], gives the direction of the linear relationship; its magnitude depends on the units of X and Y, so it is not comparable across variables. Correlation (Pearson) = cov(X,Y) / (sigma_x * sigma_y) is the standardised version, unit-free and bounded between -1 and 1. Zero correlation means no linear relationship, not necessarily independence.

### 3929  (raw 311; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** TYPO;THIN_ANSWER
* **Issue:** stray 'C' before 'Causality'; no illustration
* **Original question:** State the differences between causality and correlation.
* **Original answer:** C Causality applies to situations where one action, say X, causes an outcome, say Y, whereas Correlation is just relating one action (X) to another action(Y) but X does not necessarily cause Y.
* **Proposed answer (rewritten_answer):** Correlation means two variables move together; causation means a change in one produces a change in the other. Correlation can arise from confounders or coincidence (ice-cream sales and drownings both rise in summer). Establishing causation needs randomised experiments (A/B tests) or careful causal inference methods that control for confounding.

### 3931  (raw 313; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR
* **Issue:** label encoding maps categories to integers, not 'to 1 and 0'
* **Proposed difficulty:** Medium
* **Original question:** Explain One-hot encoding and Label Encoding. How do they affect dimensionality?
* **Original answer:** One-hot encoding is the representation of categorical variables as binary vectors. Label Encoding is converting labels/words into numeric form. Using one-hot encoding increases the dimensionality of the data set. Label encoding doesn’t affect the dimensionality of the data set. One-hot encoding creates a new variable for each level in the variable whereas, in Label encoding, the levels of a variable get encoded as 1 and 0.
* **Proposed answer (rewritten_answer):** One-hot encoding turns a categorical variable with k levels into k binary columns (one per level), so it increases dimensionality and implies no order. Label encoding maps each level to an integer (0, 1, 2, ...) in a single column, so dimensionality is unchanged, but it implies an artificial order, so it suits ordinal variables or tree-based models rather than linear models.

### 3934  (raw 316; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE;CORRUPTED
* **Issue:** 'high variance dataset' should be a high-variance model; description of bagging is garbled ('polling')
* **Proposed difficulty:** Medium
* **Original question:** If your dataset is suffering from high variance, how would you handle it?
* **Proposed question:** How would you reduce high variance (overfitting) in a model?
* **Original answer:** For datasets with high variance, we could use the bagging algorithm to handle it. Bagging algorithm splits the data into subgroups with sampling replicated from random data. After the data is split, random data is used to create rules using a training algorithm. Then we use polling technique to combine all the predicted outcomes of the model.
* **Proposed answer (rewritten_answer):** Options: get more training data; reduce model complexity (shallower trees, fewer parameters); add regularisation (L1/L2, dropout, early stopping); use feature selection or dimensionality reduction; use bagging/random forests, which average many high-variance models trained on bootstrap samples; use cross-validation to tune.

### 3937  (raw 319; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE
* **Issue:** 'doesn't require any minimum or maximum time input' is filler; regular intervals are common, not required
* **Original question:** What is Time series?
* **Original answer:** A Time series is a sequence of numerical data points in successive order. It tracks the movement of the chosen data points, over a specified period of time and records the data points at regular intervals. Time series doesn’t require any minimum or maximum time input. Analysts often use Time series to examine data according to their specific requirement.
* **Proposed answer (rewritten_answer):** A time series is a sequence of observations recorded over time, usually at regular intervals (hourly, daily, monthly). Observations are time-ordered and often dependent on earlier values. Typical components: trend, seasonality, cyclical patterns and noise. Standard tasks: forecasting, anomaly detection and decomposition.

### 3938  (raw 320; Machine Learning; current Easy, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** MISSING_FORMULA;IMPRECISE
* **Issue:** no formula; requires positive data; transforms towards normality rather than guaranteeing it
* **Proposed difficulty:** Hard
* **Original question:** What is a Box-Cox transformation?
* **Original answer:** Box-Cox transformation is a power transform which transforms non-normal dependent variables into normal variables as normality is the most common assumption made while using many statistical techniques. It has a lambda parameter which when set to 0 implies that this transform is equivalent to log-transform. It is used for variance stabilization and also to normalize the distribution.
* **Proposed answer (rewritten_answer):** Box-Cox is a power transformation for strictly positive data: y(lambda) = (y^lambda - 1) / lambda for lambda != 0 and y(lambda) = ln(y) for lambda = 0. Lambda is chosen by maximum likelihood to make the data as close to normal (and variance as stable) as possible. For data with zeros or negatives, use Yeo-Johnson.

### 3942  (raw 324; Machine Learning; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** CORRUPTED;UNVERIFIED_CLAIM
* **Issue:** 'combine decision trees but at the beginning of the process' is garbled; claims about multiclass detection and imbalanced data are unsupported
* **Original question:** Explain the differences between Random Forest and Gradient Boosting machines.
* **Original answer:** Random forests are a significant number of decision trees pooled using averages or majority rules at the end. Gradient boosting machines also combine decision trees but at the beginning of the process unlike Random forests. Random forest creates each tree independent of the others while gradient boosting develops one tree at a time. Gradient boosting yields better outcomes than random forests if parameters are carefully tuned but it’s not a good option if the data set contains a lot of outliers/anomalies/noise as it can result in overfitting of the model.Random forests perform well for multiclass object detection. Gradient Boosting performs well when there is data which is not balanced such as in real time risk assessment.
* **Proposed answer (rewritten_answer):** Random forest builds many deep trees independently on bootstrap samples with random feature subsets and averages them, reducing variance; it is easy to tune and hard to overfit. Gradient boosting builds shallow trees sequentially, each fitted to the errors (negative gradient of the loss) of the ensemble so far, mainly reducing bias; it often reaches higher accuracy but needs careful tuning (learning rate, trees, depth) and is more sensitive to noisy labels and outliers.

### 3945  (raw 327; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE;MISLEADING
* **Issue:** 'outliers are lost' is wrong (min-max normalisation is distorted by outliers); 'standardization recommended for most applications' is a blanket claim
* **Original question:** Explain the difference between Normalization and Standardization.
* **Original answer:** Normalization and Standardization are the two very popular methods used for feature scaling. Normalization refers to re-scaling the values to fit into a range of [0,1]. Standardization refers to re-scaling data to have a mean of 0 and a standard deviation of 1 (Unit variance). Normalization is useful when all parameters need to have the identical positive scale however the outliers from the data set are lost. Hence, standardization is recommended for most applications.
* **Proposed answer (rewritten_answer):** Normalisation (min-max scaling) rescales values to a fixed range, usually [0, 1]: x' = (x - min) / (max - min). Standardisation (z-score) rescales to mean 0 and standard deviation 1: z = (x - mu) / sigma. Min-max is sensitive to outliers because they set the min and max; standardisation is less affected and is preferred for algorithms that assume centred data (e.g. linear models, SVM, PCA). Fit the scaler on training data only.

### 3947  (raw 329; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE
* **Issue:** 'multivariate normality' applies to the residuals (needed for inference), not the variables; independence of errors is listed as 'no auto-correlation'
* **Proposed difficulty:** Medium
* **Original question:** List all assumptions to be met before starting linear regression.
* **Original answer:** Before starting linear regression, the assumptions to be met are as follow: Linear relationship Multivariate normality No or little multicollinearity No auto-correlation Homoscedasticity
* **Proposed answer (rewritten_answer):** Main assumptions: (1) linear relationship between predictors and target; (2) independent errors (no autocorrelation); (3) homoscedasticity (constant error variance); (4) approximately normal residuals, needed for confidence intervals and tests; (5) no severe multicollinearity among predictors.

### 3948  (raw 330; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ILL_POSED_QUESTION;IMPRECISE
* **Issue:** line does not 'rotate'; best fit is where squared error is minimised
* **Proposed difficulty:** Medium
* **Original question:** When does the linear regression line stop rotating or find the optimal fit?
* **Proposed question:** How is the best-fit line determined in linear regression?
* **Original answer:** A place where the highest RSquared value is found, is the place where the line comes to rest. RSquared represents the amount of variance captured by the virtual linear regression line with respect to the total variance captured by the dataset.
* **Proposed answer (rewritten_answer):** The line is chosen to minimise the sum of squared residuals (ordinary least squares). This has a closed-form solution (the normal equations) and can also be reached with gradient descent. For a given dataset, minimising squared error is equivalent to maximising R^2.

### 3949  (raw 331; Machine Learning; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** CORRUPTED;FACTUAL_ERROR
* **Issue:** 'derived from cost function' is wrong; logistic regression is based on the logit (log-odds) / sigmoid function
* **Proposed difficulty:** Medium
* **Original question:** Why is logistic regression a type of classification technique and not a regression? Name the function it is derived from?
* **Proposed question:** Why is logistic regression a classification technique despite its name, and which function does it use?
* **Original answer:** Since the target column is categorical, it uses linear regression to create an odd function that is wrapped with a log function to use regression as a classifier. Hence, it is a type of classification technique and not a regression. It is derived from cost function.
* **Proposed answer (rewritten_answer):** Logistic regression models the probability of a class with the sigmoid (logistic) function, P(y=1|x) = 1 / (1 + exp(-(w.x + b))); equivalently, it models the log-odds as a linear function of the features. Because the output is a probability that is thresholded (e.g. at 0.5) to assign a class, it is used for classification, even though it is a regression on the log-odds.

### 3953  (raw 335; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** QUESTION_ANSWER_MISMATCH
* **Issue:** question asks for three stages; answer lists six steps
* **Original question:** What Are the Three Stages of Building a Model in Machine Learning?
* **Proposed question:** What are the main steps in building a machine learning model?
* **Original answer:** To build a model in machine learning, you need to follow few steps: - Understand the business model - Data acquisitions - Data cleaning - Exploratory data analysis - Use machine learning algorithms to make a model - Use unknown dataset to check the accuracy of the model
* **Proposed answer:** none proposed (answer unchanged)

### 3957  (raw 339; NLP; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR
* **Issue:** says NLP extracts data 'from audio'; NLP handles text (speech is a separate front end)
* **Original question:** What do you understand by Natural Language Processing?
* **Original answer:** Natural Language Processing is a field of computer science that deals with communication between computer systems and humans. It is a technique used in Artificial Intelligence and Machine Learning. It is used to create automated software that helps understand human spoken languages to extract useful information from the data it gets in the form of audio. Techniques in NLP allow computer systems to process and interpret data in the form of natural languages.
* **Proposed answer (rewritten_answer):** Natural Language Processing is the field of AI and linguistics concerned with enabling computers to process, understand and generate human language. Typical tasks: tokenisation, part-of-speech tagging, parsing, named entity recognition, sentiment analysis, machine translation, question answering and summarisation. Speech is handled by a speech-recognition front end that produces text.

### 3958  (raw 340; NLP; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE;OVERSTATED
* **Issue:** 'useless data' and 'one of the most important tasks' are overstatements; removal is task-dependent
* **Proposed difficulty:** Medium
* **Original question:** What are stop words?
* **Original answer:** Stop words are said to be useless data for a search engine. Words such as articles, prepositions, etc. are considered as stop words. There are stop words such as was, were, is, am, the, a, an, how, why, and many more. In Natural Language Processing, we eliminate the stop words to understand and analyze the meaning of a sentence. The removal of stop words is one of the most important tasks for search engines. Engineers design the algorithms of search engines in such a way that they ignore the use of stop words. This helps show the relevant search result for a query.
* **Proposed answer (rewritten_answer):** Stop words are very common words (the, is, a, of) that carry little discriminative meaning for many tasks, so they are often removed to reduce noise and feature space in search and bag-of-words models. They should not always be removed: negations and function words matter for sentiment, and modern transformer models use them.

### 3959  (raw 341; NLP; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** MISSING_FORMULA;FACTUAL_ERROR
* **Issue:** IDF is a corpus-level measure, not 'the importance of the term in a document'; no formula
* **Proposed difficulty:** Medium
* **Original question:** What is TF-IDF?
* **Original answer:** TFIDF or Term Frequency-Inverse Document Frequency indicates the importance of a word in a set. It helps in information retrieval with numerical statistics. For a specific document, TF-IDF shows a frequency that helps identify the keywords in a document. The major use of TF-IDF in NLP is the extraction of useful information from crucial documents by statistical data. It is ideally used to classify and summarize the text in documents and filter out stop words. TF helps calculate the ratio of the frequency of a term in a document and the total number of terms. Whereas, IDF denotes the importance of the term in a document.
* **Proposed answer (rewritten_answer):** TF-IDF weights a term by how frequent it is in a document (TF) and how rare it is across the corpus (IDF): tf-idf(t,d) = tf(t,d) * log(N / df(t)), where N is the number of documents and df(t) the number containing t (libraries add smoothing variants). Words common in one document but rare overall get high weights; words in nearly every document get low weights. Used for search ranking, keyword extraction and text-classification features.

### 3960  (raw 342; NLP; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** FACTUAL_ERROR;IMPRECISE
* **Issue:** syntactic analysis recovers sentence structure; extracting meaning is semantic analysis
* **Original question:** What is Syntactic Analysis?
* **Original answer:** Syntactic analysis is a technique of analyzing sentences to extract meaning from it. Using syntactic analysis, a machine can analyze and understand the order of words arranged in a sentence. NLP employs grammar rules of a language that helps in the syntactic analysis of the combination and order of words in documents.
* **Proposed answer (rewritten_answer):** Syntactic analysis (parsing) determines the grammatical structure of a sentence - how words group into phrases and how they relate (constituency or dependency trees) - using grammar rules or statistical models. It deals with structure, not meaning, which is the job of semantic analysis.

### 3970  (raw 352; NLP; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** CORRUPTED;IMPRECISE
* **Issue:** answer recites formal-language definitions rather than how regular expressions are used in NLP
* **Proposed difficulty:** Medium
* **Original question:** What are Regular Expressions?
* **Original answer:** A regular expression is used to match and tag words. It consists of a series of characters for matching strings. Suppose, if A and B are regular expressions, then the following are true for them: If {ɛ} is a regular language, then ɛ is a regular expression for it. If A and B are regular expressions, then A + B is also a regular expression within the language {A, B}. If A and B are regular expressions, then the concatenation of A and B (A.B) is a regular expression. If A is a regular expression, then A* (A occurring multiple times) is also a regular expression.
* **Proposed answer (rewritten_answer):** A regular expression (regex) is a pattern language for matching and extracting strings, e.g. r'\d+' matches digits and r'\b[A-Z][a-z]+\b' matches capitalised words. In NLP they are used for tokenisation, cleaning (removing URLs and punctuation), pattern-based extraction (emails, dates) and rule-based tagging. Formally, regular expressions describe regular languages and are equivalent to finite automata.

### 3978  (raw 360; NLP; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** ANSWER_BLEED
* **Issue:** answer ends with diagram reference
* **Original question:** What is Parsing in the context of NLP?
* **Original answer:** Parsing in NLP refers to the understanding of a sentence and its grammatical structure by a machine. Parsing allows the machine to understand the meaning of a word in a sentence and the grouping of words, phrases, nouns, subjects, and objects in a sentence. Parsing helps analyze the text or the document to extract useful insights from it. To understand parsing, refer to the below diagram:
* **Proposed answer (trim):** Parsing in NLP refers to the understanding of a sentence and its grammatical structure by a machine. Parsing allows the machine to understand the meaning of a word in a sentence and the grouping of words, phrases, nouns, subjects, and objects in a sentence. Parsing helps analyze the text or the document to extract useful insights from it.

### 3979  (raw 361; NLP; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOES_NOT_ADDRESS;CORRUPTED
* **Issue:** answer describes recommender-system behaviour rather than text feature extraction
* **Proposed difficulty:** Medium
* **Original question:** What is Feature Extraction in NLP?
* **Original answer:** Features or characteristics of a word help in text or document analysis. They also help in sentiment analysis of a text. Feature extraction is one of the techniques that are used by recommendation systems. Reviews such as ‘excellent,’ ‘good,’ or ‘great’ for a movie are positive reviews, recognized by a recommender system. The recommender system also tries to identify the features of the text that help in describing the context of a word or a sentence. Then, it makes a group or category of the words that have some common characteristics. Now, whenever a new word arrives, the system categorizes it as per the labels of such groups.
* **Proposed answer (rewritten_answer):** Feature extraction converts raw text into numerical features a model can use: bag of words, n-grams, TF-IDF, word embeddings (word2vec, GloVe, contextual embeddings from transformers), plus linguistic features such as POS tags, named entities and sentence length.

### 3983  (raw 365; NLP; current Hard, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE
* **Issue:** ambiguity explanation is loose; algorithms and relations not mentioned
* **Proposed difficulty:** Medium
* **Original question:** Explain Dependency Parsing in NLP?
* **Proposed question:** Explain dependency parsing in NLP.
* **Original answer:** Dependency Parsing, also known as Syntactic parsing in NLP is a process of assigning syntactic structure to a sentence and identifying its dependency parses. This process is crucial to understand the correlations between the “head” words in the syntactic structure. The process of dependency parsing can be a little complex considering how any sentence can have more than one dependency parses. Multiple parse trees are known as ambiguities. Dependency parsing needs to resolve these ambiguities in order to effectively assign a syntactic structure to a sentence.Dependency parsing can be used in the semantic analysis of a sentence apart from the syntactic structuring.
* **Proposed answer (rewritten_answer):** Dependency parsing analyses the grammatical structure of a sentence as directed, labelled relations between a head word and its dependents (e.g. nsubj, dobj), producing a tree rooted at the main verb. Parsers are transition-based or graph-based and trained on treebanks (Universal Dependencies). Uses: information extraction, relation extraction, question answering and grammar checking.

### 3984  (raw 366; NLP; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** THIN_ANSWER;OVERSTATED
* **Issue:** promotional wording; omits extractive vs abstractive
* **Proposed difficulty:** Medium
* **Original question:** What is text Summarization?
* **Original answer:** Text summarization is the process of shortening a long piece of text with its meaning and effect intact. Text summarization intends to create a summary of any given piece of text and outlines the main points of the document. This technique has improved in recent times and is capable of summarizing volumes of text successfully. Text summarization has proved to a blessing since machines can summarise large volumes of text in no time which would otherwise be really time-consuming.
* **Proposed answer (rewritten_answer):** Text summarisation produces a shorter version of a text that keeps its key information. Extractive summarisation selects the most important sentences from the source (e.g. TextRank, TF-IDF scoring); abstractive summarisation generates new sentences, typically with sequence-to-sequence or transformer models, and can hallucinate. Evaluated with ROUGE and human judgement.

### 3986  (raw 368; NLP; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** IMPRECISE
* **Issue:** list of 'modules' includes sentiment and classification, which are not information extraction
* **Proposed difficulty:** Medium
* **Original question:** What is information extraction?
* **Original answer:** Information extraction in the context of Natural Language Processing refers to the technique of extracting structured information automatically from unstructured sources to ascribe meaning to it. This can include extracting information regarding attributes of entities, relationship between different entities and more. The various models of information extraction includes: Tagger Module Relation Extraction Module Fact Extraction Module Entity Extraction Module Sentiment Analysis Module Network Graph Module Document Classification & Language Modeling Module
* **Proposed answer (rewritten_answer):** Information extraction automatically turns unstructured text into structured data. Main tasks: named entity recognition, relation extraction (e.g. person-works-for-company), event extraction, coreference resolution and template filling. Output is typically stored in a database or knowledge graph.

### 3989  (raw 371; NLP; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** CORRUPTED;THIN_ANSWER
* **Issue:** 'taking an output from the corrupt input' is garbled
* **Proposed difficulty:** Medium
* **Original question:** What is Masked Language Model?
* **Original answer:** Masked language models help learners to understand deep representations in downstream tasks by taking an output from the corrupt input. This model is often used to predict the words to be used in a sentence.
* **Proposed answer (rewritten_answer):** A masked language model hides (masks) a fraction of the input tokens (about 15% in BERT) and trains the model to predict them from the surrounding bidirectional context. This pre-training objective yields deep contextual representations that are then fine-tuned for downstream tasks.

### 3993  (raw 375; NLP; current Medium, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** QUESTION_TYPO
* **Issue:** 'NES' should be NER; 'Name entity recognition' should be 'Named entity recognition'
* **Proposed difficulty:** Easy
* **Original question:** What is NES?
* **Proposed question:** What is Named Entity Recognition (NER)?
* **Original answer:** Name entity recognition is more commonly known as NER is the process of identifying specific entities in a text document which are more informative and have a unique context. These often denote places, people, organisations, and more. Even though it seems like these entities are proper nouns, the NER process is far from identifying just the nouns. In fact, NER involves entity chunking or extraction wherein entities are segmented to categorise them under different predefined classes. This step further helps in extracting information.
* **Proposed answer (replace):** Named entity recognition is more commonly known as NER is the process of identifying specific entities in a text document which are more informative and have a unique context. These often denote places, people, organisations, and more. Even though it seems like these entities are proper nouns, the NER process is far from identifying just the nouns. In fact, NER involves entity chunking or extraction wherein entities are segmented to categorise them under different predefined classes. This step further helps in extracting information.

### 4026  (raw 408; Machine Learning; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOMAIN_MISMATCH;MISSING_FORMULA
* **Issue:** churn rate is a product-analytics metric; formula is verbal
* **Proposed domain:** Data Analysis
* **Original question:** What kind of services would find churn helpful? How would you calculate churn?
* **Original answer:** Subscription or recurring-use services. Churn = customers lost during a period divided by customers at the start.
* **Proposed answer (rewritten_answer):** Churn is useful for subscription and recurring-use services (telecom, SaaS, streaming, banking). Churn rate = customers lost during a period / customers at the start of the period (for example 50 lost out of 1,000 gives 5% monthly churn). Retention rate = 1 - churn rate.

### 4045  (raw 427; SQL; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** THIN_ANSWER
* **Issue:** lists the acronym without explaining any property
* **Proposed difficulty:** Medium
* **Original question:** Explain ACID properties.
* **Original answer:** Atomicity, Consistency, Isolation and Durability.
* **Proposed answer (rewritten_answer):** Atomicity: a transaction is all-or-nothing - if any step fails, every change is rolled back. Consistency: a transaction moves the database from one valid state to another, respecting constraints. Isolation: concurrent transactions do not see each other's uncommitted changes (controlled by isolation levels). Durability: once committed, changes survive crashes (via write-ahead logging).

### 4049  (raw 431; SQL; current Easy, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** THIN_ANSWER;IMPRECISE
* **Issue:** omits tie behaviour of RANK (gaps) and DENSE_RANK
* **Proposed difficulty:** Medium
* **Original question:** Difference between ROW_NUMBER and RANK?
* **Original answer:** ROW_NUMBER is unique; RANK allows ties.
* **Proposed answer (rewritten_answer):** ROW_NUMBER assigns a unique sequential number to each row in the partition, breaking ties arbitrarily (or by the ORDER BY). RANK gives tied rows the same number and then skips numbers (1, 2, 2, 4). DENSE_RANK gives tied rows the same number without gaps (1, 2, 2, 3).

### 4065  (raw 447; Python; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** THIN_ANSWER;REQUIRES_CODE
* **Issue:** does not state in-place vs copy distinction
* **Original question:** How would you reverse a list in Python?
* **Original answer:** You can reverse a list using list.reverse() method, slicing [::-1], or reversed() function. Each method has different use cases and performance characteristics.
* **Proposed answer (rewritten_answer):** list.reverse() reverses in place and returns None; slicing [::-1] returns a new reversed list; reversed() returns an iterator over the items in reverse order (wrap in list() for a list). Each is O(n); use reverse() to avoid a copy and slicing/reversed() to keep the original.

```python
a = [1, 2, 3]
b = a[::-1]          # new reversed list; a unchanged
c = list(reversed(a)) # iterator -> new list; a unchanged
a.reverse()          # in place; returns None
```
* **Code test:** PASS

### 4066  (raw 448; Python; current Easy, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOES_NOT_ADDRESS;REQUIRES_CODE;IMPRECISE
* **Issue:** asks for an implementation; answer only describes a BST; O(log n) holds only for balanced trees (O(n) worst case)
* **Proposed difficulty:** Hard
* **Original question:** Implement a binary search tree in Python.
* **Original answer:** A binary search tree is a tree data structure where each node has at most two children, left child contains values less than parent, right child contains values greater than parent. Provides O(log n) average case for search, insert, delete operations.
* **Proposed answer (rewritten_answer):** A BST stores keys so that every left descendant is smaller and every right descendant is larger. Search, insert and delete take O(h), where h is the height: O(log n) on average for random insertions but O(n) in the worst case (sorted input) unless the tree is self-balancing (AVL, red-black). Minimal implementation (no delete):

```python
class Node:
    def __init__(self, key):
        self.key, self.left, self.right = key, None, None

class BST:
    def __init__(self):
        self.root = None

    def insert(self, key):
        if self.root is None:
            self.root = Node(key)
            return
        cur = self.root
        while True:
            if key < cur.key:
                if cur.left is None:
                    cur.left = Node(key); return
                cur = cur.left
            elif key > cur.key:
                if cur.right is None:
                    cur.right = Node(key); return
                cur = cur.right
            else:
                return  # ignore duplicates

    def search(self, key):
        cur = self.root
        while cur:
            if key == cur.key:
                return True
            cur = cur.left if key < cur.key else cur.right
        return False

    def inorder(self):
        out, stack, cur = [], [], self.root
        while stack or cur:
            while cur:
                stack.append(cur); cur = cur.left
            cur = stack.pop(); out.append(cur.key); cur = cur.right
        return out
```
* **Code test:** PASS

### 4068  (raw 450; Python; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOES_NOT_ADDRESS;REQUIRES_CODE
* **Issue:** asks for an implementation; answer only restates the problem
* **Proposed difficulty:** Medium
* **Original question:** Implement the fizzbuzz algorithm in Python.
* **Original answer:** FizzBuzz is a programming problem where numbers from 1 to n are printed, but for multiples of 3 print 'Fizz', for multiples of 5 print 'Buzz', and for multiples of both 3 and 5 print 'FizzBuzz'.
* **Proposed answer (rewritten_answer):** Loop from 1 to n; test divisibility by 15 (or by 3 and 5) first, then 3, then 5, otherwise use the number. Checking the combined case first is the key detail.

```python
def fizzbuzz(n):
    out = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            out.append("FizzBuzz")
        elif i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(str(i))
    return out
```
* **Code test:** PASS

### 4069  (raw 451; Python; current Easy, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOES_NOT_ADDRESS;REQUIRES_CODE
* **Issue:** asks for an implementation; answer only gives complexity
* **Proposed difficulty:** Hard
* **Original question:** Implement Dijkstra's shortest path algorithm.
* **Original answer:** Dijkstra's algorithm finds the shortest path from a starting node to all other nodes in a weighted graph. It uses a priority queue and has O((V + E) log V) time complexity.
* **Proposed answer (rewritten_answer):** Dijkstra's algorithm finds shortest paths from a source to all nodes in a graph with non-negative edge weights. Use a min-heap keyed by distance; repeatedly pop the closest unfinalised node and relax its edges. With a binary heap it runs in O((V + E) log V). It fails with negative weights (use Bellman-Ford).

```python
import heapq

def dijkstra(graph, source):
    """graph: {node: [(neighbour, weight), ...]} with non-negative weights."""
    dist = {node: float("inf") for node in graph}
    dist[source] = 0
    heap = [(0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue  # stale entry
        for v, w in graph[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dist
```
* **Code test:** PASS

### 4070  (raw 452; Python; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** QUESTION_TYPO;REQUIRES_CODE
* **Issue:** 'Whats quicksort algorithm in Python.' is not a well-formed question; no implementation
* **Proposed difficulty:** Medium
* **Original question:** Whats quicksort algorithm in Python.
* **Proposed question:** What is quicksort and how would you implement it in Python?
* **Original answer:** Quicksort is a divide-and-conquer algorithm that picks a pivot element and partitions the array around it. It has average case O(n log n) time complexity but O(n²) worst case.
* **Proposed answer (rewritten_answer):** Quicksort is a divide-and-conquer sort: choose a pivot, partition the items into smaller, equal and larger groups, and recursively sort the outer groups. Average time is O(n log n); the worst case is O(n^2) (for example consistently bad pivots), and the in-place version uses O(log n) extra stack space on average. The version below favours clarity (it allocates new lists):

```python
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    mid = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + mid + quicksort(right)
```
* **Code test:** PASS

### 4071  (raw 453; Python; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** QUESTION_TYPO
* **Issue:** 'Whats bubble sort in Python.' is not a well-formed question
* **Original question:** Whats bubble sort in Python.
* **Proposed question:** What is bubble sort and what is its time complexity?
* **Original answer:** Bubble sort repeatedly steps through the list, compares adjacent elements and swaps them if they're in the wrong order. It has O(n²) time complexity and is mainly used for educational purposes.
* **Proposed answer:** none proposed (answer unchanged)

### 4073  (raw 455; Python; current Easy, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** QUESTION_TYPO;REQUIRES_CODE
* **Issue:** question is a fragment; no Python implementation
* **Proposed difficulty:** Medium
* **Original question:** Whats the Singleton design pattern in Python.
* **Proposed question:** What is the Singleton pattern and how can you implement it in Python?
* **Original answer:** The Singleton pattern restricts a class to a single instance and provides global access to that instance. It's commonly used for logging, configuration, and database connections.
* **Proposed answer (rewritten_answer):** The Singleton pattern restricts a class to one instance and provides global access to it, e.g. for configuration, logging or connection pools. In Python the simplest singleton is a module-level object (modules are imported once); alternatively override __new__ as below. Caveats: it is global state, makes testing harder, and the simple version is not thread-safe.

```python
class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```
* **Code test:** PASS

### 4074  (raw 456; Python; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOES_NOT_ADDRESS;REQUIRES_CODE
* **Issue:** asks for an example; none given
* **Proposed difficulty:** Medium
* **Original question:** Explain inheritance in Python with an example.
* **Original answer:** Inheritance allows a class to inherit attributes and methods from another class. This promotes code reuse and creates a parent-child relationship between classes.
* **Proposed answer (rewritten_answer):** Inheritance lets a child class reuse and extend a parent class: it inherits attributes and methods, can override them, and can call the parent's version with super(). It models an 'is-a' relationship and promotes reuse; Python also supports multiple inheritance (resolved with the MRO).

```python
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return f"{self.name} makes a sound"

class Dog(Animal):
    def speak(self):               # method overriding
        return f"{self.name} barks"

class Cat(Animal):
    def __init__(self, name, indoor=True):
        super().__init__(name)     # reuse parent initialiser
        self.indoor = indoor
```
* **Code test:** PASS

### 4078  (raw 460; Python; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOES_NOT_ADDRESS;REQUIRES_CODE
* **Issue:** asks how; answer names scatter() but gives no usage
* **Proposed difficulty:** Medium
* **Original question:** How do you create a basic scatter plot using Matplotlib?
* **Original answer:** Matplotlib provides scatter() function for creating scatter plots. You can customize colors, sizes, labels, and add titles to make the visualization more informative.
* **Proposed answer (rewritten_answer):** Call plt.scatter(x, y) (or ax.scatter on an Axes); useful options are c (colour or values), s (marker size), alpha (transparency) and label. Add axis labels, a title and optionally a legend, then show or save the figure.

```python
import matplotlib.pyplot as plt

x = [1, 2, 3, 4, 5]
y = [2, 4, 5, 4, 5]
plt.scatter(x, y, c="tab:blue", s=40, alpha=0.8, label="samples")
plt.xlabel("x"); plt.ylabel("y"); plt.title("Scatter plot")
plt.legend()
plt.show()
```
* **Code test:** PASS

### 4080  (raw 462; Python; current Easy, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOES_NOT_ADDRESS;REQUIRES_CODE
* **Issue:** asks for an implementation; answer only describes the method
* **Proposed difficulty:** Hard
* **Original question:** Implement a simple linear regression from scratch using NumPy.
* **Original answer:** Linear regression finds the best-fit line by minimizing the sum of squared differences between predicted and actual values. Uses the normal equation or gradient descent to find optimal parameters.
* **Proposed answer (rewritten_answer):** Linear regression picks the parameters that minimise the sum of squared errors. With a design matrix Xb (including a column of ones), the closed-form (normal-equation) solution is theta = (Xb^T Xb)^-1 Xb^T y; gradient descent is the alternative for large or high-dimensional data. Implementation:

```python
import numpy as np

def fit_linear_regression(X, y):
    """Ordinary least squares via the normal equation; adds an intercept."""
    X = np.asarray(X, dtype=float).reshape(len(X), -1)
    Xb = np.c_[np.ones(len(X)), X]
    theta = np.linalg.pinv(Xb.T @ Xb) @ Xb.T @ np.asarray(y, dtype=float)
    return theta  # theta[0] = intercept, theta[1:] = coefficients

def predict(theta, X):
    X = np.asarray(X, dtype=float).reshape(len(X), -1)
    return np.c_[np.ones(len(X)), X] @ theta
```
* **Code test:** PASS

### 4083  (raw 465; Python; current Easy, raw Easy)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** THIN_ANSWER;REQUIRES_CODE
* **Issue:** no example
* **Original question:** How do you write a basic unit test in Python?
* **Original answer:** Python's unittest module provides a framework for writing test cases. You inherit from unittest.TestCase and write methods that start with 'test'.
* **Proposed answer (rewritten_answer):** Import unittest, subclass unittest.TestCase and write methods whose names start with 'test', using assertion methods such as assertEqual, assertTrue and assertRaises. Run with python -m unittest (or pytest).

```python
import unittest

def add(a, b):
    return a + b

class TestAdd(unittest.TestCase):
    def test_add_positive(self):
        self.assertEqual(add(2, 3), 5)

    def test_add_negative(self):
        self.assertEqual(add(-1, 1), 0)

if __name__ == "__main__":
    unittest.main()
```
* **Code test:** PASS

### 4084  (raw 466; Python; current Easy, raw Hard)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOES_NOT_ADDRESS;REQUIRES_CODE
* **Issue:** asks for an implementation; answer only explains the keywords
* **Proposed difficulty:** Hard
* **Original question:** Implement async/await for concurrent operations in Python.
* **Original answer:** Async/await allows you to write asynchronous code that looks synchronous. async def defines coroutines, await pauses execution until the coroutine completes, enabling efficient I/O operations.
* **Proposed answer (rewritten_answer):** async def defines a coroutine; await suspends it until an awaitable finishes, letting the event loop run other tasks. asyncio.gather (or tasks created with asyncio.create_task) runs coroutines concurrently, which helps I/O-bound work but not CPU-bound work. Example:

```python
import asyncio

async def fetch(name, delay):
    await asyncio.sleep(delay)        # stands in for an I/O call
    return f"{name} done"

async def main():
    results = await asyncio.gather(
        fetch("a", 1), fetch("b", 1), fetch("c", 1)
    )
    return results                    # takes about 1 second, not 3

# asyncio.run(main())
```
* **Code test:** PASS

### 4085  (raw 467; Python; current Easy, raw Medium)
* **Review state:** ready_for_approval; **confidence:** high; **flags:** DOES_NOT_ADDRESS;REQUIRES_CODE
* **Issue:** asks for an implementation; answer only describes generators
* **Proposed difficulty:** Medium
* **Original question:** Implement a generator function in Python.
* **Original answer:** Generators are functions that use 'yield' instead of 'return'. They produce a sequence of values over time, pausing and resuming execution, which is memory-efficient for large datasets.
* **Proposed answer (rewritten_answer):** A generator function contains yield; calling it returns an iterator that produces values lazily, pausing at each yield and resuming where it left off, so it uses constant memory even for huge or infinite sequences. Example:

```python
def fibonacci(limit):
    a, b = 0, 1
    while a < limit:
        yield a
        a, b = b, a + b
```
* **Code test:** PASS

## B. Needs review (judgement involved) (30)

### 3633  (raw 15; Data Analysis; current Easy, raw Medium)
* **Review state:** needs_review; **confidence:** medium; **flags:** QUESTION_CORRUPTED;OPEN_ENDED;THIN_ANSWER
* **Issue:** lost 'fi' ligatures: 'wi' = 'wifi', 'o ce' = 'office'; answer weak
* **Proposed difficulty:** Medium
* **Original question:** Given that you have wi data in your o ce, how would you determine which rooms and areas are underutilized and overutilized?
* **Proposed question:** Given that you have wifi data in your office, how would you determine which rooms and areas are underutilized and overutilized?
* **Original answer:** If the data is more used in one room, then that one is over utilized! Maybe account for the room capacity and normalize the data.
* **Proposed answer (rewritten_answer):** Aggregate WiFi connection logs (connected devices per access point / room by hour) and normalise by room capacity and opening hours; compare utilisation distributions (average vs peak) and flag rooms persistently below or above agreed thresholds. Caveats: devices are not people, one person may have several devices, and access-point coverage overlaps rooms.

### 3636  (raw 18; Data Analysis; current Easy, raw Hard)
* **Review state:** needs_review; **confidence:** low; **flags:** OPEN_ENDED;THIN_ANSWER;REQUIRES_DATA
* **Issue:** answer only restates the question
* **Proposed difficulty:** Hard
* **Original question:** Given position data of NBA players in a season’s games, how would you evaluate a basketball player’s defensive ability?
* **Original answer:** - Measure how effectively a player reduces opponents' scoring opportunities through positioning, shot contesting, and defensive coverage. Lower opponent scoring indicates stronger defense.
* **Proposed answer:** none proposed

### 3652  (raw 34; Deep Learning; current Easy, raw Easy)
* **Review state:** needs_review; **confidence:** medium; **flags:** OUTDATED;CORRUPTED
* **Issue:** lists Theano/Caffe2/CNTK/Chainer as current and run-together 'DyNetGensim'
* **Original question:** What are the deep learning frameworks or tools?
* **Original answer:** Deep learning frameworks or tools are: Tensorflow, Keras, Chainer, Pytorch, Theano & Ecosystem, Caffe2, CNTK, DyNetGensim, DSSTNE, Gluon, Paddle, Mxnet, BigDL
* **Proposed answer (rewritten_answer):** Mainstream frameworks today: PyTorch, TensorFlow with Keras (Keras 3 can run on TensorFlow, JAX or PyTorch) and JAX. Older or discontinued: Theano, CNTK, Caffe/Caffe2, Chainer. Hugging Face Transformers is a higher-level library built on top of these. (Verify against current documentation before ingestion: the landscape changes.)

### 3803  (raw 185; Machine Learning; current Easy, raw Hard)
* **Review state:** needs_review; **confidence:** medium; **flags:** IMPRECISE;MISLEADING
* **Issue:** 'twice as likely to be picked' is an unsupported claim; 'linearly contain the same information' is loose
* **Proposed difficulty:** Medium
* **Original question:** What happens when we have correlated features in our data?
* **Original answer:** In random forest, the information contained in correlated features is twice as much likely to be picked than any other information. Adding correlated features means they linearly contain the same information and thus it will reduce the robustness of your model. Each time you train your model, your model might pick one feature or the other to do the same job.
* **Proposed answer (rewritten_answer):** In a random forest, correlated features share the importance: either one can be chosen at a split, so the importance of each is diluted and feature-importance rankings become unstable, though predictive accuracy is usually little affected. In linear models, strong multicollinearity makes coefficient estimates unstable with large variance. Remedies: drop or combine redundant features, use PCA, or use regularisation (ridge/lasso).

### 3809  (raw 191; Machine Learning; current Hard, raw Hard)
* **Review state:** needs_review; **confidence:** medium; **flags:** FACTUAL_ERROR;DOMAIN_MISMATCH
* **Issue:** gradient descent via backprop does not guarantee a global minimum; deep-learning content labelled ML (check duplicate against the DL block)
* **Proposed difficulty:** Medium
* **Proposed domain:** Deep Learning
* **Original question:** What is a neural network?
* **Original answer:** Neural networks are typically organized in layers. Layers are made up of a number of interconnected nodes which contain an activation function. Patterns are presented to the network via the input layer, which communicates to one or more hidden layers where the actual processing is done via a system of weighted connections. The hidden layers then link to an output layer where the answer is output. Backpropagation performs a gradient descent within the solution's vector space towards a global minimum along the steepest vector of the error surface.
* **Proposed answer (replace):** Neural networks are typically organized in layers. Layers are made up of a number of interconnected nodes which contain an activation function. Patterns are presented to the network via the input layer, which communicates to one or more hidden layers where the actual processing is done via a system of weighted connections. The hidden layers then link to an output layer where the answer is output. Backpropagation performs a gradient descent within the solution's vector space towards a (local) minimum along the steepest vector of the error surface.

### 3810  (raw 192; Machine Learning; current Medium, raw Medium)
* **Review state:** needs_review; **confidence:** medium; **flags:** CORRUPTED;IMPRECISE
* **Issue:** 'linear regression either - svm' is garbled; 'sparse data' is ambiguous (many zeros vs missing values)
* **Original question:** How do you deal with sparse data?
* **Proposed question:** How do you deal with sparse data (features that are mostly zeros)?
* **Original answer:** We could take a look at L1 regularization since it best fits the sparse data and does feature selection. If linear relationship - linear regression either - svm. Also it would be nice to use one-hot-encoding or bag-of-words. A one hot encoding is a representation of categorical variables as binary vectors.This first requires that the categorical values be mapped to integer values.Then, each integer value is represented as a binary vector that is all zero values except the index of the integer, which is marked with a 1.
* **Proposed answer (rewritten_answer):** Store the data in a sparse format (e.g. CSR) so memory and computation scale with non-zeros. Use models that handle sparsity well: L1-regularised linear/logistic regression (also performs feature selection), linear SVMs, Naive Bayes. Reduce dimensionality with truncated SVD or feature hashing, and drop very rare features. For high-cardinality categoricals, one-hot encoding creates sparse vectors by design.

### 3813  (raw 195; Machine Learning; current Easy, raw Hard)
* **Review state:** needs_review; **confidence:** medium; **flags:** THIN_ANSWER;UNVERIFIED_CLAIM
* **Issue:** answer is circular; whether reduction helps an SVM depends on the data (SVMs cope well with high dimensions)
* **Proposed difficulty:** Medium
* **Original question:** What is the advantage of performing dimensionality reduction before fitting an SVM?
* **Original answer:** Support Vector Machine Learning Algorithm performs better in the reduced space. It is beneficial to perform dimensionality reduction before fitting an SVM if the number of features is large when compared to the number of observations.
* **Proposed answer (rewritten_answer):** Dimensionality reduction (e.g. PCA) before an SVM can reduce noise and redundant features, lower training and prediction cost (kernel SVM training is roughly quadratic to cubic in samples and linear in features), and reduce overfitting when features greatly outnumber samples. It is not always beneficial: SVMs often work well in high dimensions, and reduction can discard discriminative information, so validate it with cross-validation.

### 3817  (raw 199; Machine Learning; current Easy, raw Hard)
* **Review state:** needs_review; **confidence:** medium; **flags:** IMPRECISE;LOW_RELEVANCE
* **Issue:** 'symmetric functions' should read sinusoids; the audit found this topic duplicated elsewhere (resolve in duplicate pass)
* **Proposed difficulty:** Medium
* **Original question:** What's a Fourier transform?
* **Original answer:** A Fourier transform is a generic method to decompose generic functions into a superposition of symmetric functions. The Fourier transform finds the set of cycle speeds, amplitudes and phases to match any time signal. A Fourier transform converts a signal from time to frequency domain — it's a very common way to extract features from audio signals or other time series such as sensor data.
* **Proposed answer (replace):** A Fourier transform is a generic method to decompose generic functions into a superposition of sinusoidal (sine and cosine) functions. The Fourier transform finds the set of cycle speeds, amplitudes and phases to match any time signal. A Fourier transform converts a signal from time to frequency domain — it's a very common way to extract features from audio signals or other time series such as sensor data.

### 3847  (raw 229; Machine Learning; current Easy, raw Medium)
* **Review state:** needs_review; **confidence:** medium; **flags:** COSMETIC_PREFIX;UNVERIFIED_CLAIM
* **Issue:** 'its inclusion increases the performance' is unsupported
* **Proposed difficulty:** Medium
* **Original question:** When can be a categorical value treated as a continuous variable and what effect does it have when done so?
* **Original answer:** Ans. A categorical predictor can be treated as a continuous one when the nature of data points it represents is ordinal. If the predictor variable is having ordinal data then it can be treated as continuous and its inclusion in the model increases the performance of the model.
* **Proposed answer (rewritten_answer):** An ordinal categorical variable can be encoded as integers and treated as continuous when the spacing between levels is roughly meaningful (e.g. rating 1-5). It saves parameters versus one-hot encoding, but assumes a linear effect per level; if the spacing is not equal, performance can suffer. Nominal categories (no order) should not be treated as continuous.

### 3858  (raw 240; Machine Learning; current Easy, raw Easy)
* **Review state:** needs_review; **confidence:** medium; **flags:** COSMETIC_PREFIX;FACTUAL_ERROR;TIME_SENSITIVE
* **Issue:** describes user-to-user filtering and company-specific practice; the published Amazon approach is item-to-item collaborative filtering (Linden et al., 2003)
* **Original question:** Which kind of recommendation system is used by amazon to recommend similar items?
* **Proposed question:** How does item-based collaborative filtering recommend similar items?
* **Original answer:** Ans. Amazon uses a collaborative filtering algorithm for the recommendation of similar items. It’s a user to user similarity based mapping of user likeness and susceptibility to buy.
* **Proposed answer (rewritten_answer):** Item-based collaborative filtering computes similarity between items from the pattern of user interactions (e.g. cosine or Pearson over item rating/purchase vectors) and recommends items most similar to those a user has already liked or bought. It scales better than user-based filtering when there are far more users than items and similarities can be precomputed.

### 3871  (raw 253; Machine Learning; current Hard, raw Medium)
* **Review state:** needs_review; **confidence:** medium; **flags:** ILL_POSED_QUESTION;INCORRECT_ABSOLUTE
* **Issue:** assumes XGBoost always beats SVM
* **Proposed difficulty:** Medium
* **Original question:** Why does XGBoost perform better than SVM?
* **Proposed question:** When does XGBoost tend to outperform an SVM, and when might an SVM be preferable?
* **Original answer:** First reason is that XGBoos is an ensemble method that uses many trees to make a decision so it gains power by repeating itself. SVM is a linear separator, when data is not linearly separable SVM needs a Kernel to project the data into a space where it can separate it, there lies its greatest strength and weakness, by being able to project data into a high dimensional space SVM can find a linear separation for almost any data but at the same time it needs to use a Kernel and we can argue that there’s not a perfect kernel for every dataset.
* **Proposed answer (rewritten_answer):** XGBoost (gradient-boosted trees) usually does better on tabular data with mixed feature types, missing values and non-linear interactions, needs little scaling and scales to large datasets. SVMs can be preferable on smaller datasets, in high-dimensional sparse settings such as text, or when a good kernel is known. Neither wins universally; compare with cross-validation.

### 3888  (raw 270; Machine Learning; current Easy, raw Medium)
* **Review state:** needs_review; **confidence:** medium; **flags:** ILL_POSED_QUESTION;MISLEADING
* **Issue:** cluster labels are pseudo-labels, not ground truth; supervised learning needs real labels
* **Proposed difficulty:** Medium
* **Original question:** How can we use a dataset without a target variable in supervised learning?
* **Proposed question:** What can you do if your dataset has no target variable but you need supervised learning?
* **Original answer:** Apply clustering algorithms to generate cluster labels, then use those labels as target variables for supervised learning.
* **Proposed answer (rewritten_answer):** Supervised learning needs labels. Options: obtain labels (manual annotation, active learning to label only the most useful samples, crowdsourcing); use weak supervision or semi-supervised learning if some labels exist; use self-supervised pre-training; or fall back to unsupervised methods (clustering, anomaly detection). Cluster assignments can be used as pseudo-labels but reflect the clustering algorithm's assumptions, not ground truth, so validate them with domain knowledge.

### 3915  (raw 297; Machine Learning; current Easy, raw Hard)
* **Review state:** needs_review; **confidence:** medium; **flags:** PLACEHOLDER;OPEN_ENDED
* **Issue:** 'our company's users' references an unspecified company
* **Proposed difficulty:** Hard
* **Original question:** How would you implement a recommendation system for our company’s users?
* **Proposed question:** How would you design a recommendation system for an e-commerce platform?
* **Original answer:** I would first understand the company, users, products, and revenue drivers, then collect user interaction data and item features. I would build a baseline, test content-based, collaborative filtering, or hybrid models, evaluate them with suitable metrics, and monitor the system after deployment.
* **Proposed answer:** none proposed (answer unchanged)

### 3932  (raw 314; Machine Learning; current Easy, raw Medium)
* **Review state:** needs_review; **confidence:** medium; **flags:** ILL_POSED_QUESTION
* **Issue:** brain-teaser with unclear wording; relies on a normality assumption
* **Proposed difficulty:** Medium
* **Original question:** A data set has missing values spread along one standard deviation from the mean. How much data would remain untouched?
* **Proposed question:** In a normally distributed feature, values within one standard deviation of the mean are missing. What fraction of the data remains?
* **Original answer:** It is given that the data is spread across mean that is the data is spread across an average. So, we can presume that it is a normal distribution. In a normal distribution, about 68% of data lies in 1 standard deviation from averages like mean, mode or median. That means about 32% of the data remains uninfluenced by missing values.
* **Proposed answer:** none proposed (answer unchanged)

### 3961  (raw 343; NLP; current Hard, raw Medium)
* **Review state:** needs_review; **confidence:** medium; **flags:** IMPRECISE
* **Issue:** NLG is generation, not a semantic-analysis technique; NER is usually information extraction
* **Proposed difficulty:** Medium
* **Original question:** What is Semantic Analysis?
* **Original answer:** Semantic analysis helps make a machine understand the meaning of a text. It uses various algorithms for the interpretation of words in sentences. It also helps understand the structure of a sentence. Techniques used for semantic analysis are as given below: Named entity recognition: This is the process of information retrieval that helps identify entities such as the name of a person, organization, place, time, emotion, etc.Word sense disambiguation: It helps identify the sense of a word used in different sentences. Natural language generation: It is a process used by the software to convert the structured data into human spoken languages. By using NLG, organizations can automate content for custom reports.
* **Proposed answer (rewritten_answer):** Semantic analysis determines the meaning of words and sentences. Typical techniques: word sense disambiguation (which sense a word has in context), semantic role labelling (who did what to whom), relation extraction and distributional/embedding-based representations. Named entity recognition is often used as a supporting step.

### 3965  (raw 347; NLP; current Easy, raw Medium)
* **Review state:** needs_review; **confidence:** medium; **flags:** REQUIRES_CODE;FACTUAL_ERROR
* **Issue:** example output ('flying' -> 'fly') does not match Porter stemmer behaviour (nltk gives 'fli'); code lines run together
* **Proposed difficulty:** Medium
* **Original question:** Explain Stemming with the help of an example.
* **Original answer:** In Natural Language Processing, stemming is the method to extract the root word by removing suffixes and prefixes from a word. For example, we can reduce ‘stemming’ to ‘stem’ by removing ‘m’ and ‘ing.’ We use various algorithms for implementing stemming, and one of them is PorterStemmer. First, we will import PorterStemmer from the nltk package. from nltk.stem import PorterStemmer Creating an object for PorterStemmer pst=PorterStemmer() pst.stem(“running”), pst.stem(“cookies”), pst.stem(“flying”) Output: (‘run’, ‘cooki', ‘fly’ )
* **Proposed answer (rewritten_answer):** Stemming reduces a word to a root form by stripping suffixes with heuristic rules, so the result need not be a real word. Example with NLTK's PorterStemmer: from nltk.stem import PorterStemmer; p = PorterStemmer(); [p.stem(w) for w in ['running', 'cookies', 'flying', 'stemming']] -> ['run', 'cooki', 'fli', 'stem']. Lemmatisation (dictionary-based) would give real words, e.g. 'flying' -> 'fly' with the verb POS.
* **Code test:** PASS

### 3973  (raw 355; NLP; current Easy, raw Easy)
* **Review state:** needs_review; **confidence:** medium; **flags:** MISSING_TABLE
* **Issue:** answer ends 'The below table shows...' with no table
* **Original question:** What is the difference between NLP and NLU?
* **Proposed question:** What is the difference between NLP and NLU?
* **Original answer:** The below table shows the difference between NLP and NLU:
* **Proposed answer (rewritten_answer):** NLP (Natural Language Processing) is the broad field covering all computational handling of human language, including understanding and generation (NLG) as well as tasks like tokenisation and translation. NLU (Natural Language Understanding) is the subset focused on comprehension - intent detection, entity extraction, meaning and context. NLU = reading comprehension; NLP = understanding plus generation.

### 3974  (raw 356; NLP; current Easy, raw Easy)
* **Review state:** needs_review; **confidence:** medium; **flags:** MISSING_TABLE
* **Issue:** answer ends 'The below table shows...' with no table
* **Original question:** What is the difference between NLP and CI?
* **Proposed question:** What is the difference between NLP and a conversational interface (CI)?
* **Original answer:** The below table shows the difference between NLP and CI:
* **Proposed answer (rewritten_answer):** NLP is the underlying technology that processes and understands language. A conversational interface (chatbot or voice assistant) is an application that lets users interact through natural dialogue and uses NLP, dialogue management and often speech components to do so. NLP can exist without a CI (e.g. search, translation); a CI depends on NLP.

### 3985  (raw 367; NLP; current Hard, raw Medium)
* **Review state:** needs_review; **confidence:** medium; **flags:** OUTDATED;UNVERIFIED_CLAIM
* **Issue:** 'spaCy supports only 7 languages' is a dated figure; other comparison points are loosely worded
* **Proposed difficulty:** Medium
* **Original question:** What is NLTK? How is it different from Spacy?
* **Original answer:** NLTK or Natural Language Toolkit is a series of libraries and programs that are used for symbolic and statistical natural language processing. This toolkit contains some of the most powerful libraries that can work on different ML techniques to break down and understand human language. NLTK is used for Lemmatization, Punctuation, Character count, Tokenization, and Stemming. The difference between NLTK and Spacey are as follows: While NLTK has a collection of programs to choose from, Spacey contains only the best-suited algorithm for a problem in its toolkit NLTK supports a wider range of languages compared to Spacey (Spacey supports only 7 languages) While Spacey has an object-oriented library, NLTK has a string processing library Spacey can support word vectors while NLTK cannot
* **Proposed answer (rewritten_answer):** NLTK is a teaching and research toolkit with many algorithms and corpora, mostly string-based and good for experimentation. spaCy is production-oriented: fast, object-oriented pipelines (tokenisation, tagging, parsing, NER), pretrained models, word vectors and transformer integration, and offers one well-chosen implementation per task. Language coverage differs and changes over time.

### 3988  (raw 370; NLP; current Easy, raw Easy)
* **Review state:** needs_review; **confidence:** medium; **flags:** FACTUAL_ERROR
* **Issue:** describes lexical ambiguity; pragmatic ambiguity depends on context, speaker intent and world knowledge
* **Proposed difficulty:** Medium
* **Original question:** What is Pragmatic Ambiguity in NLP?
* **Original answer:** Pragmatic ambiguity refers to those words which have more than one meaning and their use in any sentence can depend entirely on the context. Pragmatic ambiguity can result in multiple interpretations of the same sentence. More often than not, we come across sentences which have words with multiple meanings, making the sentence open to interpretation. This multiple interpretation causes ambiguity and is known as Pragmatic ambiguity in NLP.
* **Proposed answer (rewritten_answer):** Pragmatic ambiguity arises when a sentence is syntactically and lexically clear but its intended meaning depends on context or speaker intent, e.g. 'Can you pass the salt?' (a request, not a question about ability) or 'I saw him at the bank' only when context resolves it. Lexical ambiguity concerns a single word with multiple senses; pragmatic ambiguity concerns the sentence in context.

### 4013  (raw 395; Machine Learning; current Easy, raw Easy)
* **Review state:** needs_review; **confidence:** medium; **flags:** DOMAIN_MISMATCH;OPEN_ENDED
* **Issue:** product metrics belong to product / data analysis, not predictive modelling
* **Proposed difficulty:** Medium
* **Proposed domain:** Data Analysis
* **Original question:** What would be good metrics of success for an advertising-driven consumer product? A service-driven consumer product?
* **Original answer:** Advertising: DAU, impressions, CTR, and revenue per user. Service: conversions, completed transactions, retention, and satisfaction.
* **Proposed answer:** none proposed (answer unchanged)

### 4014  (raw 396; Machine Learning; current Easy, raw Easy)
* **Review state:** needs_review; **confidence:** medium; **flags:** DOMAIN_MISMATCH;OPEN_ENDED
* **Issue:** product metrics question
* **Proposed difficulty:** Medium
* **Proposed domain:** Data Analysis
* **Original question:** What would be good metrics of success for a productivity tool? A MOOC?
* **Original answer:** Productivity: active use, retention, and task completion. MOOC: enrolment, progress, completion, and paid conversion.
* **Proposed answer:** none proposed (answer unchanged)

### 4015  (raw 397; Machine Learning; current Easy, raw Medium)
* **Review state:** needs_review; **confidence:** medium; **flags:** DOMAIN_MISMATCH;OPEN_ENDED
* **Issue:** product metrics question
* **Proposed difficulty:** Medium
* **Proposed domain:** Data Analysis
* **Original question:** What would be good metrics of success for an e-commerce product? A subscription product? Premium subscriptions?
* **Original answer:** E-commerce: conversion, AOV, revenue, and repeat purchases. Subscription: churn, MRR, CAC, LTV, and retention. Premium: free-to-paid conversion and renewal.
* **Proposed answer:** none proposed (answer unchanged)

### 4016  (raw 398; Machine Learning; current Easy, raw Medium)
* **Review state:** needs_review; **confidence:** medium; **flags:** DOMAIN_MISMATCH;OPEN_ENDED
* **Issue:** product metrics question
* **Proposed difficulty:** Medium
* **Proposed domain:** Data Analysis
* **Original question:** What would be good metrics of success for a consumer product that relies heavily on engagement and interaction? A messaging product?
* **Original answer:** Engagement product: DAU/MAU, sessions, interactions, and retention. Messaging: messages, active chats, response rate, and reliability.
* **Proposed answer:** none proposed (answer unchanged)

### 4017  (raw 399; Machine Learning; current Easy, raw Easy)
* **Review state:** needs_review; **confidence:** medium; **flags:** DOMAIN_MISMATCH;OPEN_ENDED
* **Issue:** product metrics question
* **Proposed difficulty:** Medium
* **Proposed domain:** Data Analysis
* **Original question:** What would be good metrics of success for a product that offered in-app purchases?
* **Original answer:** Track ARPU, ARPPU, payer conversion, purchase frequency, retention, LTV, and total purchase revenue.
* **Proposed answer:** none proposed (answer unchanged)

### 4018  (raw 400; Machine Learning; current Easy, raw Medium)
* **Review state:** needs_review; **confidence:** medium; **flags:** DOMAIN_MISMATCH;OPEN_ENDED
* **Issue:** root-cause analysis of metric changes is a data-analysis topic
* **Proposed difficulty:** Medium
* **Proposed domain:** Data Analysis
* **Original question:** A certain metric is violating your expectations by going down or up more than you expect. How would you try to identify the cause of the change?
* **Original answer:** Break down and segment the metric, then check launches, bugs, campaigns, seasonality, and behaviour changes.
* **Proposed answer:** none proposed (answer unchanged)

### 4019  (raw 401; Machine Learning; current Easy, raw Medium)
* **Review state:** needs_review; **confidence:** medium; **flags:** DOMAIN_MISMATCH;OPEN_ENDED
* **Issue:** root-cause analysis of metric changes
* **Proposed difficulty:** Medium
* **Proposed domain:** Data Analysis
* **Original question:** Growth for total number of tweets sent has been slow this month. What data would you look at to determine the cause of the problem?
* **Original answer:** Check active users, new users, retention, tweets per user, cohorts, product changes, and affected segments.
* **Proposed answer:** none proposed (answer unchanged)

### 4020  (raw 402; Machine Learning; current Easy, raw Medium)
* **Review state:** needs_review; **confidence:** medium; **flags:** DOMAIN_MISMATCH;OPEN_ENDED
* **Issue:** business-analysis case
* **Proposed difficulty:** Medium
* **Proposed domain:** Data Analysis
* **Original question:** You are a restaurant and are approached by Groupon to run a deal. What data would you ask from them in order to determine whether or not to do the deal?
* **Original answer:** Ask for similar deal results, expected sales, redemption rate, repeat visits, costs, and net profit after discount.
* **Proposed answer:** none proposed (answer unchanged)

### 4023  (raw 405; Machine Learning; current Easy, raw Hard)
* **Review state:** needs_review; **confidence:** medium; **flags:** DOMAIN_MISMATCH;OPEN_ENDED
* **Issue:** A/B test / experimentation design question
* **Proposed difficulty:** Hard
* **Proposed domain:** Data Analysis
* **Original question:** How would you measure the impact that sponsored stories on Facebook News Feed have on user engagement? How would you determine the optimum balance between sponsored stories and organic content on a user's News Feed?
* **Original answer:** Run A/B tests with different ad loads and compare engagement, retention, revenue, complaints, hides, and reports.
* **Proposed answer:** none proposed (answer unchanged)

### 4077  (raw 459; Python; current Easy, raw Hard)
* **Review state:** needs_review; **confidence:** low; **flags:** REQUIRES_CODE;SECURITY_SENSITIVE;LOW_RELEVANCE
* **Issue:** asks for an implementation; answer only defines JWT. Authentication code is security-sensitive and not verified here; outside the six interview domains
* **Proposed difficulty:** Hard
* **Original question:** Implement JWT authentication in a Flask API.
* **Original answer:** JWT (JSON Web Tokens) provide stateless authentication. The server generates a token containing user information that clients include in subsequent requests.
* **Proposed answer:** none proposed
* **Code test:** NOT_TESTED

## C. Needs code test (4)

### 3963  (raw 345; NLP; current Easy, raw Easy)
* **Review state:** needs_code_test; **confidence:** medium; **flags:** DOES_NOT_ADDRESS;REQUIRES_CODE
* **Issue:** asks how to tokenize with NLTK; answer only defines tokenization
* **Original question:** How to tokenize a sentence using the nltk package?
* **Original answer:** Tokenization is a process used in NLP to split a sentence into tokens. Sentence tokenization refers to splitting a text or paragraph into sentences.
* **Proposed answer (rewritten_answer):** import nltk; nltk.download('punkt') (a one-off download). Then: from nltk.tokenize import sent_tokenize, word_tokenize; text = 'Hello, world! NLP is fun.'; sent_tokenize(text) -> ['Hello, world!', 'NLP is fun.']; word_tokenize('Hello, world!') -> ['Hello', ',', 'world', '!'].
* **Code test:** FAIL_OR_NOT_RUNNABLE

### 3967  (raw 349; NLP; current Easy, raw Easy)
* **Review state:** needs_code_test; **confidence:** low; **flags:** DOES_NOT_ADDRESS;REQUIRES_CODE;REQUIRES_DATA
* **Issue:** asks how with spaCy; answer gives no code; needs a model with word vectors; similarity is cosine and can be negative
* **Original question:** How to check word similarity using the spacy package?
* **Original answer:** To find out the similarity among words, we use word similarity. We evaluate the similarity with the help of a number that lies between 0 and 1. We use the spacy library to implement the technique of word similarity.
* **Proposed answer:** none proposed
* **Code test:** NOT_TESTED

### 4075  (raw 457; Python; current Easy, raw Medium)
* **Review state:** needs_code_test; **confidence:** low; **flags:** REQUIRES_CODE;LOW_RELEVANCE
* **Issue:** answer contains no code; web development is outside the six interview domains
* **Proposed difficulty:** Medium
* **Original question:** How do you create a simple REST API using Flask?
* **Original answer:** Flask provides decorators to define routes and HTTP methods. You can create endpoints that return JSON responses for building REST APIs.
* **Proposed answer:** none proposed
* **Code test:** NOT_TESTED

### 4081  (raw 463; Python; current Easy, raw Medium)
* **Review state:** needs_code_test; **confidence:** low; **flags:** REQUIRES_CODE
* **Issue:** answer is a definition; no pytest example. pytest is not installed in the audit sandbox, so no example could be executed
* **Proposed difficulty:** Medium
* **Original question:** How do you use mocking in unit tests with pytest?
* **Original answer:** Mocking allows you to replace parts of your system under test with mock objects. This is useful for isolating code from external dependencies like databases or APIs.
* **Proposed answer:** none proposed
* **Code test:** NOT_TESTED

## D. Needs a source (1)

### 3834  (raw 216; Machine Learning; current Medium, raw Medium)
* **Review state:** needs_source; **confidence:** low; **flags:** UNVERIFIED_CLAIM;LOW_RELEVANCE
* **Issue:** niche RL topic; claims such as 'works in continuous environments' and 'sensitive to initialization' need a source
* **Original question:** List the advantages and limitations of the Temporal Difference Learning Method.
* **Original answer:** Temporal Difference Learning Method is a mix of Monte Carlo method and Dynamic programming method. Some of the advantages of this method include: - It can learn in every step online or offline. - It can learn from a sequence which is not complete as well. - It can work in continuous environments. - It has lower variance compared to MC method and is more efficient than MC method. Limitations of TD method are: - It is a biased estimation. - It is more sensitive to initialization.
* **Proposed answer:** none proposed
