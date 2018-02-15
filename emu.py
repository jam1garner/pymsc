#**************************************************************************#
# This file is part of pymsc which is released under MIT License. See file #
# LICENSE or go to https://github.com/jam1garner/pymsc/blob/master/LICENSE #
# for full license details.                                                #
#**************************************************************************#
import struct
from sys import argv
from msc import *
from param import *
from time import sleep
from random import randint,random
from os.path import isfile
from argparse import ArgumentParser
from math import sqrt, cos, sin, atan


class FunctionInfo:
    def __init__(self, thisLocalVarPos, returnAddress, stackPos):
        self.localVarPos = thisLocalVarPos
        self.returnAddress = returnAddress
        self.stackPos = stackPos

    def restore(self):
        global evalPos, localVarPos
        localVarPos = self.localVarPos
        evalPos = returnAddress

#Simulate an MSC syscall given the information from 
def syscall(syscallNum, args, pushBit):
    global sharedVars,evalPos,stack,y_unit
    #Random int in range
    if syscallNum == 0x9:
        push(randint(args[0], args[1]-1), pushBit)
    
    #Variable access
    elif syscallNum == 0x16:
        operation = args[0]
        if operation == 0x6:
            if not args[1] in sharedVars:
                print("ERROR: Variable 0x%08X doesn't not exist (Accessed at %X)" % (args[1],evalPos))
                quit()
            else:
                push(sharedVars[args[1]], pushBit)
        elif operation == 0x7:
            sharedVars[args[2]] = args[1]
        elif operation == 0x10:
            if not args[1] in sharedVars:
                print("ERROR: Variable 0x%08X doesn't not exist (Accessed at %X)" % (args[1],evalPos))
                quit()
            else:
                push(0 if sharedVars[args[1]] == 0 else 1, pushBit)
        elif operation == 0x2710:
            sharedVars[args[1]] = 0
        elif operation == 0x2711:
            sharedVars[args[1]] = 1

    elif syscallNum == 0xA:
        operation = args[0]
        if operation == 0: #sqrt
            push(sqrt(intToFloat(args[1])),pushBit)
        elif operation == 1: #angle
            push(atan(intToFloat(args[1]) / intToFloat(args)),pushbit)
        elif operation == 2:
            push(intToFloat(args[1])**args[2],pushBit)
        elif operation == 3:
            push(sqrt((intToFloat(args[1])**2)+(intToFloat(args[2])**2)+(intToFloat(args[3])**2)),pushBit)
        elif operation == 4:
            push(cos(intToFloat(args[1])),pushBit)
        elif operation == 5:
            push(sin(intToFloat(args[1])),pushBit)
        elif operation == 6:
            push(random(), pushBit)
        elif operation == 7:
            push(abs(atan2(intToFloat(args[1]), intToFloat(args[2])) - atan2(intToFloat(args[3]), intToFloat(args[4]))),pushBit)
        elif operation == 8:
            push(y_unit, pushBit)
        elif operation == 0xA:
            mag = sqrt((intToFloat(args[1])**2)+(intToFloat(args[2])**2))
            x = intToFloat(args[1]) / mag
            y_unit = intToFloat(args[2]) / mag
            push(,pushBit)

    #Variable access
    elif syscallNum == 0x17:
        operation = args[0]
        if operation == 0x0:
            if not args[1] in sharedVars:
                print("ERROR: Variable 0x%08X doesn't not exist (Accessed at %X)" % (args[1],evalPos))
                quit()
            else:
                push(sharedVars[args[1]], pushBit)

    #Debug stack dump
    elif syscallNum == 0xF0:
        stackString = "DEBUG: ["
        for i in range(len(stack)):
            if stack[i] != None:
                stackString += ('*' if i == stackPos else '') + hex(stack[i]) + (', ' if i != len(stack) - 1 else '')
        if stackString != "[":
            stackString = stackString[:-2]
        print("Stack [Position = %i] - %s" % (stackPos, str([intToFloat(j) if j else 0 for j in stack])))

    #Debug var print
    elif syscallNum == 0xF1:
        if len(args) == 0:
            l = tuple(["0x%08X : 0x%08X, " % (i,j) for i,j in sharedVars.items()])
            print('DEBUG: {' + (('%s' * len(l)) % l).rstrip(', ') + '}')
        else:
            if args[0] in sharedVars:
                print("DEBUG: 0x%08X = 0x%08X" % (args[0], sharedVars[args[0]]))

    else:
        print("ERROR: Unsupported syscall 0x%X at location %X" % (syscallNum,evalPos))
        quit()

