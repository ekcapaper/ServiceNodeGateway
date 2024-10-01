import uvicorn
from fastapi import FastAPI, APIRouter

client_node_app = FastAPI()

# 로그인 시에 변경될 내용
server_ip = "127.0.0.1"
server_port = 58000

# 이 부분은 로그인 시에 변경될 내용
service_name = "sample-node"
service_password = "abcd"

client_node_app_client_node_router = APIRouter(prefix="/nodes", tags=["Node"])

# server 연동
# server의 node 등록 정보
# 노드를 등록할 수 있도록 제공한다. 이때 그냥 가지고 있고 등록할 수 있도록ㄷ 하는 형태로 한다.
@client_node_app_client_node_router.get("")
async def nodes():
    return {"message": "Hello World"}

# server 연동
# server의 node의 서비스, 포트 등록 정보
@client_node_app_client_node_router.post("/services")
async def nodes_services():
    return {"message": "Hello World"}

# server 연동
# server의 node에서 샘플 코드를 보여준다.
# 포트를 그대로 사용하는 것으로 오해할 수 있으므로 이 부분을 확실하게 이렇게 호출하라는 것으로 명시적으로 보여준다.
# 사실 처음에 구상할 때에는 포트를 그대로 제공해서 하는 방식으로도 생각을 했지만 이 경우에는 서버측의 포트인지 클라이언트의 포트인지가 혼란스러워서
# API 게이트웨이 하나를 두고 여기에서 등록된 노드들의 API를 호출해주는 식으로 변경

# server 연동
# 정보 보여주기

# 프론트측에서 처리해도 될 내용이지만 ssh로 연결하는 부분을 처리하기 위해서 별도의 웹 서버로 뺀 부분

client_node_app.include_router(client_node_app_client_node_router)

if __name__ == '__main__':
    uvicorn.run(client_node_app, host='0.0.0.0', port=58001)
