"""Read only the Buffer mutation schema needed to pause approved TikTok scheduling."""
import importlib.util,json,os
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('buffer_inspect',root/'marketing/publisher/buffer_publish.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def unwrap(value):
    while isinstance(value,dict) and value.get('ofType'):value=value['ofType']
    return value.get('name') if isinstance(value,dict) else None

def main():
    client=module.BufferClient(os.environ.get('BUFFER_API_KEY'))
    fields=client.query('query { __type(name:"Mutation") { fields { name args { name type { kind name ofType { kind name ofType { kind name } } } } type { kind name ofType { kind name } } } } }')['__type']['fields']
    selected=[f for f in fields if any(word in f['name'].lower() for word in ('pause','updatepost','editpost','draft','updatechannel'))]
    inputs={}
    for field in selected:
        for arg in field['args']:
            name=unwrap(arg['type'])
            if not name or name in inputs:continue
            inputs[name]=client.query('query { __type(name:'+json.dumps(name)+') { kind name inputFields { name type { kind name ofType { kind name ofType { kind name } } } } fields { name type { kind name ofType { kind name } } } enumValues { name } } }')['__type']
    report={'mode':'read_only','posts_created':0,'posts_modified':0,'schema_mutations':selected,'input_types':inputs}
    out=root/'.runtime/tiktok-control-schema.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':'schema_read_only_complete','posts_modified':0,'mutation_names':[f['name'] for f in selected]}))
if __name__=='__main__':
    try:main()
    except Exception:print(json.dumps({'status':'schema_inspection_unavailable','posts_modified':0}));sys.exit(2)
