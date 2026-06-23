#!/usr/bin/env python3
"""
Minimal macOS-friendly RS485 CLI for GIM/ZE300/GDZ drivers.

Requires pyserial:
  python3 -m pip install pyserial

Examples:
  python3 gim_rs485_tool.py list
  python3 gim_rs485_tool.py --port /dev/cu.usbserial-XXXX version
  python3 gim_rs485_tool.py --port /dev/cu.usbserial-XXXX status
  python3 gim_rs485_tool.py --port /dev/cu.usbserial-XXXX disable
"""

from __future__ import annotations

import argparse
import glob
import os
import select
import struct
import sys
import termios
import time


def require_serial():
    try:
        import serial
        import serial.tools.list_ports
    except ImportError:
        return None
    return serial


class PosixSerial:
    """Small pyserial fallback for macOS/Linux callout serial devices."""

    BAUDS = {
        9600: termios.B9600,
        19200: termios.B19200,
        38400: termios.B38400,
        57600: termios.B57600,
        115200: termios.B115200,
        230400: getattr(termios, "B230400", termios.B115200),
        460800: getattr(termios, "B460800", termios.B115200),
        921600: getattr(termios, "B921600", termios.B115200),
    }

    def __init__(self, port: str, baudrate: int, timeout: float = 0.05, **_kwargs):
        if baudrate not in self.BAUDS:
            raise ValueError(f"unsupported baudrate without pyserial: {baudrate}")
        self.port = port
        self.timeout = timeout
        self.fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        self._setup(baudrate)

    def _setup(self, baudrate: int) -> None:
        attrs = termios.tcgetattr(self.fd)
        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[3] = 0
        attrs[4] = self.BAUDS[baudrate]
        attrs[5] = self.BAUDS[baudrate]
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = max(1, int(self.timeout * 10))
        termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        termios.tcflush(self.fd, termios.TCIOFLUSH)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        os.close(self.fd)

    def reset_input_buffer(self) -> None:
        termios.tcflush(self.fd, termios.TCIFLUSH)

    def write(self, data: bytes) -> int:
        return os.write(self.fd, data)

    def flush(self) -> None:
        termios.tcdrain(self.fd)

    def read(self, size: int) -> bytes:
        ready, _, _ = select.select([self.fd], [], [], self.timeout)
        if not ready:
            return b""
        try:
            return os.read(self.fd, size)
        except BlockingIOError:
            return b""


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def make_packet(seq: int, addr: int, cmd: int, payload: bytes = b"") -> bytes:
    body = bytes([0xAE, seq & 0xFF, addr & 0xFF, cmd & 0xFF, len(payload)]) + payload
    return body + struct.pack("<H", crc16_modbus(body))


def read_reply(ser, timeout: float = 1.0) -> tuple[int, int, int, bytes]:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        b = ser.read(1)
        if not b:
            continue
        if b[0] == 0xAC:
            break
    else:
        raise TimeoutError("no reply header 0xAC")

    header_rest = ser.read(4)
    if len(header_rest) != 4:
        raise TimeoutError("short reply header")

    seq, addr, cmd, length = header_rest
    payload_crc = ser.read(length + 2)
    if len(payload_crc) != length + 2:
        raise TimeoutError("short reply payload")

    payload = payload_crc[:length]
    rx_crc = struct.unpack("<H", payload_crc[length:])[0]
    frame = bytes([0xAC]) + header_rest + payload
    calc_crc = crc16_modbus(frame)
    if rx_crc != calc_crc:
        raise ValueError(f"bad CRC: got 0x{rx_crc:04X}, expected 0x{calc_crc:04X}")

    return seq, addr, cmd, payload


def _open_serial(args):
    serial = require_serial()
    serial_class = serial.Serial if serial else PosixSerial
    return serial_class(
        port=args.port,
        baudrate=args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=0.05,
        write_timeout=1.0,
    )


