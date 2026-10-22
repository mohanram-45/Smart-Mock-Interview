import json,subprocess,sys,tempfile,os
R=os.path.dirname(os.path.abspath(__file__))+'/../..'
PY={'3.13':'/home/claude/work/dep/v/bin/python','3.10':'/home/claude/work/v310/bin/python','3.11':'/home/claude/work/v311/bin/python'}
res={}
for n in range(1,5):
    t=json.load(open(f'{R}/data/expansion/batch_0{n}/code_tests.json'))
    for rid,c in t.items():
        if c.get('language')!='python': res[rid]={'skipped':c.get('language')}; continue
        src=(c.get('setup') or '')+'\n'+c['solution']+'\n'+c['test']+'\n'
        r={}
        for v,p in PY.items():
            with tempfile.TemporaryDirectory() as d:
                f=d+'/t.py'; open(f,'w').write(src)
                try:
                    q=subprocess.run([p,'-I',f],capture_output=True,text=True,timeout=120,cwd=d)
                    r[v]=q.returncode==0 or q.stderr[-200:]
                except Exception as e: r[v]=str(e)[:100]
        res[rid]=r
json.dump(res,open(f'{R}/reports/code_test_rerun.json','w'),indent=1)
bad={k:v for k,v in res.items() if not all(x is True for x in v.values())}
print(len(res),'tests; failures:',bad)
