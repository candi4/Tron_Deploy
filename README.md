# Use TRON with a Windows 11 Laptop

## SDK ([`pointfoot-sdk-lowlevel`](pointfoot-sdk-lowlevel/))
https://www.limxdynamics.com/en/documents/799664773997400064?channel=option_google_advertising__c#1.-Pointfoot-SDK-Overview

### Installation
Create a conda environment and install the SDK:
```bat
conda create -n tron python=3.8 -y
conda activate tron
python -m pip install .\pointfoot-sdk-lowlevel\python3\win\limxsdk-3.4.2-py3-none-any.whl
```
For other OS, refer to [here](pointfoot-sdk-lowlevel\README.md#32-install-python-sdk).

### Connect to TRON
Connect Windows to the TRON Wi-Fi:
```text
SSID: PF_TRON1A_... # PF_TRON1A_224
Password: 12345678
```

Check the connection:
```bat
# Open the robot page: http://10.192.1.2:8080
ping 10.192.1.2
```

### Run Tests
```bat
python .\tron_imu_test.py
python .\tron_led_test.py
```

## Deploy policy [`rl-deploy-with-python`](rl-deploy-with-python/)
Everything related to deploying is in `rl-deploy-with-python` in Tron computer.
### 1. Turn on
Turn on Tron and remote controller.
Enter Developer mode (green LED). In remote controller, `R1` + `←`.

### 2. Connect to Tron
Connect to Tron using Ethernet.
```
# In local
ssh guest@10.192.1.2
# password: 123456
```

### 3. Replace policy
Replace `policy.onnx` and `encoder.onnx` into [rl-deploy-with-python/controllers/model/PF_TRON1A/policy/isaacgym/](rl-deploy-with-python/controllers/model/PF_TRON1A/policy/isaacgym/).

#### 1. Ensure [rl-deploy-with-python/controllers/PointfootController.py](rl-deploy-with-python/controllers/PointfootController.py) to use the replaced `policy.onnx` and `encoder.onnx`:
```
# Load configuration and model file paths based on robot type
self.config_file = f'{model_dir}/{self.robot_type}/params.yaml'
self.model_policy = f'{model_dir}/{self.robot_type}/policy/{self.rl_type}/policy_check0.onnx'
self.model_encoder = f'{model_dir}/{self.robot_type}/policy/{self.rl_type}/encoder_check0.onnx'
```
#### 2. Ensure controller weights in [PointfootController.py](rl-deploy-with-python/controllers/PointfootController.py).
```
self.commands[0] = linear_x * 0.7
self.commands[1] = linear_y * 0.7
self.commands[2] = angular_z * 0.5
```
#### 3. Ensure command constraints in [PointfootController.py](rl-deploy-with-python/controllers/PointfootController.py).
```
linear_x  = 1.0 if linear_x > 1.0 else (-1 if linear_x < -1 else linear_x)
linear_y  = 1.0 if linear_y > 1.0 else (-1 if linear_y < -1 else linear_y)
angular_z = 1.0 if angular_z > 1.0 else (-1 if angular_z < -1 else angular_z)
```

### 4. Deploy
```
export RL_TYPE=isaacgym
export ROBOT_TYPE=PF_TRON1A
python3 rl-deploy-with-python/main.py 10.192.1.2
```

### 5. Remote controller
```
 △ 
□ ○
 X
```
* `L1` + `△`: run model
* `L1` + `□`: stop robot
* 