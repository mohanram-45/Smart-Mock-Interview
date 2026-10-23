"""Decision helpers. Status: KEEP / FIX / EXCLUDE. diff = proposed difficulty (E/M/H) by written rubric, reviewer judgement.
state (review_state): ready_for_approval | needs_review | needs_source | needs_code_test | n/a
conf: proposal confidence (high/medium/low). EVERY proposal awaits human approval; nothing is applied."""
D = {}
DN = {"E":"Easy","M":"Medium","H":"Hard"}
def _put(i, status, diff, flags, note, **kw):
    assert i not in D, f"duplicate decision {i}"
    D[i] = dict(status=status, pdiff=DN.get(diff,""), flags=[f for f in flags.split(";") if f], note=note, **kw)
def K(i, diff, flags="", note=""):
    _put(i,"KEEP",diff,flags,note)
def F(i, diff, flags, note, pq=None, pa=None, pd=None, trim=None, repl=None, state="needs_review", conf="medium", code=None):
    """trim=text marker: answer is cut before first occurrence (removes bleed). repl=[(old,new)] exact substring replacements."""
    _put(i,"FIX",diff,flags,note,pq=pq,pa=pa,pd=pd,trim=trim,repl=repl,state=state,conf=conf,code=code)
def X(i, flags, note, dup_of=None):
    _put(i,"EXCLUDE","",flags,note,dup_of=dup_of)
