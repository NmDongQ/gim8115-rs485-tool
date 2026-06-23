# GIM 모터/드라이버 자료 요약

검토 기준일: 2026-06-22

## 자료 구성

- `GIM. Document of GDZ34, GDZ468, GDZ810 Driver. 20260416/`
  - GIM 계열 드라이버 문서 묶음.
  - 대상 드라이버/제품군 표기: GDZ34, GDZ468, GDZ810 Driver.
  - 핵심 자료: CAN, RS485, Modbus, SDC300 외장 드라이버, ZE300 GUI, 펌웨어, 배선, 데모 보드.
- `Robstride. motor_toolV14L/`
  - Robstride 전용 Windows 툴로 보임. GIM/ZE300 자료와는 별도 제품군으로 취급.

## 우선 읽어야 할 원문

- CAN 최신 문서: `2.自定义CAN通信协议/自定义CAN通信协议_3.09b0.pdf`
- CAN 영문 참고: `Custom_CAN_Protocol_V3_07b0_EN.pdf`
- RS485 최신 문서: `1.自定义RS485通信协议/自定义RS485通信协议_3.03b0.pdf`
- 외장 드라이버: `5.外置驱动使用说明/SDC300外置驱动产品说明_1.01.pdf`
- GUI 사용법: `6.上位机the host computer software/V3.03x/ZE300_GUI上位机说明文档.pdf`
- 배선: `9.其他资料/座子接线说明_260416.pdf`
- Modbus 레지스터: `3.Modbus通信协议/ModbusRTU寄存器表_V3.03b1_20260331.xlsx`

## 하드웨어/드라이버 핵심

- SDC300은 BLDC/gimbal motor용 FOC 드라이버.
- 전원 입력 범위: 12-40 V DC.
- RS485와 CAN 지원. USB는 GUI 설정용으로 사용 가능.
- USB 포트는 전원 공급용이 아님. 드라이버 전원 입력을 먼저 넣어야 USB가 정상 인식됨.
- USB와 RS485는 같은 직렬 포트를 공유하므로 동시에 사용하면 안 됨.
- 모터 3상선은 SDC300 기준 순서 요구가 없다고 문서에 적혀 있음.
- SPI/PWM/RS485 엔코더 인터페이스 지원. 엔코더 PCB는 축과 동심이고 단단히 고정돼야 함.
- 동작 환경: -40~85도 표기.
- 보호: 과전압/과전류/과온 등.

## 초기 설정/캘리브레이션 절차

1. 모터 3상선, 엔코더선, 전원을 올바르게 연결.
2. 전원 인가 후 상태 LED 점멸 확인.
3. USB 또는 USB-RS485로 ZE300_GUI 연결.
   - 기본 장치 주소: 1
   - RS485 기본 baudrate: 115200
   - 주소를 모르면 public address 255로 연결 가능. 단, RS485 버스에 여러 대가 있으면 public address 사용 주의.
4. GUI에서 엔코더 타입과 모터 하드웨어 파라미터를 설정/저장.
5. 시스템 재시작.
6. 손으로 모터를 돌려 GUI 각도 계기가 같이 변하는지 확인.
7. 엔코더 각도 캘리브레이션 실행.
   - 반드시 무부하.
   - 외력으로 방해하면 안 됨.
   - 약 30-90초 동안 정/역회전.
8. `최단거리 원점복귀`로 원점과 0도 표시 확인.

주의:

- 엔코더 커버 분해, 엔코더 교체, 모터 교체 후에는 엔코더 캘리브레이션을 다시 해야 함.
- 펌웨어를 V301x <-> V302x로 변경하면 시스템 파라미터 기본값 복구 후 무부하 엔코더 캘리브레이션 필요.
- 302x 펌웨어는 V3.02 GUI, 303x 펌웨어는 V3.03 GUI 사용.

## 배선 주의

- 통신선 심선 노출 금지. 단락 방지.
- CAN 또는 RS485 중 하나만 쓸 때 나머지 통신선은 절연 처리.
- 전원 접촉 불량 금지. 전원 GND/VCC 접촉 불량은 전류 귀환 경로 이상으로 통신 인터페이스 손상 위험.
- 구매한 모터의 최대 지원 전압을 확인하고 초과하지 말 것.
- GDZ468/GDZ810 계열 배선 예:
  - CAN-L, CAN-H
  - RS485-A, RS485-B
  - XT30 전원: GND, VCC
- GDZ34 계열 배선 예:
  - SH1.0-4P: CAN-L, CAN-H, RS485-A, RS485-B
  - 전원은 빨간선 VCC, 검은선 GND로 출고 납땜되는 타입이라고 문서에 표기.

## CAN 프로토콜 핵심

- 최신 문서: Custom CAN V3.09b0.
- CAN 기본 baudrate: 1 Mbps.
- GUI에서 1 Mbps, 500 kbps, 250 kbps, 125 kbps, 100 kbps 설정 가능.
- 표준 11-bit CAN ID 사용.
- 멀티바이트 데이터는 little endian.
- 기본 장치 주소 `Dev_addr`: `0x01`, 설정 범위 1-254.
- 특수 주소:
  - `0x00`: broadcast. 모든 slave가 실행하지만 응답 없음.
  - `0xFF`: public address. 모든 slave가 응답. 여러 장치가 같은 버스에 있으면 충돌 위험.
