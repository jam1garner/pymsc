from msc import *
import struct
from sys import argv
from time import sleep

class FunctionInfo:
    def __init__(self, thisLocalVarPos, returnAddress):
        self.localVarPos = thisLocalVarPos
        self.returnAddress = returnAddress

    def restore(self):
        localVarPos = self.localVarPos
        evalPos = returnAddress

def syscall(syscallNum, args):
    global sharedVars,evalPos
    if syscallNum == 0x16:
        operation = args[0]
        if operation == 0x6:
            if not args[1] in sharedVars:
                print("ERROR: Variable 0x%08X doesn't not exist (Accessed at %X)" % (args[1],evalPos))
                quit()
            else:
                push(sharedVars[args[1]])
        elif operation == 0x7:
            sharedVars[args[2]] = args[1]
        elif operation == 0x10:
            if not args[1] in sharedVars:
                print("ERROR: Variable 0x%08X doesn't not exist (Accessed at %X)" % (args[1],evalPos))
                quit()
            else:
                push(0 if sharedVars[args[1]] == 0 else 1)
        elif operation == 0x2710:
            sharedVars[args[1]] = 0
        elif operation == 0x2711:
            sharedVars[args[1]] = 1
    else:
        print("ERROR: Unsupported syscall 0x%X at location %X" % (syscallNum,evalPos))
        quit()

def push(val, actuallyPush=True):
    global mscFile,mscFileBytes,stack,functionStack,stackPos,localVarPos,evalPos,exceptionRegister,globalVars,executing,strings,linkRegister
    if not actuallyPush:
        return
    if stackPos == 0x80:
        print("At instruction %08X:")
        print("WARNING: STACK OVERFLOW, STACK INDEX OVERWRITTEN ")

    newVal = None
    if type(val) == int:
        newVal = (val & 0xFFFFFFFF)
    elif type(val) == float:
        newVal = floatToInt(val)
    else:
        print("ERROR: Invalid type to push type=%s at position %X (Object = %s)" % (str(type(val)), evalPos, str(val)))
        raise TypeError("Invalid push type")

    if stackPos < 0x80 and stackPos >= 0:
        stack[stackPos] = newVal
    elif stackPos == 0x80:
        stackPos = newVal
    elif stackPos < 0:
        globalVars[0x8A + stackPos] = newVal
    else:
        print("WARNING: WRITE OOB (Not in emulated memory)")
    stackPos += 1

def pop():
    global mscFile,mscFileBytes,stack,functionStack,stackPos,localVarPos,evalPos,exceptionRegister,globalVars,executing,strings,linkRegister
    if stackPos == 0:
        print("At instruction %08X:" % evalPos)
        print("WARNING: STACK UNDERFLOW")
    stackPos -= 1
    value = None
    if stackPos < 0 and stackPos >= -0x8A:
        value = globalVars[0x8A + stackPos]
    elif stackPos >= 0 and stackPos < 0x80:
        value = stack[stackPos]
    elif value == 0x80:
        value = stackPos
    else:
        print("WARNING: OOB POP UNHANDLED BY EMU, RETURNING 0")
        print("         this will cause inaccuracy in emulation")
        return 0

    if value == None:
        print("WARNING: POPPED UNINITIALIZED VALUE, ASSUMING 0")
        return 0
    else:
        return value

