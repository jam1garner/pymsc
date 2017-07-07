import sys, os
from msc import *

fname = sys.argv[1]

mscFile = MscFile()

with open(fname, 'rb') as f:
    mscFile.readFromFile(f)

if not os.path.isdir("output/"):
    os.mkdir("output/")

with open('output/Scripts', 'w') as f:
    print('>globals.txt', file=f)
    with open('output/globals.txt', 'w') as globalFile:
        for string in mscFile.strings:
            print('.string '+string, file=globalFile)

    for i,script in enumerate(mscFile):
        print('%sscript_%i.txt' % (':' if mscFile.entryPoint == script.bounds[0] else '',i),file=f)
        jumpPositions = []
        for cmd in script:
            if cmd.command in [0x4, 0x5, 0x2e, 0x34, 0x35, 0x36]:
                if not cmd.parameters[0] in jumpPositions:
                    jumpPositions.append(cmd.parameters[0])
                    cmd.parameters[0] = 'loc_%X' % (cmd.parameters[0] - script.bounds[0])
        with open('output/script_%i.txt' % (i), 'w') as scriptFile:
            for cmd in script:
                if cmd.commandPosition in jumpPositions:
                    print('',file=scriptFile)
                    print('loc_%X:' % (cmd.commandPosition - script.bounds[0]), file=scriptFile)
                print((' ' * 8 if len(jumpPositions) > 0 else '') + COMMAND_NAMES[cmd.command] + ('.' if cmd.pushBit else '') + ' '+cmd.strParams(), file=scriptFile)
