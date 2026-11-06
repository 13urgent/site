#!/usr/bin/env python3
"""Read-only Buffer connection test. Never print tokens, emails or raw replies."""
import json, os, sys, urllib.request, urllib.error

def query(text):
    key=os.environ.get("BUFFER_API_KEY", "").strip()
    if not key: raise RuntimeError("BUFFER_API_KEY_missing")
    request=urllib.request.Request("https://api.buffer.com",data=json.dumps({"query":text}).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json","User-Agent":"13URGENT-marketing/1.0"},method="POST")
    try:
        with urllib.request.urlopen(request,timeout=30) as response:
            result=json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError("Buffer_HTTP_"+str(error.code)) from None
    except Exception:
        raise RuntimeError("Buffer_network_or_invalid_response") from None
    if result.get("errors") or not isinstance(result.get("data"),dict):
        raise RuntimeError("Buffer_GraphQL_error")
    return result["data"]

def main():
    organizations=query("query { account { organizations { id name } } }")["account"]["organizations"]
    channels=[]
    for org in organizations:
        channels.extend(query("query { channels(input: { organizationId: "+json.dumps(org["id"])+" }) { id name service } }")["channels"])
    public={"connection_ok":True,"read_only":True,"sent_posts":0}
    print(json.dumps(public,ensure_ascii=False,indent=2))
    summary=os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a") as f:f.write("# Connexion Buffer : lecture seule\n\n```json\n"+json.dumps(public,ensure_ascii=False,indent=2)+"\n```\n")
    return public

if __name__=="__main__":
    try:main()
    except Exception as error:
        safe=str(error) if isinstance(error,RuntimeError) else "invalid_Buffer_schema"
        print("Connection failed: "+safe,file=sys.stderr)
        sys.exit(1)
