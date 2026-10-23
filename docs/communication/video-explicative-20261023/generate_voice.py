from pathlib import Path
import sys,json,wave,time
sys.path.insert(0,'/workspace/13urgent-explication-20261023/tools')
import sherpa_onnx
root=Path('/workspace/13urgent-explication-20261023');prod=root/'production';model=prod/'vits-piper-fr_FR-siwis-medium'
scenes=[
('urgent','Un transport urgent à organiser autour de Marseille ?'),
('depot','Avec Treize Urgent, créez votre compte professionnel et déposez gratuitement votre demande.'),
('offres','Recevez des propositions confidentielles et choisissez votre transporteur.'),
('suivi','Suivez les étapes déclarées de votre course, depuis votre espace.'),
('frais',"À l’attribution commerciale confirmée : un virgule cinq pour cent du prix hors taxes du transport, TVA en supplément."),
('transporteurs',"Transporteur ? Choisissez votre forfait et transmettez vos documents. Proposez vos tarifs après validation du dossier et de vos droits d’accès."),
('contact','Treize Urgent. Votre urgence, notre priorité. Rendez-vous sur treize urgent point F R.')]
config=sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=str(model/'fr_FR-siwis-medium.onnx'),lexicon='',tokens=str(model/'tokens.txt'),data_dir=str(model/'espeak-ng-data')),num_threads=2,debug=False,provider='cpu'),max_num_sentences=1)
tts=sherpa_onnx.OfflineTts(config);result=[]
import numpy as np
for name,text in scenes:
 audio=tts.generate(text,sid=0,speed=1.1)
 path=prod/(name+'.wav');samples=np.clip(np.asarray(audio.samples)*32767,-32768,32767).astype('<i2')
 with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(audio.sample_rate);w.writeframes(samples.tobytes())
 result.append(dict(name=name,text=text,duration=len(samples)/audio.sample_rate));print(name,round(result[-1]['duration'],2),flush=True)
(prod/'narration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