def _transceive(ser, args, cmd: int, payload: bytes = b"", timeout: float | None = None) -> bytes:
    ser.reset_input_buffer()
    packet = make_packet(args.seq, args.addr, cmd, payload)
    if args.verbose:
        print("tx:", packet.hex(" ").upper())
    ser.write(packet)
    ser.flush()
    if args.addr == 0:
        return b""
    seq, addr, reply_cmd, reply_payload = read_reply(ser, args.timeout if timeout is None else timeout)
    if args.verbose:
        print("rx:", bytes([0xAC, seq, addr, reply_cmd, len(reply_payload)]).hex(" ").upper(), reply_payload.hex(" ").upper())
    if reply_cmd != cmd:
        raise ValueError(f"unexpected reply cmd 0x{reply_cmd:02X}, expected 0x{cmd:02X}")
    return reply_payload


def transceive(args, cmd: int, payload: bytes = b"", expect_reply: bool = True, timeout: float | None = None) -> bytes:
    with _open_serial(args) as ser:
        if not expect_reply or args.addr == 0:
            ser.reset_input_buffer()
            ser.write(make_packet(args.seq, args.addr, cmd, payload))
            ser.flush()
            return b""
        return _transceive(ser, args, cmd, payload, timeout)


def s16(v: bytes) -> int:
    return struct.unpack("<h", v)[0]


def s32(v: bytes) -> int:
    return struct.unpack("<i", v)[0]


def u16(v: bytes) -> int:
    return struct.unpack("<H", v)[0]


def u32(v: bytes) -> int:
    return struct.unpack("<I", v)[0]


def f32(v: bytes) -> float:
    return struct.unpack("<f", v)[0]


def count_from_degrees(deg: float) -> int:
    return round(deg * 16384.0 / 360.0)


def cmd_list(_args) -> None:
    serial = require_serial()
    if serial:
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("No serial ports found.")
            return
        for p in ports:
            print(f"{p.device}\t{p.description}\t{p.hwid}")
        return

    ports = sorted(glob.glob("/dev/cu.*"))
    if not ports:
        print("No serial ports found.")
        return
    for p in ports:
        print(p)


def cmd_version(args) -> None:
    p = transceive(args, 0x0A)
    if len(p) < 22:
        print("raw:", p.hex(" ").upper())
        return
    print(f"boot={u16(p[0:2])}")
    print(f"app={u16(p[2:4])}")
    print(f"hardware={u16(p[4:6])}")
    print(f"rs485_custom={p[6]}")
    print(f"rs485_modbus={p[7]}")
    print(f"can_custom={p[8]}")
    print(f"canopen={p[9]}")
    print("uid=" + p[10:22].hex(" ").upper())


def cmd_status(args) -> None:
    p = transceive(args, 0x0B)
    if len(p) < 22:
        print("raw:", p.hex(" ").upper())
        return
    single = u16(p[0:2])
    multi = s32(p[2:6])
    velocity = s32(p[6:10]) * 0.01
    current_q = s32(p[10:14]) * 0.001
    bus_v = u16(p[14:16]) * 0.01
    bus_i = u16(p[16:18]) * 0.01
    temp = p[18]
    run_state = p[19]
    motor_state = p[20]
    fault = p[21]

    print(f"single_turn={single} count = {single * 360.0 / 16384.0:.2f} deg")
    print(f"multi_turn={multi} count = {multi * 360.0 / 16384.0:.2f} deg")
    print(f"velocity={velocity:.2f} rpm")
    print(f"q_current={current_q:.3f} A")
    print(f"bus_voltage={bus_v:.2f} V")
    print(f"bus_current={bus_i:.2f} A")
    print(f"temperature={temp} C")
    print(f"run_state={run_state} (0 disabled, 1 voltage, 2 q-current, 3 speed, 4 position)")
    print(f"motor_state={motor_state} (0 disabled, nonzero enabled)")
    print(f"fault=0x{fault:02X} {fault_text(fault)}")


def fault_text(fault: int) -> str:
    names = [
        (0, "voltage"),
        (1, "current"),
        (2, "temperature"),
        (3, "encoder"),
        (5, "communication"),
        (6, "hardware"),
        (7, "software"),
    ]
    active = [name for bit, name in names if fault & (1 << bit)]
    return "OK" if not active else ",".join(active)


def cmd_simple(args, cmd: int, label: str) -> None:
    p = transceive(args, cmd)
    print(f"{label}: ok, payload={p.hex(' ').upper()}")


