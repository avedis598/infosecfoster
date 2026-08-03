import re

with open("aml_siem/steps/m2_automation.py", "r") as f:
    content = f.read()

dummy_cmd = """"KUBECONFIG=~/.kube/config kubectl create secret generic thehive-api-key --from-literal=api-key='aml-siem-mock-key-12345' -n aml-lab --dry-run=client -o yaml | KUBECONFIG=~/.kube/config kubectl apply -f -\""""

automated_cmd = '"""cat << \\\'EOF\\\' > /tmp/get_thehive_key.py\n' \
'import urllib.request, urllib.error, json\n' \
'url = "http://thehive.aml-lab.svc.cluster.local:9000/api/v1/login"\n' \
'req = urllib.request.Request(url, data=json.dumps({"user": "admin@thehive.local", "password": "secret"}).encode(), headers={"Content-Type": "application/json"}, method="POST")\n' \
'cookie = urllib.request.urlopen(req).headers.get("Set-Cookie").split(";")[0]\n' \
'req_me = urllib.request.Request("http://thehive.aml-lab.svc.cluster.local:9000/api/v1/user/current", headers={"Cookie": cookie})\n' \
'user_id = json.loads(urllib.request.urlopen(req_me).read())["_id"]\n' \
'url2 = f"http://thehive.aml-lab.svc.cluster.local:9000/api/v1/user/{user_id}/key/renew"\n' \
'req2 = urllib.request.Request(url2, headers={"Cookie": cookie, "Content-Type": "application/json"}, method="POST")\n' \
'print(urllib.request.urlopen(req2).read().decode())\n' \
'EOF\n' \
'KEY=$(KUBECONFIG=~/.kube/config kubectl run -i --rm thehive-keygen-$RANDOM --image=python:3.9-slim --restart=Never -n aml-lab -- sh -c "cat > /tmp/get_key.py && python /tmp/get_key.py" < /tmp/get_thehive_key.py | tail -n 1)\n' \
'if [ -z "$KEY" ] || [[ "$KEY" == *"Error"* ]]; then echo "Failed to generate key: $KEY"; exit 1; fi\n' \
'KUBECONFIG=~/.kube/config kubectl create secret generic thehive-api-key --from-literal=api-key="$KEY" -n aml-lab --dry-run=client -o yaml | KUBECONFIG=~/.kube/config kubectl apply -f -"""'

content = content.replace(dummy_cmd, automated_cmd)

with open("aml_siem/steps/m2_automation.py", "w") as f:
    f.write(content)
