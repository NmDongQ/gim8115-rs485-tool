# GIM8115-6 RS485 Motor Test Tool (macOS)

Python CLI for controlling and validating GIM8115-6 motors via RS485 on macOS.

## Environment

- **OS**: macOS (Apple Silicon / Intel)
- **Motor**: GIM8115-6
- **Driver**: GDZ series / SDC300-based
- **Interface**: RS485 via USB-RS485 adapter, 115200 baud, 8N1
- **Python**: 3.8+, `pyserial` optional (falls back to built-in `termios`)

## Install

```bash
pip install pyserial   # optional
```

## Usage

```bash
# List available serial ports
python3 gim_rs485_tool.py list

# All other commands require --port
MOTOR="--port /dev/cu.usbserial-XXXX"

python3 gim_rs485_tool.py $MOTOR version        # firmware version + UID
python3 gim_rs485_tool.py $MOTOR status         # real-time state
python3 gim_rs485_tool.py $MOTOR set-zero       # save current position as 0°
python3 gim_rs485_tool.py $MOTOR disable        # disable motor output
python3 gim_rs485_tool.py $MOTOR clear-fault    # clear faults
python3 gim_rs485_tool.py $MOTOR motion-params  # read motion parameters

# Position control
python3 gim_rs485_tool.py $MOTOR rel-pos --deg 5 --yes   # relative +5°
python3 gim_rs485_tool.py $MOTOR abs-pos --deg 0 --yes   # absolute 0°

# Automated back-and-forth sweep test
python3 gim_rs485_tool.py $MOTOR sweep --deg 30 --reps 3 --yes

# Encoder calibration (unloaded only)
python3 gim_rs485_tool.py $MOTOR calibrate --yes
```

## Pre-assembly Test Procedure

Run this sequence for each motor before attaching any mechanism.

```bash
MOTOR="--port /dev/cu.usbserial-XXXX"

# 1. Verify communication and state
python3 gim_rs485_tool.py $MOTOR status

# 2. Set home position
python3 gim_rs485_tool.py $MOTOR set-zero

# 3. Minimal motion check ±5°
python3 gim_rs485_tool.py $MOTOR rel-pos --deg 5 --yes
python3 gim_rs485_tool.py $MOTOR rel-pos --deg -5 --yes

# 4. Expand sweep range
python3 gim_rs485_tool.py $MOTOR sweep --deg 15 --reps 3 --yes
python3 gim_rs485_tool.py $MOTOR sweep --deg 30 --reps 3 --yes

# 5. Final state check
python3 gim_rs485_tool.py $MOTOR status
```

## Test Results (2026-06-22 ~ 23)

4× GIM8115-6 motors validated.

| Test | Result |
|---|---|
| RS485 communication | All motors OK |
| Encoder calibration | Completed (~150 s) |
| rel-pos ±5° | Error < 0.3° |
| sweep ±15° × 3 reps | All settled OK |
| sweep ±30° × 3 reps | All settled OK |
| Final fault code | 0x00 OK on all motors |
| Operating temperature | 26–40°C (incl. post-calibration) |

## Protocol Reference

- Default baudrate: 115200, 8N1
- Packet: `0xAE` header + seq + addr + cmd + len + data + CRC16-MODBUS
- Reply: `0xAC` header
- Default device address: 1 (range 1–254)
- Address 0: broadcast (no reply), address 255: public (single device only)
- Encoder resolution: 16384 counts/rev → `deg = count × 360 / 16384`

See `GIM_motor_protocol_summary.md` for full protocol details.

## Files

| File | Description |
|---|---|
| `gim_rs485_tool.py` | RS485 CLI tool |
| `GIM_motor_protocol_summary.md` | GIM/GDZ driver protocol summary |
| `Robstride02_test_notes.md` | Robstride02 CAN test preparation notes |

---

# GIM8115-6 RS485 모터 테스트 툴 (macOS)

GIM8115-6 모터를 macOS에서 RS485로 제어·검증하는 Python CLI 툴입니다.

## 환경

