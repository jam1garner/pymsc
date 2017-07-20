from msc import *
from sys import argv

def RepresentsInt(s):
    try:
        int(s, 0)
        return True
    except ValueError:
        return False

def getOffsetFromScriptName(mscFile, name):
    if name[:7] == "script_":
        scriptNum = int(name[7:],0)
        return mscFile[scriptNum].bounds[0]
    else:
        return None

with open(argv[1], 'rb') as f:
    mscFile = MscFile()
    mscFile.readFromFile(f)
    print()
    if len(argv) > 2:
        num = int(argv[2] ,0) if RepresentsInt(argv[2]) else getOffsetFromScriptName(mscFile, argv[2])
        for i,script in enumerate(mscFile):
            if script.bounds[0] <= num and num < script.bounds[1]:
                print('Offset %X is in script_%i (offset %X)' % (num,i,script.bounds[0]))
    else:
        for i,script in enumerate(mscFile):
            print('Offset %X = script_%i' % (script.bounds[0],i))
