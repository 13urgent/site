'use strict';
(()=>{
 const zone='Europe/Paris';
 const parts=value=>Object.fromEntries(new Intl.DateTimeFormat('sv-SE',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(new Date(value)).filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));
 function input(value){if(!value||!Number.isFinite(new Date(value).getTime()))return '';const p=parts(value);return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}:${p.second}`;}
 function parse(value){
  const m=/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(String(value));
  if(!m)throw Error('Renseignez une date et une heure valides.');
  const [y,mo,d,h,mi,se]=m.slice(1).map(Number);const utc=Date.UTC(y,mo-1,d,h,mi,se||0);const normalized=String(value).length===16?value+':00':value;
  const offsets=new Set([-86400000,0,86400000].map(delta=>{const p=parts(utc+delta);return Date.UTC(+p.year,+p.month-1,+p.day,+p.hour,+p.minute,+p.second)-(utc+delta);}));
  const matches=[...offsets].map(o=>utc-o).filter(t=>input(t)===normalized);
  if(matches.length!==1)throw Error(matches.length?'Cette heure apparaît deux fois lors du changement d’heure à Paris. Choisissez un horaire sans ambiguïté.':'Cet horaire n’existe pas à Paris. Vérifiez la date et le changement d’heure.');
  return new Date(matches[0]).toISOString();
 }
 function format(value){return value&&Number.isFinite(new Date(value).getTime())?new Intl.DateTimeFormat('fr-FR',{timeZone:zone,dateStyle:'short',timeStyle:'short'}).format(new Date(value)):'Non renseignée';}
 function append(parent,shipment){const box=document.createElement('div');box.className='shipment-schedule';for(const[label,value]of[['Départ prévu',shipment.pickup],['Arrivée prévue',shipment.delivery_at]]){const p=document.createElement('p');const strong=document.createElement('strong');strong.textContent=label+' : ';p.append(strong,document.createTextNode(format(value)));box.append(p);}const note=document.createElement('small');note.textContent='Horaires prévus · heure de Paris';box.append(note);parent.append(box);}
 window.urgentShipmentSchedule=Object.freeze({input,parse,format,append});
})();
