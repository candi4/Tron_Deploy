# Use TRON with a Windows 11 Laptop

## Installation
Create a conda environment and install the SDK:
```bat
conda create -n tron python=3.8 -y
conda activate tron
python -m pip install .\pointfoot-sdk-lowlevel\python3\win\limxsdk-3.4.2-py3-none-any.whl
```

## Connect to TRON
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

## Run Tests
```bat
python .\tron_imu_test.py
python .\tron_led_test.py
```