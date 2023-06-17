import os
from cffi import FFI
from typing import List

from panda import LEN_TO_DLC
from panda.tests.libpanda.safety_helpers import PandaSafety, setup_safety_helpers

libpanda_dir = os.path.dirname(os.path.abspath(__file__))
libpanda_fn = os.path.join(libpanda_dir, "libpanda.so")

ffi = FFI()

ffi.cdef("""
typedef struct {
  unsigned char reserved : 1;
  unsigned char bus : 3;
  unsigned char data_len_code : 4;
  unsigned char rejected : 1;
  unsigned char returned : 1;
  unsigned char extended : 1;
  unsigned int addr : 29;
  unsigned char checksum;
  unsigned char data[64];
} CANPacket_t;
""", packed=True)

ffi.cdef("""
int safety_rx_hook(CANPacket_t *to_send);
int safety_tx_hook(CANPacket_t *to_push);
int safety_fwd_hook(int bus_num, int addr);
int set_safety_hooks(uint16_t mode, uint16_t param);
""")

ffi.cdef("""
typedef struct {
  volatile uint32_t w_ptr;
  volatile uint32_t r_ptr;
  uint32_t fifo_size;
  CANPacket_t *elems;
} can_ring;

extern can_ring *rx_q;
extern can_ring *txgmlan_q;
extern can_ring *tx1_q;
extern can_ring *tx2_q;
extern can_ring *tx3_q;

bool can_pop(can_ring *q, CANPacket_t *elem);
bool can_push(can_ring *q, CANPacket_t *elem);
void can_set_checksum(CANPacket_t *packet);
int comms_can_read(uint8_t *data, uint32_t max_len);
void comms_can_write(uint8_t *data, uint32_t len);
void comms_can_reset(void);
uint32_t can_slots_empty(can_ring *q);
""")

ffi.cdef("""
  typedef struct timestamp_t {
    uint16_t year;
    uint8_t month;
    uint8_t day;
    uint8_t weekday;
    uint8_t hour;
    uint8_t minute;
    uint8_t second;
  } timestamp_t;

  typedef struct {
    uint16_t id;
    timestamp_t timestamp;
    uint32_t uptime;
    char msg[50];
  } log_t;

  extern uint32_t *logging_bank;
  extern uint32_t logging_bank_size;
  extern uint32_t logging_rate_limit;

  void logging_init(void);
  void logging_tick(void);
  void log(const char* msg);
  uint8_t logging_read(uint8_t *buffer);
""")

setup_safety_helpers(ffi)

class CANPacket:
  reserved: int
  bus: int
  data_len_code: int
  rejected: int
  returned: int
  extended: int
  addr: int
  data: List[int]

class Panda(PandaSafety):
  # safety
  def safety_rx_hook(self, to_send: CANPacket) -> int: ...
  def safety_tx_hook(self, to_push: CANPacket) -> int: ...
  def safety_fwd_hook(self, bus_num: int, addr: int) -> int: ...
  def set_safety_hooks(self, mode: int, param: int) -> int: ...

  # logging
  def logging_init(self) -> None: ...
  def logging_tick(self) -> None: ...
  def log(self, msg: bytearray) -> None: ...
  def logging_read(self, buffer: bytearray) -> int: ...
  logging_bank: bytearray
  logging_bank_size: int
  logging_rate_limit: int

libpanda: Panda = ffi.dlopen(libpanda_fn)


# helpers

def make_CANPacket(addr: int, bus: int, dat):
  ret = ffi.new('CANPacket_t *')
  ret[0].extended = 1 if addr >= 0x800 else 0
  ret[0].addr = addr
  ret[0].data_len_code = LEN_TO_DLC[len(dat)]
  ret[0].bus = bus
  ret[0].data = bytes(dat)
  libpanda.can_set_checksum(ret)

  return ret