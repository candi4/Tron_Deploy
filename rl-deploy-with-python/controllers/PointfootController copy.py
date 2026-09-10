# import os
# import sys
# import copy
# import numpy as np
# import yaml
# import time
# import onnxruntime as ort
# from scipy.spatial.transform import Rotation as R
# from functools import partial
# import limxsdk
# import limxsdk.robot.Rate as Rate
# import limxsdk.robot.Robot as Robot
# import limxsdk.robot.RobotType as RobotType
# import limxsdk.datatypes as datatypes


# import threading
# import socket
# import numpy as np




# class PointfootController:
#     def __init__(self, model_dir, robot, robot_type, start_controller):
#         # Initialize robot and type information
#         self.robot = robot
#         self.robot_type = robot_type
#         self.depth_image_from_socket = np.zeros((1,1,58,87), dtype=np.float32)  # default ban đầu
#         #self.start_depth_server()


#         # Load configuration and model file paths based on robot type
#         self.config_file = f'{model_dir}/{self.robot_type}/params.yaml'
#         self.model_policy = f'{model_dir}/{self.robot_type}/policy/policy.onnx'
#         self.model_encoder = f'{model_dir}/{self.robot_type}/policy/encoder.onnx'
#         self.depth_encoder = f'{model_dir}/{self.robot_type}/policy/depth_encoder.onnx'

#         # Load configuration settings from the YAML file
#         self.load_config(self.config_file)

#         # Load the ONNX model and set up input and output names
#         self.policy_session = ort.InferenceSession(self.model_policy)
#         self.policy_input_names = [self.policy_session.get_inputs()[i].name for i in range(self.policy_session.get_inputs().__len__())]
#         self.policy_output_names = [self.policy_session.get_outputs()[i].name for i in range(self.policy_session.get_outputs().__len__())]
#         self.policy_input_shapes = [self.policy_session.get_inputs()[i].shape for i in range(self.policy_session.get_inputs().__len__())]
#         self.policy_output_shapes = [self.policy_session.get_outputs()[i].shape for i in range(self.policy_session.get_outputs().__len__())]

#         self.encoder_session = ort.InferenceSession(self.model_encoder)
#         self.encoder_input_names = [self.encoder_session.get_inputs()[i].name for i in range(self.encoder_session.get_inputs().__len__())]
#         self.encoder_output_names = [self.encoder_session.get_outputs()[i].name for i in range(self.encoder_session.get_outputs().__len__())]
#         self.encoder_input_shapes = [self.encoder_session.get_inputs()[i].shape for i in range(self.encoder_session.get_inputs().__len__())]
#         self.encoder_output_shapes = [self.encoder_session.get_outputs()[i].shape for i in range(self.encoder_session.get_outputs().__len__())]
        
#         self.depth_sess = ort.InferenceSession(self.depth_encoder)
#         self.depth_input_names = [i.name for i in self.depth_sess.get_inputs()]
#         self.depth_output_names = [o.name for o in self.depth_sess.get_outputs()]



#         self.h_state = np.zeros((1, 1, 512), dtype=np.float32)

#         # Prepare robot command structure with default values for mode, q, dq, tau, Kp, Kd
#         self.robot_cmd = datatypes.RobotCmd()
#         self.robot_cmd.mode = [0. for x in range(0, self.joint_num)]
#         self.robot_cmd.q = [0. for x in range(0, self.joint_num)]
#         self.robot_cmd.dq = [0. for x in range(0, self.joint_num)]
#         self.robot_cmd.tau = [0. for x in range(0, self.joint_num)]
#         self.robot_cmd.Kp = [self.control_cfg['stiffness'] for x in range(0, self.joint_num)]
#         self.robot_cmd.Kd = [self.control_cfg['damping'] for x in range(0, self.joint_num)]

#         # Prepare robot state structure
#         self.robot_state = datatypes.RobotState()
#         self.robot_state.tau = [0. for x in range(0, self.joint_num)]
#         self.robot_state.q = [0. for x in range(0, self.joint_num)]
#         self.robot_state.dq = [0. for x in range(0, self.joint_num)]
#         self.robot_state_tmp = copy.deepcopy(self.robot_state)

#         # Initialize IMU (Inertial Measurement Unit) data structure
#         self.imu_data = datatypes.ImuData()
#         self.imu_data.quat[0] = 0
#         self.imu_data.quat[1] = 0
#         self.imu_data.quat[2] = 0
#         self.imu_data.quat[3] = 1
#         self.imu_data_tmp = copy.deepcopy(self.imu_data)



#         # Set up a callback to receive updated robot state data
#         self.robot_state_callback_partial = partial(self.robot_state_callback)
#         self.robot.subscribeRobotState(self.robot_state_callback_partial)

#         # Set up a callback to receive updated IMU data
#         self.imu_data_callback_partial = partial(self.imu_data_callback)
#         self.robot.subscribeImuData(self.imu_data_callback_partial)

#         # Set up a callback to receive updated SensorJoy
#         self.sensor_joy_callback_partial = partial(self.sensor_joy_callback)
#         self.robot.subscribeSensorJoy(self.sensor_joy_callback_partial)

#         # Set up a callback to receive diagnostic data
#         self.robot_diagnostic_callback_partial = partial(self.robot_diagnostic_callback)
#         self.robot.subscribeDiagnosticValue(self.robot_diagnostic_callback_partial)

#         # Initialize the calibration state to -1, indicating no calibration has occurred.
#         self.calibration_state = -1

#         # Flag to start the controller
#         self.start_controller = start_controller

#         # Gait index
#         self.gait_index = 0

#         # Flag indicating first received observation
#         self.is_first_rec_obs = True

#     # Load the configuration from a YAML file
#     def start_depth_server(self, host='127.0.0.1', port=8888):
#         def server_thread():
#             with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#                 s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#                 s.bind((host, port))
#                 s.listen(1)
#                 print(f"Depth server listening on {host}:{port}")

#                 while True:
#                     conn, _ = s.accept()
#                     print("Depth connection established")
#                     with conn:
#                         data = conn.recv(58*87*4)
#                         print(f"[DEBUG] Received bytes: {len(data)}")
#                         if data:
#                             depth_array = np.frombuffer(data, dtype=np.float32).reshape((1, 1, 58, 87))
#                             self.depth_image_from_socket = depth_array
#                         else:
#                             print("[WARNING] No data received from client.")
#         threading.Thread(target=server_thread, daemon=True).start()
#     def load_config(self, config_file):
#         with open(config_file, 'r') as f:
#             config = yaml.safe_load(f)

#         # Assign configuration parameters to controller variables
#         self.joint_names = config['PointfootCfg']['joint_names']
#         self.init_state = config['PointfootCfg']['init_state']['default_joint_angle']
#         self.stand_duration = config['PointfootCfg']['stand_mode']['stand_duration']
#         self.control_cfg = config['PointfootCfg']['control']
#         self.rl_cfg = config['PointfootCfg']['normalization']
#         self.obs_scales = config['PointfootCfg']['normalization']['obs_scales']
#         self.actions_size = config['PointfootCfg']['size']['actions_size']
#         self.commands_size = config['PointfootCfg']['size']['commands_size']
#         self.observations_size = config['PointfootCfg']['size']['observations_size']
#         self.obs_history_length = config['PointfootCfg']['size']['obs_history_length']
#         self.encoder_output_size = config['PointfootCfg']['size']['encoder_output_size']
#         self.imu_orientation_offset = np.array(list(config['PointfootCfg']['imu_orientation_offset'].values()))
#         self.user_cmd_cfg = config['PointfootCfg']['user_cmd_scales']
#         self.loop_frequency = config['PointfootCfg']['loop_frequency']
#         self.encoder_input_size = self.obs_history_length * self.observations_size

#         # Initialize variables for actions, observations, and commands
#         self.proprio_history_vector = np.zeros(self.obs_history_length * self.observations_size)
#         self.encoder_out = np.zeros(self.encoder_output_size)
#         self.actions = np.zeros(self.actions_size)
#         self.observations = np.zeros(self.observations_size)
#         self.last_actions = np.zeros(self.actions_size)
#         self.commands = np.zeros(self.commands_size)  # command to the robot (e.g., velocity, rotation)
#         self.scaled_commands = np.zeros(self.commands_size)
#         self.base_lin_vel = np.zeros(3)  # base linear velocity
#         self.base_position = np.zeros(3)  # robot base position
#         self.loop_count = 0  # loop iteration count
#         self.stand_percent = 0  # percentage of time the robot has spent in stand mode
#         self.policy_session = None  # ONNX model session for policy inference
#         self.joint_num = len(self.joint_names)  # number of joints

#         # Initialize joint angles based on the initial configuration
#         self.init_joint_angles = np.zeros(len(self.joint_names))
#         for i in range(len(self.joint_names)):
#             self.init_joint_angles[i] = self.init_state[self.joint_names[i]]
        
#         # Set initial mode to "STAND"
#         self.mode = "STAND"

#     # Main control loop
#     def run(self):
#         # Wait until the controller is started
#         while not self.start_controller:
#           time.sleep(1)

#         # Initialize default joint angles for standing
#         self.default_joint_angles = np.array([0.0] * len(self.joint_names))
#         self.stand_percent += 1 / (self.stand_duration * self.loop_frequency)
#         self.mode = "STAND"
#         self.loop_count = 0

#         # Set the loop rate based on the frequency in the configuration
#         rate = Rate(self.loop_frequency)
#         while self.start_controller:
#             self.update()
#             rate.sleep()
        
#         # Reset robot command values to ensure a safe stop when exiting the loop
#         self.robot_cmd.q = [0. for x in range(0, self.joint_num)]
#         self.robot_cmd.dq = [0. for x in range(0, self.joint_num)]
#         self.robot_cmd.tau = [0. for x in range(0, self.joint_num)]
#         self.robot_cmd.Kp = [0. for x in range(0, self.joint_num)]
#         self.robot_cmd.Kd = [1.0 for x in range(0, self.joint_num)]
#         self.robot.publishRobotCmd(self.robot_cmd)
#         time.sleep(1)

#     # Handle the stand mode for smoothly transitioning the robot into standing
#     def handle_stand_mode(self):
#         if self.stand_percent < 1:
#             for j in range(len(self.joint_names)):
#                 # Interpolate between initial and default joint angles during stand mode
#                 pos_des = self.default_joint_angles[j] * (1 - self.stand_percent) + self.init_state[self.joint_names[j]] * self.stand_percent
#                 self.set_joint_command(j, pos_des, 0, 0, self.control_cfg['stiffness'], self.control_cfg['damping'])
#             # Increment the stand percentage over time
#             self.stand_percent += 1 / (self.stand_duration * self.loop_frequency)
#         else:
#             # Switch to walk mode after standing
#             self.mode = "WALK"

#     # Handle the walk mode where the robot moves based on computed actions
#     def handle_walk_mode(self):
#         # Update the temporary robot state and IMU data
#         self.robot_state_tmp = copy.deepcopy(self.robot_state)
#         self.imu_data_tmp = copy.deepcopy(self.imu_data)

#         # Execute actions every 'decimation' iterations
#         if self.loop_count % self.control_cfg['decimation'] == 0:
#             self.compute_observation()
#             self.compute_encoder()
#             self.compute_actions()
#             # Clip the actions within predefined limits
#             action_min = -self.rl_cfg['clip_scales']['clip_actions']
#             action_max = self.rl_cfg['clip_scales']['clip_actions']
#             self.actions = np.clip(self.actions, action_min, action_max)

#         # Iterate over the joints and set commands based on actions
#         joint_pos = np.array(self.robot_state_tmp.q)
#         joint_vel = np.array(self.robot_state_tmp.dq)

#         for i in range(len(joint_pos)):
#             # Compute the limits for the action based on joint position and velocity
#             action_min = (joint_pos[i] - self.init_joint_angles[i] +
#                           (self.control_cfg['damping'] * joint_vel[i] - self.control_cfg['user_torque_limit']) /
#                           self.control_cfg['stiffness'])
#             action_max = (joint_pos[i] - self.init_joint_angles[i] +
#                           (self.control_cfg['damping'] * joint_vel[i] + self.control_cfg['user_torque_limit']) /
#                           self.control_cfg['stiffness'])

#             # Clip action within limits
#             self.actions[i] = max(action_min / self.control_cfg['action_scale_pos'],
#                                   min(action_max / self.control_cfg['action_scale_pos'], self.actions[i]))

#             # Compute the desired joint position and set it
#             pos_des = self.actions[i] * self.control_cfg['action_scale_pos'] + self.init_joint_angles[i]
#             self.set_joint_command(i, pos_des, 0, 0, self.control_cfg['stiffness'], self.control_cfg['damping'])

#             # Save the last action for reference
#             self.last_actions[i] = self.actions[i]

#     def compute_observation(self):
#         # Convert IMU orientation from quaternion to Euler angles (ZYX convention)
#         imu_orientation = np.array(self.imu_data_tmp.quat)
#         q_wi = R.from_quat(imu_orientation).as_euler('zyx')  # Quaternion to Euler ZYX conversion
#         inverse_rot = R.from_euler('zyx', q_wi).inv().as_matrix()  # Get the inverse rotation matrix

#         # Project the gravity vector (pointing downwards) into the body frame
#         gravity_vector = np.array([0, 0, -1])  # Gravity in world frame (z-axis down)
#         projected_gravity = np.dot(inverse_rot, gravity_vector)  # Transform gravity into body frame

#         # Retrieve base angular velocity from the IMU data
#         base_ang_vel = np.array(self.imu_data_tmp.gyro)
#         # Apply IMU orientation offset correction (using Euler angles)
#         rot = R.from_euler('zyx', self.imu_orientation_offset).as_matrix()  # Rotation matrix for offset correction
#         base_ang_vel = np.dot(rot, base_ang_vel)  # Apply correction to angular velocity
#         projected_gravity = np.dot(rot, projected_gravity)  # Apply correction to projected gravity

#         # Retrieve joint positions and velocities from the robot state
#         joint_positions = np.array(self.robot_state_tmp.q)
#         joint_velocities = np.array(self.robot_state_tmp.dq)

