from dec_helpers import *
K(3701,"E","THIN_ANSWER","adequate")
K(3702,"E","","adequate")
F(3703,"E","IMPRECISE","'used to understand parameters' is garbled",
  pa="Hyperparameters are settings chosen before training that control the model structure and the training process, e.g. learning rate, number of layers and units, batch size, number of epochs, dropout rate and optimiser. Unlike parameters (weights and biases), they are not learned by gradient descent.",
  state="ready_for_approval",conf="high")
F(3704,"M","ILL_POSED_QUESTION;MISLEADING","hyperparameters are tuned, not 'trained'; the answer lists batch size/epochs/momentum/learning rate as 'four components'",
  pq="How are hyperparameters tuned in neural networks?",
  pa="Hyperparameters are not learned by backpropagation; they are tuned using performance on a validation set. Common approaches: manual tuning, grid search, random search (often more efficient than grid search), Bayesian optimisation (e.g. with Optuna or Hyperopt) and early-stopping-based schemes such as Hyperband. Use a held-out validation set (or cross-validation when affordable) and keep the test set untouched.",
  state="ready_for_approval",conf="high")
X(3705,"DUPLICATE","covered by 3673",dup_of=3673)
X(3706,"DUPLICATE","covered by 3674",dup_of=3674)
X(3707,"DUPLICATE;EDITORIAL","covered by 3676; contains promotional lead-in",dup_of=3676)
X(3708,"LOW_RELEVANCE;DUPLICATE","Boltzmann machine (legacy)",dup_of=3675)
X(3709,"LOW_VALUE","tool advocacy list; TF1-era wording")
F(3710,"M","EDITORIAL;PROVENANCE_RISK","answer ends with a promotion for a named vendor's course",
  trim=" If you are looking forward to becoming an expert",state="ready_for_approval",conf="high")
X(3711,"DUPLICATE;EDITORIAL","covered by 3682; contains editorial text",dup_of=3682)
F(3712,"M","FACTUAL_ERROR;CORRUPTED","pooling described as maintaining image size (it reduces spatial size); 'Connectedness' = fully connected layer",
  pa="A typical CNN stacks convolutional layers (learnable filters/kernels that detect local features), a non-linearity such as ReLU, pooling layers (max or average pooling that reduce spatial size and add some translation tolerance), and finally one or more fully connected layers (often ending in softmax) that produce the output.",
  state="ready_for_approval",conf="high")
X(3713,"DUPLICATE","covered by 3683",dup_of=3683)
K(3714,"M","","correct")
F(3715,"M","ILL_POSED_QUESTION;CORRUPTED","'exploding gradient descent' is not a term; answer is muddled",
  pq="What is the exploding gradient problem in deep learning?",
  pa="Exploding gradients occur when gradients grow exponentially as they are backpropagated through many layers or time steps, producing very large weight updates and unstable or diverging training (loss becomes NaN). Typical remedies: gradient clipping, careful weight initialisation, a smaller learning rate, normalisation layers, and gated architectures such as LSTM/GRU.",
  state="ready_for_approval",conf="high")
F(3716,"M","CORRUPTED;THIN_ANSWER","'used to sequence a string of data' / 'general-purpose computational entity' is garbled",
  pa="LSTM (Long Short-Term Memory) is a recurrent architecture with a memory cell and input, forget and output gates that control what to store, discard and expose. It can learn long-range dependencies and mitigates the vanishing-gradient problem of plain RNNs. Used for sequence tasks such as language modelling, speech recognition and time-series forecasting.",
  state="ready_for_approval",conf="high")
F(3717,"M","IMPRECISE;THIN_ANSWER","'feature removal and variation' is unclear; omits anomaly detection",
  pa="Typical uses: denoising (denoising autoencoders), dimensionality reduction / compression, anomaly detection (unusually high reconstruction error), unsupervised feature learning or pre-training, and generative modelling with variational autoencoders.",
  state="ready_for_approval",conf="high")
K(3718,"M","THIN_ANSWER","list of four common types (denoising and variational also common)")
X(3719,"LOW_RELEVANCE","restricted Boltzmann machine (legacy)")
X(3720,"DUPLICATE;EDITORIAL","covered by 3653; contains editorial tail",dup_of=3653)
X(3721,"DUPLICATE","covered by 3679",dup_of=3679)
X(3722,"DUPLICATE","covered by 3680",dup_of=3680)
X(3723,"LOW_RELEVANCE;OUTDATED;EDITORIAL","deep autoencoders framed as stacked DBNs; editorial tail")
X(3724,"DUPLICATE","covered by 3666",dup_of=3666)
X(3725,"LOW_VALUE","mixes architectures with learning paradigms")
X(3726,"LOW_VALUE;EDITORIAL","mixes architectures with learning paradigms; editorial tail")
X(3727,"DUPLICATE","covered by 3655",dup_of=3655)
F(3728,"M","FACTUAL_ERROR","says padding is added 'around the output matrix'; it is added around the input",
  pa="Valid padding: no padding is added, so with stride 1 the output has size n - f + 1 in each dimension (it shrinks). Same padding: zeros are added around the input so that, with stride 1, the output has the same height and width as the input (padding p = (f - 1) / 2 for an odd filter size f).",
  state="ready_for_approval",conf="high")
