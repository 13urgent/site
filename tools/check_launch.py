"""Vérifications locales groupées. Aucun appel au projet Supabase réel."""
from pathlib import Path
import subprocess,os,json,concurrent.futures,sys,time
root=Path(__file__).resolve().parents[1]
checks=['admin-lockdown-sql.cjs','document-file-boundary-sql.cjs','registration-alerts-sql.cjs','registration-alerts-http.cjs','monthly-reports-sql.cjs','monthly-reports-http.cjs','business-registration.cjs','signup-compatibility.cjs','carrier-shipper-sql.cjs','manual-commerce-sql.cjs','marketplace-pilot-browser.cjs','manual-commerce-browser.cjs','document-review-browser.cjs','document-session-browser.cjs','external-drafts-browser.cjs','subscription-choice-browser.cjs','production-no-local-fallback.cjs']
env=dict(os.environ);env['NODE_PATH']='/workspace/13urgent-tools/node_modules:/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules'+(':'+env['NODE_PATH'] if env.get('NODE_PATH') else '')
def run(name):
 started=time.monotonic()
 try:
  result=subprocess.run(['node',str(root/'tests'/name)],cwd=root,env=env,capture_output=True,text=True,timeout=120)
  return {'test':name,'ok':result.returncode==0,'seconds':round(time.monotonic()-started,1),'output':(result.stdout+result.stderr).strip()}
 except subprocess.TimeoutExpired:return {'test':name,'ok':False,'output':'Délai de 120 secondes dépassé'}
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for item in pool.map(run,checks):
  results.append(item);print(('PASS' if item['ok'] else 'FAIL'),item['test'],flush=True)
  if not item['ok']:print(item['output'],flush=True)
report=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/workspace/13urgent-controle-lancement-20261023.json')
report.write_text(json.dumps(results,ensure_ascii=False,indent=2));print('Résultat',sum(r['ok'] for r in results),'/',len(results),'—',report)
sys.exit(0 if all(r['ok'] for r in results) else 1)