def getVar(varType, varNum):
    global mscFile,mscFileBytes,stack,functionStack,stackPos,localVarPos,evalPos,exceptionRegister,globalVars,executing,strings,linkRegister
    if varType == 0: #(Local)
        if localVarPos + varNum == 0x80:
            return stackPos
        elif localVarPos + varNum < 0x80:
            return stack[localVarPos+varNum]
        else:
             print("WARNING: OOB READ OF LOCAL VAR %i AT LOCATION %X" % (varNum, evalPos))
             print("         IS UNMAPPED IN EMULATOR MEMORY, TO AVOID")
             print("         ERRORS ASSUMING VALUE OF 0, THIS WILL")
             print("         LIKELY BE INACCURATE TO ON CONSOLE BEHAIVIOR")
             return 0
    elif varType == 1: #(global variable)
        if varNum < 0x8A:
            return globalVars[varNum]
        elif varNum >= 0x8A and varNum < 0x10A:
            return stack[varNum - 0x8A]
        elif varNum == 0x10A:
            return stackPos
        elif varNum > 0x10A:
            print("WARNING: OOB READ OF GLOBAL VAR %i AT LOCATION %X" % (varNum, evalPos))
            print("         IS UNMAPPED IN EMULATOR MEMORY, TO AVOID")
            print("         ERRORS ASSUMING VALUE OF 0, THIS WILL")
            print("         LIKELY BE INACCURATE TO ON CONSOLE BEHAIVIOR")
            return 0
    else:
        print("ERROR: UNKNOWN VARIABLE TYPE %i AT LOCATION %X" % (varType, evalPos))
        raise ValueError

def setVar(varType, varNum, value, pushBit):
    global mscFile,mscFileBytes,stack,functionStack,stackPos,localVarPos,evalPos,exceptionRegister,globalVars,executing,strings,linkRegister
    if varType == 0: #(Local)
        if localVarPos + varNum == 0x80:
            stackPos = value
        elif localVarPos + varNum < 0x80:
            stack[localVarPos+varNum] = value
        else:
             print("WARNING: OOB WRITE OF LOCAL VAR %i AT LOCATION %X" % (varNum, evalPos))
             print("         IS UNMAPPED IN EMULATOR MEMORY, THIS WRITE")
             print("         WILL NOT HAVE HAPPENED MORE OR LESS")
    elif varType == 1: #(global variable)
        if varNum < 0x8A:
            globalVars[varNum] = value
        elif varNum >= 0x8A and varNum < 0x10A:
            stack[varNum - 0x8A] = value
        elif varNum == 0x10A:
            stackPos = value
        elif varNum > 0x10A:
            print("WARNING: OOB READ OF GLOBAL VAR %i AT LOCATION %X" % (varNum, evalPos))
            print("         IS UNMAPPED IN EMULATOR MEMORY, THIS WRITE")
            print("         WILL NOT HAVE HAPPENED MORE OR LESS")
    else:
        print("ERROR: UNKNOWN VARIABLE TYPE %i AT LOCATION %X" % (varType, evalPos))
        raise ValueError
    if pushBit:
        push(value)

#Converts an int representing bytes to a float
#Example 0x3F800000 -> 1.0
def intToFloat(val):
    return struct.unpack('>f', struct.pack('>L', val))[0]

#Converts a float to an int representing bytes
#Example 1.0 -> 0x3F800000
def floatToInt(val):
    return struct.unpack('>L', struct.pack('>f', val))[0]

def printf(printString, args):
    specifierLocs = [i for i,j in enumerate(printString) if j == '%' and i < len(printString) and printString[i+1] in ['X', 'i', 'f', '0']]
    for i,j in enumerate(specifierLocs):
        if printString[j+1] == 'f':
            args[i] = intToFloat(args[i])
    print(printString % tuple(args))