def cmd_disable(args) -> None:
    cmd_simple(args, 0x2F, "disable")


def cmd_clear_fault(args) -> None:
    cmd_simple(args, 0x0F, "clear_fault")


def cmd_set_zero(args) -> None:
    cmd_simple(args, 0x1D, "set_zero")


def cmd_home(args) -> None:
    cmd_simple(args, 0x24, "home")


def require_yes(args, text: str) -> None:
    if args.yes:
        return
    print(text)
    print("Re-run with --yes if the motor is unloaded and mechanically safe.", file=sys.stderr)
    raise SystemExit(2)


def cmd_calibrate(args) -> None:
    require_yes(args, "Encoder calibration rotates the motor for about 30-90 seconds.")
    p = transceive(args, 0x1E, timeout=max(args.timeout, 3.0))
    print("calibrate started/replied:", p.hex(" ").upper())


def cmd_q_current(args) -> None:
    require_yes(args, "Q-current command can create torque immediately.")
    target = round(args.amps * 1000.0)
    slope = round(args.slope * 1000.0)
    payload = struct.pack("<iI", target, slope)
    p = transceive(args, 0x20, payload)
    print("q_current sent:", p.hex(" ").upper())


def cmd_speed(args) -> None:
    require_yes(args, "Speed command can rotate the motor immediately.")
    target = round(args.rpm * 100.0)
    accel = round(args.accel * 100.0)
    payload = struct.pack("<iI", target, accel)
    p = transceive(args, 0x21, payload)
    print("speed sent:", p.hex(" ").upper())


def cmd_motion_params(args) -> None:
    p = transceive(args, 0x14)
    if not p:
        print("no response")
        return
    print(f"raw motion params ({len(p)} bytes): {p.hex(' ').upper()}")
    # RS485 0x14 motion param layout (little-endian, units from protocol doc):
    # bytes 0-3:  position mode max speed  (s32, 0.01 rpm)
    # bytes 4-7:  max Q-axis current       (s32, 0.001 A)
    # bytes 8-11: current ramp rate        (s32, 0.001 A/s)
    # bytes 12-15: speed mode acceleration (s32, 0.01 rpm/s)
    # — cross-check against RS485 protocol doc 0x14 payload spec before trusting
    if len(p) >= 16:
        max_spd = struct.unpack("<i", p[0:4])[0] * 0.01
        max_cur = struct.unpack("<i", p[4:8])[0] * 0.001
        cur_ramp = struct.unpack("<i", p[8:12])[0] * 0.001
        spd_accel = struct.unpack("<i", p[12:16])[0] * 0.01
        print(f"  [guessed] pos_max_speed={max_spd:.2f} rpm")
        print(f"  [guessed] max_q_current={max_cur:.3f} A")
        print(f"  [guessed] current_ramp={cur_ramp:.3f} A/s")
        print(f"  [guessed] speed_accel={spd_accel:.2f} rpm/s")
        print("  NOTE: verify byte layout against RS485 protocol doc 0x14 before relying on these values")


def _wait_settled(ser, args, target_count: int, vel_thr_rpm: float = 2.0, pos_thr_counts: int = 50, n_consec: int = 3, timeout: float = 8.0) -> bool:
    deadline = time.monotonic() + timeout
    consec = 0
    while time.monotonic() < deadline:
        try:
            p = _transceive(ser, args, 0x0B)
            if len(p) >= 10:
                multi = struct.unpack("<i", p[2:6])[0]
                velocity = struct.unpack("<i", p[6:10])[0] * 0.01
                if abs(velocity) < vel_thr_rpm and abs(multi - target_count) < pos_thr_counts:
                    consec += 1
                    if consec >= n_consec:
                        return True
                else:
                    consec = 0
        except Exception:
            consec = 0
        time.sleep(0.05)
    return False


