import os
import sys
import time

os.environ.setdefault("ROBOT_TYPE", "PF_TRON1A")

import limxsdk.datatypes as datatypes
import limxsdk.robot.Robot as Robot
import limxsdk.robot.RobotType as RobotType


def main():
    robot_ip = sys.argv[1] if len(sys.argv) > 1 else "10.192.1.2"

    robot = Robot(RobotType.PointFoot)
    if not robot.init(robot_ip):
        print(f"Failed to connect to robot at {robot_ip}")
        return 1

    print("STATIC_RED:", robot.setRobotLightEffect(datatypes.LightEffect.STATIC_RED))
    time.sleep(2)
    print("FAST_FLASH_YELLOW:", robot.setRobotLightEffect(datatypes.LightEffect.FAST_FLASH_YELLOW))
    time.sleep(2)
    print("STATIC_GREEN:", robot.setRobotLightEffect(datatypes.LightEffect.STATIC_GREEN))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
