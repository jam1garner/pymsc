from msc import *
from sys import argv
from os.path import isfile

scriptsFile = "Scripts"
if not isfile('Scripts') and len(argv) < 2:
    print('No "Scripts" file found or provided')
    quit()
elif len(argv) >= 2:
    if argv[1].lower() != '-s':
        scriptsFile = argv[1]
with open(scriptsFile, 'r') as f:
    lines = f.read().split('\n')
scriptPaths = [line.split('#')[0].strip() for line in lines if line.split('#')[0].strip() != '' and line.strip()[0] != '>' and line.strip()[0] != '|']
globalPaths = [line.split('#')[0].strip()[1:] for line in lines if line.split('#')[0].strip() != '' and line.strip()[0] == '>' and line.strip()[0] != '|']
savePaths = [line.split('#')[0].strip()[1:] for line in lines if line.split('#')[0].strip() != '' and line.strip()[0] != '>' and line.strip()[0] == '|']

strings = []
for globalPath in globalPaths:
    if isfile(globalPath):
        with open(globalPath, 'r') as f:
            globalLines = [l.split('#')[0].strip() for l in f.read().split('\n') if l.split('#')[0].strip() != '']
        for globalLine in globalLines:
            instruction = globalLine[:globalLine.find(' ')]

            if instruction == '.string':
                strings.append(globalLine[8:])
            elif instruction == '.alias':
                globalParams = globalLine[7:].replace(' ','').split(',')
                globalAliases[globalParams[1]] = int(globalParams[0], 0)

maxStringLength = 0
for string in strings:
    if len(string) > maxStringLength:
        maxStringLength = len(string)
if maxStringLength % 0x10 != 0:
    maxStringLength += 0x10 - (maxStringLength % 0x10)

entrypoint = 'script_0'

for i,script in enumerate(scriptPaths):
    if script[:1] == ":":
        script = script[1:]
        scriptPaths[i] = script
        entrypoint = 'script_%i' % i
    if not isfile(script):
        print('File "%s" not found' % (script))
        quit()

scripts = []
for script in scriptPaths:
    with open(script, 'r') as f:
        tempScript = MscScript()
        tempScript.cmds = parseCommands(f.read())
        scripts.append(tempScript)

scriptPositions = {}
currentPos = 0x10
for i,script in enumerate(scripts):
    scriptPositions['script_%i' % i] = currentPos
    currentPos += script.size()

scriptNames = scriptPositions.keys()
for script in scripts:
    for cmd in script:
        for i in range(len(cmd.parameters)):
            if cmd.parameters[i] in scriptNames:
                cmd.parameters[i] = scriptPositions[cmd.parameters[i]]

for i,script in enumerate(scripts):
    script.offset(scriptPositions['script_%i' % i])

fileBytes = MSC_MAGIC
fileBytes += struct.pack('<L', currentPos)
fileBytes += struct.pack('<L', scriptPositions[entrypoint])
fileBytes += struct.pack('<L', len(scriptNames))
fileBytes += struct.pack('<L', 0x16)#This probably doesn't matter?
fileBytes += struct.pack('<L', maxStringLength)
fileBytes += struct.pack('<L', len(strings))
fileBytes += b'\x00' * 0x18

for script in scripts:
    for cmd in script:
        fileBytes += cmd.write()

if len(fileBytes) % 0x10 != 0:
    fileBytes += b'\x00' * (0x10 - (len(fileBytes) % 0x10))

for i in range(len(scripts)):
    fileBytes += struct.pack('<L',scriptPositions['script_%i' % i])

if len(fileBytes) % 0x10 != 0:
    fileBytes += b'\x00' * (0x10 - (len(fileBytes) % 0x10))

for string in strings:
    fileBytes += string.encode('ascii')
    fileBytes += b'\x00' * (maxStringLength - len(string))

if len(argv) >= 3:
    for arg in argv[2:]:
        savePaths.append(arg)

if len(savePaths) == 0:
    savePaths = ["test.mscsb"]

for savePath in savePaths:
    with open(savePath, 'wb') as f:
        f.write(fileBytes)