def cmd_sweep(args) -> None:
    require_yes(args, f"Sweep will rotate the motor ±{args.deg}° for {args.reps} rep(s).")
    amp = count_from_degrees(args.deg)
    print(f"sweep ±{args.deg}° ({amp} counts) × {args.reps} reps, settle_timeout={args.settle}s")

    with _open_serial(args) as ser:
        for rep in range(args.reps):
            # move to +deg (absolute)
            _transceive(ser, args, 0x22, struct.pack("<i", amp))
            print(f"  rep {rep + 1}/{args.reps}  +{args.deg}° ...", end="", flush=True)
            ok = _wait_settled(ser, args, amp, timeout=args.settle)
            print(" ok" if ok else " TIMEOUT")

            # move to -deg (absolute)
            _transceive(ser, args, 0x22, struct.pack("<i", -amp))
            print(f"  rep {rep + 1}/{args.reps}  -{args.deg}° ...", end="", flush=True)
            ok = _wait_settled(ser, args, -amp, timeout=args.settle)
            print(" ok" if ok else " TIMEOUT")

        # return to zero
        _transceive(ser, args, 0x22, struct.pack("<i", 0))
        print("  → 0° ...", end="", flush=True)
        ok = _wait_settled(ser, args, 0, timeout=args.settle)
        print(" ok" if ok else " TIMEOUT")

        # disable
        _transceive(ser, args, 0x2F)
        print("disabled")


def cmd_position(args, relative: bool) -> None:
    require_yes(args, "Position command can rotate the motor immediately.")
    count = args.count if args.count is not None else count_from_degrees(args.deg)
    payload = struct.pack("<i", count)
    p = transceive(args, 0x23 if relative else 0x22, payload)
    print(("relative" if relative else "absolute") + f" position sent: {count} count, payload={p.hex(' ').upper()}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GIM/ZE300/GDZ RS485 helper")
    parser.add_argument("--port", help="Serial port, e.g. /dev/cu.usbserial-XXXX")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--addr", type=lambda x: int(x, 0), default=1)
    parser.add_argument("--seq", type=lambda x: int(x, 0), default=0)
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--verbose", action="store_true")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list").set_defaults(func=cmd_list, no_port=True)
    sub.add_parser("version").set_defaults(func=cmd_version)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("disable").set_defaults(func=cmd_disable)
    sub.add_parser("clear-fault").set_defaults(func=cmd_clear_fault)
    sub.add_parser("set-zero").set_defaults(func=cmd_set_zero)
    sub.add_parser("home").set_defaults(func=cmd_home)

    cal = sub.add_parser("calibrate")
    cal.add_argument("--yes", action="store_true")
    cal.set_defaults(func=cmd_calibrate)

    cur = sub.add_parser("q-current")
    cur.add_argument("amps", type=float)
    cur.add_argument("--slope", type=float, default=0.2, help="A/s")
    cur.add_argument("--yes", action="store_true")
    cur.set_defaults(func=cmd_q_current)

    spd = sub.add_parser("speed")
    spd.add_argument("rpm", type=float)
    spd.add_argument("--accel", type=float, default=20.0, help="rpm/s")
    spd.add_argument("--yes", action="store_true")
    spd.set_defaults(func=cmd_speed)

    mp = sub.add_parser("motion-params")
    mp.set_defaults(func=cmd_motion_params)

    sw = sub.add_parser("sweep")
    sw.add_argument("--deg", type=float, default=15.0, help="amplitude in degrees (default 15)")
    sw.add_argument("--reps", type=int, default=3, help="number of back-and-forth repetitions")
    sw.add_argument("--settle", type=float, default=8.0, help="settle timeout per move in seconds")
    sw.add_argument("--yes", action="store_true")
    sw.set_defaults(func=cmd_sweep)

    abs_pos = sub.add_parser("abs-pos")
    abs_pos.add_argument("--deg", type=float, default=0.0)
    abs_pos.add_argument("--count", type=int)
    abs_pos.add_argument("--yes", action="store_true")
    abs_pos.set_defaults(func=lambda args: cmd_position(args, relative=False))

    rel_pos = sub.add_parser("rel-pos")
    rel_pos.add_argument("--deg", type=float, default=0.0)
    rel_pos.add_argument("--count", type=int)
    rel_pos.add_argument("--yes", action="store_true")
    rel_pos.set_defaults(func=lambda args: cmd_position(args, relative=True))

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "no_port", False) and not args.port:
        parser.error("--port is required for this command")
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