- slave는 `Dev_addr`와 `(0x100 | Dev_addr)` 둘 다 수신 가능.
- slave 응답 ID는 항상 `Dev_addr`.
- 전원 인가 후 기본 상태는 motor output disabled/free state.

### CAN 상태 읽기

- `0xA0`: Boot/app/hardware/CAN protocol version 읽기.
- `0xA1`: Q-axis current 읽기. 단위 0.001 A.
- `0xA2`: speed 읽기. 단위 0.01 rpm.
- `0xA3`: single-turn, multi-turn absolute angle 읽기.
  - 1 rev = 16384 counts.
  - angle deg = count * 360 / 16384.
- `0xA4`: temperature, Q current, speed, single-turn angle 압축 읽기.
- `0xAE`: bus voltage, bus current, temperature, run mode, fault code 읽기.
  - bus voltage 단위 0.01 V.
  - bus current 단위 0.01 A.
  - run mode: 0 disabled, 1 voltage, 2 Q current, 3 speed, 4 position.
  - fault bit: bit0 voltage, bit1 current, bit2 temperature, bit3 encoder, bit5 communication, bit6 hardware, bit7 software.
  - fault 발생 시 통신 fault 외 fault는 200 ms 주기로 `0xAE` 상태를 자동 보고.
- `0xAF`: fault clear.

### CAN 파라미터

- `0xB0`: torque constant 읽기.
  - V3.09에서는 pole pairs/gear ratio 자리에 0x00이 들어가고 torque constant만 유효.
  - torque = Q_current[A] * torque_constant.
- `0xB1`: 현재 위치를 원점으로 저장. 전원 꺼져도 유지.
- `0xB2`: position mode max speed 읽기/쓰기. 단위 0.01 rpm. 전원 꺼지면 미저장.
- `0xB3`: position/speed mode max Q-axis current 읽기/쓰기. 단위 0.001 A. 전원 꺼지면 미저장.
- `0xB4`: current control mode Q-current ramp rate. 단위 0.001 A/s. 전원 꺼지면 미저장.
- `0xB5`: speed mode acceleration. 단위 0.01 rpm/s. 전원 꺼지면 미저장.
- `0xB6`, `0xB7`: position loop Kp/Ki.
- `0xB8`, `0xB9`: speed loop Kp/Ki.
- `0xBA`: device address 읽기/쓰기. 재전원 또는 재시작 후 적용. 전원 꺼져도 저장.
- `0xCD`: CAN communication timeout 설정.
  - enable, timeout ms, action type.
  - timeout 초과 시 communication fault 및 motor disable.
  - bit0: communication fault를 software clear 불가.
  - bit1: brake switch open.
- `0xCE`: brake switch output control/read.
- `0xCF`: motor output disable/free state.

### CAN 제어 명령

- `0xC0`: Q-axis current control.
  - data: signed 32-bit, 0.001 A.
  - torque = current[A] * torque_constant.
- `0xC1`: speed control.
  - data: signed 32-bit, 0.01 rpm.
- `0xC2`: absolute position control.
  - data: signed 32-bit count.
  - 1 rev = 16384 counts.
- `0xC3`: relative position control.
  - data: signed 32-bit count.
- `0xC4`: shortest path return to stored home. rotation <= 180 deg.
- `0xD0`: trapezoid position acceleration. 0.01 rpm/s, default 10 rpm/s.
- `0xD1`: trapezoid position deceleration. 0.01 rpm/s, default 10 rpm/s.
- `0xD5`: position-filter bandwidth. Hz, default 50 Hz.
- `0xD6`: position-filter inertia. Nm/(turn/s^2), default 0.001. 0 disables current feedforward.
- `0xD7`: position-filter current feedforward limit. 0.001 A, default 1 A.
- `0xDA`: trapezoid position control.
  - byte 1 position type: 0 absolute, 1 relative.
  - bytes 2-5 target position count.
- `0xDC`: position-filter control.
  - byte 1 position type: 0 absolute, 1 relative.
  - bytes 2-5 target position count.

### CAN MIT-style motion control

- `0xF0`: read/configure `Pos_Max`, `Vel_Max`, `T_Max`.
  - saved in driver.
  - Pos_Max unit 0.1 rad, default 95.5 rad.
  - Vel_Max unit 0.01 rad/s, default 45.00 rad/s.
  - T_Max unit 0.01 Nm, default 18.00 Nm.
- `0xF1`: read real-time MIT position, velocity, torque, status.
- Motion control frame has no command byte.
  - Set standard ID bit 10: `0x400 | Dev_addr`.
  - Example for address 1: `0x401`.
  - Receiving this frame switches immediately into motion control mode.
  - Exit MIT mode with `0xCF`.
- MIT units:
  - position: rad.
  - velocity: rad/s.
  - torque: Nm.
