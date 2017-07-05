from msc import *

with open("testAsm.txt","r") as f:
    text = f.read()

script = bytes()
for cmd in parseCommands(text):
    script += cmd.write()

fileBytes = MSC_MAGIC
fileBytes += struct.pack('<L', 0x10 + len(script))
fileBytes += struct.pack('<L', 0x10)
fileBytes += struct.pack('<L', 1)
fileBytes += struct.pack('<L', 22)
fileBytes += struct.pack('<L', 0x40)
fileBytes += struct.pack('<L', 0)
fileBytes += b'\x00' * 0x18

fileBytes += script

if len(fileBytes) % 0x10 != 0:
    fileBytes += b'\x00' * (0x10 - (len(fileBytes) % 0x10))

fileBytes += struct.pack('<L', 0x10)
fileBytes += b'\x00' * 0xc

with open("test.mscsb", 'wb') as f:
    f.write(fileBytes)
