import uvicorn
from fastapi import FastAPI, APIRouter

server_node_app = FastAPI()

server_node_app_client_node_router = APIRouter(prefix="/nodes", tags=["Node"])


nodes_space = {}


# server 연동
# server의 node 등록 정보
# 노드를 등록할 수 있도록 제공한다. 이때 그냥 가지고 있고 등록할 수 있도록ㄷ 하는 형태로 한다.
@server_node_app_client_node_router.get("")
async def nodes():
    return {"message": "Hello World"}

# server 연동
# server의 node의 서비스, 포트 등록 정보
@server_node_app_client_node_router.post("/services")
async def nodes_services():
    return {"message": "Hello World"}



server_node_app.include_router(server_node_app_client_node_router)

if __name__ == '__main__':
    uvicorn.run(server_node_app, host='0.0.0.0', port=58000)