- **OS**: macOS (Apple Silicon / Intel 공통)
- **모터**: GIM8115-6
- **드라이버**: GDZ 시리즈 / SDC300 기반
- **통신**: RS485 (USB-RS485 어댑터), 115200 baud, 8N1
- **Python**: 3.8+, `pyserial` 선택 설치 (없어도 동작)

## 설치

```bash
pip install pyserial   # 선택 사항, 없으면 내장 termios 사용
```

## 사용법

```bash
# 연결된 시리얼 포트 목록
python3 gim_rs485_tool.py list

# 이후 명령은 --port 필수
MOTOR="--port /dev/cu.usbserial-XXXX"

python3 gim_rs485_tool.py $MOTOR version        # 펌웨어/UID 읽기
python3 gim_rs485_tool.py $MOTOR status         # 실시간 상태 읽기
python3 gim_rs485_tool.py $MOTOR set-zero       # 현재 위치를 0°로 저장
python3 gim_rs485_tool.py $MOTOR disable        # 모터 출력 해제
python3 gim_rs485_tool.py $MOTOR clear-fault    # fault 클리어
python3 gim_rs485_tool.py $MOTOR motion-params  # 모션 파라미터 읽기

# 위치 제어
python3 gim_rs485_tool.py $MOTOR rel-pos --deg 5 --yes   # 상대 +5°
python3 gim_rs485_tool.py $MOTOR abs-pos --deg 0 --yes   # 절대 0°

# 왕복 sweep 테스트
python3 gim_rs485_tool.py $MOTOR sweep --deg 30 --reps 3 --yes

# 엔코더 캘리브레이션 (반드시 무부하)
python3 gim_rs485_tool.py $MOTOR calibrate --yes
```

## 기본 테스트 절차

기구물 장착 전 각 모터에 대해 아래 순서로 진행합니다.

```bash
MOTOR="--port /dev/cu.usbserial-XXXX"

# 1. 통신·상태 확인
python3 gim_rs485_tool.py $MOTOR status

# 2. 원점 설정
python3 gim_rs485_tool.py $MOTOR set-zero

# 3. ±5° 최소 동작 확인
python3 gim_rs485_tool.py $MOTOR rel-pos --deg 5 --yes
python3 gim_rs485_tool.py $MOTOR rel-pos --deg -5 --yes

# 4. sweep 범위 확대
python3 gim_rs485_tool.py $MOTOR sweep --deg 15 --reps 3 --yes
python3 gim_rs485_tool.py $MOTOR sweep --deg 30 --reps 3 --yes

# 5. 최종 상태 확인
python3 gim_rs485_tool.py $MOTOR status
```

## 테스트 결과 (2026-06-22 ~ 23)

총 4개 GIM8115-6 모터 검증 완료.

| 항목 | 결과 |
|---|---|
| RS485 통신 | 전 모터 정상 |
| 엔코더 캘리브레이션 | 정상 완료 (~150초) |
| rel-pos ±5° | 오차 < 0.3° |
| sweep ±15° × 3 | 전 모터 settle ok |
| sweep ±30° × 3 | 전 모터 settle ok |
| 최종 fault | 전 모터 0x00 OK |
| 동작 온도 | 26–40°C (캘리브레이션 직후 포함) |

## 프로토콜 참고

- RS485 기본 baudrate: 115200, 8N1
- 패킷: `0xAE` 헤더 + seq + addr + cmd + len + data + CRC16-MODBUS
- 응답: `0xAC` 헤더
- 기본 장치 주소: 1 (1–254 설정 가능)
- 주소 0: broadcast (응답 없음), 주소 255: public (버스에 1대일 때만 사용)
- 엔코더 분해능: 16384 counts/rev → `deg = count × 360 / 16384`

자세한 프로토콜은 `GIM_motor_protocol_summary.md` 참고.

## 관련 파일

| 파일 | 설명 |
|---|---|
| `gim_rs485_tool.py` | RS485 CLI 툴 본체 |
| `GIM_motor_protocol_summary.md` | GIM/GDZ 드라이버 프로토콜 요약 |
| `Robstride02_test_notes.md` | Robstride02 CAN 테스트 준비 메모 |
