import os
import sys
import time

os.environ.setdefault("ROBOT_TYPE", "PF_TRON1A")

import limxsdk.datatypes as datatypes
import limxsdk.robot.Robot as Robot
import limxsdk.robot.RobotType as RobotType


class ImuPrinter:
    def __init__(self, interval_sec=0.5):
        self.interval_sec = interval_sec
        self.last_print = 0.0
        self.packet_count = 0

    def callback(self, imu: datatypes.ImuData):
        self.packet_count += 1
        now = time.time()
        if now - self.last_print < self.interval_sec:
            return
        self.last_print = now

        print(
            "\nIMU"
            + "\n  stamp: " + str(imu.stamp)
            + "\n  acc:   " + str(imu.acc)
            + "\n  gyro:  " + str(imu.gyro)
            + "\n  quat:  " + str(imu.quat),
            flush=True,
        )


class StatePrinter:
    def __init__(self, interval_sec=1.0):
        self.interval_sec = interval_sec
        self.last_print = 0.0
        self.packet_count = 0

    def callback(self, state: datatypes.RobotState):
        self.packet_count += 1
        now = time.time()
        if now - self.last_print < self.interval_sec:
            return
        self.last_print = now

        print(
            "\nRobotState"
            + "\n  stamp: " + str(state.stamp)
            + "\n  motors: " + str(state.motor_names)
            + "\n  q:      " + str(state.q),
            flush=True,
        )


class DiagnosticPrinter:
    def __init__(self):
        self.packet_count = 0

    def callback(self, diagnostic: datatypes.DiagnosticValue):
        self.packet_count += 1
        print(
            "\nDiagnostic"
            + "\n  stamp:   " + str(diagnostic.stamp)
            + "\n  name:    " + str(diagnostic.name)
            + "\n  level:   " + str(diagnostic.level)
            + "\n  code:    " + str(diagnostic.code)
            + "\n  message: " + str(diagnostic.message),
            flush=True,
        )


def main():
    robot_ip = sys.argv[1] if len(sys.argv) > 1 else "10.192.1.2"

    robot = Robot(RobotType.PointFoot)
    if not robot.init(robot_ip):
        print(f"Failed to connect to robot at {robot_ip}")
        return 1

    imu_printer = ImuPrinter()
    state_printer = StatePrinter()
    diagnostic_printer = DiagnosticPrinter()
    callbacks = [
        imu_printer.callback,
        state_printer.callback,
        diagnostic_printer.callback,
    ]

    print("subscribeImuData:", robot.subscribeImuData(callbacks[0]))
    print("subscribeRobotState:", robot.subscribeRobotState(callbacks[1]))
    print("subscribeDiagnosticValue:", robot.subscribeDiagnosticValue(callbacks[2]))

    print(f"Connected to {robot_ip}. Reading data. Press Ctrl+C to stop.")

    try:
        started_at = time.time()
        last_notice = 0.0
        while True:
            time.sleep(1)
            total_packets = (
                imu_printer.packet_count
                + state_printer.packet_count
                + diagnostic_printer.packet_count
            )
            elapsed = time.time() - started_at
            if total_packets == 0 and elapsed >= 5 and time.time() - last_notice >= 5:
                last_notice = time.time()
                print(
                    "No IMU/RobotState packets yet. "
                    "Check Developer Mode and Windows Firewall if this continues.",
                    flush=True,
                )
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
