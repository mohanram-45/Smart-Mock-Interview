import importlib
from dec_helpers import D
MODS=['dec_01_da_dl_a','dec_02_dl_b','dec_03_dl_c','dec_04_ml_a','dec_05_ml_b','dec_06_ml_c','dec_07_ml_d','dec_08_ml_nlp','dec_09_pm','dec_10_sql','dec_11_py']
for m in MODS: importlib.import_module(m)
