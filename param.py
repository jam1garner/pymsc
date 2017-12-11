#**************************************************************************#
# This file is part of pymsc which is released under MIT License. See file #
# LICENSE or go to https://github.com/jam1garner/pymsc/blob/master/LICENSE #
# for full license details.                                                #
#**************************************************************************#
from struct import unpack,pack

class u8(int):
    size = 1
    def __bytes__(self):
        return b'\x01'+pack('>B', self)

    def unpack(b):
        return u8(unpack('>B', b)[0])

class s8(int):
    size = 1
    def __bytes__(self):
        return b'\x02'+pack('>b', self)

    def unpack(b):
        return s8(unpack('>b', b)[0])

class u16(int):
    size = 2
    def __bytes__(self):
        return b'\x03'+pack('>H', self)

    def unpack(b):
        return u16(unpack('>H', b)[0])

class s16(int):
    size = 2
    def __bytes__(self):
        return b'\x04'+pack('>h', self)

    def unpack(b):
        return s16(unpack('>h', b)[0])

class u32(int):
    size = 4
    def __bytes__(self):
        return b'\x05'+pack('>L', self)

    def unpack(b):
        return u32(unpack('>L', b)[0])

class s32(int):
    size = 4
    def __bytes__(self):
        return b'\x06'+pack('>l', self)

    def unpack(b):
        return s32(unpack('>l', b)[0])

class f32(float):
    size = 4
    def __bytes__(self):
        return b'\x07'+pack('>f', self)

    def unpack(b):
        return f32(unpack('>f', b)[0])

class pString(str):
    size = None
    def __bytes__(self):
        return b'\x08'+pack('>L',len(self))+self.encode('latin8')

    def unpack(b):
        return pString(b.decode('latin8'))

class Group(list):
    def __init__(self):
        self.entryCount = 1

    def __bytes__(self):
        b = b'\x20' + pack('>L', int(self.entryCount))
        for i in self:
            b += bytes(i)
        return b

    def entry(self, i):
        if self.entryCount == 0:
            return []
        entrySize = int((len(self) / self.entryCount) + 0.5)
        return self[i * entrySize : (i+1) * entrySize]

    def setEntry(self, i, newEntry):
        if self.entryCount == 0:
            raise TypeError("Entry size is zero")
        entrySize = int((len(self) / self.entryCount) + 0.5)
        for j, k in enumerate(range(i*entrySize, (i+1) * entrySize)):
            self[j] = newEntry[k]


    def setEntrySize(self, newSize):
        if self.entryCount == 0:
            return
        entrySize = int((len(self) / self.entryCount) + 0.5)
        
        j = []
        for i in range(self.entryCount):
            j += (self.entry(i)[:newSize] + ([None] * (newSize - entrySize)))
        self.clear()
        for i in j:
            self.append(i)

    def entries(self):
        l = []
        for i in range(self.entryCount):
            l.append(self.entry(i))
        return l

    def deleteEntry(self, i):
        if self.entryCount == 0:
            return
        entrySize = int((len(self) / self.entryCount) + 0.5)
        del self[i * entrySize : (i+1) * entrySize]

    def unpack(b, start=4, groupType=None):
        isFile = groupType != None
        if groupType == None:
            g = Group()
        else:
            g = groupType()
        if start == 4:
            g.entryCount = unpack('>L', b[:4])[0]
        else:
            g.entryCount = 1

        i = 0
        values = b[start:]
        while i < len(values):
            try:
                valType = types[values[i]]
            except KeyError:
                i += 1
                break
            if valType == pString:
                length = unpack('>L', values[i+1:i+5])[0]
                g.append(pString.unpack(values[i+5 : i+5+length]))
                i += 5+length
            elif valType != Group:
                g.append(valType.unpack(values[i+1 : i+1+valType.size]))
                i += valType.size + 1
            else:
                if not isFile and len(g) % g.entryCount == 0 and len(g) != 0:
                    break
                else:
                    newGroup, groupSize = Group.unpack(values[i+1:])
                    i += 5+groupSize
                    g.append(newGroup)

        return (g, i)

class ParamFile(Group):
    def __bytes__(self):
        b = b'\xFF\xFF' + (b'\x00' * 6)
        for i in self:
            b += bytes(i)
        return b

    def unpack(b):
        return Group.unpack(b, 0, ParamFile)[0]

types = {1 : u8, 2 : s8, 3 : u16, 4 : s16, 5 : u32, 6 : s32, 7 : f32, 8 : pString, 32 : Group}

def openParam(f):
    if isinstance(f, str):
        f = open(f, 'rb')

    if not hasattr(f, 'read'):
        raise TypeError

    f.seek(8)
    p = ParamFile.unpack(f.read())

    f.close()

    return p

def saveParam(param, f):
    if isinstance(f, str):
        f = open(f, 'wb')

    if not hasattr(f, 'write'):
        raise TypeError

    f.write(bytes(p))

    f.close()