- MIT frame packing:
  - position: 16-bit maps [0, 65535] to [-Pos_Max, +Pos_Max].
  - velocity: 12-bit maps [0, 4095] to [-Vel_Max, +Vel_Max].
  - Kp: 12-bit maps [0, 4095] to [0, 500].
  - Kd: 12-bit maps [0, 4095] to [0, 5].
  - torque: 12-bit maps [0, 4095] to [-T_Max, +T_Max].

## RS485 프로토콜 핵심

- 기본 baudrate: 115200, 8N1.
- 지원 baudrate: 921600, 460800, 115200, 57600, 38400, 19200, 9600.
- little endian.
- 기본 주소: 1.
- 주소 0: broadcast, 실행만 하고 응답 없음.
- 주소 255: public address, 모든 slave 응답. 여러 장치가 있으면 사용 금지.
- 패킷:
  - master header: `0xAE`
  - slave reply header: `0xAC`
  - packet sequence
  - device address
  - command
  - data length
  - data
  - CRC16-MODBUS
- 주요 명령:
  - `0x0A`: version/UID read.
  - `0x0B`: real-time state read.
  - `0x0F`: fault clear.
  - `0x10`/`0x11`: user parameter read/write-save.
  - `0x12`/`0x13`: motor hardware parameter read/write-save.
  - `0x14`/`0x15`/`0x16`: motion parameter read/write/write-save.
  - `0x17`: position-filter parameter write/read.
  - `0x1D`: set current position as home.
  - `0x1E`: encoder calibration. motor must be unloaded.
  - `0x1F`: restore default parameters, excluding address, encoder calibration parameters, motor hardware parameters.
  - `0x20`: Q-axis current control.
  - `0x21`: speed control.
  - `0x22`: absolute position control.
  - `0x23`: relative position control.
  - `0x24`: shortest path return home.
  - `0x25`: position-speed control.
  - `0x26`: trapezoid position control.
  - `0x27`: position-filter control.
  - `0x2D`: RS485 communication timeout.
  - `0x2E`: brake output.
  - `0x2F`: motor disable/free state.
  - `0x30`/`0x31`/`0x32`: MIT motion control parameters/read/control.

## Modbus 핵심

- Modbus는 별도 레지스터 기반 제어 경로.
- 레지스터 표 파일: `ModbusRTU寄存器表_V3.03b1_20260331.xlsx`.
- 주요 주소:
  - 0-17: version, UID, calibration offset.
  - 64-80: motor name/hardware parameters, including `MotorKt`.
  - 128-139: realtime state.
  - 192-206: user parameters, address, baudrate, limits, brake.
  - 256-266: position/speed loop parameters and current/speed limits.
  - 320-325: restart, fault clear, set zero, encoder calibration, reset params, home.
  - 384-396: control word, run mode, target current/speed/position.
  - 500-507: trapezoid/filter parameters.
  - 600-606: trapezoid/filter position command registers.
- Modbus examples include recommended sequence: disable motor -> set mode/target/ramp -> enable motor.

## 로봇 투입 전 권장 절차

1. 원문 기준으로 정확한 제품 타입과 배선 타입 확인.
2. 전원 공급 전 VCC/GND, CANH/CANL 또는 RS485-A/B 재확인.
3. GUI 연결 후 firmware/app/protocol version 확인.
4. 주소를 모터마다 고유하게 설정.
5. 엔코더 값이 손회전과 같이 변하는지 확인.
6. 무부하 엔코더 캘리브레이션.
7. `0xB0` 또는 Modbus hardware parameter로 torque constant 확인.
8. 낮은 current limit부터 설정.
9. motor output disabled 상태에서 상태 읽기부터 검증.
10. Q-axis current control은 낮은 전류부터 짧게 테스트.
11. speed/position 제어는 낮은 speed, 낮은 current limit에서 시작.
12. 통신 timeout을 enable해서 통신 끊김 시 motor disable 되게 설정.
13. 로봇 장착 전에는 각 관절 방향, 원점, 소프트 리밋, 비상 disable 명령을 검증.

## 로봇 코드 작성 시 기본 선택

- 실시간 로봇 제어는 CAN custom protocol 우선.
- 초기 설정/캘리브레이션/파라미터 확인은 ZE300_GUI 또는 RS485.
- 단순 벤치 테스트는 RS485/GUI가 편함.
- 제어 코드에서는 다음을 최소 구현:
  - version read
  - state read `0xAE`/`0xA4`
  - fault clear `0xAF`
  - disable `0xCF`
  - current limit `0xB3`
  - current ramp `0xB4`
  - speed/position limit `0xB2`, `0xB5`
  - set home `0xB1`
  - current/speed/position command `0xC0`/`0xC1`/`0xC2`/`0xC3`
  - communication timeout `0xCD`

## 확인이 필요한 것

- GIM-8115-6이 이 자료의 GDZ34/GDZ468/GDZ810 중 어느 배선/드라이버 타입에 해당하는지 확인 필요.
- 모터 자체 최대 전압, 연속/피크 전류, torque constant, gear ratio는 제품 자료 또는 `0xB0`/Modbus에서 확인해야 함.
- 펌웨어가 V302x인지 V303x인지 확인해서 GUI 버전을 맞춰야 함.
