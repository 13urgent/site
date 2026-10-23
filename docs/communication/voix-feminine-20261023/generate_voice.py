"""Génère la nouvelle narration ; ne publie rien sur les réseaux sociaux."""
from pathlib import Path
import asyncio,os,json,subprocess
import edge_tts
import edge_tts.communicate as com
# Ajouter l'autorité de certification fournie par la plateforme sans désactiver TLS.
if os.environ.get('SSL_CERT_FILE'):com._SSL_CTX.load_verify_locations(cafile=os.environ['SSL_CERT_FILE'])
root=Path('/workspace/13urgent-social-voix-naturelle-20261023');p=root/'production';p.mkdir(parents=True,exist_ok=True)
scenes=[('urgence','Un transport urgent à organiser autour de Marseille ?'),('demande','Avec Treize Urgent, déposez gratuitement votre demande professionnelle.'),('compare','Comparez les propositions confidentielles et choisissez votre transporteur.'),('frais','À l’attribution confirmée : un virgule cinq pour cent du prix hors taxes du transport, plus TVA.'),('contact','Votre prochaine demande commence sur treize urgent point F R.')]
async def main():
 results=[]
 for name,text in scenes:
  narration=edge_tts.Communicate(text,voice='fr-FR-VivienneMultilingualNeural',rate='-3%',pitch='-1Hz',proxy=os.environ.get('HTTPS_PROXY'),receive_timeout=30,boundary='WordBoundary')
  file=p/(name+'.mp3');await narration.save(str(file),str(p/(name+'-timings.jsonl')))
  duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(file)]))
  results.append({'name':name,'text':text,'duration':duration,'voice':'fr-FR-VivienneMultilingualNeural','rate':'-3%','pitch':'-1Hz'})
  print(name,duration,flush=True)
 (p/'narration.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
asyncio.run(main())
