import uvicorn
from fastapi import FastAPI, APIRouter

server_node_app = FastAPI()

server_node_app_client_node_router = APIRouter(prefix="/nodes", tags=["Node"])

nodes_space = {
    "sample-node": {
        "node-name": "sample-node",
        "node-password": "abcd"
    }
}

service_space = {
    "sample-service": {
        "node-name": "sample-node",
        "node-service-name": "sample-service",
        "node-service-port": 58002
    }
}

# server 연동
# server의 node 등록 정보
# 노드를 등록할 수 있도록 제공한다. 이때 그냥 가지고 있고 등록할 수 있도록ㄷ 하는 형태로 한다.
@server_node_app_client_node_router.get("")
async def nodes():
    global nodes_space
    return nodes_space


server_node_app_client_service_router = APIRouter(prefix="/services", tags=["Node"])
# server 연동
# server의 node의 서비스, 포트 등록 정보
@server_node_app_client_service_router.get("")
async def nodes_services():
    global nodes_space
    return service_space

server_node_app_service_api = APIRouter(prefix="/api", tags=["Service API"])

@server_node_app_service_api.get("/{service_name}/{service_api_path}")
async def services(service_name: str, service_api_path: str):
    

    pass

server_node_app.include_router(server_node_app_client_node_router)
server_node_app.include_router(server_node_app_client_service_router)

if __name__ == '__main__':
    uvicorn.run(server_node_app, host='0.0.0.0', port=58000)
