import struct, tempfile

MSC_MAGIC = b'\xB2\xAC\xBC\xBA\xE6\x90\x32\x01\xFD\x02\x00\x00\x00\x00\x00\x00'

COMMAND_NAMES = {
    0x0 : "nop",
    0x2 : "BeginSub",
    0x3 : "End",
    0x4 : "jump4",
    0x5 : "jump5",
    0x6 : "return_6",
    0x7 : "return_7",
    0x8 : "return_8",
    0x9 : "return_9",
    0xa : "pushInt",
    0xb : "pushVar",
    0xd : "pushShort",
    0xe : "addi",
    0xf : "subi",
    0x10 : "multi",
    0x11 : "divi",
    0x12 : "modi",
    0x13 : "negi",
    0x14 : "i++",
    0x15 : "i--",
    0x16 : "BitwiseAnd",
    0x17 : "BitwiseOr",
    0x18 : "BitwiseNot",
    0x19 : "BitwiseXor",
    0x1a : "leftShift",
    0x1b : "rightShift",
    0x1c : "setVar",
    0x1d : "i+=",
    0x1e : "i-=",
    0x1f : "i*=",
    0x20 : "i/=",
    0x21 : "i%=",
    0x22 : "i&=",
    0x23 : "i|=",
    0x24 : "i^=",
    0x25 : "equals",
    0x26 : "notEqual",
    0x27 : "lessThan",
    0x28 : "lessOrEqual",
    0x29 : "greater",
    0x2a : "greaterOrEqual",
    0x2b : "not",
    0x2c : "printf",
    0x2d : "Call_Func",
    0x2e : "unk_2E",
    0x2f : "Call_Func2",
    0x30 : "call_func3",
    0x31 : "Call_Func4",
    0x32 : "push",
    0x33 : "pop",
    0x34 : "if",
    0x35 : "ifNot",
    0x36 : "else",
    0x37 : "unk_37",
    0x38 : "unk_38",
    0x39 : "unk_39",
    0x3a : "addf",
    0x3b : "subf",
    0x3c : "multf",
    0x3d : "divf",
    0x3e : "negf",
    0x3f : "f++",
    0x40 : "f--",
    0x41 : "floatVarSet",
    0x42 : "float+=",
    0x43 : "float-=",
    0x44 : "float*=",
    0x45 : "float/=",
    0x46 : "floatGreater",
    0x47 : "floatLessOrEqual",
    0x48 : "floatLess",
    0x49 : "floatNotEqual",
    0x4a : "floatEqual",
    0x4b : "floatGreaterOrEqual",
    0x4c : "unk_4c",
    0x4d : "exit"
}

COMMAND_FORMAT = {
    0x0 : '',
    0x2 : 'HH',
    0x3 : '',
    0x4 : 'I',
    0x5 : 'I',
    0x6 : '',
    0x7 : '',
    0x8 : '',
    0x9 : '',
    0xa : 'I',
    0xb : 'BH',
    0xd : 'H',
    0xe : '',
    0xf : '',
    0x10 : '',
    0x11 : '',
    0x12 : '',
    0x13 : '',
    0x14 : 'BH',
    0x15 : 'BH',
    0x16 : '',
    0x17 : '',
    0x1a : '',
    0x1c : 'BH',
    0x1d : 'BH',
    0x1e : 'BH',
    0x1f : 'BH',
    0x20 : 'BH',
    0x21 : 'BH',
    0x22 : 'BH',
    0x23 : 'BH',
    0x24 : 'BH',
    0x25 : '',
    0x26 : '',
    0x27 : '',
    0x28 : '',
    0x29 : '',
    0x2a : '',
    0x2b : '',
    0x2c : 'B',
    0x2d : 'BB',
    0x2e : 'I',
    0x2f : 'B',
    0x30 : 'B',
    0x31 : 'B',
    0x32 : '',
    0x33 : '',
    0x34 : 'I',
    0x35 : 'I',
    0x36 : 'I',
    0x38 : 'B',
    0x39 : 'B',
    0x3a : '',
    0x3b : '',
    0x3c : '',
    0x3d : '',
    0x3e : '',
    0x40 : 'BH',
    0x41 : 'BH',
    0x42 : 'BH',
    0x43 : 'BH',
    0x44 : 'BH',
    0x45 : 'BH',
    0x46 : '',
    0x47 : '',
    0x48 : '',
    0x49 : '',
    0x4a : '',
    0x4b : '',
    0x4c : '',
    0x4d : ''
}

TYPE_SIZES = {
    'B' : 1,
    'H' : 2,
    'I' : 4
}

def getSizeFromFormat(formatString):
    s = 0
    for char in formatString:
        s += TYPE_SIZES[char]
    return s

def disassembleCommands(rawCommands, startOffset):
    pos = 0
    commands = []
    while pos < len(rawCommands):
        newCommand = Command()
        newCommand.read(rawCommands, pos)
        newCommand.commandPosition = startOffset + pos
        commands.append(newCommand)
        pos += (1 + newCommand.paramSize)
    return commands

