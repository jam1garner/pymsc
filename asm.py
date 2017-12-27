#**************************************************************************#
# This file is part of pymsc which is released under MIT License. See file #
# LICENSE or go to https://github.com/jam1garner/pymsc/blob/master/LICENSE #
# for full license details.                                                #
#**************************************************************************#
from msc import *
from sys import argv
from os.path import isfile, dirname

#Parse args
savePaths = []
isLib = False
scriptsFile = None
state = None
for arg in argv[1:]:
    if state == "script":
        scriptsFile = arg
    elif state == "lib" or state == "library":
        isLib = True
        state = None #The next passed value should be handled normally
    elif state == "saveas":
        savePaths.append(arg)
    if state == None:
        if arg[:2] == "--":
            state = arg[2:].lower()
        else:
            if scriptsFile == None:
                scriptsFile = arg
            else:
                savePaths.append(arg)
    else:
        state = None

if scriptsFile == None:
    scriptsFile = "Scripts"

if not isfile(scriptsFile):
    print('No "Scripts" file found or provided')
    quit()

with open(scriptsFile, 'r') as f:
    lines = f.read().split('\n')
scriptPaths = [line.split('#')[0].strip() for line in lines if line.split('#')[0].strip() != '' and line.strip()[0] != '>' and line.strip()[0] != '|']
globalPaths = [line.split('#')[0].strip()[1:] for line in lines if line.split('#')[0].strip() != '' and line.strip()[0] == '>' and line.strip()[0] != '|']
savePaths += [line.split('#')[0].strip()[1:] for line in lines if line.split('#')[0].strip() != '' and line.strip()[0] != '>' and line.strip()[0] == '|']
if len(savePaths) == 0:
    savePaths = [dirname(__file__)+".mscsb"]

print("Assembling to files:\n"+"\n".join(savePaths))

globalAliases = {}

if isLib:
    fileBytes = b'MSCLIB\x00'
    fileBytes += struct.pack('<L', len(scriptPaths))
    fileBytes += struct.pack('<L', len(globalPaths))
else:
    strings = []
    exports = {}
    imports = []
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
                elif instruction == '.export':
                    globalParams = globalLine[7:].strip().split(' ')
                    exports[globalParams[1]] = globalParams[0]
                    if not globalParams[0] in strings:
                        strings.append(globalParams[0])
                elif instruction == '.import':
                    importPath = globalLine[8:].strip().strip("'").strip('"').strip()
                    with open(importPath) as f:
                        pass

    entrypoint = 'script_0'

    for i,script in enumerate(scriptPaths):
        if script[0] == ":":
            script = script[1:]
            scriptPaths[i] = script
            entrypoint = 'script_%i' % i
        if not isfile(script):
            print('File "%s" not found' % (script))
            quit()

    scripts = []
    for script in scriptPaths:
        with open(script, 'r', encoding='utf-8') as f:
            tempScript = MscScript()
            tempScript.cmds = parseCommands(f.read(), globalAliases, strings)
            tempScript.name = script
            scripts.append(tempScript)

    scriptPositions = {}
    currentPos = 0x10
    for i,script in enumerate(scripts):
        scriptPositions['script_%i' % i] = currentPos
        scriptPositions[script.name[:script.name.find('.')]] = currentPos 
        currentPos += script.size()

    scriptNames = scriptPositions.keys()
    for script in scripts:
        for cmd in script:
            for i in range(len(cmd.parameters)):
                if cmd.parameters[i] in scriptNames:
                    cmd.parameters[i] = scriptPositions[cmd.parameters[i]]

    for i,script in enumerate(scripts):
        script.offset(scriptPositions['script_%i' % i])


    maxStringLength = 0
    for string in strings:
        if len(string) > maxStringLength:
            maxStringLength = len(string)
    if maxStringLength % 0x10 != 0:
        maxStringLength += 0x10 - (maxStringLength % 0x10)

    fileBytes = MSC_MAGIC
    fileBytes += struct.pack('<L', currentPos)
    fileBytes += struct.pack('<L', scriptPositions[entrypoint])
    fileBytes += struct.pack('<L', len(scripts))
    fileBytes += struct.pack('<L', 0x16)#This probably doesn't matter?
    fileBytes += struct.pack('<L', maxStringLength)
    fileBytes += struct.pack('<L', len(strings))
    fileBytes += struct.pack('<L', 0)
    fileBytes += struct.pack('<L', 0)
    fileBytes += b'\x00' * 0x10

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
        fileBytes += string.encode('utf-8')
        fileBytes += b'\x00' * (maxStringLength - len(string))

    if len(fileBytes) % 0x10 != 0:
        fileBytes += b'\x00' * (0x10 - (len(fileBytes) % 0x10))

for savePath in savePaths:
    with open(savePath, 'wb') as f:
        f.write(fileBytes)
