import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from hospital_interfaces.srv import ObjectTarget

class GetKeywordClient(Node):
    def __init__(self):
        super().__init__('get_keyword_client')
        self.cli = self.create_client(ObjectTarget, '/get_keyword')

        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('서비스를 기다리는 중: get_keyword...')

        self.req = ObjectTarget.Request()

    def send_request(self):
        self.future = self.cli.call_async(self.req)


def main():
    rclpy.init()

    client = GetKeywordClient()
    client.send_request()

    rclpy.spin_until_future_complete(client, client.future)

    if client.future.result() is not None:
        response = client.future.result()
        print(f"\n🟢 [응답 성공 여부]: {response.success}")
        print(f"📝 [응답 메시지]: {response.object}, {response.target}")
        print(f'suction 여부:{response.commands}')
    else:
        client.get_logger().error('서비스 호출 실패!')

    client.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
