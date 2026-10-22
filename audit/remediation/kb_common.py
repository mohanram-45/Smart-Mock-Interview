"""Shared helpers for the curated-KB build and validation scripts."""
import re
STOP = {"the","and","of","for","in","to","a","an","vs","with","on","data","model","is","are","by","as"}
ACR = {"rnn","nlp","knn","svm","ner","svd","cnn","gan","lstm","pca","roc","auc","sql","bert","tf","idf","mlm","cte","acid","gpu","vae","gru","bpe","lda","sgd","mse","bleu","gpt","rag","pos","oov","nan","iqr","vif","ann","mrr","ols","ctr","etl","mae","rmse","dnn","tpu","api"}

def _stem(w):
    for suf in ("ations","ation","ings","ing","ised","ized","ises","izes","ise","ize","ies","ied","es","ed","s","y","al","ly"):
        if len(w) > len(suf) + 3 and w.endswith(suf): return w[: -len(suf)]
    return w

def words_of(text):
    return {_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower())} | set(re.findall(r"[a-z0-9]+", text.lower()))

def weak_concepts(concepts, text):
    """Return the concepts that are not grounded in `text` (question+answer). A concept is grounded when each of its
    content tokens (or its stem/prefix) occurs in the text; acronym-only concepts and tokens <3 chars are tolerated."""
    ws = words_of(text); raw = text.lower()
    weak = []
    for k in concepts:
        kl = k.lower()
        if kl in raw: continue
        ts = [t for t in re.findall(r"[a-z0-9]+", kl) if t not in STOP]
        if not ts or all(t in ACR for t in ts): continue
        miss = []
        for t in ts:
            if t in ACR or len(t) < 3: continue
            st = _stem(t)
            if t in ws or st in ws or any(w.startswith(st[:5]) and len(st) >= 4 for w in ws) or any(len(w) >= 4 and st.startswith(w[:5]) for w in ws):
                continue
            miss.append(t)
        if miss: weak.append(k)
    return weak