#         gait = np.array([2.0, 0.5, 0.5, 0.1])
#         self.gait_index += 0.02 * gait[0]
#         if self.gait_index > 1.0:
#             self.gait_index = 0.0
#         gait_clock = np.array([np.sin(self.gait_index * 2 * np.pi), np.cos(self.gait_index * 2 * np.pi)])

#         # Retrieve the last actions that were applied to the robot
#         actions = np.array(self.last_actions)

#         # Create a command scaler matrix for linear and angular velocities
#         command_scaler = np.diag([
#             self.user_cmd_cfg['lin_vel_x'],  # Scale factor for linear velocity in x direction
#             self.user_cmd_cfg['lin_vel_y'],  # Scale factor for linear velocity in y direction
#             self.user_cmd_cfg['ang_vel_yaw']  # Scale factor for yaw (angular velocity)
#         ])

#         # Apply scaling to the command inputs (velocity commands)
#         self.scaled_commands = np.dot(command_scaler, self.commands)

#         # Populate observation vector
#         joint_pos_input = (joint_positions - self.init_joint_angles) * self.obs_scales['dof_pos']

#         # Create the observation vector by concatenating various state variables:
#         # - Base angular velocity (scaled)
#         # - Projected gravity vector
#         # - Joint positions (difference from initial angles, scaled)
#         # - Joint velocities (scaled)
#         # - Last actions applied to the robot
#         # - gait_clock: A clock signal related to the gait of the robot.
#         # - gait: Information about the current gait of the robot.
#         #depth = self.depth_image_from_socket
        
        
#         obs = np.concatenate([
#             base_ang_vel * self.obs_scales['ang_vel'],  # Scaled base angular velocity
#             projected_gravity,  # Projected gravity vector in body frame
#             joint_pos_input,  # Scaled joint positions
#             joint_velocities * self.obs_scales['dof_vel'],  # Scaled joint velocities
#             actions,  # Last actions taken by the robot
#             gait_clock,  # A clock signal related to the robot's gait
#             gait  # Information about the current gait pattern of the robot
#         ])
#         num_prop = 30  # 👈 chỉnh đúng số proprio lúc bạn huấn luyện depth encoder
#         obs = obs[:num_prop]
#         depth = np.full((11, 11), 0.00, dtype=float)
#         depth = depth.reshape(-1)
#         #obs = np.concatenate([obs[:num_prop],depth])
#         #obs_add_cmd = np.concatenate([obs[:num_prop],self.scaled_commands])
#         #depth_obs = self.compute_depth_latent(depth, obs_add_cmd)

#         #obs = np.concatenate([obs,depth_obs])

#         # Check if this is the first recorded observation
#         if self.is_first_rec_obs:
#             # Calculate the total size of the encoder input
#             input_size = np.prod(self.encoder_input_shapes[0])
#             print("inputsize",input_size)
            
#             # Initialize the proprioceptive history buffer with zeros
#             self.proprio_history_buffer = np.zeros(input_size)

#             # Fill the proprioceptive history buffer with the current observation for the entire history length
#             for i in range(self.obs_history_length):
#                 self.proprio_history_buffer[i * self.observations_size:(i + 1) * self.observations_size] = obs

#             # Update the flag to indicate that the first observation has been processed
#             self.is_first_rec_obs = False
        
#         # Shift the existing proprioceptive history buffer to the left
#         self.proprio_history_buffer[:-self.observations_size] = self.proprio_history_buffer[self.observations_size:]

#         # Add the current observation to the end of the proprioceptive history buffer
#         self.proprio_history_buffer[-self.observations_size:] = obs

#         # Convert the proprioceptive history buffer to a numpy array
#         self.proprio_history_vector = np.array(self.proprio_history_buffer)

#         # Clip the observation values to within the specified limits for stability
#         self.observations = np.clip(
#             obs, 
#             -self.rl_cfg['clip_scales']['clip_observations'],  # Lower limit for clipping
#             self.rl_cfg['clip_scales']['clip_observations']  # Upper limit for clipping
#         )

#     def compute_actions(self):
#         """
#         Computes the actions based on the current observations using the policy session.
#         """
#         # Concatenate observations into a single tensor and convert to float32
#         input_tensor = np.concatenate([self.encoder_out, self.observations, self.scaled_commands], axis=0)
#         input_tensor = input_tensor.astype(np.float32)
        
#         # Create a dictionary of inputs for the policy session
#         inputs = {self.policy_input_names[0]: input_tensor}
        
#         # Run the policy session and get the output
#         output = self.policy_session.run(self.policy_output_names, inputs)
        
#         # Flatten the output and store it as actions
#         self.actions = np.array(output).flatten()

#     def compute_encoder(self):
#         """
#         Computes the encoder output based on the proprioceptive history buffer.

#         This method first concatenates the proprioceptive history buffer into a single input tensor.
#         Then it converts the input tensor to the float32 data type. After that, it creates a dictionary
#         of inputs for the encoder session and runs the encoder session to get the output. Finally,
#         it flattens the output and stores it as the encoder output.
#         """
#         # Concatenate the proprioceptive history buffer into a single tensor and convert to float32
#         input_tensor = np.concatenate([self.proprio_history_buffer], axis=0)
#         input_tensor = input_tensor.astype(np.float32)

#         # Create a dictionary of inputs for the encoder session
#         inputs = {self.encoder_input_names[0]: input_tensor}

#         # Run the encoder session and get the output
#         output = self.encoder_session.run(self.encoder_output_names, inputs)

#         # Flatten the output and store it as the encoder output
#         self.encoder_out = np.array(output).flatten()
        
        
#     def compute_depth_latent(self, depth_image, proprio):
#         """
#         depth_image: numpy array shape (1,1,58,87)
#         proprio:     numpy array shape (1,32)
#         """

#         # Bảo đảm dtype đúng
#         depth_image = depth_image.astype(np.float32)
#         proprio     = proprio.astype(np.float32).reshape(1, -1)  # ensure (1, 32)
#         h_in        = self.h_state.astype(np.float32)

#         # Chuẩn bị dict input cho ONNX
#         inputs = {
#             self.depth_input_names[0]: depth_image,
#             self.depth_input_names[1]: proprio,
#             self.depth_input_names[2]: h_in,
#         }

#         # Forward ONNX
#         latent, h_out = self.depth_sess.run(self.depth_output_names, inputs)

#         # Cập nhật hidden state GRU
#         self.h_state = h_out

#         # Trả latent (1, latent_dim)
#         return latent.flatten()

 
#     def set_joint_command(self, joint_index, q, dq, tau, kp, kd):
#         """
#         Sends a command to configure the state of a specific joint.
#         This method updates the joint's desired position, velocity, torque, and control gains.
#         Replace this implementation with the actual communication logic for your hardware.

#         Parameters:
#         joint_index (int): The index of the joint to be controlled.
#         q (float): The desired joint position, typically in radians or degrees.
#         dq (float): The desired joint velocity, typically in radians/second or degrees/second.
#         tau (float): The desired joint torque, typically in Newton-meters (Nm).
#         kp (float): The proportional gain for position control.
#         kd (float): The derivative gain for velocity control.
#         """
#         self.robot_cmd.q[joint_index] = q
#         self.robot_cmd.dq[joint_index] = dq
#         self.robot_cmd.tau[joint_index] = tau
#         self.robot_cmd.Kp[joint_index] = kp
#         self.robot_cmd.Kd[joint_index] = kd

#     def update(self):
#         """
#         Updates the robot's state based on the current mode and publishes the robot command.
#         """
#         if self.mode == "STAND":
#             self.handle_stand_mode()
#         elif self.mode == "WALK":
#             self.handle_walk_mode()
        
#         # Increment the loop count
#         self.loop_count += 1

#         # Publish the robot command
#         self.robot.publishRobotCmd(self.robot_cmd)
        
#     # Callback function for receiving robot command data
#     def robot_state_callback(self, robot_state: datatypes.RobotState):
#         """
#         Callback function to update the robot state from incoming data.
        
#         Parameters:
#         robot_state (datatypes.RobotState): The current state of the robot.
#         """
#         self.robot_state = robot_state

#     # Callback function for receiving imu data
#     def imu_data_callback(self, imu_data: datatypes.ImuData):
#         """
#         Callback function to update IMU data from incoming data.
        
#         Parameters:
#         imu_data (datatypes.ImuData): The IMU data containing stamp, acceleration, gyro, and quaternion.
#         """
#         self.imu_data.stamp = imu_data.stamp
#         self.imu_data.acc = imu_data.acc
#         self.imu_data.gyro = imu_data.gyro
        
#         # Rotate quaternion values
#         self.imu_data.quat[0] = imu_data.quat[1]
#         self.imu_data.quat[1] = imu_data.quat[2]
#         self.imu_data.quat[2] = imu_data.quat[3]
#         self.imu_data.quat[3] = imu_data.quat[0]

#     # Callback function for receiving sensor joy data
#     def sensor_joy_callback(self, sensor_joy: datatypes.SensorJoy):
#         # Check if the robot is in the calibration state and both L1 (button index 4) and Y (button index 3) buttons are pressed.
#         if not self.start_controller and self.calibration_state == 0 and sensor_joy.buttons[4] == 1 and sensor_joy.buttons[3] == 1:
#           print(f"L1 + Y: start_controller...")
#           self.start_controller = True

#         # Check if both L1 (button index 4) and X (button index 2) are pressed to stop the controller
#         if self.start_controller and sensor_joy.buttons[4] == 1 and sensor_joy.buttons[2] == 1:
#           print(f"L1 + X: stop_controller...")
#           self.start_controller = False

#         linear_x  = sensor_joy.axes[1]
#         linear_y  = sensor_joy.axes[0]
#         angular_z = sensor_joy.axes[2]

#         linear_x  = 1.0 if linear_x > 1.0 else (-1.0 if linear_x < -1.0 else linear_x)
#         linear_y  = 1.0 if linear_y > 1.0 else (-1.0 if linear_y < -1.0 else linear_y)
#         angular_z = 1.0 if angular_z > 1.0 else (-1.0 if angular_z < -1.0 else angular_z)

#         self.commands[0] = linear_x * 0.5
#         self.commands[1] = linear_y * 0.5
#         self.commands[2] = angular_z * 0.5

#     # Callback function for receiving diagnostic data
#     def robot_diagnostic_callback(self, diagnostic_value: datatypes.DiagnosticValue):
#       # Check if the received diagnostic data is related to calibration.
#       if diagnostic_value.name == "calibration":
#         print(f"Calibration state: {diagnostic_value.code}")
#         self.calibration_state = diagnostic_value.code

import os
import sys
import copy
import numpy as np
import yaml
import time
import onnxruntime as ort
from scipy.spatial.transform import Rotation as R
from functools import partial
import limxsdk
import limxsdk.robot.Rate as Rate
import limxsdk.robot.Robot as Robot
import limxsdk.robot.RobotType as RobotType
import limxsdk.datatypes as datatypes

import threading
import socket
import numpy as np