def evalCommand(command):
    global mscFile,mscFileBytes,stack,functionStack,stackPos,localVarPos,evalPos,exceptionRegister,globalVars,executing,strings,linkRegister
    if command == None or command.command == 0xFFFE:
        if evalPos != None:
            print("Error: Invalid command at %X" % evalPos)
            quit()
        else:
            print("Error: Invalid command (And Invalid eval position)")
        executing = False
        return

     #This is used for determining if to add command size to
    isJump = False

    c = command.command
    cParams = command.parameters
    pushBit = command.pushBit
    if c == 0x0: #nop
        pass
    elif c == 0x1:
        pass
    elif c == 0x2: #begin
        functionStack.append(FunctionInfo(localVarPos, linkRegister))
        stackPos -= cParams[0]
        localVarPos = stackPos
        stackPos += cParams[1]
    elif c == 0x3: #end
        if len(functionStack) == 0:
            executing = False
            return
        fInfo = functionStack.pop()
        if fInfo.returnAddress == None:
            executing = False
            return
        localVarPos = fInfo.localVarPos
        evalPos = fInfo.returnAddress
        isJump = True
    elif c in [0x4, 0x5, 0x36]:
        isJump = True
        evalPos = cParams[0]
    elif c == 0x6 or c == 0x8: #return value
        fInfo = functionStack.pop()
        if fInfo.returnAddress == None:
            executing = False
            return
        localVarPos = fInfo.localVarPos
        evalPos = fInfo.returnAddress
        isJump = True
    elif c == 0x7 or c == 0x9: #return no value
        fInfo = functionStack.pop()
        if fInfo.returnAddress == None:
            executing = False
            return
        localVarPos = fInfo.localVarPos
        evalPos = fInfo.returnAddress
        isJump = True
    elif c == 0xA or c == 0xD:
        push(cParams[0], pushBit)
    elif c == 0xB:
        print(evalPos)
        push(getVar(cParams[0], cParams[1]), pushBit)
    elif c == 0xC:
        pass
    elif c == 0xE:
        push(pop() + pop(), pushBit)  #Add int
    elif c == 0xF:
        push((-pop()) + pop(), pushBit)  #Subtract int
    elif c == 0x10:
        push(pop() * pop(), pushBit)  #Multiply int
    elif c == 0x11:
        divideBy = pop()
        push(pop() // divideBy, pushBit) #Divide int
    elif c == 0x12:
        divideBy = pop()
        push(pop() % divideBy, pushBit) #Mod int
    elif c == 0x13:
        push(-pop(), pushBit) #Negate value
    elif c == 0x14:
        setVar(cParams[0], cParams[1], getVar(cParams[0], cParams[1]) + 1,pushBit) #Var++
    elif c == 0x15:
        setVar(cParams[0], cParams[1], getVar(cParams[0], cParams[1]) - 1,pushBit) #Var--
    elif c == 0x16:
        push(pop() & pop(), pushBit)#bitAnd
    elif c == 0x17:
        push(pop() | pop(), pushBit)#bitOr
    elif c == 0x18:
        push(pop() ^ 0xFFFFFFFF, pushBit)#bitNot
    elif c == 0x19:
        push(pop() ^ pop(), pushBit)#bitXor
    elif c == 0x1A:
        shiftBy = pop() #leftShift
        push(pop() << shiftBy, pushBit)
    elif c == 0x1B:
        shiftBy = pop()
        push(pop() >> shiftBy, pushBit)#rightShift
    elif c == 0x1C:
        setVar(cParams[0], cParams[1], pop(),pushBit) #setVar
    elif c == 0x1D:
        setVar(cParams[0], cParams[1], getVar(cParams[0], cParams[1]) + pop(),pushBit) #Var +=
    elif c == 0x1E:
        setVar(cParams[0], cParams[1], getVar(cParams[0], cParams[1]) - pop(),pushBit) #Var -=
    elif c == 0x1F:
        setVar(cParams[0], cParams[1], getVar(cParams[0], cParams[1]) * pop(),pushBit) #Var *=
    elif c == 0x20:
        setVar(cParams[0], cParams[1], getVar(cParams[0], cParams[1]) / pop(),pushBit) #Var /=
    elif c == 0x21:
        setVar(cParams[0], cParams[1], getVar(cParams[0], cParams[1]) % pop(),pushBit) #Var %=
    elif c == 0x22:
        setVar(cParams[0], cParams[1], getVar(cParams[0], cParams[1]) & pop(),pushBit) #Var &=
    elif c == 0x23:
        setVar(cParams[0], cParams[1], getVar(cParams[0], cParams[1]) | pop(),pushBit) #Var |=
    elif c == 0x24:
        setVar(cParams[0], cParams[1], getVar(cParams[0], cParams[1]) ^ pop(),pushBit) #Var ^=
    elif c == 0x25:
        push(int(pop() == pop()), pushBit) #equals
    elif c == 0x26:
        push(int(pop() != pop()), pushBit) #not equals
    elif c == 0x27:
        compareTo = pop()
        push(int(pop() < compareTo), pushBit) #less than
    elif c == 0x28:
        compareTo = pop()
        push(int(pop() <= compareTo), pushBit) #less than or equal
    elif c == 0x29:
        compareTo = pop()
        push(int(pop() > compareTo), pushBit) #greater than
    elif c == 0x2A:
        compareTo = pop()
        push(int(pop() >= compareTo), pushBit) #greater than or equal to
    elif c == 0x2B:
        push(0 if pop() != 0 else 1, pushBit)#logic not
    elif c == 0x2C:
        formatString = strings[pop()]
        formatValues = []
        for i in range(cParams[0]-1):
            formatValues.insert(0, pop())
        printf(formatString, formatValues)
    elif c == 0x2D:
        args = []
        for i in range(cParams[0]):
            args.insert(0, pop())
        syscall(cParams[1], args)
    elif c == 0x2E:
        exceptionRegister = cParams[0]
    elif c in [0x2F, 0x30, 0x31]:
        isJump = True
        jumpPos = pop()
        #paramList = [pop() for i in range(cParams[0])]
        hitException = False
        if c == 0x2F:
            gottenScript = mscFile.getScriptAtLocation(jumpPos)
            if gottenScript == None or gottenScript.getCommand(jumpPos).command != 0x2:
                print("WARNING: at %X invalid function call, jumping to exception register (%X)" % (evalPos, exceptionRegister))
                evalPos = exceptionRegister
                hitException = True
                isJump = True

        if not hitException:
            isJump = True
            linkRegister = evalPos + len(command)
            evalPos = jumpPos
    elif c == 0x32:
        v = pop()
        push(v)   #push, the essentially pushes the last return value
        push(v)
        push(v,pushBit)
    elif c == 0x33:
        push(pop(), pushBit)
    elif c == 0x34:
        if pop() == 0:
            isJump = True
            evalPos = cParams[0]
    elif c == 0x35:
        if pop() != 0:
            isJump = True
            evalPos = cParams
    elif c == 0x38:
        convertToFloat = lambda i: floatToInt(float(i))
        stack[stackPos - (1 + cParams[0])] = convertToFloat(stack[stackPos - (1 + cParams[0])]) # intToFloat
    elif c == 0x39:
        convertToInt = lambda f: int(intToFloat(f))
        stack[stackPos - (1 + cParams[0])] = convertToInt(stack[stackPos - (1 + cParams[0])]) # floatToInt
    elif c == 0x3A:
        push(intToFloat(pop()) + intToFloat(pop()), pushBit)
    elif c == 0x3B:
        v = intToFloat(pop())
        push(intToFloat(pop()) - v, pushBit)
    elif c == 0x3C:
        push(intToFloat(pop()) * intToFloat(pop()), pushBit)
    elif c == 0x3D:
        v = intToFloat(pop())
        push(intToFloat(pop()) / v, pushBit)
    elif c == 0x3E:
        push(-intToFloat(pop()), pushBit)
    elif c == 0x3F:
        setVar(cParams[0], cParams[1], floatToInt(intToFloat(getVar(cParams[0], cParams[1])) + 1),pushBit) #float Var++
    elif c == 0x40:
        setVar(cParams[0], cParams[1], floatToInt(intToFloat(getVar(cParams[0], cParams[1])) - 1),pushBit) #float Var--
    elif c == 0x41:
        setVar(cParams[0], cParams[1], pop(), pushBit) #setFloatVar
    elif c == 0x42:
        setVar(cParams[0], cParams[1], floatToInt(intToFloat(getVar(cParams[0], cParams[1])) + intToFloat(pop())),pushBit) #float Var+=
    elif c == 0x43:
        setVar(cParams[0], cParams[1], floatToInt(intToFloat(getVar(cParams[0], cParams[1])) - intToFloat(pop())),pushBit) #float Var-=
    elif c == 0x44:
        setVar(cParams[0], cParams[1], floatToInt(intToFloat(getVar(cParams[0], cParams[1])) * intToFloat(pop())),pushBit) #float Var+=
    elif c == 0x45:
        setVar(cParams[0], cParams[1], floatToInt(intToFloat(getVar(cParams[0], cParams[1])) / intToFloat(pop())),pushBit) #float Var-=
    elif c == 0x46:
        compTo = intToFloat(pop())
        push(int(intToFloat(pop()) > compTo), pushBit)
    elif c == 0x47:
        compTo = intToFloat(pop())
        push(int(intToFloat(pop()) <= compTo), pushBit)
    elif c == 0x48:
        compTo = intToFloat(pop())
        push(int(intToFloat(pop()) < compTo), pushBit)
    elif c == 0x49:
        push(int(intToFloat(pop()) != intToFloat(pop())), pushBit) #float equals
    elif c == 0x4A:
        push(int(intToFloat(pop()) == intToFloat(pop())), pushBit) #float equals
    elif c == 0x4B:
        compTo = intToFloat(pop())
        push(int(intToFloat(pop()) >= compTo), pushBit)
    elif c == 0x4D:
        executing = False
        return

    if not isJump:
        evalPos += len(command)

def evalMscFile(mscFileObject):
    global mscFile,mscFileBytes,stack,functionStack,stackPos,localVarPos,evalPos,exceptionRegister,globalVars,executing,strings,linkRegister
    mscFile = mscFileObject
    strings = mscFile.strings
    evalPos = mscFile.entryPoint
    startScript = mscFile.getScriptAtLocation(mscFile.entryPoint)
    if startScript != None:
        executing = True
        while executing:
            currentExecutingScript = mscFile.getScriptAtLocation(evalPos)
            if currentExecutingScript != None:
                evalCommand(currentExecutingScript.getCommand(evalPos))
                if executing:
                    executing = (evalPos != None)
            else:
                executing = False

def evalFile(filepath):
    with open(filepath, 'rb') as f:
        mscFile = MscFile().readFromFile(f)
    evalMscFile(mscFile)

def evalText():
    mscFile = MscFile()
    strs = []
    scriptString = ""
    print("+----------------------------------------------+")
    print("|  Text interpreter - Type in your script.     |")
    print("|  Script input will stop after you type 'end' |")
    print("+----------------------------------------------+")
    nextLine = input("> ")
    while nextLine.strip().lower() != "end":
        scriptString += nextLine + "\n"
        nextLine = input("> ")
    print("------------------------------------------------")
    scr = MscScript()
    cmds = parseCommands(scriptString, mscStrings=strs)
    cmdsSize = 0
    for c in cmds:
        cmdsSize += len(c)
    scr.bounds = [0x10, 0x10+cmdsSize]
    scr.cmds = cmds
    scr.setStart(0x10)
    scr.offset(0x10)
    mscFile.entryPoint = 0x10
    mscFile.strings = strs
    mscFile.scripts.append(scr)
    evalMscFile(mscFile)

def main():
    global mscFile,mscFileBytes,stack,functionStack,stackPos,localVarPos,evalPos,exceptionRegister,globalVars,executing,strings,linkRegister,sharedVars
    mscFile = None
    mscFileBytes = None
    stack = [None] * 0x80
    functionStack = []
    stackPos = 0
    localVarPos = 0
    evalPos = 0
    exceptionRegister = 0
    linkRegister = None
    globalVars = [None] * 0x8A #Note a lot of this is actually unused but is simulated for exploitation
    executing = False
    strings = []
    sharedVars = {}
    if len(argv) > 1:
        evalFile(argv[1])
    else:
        evalText() #Go to text evaluation

if __name__ == '__main__':
    main()