#push a value onto the stack given that the push bit is enabled
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
    specifierLocs = [i for i,j in enumerate(printString) if j == '%' and i < len(printString) and printString[i+1] in ['x', 'X', 'i', 'f', '0']]
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
        stackPos -= cParams[0]
        functionStack.append(FunctionInfo(localVarPos, linkRegister, stackPos))
        localVarPos = stackPos
        stackPos += cParams[1]
    elif c in [0x3, 0x6, 0x7, 0x8, 0x9]: #end or return    
        if len(functionStack) == 0:
            executing = False
            return
        fInfo = functionStack.pop()
        if fInfo.returnAddress == None:
            executing = False
            return
        if c in [0x6, 0x8]: #return a value
            v = pop()
            stackPos = fInfo.stackPos
            push(v)
        localVarPos = fInfo.localVarPos
        evalPos = fInfo.returnAddress
        isJump = True
    elif c in [0x4, 0x5, 0x36]:
        isJump = True
        evalPos = cParams[0]
    elif c == 0xA or c == 0xD:
        push(cParams[0], pushBit)
    elif c == 0xB:
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
        formatValues = []
        for i in range(cParams[0]-1):
            formatValues.insert(0, pop())
        formatString = strings[pop()]
        printf(formatString, formatValues)
    elif c == 0x2D:
        args = []
        for i in range(cParams[0]):
            args.insert(0, pop())
        syscall(cParams[1], args, pushBit)
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
            evalPos = cParams[0]
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
        push(int(intToFloat(pop()) == compTo), pushBit)
    elif c == 0x47:
        compTo = intToFloat(pop())
        push(int(intToFloat(pop()) != compTo), pushBit)
    elif c == 0x48:
        compTo = intToFloat(pop())
        push(int(intToFloat(pop()) < compTo), pushBit)
    elif c == 0x49:
        push(int(intToFloat(pop()) <= intToFloat(pop())), pushBit) #float equals
    elif c == 0x4A:
        push(int(intToFloat(pop()) > intToFloat(pop())), pushBit) #float equals
    elif c == 0x4B:
        compTo = intToFloat(pop())
        push(int(intToFloat(pop()) >= compTo), pushBit)
    elif c == 0x4D:
        executing = False
        return

    if not isJump:
        evalPos += len(command)

def evalMscFile(mscFileObject):
    global mscFile,mscFileBytes,stack,functionStack,stackPos,localVarPos,evalPos,exceptionRegister,globalVars,executing,strings,linkRegister,mainLoopFunc
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
    global stack, stackPos
    mscFile = MscFile()
    strs = []
    scriptString = ""
    print("+----------------------------------------------+")
    print("|  Text interpreter - Type in your script.     |")
    print("|  Script input will stop after you type 'end' |")
    print("+----------------------------------------------+")
    nextLine = input()
    while nextLine.strip().lower() != "end":
        scriptString += nextLine + "\n"
        nextLine = input()
    scriptString += nextLine
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
    if scr[0].command == 0x2 and scr[0].parameters[0] > 0:
        stackPos = scr[0].parameters[0]
        print('Input %i parameter(s)' % scr[0].parameters[0])
        for i in range(scr[0].parameters[0]):
            p = input('Input parameter %i: ' % i).strip()
            if p[-1] == 'f':
                stack[i] = int(floatToInt(float(p[0 : len(p)-1])))
            else:
                stack[i] = int(p, 0)
    evalMscFile(mscFile)

