from msc import *
from sys import argv

with open(argv[1], 'rb') as f:
    mscFile = MscFile()
    mscFile.readFromFile(f)
    if len(argv) > 2:
        nums = [int(i,0) for i in argv[2:]]
        for num in nums:
            for i,script in enumerate(mscFile):
                if script.bounds[0] == num:
                    print('Offset %i = script_%i' % (num,i))
    else:
        for i,script in enumerate(mscFile):
            print('Offset %X = script_%i' % (script.bounds[0],i))
