import subprocess,sys,os,json,tempfile
from load_all import D
res={}
env=dict(os.environ,PYTHONPATH="/home/claude/work/triage/_libs",MPLBACKEND="Agg")
for i,v in sorted(D.items()):
    c=v.get('code')
    if not c: continue
    with tempfile.NamedTemporaryFile('w',suffix='.py',delete=False,dir='/tmp') as f: f.write(c); p=f.name
    r=subprocess.run([sys.executable,'-I',p],capture_output=True,text=True,timeout=60,env=env)
    # -I ignores PYTHONPATH; use without -I for nltk
    if r.returncode!=0 and 'nltk' in c:
        r=subprocess.run([sys.executable,p],capture_output=True,text=True,timeout=60,env=env)
    res[i]=dict(rc=r.returncode,out=(r.stdout or '')[-300:],err=(r.stderr or '')[-300:])
    print(i,'PASS' if r.returncode==0 else 'FAIL',r.stdout.strip()[:120],r.stderr.strip()[-150:])
json.dump(res,open('code_test_results.json','w'),indent=1)