F(3729,"M","DOES_NOT_ADDRESS","asks for applications; answer lists model names",
  pq="What is transfer learning and when is it used?",
  pa="Transfer learning reuses a model pre-trained on a large dataset (e.g. ResNet on ImageNet, BERT on large text corpora) for a related task that has less data, either as a fixed feature extractor or by fine-tuning some or all layers. It cuts training time and data requirements. Typical uses: image classification and object detection with small datasets, and NLP tasks such as text classification and NER. It works best when the source and target domains are similar.",
  state="ready_for_approval",conf="high")
F(3730,"M","CORRUPTED;THIN_ANSWER","garbled phrasing; does not state the parallelism / long-range-dependency advantages clearly",
  pa="RNNs process tokens one after another, which prevents parallelisation across time steps and makes long-range dependencies hard to learn (vanishing gradients). Transformers use self-attention: every token can attend directly to every other token, all positions are computed in parallel (much faster training on GPUs) and long-range dependencies are easier to capture. Costs: attention is O(n^2) in sequence length and word-order information must be added via positional encodings.",
  state="ready_for_approval",conf="high")
K(3731,"M","THIN_ANSWER","forget / update / output steps summarised correctly")
X(3732,"OUTDATED;LOW_RELEVANCE","TensorFlow 1.x concepts (constants, variables, placeholders)")
X(3733,"FACTUAL_ERROR;DOMAIN_MISMATCH","bagging/boosting described incorrectly and are not deep-learning concepts; ML equivalents kept (3763, 3909)")
K(3734,"M","","generator/discriminator explanation correct")
X(3735,"LOW_VALUE","'why popular' list of uses")
F(3736,"M","ANSWER_BLEED;COSMETIC_PREFIX","answer starts mid-sentence ('otherwise...') and continues into '2. Describe two ways of dealing with the vanishing gradient problem...'",
  pa="Without non-linear activation functions, a stack of layers is just a composition of linear functions, which is itself a linear function, so the whole network would behave like a single linear model with limited expressive power. Non-linearities let the network learn complex, non-linear decision boundaries.",
  state="ready_for_approval",conf="high")
F(3737,"M","ANSWER_BLEED;COSMETIC_PREFIX;IMPRECISE","bleed into '4. Describe two ways to visualize features of a CNN...'; 'translation invariant' is loosely used (convolution is translation-equivariant; pooling adds approximate invariance)",
  trim=" 4. Describe two ways to visualize features",state="ready_for_approval",conf="high")
K(3738,"M","COSMETIC_PREFIX","correct (log-scale search)")
F(3739,"M","ANSWER_BLEED;COSMETIC_PREFIX","answer continues into questions 7 and 8",
  trim=" 7. Explain the idea behind the Adam optimizer",state="ready_for_approval",conf="high")
K(3740,"E","COSMETIC_PREFIX","correct")
X(3741,"DUPLICATE","covered by 3734",dup_of=3734)
K(3742,"M","COSMETIC_PREFIX;THIN_ANSWER","correct but brief")
X(3743,"LOW_RELEVANCE","multi-task learning is rarely asked at junior level")
K(3744,"M","COSMETIC_PREFIX","adequate")
K(3745,"M","COSMETIC_PREFIX","correct reasoning (non-negative ReLU output -> sigmoid >= 0.5)")
K(3746,"M","COSMETIC_PREFIX;THIN_ANSWER","gradient clipping by value; norm clipping not mentioned")
K(3747,"M","COSMETIC_PREFIX","correct")
F(3748,"M","ANSWER_BLEED;COSMETIC_PREFIX","answer continues into '18. Describe some hyperparameters for transfer learning.'",
  trim=" 18. Describe some hyperparameters for transfer learning",state="ready_for_approval",conf="high")
F(3749,"M","ANSWER_BLEED;COSMETIC_PREFIX;THIN_ANSWER","answer continues into questions 20-21; trimmed answer omits inference-time scaling",
  trim=" 20. Explain why dropout in a neural network acts",state="ready_for_approval",conf="high")
F(3750,"H","ANSWER_BLEED;COSMETIC_PREFIX","answer continues into '23. True/false...'",
  trim=" 23. True/false: adding L2 regularization",state="ready_for_approval",conf="high")
F(3751,"M","ANSWER_BLEED;COSMETIC_PREFIX","answer continues into '25. Describe how L2 regularization...'",
  trim=" 25. Describe how L2 regularization",state="ready_for_approval",conf="high")
