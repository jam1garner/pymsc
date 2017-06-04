import sys
from msc import *

with open(sys.argv[1], 'rb') as f:
    mscFile = MscFile()
    mscFile.readFromFile(f)
    with open('dump.txt', 'w') as out:
        for script in mscFile:
            print((' ' * 20) + script.name, file=out)
            print('-' * 50, file=out)
            for command in script:
                print(command, file=out)
