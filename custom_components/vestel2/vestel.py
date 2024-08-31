import asyncio

# KEY CODES AND COMMANDS:
# https://vestelvisualsolutions.com/eu/products/interactive-flat-panel/ifd75th653-3/files/vestel-visual-solutions-rs232-lan-customer-control-v1-1-b325fc453121.pdf

import logging
LOGGER = logging.getLogger(__name__)

VESTEL_STATE_ON = True
VESTEL_STATE_OFF = False

ATTRIBUTE_CMD = [
  "GETVOLUME",
  "GETHEADPHONEVOLUME",
  "GETSOURCE",
  "GETPROGRAM",
#  "GETSTANDBY",
#  "GETBACKLIGHT",
#  "GETCOUNTRY",
#  "GETSWVERSION",
  "GETMUTE"
]

class VestelHelper():
  def __init__(self, host, port = 1986):
    self.reader = None
    self.writer = None
    self.port = port
    self.host = host
    self.lock = asyncio.Lock()
    self.state = VESTEL_STATE_OFF
    self.attributes = {}

  async def _connect(self):
    fut = asyncio.open_connection(self.host, self.port)
    try:
      self.reader, self.writer = await asyncio.wait_for(fut, timeout=2)
      self.state = VESTEL_STATE_ON
    except:
      self.reader = None
      self.writer = None
      self.state = VESTEL_STATE_OFF

  async def _sendcommand(self, command, expect_response=True):
    async with self.lock:
      if self.writer == None:
        await self._connect()
      try:
        self.writer.write((command + "\n").encode())
        if expect_response:
          ret = await asyncio.wait_for(self.reader.readline(), timeout=2)
          return ret.decode()
      except:
        if expect_response == True:
          self.reader = None
          self.writer = None
          self.state = VESTEL_STATE_OFF
      return None

  async def sendkey(self, key):
    ret = await self._sendcommand("KEY {}".format(key), expect_response=False)

  async def command(self, command, expect_response=True):
    ret = await self._sendcommand(command, expect_response)
    if ret:
      if " is " in ret:
        ret = ret.split(" is ", 1)[-1].strip()
      elif " IS : " in ret:
        ret = ret.split(" IS : ", 1)[-1].strip()
      elif " to " in ret:
        ret = ret.split(" to ", 1)[-1].strip()
      elif " " in ret:
        ret = ret.split(" ", 1)[-1].strip()
      key = command.replace("GET", "").replace("SET", "")
      self.attributes[key] = ret.strip()
    return ret

  async def update(self):
    for cmd in ATTRIBUTE_CMD:
      ret = await self.command(cmd, expect_response=True)
      if ret is None:
        break