class Command:
    def __init__(self):
        self.command = 0
        self.parameters = []
        self.pushBit = False
        self.paramSize = 0
        self.commandPosition = 0

    def read(self, byteBuffer, pos):
        self.command = int(byteBuffer[pos]) & 0x7F
        self.pushBit = (int(byteBuffer[pos]) & 0x80) != 0
        if self.command in COMMAND_NAMES:
            self.paramSize = getSizeFromFormat(COMMAND_FORMAT[self.command])
            self.parameters = list(struct.unpack('>'+COMMAND_FORMAT[self.command], byteBuffer[pos+1:pos+1+self.paramSize]))
        else:
            self.command = 0xFF #unknown command, display as ???

    def __strParams(self):
        params = ""
        for i in range(len(self.parameters)):
            params += hex(self.parameters[i])
            if i != len(self.parameters) - 1:
                params += ', '
        return params

    def __str__(self):
        if self.pushBit:
            temp = ' -> '
        else:
            temp = '    '

        com = "{0:0{1}x}".format(self.commandPosition,8).upper()+':'+temp+' '+COMMAND_NAMES[self.command]+' '
        if len(com) < 37:
            com += (37 - len(com)) * ' '
        return com+self.__strParams()

class MscScript:
    def __init__(self):
        self.cmds = []
        self.name = 'Unnamed Script'
        self.bounds = [0,0]
        self._iterationPosition = 0

    def __getitem__(self, key):
        return self.cmds[key]

    def __iter__(self):
        return self

    def __next__(self):
        if self._iterationPosition >= len(self.cmds):
            raise StopIteration
        else:
            self._iterationPosition += 1
            return self.cmds[self._iterationPosition - 1]

    def __str__(self):
        returnVal = ""
        for command in self.cmds:
            returnVal += str(command) + "\n"
        return returnVal

    def __len__(self):
        return len(self.cmds)

    def read(self, f, start, end):
        self.bounds = [start - 0x30, end - 0x30]
        f.seek(start)
        self.cmds = disassembleCommands(f.read(end - start), start - 0x30)

    def getInstructionText(self, index):
        if index < 0 or index >= len(self.cmds):
            return ""
        else:
            return str(cmds[index])

    def getIndexOfInstruction(self, location):
        for i in range(len(self.cmds)):
            cmd = self.cmds[i]
            if cmd.commandPosition == location:
                return i
        return 0

    def getInstructionOfIndex(self, index):
        return cmd[index].commandPosition

def readInt(f, endian):
    try:
        return struct.unpack(endian+'L', f.read(4))[0]
    except struct.error as e:
        print('pos - '+str(f.tell()))
        print(e.with_traceback)
        raise e

class MscFile:
    def __init__(self):
        self.scripts = []
        self.strings = []
        self.entryPoint = 0
        self.stringSize = 0
        self.unk = 0
        self._iterationPosition = 0

    def __getitem__(self, key):
        return self.scripts[key]

    def __iter__(self):
        return self

    def __next__(self):
        if self._iterationPosition >= len(self.scripts):
            raise StopIteration
        else:
            self._iterationPosition += 1
            return self.scripts[self._iterationPosition - 1]

    def __str__(self):
        returnVal = ""
        for script in self.scripts:
            returnVal += (' ' * 20) + script.name + '\n' + ('-' * 50) + '\n'
            for command in script:
                returnVal += str(command) + "\n"
        return returnVal

    def __len__(self):
        return len(self.scripts)

    def readFromFile(self, f, headerEndianess = '<'):
        f.seek(0x10)
        entriesOffset = readInt(f, headerEndianess) + 0x30
        endOfScripts = entriesOffset
        if entriesOffset % 0x10 != 0:
            entriesOffset += 0x10 - (entriesOffset % 0x10)
        self.entryPoint = readInt(f, headerEndianess)
        entryCount = readInt(f, headerEndianess)
        self.unk = readInt(f, headerEndianess)
        self.stringSize = readInt(f, headerEndianess)
        stringCount = readInt(f, headerEndianess)
        scriptOffsets = []
        f.seek(entriesOffset)
        for i in range(entryCount):
            scriptOffsets.append(readInt(f, headerEndianess) + 0x30)
        sortedScriptOffsets = scriptOffsets
        sortedScriptOffsets.sort()
        if f.tell() % 0x10 != 0:
            f.seek(0x10 - (f.tell() % 0x10), 1)
        for i in range(stringCount):
            self.strings.append(f.read(self.stringSize).decode('utf-8').replace('\x00',''))
        for j in scriptOffsets:
            i = sortedScriptOffsets.index(j)
            start = sortedScriptOffsets[i]
            if i != len(scriptOffsets) - 1:
                end = sortedScriptOffsets[i+1]
            else:
                end = endOfScripts
            newScript = MscScript()
            newScript.name = 'Script '+str(i)
            if i == self.entryPoint:
                newScript.name = 'Entrypoint Script'
            newScript.read(f, start, end)
            self.scripts.append(newScript)

    def readFromBytes(self, b, headerEndianess='>'):
        with tempfile.SpooledTemporaryFile(mode='w+b') as f:
            f.write(b)
            f.seek(0)
            self.readFromFile(f, headerEndianess)

    def getScriptAtLocation(self, location):
        for script in self.scripts:
            if script.bounds[0] <= location and script.bounds[1] > location:
                return script
