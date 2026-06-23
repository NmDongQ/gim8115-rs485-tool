# Robstride02 테스트 메모

검토 기준일: 2026-06-23

## 로컬 자료 확인 결과

- 로컬 폴더 `Robstride. motor_toolV14L/`에는 Windows GUI 실행 파일과 Qt DLL만 있음.
- 별도 PDF/README/프로토콜 문서는 없음.
- `motor_tool.exe` 내부 문자열 기준 GUI 이름은 `motorstudio 0.0.14L`.
- GUI에서 지원하는 모터 타입 목록에 `RS00`, `RS01`, `RS02`, `RS03` ... `RS09`, `EL05`, `RB81` 등이 있음.
- GUI에서 확인되는 CAN 관련 기능:
  - USB-CAN module
  - CAN baud rate: `1Mbps`, `500kbps`, `250kbps`, `125kbps`
  - frame type: standard frame / extended frame
  - device detection
  - CAN ID set
  - fault clear
  - set zero position / mechanical zero
  - encoder calibration
  - start/stop auto report
  - parameter table read/write/export/factory reset
- GUI에서 확인되는 제어 모드:
  - MIT
  - CSP position mode
  - Velocity
  - Current
  - PP interpolated position mode
  - homing mode
  - collision test
  - open-loop mode
  - Stop

## GIM과 다른 점

- GIM 테스트에 쓴 `gim_rs485_tool.py`는 RS485 프로토콜용이므로 Robstride02 CAN L/H 단자에 직접 사용할 수 없음.
- Robstride02 테스트에는 USB-RS485가 아니라 USB-CAN 어댑터가 필요함.
- CAN L/H는 차동 통신선이며, 전원 V+/GND와 별도로 연결해야 함.
- 프로토콜 원문이 로컬에 없으므로, 확인 전까지 임의 CAN 제어 프레임을 보내면 안 됨.

## 우선 테스트 전략

1. 모터 전원 사양을 확인하고 전류 제한 가능한 전원 공급기를 사용한다.
2. 배선:
   - 전원 V+ / GND
   - USB-CAN CANH -> 모터 CAN H
   - USB-CAN CANL -> 모터 CAN L
   - USB-CAN이 비절연이면 GND 기준을 공유하는 편이 안전함.
3. CAN 종단:
   - 짧은 단일 모터 테스트도 통신이 불안정하면 CANH-CANL 사이 120 ohm 종단 확인.
   - 어댑터/모터에 내장 종단이 있는지 먼저 확인.
4. 처음은 구동 명령 금지:
   - bus/device detection
   - device ID 확인
   - fault/status 읽기
   - 현재 position/speed/temperature 읽기
5. 손으로 축을 천천히 돌려 position 값이 변하는지 확인한다.
6. fault가 없고 position feedback이 정상일 때만 zero 설정.
7. 그 다음 아주 작은 명령부터:
   - MIT 모드라면 torque 0, 낮은 Kp/Kd, 현재 위치 유지부터
   - 위치 모드라면 0.03-0.05 rad 정도의 작은 상대 이동부터
   - 테스트 후 즉시 Stop/RESET/BRAKE 상태 전환 명령 확인

## 아직 확정하지 않은 것

- Robstride02의 정확한 CAN 프레임 포맷.
- 기본 CAN ID.
- 기본 frame type이 standard인지 extended인지.
- 기본 baudrate가 실제로 1Mbps인지.
- enable/disable/stop 명령의 정확한 arbitration ID와 payload.

이 네 가지는 실제 GUI 또는 원문 프로토콜 문서로 확인하기 전까지 추정해서 제어 코드를 만들지 않는다.
