from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ClientNodeStatus import ConnectionMachine, EstablishedProxyPort, DisconnectState

connection_machine_instance = ConnectionMachine()

import os

# 환경 변수 설정
os.environ['SERVER_CONTROL_API_PORT'] = "58000"
os.environ["SERVER_SSH_USER"] = ""
os.environ["SERVER_SSH_USER_PASSWORD"] = ""

client_node_app = FastAPI()


class ConnectRequestModel(BaseModel):
    server_host: str
    server_port: int
    node_name: str
    node_password: str

class ConnectResponseModel(BaseModel):
    server_host: Optional[str]
    server_port: Optional[int]
    node_name: Optional[str]
    node_password: Optional[str]



class MessageModel(BaseModel):
    message: str


@client_node_app.post("/node/info", response_model=MessageModel)
async def post_node_info(connect_request_model: ConnectRequestModel, background_tasks: BackgroundTasks):
    global connection_machine_instance
    # 진행 조건
    connection_machine_instance.server_host = connect_request_model.server_host
    connection_machine_instance.server_port = connect_request_model.server_port
    connection_machine_instance.node_name = connect_request_model.node_name
    connection_machine_instance.node_password = connect_request_model.node_password
    connection_machine_instance.background_tasks = background_tasks

    return {
        "message": "Submit a connect request"
    }

@client_node_app.get("/node/info", response_model=ConnectResponseModel)
async def get_node_info():
    return {
        "server_host": connection_machine_instance.server_host,
        "server_port": connection_machine_instance.server_port,
        "node_name": connection_machine_instance.node_name,
        "node_password": connection_machine_instance.node_password,
    }

@client_node_app.post("/connction/proceed", response_model=MessageModel)
async def post_connection_proceed(background_tasks: BackgroundTasks):
    connection_machine_instance.background_tasks = background_tasks
    background_tasks.add_task(connection_machine_instance.proceed)
    return {
        "message": "Connection Proceed"
    }

@client_node_app.get("/connction/status", response_model=MessageModel)
async def get_connection_status():
    return {
        "message": connection_machine_instance.get_state_name()
    }

# DISconnect 기능 추가

@client_node_app.post("/connection/back", response_model=MessageModel)
async def disconnect_server_node():
    await connection_machine_instance.turn_back()
    return {
        "message": "Submit a disconnect request"
    }



if __name__ == '__main__':
    uvicorn.run(client_node_app, host='0.0.0.0', port=58001)