def load_fighter_param_common(filepath):
    global sharedVars
    p = openParam(filepath)
    for i in range(len(p)):
        val = p[i]
        if isinstance(val, f32):
            val = floatToInt(val)
        elif not True in [isinstance(val, t) for t in [u8, s8, u16, s16, u32, s32]]:
            continue
        sharedVars[0x12000000 + i] = int(val)
        sharedVars[0x02000000 + i] = int(val)

def load_fighter_param(filepath, entry):
    global sharedVars
    p = openParam(filepath)[0].entry(entry)
    for i in range(len(p)):
        val = p[i]
        if isinstance(val, f32):
            val = floatToInt(val)
        elif not True in [isinstance(val, t) for t in [u8, s8, u16, s16, u32, s32]]:
            continue
        sharedVars[0x13000000 + i] = int(val)
        sharedVars[0x03000000 + i] = int(val)

def main():
    global mscFile,mscFileBytes,stack,functionStack,stackPos,localVarPos,evalPos,exceptionRegister,globalVars,executing,strings,linkRegister,sharedVars,mainLoopFunc
    mscFile = None
    mscFileBytes = None
    mainLoopFunc = None
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
    #Parse arguments
    parse = ArgumentParser(description="Emulate MSC bytecode")
    parse.add_argument("--fighter_param_common", action="store", dest="fighter_param_common", help="Path of fighter_param_common to load")
    parse.add_argument("--fighter_param", action="store", dest="fighter_param", help="Path of fighter_param to load")
    parse.add_argument("--character", action="store", dest="character", help="Name of character to load from fighter_param")
    parse.add_argument("--character_list", action="store_true", dest="charLS", help="List character names")
    parse.add_argument("mscFile", nargs='?', type=str, help="MSC File to emulate")
    args = parse.parse_args()


    charIds = {'miienemyf': 62, 'miienemys': 63, 'miienemyg': 64, 'littlemacg': 60, 'mariod': 36, 'pikmin': 26, 'sheik': 17, 'roy': 54, 'yoshi': 7, 'duckhunt': 45, 'koopajr': 46, 'pit': 24, 'metaknight': 23, 'cloud': 55, 'miifighter': 0, 'miiswordsman': 1, 'miigunner': 2, 'wiifit': 40, 'pacman': 49, 'gamewatch': 19, 'peach': 14, 'robot': 31, 'rockman': 50, 'fox': 9, 'zelda': 16, 'bayonetta': 56, 'purin': 35, 'donkey': 4, 'shulk': 47, 'ryu': 52, 'toonlink': 32, 'sonic': 34, 'lucariom': 61, 'lizardon': 33, 'littlemac': 41, 'kirby': 8, 'pikachu': 10, 'murabito': 42, 'ness': 13, 'palutena': 43, 'diddy': 27, 'mario': 3, 'wario': 22, 'link': 5, 'ike': 29, 'rosetta': 39, 'samus': 6, 'falcon': 12, 'mewtwo': 51, 'lucas': 53, 'ganon': 20, 'koopag': 58, 'gekkouga': 48, 'dedede': 28, 'pitb': 38, 'lucina': 37, 'warioman': 59, 'marth': 18, 'szerosuit': 25, 'koopa': 15, 'kamui': 57, 'lucario': 30, 'luigi': 11, 'reflet': 44, 'falco': 21}

    if args.charLS:
        print(list(charIds.keys()))
        quit()

    if args.fighter_param != None and isfile(args.fighter_param) and args.character in charIds:
        print("loading fighter_param")
        load_fighter_param(args.fighter_param, charIds[args.character])

    if args.fighter_param_common != None and isfile(args.fighter_param_common):
        load_fighter_param_common(args.fighter_param_common)

    if args.mscFile == None:
        evalText()
    else:
        evalFile(args.mscFile)

if __name__ == '__main__':
    main()
