import asyncio
from typing import Optional

import asyncssh
import httpx
import uvicorn
from fastapi import FastAPI, BackgroundTasks
from peewee import SqliteDatabase, Model, CharField, IntegerField, BooleanField
from pydantic import BaseModel
from fastapi import Request, Response
import os

os.environ["CLIENT_SSH_USER"] = ""
os.environ["CLIENT_SSH_USER_PASSWORD"] = ""

# DB
db = SqliteDatabase('nodes.db')

class PeeweeBaseModel(Model):
    class Meta:
        database = db

class Node(PeeweeBaseModel):
    node_name = CharField(max_length=255)
    node_password = CharField(max_length=255)
    route_port = IntegerField()
    connection_valid = BooleanField(default=False)
    proxy_port = IntegerField(null=True)

# 테이블 생성
db.connect()
db.create_tables([Node])

server_node_app = FastAPI()

class RequestAccountCheckModel(BaseModel):
    node_name: str
    node_password: str

class ResponseAccountCheckModel(BaseModel):
    valid: bool
class MessageModel(BaseModel):
    message: str
@server_node_app.post("/node/account/check")
async def post_node_account_valid(request_account_check_model: RequestAccountCheckModel):
    node_exists = Node.select().where(
        (Node.node_name == request_account_check_model) & (Node.node_password == request_account_check_model.node_password)
    ).exists()
    return {
        "valid": node_exists
    }

class RequestNodeAccount(BaseModel):
    node_name: str
    node_password: str
    route_port: int
@server_node_app.post("/node/account", response_model=MessageModel)
async def post_node_account(request_node_account: RequestNodeAccount):
    new_node = Node.create(
        node_name=request_node_account.node_name,
        node_password=request_node_account.node_password,
        route_port=request_node_account.route_port,
    )
    return {
        "message": "success"
    }

class ResponseNodeStatus(BaseModel):
    node_name: str
    route_port: int
    connection_valid: bool
    proxy_port: Optional[int]

@server_node_app.get("/node/check", response_model=ResponseNodeStatus)
def get_node_check(node_name: str):
    node_instance = Node.select().where(Node.node_name == node_name).get()
    return {
        "node_name": node_instance.node_name,
        "route_port": node_instance.route_port,
        "connection_valid": node_instance.connection_valid,
        "proxy_port": node_instance.proxy_port
    }

class RequestDisconnectModel(BaseModel):
    node_name: str
@server_node_app.post("/node/disconnect", response_model=MessageModel)
async def post_node_disconnect(request_disconnect_model: RequestDisconnectModel):
    Node.update(connection_valid=False).where(Node.node_name == request_disconnect_model.node_name).execute()
    return {
        "message": "request disconnect"
    }

# username과 패스워드는 node name, password로 바꾸기
async def create_reverse_ssh_tunnel(remote_ssh_port, proxy_port, node_name, node_password):
    # SSH 서버 정보
    remote_host = '127.0.0.1'
    local_socks_port = proxy_port


    async with asyncssh.connect(host=remote_host, port=remote_ssh_port, username=os.getenv('CLIENT_SSH_USER'), password=os.getenv('CLIENT_SSH_USER_PASSWORD'), known_hosts=None) as conn:
        # 리버스 포트 포워딩 설정
        ssh_listener = await conn.forward_socks("127.0.0.1", local_socks_port)
        Node.update(proxy_port=proxy_port).where(Node.node_name == node_name).execute()
        Node.update(connection_valid=True).where(Node.node_name == node_name).execute()

        print(f'SOCKS Established')
        # 연결 유지
        while True:
            node_instance = Node.select().where(Node.node_name == node_name).get()
            if not node_instance.connection_valid:
                break
            await asyncio.sleep(1)  # 1시간 대기
        ssh_listener.close()
        print("disconnect")


class RequestProxyModel(BaseModel):
    node_name: str
    node_password: str
    remote_ssh_port: int
    proxy_port: int

@server_node_app.post("/proxy/provide", response_model=MessageModel)
async def request_proxy(request_proxy_model: RequestProxyModel, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        create_reverse_ssh_tunnel,
        node_name=request_proxy_model.node_name,
        node_password=request_proxy_model.node_password,
        remote_ssh_port=request_proxy_model.remote_ssh_port,
        proxy_port=request_proxy_model.proxy_port
    )
    # 진행 메시지
    return {
        "message": "Submit a proxy request "+str(request_proxy_model.proxy_port)
    }

