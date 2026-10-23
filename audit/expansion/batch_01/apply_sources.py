import json,copy
W="/home/claude/work/proj/data/expansion/batch_01/work/"
recs={g['plan_id']:g for g in json.load(open(W+"corrected.json"))}
order=list(recs)
fin={};ver={}
for n in range(4):
    for r in json.load(open(f"rs_out_{n}.json")): fin[r['plan_id']]=r
for n in range(3):
    for v in json.load(open(f"sv_out_{n}.json")): ver[v['entry_id']]=v
LEAD={"https://github.com/facebookresearch/faiss/wiki/Faiss-indexes","https://qdrant.tech/articles/filterable-hnsw/","https://arxiv.org/pdf/2306.05685","https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/","https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion","https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html","https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index","https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf","https://arxiv.org/abs/2210.11934","https://arxiv.org/abs/2307.03172","https://arxiv.org/abs/2212.10496"}
log=[];skipped=[]
def fix(g,f,claim,rep,origin):
    t=g.get(f)
    if t is None or t.count(claim)!=1: skipped.append((g['plan_id'],f,claim[:70],origin)); return
    g[f]=t.replace(claim,rep); log.append((g['plan_id'],f,claim,rep,origin))
for pid,g in recs.items():
    r=fin.get(pid)
    for x in (r['fixes'] if r else []): fix(g,x['field'],x['claim'],x['replacement'],'source_finder')
for pid,g in recs.items():
    for eid,v in ver.items():
        if eid.split('#')[0]==pid:
            for x in v.get('fixes') or []: fix(g,x['field'],x['claim'],x['replacement'],'source_verifier')
srcs={}
for pid,g in recs.items():
    r=fin.get(pid); out=[]
    for i,s in enumerate(r['sources'] if r else []):
        v=ver[f"{pid}#{i}"]
        if v['verdict'] not in('supported','partial'): continue
        lead=s['url'] in LEAD
        st=("lead_opened_" if lead else "independent_reviewer_")+("supported" if v['verdict']=='supported' else "partially")
        sup=s['supports'] if v['verdict']=='supported' else (v.get('narrowed_supports') or s['supports'])
        out.append({"title":s['title'],"url":s['url'],"supports":sup,"status":st,"source_type":s['type']})
    srcs[pid]=out
json.dump([recs[p] for p in order],open("corrected_3.json","w"),indent=1)
json.dump(srcs,open("lead_sources_v2.json","w"),indent=1)
json.dump({"applied":log,"skipped":skipped},open("source_fixes_log.json","w"),indent=1)
n_any=sum(bool(v) for v in srcs.values()); n_full=sum(any(s['status'].endswith('supported') for s in v) for v in srcs.values())
print(len(log),"applied;",len(skipped),"skipped",skipped); print("records with any source",n_any,"with >=1 fully supporting",n_full,"of",len(srcs))
