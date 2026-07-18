"""Interview Configuration - Role mappings and progression rules."""

# Role to Domain Mapping
ROLE_MAPPING = {
    "Data Scientist": [
        "ML",
        "DL",
        "NLP",
        "DATA_ANALYSIS",
        "Python"
    ],
    "Machine Learning Engineer": [
        "ML",
        "DL",
        "Python"
    ],
    "NLP Engineer": [
        "NLP"
    ],
    "Data Analyst": [
        "DATA_ANALYSIS",
        "Python"
    ],
    "Python Developer": [
        "Python"
    ],
    "Custom Interview": []
}

# ─────────────────────────────────────────────────────────────────
# ADAPTIVE SCORING ENGINE - Sentence-BERT and TF-IDF + Grammar.
#
# Each round asks a compulsory "base" batch first (size randomized within
# a range so it varies session to session). Once the base batch is
# answered, the running average is checked against the round's threshold:
#   - Clears the threshold -> advance to the next round immediately.
#   - Falls short -> ask ONE more question, recheck the average, repeat
#     one at a time up to the round's extra-question cap.
#   - Still short once the extra cap is exhausted -> don't end the
#     interview. Switch into "fallback mode" for the rest of the session:
#     every remaining round gets a short, reduced-size batch with NO
#     threshold checking, and the interview winds down to the report.
#
# Hard has no round after it, so it never threshold-checks either way -
# it always just asks its batch (normal-size or fallback-size) and ends.
# ─────────────────────────────────────────────────────────────────
ADAPTIVE_EASY_BASE_RANGE = (5, 6)      # Compulsory Easy questions before first check
ADAPTIVE_EASY_THRESHOLD = 70            # Avg needed to advance Easy -> Medium
ADAPTIVE_EASY_EXTRA_MAX = 5             # Extra Easy questions (1-at-a-time) before falling back

ADAPTIVE_MEDIUM_BASE = 5                # Compulsory Medium questions before first check
ADAPTIVE_MEDIUM_THRESHOLD = 50          # Avg needed to advance Medium -> Hard
ADAPTIVE_MEDIUM_EXTRA_RANGE = (3, 4)    # Extra Medium questions (1-at-a-time) before falling back

ADAPTIVE_HARD_BASE_RANGE = (3, 4)       # Hard batch size on the normal (non-fallback) path

# Fallback batch sizes - used for whichever round(s) come after a round
# that exhausted its extras without clearing its threshold. No threshold
# checking applies to fallback batches; they're just asked and the
# interview moves on (or ends, if it's Hard).
FALLBACK_MEDIUM_RANGE = (2, 3)
FALLBACK_HARD_RANGE = (1, 2)

# Skips never provide enough evidence to finish a round by themselves.
# Replacement questions are added until these many questions have actual answers.
MIN_ANSWERED_PER_ROUND = {
    "Easy": 3,
    "Medium": 3,
    "Hard": 2,
}

# ─────────────────────────────────────────────────────────────────
# FIXED-CURRICULUM ENGINE - Siamese Bi-LSTM.
# The Bi-LSTM's scores aren't reliable enough to gate progression on
# (see feedback_generator.py), so it always asks a fixed number of
# random questions per round and moves straight through Easy -> Medium
# -> Hard -> end, regardless of score.
# ─────────────────────────────────────────────────────────────────
FIXED_EASY_COUNT = 5
FIXED_MEDIUM_COUNT = 4
FIXED_HARD_COUNT = 4

# Round Progression Order
ROUND_ORDER = ["Easy", "Medium", "Hard"]

# Round Colors for UI
ROUND_COLORS = {
    "Easy": "#4CAF50",
    "Medium": "#FF9800",
    "Hard": "#F44336"
}
