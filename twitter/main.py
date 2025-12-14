from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
from collections import defaultdict
import threading
import time
import sys
import uvicorn
import requests

app = FastAPI()

# ------------------------------------------------------------
# Estado global
# ------------------------------------------------------------
myProcessId = 0
numProcesses = 3
vectorClock = [0] * numProcesses
posts = defaultdict(list)
replies = defaultdict(list)
buffer = []  # mensagens pendentes

processes = [
    "localhost:8080",
    "localhost:8081",
    "localhost:8082",
]

# ------------------------------------------------------------
# Modelo de evento
# ------------------------------------------------------------
class Event(BaseModel):
    processId: int
    evtId: str
    parentEvtId: Optional[str] = None
    author: str
    text: str
    timestamp: Optional[List[int]] = None  # vetor lógico

# ------------------------------------------------------------
# Funções de relógio
# ------------------------------------------------------------
def incrementClock():
    vectorClock[myProcessId] += 1

def updateClock(receivedVC):
    global vectorClock
    for i in range(numProcesses):
        vectorClock[i] = max(vectorClock[i], receivedVC[i])

def canDeliver(msg: Event):
    VCm = msg.timestamp
    p = msg.processId
    # Condição de entrega causal
    for i in range(numProcesses):
        if i == p:
            if VCm[i] != vectorClock[i] + 1:
                return False
        else:
            if VCm[i] > vectorClock[i]:
                return False
    return True

def tryDeliver():
    delivered = True
    while delivered:
        delivered = False
        for msg in buffer[:]:
            if canDeliver(msg):
                buffer.remove(msg)
                deliver(msg)
                delivered = True

def deliver(msg: Event):
    if msg.parentEvtId is None:
        posts[msg.evtId].append(msg)
    else:
        replies[msg.parentEvtId].append(msg)
    updateClock(msg.timestamp)
    showFeed()

# ------------------------------------------------------------
# Endpoints HTTP
# ------------------------------------------------------------
@app.post("/post")
def post(msg: Event):
    incrementClock()
    msg.timestamp = vectorClock.copy()
    deliver(msg)
    for i, proc in enumerate(processes):
        if i != myProcessId:
            async_send(f"http://{proc}/share", msg.dict())
    return {"status": "ok", "msg": msg.dict()}

@app.post("/share")
def share(msg: Event):
    if canDeliver(msg):
        deliver(msg)
        tryDeliver()
    else:
        buffer.append(msg)
    return {"status": "received"}

# ------------------------------------------------------------
# Funções auxiliares
# ------------------------------------------------------------
def async_send(url: str, payload: dict):
    def worker():
        try:
            requests.post(url, json=payload, timeout=2)
        except Exception as e:
            print(f"[ERRO] Falha ao enviar para {url}: {e}")
    threading.Thread(target=worker).start()

def showFeed():
    print("\n=== FEED LOCAL ===")
    for postId, postList in posts.items():
        for p in postList:
            print(f"[POST] {p.author} {p.timestamp}: {p.text}")
            if postId in replies:
                for r in replies[postId]:
                    print(f"   ↳ [REPLY] {r.author}: {r.text}")
    print("==================\n")

# ------------------------------------------------------------
# Inicialização
# ------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python main.py <processId>")
        sys.exit(1)

    myProcessId = int(sys.argv[1])
    host, port = processes[myProcessId].split(":")
    uvicorn.run("main:app", host=host, port=int(port), reload=False)