import socket
import random


class PortModel(BaseModel):
    port:int

@server_node_app.get("/port/random", response_model=PortModel)
def get_random_free_port():
    while True:
        port = random.randint(10000, 40000)  # 1024에서 65535 범위 내에서 랜덤 포트 선택
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return {
                    "port": port
                }# 포트가 사용 가능하면 반환
            except OSError:
                # 포트가 이미 사용 중이면 다음 랜덤 포트를 시도
                continue

@server_node_app.get("/route/{node_name}/{path:path}")
async def proxy_get(node_name:str, path: str, request: Request):
    node_instance = Node.select().where(Node.node_name == node_name).get()
    route_port = node_instance.route_port
    proxy_port = node_instance.proxy_port
    proxy_url = f"socks5://localhost:{proxy_port}"
    # 백엔드 API로 요청을 프록시 서버를 통해 전달
    async with httpx.AsyncClient(proxies=proxy_url) as client:
        # 원래 요청의 쿼리 파라미터 및 헤더를 백엔드로 전달
        query_params = request.query_params
        headers = dict(request.headers)
        backend_response = await client.get(f"http://localhost:{route_port}/{path}", params=query_params, headers=headers)

        return Response(
            content=backend_response.content,
            status_code=backend_response.status_code,
            headers=dict(backend_response.headers)
        )

@server_node_app.post("/route/{node_name}/{path:path}")
async def proxy_post(node_name:str, path: str, request: Request):
    node_instance = Node.select().where(Node.node_name == node_name).get()
    route_port = node_instance.route_port
    proxy_port = node_instance.proxy_port
    proxy_url = f"socks5://localhost:{proxy_port}"
    # 백엔드 API로 요청을 프록시 서버를 통해 전달
    async with httpx.AsyncClient(proxies=proxy_url) as client:
        # 원래 요청의 쿼리 파라미터 및 헤더를 백엔드로 전달
        query_params = request.query_params
        headers = dict(request.headers)
        # 요청 본문 읽기
        body = await request.body()

        # POST 요청을 백엔드로 전달
        backend_response = await client.post(
            url=f"http://localhost:{route_port}/{path}",
            headers=headers,
            params=query_params,
            content=body
        )

        return Response(
            content=backend_response.content,
            status_code=backend_response.status_code,
            headers=dict(backend_response.headers)
        )

# PATCH 요청을 처리하는 프록시 엔드포인트
@server_node_app.patch("/route/{node_name}/{path:path}")
async def proxy_patch(node_name: str, path: str, request: Request):
    # 데이터베이스에서 노드 정보 가져오기
    node_instance = Node.select().where(Node.node_name == node_name).get()
    route_port = node_instance.route_port
    proxy_port = node_instance.proxy_port
    proxy_url = f"socks5://localhost:{proxy_port}"

    # 프록시 서버를 통해 PATCH 요청 전송
    async with httpx.AsyncClient(proxies=proxy_url) as client:
        query_params = request.query_params
        headers = dict(request.headers)
        body = await request.body()

        backend_response = await client.patch(
            url=f"http://localhost:{route_port}/{path}",
            headers=headers,
            params=query_params,
            content=body
        )

        return Response(
            content=backend_response.content,
            status_code=backend_response.status_code,
            headers=dict(backend_response.headers)
        )

# DELETE 요청을 처리하는 프록시 엔드포인트
@server_node_app.delete("/route/{node_name}/{path:path}")
async def proxy_delete(node_name: str, path: str, request: Request):
    # 데이터베이스에서 노드 정보 가져오기
    node_instance = Node.select().where(Node.node_name == node_name).get()
    route_port = node_instance.route_port
    proxy_port = node_instance.proxy_port
    proxy_url = f"socks5://localhost:{proxy_port}"

    # 프록시 서버를 통해 DELETE 요청 전송
    async with httpx.AsyncClient(proxies=proxy_url) as client:
        query_params = request.query_params
        headers = dict(request.headers)

        backend_response = await client.delete(
            url=f"http://localhost:{route_port}/{path}",
            headers=headers,
            params=query_params
        )

        return Response(
            content=backend_response.content,
            status_code=backend_response.status_code,
            headers=dict(backend_response.headers)
        )
if __name__ == '__main__':
    uvicorn.run(server_node_app, host='0.0.0.0', port=58000)
