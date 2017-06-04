import struct, tempfile

MSC_MAGIC = b'\xB2\xAC\xBC\xBA\xE6\x90\x32\x01\xFD\x02\x00\x00\x00\x00\x00\x00'

COMMAND_NAMES = {
    0x2 : "BeginSub",
    0x3 : "End",
    0x4 : "unk_4",
    0x6 : "return_6",
    0x7 : "return",
    0xa : "pushInt",
    0xb : "pushVar",
    0xd : "pushShort",
    0xe : "unk_E",
    0xf : "unk_F",
    0x10 : "unk_10",
    0x11 : "unk_11",
    0x12 : "unk_12",
    0x13 : "unk_13",
    0x14 : "unk_14",
    0x15 : "unk_15",
    0x16 : "BitwiseAnd",
    0x17 : "unk_17",
    0x1a : "unk_1A",
    0x1c : "Set_Variable",
    0x1d : "variable_manipulation1",
    0x1e : "variable_manipulation2",
    0x1f : "variable_manipulation3",
    0x23 : "variable_manipulation4",
    0x25 : "lessThan",
    0x26 : "lessOrEqual",
    0x27 : "equals",
    0x28 : "notEquals",
    0x29 : "greater",
    0x2a : "greaterOrEqual",
    0x2b : "true",
    0x2c : "printf",
    0x2d : "Call_Func",
    0x2e : "unk_2E",
    0x2f : "Call_Func2",
    0x30 : "call_func3",
    0x31 : "Call_Func4",
    0x34 : "if",
    0x35 : "unk_35",
    0x36 : "else",
    0x38 : "unk_38",
    0x39 : "unk_39",
    0x3a : "floatAdd",
    0x3b : "unk_3B",
    0x3c : "unk_3C",
    0x3d : "unk_3D",
    0x3e : "unk_3E",
    0x41 : "variable_manipulation5",
    0x42 : "variable_manipulation6",
    0x43 : "variable_manipulation7",
    0x44 : "variable_manipulation8",
    0x45 : "variable_manipulation9",
    0x46 : "float_compare1",
    0x47 : "float_compare2",
    0x48 : "float_compare3",
    0x49 : "float_compare4",
    0x4a : "float_compare5",
    0x4b : "float_compare6",
    0x70 : "unk_70"
}

COMMAND_FORMAT = {
    0x2 : 'BBBB',
    0x3 : '',
    0x4 : 'I',
    0x6 : '',
    0x7 : '',
    0x0a : 'I',
    0x0b : 'BBB',
    0x0d : 'H',
    0x0e : '',
    0x0f : '',
    0x10 : '',
    0x11 : '',
    0x12 : '',
    0x13 : '',
    0x14 : 'BBB',
    0x15 : 'BBB',
    0x16 : '',
    0x17 : '',
    0x1a : '',
    0x1c : 'BBB',
    0x1d : 'BBB',
    0x1e : 'BBB',
    0x1f : 'BBB',
    0x23 : 'BBB',
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
    0x41 : 'BBB',
    0x42 : 'BBB',
    0x43 : 'BBB',
    0x44 : 'BBB',
    0x45 : 'BBB',
    0x46 : '',
    0x47 : '',
    0x48 : '',
    0x49 : '',
    0x4a : '',
    0x4b : '',
    0x70 : 'BB',
}

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
            self.paramSize = struct.calcsize(COMMAND_FORMAT[self.command])
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

    def read(self, f, start, end):
        self.bounds = [start, end]
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

    def readFromBytes(self, b):
        with tempfile.SpooledTemporaryFile(mode='w+b') as f:
            f.write(b)
            f.seek(0)
            readFromFile(f, '>')

    def getScriptAtLocation(self, location):
        for script in self.scripts:
            if script.bounds[0] <= location and script.bounds[1] > location:
                return script
