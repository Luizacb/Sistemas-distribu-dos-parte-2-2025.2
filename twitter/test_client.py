import requests
import time

BASES = [
    "http://localhost:8080",
    "http://localhost:8081",
    "http://localhost:8082",
]

def send_post(processId, evtId, author, text, parentEvtId=None):
    body = {
        "processId": processId,
        "evtId": evtId,
        "author": author,
        "text": text,
    }
    if parentEvtId:
        body["parentEvtId"] = parentEvtId

    url = f"{BASES[processId]}/post"
    r = requests.post(url, json=body)
    print(f"{author} -> {text} (evtId={evtId}, parent={parentEvtId})")

if __name__ == "__main__":
    # 1. Enviar reply ANTES do post pai (vai para o buffer)
    send_post(1, "r1", "João", "Legal!", parentEvtId="p1")

    time.sleep(1)

    # 2. Agora enviar o post pai
    send_post(0, "p1", "Maria", "Meu primeiro post!")

    time.sleep(1)

    # 3. Outro reply depois do post
    send_post(2, "r2", "Ana", "Concordo!", parentEvtId="p1")
