import asyncio
import os
import time
from abc import ABC, abstractmethod

import asyncssh
import httpx

class ProceedException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class TurnBackException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class ConnectionState(ABC):
    @abstractmethod
    def get_state_name(self):
        pass

    @abstractmethod
    def get_level(self):
        pass

    @abstractmethod
    async def proceed(self, context):
        pass

    @abstractmethod
    async def turn_back(self, context):
        pass


# 0
class DisconnectState(ConnectionState):
    def get_state_name(self):
        return "Disconnect"

    def get_level(self):
        return 0

    async def proceed(self, context):
        context.state = RequestConnectReverseSSHPort()

    async def turn_back(self, context):
        context.state = DisconnectState()


# 1
async def create_reverse_ssh_tunnel(
        context,
        server_host: str,
        server_port: int,
        node_name: str,
        node_password: str
):
    async with httpx.AsyncClient() as client:
        url = f"http://{context.server_host}:{os.getenv('SERVER_CONTROL_API_PORT')}/port/random"
        response = await client.get(url)
        # error
        if response.status_code != 200:
            raise ProceedException("Failed port random")
        remote_port = response.json()["port"]
        context.remote_ssh_port = remote_port

    local_port = int(os.getenv('LOCAL_SSH_PORT'))
    async with asyncssh.connect(
            host=server_host,
            port=server_port,
            username=os.getenv('SERVER_SSH_USER'),
            password=os.getenv('SERVER_SSH_USER_PASSWORD'),
            known_hosts=None
    ) as conn:
        # 리버스 포트 포워딩 설정
        ssh_listener = await conn.forward_remote_port("127.0.0.1", remote_port, "127.0.0.1", local_port)
        context.state = EstablishedReverseSSHPort()

        # 연결 유지
        while True:
            if context.state.get_level() <= 1:
                break
            await asyncio.sleep(1)
        ssh_listener.close()


class RequestConnectReverseSSHPort(ConnectionState):
    def get_state_name(self):
        return "RequestConnectReverseSSHPort"

    def get_level(self):
        return 1

    async def proceed(self, context):
        # account check
        async with httpx.AsyncClient() as client:
            url = f"http://{context.server_host}:{os.getenv('SERVER_CONTROL_API_PORT')}/node/account/check"
            response = await client.post(url, json={
                "node_name": context.node_name,
                "node_password": context.node_password
            })
            if response.status_code != 200:
                return

        context.background_tasks.add_task(
            create_reverse_ssh_tunnel,
            context=context,
            server_host=context.server_host,
            server_port=context.server_port,
            node_name=context.node_name,
            node_password=context.node_password
        )



    async def turn_back(self, context):
        context.state = DisconnectState()

# 2
class EstablishedReverseSSHPort(ConnectionState):
    def get_state_name(self):
        return "EstablishedReverseSSHPort"

    def get_level(self):
        return 2

    async def proceed(self, context):
        context.state = RequestConnectProxyPort()

    async def turn_back(self, context):
        context.state = RequestConnectReverseSSHPort()



# 3
class RequestConnectProxyPort(ConnectionState):
    def get_state_name(self):
        return "RequestConnectProxyPort"

    def get_level(self):
        return 3

    async def proceed(self, context):
        async with httpx.AsyncClient() as client:
            url = f"http://{context.server_host}:{os.getenv('SERVER_CONTROL_API_PORT')}/port/random"
            response = await client.get(url)
            proxy_port = response.json()["port"]
            if response.status_code != 200:
                raise ProceedException("Failed port random")

            url = f"http://{context.server_host}:{os.getenv('SERVER_CONTROL_API_PORT')}/proxy/provide"
            data = {
                "node_name": context.node_name,
                "node_password": context.node_password,
                "remote_ssh_port": int(context.remote_ssh_port),
                "proxy_port": int(proxy_port)
            }
            response = await client.post(url, json=data)
            if response.status_code != 200:
                raise ProceedException("Failed proxy")

            context.proxy_port = proxy_port
        context.state = EstablishedProxyPort()

    async def turn_back(self, context):
        context.state = EstablishedReverseSSHPort()


# 4
class EstablishedProxyPort(ConnectionState):
    def get_state_name(self):
        return "EstablishedProxyPort"

    def get_level(self):
        return 4

    async def proceed(self, context):
        context.state = EstablishedProxyPort()

    async def turn_back(self, context):
        async with httpx.AsyncClient() as client:
            url = f"http://{context.server_host}:{os.getenv('SERVER_CONTROL_API_PORT')}/node/disconnect"
            response = await client.post(url, json={
                "node_name": context.node_name,
            })
            if response.status_code != 200:
                raise TurnBackException("Failed disconnect")

        context.state = RequestConnectProxyPort()



# context에 변수 저장
# 종료시에도 변수 초기화를 역으로 들어가면서 제어
class ConnectionMachine:
    def __init__(self):
        self.__state = DisconnectState()
        self.__background_tasks = None

        self.__server_host = None
        self.__server_port = None
        self.__node_name = None
        self.__node_password = None

        self.__remote_ssh_port = None
        self.__proxy_port = None

    @property
    def proxy_port(self):
        return self.__proxy_port

    @proxy_port.setter
    def proxy_port(self, value):
        self.__proxy_port = value

    @property
    def remote_ssh_port(self):
        return self.__remote_ssh_port

    @remote_ssh_port.setter
    def remote_ssh_port(self, value):
        self.__remote_ssh_port = value

    @property
    def server_host(self):
        return self.__server_host

    @server_host.setter
    def server_host(self, server_host):
        self.__server_host = server_host

    @property
    def server_port(self):
        return self.__server_port

    @server_port.setter
    def server_port(self, server_port):
        self.__server_port = server_port

    @property
    def node_name(self):
        return self.__node_name

    @node_name.setter
    def node_name(self, node_name):
        self.__node_name = node_name

    @property
    def node_password(self):
        return self.__node_password

    @node_password.setter
    def node_password(self, node_password):
        self.__node_password = node_password

    @property
    def state(self):
        return self.__state

    @state.setter
    def state(self, state):
        self.__state = state

    def get_state_name(self):
        return self.__state.get_state_name()

    @property
    def background_tasks(self):
        return self.__background_tasks

    @background_tasks.setter
    def background_tasks(self, background_tasks):
        self.__background_tasks = background_tasks

    async def proceed(self):
        await self.__state.proceed(self)

    async def turn_back(self):
        await self.__state.turn_back(self)
