import unittest
from client.ClientNodeStatus import ConnectionMachine

class TestConnectionMachine(unittest.TestCase):

    def test_connection_machine_state_transition(self):
        # 상태 머신 인스턴스를 생성합니다.
        connection_machine = ConnectionMachine()

        # 초기 상태는 DisconnectState이어야 합니다.
        self.assertEqual(connection_machine.get_state_name(), "Disconnect")

        # 상태 전이 과정을 진행합니다.
        connection_machine.proceed()  # RequestConnectReverseSSHPort로 전이
        self.assertEqual(connection_machine.get_state_name(), "RequestConnectReverseSSHPort")

        connection_machine.proceed()  # EstablishedReverseSSHPort로 전이
        self.assertEqual(connection_machine.get_state_name(), "EstablishedReverseSSHPort")

        connection_machine.proceed()  # RequestConnectProxyPort로 전이
        self.assertEqual(connection_machine.get_state_name(), "RequestConnectProxyPort")

        connection_machine.proceed()  # EstablishedProxyPort로 전이
        self.assertEqual(connection_machine.get_state_name(), "EstablishedProxyPort")

        connection_machine.proceed()  # EstablishedProxyPort로 계속 머무름
        self.assertEqual(connection_machine.get_state_name(), "EstablishedProxyPort")

if __name__ == "__main__":
    unittest.main()
