from msc import *
from sys import argv

with open(argv[1], 'rb') as f:
    mscFile = MscFile()
    mscFile.readFromFile(f)
    mscFile.addDebugStrings()
    print(mscFile[int(argv[2])])
