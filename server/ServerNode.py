import httpx
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
    # 포트 정보 뽑기
    service_info = service_space[service_name]
    # 어차피 나중에 프록시 서버를 열어서 제공할 에정
    # 따라서 127.0.0.1이 될 것이다.
    # 대신 포트는 프록시 서버를 통해서 어디로 갈지를 결정해야 하므로 필요한 부분이다.
    # 클라이언트 노드의 목적지 포트이다. 하나의 API에서 모든 것을 처리할 수 있도록 한다.
    # 나중에 어떻게 어떤 IP로 호출할 수 있는지에 대한 정보를 샘플로써 제공하고 openapi.json으로도 제공한다.
    # 자신의 127.0.0.1 에서 나중에 프록시를 켜서 넣는다.
    async with httpx.AsyncClient() as client:
        try:
            # 내부 API에 요청 보내기
            api_nodes = "http://" + "127.0.0.1" + ":" + str(service_space["node-service-port"])+"/"+service_api_path
            response = await client.get(f"{api_nodes}")
            # 응답이 성공적일 경우 그대로 반환
            return response.json()
        except httpx.RequestError as e:
            # 요청 에러 발생 시 오류 메시지 반환
            return {
                "status_code": 500,
                "error": str(e)
            }

server_node_app.include_router(server_node_app_client_node_router)
server_node_app.include_router(server_node_app_client_service_router)
server_node_app.include_router(server_node_app_service_api)

if __name__ == '__main__':
    uvicorn.run(server_node_app, host='0.0.0.0', port=58000)
