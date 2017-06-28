import sys
from msc import *

fname = sys.argv[1]

mscFile = MscFile()

with open(fname, 'rb') as f:
    mscFile.readFromFile(f)

mscFile.addDebugStrings()
mscFile.addScriptNames()

with open('dump.txt', 'w') as out:
    scriptNum = 0
    for script in mscFile:
        print((' ' * 20) + script.name, file=out)
        print('-' * 50, file=out)
        commandNum = 0
        for command in script:
            print(command, file=out)
            commandNum += 1
        scriptNum += 1
    print('',file=out)
    for string in mscFile.strings:
        print('.string      "'+string+'"',file=out)