class PointfootController:
    def __init__(self, model_dir, robot, robot_type, rl_type, start_controller):
        # Initialize robot and type information
        self.robot = robot
        self.robot_type = robot_type
        self.rl_type = rl_type
        self.depth_image_from_socket = np.zeros((1,1,58,87), dtype=np.float32)  # default ban đầu
        self.start_depth_server()
        # Load configuration and model file paths based on robot type
        self.config_file = f'{model_dir}/{self.robot_type}/params.yaml'
        self.model_policy = f'{model_dir}/{self.robot_type}/policy/{self.rl_type}/depth_policy.onnx'
        self.model_encoder = f'{model_dir}/{self.robot_type}/policy/{self.rl_type}/encoder_history_depth.onnx'
        self.depth_encoder = f'{model_dir}/{self.robot_type}/policy/{self.rl_type}/depth_encoder.onnx'

        # Load configuration settings from the YAML file
        self.load_config(self.config_file)
        
        # Load the ONNX model
        self.initialize_onnx_models()

        # Prepare robot command structure with default values for mode, q, dq, tau, Kp, Kd
        self.robot_cmd = datatypes.RobotCmd()
        self.robot_cmd.mode = [0. for x in range(0, self.joint_num)]
        self.robot_cmd.q = [0. for x in range(0, self.joint_num)]
        self.robot_cmd.dq = [0. for x in range(0, self.joint_num)]
        self.robot_cmd.tau = [0. for x in range(0, self.joint_num)]
        self.robot_cmd.Kp = [self.control_cfg['stiffness'] for x in range(0, self.joint_num)]
        self.robot_cmd.Kd = [self.control_cfg['damping'] for x in range(0, self.joint_num)]

        # Prepare robot state structure
        self.robot_state = datatypes.RobotState()
        self.robot_state.tau = [0. for x in range(0, self.joint_num)]
        self.robot_state.q = [0. for x in range(0, self.joint_num)]
        self.robot_state.dq = [0. for x in range(0, self.joint_num)]
        self.robot_state_tmp = copy.deepcopy(self.robot_state)

        # Initialize IMU (Inertial Measurement Unit) data structure
        self.imu_data = datatypes.ImuData()
        self.imu_data.quat[0] = 0
        self.imu_data.quat[1] = 0
        self.imu_data.quat[2] = 0
        self.imu_data.quat[3] = 1
        self.imu_data_tmp = copy.deepcopy(self.imu_data)

        # Set up a callback to receive updated robot state data
        self.robot_state_callback_partial = partial(self.robot_state_callback)
        self.robot.subscribeRobotState(self.robot_state_callback_partial)

        # Set up a callback to receive updated IMU data
        self.imu_data_callback_partial = partial(self.imu_data_callback)
        self.robot.subscribeImuData(self.imu_data_callback_partial)

        # Set up a callback to receive updated SensorJoy
        self.sensor_joy_callback_partial = partial(self.sensor_joy_callback)
        self.robot.subscribeSensorJoy(self.sensor_joy_callback_partial)

        # Set up a callback to receive diagnostic data
        self.robot_diagnostic_callback_partial = partial(self.robot_diagnostic_callback)
        self.robot.subscribeDiagnosticValue(self.robot_diagnostic_callback_partial)

        # Initialize the calibration state to -1, indicating no calibration has occurred.
        self.calibration_state = -1

        # Flag to start the controller
        self.start_controller = start_controller

        # Gait index
        self.gait_index = 0

        # Flag indicating first received observation
        self.is_first_rec_obs = True

    def start_depth_server(self, host='127.0.0.1', port=8888):
        def server_thread():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                s.listen(1)
                print(f"Depth server listening on {host}:{port}")

                while True:
                    conn, _ = s.accept()
                    print("Depth connection established")
                    with conn:
                        data = conn.recv(58*87*4)
                        print(f"[DEBUG] Received bytes: {len(data)}")
                        if data:
                            depth_array = np.frombuffer(data, dtype=np.float32).reshape((1, 1, 58, 87))
                            self.depth_image_from_socket = depth_array
                        else:
                            print("[WARNING] No data received from client.")
        threading.Thread(target=server_thread, daemon=True).start()
    
    def initialize_onnx_models(self):
        # Configure ONNX Runtime session options to optimize CPU usage
        session_options = ort.SessionOptions()
        # Limit the number of threads used for parallel computation within individual operators
        session_options.intra_op_num_threads = 1
        # Limit the number of threads used for parallel execution of different operators
        session_options.inter_op_num_threads = 1
        # Enable all possible graph optimizations to improve inference performance
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        # Disable CPU memory arena to reduce memory fragmentation
        session_options.enable_cpu_mem_arena = False
        # Disable memory pattern optimization to have more control over memory allocation
        session_options.enable_mem_pattern = False

        # Define execution providers to use CPU only, ensuring no GPU inference
        cpu_providers = ['CPUExecutionProvider']
        
        # Load the ONNX model and set up input and output names
        self.policy_session = ort.InferenceSession(self.model_policy, sess_options=session_options, providers=cpu_providers)
        self.policy_input_names = [self.policy_session.get_inputs()[i].name for i in range(self.policy_session.get_inputs().__len__())]
        self.policy_output_names = [self.policy_session.get_outputs()[i].name for i in range(self.policy_session.get_outputs().__len__())]
        self.policy_input_shapes = [self.policy_session.get_inputs()[i].shape for i in range(self.policy_session.get_inputs().__len__())]
        self.policy_output_shapes = [self.policy_session.get_outputs()[i].shape for i in range(self.policy_session.get_outputs().__len__())]

        self.encoder_session = ort.InferenceSession(self.model_encoder, sess_options=session_options, providers=cpu_providers)
        self.encoder_input_names = [self.encoder_session.get_inputs()[i].name for i in range(self.encoder_session.get_inputs().__len__())]
        self.encoder_output_names = [self.encoder_session.get_outputs()[i].name for i in range(self.encoder_session.get_outputs().__len__())]
        self.encoder_input_shapes = [self.encoder_session.get_inputs()[i].shape for i in range(self.encoder_session.get_inputs().__len__())]
        self.encoder_output_shapes = [self.encoder_session.get_outputs()[i].shape for i in range(self.encoder_session.get_outputs().__len__())]
        
        self.depth_sess = ort.InferenceSession(self.depth_encoder)
        self.depth_input_names = [i.name for i in self.depth_sess.get_inputs()]
        self.depth_output_names = [o.name for o in self.depth_sess.get_outputs()]



        self.h_state = np.zeros((1, 1, 512), dtype=np.float32)
    
    # Load the configuration from a YAML file
    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        # Assign configuration parameters to controller variables
        self.joint_names = config['PointfootCfg']['joint_names']
        self.init_state = config['PointfootCfg']['init_state']['default_joint_angle']
        self.stand_duration = config['PointfootCfg']['stand_mode']['stand_duration']
        self.control_cfg = config['PointfootCfg']['control']
        self.rl_cfg = config['PointfootCfg']['normalization']
        self.obs_scales = config['PointfootCfg']['normalization']['obs_scales']
        self.actions_size = config['PointfootCfg']['size']['actions_size']
        self.commands_size = config['PointfootCfg']['size']['commands_size']
        self.observations_size = config['PointfootCfg']['size']['observations_size']
        self.obs_history_length = config['PointfootCfg']['size']['obs_history_length']
        self.encoder_output_size = config['PointfootCfg']['size']['encoder_output_size']
        self.imu_orientation_offset = np.array(list(config['PointfootCfg']['imu_orientation_offset'].values()))
        self.user_cmd_cfg = config['PointfootCfg']['user_cmd_scales']
        self.loop_frequency = config['PointfootCfg']['loop_frequency']
        self.encoder_input_size = self.obs_history_length * self.observations_size

        # Initialize variables for actions, observations, and commands
        self.proprio_history_vector = np.zeros(self.obs_history_length * self.observations_size)
        self.encoder_out = np.zeros(self.encoder_output_size)
        self.actions = np.zeros(self.actions_size)
        self.observations = np.zeros(self.observations_size)
        self.last_actions = np.zeros(self.actions_size)
        self.commands = np.zeros(self.commands_size)  # command to the robot (e.g., velocity, rotation)
        self.scaled_commands = np.zeros(self.commands_size)
        self.base_lin_vel = np.zeros(3)  # base linear velocity
        self.base_position = np.zeros(3)  # robot base position
        self.loop_count = 0  # loop iteration count
        self.stand_percent = 0  # percentage of time the robot has spent in stand mode
        self.policy_session = None  # ONNX model session for policy inference
        self.joint_num = len(self.joint_names)  # number of joints

        # Initialize joint angles based on the initial configuration
        self.init_joint_angles = np.zeros(len(self.joint_names))
        for i in range(len(self.joint_names)):
            self.init_joint_angles[i] = self.init_state[self.joint_names[i]]
        
        # Set initial mode to "STAND"
        self.mode = "STAND"

    # Main control loop
    def run(self):
        # Wait until the controller is started
        while not self.start_controller:
          time.sleep(1)

        # Initialize default joint angles for standing
        self.default_joint_angles = np.array([0.0] * len(self.joint_names))
        self.stand_percent += 1 / (self.stand_duration * self.loop_frequency)
        self.mode = "STAND"
        self.loop_count = 0

        # Set the loop rate based on the frequency in the configuration
        rate = Rate(self.loop_frequency)
        while self.start_controller:
            self.update()
            rate.sleep()
        
        # Reset robot command values to ensure a safe stop when exiting the loop
        self.robot_cmd.q = [0. for x in range(0, self.joint_num)]
        self.robot_cmd.dq = [0. for x in range(0, self.joint_num)]
        self.robot_cmd.tau = [0. for x in range(0, self.joint_num)]
        self.robot_cmd.Kp = [0. for x in range(0, self.joint_num)]
        self.robot_cmd.Kd = [1.0 for x in range(0, self.joint_num)]
        self.robot.publishRobotCmd(self.robot_cmd)
        time.sleep(1)

    # Handle the stand mode for smoothly transitioning the robot into standing
    def handle_stand_mode(self):
        if self.stand_percent < 1:
            for j in range(len(self.joint_names)):
                # Interpolate between initial and default joint angles during stand mode
                pos_des = self.default_joint_angles[j] * (1 - self.stand_percent) + self.init_state[self.joint_names[j]] * self.stand_percent
                self.set_joint_command(j, pos_des, 0, 0, self.control_cfg['stiffness'], self.control_cfg['damping'])
            # Increment the stand percentage over time
            self.stand_percent += 1 / (self.stand_duration * self.loop_frequency)
        else:
            # Switch to walk mode after standing
            self.mode = "WALK"

    # Handle the walk mode where the robot moves based on computed actions
    def handle_walk_mode(self):
        # Update the temporary robot state and IMU data
        self.robot_state_tmp = copy.deepcopy(self.robot_state)
        self.imu_data_tmp = copy.deepcopy(self.imu_data)

        # Execute actions every 'decimation' iterations
        if self.loop_count % self.control_cfg['decimation'] == 0:
            self.compute_observation()
            self.compute_encoder()
            self.compute_actions()
            # Clip the actions within predefined limits
            action_min = -self.rl_cfg['clip_scales']['clip_actions']
            action_max = self.rl_cfg['clip_scales']['clip_actions']
            self.actions = np.clip(self.actions, action_min, action_max)

            # swap actions positions back to deep first, only when action updated
            if self.rl_type == "isaaclab":
                self.actions = self.swap_positions(self.actions, reverse=True)
        
        # Iterate over the joints and set commands based on actions
        joint_pos = np.array(self.robot_state_tmp.q)
        joint_vel = np.array(self.robot_state_tmp.dq)

        for i in range(len(joint_pos)):
            # Compute the limits for the action based on joint position and velocity
            action_min = (joint_pos[i] - self.init_joint_angles[i] +
                          (self.control_cfg['damping'] * joint_vel[i] - self.control_cfg['user_torque_limit']) /
                          self.control_cfg['stiffness'])
            action_max = (joint_pos[i] - self.init_joint_angles[i] +
                          (self.control_cfg['damping'] * joint_vel[i] + self.control_cfg['user_torque_limit']) /
                          self.control_cfg['stiffness'])

            # Clip action within limits
            self.actions[i] = max(action_min / self.control_cfg['action_scale_pos'],
                                  min(action_max / self.control_cfg['action_scale_pos'], self.actions[i]))

            # Compute the desired joint position and set it
            pos_des = self.actions[i] * self.control_cfg['action_scale_pos'] + self.init_joint_angles[i]
            self.set_joint_command(i, pos_des, 0, 0, self.control_cfg['stiffness'], self.control_cfg['damping'])

            # Save the last action for reference
            self.last_actions[i] = self.actions[i]

    def swap_positions(self, initial_array, reverse=False):
        joint_idx_lab = [0, 3, 1, 4, 2, 5]
        new_array = np.zeros(initial_array.shape)
        for i in range(len(joint_idx_lab)):
            if not reverse:
                new_array[i] = initial_array[joint_idx_lab[i]]
            else:
                new_array[joint_idx_lab[i]] = initial_array[i]
        return new_array

    def compute_observation(self):
        # Convert IMU orientation from quaternion to Euler angles (ZYX convention)
        imu_orientation = np.array(self.imu_data_tmp.quat)
        q_wi = R.from_quat(imu_orientation).as_euler('zyx')  # Quaternion to Euler ZYX conversion
        inverse_rot = R.from_euler('zyx', q_wi).inv().as_matrix()  # Get the inverse rotation matrix

        # Project the gravity vector (pointing downwards) into the body frame
        gravity_vector = np.array([0, 0, -1])  # Gravity in world frame (z-axis down)
        projected_gravity = np.dot(inverse_rot, gravity_vector)  # Transform gravity into body frame

        # Retrieve base angular velocity from the IMU data
        base_ang_vel = np.array(self.imu_data_tmp.gyro)
        # Apply IMU orientation offset correction (using Euler angles)
        rot = R.from_euler('zyx', self.imu_orientation_offset).as_matrix()  # Rotation matrix for offset correction
        base_ang_vel = np.dot(rot, base_ang_vel)  # Apply correction to angular velocity
        projected_gravity = np.dot(rot, projected_gravity)  # Apply correction to projected gravity

        # Retrieve joint positions and velocities from the robot state
        joint_positions = np.array(self.robot_state_tmp.q)
        joint_velocities = np.array(self.robot_state_tmp.dq)

        gait = np.array([2.0, 0.5, 0.5, 0.1])
        self.gait_index += 0.02 * gait[0]
        if self.gait_index > 1.0:
            self.gait_index = 0.0
        gait_clock = np.array([np.sin(self.gait_index * 2 * np.pi), np.cos(self.gait_index * 2 * np.pi)])

        # Retrieve the last actions that were applied to the robot
        actions = np.array(self.last_actions)

        # Create a command scaler matrix for linear and angular velocities
        command_scaler = np.diag([
            self.user_cmd_cfg['lin_vel_x'],  # Scale factor for linear velocity in x direction
            self.user_cmd_cfg['lin_vel_y'],  # Scale factor for linear velocity in y direction
            self.user_cmd_cfg['ang_vel_yaw']  # Scale factor for yaw (angular velocity)
        ])

        # Apply scaling to the command inputs (velocity commands)
        
        self.scaled_commands = np.dot(command_scaler, self.commands)
        scaled_commands2 = [2.8794e-01, 4.7069e-01, -1.1301e-02]
        self.scaled_commands = [0.3,0,0]
        # Populate observation vector
        joint_pos_input = (joint_positions - self.init_joint_angles) * self.obs_scales['dof_pos']
        # swap positions in joint_pos, joint_vel and actions if mode is isaaclab
        if self.rl_type == "isaaclab":
            joint_pos_input = self.swap_positions(joint_pos_input)
            joint_velocities = self.swap_positions(joint_velocities)
            actions = self.swap_positions(actions)

        # Create the observation vector by concatenating various state variables:
        # - Base angular velocity (scaled)
        # - Projected gravity vector
        # - Joint positions (difference from initial angles, scaled)
        # - Joint velocities (scaled)
        # - Last actions applied to the robot
        # - gait_clock: A clock signal related to the gait of the robot.
        # - gait: Information about the current gait of the robot.
        depth1 = self.depth_image_from_socket
        # depth_np = depth1.squeeze().reshape(58, 87)  # shape: (58, 87)
        # np.savetxt("depth_output.csv", depth_np, delimiter=",", fmt="%.5f")
        # print("Saved depth image to depth_output.csv")
        obs = np.concatenate([
            base_ang_vel * self.obs_scales['ang_vel'],  # Scaled base angular velocity
            projected_gravity,  # Projected gravity vector in body frame
            joint_pos_input,  # Scaled joint positions
            joint_velocities * self.obs_scales['dof_vel'],  # Scaled joint velocities
            actions,  # Last actions taken by the robot
            gait_clock,  # A clock signal related to the robot's gait
            gait  # Information about the current gait pattern of the robot
        ])
        num_prop = 29  # 👈 chỉnh đúng số proprio lúc bạn huấn luyện depth encoder
        obs = obs[:num_prop]
        depth = np.full((11, 11), 0.18, dtype=float)
        depth = depth.reshape(-1)
        obs_add_cmd2 = np.concatenate([obs[:num_prop],self.scaled_commands])
        # obs_add_cmd2 = np.array([
        #     9.3439e-02,  4.1379e-02, -2.4626e-02, -3.3632e-02,  2.5529e-03,
        #     -9.9943e-01, -9.7621e-02,  2.7469e-02,  3.6526e-01, -5.1908e-01,
        #     7.3923e-01, -9.5512e-01, -7.8229e-02,  3.3961e-02,  1.2008e-02,
        #     -3.1060e-02, -8.0256e-03, -1.7278e-01,  1.9925e+00,  3.8802e-01,
        #     1.5784e+00, -2.4449e+00, -3.3351e+00, -4.3137e+00,  5.5262e-01,
        #     8.3343e-01,  2.3908e+00,  5.0000e-01,  5.0000e-01,  2.8794e-01,
        #     4.7069e-01, -1.1301e-02
        # ], dtype=np.float32)
        raw = """
        1.59881,1.58886,1.57909,1.56948,1.56006,1.55080,1.54173,1.53284,1.52413,1.51560,1.50726,1.49910,1.49113,1.48336,1.47577,1.46838,1.46118,1.45418,1.44738,1.44078,1.43437,1.42817,1.42218,1.41638,1.41080,1.40542,1.40024,1.39528,1.39052,1.38598,1.38164,1.37752,1.37361,1.36991,1.36643,1.36316,1.36010,1.35725,1.35462,1.35221,1.35000,1.34801,1.34623,1.34467,1.34331,1.34217,1.34124,1.34051,1.34000,1.33969,1.33959,1.33970,1.34001,1.34052,1.34123,1.34215,1.34326,1.34456,1.34607,1.34776,1.34965,1.35172,1.35398,1.35643,1.35906,1.36187,1.36486,1.36802,1.37136,1.37487,1.37855,1.38239,1.38640,1.39057,1.39490,1.39939,1.40403,1.40882,1.41376,1.41885,1.42408,1.42946,1.43497,1.44062,1.44640,1.45231,1.45835
        1.55338,1.54363,1.53405,1.52463,1.51539,1.50632,1.49742,1.48871,1.48017,1.47181,1.46363,1.45563,1.44783,1.44020,1.43277,1.42553,1.41848,1.41162,1.40495,1.39849,1.39222,1.38614,1.38027,1.37460,1.36914,1.36387,1.35881,1.35396,1.34932,1.34488,1.34065,1.33662,1.33281,1.32921,1.32581,1.32263,1.31966,1.31690,1.31435,1.31201,1.30989,1.30797,1.30626,1.30477,1.30348,1.30240,1.30153,1.30087,1.30041,1.30016,1.30011,1.30027,1.30063,1.30118,1.30194,1.30289,1.30404,1.30539,1.30692,1.30865,1.31057,1.31267,1.31496,1.31743,1.32008,1.32291,1.32591,1.32909,1.33244,1.33596,1.33965,1.34350,1.34751,1.35169,1.35602,1.36050,1.36514,1.36992,1.37486,1.37993,1.38515,1.39051,1.39601,1.40164,1.40740,1.41329,1.41931
        1.51017,1.50060,1.49120,1.48197,1.47290,1.46400,1.45528,1.44673,1.43835,1.43015,1.42213,1.41429,1.40663,1.39916,1.39187,1.38476,1.37785,1.37113,1.36459,1.35825,1.35211,1.34616,1.34041,1.33486,1.32950,1.32435,1.31940,1.31465,1.31011,1.30577,1.30164,1.29771,1.29399,1.29047,1.28717,1.28407,1.28118,1.27850,1.27603,1.27376,1.27171,1.26986,1.26822,1.26679,1.26557,1.26455,1.26373,1.26313,1.26272,1.26252,1.26252,1.26272,1.26313,1.26373,1.26452,1.26551,1.26670,1.26808,1.26965,1.27140,1.27334,1.27547,1.27778,1.28027,1.28294,1.28579,1.28881,1.29200,1.29536,1.29889,1.30258,1.30643,1.31045,1.31462,1.31895,1.32343,1.32806,1.33284,1.33776,1.34283,1.34803,1.35337,1.35885,1.36446,1.37020,1.37607,1.38206
        1.46904,1.45966,1.45043,1.44137,1.43247,1.42374,1.41517,1.40678,1.39856,1.39051,1.38264,1.37495,1.36743,1.36009,1.35294,1.34597,1.33919,1.33259,1.32619,1.31997,1.31394,1.30811,1.30247,1.29703,1.29178,1.28674,1.28189,1.27724,1.27279,1.26855,1.26451,1.26067,1.25704,1.25361,1.25038,1.24736,1.24455,1.24194,1.23954,1.23735,1.23536,1.23358,1.23200,1.23063,1.22946,1.22850,1.22774,1.22719,1.22683,1.22668,1.22672,1.22697,1.22741,1.22805,1.22888,1.22991,1.23113,1.23254,1.23413,1.23591,1.23788,1.24003,1.24236,1.24487,1.24755,1.25041,1.25344,1.25664,1.26001,1.26355,1.26724,1.27110,1.27511,1.27928,1.28361,1.28808,1.29270,1.29747,1.30238,1.30743,1.31262,1.31794,1.32340,1.32899,1.33470,1.34054,1.34651
        1.42989,1.42067,1.41161,1.40271,1.39398,1.38540,1.37699,1.36875,1.36068,1.35278,1.34505,1.33749,1.33011,1.32291,1.31589,1.30904,1.30239,1.29591,1.28962,1.28352,1.27761,1.27189,1.26636,1.26102,1.25588,1.25093,1.24618,1.24163,1.23727,1.23312,1.22916,1.22541,1.22185,1.21850,1.21536,1.21241,1.20967,1.20714,1.20480,1.20267,1.20075,1.19903,1.19751,1.19620,1.19508,1.19417,1.19347,1.19296,1.19265,1.19254,1.19263,1.19291,1.19339,1.19406,1.19493,1.19599,1.19723,1.19867,1.20029,1.20210,1.20408,1.20625,1.20860,1.21112,1.21382,1.21669,1.21973,1.22294,1.22631,1.22985,1.23355,1.23740,1.24142,1.24558,1.24990,1.25436,1.25897,1.26373,1.26863,1.27366,1.27883,1.28414,1.28957,1.29514,1.30083,1.30664,1.31258
        1.39260,1.38354,1.37464,1.36590,1.35732,1.34889,1.34063,1.33254,1.32460,1.31684,1.30925,1.30182,1.29457,1.28750,1.28060,1.27388,1.26734,1.26098,1.25481,1.24882,1.24301,1.23740,1.23197,1.22673,1.22169,1.21683,1.21217,1.20771,1.20344,1.19937,1.19550,1.19183,1.18835,1.18508,1.18200,1.17913,1.17646,1.17399,1.17172,1.16965,1.16779,1.16612,1.16466,1.16340,1.16234,1.16148,1.16081,1.16035,1.16008,1.16001,1.16014,1.16046,1.16098,1.16168,1.16258,1.16366,1.16494,1.16640,1.16804,1.16987,1.17187,1.17406,1.17642,1.17895,1.18166,1.18454,1.18759,1.19080,1.19418,1.19772,1.20141,1.20527,1.20928,1.21343,1.21774,1.22220,1.22680,1.23154,1.23642,1.24144,1.24659,1.25187,1.25728,1.26282,1.26849,1.27427,1.28018
        1.35707,1.34817,1.33942,1.33083,1.32240,1.31412,1.30600,1.29804,1.29024,1.28261,1.27515,1.26785,1.26073,1.25377,1.24700,1.24039,1.23397,1.22772,1.22165,1.21577,1.21007,1.20455,1.19922,1.19408,1.18913,1.18436,1.17979,1.17541,1.17123,1.16724,1.16345,1.15985,1.15645,1.15324,1.15024,1.14743,1.14483,1.14242,1.14021,1.13820,1.13639,1.13478,1.13337,1.13216,1.13114,1.13033,1.12971,1.12929,1.12906,1.12903,1.12919,1.12954,1.13009,1.13082,1.13175,1.13286,1.13416,1.13564,1.13730,1.13915,1.14117,1.14337,1.14574,1.14829,1.15100,1.15389,1.15694,1.16016,1.16354,1.16707,1.17077,1.17462,1.17862,1.18277,1.18707,1.19151,1.19609,1.20082,1.20568,1.21068,1.21581,1.22107,1.22646,1.23197,1.23761,1.24336,1.24924
        1.32321,1.31446,1.30586,1.29741,1.28912,1.28098,1.27299,1.26517,1.25750,1.25000,1.24266,1.23549,1.22848,1.22165,1.21498,1.20849,1.20217,1.19603,1.19007,1.18429,1.17868,1.17326,1.16803,1.16298,1.15811,1.15344,1.14895,1.14465,1.14055,1.13663,1.13291,1.12939,1.12606,1.12292,1.11998,1.11724,1.11469,1.11235,1.11019,1.10824,1.10648,1.10492,1.10356,1.10239,1.10143,1.10065,1.10007,1.09969,1.09950,1.09950,1.09970,1.10008,1.10066,1.10142,1.10237,1.10350,1.10482,1.10632,1.10800,1.10986,1.11190,1.11411,1.11649,1.11905,1.12177,1.12466,1.12772,1.13093,1.13431,1.13784,1.14153,1.14537,1.14937,1.15351,1.15779,1.16222,1.16679,1.17150,1.17635,1.18132,1.18643,1.19167,1.19703,1.20251,1.20812,1.21385,1.21969
        1.29093,1.28233,1.27387,1.26556,1.25740,1.24940,1.24154,1.23385,1.22631,1.21893,1.21171,1.20465,1.19776,1.19104,1.18448,1.17810,1.17188,1.16585,1.15998,1.15429,1.14879,1.14346,1.13831,1.13335,1.12857,1.12398,1.11957,1.11535,1.11132,1.10748,1.10383,1.10038,1.09711,1.09404,1.09116,1.08848,1.08599,1.08370,1.08160,1.07970,1.07799,1.07648,1.07517,1.07404,1.07312,1.07238,1.07184,1.07149,1.07134,1.07137,1.07160,1.07201,1.07261,1.07340,1.07437,1.07553,1.07686,1.07838,1.08008,1.08195,1.08400,1.08622,1.08861,1.09117,1.09390,1.09679,1.09985,1.10306,1.10643,1.10996,1.11365,1.11748,1.12146,1.12559,1.12986,1.13428,1.13883,1.14352,1.14834,1.15330,1.15838,1.16359,1.16893,1.17438,1.17996,1.18565,1.19146
        1.26016,1.25170,1.24338,1.23520,1.22717,1.21930,1.21157,1.20399,1.19657,1.18931,1.18221,1.17527,1.16849,1.16187,1.15542,1.14914,1.14303,1.13709,1.13132,1.12573,1.12031,1.11507,1.11001,1.10513,1.10043,1.09592,1.09159,1.08744,1.08349,1.07972,1.07614,1.07275,1.06954,1.06654,1.06372,1.06109,1.05866,1.05642,1.05437,1.05252,1.05086,1.04939,1.04812,1.04704,1.04615,1.04545,1.04495,1.04463,1.04451,1.04457,1.04483,1.04526,1.04589,1.04670,1.04769,1.04886,1.05022,1.05175,1.05346,1.05534,1.05740,1.05963,1.06203,1.06459,1.06732,1.07021,1.07327,1.07648,1.07985,1.08337,1.08705,1.09087,1.09484,1.09896,1.10321,1.10761,1.11215,1.11681,1.12162,1.12655,1.13161,1.13679,1.14209,1.14752,1.15306,1.15872,1.16449
        1.23082,1.22249,1.21430,1.20626,1.19835,1.19060,1.18299,1.17554,1.16824,1.16109,1.15410,1.14726,1.14059,1.13408,1.12773,1.12155,1.11554,1.10969,1.10401,1.09851,1.09318,1.08803,1.08305,1.07825,1.07363,1.06919,1.06494,1.06086,1.05698,1.05327,1.04976,1.04643,1.04329,1.04034,1.03758,1.03501,1.03263,1.03044,1.02844,1.02663,1.02502,1.02359,1.02236,1.02132,1.02047,1.01980,1.01933,1.01905,1.01895,1.01904,1.01932,1.01978,1.02043,1.02126,1.02227,1.02346,1.02483,1.02637,1.02809,1.02999,1.03205,1.03429,1.03669,1.03925,1.04198,1.04488,1.04793,1.05113,1.05450,1.05801,1.06168,1.06549,1.06945,1.07355,1.07779,1.08216,1.08668,1.09133,1.09610,1.10101,1.10604,1.11120,1.11647,1.12187,1.12738,1.13300,1.13874
        1.20284,1.19464,1.18658,1.17866,1.17088,1.16324,1.15576,1.14842,1.14123,1.13419,1.12731,1.12058,1.11401,1.10760,1.10135,1.09526,1.08934,1.08359,1.07800,1.07258,1.06734,1.06227,1.05737,1.05265,1.04810,1.04374,1.03956,1.03555,1.03173,1.02809,1.02464,1.02137,1.01829,1.01539,1.01269,1.01017,1.00784,1.00570,1.00374,1.00198,1.00041,0.99902,0.99783,0.99682,0.99601,0.99538,0.99494,0.99468,0.99461,0.99473,0.99503,0.99552,0.99618,0.99703,0.99806,0.99926,1.00064,1.00220,1.00393,1.00583,1.00790,1.01013,1.01254,1.01510,1.01783,1.02072,1.02377,1.02697,1.03032,1.03383,1.03748,1.04128,1.04522,1.04930,1.05353,1.05788,1.06238,1.06700,1.07175,1.07663,1.08164,1.08676,1.09201,1.09737,1.10284,1.10843,1.11413
        1.17616,1.16808,1.16014,1.15234,1.14468,1.13716,1.12979,1.12256,1.11548,1.10855,1.10178,1.09515,1.08868,1.08237,1.07621,1.07022,1.06439,1.05872,1.05322,1.04789,1.04273,1.03774,1.03292,1.02827,1.02380,1.01950,1.01539,1.01145,1.00769,1.00412,1.00072,0.99751,0.99449,0.99165,0.98899,0.98652,0.98424,0.98215,0.98024,0.97852,0.97698,0.97564,0.97448,0.97351,0.97272,0.97212,0.97171,0.97148,0.97144,0.97158,0.97190,0.97240,0.97309,0.97395,0.97499,0.97621,0.97760,0.97917,0.98090,0.98281,0.98488,0.98712,0.98952,0.99209,0.99482,0.99770,1.00074,1.00393,1.00728,1.01077,1.01441,1.01819,1.02212,1.02618,1.03038,1.03472,1.03919,1.04379,1.04852,1.05337,1.05834,1.06344,1.06865,1.07397,1.07942,1.08497,1.09062
        1.15070,1.14275,1.13493,1.12725,1.11971,1.11230,1.10504,1.09792,1.09095,1.08412,1.07745,1.07092,1.06455,1.05833,1.05227,1.04637,1.04062,1.03504,1.02963,1.02437,1.01929,1.01438,1.00963,1.00506,1.00066,0.99643,0.99238,0.98851,0.98481,0.98130,0.97796,0.97481,0.97183,0.96905,0.96644,0.96402,0.96178,0.95973,0.95786,0.95618,0.95469,0.95338,0.95225,0.95131,0.95056,0.94999,0.94960,0.94940,0.94938,0.94954,0.94988,0.95040,0.95110,0.95198,0.95303,0.95426,0.95566,0.95723,0.95898,0.96088,0.96296,0.96520,0.96760,0.97016,0.97289,0.97576,0.97879,0.98198,0.98531,0.98879,0.99241,0.99618,1.00009,1.00413,1.00831,1.01263,1.01707,1.02164,1.02634,1.03116,1.03611,1.04117,1.04635,1.05164,1.05704,1.06256,1.06818
        1.12643,1.11860,1.11090,1.10333,1.09590,1.08861,1.08145,1.07444,1.06757,1.06084,1.05427,1.04784,1.04156,1.03543,1.02946,1.02365,1.01799,1.01249,1.00716,1.00199,0.99698,0.99214,0.98746,0.98296,0.97863,0.97447,0.97048,0.96667,0.96304,0.95958,0.95630,0.95320,0.95028,0.94754,0.94498,0.94261,0.94041,0.93840,0.93658,0.93493,0.93347,0.93220,0.93111,0.93020,0.92947,0.92893,0.92857,0.92839,0.92839,0.92857,0.92893,0.92947,0.93018,0.93107,0.93213,0.93337,0.93478,0.93636,0.93810,0.94001,0.94209,0.94433,0.94672,0.94928,0.95200,0.95486,0.95789,0.96106,0.96438,0.96784,0.97145,0.97520,0.97909,0.98311,0.98727,0.99156,0.99597,1.00052,1.00519,1.00998,1.01489,1.01992,1.02506,1.03032,1.03568,1.04116,1.04674
        1.10329,1.09557,1.08798,1.08053,1.07321,1.06602,1.05897,1.05206,1.04529,1.03866,1.03218,1.02585,1.01966,1.01363,1.00774,1.00201,0.99644,0.99102,0.98577,0.98067,0.97574,0.97097,0.96637,0.96194,0.95767,0.95357,0.94965,0.94590,0.94232,0.93892,0.93569,0.93265,0.92978,0.92709,0.92457,0.92224,0.92009,0.91812,0.91633,0.91473,0.91330,0.91206,0.91100,0.91012,0.90942,0.90890,0.90856,0.90840,0.90842,0.90862,0.90900,0.90955,0.91028,0.91118,0.91225,0.91349,0.91491,0.91649,0.91823,0.92015,0.92222,0.92446,0.92685,0.92940,0.93211,0.93497,0.93797,0.94113,0.94444,0.94788,0.95147,0.95520,0.95907,0.96307,0.96721,0.97147,0.97586,0.98038,0.98502,0.98977,0.99465,0.99965,1.00475,1.00997,1.01530,1.02073,1.02626
        1.08122,1.07361,1.06614,1.05879,1.05158,1.04449,1.03755,1.03074,1.02407,1.01754,1.01115,1.00491,0.99881,0.99287,0.98707,0.98142,0.97593,0.97059,0.96541,0.96039,0.95553,0.95084,0.94630,0.94194,0.93774,0.93370,0.92984,0.92615,0.92263,0.91928,0.91610,0.91311,0.91029,0.90764,0.90517,0.90288,0.90077,0.89884,0.89709,0.89552,0.89413,0.89291,0.89188,0.89103,0.89036,0.88986,0.88955,0.88941,0.88945,0.88966,0.89005,0.89061,0.89135,0.89226,0.89334,0.89459,0.89601,0.89759,0.89934,0.90125,0.90332,0.90555,0.90794,0.91048,0.91318,0.91602,0.91902,0.92216,0.92545,0.92888,0.93245,0.93616,0.94000,0.94398,0.94809,0.95232,0.95669,0.96117,0.96578,0.97051,0.97535,0.98031,0.98537,0.99055,0.99584,1.00123,1.00672
        1.06017,1.05268,1.04532,1.03808,1.03097,1.02399,1.01714,1.01043,1.00386,0.99742,0.99113,0.98497,0.97897,0.97310,0.96739,0.96183,0.95641,0.95115,0.94605,0.94110,0.93632,0.93169,0.92722,0.92292,0.91878,0.91481,0.91100,0.90737,0.90390,0.90061,0.89749,0.89454,0.89176,0.88916,0.88674,0.88449,0.88242,0.88052,0.87881,0.87727,0.87591,0.87473,0.87372,0.87289,0.87224,0.87177,0.87148,0.87136,0.87141,0.87164,0.87204,0.87262,0.87337,0.87428,0.87537,0.87662,0.87804,0.87962,0.88137,0.88328,0.88534,0.88757,0.88995,0.89248,0.89517,0.89800,0.90098,0.90411,0.90738,0.91079,0.91434,0.91803,0.92184,0.92580,0.92988,0.93408,0.93842,0.94287,0.94744,0.95214,0.95694,0.96186,0.96689,0.97203,0.97727,0.98262,0.98807
        1.04012,1.03273,1.02547,1.01834,1.01133,1.00445,0.99771,0.99109,0.98461,0.97827,0.97206,0.96600,0.96008,0.95430,0.94867,0.94319,0.93785,0.93267,0.92764,0.92276,0.91805,0.91349,0.90909,0.90484,0.90077,0.89686,0.89311,0.88953,0.88612,0.88287,0.87980,0.87690,0.87417,0.87161,0.86923,0.86702,0.86499,0.86313,0.86145,0.85994,0.85861,0.85746,0.85648,0.85568,0.85505,0.85460,0.85432,0.85422,0.85429,0.85453,0.85494,0.85553,0.85628,0.85720,0.85829,0.85955,0.86097,0.86255,0.86430,0.86620,0.86826,0.87048,0.87285,0.87537,0.87804,0.88086,0.88383,0.88694,0.89019,0.89358,0.89710,0.90077,0.90456,0.90848,0.91254,0.91671,0.92101,0.92544,0.92998,0.93463,0.93940,0.94428,0.94927,0.95437,0.95957,0.96487,0.97028
        1.02100,1.01372,1.00657,0.99954,0.99263,0.98585,0.97920,0.97268,0.96629,0.96004,0.95393,0.94795,0.94211,0.93642,0.93087,0.92546,0.92020,0.91509,0.91014,0.90533,0.90068,0.89619,0.89185,0.88768,0.88366,0.87981,0.87612,0.87259,0.86923,0.86604,0.86301,0.86016,0.85747,0.85496,0.85262,0.85045,0.84845,0.84663,0.84498,0.84350,0.84220,0.84107,0.84012,0.83934,0.83873,0.83830,0.83804,0.83795,0.83803,0.83829,0.83871,0.83931,0.84007,0.84099,0.84209,0.84334,0.84476,0.84634,0.84808,0.84998,0.85203,0.85424,0.85660,0.85911,0.86177,0.86457,0.86752,0.87061,0.87384,0.87721,0.88071,0.88435,0.88811,0.89201,0.89603,0.90018,0.90445,0.90883,0.91334,0.91796,0.92269,0.92753,0.93248,0.93753,0.94269,0.94795,0.95330
        1.00279,0.99562,0.98856,0.98163,0.97482,0.96814,0.96159,0.95516,0.94887,0.94270,0.93667,0.93078,0.92503,0.91941,0.91394,0.90861,0.90343,0.89840,0.89351,0.88878,0.88419,0.87977,0.87549,0.87138,0.86742,0.86362,0.85999,0.85652,0.85321,0.85006,0.84709,0.84428,0.84163,0.83916,0.83686,0.83473,0.83276,0.83097,0.82935,0.82791,0.82663,0.82553,0.82460,0.82384,0.82326,0.82284,0.82260,0.82253,0.82262,0.82289,0.82332,0.82392,0.82469,0.82562,0.82671,0.82797,0.82939,0.83096,0.83270,0.83459,0.83663,0.83883,0.84117,0.84367,0.84631,0.84910,0.85203,0.85510,0.85831,0.86165,0.86513,0.86874,0.87248,0.87634,0.88033,0.88445,0.88868,0.89303,0.89750,0.90208,0.90677,0.91157,0.91648,0.92149,0.92660,0.93181,0.93712
        0.98544,0.97837,0.97142,0.96459,0.95788,0.95129,0.94483,0.93850,0.93229,0.92621,0.92027,0.91446,0.90879,0.90326,0.89787,0.89261,0.88751,0.88254,0.87773,0.87306,0.86854,0.86418,0.85997,0.85591,0.85201,0.84827,0.84469,0.84127,0.83801,0.83492,0.83199,0.82922,0.82662,0.82419,0.82192,0.81983,0.81790,0.81614,0.81455,0.81314,0.81189,0.81081,0.80990,0.80917,0.80860,0.80820,0.80797,0.80791,0.80802,0.80829,0.80873,0.80934,0.81011,0.81104,0.81214,0.81339,0.81481,0.81638,0.81810,0.81999,0.82202,0.82420,0.82654,0.82902,0.83164,0.83441,0.83732,0.84037,0.84355,0.84687,0.85032,0.85391,0.85762,0.86145,0.86541,0.86949,0.87369,0.87800,0.88243,0.88697,0.89162,0.89638,0.90124,0.90621,0.91127,0.91644,0.92170
        0.96892,0.96196,0.95510,0.94837,0.94176,0.93526,0.92889,0.92265,0.91653,0.91054,0.90469,0.89896,0.89337,0.88792,0.88260,0.87742,0.87239,0.86750,0.86275,0.85815,0.85370,0.84940,0.84525,0.84125,0.83741,0.83372,0.83020,0.82683,0.82362,0.82057,0.81768,0.81496,0.81240,0.81001,0.80778,0.80572,0.80383,0.80210,0.80054,0.79915,0.79793,0.79687,0.79599,0.79527,0.79472,0.79434,0.79412,0.79408,0.79419,0.79448,0.79492,0.79553,0.79631,0.79724,0.79833,0.79959,0.80099,0.80256,0.80428,0.80615,0.80817,0.81034,0.81266,0.81513,0.81773,0.82048,0.82337,0.82639,0.82955,0.83285,0.83627,0.83982,0.84350,0.84730,0.85123,0.85527,0.85943,0.86371,0.86810,0.87260,0.87721,0.88192,0.88674,0.89166,0.89668,0.90179,0.90700
        0.95320,0.94633,0.93958,0.93294,0.92642,0.92002,0.91375,0.90759,0.90156,0.89566,0.88988,0.88424,0.87873,0.87335,0.86811,0.86301,0.85805,0.85322,0.84855,0.84401,0.83963,0.83539,0.83130,0.82736,0.82358,0.81994,0.81647,0.81315,0.80999,0.80699,0.80415,0.80147,0.79895,0.79659,0.79440,0.79238,0.79051,0.78882,0.78729,0.78592,0.78473,0.78369,0.78283,0.78213,0.78160,0.78123,0.78103,0.78099,0.78112,0.78141,0.78186,0.78247,0.78325,0.78418,0.78527,0.78652,0.78792,0.78948,0.79119,0.79305,0.79506,0.79722,0.79952,0.80196,0.80455,0.80728,0.81014,0.81314,0.81628,0.81954,0.82294,0.82646,0.83011,0.83387,0.83776,0.84177,0.84589,0.85013,0.85448,0.85894,0.86350,0.86817,0.87294,0.87782,0.88279,0.88785,0.89301
        0.93824,0.93148,0.92482,0.91828,0.91185,0.90554,0.89935,0.89329,0.88734,0.88152,0.87583,0.87027,0.86484,0.85954,0.85437,0.84934,0.84445,0.83970,0.83509,0.83062,0.82630,0.82212,0.81809,0.81421,0.81048,0.80690,0.80348,0.80021,0.79710,0.79414,0.79135,0.78871,0.78623,0.78391,0.78176,0.77976,0.77793,0.77627,0.77476,0.77342,0.77225,0.77124,0.77039,0.76971,0.76920,0.76884,0.76865,0.76862,0.76876,0.76906,0.76951,0.77013,0.77090,0.77183,0.77292,0.77417,0.77556,0.77711,0.77881,0.78066,0.78265,0.78479,0.78708,0.78951,0.79207,0.79478,0.79762,0.80059,0.80370,0.80694,0.81030,0.81379,0.81740,0.82114,0.82499,0.82896,0.83304,0.83724,0.84155,0.84596,0.85048,0.85510,0.85983,0.86465,0.86958,0.87459,0.87970
        0.92402,0.91735,0.91079,0.90434,0.89800,0.89179,0.88569,0.87971,0.87385,0.86811,0.86250,0.85702,0.85167,0.84644,0.84135,0.83640,0.83157,0.82689,0.82235,0.81794,0.81368,0.80957,0.80560,0.80177,0.79810,0.79458,0.79120,0.78798,0.78492,0.78201,0.77925,0.77665,0.77421,0.77193,0.76981,0.76785,0.76605,0.76442,0.76294,0.76163,0.76048,0.75949,0.75866,0.75800,0.75749,0.75715,0.75697,0.75695,0.75710,0.75740,0.75786,0.75847,0.75925,0.76018,0.76126,0.76250,0.76389,0.76542,0.76711,0.76895,0.77093,0.77305,0.77532,0.77772,0.78027,0.78295,0.78576,0.78871,0.79179,0.79500,0.79833,0.80179,0.80536,0.80906,0.81288,0.81681,0.82085,0.82501,0.82927,0.83364,0.83812,0.84269,0.84737,0.85214,0.85702,0.86198,0.86704
        0.91050,0.90392,0.89746,0.89110,0.88486,0.87873,0.87272,0.86682,0.86105,0.85540,0.84987,0.84447,0.83919,0.83404,0.82902,0.82414,0.81939,0.81477,0.81029,0.80596,0.80176,0.79770,0.79379,0.79002,0.78640,0.78293,0.77961,0.77644,0.77342,0.77055,0.76784,0.76528,0.76288,0.76064,0.75855,0.75662,0.75485,0.75324,0.75179,0.75050,0.74938,0.74841,0.74760,0.74695,0.74646,0.74613,0.74596,0.74595,0.74610,0.74640,0.74687,0.74748,0.74826,0.74918,0.75026,0.75149,0.75287,0.75440,0.75607,0.75789,0.75986,0.76196,0.76421,0.76659,0.76911,0.77177,0.77456,0.77748,0.78053,0.78370,0.78700,0.79042,0.79397,0.79763,0.80140,0.80529,0.80930,0.81341,0.81763,0.82195,0.82638,0.83091,0.83554,0.84026,0.84508,0.85000,0.85500
        0.89765,0.89117,0.88480,0.87854,0.87238,0.86634,0.86042,0.85461,0.84892,0.84335,0.83790,0.83258,0.82738,0.82230,0.81736,0.81254,0.80786,0.80331,0.79890,0.79463,0.79049,0.78649,0.78264,0.77893,0.77536,0.77194,0.76867,0.76555,0.76257,0.75975,0.75708,0.75456,0.75220,0.74999,0.74794,0.74604,0.74430,0.74272,0.74130,0.74003,0.73892,0.73797,0.73718,0.73655,0.73607,0.73576,0.73560,0.73559,0.73575,0.73605,0.73652,0.73713,0.73790,0.73882,0.73990,0.74112,0.74249,0.74400,0.74566,0.74747,0.74941,0.75150,0.75373,0.75609,0.75858,0.76122,0.76398,0.76687,0.76988,0.77303,0.77629,0.77968,0.78319,0.78681,0.79055,0.79440,0.79836,0.80242,0.80660,0.81088,0.81526,0.81974,0.82432,0.82899,0.83376,0.83862,0.84356
        0.88546,0.87907,0.87279,0.86662,0.86055,0.85460,0.84876,0.84304,0.83743,0.83194,0.82657,0.82133,0.81620,0.81120,0.80633,0.80159,0.79697,0.79249,0.78815,0.78393,0.77986,0.77592,0.77212,0.76847,0.76496,0.76159,0.75836,0.75529,0.75236,0.74958,0.74695,0.74447,0.74215,0.73997,0.73796,0.73609,0.73438,0.73282,0.73143,0.73018,0.72909,0.72816,0.72739,0.72677,0.72631,0.72600,0.72585,0.72585,0.72601,0.72632,0.72678,0.72740,0.72816,0.72908,0.73014,0.73136,0.73271,0.73422,0.73586,0.73765,0.73958,0.74164,0.74385,0.74619,0.74866,0.75126,0.75399,0.75685,0.75984,0.76295,0.76618,0.76953,0.77300,0.77658,0.78028,0.78409,0.78800,0.79203,0.79616,0.80039,0.80472,0.80915,0.81368,0.81830,0.82301,0.82782,0.83271
        0.87388,0.86759,0.86140,0.85532,0.84934,0.84348,0.83773,0.83209,0.82656,0.82115,0.81586,0.81069,0.80564,0.80072,0.79592,0.79124,0.78670,0.78228,0.77800,0.77385,0.76984,0.76596,0.76222,0.75862,0.75516,0.75184,0.74867,0.74564,0.74275,0.74002,0.73743,0.73499,0.73270,0.73056,0.72857,0.72674,0.72506,0.72353,0.72215,0.72093,0.71987,0.71895,0.71819,0.71759,0.71714,0.71684,0.71670,0.71671,0.71687,0.71718,0.71764,0.71825,0.71902,0.71992,0.72098,0.72218,0.72353,0.72502,0.72665,0.72842,0.73033,0.73237,0.73455,0.73687,0.73931,0.74189,0.74459,0.74742,0.75037,0.75345,0.75664,0.75995,0.76338,0.76693,0.77058,0.77434,0.77822,0.78220,0.78628,0.79046,0.79474,0.79912,0.80360,0.80817,0.81283,0.81757,0.82241
        0.86291,0.85671,0.85061,0.84462,0.83873,0.83295,0.82728,0.82173,0.81628,0.81095,0.80574,0.80065,0.79567,0.79082,0.78609,0.78149,0.77701,0.77266,0.76844,0.76435,0.76040,0.75658,0.75290,0.74935,0.74594,0.74268,0.73955,0.73657,0.73373,0.73103,0.72849,0.72609,0.72383,0.72173,0.71977,0.71797,0.71631,0.71481,0.71346,0.71226,0.71121,0.71032,0.70957,0.70898,0.70854,0.70825,0.70812,0.70813,0.70829,0.70861,0.70907,0.70968,0.71043,0.71134,0.71238,0.71357,0.71491,0.71638,0.71799,0.71975,0.72163,0.72366,0.72581,0.72810,0.73052,0.73307,0.73574,0.73854,0.74145,0.74449,0.74765,0.75093,0.75432,0.75782,0.76143,0.76515,0.76898,0.77291,0.77694,0.78108,0.78531,0.78964,0.79406,0.79857,0.80318,0.80787,0.81265
        0.85251,0.84640,0.84039,0.83449,0.82869,0.82299,0.81741,0.81194,0.80657,0.80132,0.79619,0.79117,0.78627,0.78149,0.77683,0.77230,0.76788,0.76360,0.75945,0.75542,0.75153,0.74776,0.74414,0.74064,0.73729,0.73407,0.73099,0.72806,0.72526,0.72261,0.72010,0.71774,0.71552,0.71345,0.71153,0.70975,0.70813,0.70665,0.70532,0.70414,0.70311,0.70224,0.70151,0.70093,0.70050,0.70022,0.70009,0.70011,0.70027,0.70058,0.70104,0.70165,0.70240,0.70329,0.70433,0.70551,0.70683,0.70829,0.70988,0.71162,0.71348,0.71548,0.71761,0.71988,0.72227,0.72478,0.72742,0.73019,0.73307,0.73607,0.73919,0.74243,0.74578,0.74924,0.75281,0.75648,0.76026,0.76415,0.76813,0.77222,0.77640,0.78067,0.78504,0.78950,0.79405,0.79869,0.80341
        0.84266,0.83664,0.83072,0.82491,0.81919,0.81358,0.80808,0.80269,0.79741,0.79224,0.78718,0.78224,0.77741,0.77270,0.76811,0.76365,0.75930,0.75508,0.75099,0.74703,0.74319,0.73949,0.73592,0.73248,0.72917,0.72601,0.72298,0.72009,0.71733,0.71472,0.71226,0.70993,0.70775,0.70571,0.70382,0.70207,0.70047,0.69902,0.69772,0.69656,0.69555,0.69468,0.69397,0.69340,0.69298,0.69271,0.69259,0.69261,0.69278,0.69309,0.69354,0.69415,0.69489,0.69578,0.69680,0.69797,0.69927,0.70071,0.70229,0.70400,0.70585,0.70783,0.70993,0.71217,0.71453,0.71701,0.71962,0.72235,0.72520,0.72816,0.73125,0.73444,0.73775,0.74116,0.74469,0.74832,0.75205,0.75589,0.75982,0.76386,0.76799,0.77221,0.77652,0.78093,0.78542,0.79000,0.79466
        0.83334,0.82741,0.82158,0.81585,0.81023,0.80470,0.79928,0.79397,0.78877,0.78368,0.77869,0.77383,0.76907,0.76444,0.75992,0.75552,0.75124,0.74709,0.74306,0.73915,0.73538,0.73173,0.72821,0.72483,0.72158,0.71846,0.71548,0.71263,0.70992,0.70735,0.70492,0.70264,0.70049,0.69849,0.69662,0.69491,0.69333,0.69190,0.69062,0.68948,0.68849,0.68764,0.68694,0.68639,0.68598,0.68571,0.68559,0.68562,0.68579,0.68610,0.68655,0.68715,0.68788,0.68876,0.68977,0.69093,0.69222,0.69364,0.69520,0.69689,0.69871,0.70066,0.70274,0.70495,0.70728,0.70974,0.71231,0.71501,0.71782,0.72075,0.72379,0.72694,0.73021,0.73358,0.73706,0.74064,0.74433,0.74812,0.75200,0.75598,0.76006,0.76423,0.76849,0.77284,0.77727,0.78179,0.78640
        0.82453,0.81869,0.81295,0.80731,0.80176,0.79632,0.79099,0.78576,0.78063,0.77562,0.77071,0.76592,0.76124,0.75667,0.75222,0.74789,0.74368,0.73959,0.73562,0.73178,0.72806,0.72447,0.72101,0.71768,0.71447,0.71141,0.70847,0.70567,0.70300,0.70048,0.69809,0.69584,0.69372,0.69175,0.68992,0.68823,0.68668,0.68528,0.68402,0.68290,0.68192,0.68109,0.68041,0.67986,0.67946,0.67920,0.67909,0.67911,0.67928,0.67959,0.68004,0.68063,0.68136,0.68223,0.68323,0.68437,0.68564,0.68705,0.68859,0.69026,0.69205,0.69398,0.69603,0.69821,0.70051,0.70293,0.70547,0.70813,0.71091,0.71380,0.71680,0.71991,0.72314,0.72646,0.72990,0.73343,0.73707,0.74081,0.74464,0.74857,0.75259,0.75671,0.76091,0.76521,0.76958,0.77405,0.77859
        0.81621,0.81046,0.80480,0.79925,0.79379,0.78843,0.78318,0.77803,0.77298,0.76804,0.76321,0.75849,0.75388,0.74939,0.74501,0.74074,0.73660,0.73257,0.72867,0.72488,0.72122,0.71769,0.71428,0.71100,0.70785,0.70483,0.70194,0.69918,0.69656,0.69407,0.69172,0.68951,0.68743,0.68549,0.68369,0.68203,0.68051,0.67913,0.67789,0.67679,0.67583,0.67501,0.67434,0.67380,0.67341,0.67316,0.67305,0.67308,0.67324,0.67355,0.67400,0.67458,0.67530,0.67616,0.67715,0.67827,0.67953,0.68092,0.68243,0.68408,0.68586,0.68776,0.68978,0.69193,0.69420,0.69659,0.69909,0.70172,0.70445,0.70730,0.71027,0.71334,0.71651,0.71980,0.72318,0.72667,0.73026,0.73395,0.73773,0.74161,0.74558,0.74964,0.75378,0.75802,0.76234,0.76674,0.77123
        0.80836,0.80269,0.79713,0.79165,0.78628,0.78100,0.77583,0.77076,0.76579,0.76093,0.75617,0.75153,0.74699,0.74256,0.73825,0.73406,0.72997,0.72601,0.72217,0.71844,0.71484,0.71136,0.70801,0.70478,0.70168,0.69871,0.69587,0.69315,0.69057,0.68813,0.68581,0.68363,0.68159,0.67968,0.67791,0.67628,0.67478,0.67342,0.67220,0.67112,0.67018,0.66938,0.66872,0.66819,0.66781,0.66756,0.66745,0.66748,0.66765,0.66796,0.66840,0.66897,0.66968,0.67053,0.67151,0.67262,0.67386,0.67522,0.67672,0.67835,0.68010,0.68197,0.68397,0.68608,0.68832,0.69068,0.69315,0.69574,0.69843,0.70124,0.70416,0.70719,0.71033,0.71356,0.71690,0.72034,0.72388,0.72752,0.73125,0.73507,0.73899,0.74299,0.74708,0.75126,0.75552,0.75987,0.76429
        0.80095,0.79538,0.78990,0.78451,0.77922,0.77402,0.76893,0.76394,0.75905,0.75426,0.74958,0.74501,0.74054,0.73618,0.73194,0.72781,0.72379,0.71989,0.71611,0.71244,0.70890,0.70548,0.70218,0.69900,0.69595,0.69303,0.69023,0.68756,0.68502,0.68261,0.68034,0.67820,0.67618,0.67431,0.67257,0.67096,0.66949,0.66815,0.66695,0.66589,0.66497,0.66418,0.66353,0.66301,0.66264,0.66240,0.66229,0.66232,0.66249,0.66279,0.66322,0.66379,0.66449,0.66533,0.66629,0.66739,0.66861,0.66996,0.67143,0.67303,0.67476,0.67661,0.67857,0.68066,0.68287,0.68519,0.68762,0.69017,0.69283,0.69560,0.69848,0.70146,0.70455,0.70774,0.71104,0.71443,0.71792,0.72150,0.72518,0.72895,0.73281,0.73676,0.74079,0.74491,0.74911,0.75340,0.75776
        0.79398,0.78849,0.78310,0.77779,0.77258,0.76747,0.76246,0.75754,0.75273,0.74802,0.74341,0.73891,0.73451,0.73023,0.72605,0.72199,0.71803,0.71419,0.71047,0.70687,0.70338,0.70001,0.69676,0.69364,0.69064,0.68776,0.68501,0.68238,0.67989,0.67752,0.67528,0.67317,0.67120,0.66935,0.66764,0.66606,0.66461,0.66330,0.66212,0.66107,0.66017,0.65939,0.65875,0.65825,0.65788,0.65764,0.65754,0.65757,0.65773,0.65803,0.65846,0.65902,0.65971,0.66053,0.66148,0.66256,0.66377,0.66509,0.66655,0.66813,0.66982,0.67164,0.67358,0.67564,0.67781,0.68010,0.68250,0.68501,0.68763,0.69036,0.69320,0.69614,0.69918,0.70232,0.70557,0.70891,0.71235,0.71588,0.71951,0.72322,0.72703,0.73092,0.73490,0.73896,0.74310,0.74732,0.75163
        0.78743,0.78202,0.77671,0.77149,0.76636,0.76133,0.75640,0.75156,0.74682,0.74218,0.73765,0.73322,0.72889,0.72468,0.72057,0.71657,0.71268,0.70890,0.70524,0.70169,0.69826,0.69495,0.69175,0.68868,0.68573,0.68290,0.68019,0.67761,0.67515,0.67282,0.67062,0.66855,0.66660,0.66479,0.66310,0.66155,0.66013,0.65884,0.65768,0.65665,0.65576,0.65500,0.65437,0.65387,0.65351,0.65328,0.65318,0.65321,0.65337,0.65367,0.65409,0.65464,0.65532,0.65613,0.65707,0.65813,0.65931,0.66062,0.66205,0.66361,0.66528,0.66707,0.66898,0.67100,0.67314,0.67539,0.67776,0.68023,0.68281,0.68550,0.68829,0.69119,0.69419,0.69729,0.70048,0.70377,0.70716,0.71064,0.71421,0.71787,0.72162,0.72546,0.72938,0.73338,0.73746,0.74163,0.74587
        0.78127,0.77595,0.77072,0.76558,0.76054,0.75558,0.75073,0.74597,0.74130,0.73674,0.73228,0.72792,0.72366,0.71951,0.71547,0.71154,0.70771,0.70399,0.70039,0.69690,0.69353,0.69027,0.68713,0.68410,0.68120,0.67842,0.67575,0.67321,0.67080,0.66851,0.66634,0.66430,0.66239,0.66061,0.65895,0.65742,0.65602,0.65476,0.65362,0.65261,0.65173,0.65098,0.65036,0.64987,0.64952,0.64929,0.64919,0.64922,0.64938,0.64967,0.65009,0.65063,0.65130,0.65210,0.65302,0.65406,0.65523,0.65652,0.65793,0.65946,0.66110,0.66287,0.66474,0.66674,0.66884,0.67106,0.67339,0.67582,0.67836,0.68101,0.68376,0.68661,0.68956,0.69261,0.69576,0.69900,0.70234,0.70577,0.70928,0.71289,0.71658,0.72036,0.72422,0.72817,0.73219,0.73629,0.74047
        0.77549,0.77026,0.76511,0.76005,0.75509,0.75021,0.74543,0.74075,0.73616,0.73167,0.72728,0.72299,0.71881,0.71472,0.71075,0.70688,0.70311,0.69946,0.69591,0.69248,0.68916,0.68596,0.68287,0.67989,0.67704,0.67430,0.67168,0.66919,0.66681,0.66456,0.66243,0.66042,0.65854,0.65679,0.65516,0.65366,0.65228,0.65103,0.64991,0.64892,0.64806,0.64732,0.64672,0.64624,0.64588,0.64566,0.64556,0.64560,0.64575,0.64604,0.64645,0.64698,0.64764,0.64842,0.64933,0.65036,0.65150,0.65277,0.65416,0.65566,0.65728,0.65901,0.66086,0.66282,0.66489,0.66708,0.66937,0.67176,0.67426,0.67687,0.67957,0.68238,0.68529,0.68829,0.69139,0.69458,0.69787,0.70124,0.70471,0.70826,0.71189,0.71562,0.71942,0.72330,0.72727,0.73131,0.73543
        0.77008,0.76493,0.75986,0.75489,0.75000,0.74520,0.74050,0.73589,0.73138,0.72696,0.72264,0.71843,0.71431,0.71029,0.70638,0.70257,0.69887,0.69527,0.69179,0.68841,0.68515,0.68200,0.67896,0.67603,0.67323,0.67053,0.66796,0.66551,0.66317,0.66096,0.65886,0.65689,0.65504,0.65332,0.65172,0.65024,0.64889,0.64766,0.64656,0.64558,0.64473,0.64401,0.64341,0.64294,0.64259,0.64237,0.64228,0.64231,0.64246,0.64274,0.64315,0.64367,0.64432,0.64509,0.64598,0.64699,0.64812,0.64936,0.65072,0.65220,0.65380,0.65550,0.65732,0.65925,0.66128,0.66343,0.66568,0.66804,0.67050,0.67306,0.67573,0.67849,0.68135,0.68430,0.68735,0.69049,0.69373,0.69705,0.70046,0.70396,0.70754,0.71120,0.71495,0.71877,0.72268,0.72666,0.73071
        0.76502,0.75995,0.75496,0.75007,0.74526,0.74054,0.73592,0.73138,0.72694,0.72260,0.71835,0.71420,0.71015,0.70620,0.70235,0.69860,0.69496,0.69143,0.68800,0.68468,0.68147,0.67837,0.67538,0.67251,0.66975,0.66710,0.66457,0.66216,0.65986,0.65769,0.65563,0.65369,0.65187,0.65018,0.64860,0.64715,0.64582,0.64461,0.64353,0.64257,0.64174,0.64102,0.64044,0.63997,0.63963,0.63941,0.63932,0.63935,0.63950,0.63978,0.64017,0.64069,0.64132,0.64208,0.64295,0.64394,0.64505,0.64628,0.64762,0.64907,0.65063,0.65231,0.65410,0.65599,0.65800,0.66011,0.66232,0.66464,0.66706,0.66958,0.67220,0.67492,0.67773,0.68064,0.68364,0.68673,0.68991,0.69318,0.69654,0.69998,0.70350,0.70711,0.71080,0.71456,0.71841,0.72233,0.72632
        0.76029,0.75530,0.75040,0.74558,0.74085,0.73621,0.73166,0.72720,0.72283,0.71856,0.71438,0.71030,0.70631,0.70243,0.69864,0.69496,0.69138,0.68791,0.68454,0.68127,0.67812,0.67507,0.67213,0.66931,0.66659,0.66399,0.66150,0.65913,0.65687,0.65473,0.65271,0.65080,0.64902,0.64735,0.64580,0.64437,0.64307,0.64188,0.64082,0.63987,0.63905,0.63835,0.63777,0.63732,0.63698,0.63677,0.63667,0.63670,0.63685,0.63712,0.63750,0.63801,0.63863,0.63938,0.64023,0.64121,0.64230,0.64350,0.64482,0.64624,0.64778,0.64943,0.65118,0.65305,0.65502,0.65709,0.65927,0.66155,0.66392,0.66640,0.66898,0.67165,0.67442,0.67728,0.68023,0.68327,0.68640,0.68962,0.69292,0.69631,0.69978,0.70333,0.70695,0.71066,0.71445,0.71830,0.72223
        0.75588,0.75098,0.74615,0.74141,0.73676,0.73219,0.72772,0.72333,0.71903,0.71483,0.71072,0.70671,0.70279,0.69897,0.69525,0.69163,0.68811,0.68469,0.68138,0.67817,0.67507,0.67207,0.66918,0.66641,0.66374,0.66118,0.65874,0.65640,0.65418,0.65208,0.65009,0.64822,0.64646,0.64482,0.64330,0.64190,0.64061,0.63945,0.63840,0.63747,0.63666,0.63597,0.63541,0.63496,0.63462,0.63441,0.63432,0.63435,0.63449,0.63475,0.63513,0.63563,0.63624,0.63697,0.63781,0.63877,0.63984,0.64102,0.64231,0.64371,0.64522,0.64684,0.64856,0.65040,0.65233,0.65437,0.65651,0.65875,0.66108,0.66352,0.66605,0.66868,0.67140,0.67421,0.67711,0.68010,0.68318,0.68635,0.68960,0.69293,0.69634,0.69983,0.70340,0.70705,0.71078,0.71457,0.71844
        0.75179,0.74696,0.74221,0.73755,0.73297,0.72848,0.72408,0.71976,0.71554,0.71141,0.70737,0.70342,0.69957,0.69581,0.69215,0.68859,0.68513,0.68177,0.67852,0.67536,0.67231,0.66937,0.66653,0.66380,0.66117,0.65866,0.65626,0.65397,0.65178,0.64972,0.64776,0.64592,0.64419,0.64258,0.64109,0.63971,0.63844,0.63730,0.63627,0.63535,0.63456,0.63388,0.63332,0.63288,0.63255,0.63234,0.63225,0.63228,0.63242,0.63267,0.63304,0.63353,0.63413,0.63484,0.63567,0.63661,0.63766,0.63881,0.64008,0.64146,0.64294,0.64453,0.64623,0.64802,0.64992,0.65192,0.65403,0.65623,0.65852,0.66092,0.66341,0.66599,0.66866,0.67143,0.67428,0.67722,0.68025,0.68336,0.68655,0.68983,0.69319,0.69662,0.70014,0.70373,0.70739,0.71113,0.71493
        0.74798,0.74323,0.73856,0.73398,0.72948,0.72506,0.72073,0.71649,0.71233,0.70827,0.70429,0.70041,0.69663,0.69293,0.68934,0.68584,0.68244,0.67913,0.67593,0.67283,0.66983,0.66694,0.66415,0.66146,0.65889,0.65642,0.65405,0.65180,0.64966,0.64763,0.64570,0.64390,0.64220,0.64061,0.63914,0.63779,0.63654,0.63542,0.63440,0.63351,0.63272,0.63206,0.63151,0.63107,0.63075,0.63054,0.63045,0.63047,0.63061,0.63086,0.63122,0.63170,0.63229,0.63298,0.63379,0.63471,0.63574,0.63688,0.63812,0.63947,0.64093,0.64249,0.64415,0.64592,0.64778,0.64975,0.65181,0.65397,0.65623,0.65858,0.66103,0.66356,0.66619,0.66891,0.67171,0.67460,0.67758,0.68064,0.68378,0.68700,0.69030,0.69368,0.69714,0.70067,0.70427,0.70795,0.71170
        0.74446,0.73978,0.73519,0.73068,0.72626,0.72191,0.71765,0.71348,0.70940,0.70540,0.70149,0.69768,0.69396,0.69033,0.68679,0.68335,0.68001,0.67676,0.67361,0.67057,0.66762,0.66478,0.66203,0.65940,0.65686,0.65443,0.65211,0.64990,0.64779,0.64580,0.64391,0.64213,0.64046,0.63890,0.63746,0.63612,0.63490,0.63379,0.63280,0.63192,0.63115,0.63049,0.62995,0.62951,0.62920,0.62899,0.62890,0.62892,0.62905,0.62930,0.62965,0.63012,0.63069,0.63138,0.63217,0.63307,0.63408,0.63520,0.63642,0.63774,0.63917,0.64070,0.64233,0.64407,0.64590,0.64783,0.64985,0.65198,0.65419,0.65650,0.65890,0.66140,0.66398,0.66665,0.66940,0.67224,0.67517,0.67817,0.68126,0.68443,0.68767,0.69100,0.69440,0.69787,0.70141,0.70503,0.70871
        0.74120,0.73661,0.73209,0.72765,0.72330,0.71903,0.71484,0.71074,0.70672,0.70280,0.69895,0.69520,0.69154,0.68798,0.68450,0.68112,0.67783,0.67464,0.67155,0.66855,0.66566,0.66286,0.66017,0.65758,0.65509,0.65270,0.65042,0.64825,0.64618,0.64421,0.64236,0.64061,0.63897,0.63744,0.63602,0.63471,0.63351,0.63242,0.63144,0.63057,0.62981,0.62916,0.62863,0.62820,0.62789,0.62769,0.62759,0.62761,0.62774,0.62798,0.62833,0.62878,0.62934,0.63001,0.63079,0.63167,0.63266,0.63376,0.63495,0.63625,0.63765,0.63915,0.64076,0.64246,0.64425,0.64615,0.64814,0.65022,0.65240,0.65466,0.65702,0.65947,0.66200,0.66463,0.66733,0.67012,0.67300,0.67595,0.67899,0.68210,0.68529,0.68856,0.69190,0.69531,0.69880,0.70236,0.70598
        0.73820,0.73368,0.72924,0.72488,0.72060,0.71640,0.71228,0.70825,0.70430,0.70044,0.69666,0.69298,0.68938,0.68587,0.68246,0.67913,0.67590,0.67277,0.66973,0.66678,0.66394,0.66119,0.65854,0.65600,0.65355,0.65121,0.64896,0.64683,0.64479,0.64286,0.64104,0.63932,0.63771,0.63621,0.63481,0.63352,0.63234,0.63127,0.63030,0.62945,0.62870,0.62807,0.62754,0.62712,0.62681,0.62661,0.62652,0.62653,0.62666,0.62689,0.62723,0.62767,0.62822,0.62888,0.62964,0.63050,0.63147,0.63254,0.63372,0.63499,0.63636,0.63784,0.63941,0.64108,0.64284,0.64470,0.64665,0.64869,0.65083,0.65306,0.65537,0.65777,0.66026,0.66284,0.66550,0.66824,0.67106,0.67397,0.67695,0.68001,0.68314,0.68635,0.68964,0.69299,0.69642,0.69992,0.70348
        0.73545,0.73100,0.72664,0.72235,0.71814,0.71401,0.70996,0.70600,0.70212,0.69832,0.69461,0.69098,0.68745,0.68400,0.68064,0.67738,0.67420,0.67112,0.66813,0.66524,0.66245,0.65975,0.65715,0.65464,0.65224,0.64994,0.64773,0.64563,0.64363,0.64174,0.63995,0.63826,0.63667,0.63520,0.63382,0.63256,0.63139,0.63034,0.62939,0.62855,0.62782,0.62719,0.62667,0.62626,0.62595,0.62575,0.62566,0.62567,0.62579,0.62602,0.62634,0.62678,0.62732,0.62796,0.62870,0.62955,0.63050,0.63155,0.63270,0.63395,0.63529,0.63674,0.63828,0.63991,0.64164,0.64347,0.64538,0.64739,0.64948,0.65167,0.65394,0.65630,0.65875,0.66127,0.66388,0.66658,0.66935,0.67220,0.67513,0.67814,0.68122,0.68437,0.68760,0.69090,0.69427,0.69771,0.70121
        0.73293,0.72856,0.72426,0.72005,0.71591,0.71185,0.70787,0.70397,0.70016,0.69642,0.69278,0.68921,0.68574,0.68235,0.67905,0.67584,0.67272,0.66969,0.66676,0.66392,0.66117,0.65852,0.65596,0.65350,0.65114,0.64888,0.64671,0.64465,0.64269,0.64082,0.63906,0.63740,0.63585,0.63439,0.63304,0.63180,0.63066,0.62962,0.62869,0.62786,0.62714,0.62652,0.62601,0.62560,0.62530,0.62510,0.62500,0.62501,0.62513,0.62535,0.62567,0.62609,0.62662,0.62725,0.62797,0.62880,0.62973,0.63076,0.63189,0.63311,0.63443,0.63584,0.63735,0.63896,0.64065,0.64244,0.64432,0.64629,0.64835,0.65049,0.65272,0.65504,0.65744,0.65992,0.66248,0.66513,0.66785,0.67065,0.67353,0.67648,0.67951,0.68261,0.68578,0.68902,0.69233,0.69571,0.69916
        0.73063,0.72634,0.72211,0.71797,0.71390,0.70991,0.70600,0.70216,0.69841,0.69474,0.69116,0.68766,0.68424,0.68091,0.67767,0.67452,0.67145,0.66848,0.66559,0.66280,0.66010,0.65750,0.65498,0.65257,0.65025,0.64802,0.64590,0.64387,0.64194,0.64011,0.63838,0.63675,0.63522,0.63379,0.63246,0.63124,0.63012,0.62910,0.62818,0.62736,0.62665,0.62604,0.62554,0.62514,0.62484,0.62464,0.62455,0.62455,0.62466,0.62487,0.62519,0.62560,0.62611,0.62673,0.62744,0.62825,0.62916,0.63017,0.63127,0.63247,0.63376,0.63515,0.63663,0.63820,0.63986,0.64162,0.64346,0.64539,0.64741,0.64951,0.65170,0.65397,0.65633,0.65876,0.66128,0.66387,0.66655,0.66930,0.67212,0.67502,0.67800,0.68104,0.68416,0.68735,0.69060,0.69392,0.69731
        0.72855,0.72433,0.72017,0.71610,0.71210,0.70817,0.70433,0.70056,0.69688,0.69327,0.68975,0.68631,0.68295,0.67968,0.67649,0.67339,0.67038,0.66746,0.66462,0.66188,0.65923,0.65667,0.65420,0.65182,0.64954,0.64736,0.64527,0.64328,0.64138,0.63958,0.63788,0.63628,0.63478,0.63337,0.63207,0.63087,0.62976,0.62876,0.62786,0.62705,0.62635,0.62575,0.62526,0.62486,0.62456,0.62437,0.62427,0.62428,0.62438,0.62459,0.62489,0.62529,0.62579,0.62639,0.62709,0.62788,0.62877,0.62976,0.63084,0.63201,0.63328,0.63464,0.63609,0.63763,0.63926,0.64098,0.64278,0.64468,0.64665,0.64872,0.65086,0.65309,0.65541,0.65780,0.66027,0.66281,0.66544,0.66814,0.67091,0.67376,0.67668,0.67967,0.68274,0.68587,0.68906,0.69233,0.69566
        0.72667,0.72252,0.71844,0.71443,0.71050,0.70664,0.70286,0.69916,0.69553,0.69199,0.68853,0.68514,0.68185,0.67863,0.67550,0.67245,0.66949,0.66662,0.66384,0.66114,0.65854,0.65602,0.65360,0.65127,0.64903,0.64688,0.64483,0.64287,0.64100,0.63924,0.63757,0.63599,0.63451,0.63313,0.63185,0.63067,0.62958,0.62860,0.62771,0.62692,0.62623,0.62564,0.62515,0.62475,0.62446,0.62427,0.62417,0.62417,0.62427,0.62447,0.62477,0.62516,0.62565,0.62623,0.62691,0.62769,0.62856,0.62952,0.63058,0.63173,0.63297,0.63430,0.63572,0.63723,0.63883,0.64051,0.64228,0.64414,0.64608,0.64810,0.65021,0.65240,0.65467,0.65701,0.65944,0.66194,0.66451,0.66716,0.66989,0.67268,0.67555,0.67849,0.68150,0.68457,0.68771,0.69092,0.69419
        0.72499,0.72090,0.71689,0.71295,0.70908,0.70529,0.70158,0.69794,0.69438,0.69089,0.68749,0.68417,0.68093,0.67777,0.67469,0.67170,0.66879,0.66597,0.66323,0.66058,0.65802,0.65555,0.65317,0.65088,0.64868,0.64657,0.64455,0.64263,0.64080,0.63906,0.63742,0.63587,0.63442,0.63306,0.63180,0.63064,0.62957,0.62860,0.62773,0.62695,0.62627,0.62569,0.62520,0.62481,0.62452,0.62433,0.62423,0.62423,0.62433,0.62452,0.62481,0.62519,0.62567,0.62624,0.62690,0.62766,0.62851,0.62945,0.63049,0.63161,0.63283,0.63413,0.63552,0.63700,0.63857,0.64022,0.64195,0.64377,0.64568,0.64766,0.64973,0.65187,0.65410,0.65640,0.65878,0.66123,0.66376,0.66636,0.66904,0.67178,0.67460,0.67748,0.68044,0.68346,0.68654,0.68969,0.69291
        0.72349,0.71947,0.71553,0.71165,0.70785,0.70413,0.70047,0.69690,0.69340,0.68997,0.68663,0.68336,0.68018,0.67707,0.67405,0.67111,0.66825,0.66548,0.66279,0.66019,0.65768,0.65525,0.65291,0.65066,0.64849,0.64642,0.64444,0.64255,0.64075,0.63905,0.63743,0.63591,0.63448,0.63315,0.63191,0.63077,0.62972,0.62876,0.62790,0.62714,0.62647,0.62589,0.62541,0.62503,0.62474,0.62455,0.62445,0.62445,0.62454,0.62472,0.62500,0.62537,0.62584,0.62640,0.62705,0.62779,0.62862,0.62954,0.63055,0.63165,0.63284,0.63412,0.63548,0.63693,0.63846,0.64008,0.64178,0.64357,0.64543,0.64738,0.64940,0.65151,0.65369,0.65595,0.65828,0.66069,0.66317,0.66572,0.66835,0.67104,0.67381,0.67664,0.67954,0.68251,0.68554,0.68863,0.69179
        """

        # Tách theo dòng → mỗi dòng là 1 list float
        rows = [list(map(float, line.split(',')))
                for line in raw.strip().split('\n')]

        arr = np.array(rows, dtype=np.float32)
        arr = arr[np.newaxis, np.newaxis, :, :]
        print("check",obs_add_cmd2)
        depth1 = self.compute_depth_latent(arr, obs_add_cmd2)
        print("hehe",depth1)
        obs = np.concatenate([obs,depth1])
        # Check if this is the first recorded observation
        if self.is_first_rec_obs:
            # Calculate the total size of the encoder input
            input_size = np.prod(self.encoder_input_shapes[0])
            
            # Initialize the proprioceptive history buffer with zeros
            self.proprio_history_buffer = np.zeros(input_size)

            # Fill the proprioceptive history buffer with the current observation for the entire history length
            for i in range(self.obs_history_length):
                self.proprio_history_buffer[i * self.observations_size:(i + 1) * self.observations_size] = obs

            # Update the flag to indicate that the first observation has been processed
            self.is_first_rec_obs = False
        
        # Shift the existing proprioceptive history buffer to the left
        self.proprio_history_buffer[:-self.observations_size] = self.proprio_history_buffer[self.observations_size:]

        # Add the current observation to the end of the proprioceptive history buffer
        self.proprio_history_buffer[-self.observations_size:] = obs

        # Convert the proprioceptive history buffer to a numpy array
        self.proprio_history_vector = np.array(self.proprio_history_buffer)

        # Clip the observation values to within the specified limits for stability
        self.observations = np.clip(
            obs, 
            -self.rl_cfg['clip_scales']['clip_observations'],  # Lower limit for clipping
            self.rl_cfg['clip_scales']['clip_observations']  # Upper limit for clipping
        )

    def compute_actions(self):
        """
        Computes the actions based on the current observations using the policy session.
        """
        # Concatenate observations into a single tensor and convert to float32
        input_tensor = np.concatenate([self.encoder_out, self.observations, self.scaled_commands], axis=0)
        input_tensor = input_tensor.astype(np.float32)
        
        # Create a dictionary of inputs for the policy session
        inputs = {self.policy_input_names[0]: input_tensor}
        
        # Run the policy session and get the output
        output = self.policy_session.run(self.policy_output_names, inputs)
        
        # Flatten the output and store it as actions
        self.actions = np.array(output).flatten()

    def compute_encoder(self):
        """
        Computes the encoder output based on the proprioceptive history buffer.

        This method first concatenates the proprioceptive history buffer into a single input tensor.
        Then it converts the input tensor to the float32 data type. After that, it creates a dictionary
        of inputs for the encoder session and runs the encoder session to get the output. Finally,
        it flattens the output and stores it as the encoder output.
        """
        # Concatenate the proprioceptive history buffer into a single tensor and convert to float32
        input_tensor = np.concatenate([self.proprio_history_buffer], axis=0)
        input_tensor = input_tensor.astype(np.float32)

        # Create a dictionary of inputs for the encoder session
        inputs = {self.encoder_input_names[0]: input_tensor}

        # Run the encoder session and get the output
        output = self.encoder_session.run(self.encoder_output_names, inputs)

        # Flatten the output and store it as the encoder output
        self.encoder_out = np.array(output).flatten()
    
    def compute_depth_latent(self, depth_image, proprio):
        """
        depth_image: numpy array shape (1,1,58,87)
        proprio:     numpy array shape (1,32)
        """

        # Bảo đảm dtype đúng
        depth_image = depth_image.astype(np.float32)
        proprio     = proprio.astype(np.float32).reshape(1, -1)  # ensure (1, 32)
        h_in        = self.h_state.astype(np.float32)

        # Chuẩn bị dict input cho ONNX
        inputs = {
            self.depth_input_names[0]: depth_image,
            self.depth_input_names[1]: proprio,
            self.depth_input_names[2]: h_in,
        }

        # Forward ONNX
        latent, h_out = self.depth_sess.run(self.depth_output_names, inputs)

        # Cập nhật hidden state GRU
        self.h_state = h_out

        # Trả latent (1, latent_dim)
        return latent.flatten()
 
    def set_joint_command(self, joint_index, q, dq, tau, kp, kd):
        """
        Sends a command to configure the state of a specific joint.
        This method updates the joint's desired position, velocity, torque, and control gains.
        Replace this implementation with the actual communication logic for your hardware.

        Parameters:
        joint_index (int): The index of the joint to be controlled.
        q (float): The desired joint position, typically in radians or degrees.
        dq (float): The desired joint velocity, typically in radians/second or degrees/second.
        tau (float): The desired joint torque, typically in Newton-meters (Nm).
        kp (float): The proportional gain for position control.
        kd (float): The derivative gain for velocity control.
        """
        self.robot_cmd.q[joint_index] = q
        self.robot_cmd.dq[joint_index] = dq
        self.robot_cmd.tau[joint_index] = tau
        self.robot_cmd.Kp[joint_index] = kp
        self.robot_cmd.Kd[joint_index] = kd

    def update(self):
        """
        Updates the robot's state based on the current mode and publishes the robot command.
        """
        if self.mode == "STAND":
            self.handle_stand_mode()
        elif self.mode == "WALK":
            self.handle_walk_mode()
        
        # Increment the loop count
        self.loop_count += 1

        # Publish the robot command
        self.robot.publishRobotCmd(self.robot_cmd)
        
    # Callback function for receiving robot command data
    def robot_state_callback(self, robot_state: datatypes.RobotState):
        """
        Callback function to update the robot state from incoming data.
        
        Parameters:
        robot_state (datatypes.RobotState): The current state of the robot.
        """
        self.robot_state = robot_state

    # Callback function for receiving imu data
    def imu_data_callback(self, imu_data: datatypes.ImuData):
        """
        Callback function to update IMU data from incoming data.
        
        Parameters:
        imu_data (datatypes.ImuData): The IMU data containing stamp, acceleration, gyro, and quaternion.
        """
        self.imu_data.stamp = imu_data.stamp
        self.imu_data.acc = imu_data.acc
        self.imu_data.gyro = imu_data.gyro
        
        # Rotate quaternion values
        self.imu_data.quat[0] = imu_data.quat[1]
        self.imu_data.quat[1] = imu_data.quat[2]
        self.imu_data.quat[2] = imu_data.quat[3]
        self.imu_data.quat[3] = imu_data.quat[0]

    # Callback function for receiving sensor joy data
    def sensor_joy_callback(self, sensor_joy: datatypes.SensorJoy):
        # Check if the robot is in the calibration state and both L1 (button index 4) and Y (button index 3) buttons are pressed.
        if not self.start_controller and self.calibration_state == 0 and sensor_joy.buttons[4] == 1 and sensor_joy.buttons[3] == 1:
          print(f"L1 + Y: start_controller...")
          self.start_controller = True

        # Check if both L1 (button index 4) and X (button index 2) are pressed to stop the controller
        if self.start_controller and sensor_joy.buttons[4] == 1 and sensor_joy.buttons[2] == 1:
          print(f"L1 + X: stop_controller...")
          self.start_controller = False

        linear_x  = sensor_joy.axes[1]
        linear_y  = sensor_joy.axes[0]
        angular_z = sensor_joy.axes[2]

        linear_x  = 1.0 if linear_x > 1.0 else (-1.0 if linear_x < -1.0 else linear_x)
        linear_y  = 1.0 if linear_y > 1.0 else (-1.0 if linear_y < -1.0 else linear_y)
        angular_z = 1.0 if angular_z > 1.0 else (-1.0 if angular_z < -1.0 else angular_z)

        self.commands[0] = linear_x * 0.5
        self.commands[1] = linear_y * 0.5
        self.commands[2] = angular_z * 0.5

    # Callback function for receiving diagnostic data
    def robot_diagnostic_callback(self, diagnostic_value: datatypes.DiagnosticValue):
      # Check if the received diagnostic data is related to calibration.
      if diagnostic_value.name == "calibration":
        print(f"Calibration state: {diagnostic_value.code}")
        self.calibration_state = diagnostic_value.code