#**************************************************************************#
# This file is part of pymsc which is released under MIT License. See file #
# LICENSE or go to https://github.com/jam1garner/pymsc/blob/master/LICENSE #
# for full license details.                                                #
#**************************************************************************#
from msc import *
import sys, os, time, os.path, timeit
from argparse import ArgumentParser

scriptNames = {}
scriptOffsets = []
scriptCalls = {}
renames = {}

gvIsOffset = [False for i in range(64)]
for gv in [7] + list(range(11,17)) + [21,22,23,25,26,27,28,30,34,35,36,37,39,40,41,42,43,44,56,57,58,59,60,61]:
    gvIsOffset[gv] = True

def updateScriptReference(popped, index, scriptName):
    global scriptCalledVars, mscFile, acmdNames, charAcmdNames
    try:
        #if the Xth command popped off the stack is pushing a constant
        if popped[index].command in [0xA, 0xD]:
            #if the index pushed is a valid script offset
            if popped[index].parameters[0] in scriptOffsets:
                newScriptName = scriptNames[popped[index].parameters[0]]
                popped[index].parameters[0] = newScriptName
                if ((newScriptName == 'script_22' and charAcmdNames) or (newScriptName == 'script_24' and not charAcmdNames)) and popped[3].command in [0xA, 0xD]:
                    acmdIndex = popped[3].parameters[0]
                    if acmdIndex < len(acmdNames) and acmdNames[acmdIndex][:2] != '0x':
                        renames[scriptName] = acmdNames[acmdIndex]
                elif ((newScriptName == 'script_23' and charAcmdNames) or (newScriptName == 'script_25' and not charAcmdNames)) and popped[1].command in [0xA, 0xD]:
                    acmdIndex = popped[1].parameters[0]
                    if acmdIndex < len(acmdNames) and acmdNames[acmdIndex][:2] != '0x':
                            renames[scriptName] = acmdNames[acmdIndex]
                if args.pathgen:
                    sn = mscFile.getScriptAtLocation(popped[index].commandPosition).bounds[0]
                    if not sn in scriptCalls:
                        scriptCalls[sn] = []
                    scriptCalls[sn].append("References %s" % popped[index].parameters[0])

        #if the Xth command popped off the stack is a variable
        if popped[index].command == 0xB:
            #if the variable is local
            if popped[index].parameters[0] == 0:
                if not scriptName in scriptCalledVars.keys():
                    scriptCalledVars[scriptName] = []
                if not popped[index].parameters[1] in scriptCalledVars[scriptName]:
                    scriptCalledVars[scriptName].append(popped[index].parameters[1])
    except:
        print(popped)
        print(index)
        print(scriptName)
        raise

#script - mscScript object
#startIndex - index in the script to start at, used for recursively evaluating all paths
#stack - the current stack, blank at start of script and passed through recursively when evaluating paths
#endPosition - when to stop searching (i.e. when the stack is empty and paths recombine)
#depth - used to determine whether or not a path can be abandoned
def emuScript(script, startIndex, stack, passCount, endPosition=None, depth=0):
    global clearedPaths,scriptCalledVars
    scriptName = scriptNames[script.bounds[0]]
    if endPosition == None:
        clearedPaths = []
    try:
        i = startIndex
        while i < len(script):
            if scriptNames[script.bounds[0]] == 'script_X':
                print('\t' * depth + str(stack))
                print('\t' * depth + str(script[i]))
            if endPosition != None and i >= endPosition and len(stack) == 0:
                return False
            #Get the number of pops based on the command and it's parameters
            popCount = COMMAND_STACKPOPS[script[i].command](script[i].parameters)
            popped = []
            try:
                for _ in range(popCount):
                    #Pop the needed commands into the popped list in case one of them is needed
                    popped.append(stack.pop())
            except:
                print('Analysis command %s pop failed in script %X command at position %X' % (COMMAND_NAMES[script[i].command], script.bounds[0], script[i].commandPosition))

            #First pass
            if passCount == 0:
                #if the command is a function call
                if script[i].command in [0x2f, 0x30, 0x31]:
                    updateScriptReference(popped, 0, scriptName)
                #if the command in a sys call
                if script[i].command == 0x2d:
                    if script[i].parameters[1] == 0:
                        updateScriptReference(popped, 0, scriptName)
                    elif script[i].parameters[1] == 3:
                        updateScriptReference(popped, 0, scriptName)
                    elif script[i].parameters[1] == 0x29:
                        updateScriptReference(popped, 1, scriptName)
                    elif script[i].parameters[1] == 0x29:
                        updateScriptReference(popped, 2, scriptName)
                #If gv16 flag is enabled and it is setting GlobalVar16
                if script[i].command == 0x1C and script[i].parameters[0] == 0x1 and gvIsOffset[script[i].parameters[1]]:
                    updateScriptReference(popped, 0, scriptName)
            elif passCount >= 1:
                if script[i].command in [0x1C, 0x41] and scriptName in scriptCalledVars.keys():
                    if script[i].parameters[0] == 0 and script[i].parameters[1] in scriptCalledVars[scriptName]:
                        updateScriptReference(popped, 0, scriptName)
                if script[i].command in [0x2f, 0x30, 0x31]:
                    if popped[0].command in [0xA, 0xD]:
                        jumpScriptName = None
                        if isinstance(popped[0].parameters[0], int) and popped[0].parameters[0] in scriptNames.keys():
                            jumpScriptName = scriptNames[popped[0].parameters[0]]
                        elif isinstance(popped[0].parameters[0], str):
                            jumpScriptName = popped[0].parameters[0]

                        if jumpScriptName in scriptCalledVars.keys():
                            for localVarNum in scriptCalledVars[jumpScriptName]:
                                if localVarNum+1 < len(popped):
                                    updateScriptReference(popped, localVarNum + 1, scriptName)

            #if the command is push, just readd the command before it
            if script[i].command == 0x32:
                stack.append(script[i-1])
            #if the pushBit is set, push the command onto the stack
            if script[i].pushBit:
                stack.append(script[i])
            #if the command is if or ifNot then evaluate both possible paths
            if script[i].command in [0x34, 0x35]:
                jumpIndex = script.getIndexOfInstruction(script[i].parameters[0])
                if jumpIndex == None:
                    print (script[i])
                endOfBlock = jumpIndex
                if script[jumpIndex - 1].command == 0x36:
                    endOfBlock = script.getIndexOfInstruction(script[jumpIndex - 1].parameters[0])
                    finished = emuScript(script, jumpIndex, stack, passCount, endOfBlock, depth+1)
                elif len(stack) > 0:
                    finished = emuScript(script, jumpIndex, stack, passCount, jumpIndex, depth+1)
                if not script[i].commandPosition in clearedPaths:
                    clearedPaths.append(script[i].commandPosition)
                else:
                    if scriptNames[script.bounds[0]] == 'script_X':
                        print(depth * '\t' + 'skipped path')
                    if depth != 0:
                        pass#return
            #if it hits a jump or else command, just jump it
            if script[i].command in [4, 5, 0x36]:
                newIndex = script.getIndexOfInstruction(script[i].parameters[0])
                if newIndex == None:
                    i += 1
                else:
                    i = newIndex
            else:
                #if it isn't a jump, move on to the next command
                i += 1
    except:
        print('Analysis error occured in script %s at %X' % (scriptNames[script.bounds[0]], script.bounds[0]))
        raise
    return True

def addCharacterComments(script, actionLines):
    for i in range(len(script)):
        try:
            if script[i].command == 0xa: # if pushInt
                parameter = script[i].parameters[0]
                isBitOrBasicMask = 0xF0000000
                isFloatMask = 0xF000000
                extractMSBMask = 0xFF000000
                extractDecimalIDMask = 0xFFFFFF
                if isinstance(parameter, int) and (parameter & isBitOrBasicMask) != 0x0: # if basic or bit
                    mostSignificantBytes = (parameter & extractMSBMask) >> (4 * 6)
                    decimalID = parameter & extractDecimalIDMask
                    if mostSignificantBytes == 0x10:
                        script[i].debugString = "LA-Basic %i" % (decimalID)
                    elif mostSignificantBytes == 0x11:
                        script[i].debugString = "RA-Basic %i" % (decimalID)
                    elif mostSignificantBytes == 0x12:
                        script[i].debugString = "fighter_param_common-Basic %i" % (decimalID)
                    elif mostSignificantBytes == 0x13:
                        script[i].debugString = "fighter_param-Basic %i" % (decimalID)
                    elif mostSignificantBytes == 0x20:
                        script[i].debugString = "LA-Bit %i" % (decimalID)
                    elif mostSignificantBytes == 0x21:
                        script[i].debugString = "RA-Bit %i" % (decimalID)
                    elif mostSignificantBytes == 0x1e:
                        script[i].debugString = "Action Status-Type1? %i" % (decimalID)
                    elif mostSignificantBytes == 0x1f:
                        script[i].debugString = "Action Status-Type2? %i" % (decimalID)
                elif isinstance(parameter, int) and (parameter & isFloatMask) != 0: # if float
                    mostSignificantBytes = (parameter & extractMSBMask) >> (4 * 5)
                    extractDecimalIDMask = 0xFFFFF
                    decimalID = parameter & extractDecimalIDMask
                    if mostSignificantBytes == 0x10:
                        script[i].debugString = "LA-Float %i" % (decimalID)
                    elif mostSignificantBytes == 0x11:
                        script[i].debugString = "RA-Float %i" % (decimalID)
                    elif mostSignificantBytes == 0x20:
                        script[i].debugString = "fighter_param_common-Float %i" % (decimalID)
                    elif mostSignificantBytes == 0x30:
                        script[i].debugString = "fighter_param-Float %i" % (decimalID)
                elif isinstance(parameter, str) and parameter == "script_16": # action
                    actionID = script[i-2].parameters[0]
                    if not actionLines[actionID].startswith("unk"):
                        script[i].debugString = "call action %s" % (actionLines[actionID][:-1])
                    else:
                        script[i].debugString = "call action 0x%x" % (actionID)
                elif isinstance(parameter, str) and parameter == "script_22": # animation
                    animationID = script[i-3].parameters[0]
                    script[i].debugString = "call animation 0x%x" % (animationID)
            elif script[i].command == 0x16: # if bitAnd
                if script[i-1].command == 0xa and script[i-2].command == 0xb:
                    if script[i-2].parameters[0] == 1: # must be global
                        ANDMask = script[i-1].parameters[0]
                        VarID = script[i-2].parameters[1]
                        if VarID == 0x26:
                            if ANDMask == 0x10:
                                script[i].debugString = "if X/Y is pressed"
                            elif ANDMask == 0x1:
                                script[i].debugString = "if A is pressed"
                            elif ANDMask == 0x4:
                                script[i].debugString = "if B is pressed"
                            elif ANDMask == 0x40:
                                script[i].debugString = "if L/R is pressed"
                        elif VarID == 0x18:
                            if ANDMask == 0x100000:
                                script[i].debugString = "if stick held up"
                            elif ANDMask == 0x20000000:
                                script[i].debugString = "if Z is pressed"
                        elif VarID == 0x1f:
                            if ANDMask == 0x10000:
                                script[i].debugString = "if stick held down"
                            elif ANDMask == 0x4000:
                                script[i].debugString = "if stick held backward"
                            elif ANDMask == 0x8000:
                                script[i].debugString = "if stick held forward"
                            elif ANDMask == 0x2:
                                script[i].debugString = "if D-Pad Up"
                            elif ANDMask == 0x4:
                                script[i].debugString = "if D-Pad Down"
                            elif ANDMask == 0x1:
                                script[i].debugString = "if D-Pad Left/Right"
            elif script[i].command == 0x25: # if equals
                if script[i-1].command == 0xa and script[i-2].command == 0xb:
                    if script[i-2].parameters == [0x1,0x12]: # push globalVar12
                        locationType = script[i-1].parameters[0]
                        if locationType == 0x0:
                            script[i].debugString = "if is grounded"
                        elif locationType == 0x1:
                            script[i].debugString = "if is on ledge"
                        elif locationType == 0x2:
                            script[i].debugString = "if is aerial"
            elif script[i].command == 0x2d: # if sys
                if script[i].parameters == [0x1, 0x12]:
                    if script[i-1].command == 0xa:
                        if script[i-1].parameters[0] == 0x2712:
                            script[i].debugString = "if animation ended"
                elif script[i].parameters == [0x1, 0x13]:
                    if script[i-1].command == 0xa:
                        if script[i-1].parameters[0] == 0x1:
                            script[i].debugString = "push animation frame"
                elif script[i].parameters == [0x1, 0x25]:
                    if script[i-1].command == 0xa:
                        if script[i-1].parameters[0] == 0x0:
                            script[i].debugString = "push current percentage"
                elif script[i].parameters == [0x1, 0x3e]:
                    if script[i-1].command == 0xa:
                        if script[i-1].parameters[0] == 0x11:
                            script[i].debugString = "push held item ID"

        except:
            script[i].debugString = None

def renameScripts(mscFile, renameDict):
    for script in mscFile:
        for command in script:
            if command.command in [0xA, 0xD]:
                if command.parameters[0] in renameDict:
                    command.parameters[0] = renameDict[command.parameters[0]]
        if script.name in renameDict:
            script.name = renameDict[script.name]

def main():
    global clearedPaths,scriptCalledVars,mscFile,args,acmdNames,charAcmdNames

    parse = ArgumentParser(description="Emulate MSC bytecode")
    parse.add_argument("--char-std", action="store_true", dest="assumeCharStd", help="Add comments assuming it uses character standard lib")
    parse.add_argument("--commentScriptNum",action="store_true", dest="commentScriptNum", help="Comment the script number in any renamed script")
    parse.add_argument("--123", "--sequential-labels", action="store_true", dest="sequentialLabels", help="Labels in style loc_1, loc_2, etc. instead of based on byte position in script")
    parse.add_argument("--pathgen", action="store_true", dest="pathgen", help="Puts every function call in a list by script stored in Paths")
    parse.add_argument("--suffix", dest="suffix", help="Add suffix to script names and references")
    parse.add_argument("--acmdNames", dest="mlistFile", help="Rename scripts based on the ACMD subaction it runs")
    parse.add_argument("--article", action="store_true", dest="isArticle", help="Use with --acmdNames for when you want to label article scripts")
    parse.add_argument("--extension", action="store", dest="extension", help="Change the extension used for scripts (default: .txt)")
    parse.add_argument("mscFile", type=str, help="MSC File to disassemble")
    parse.add_argument("outputDir", nargs='?', type=str, help="Folder to put output")
    args = parse.parse_args()

    fname = args.mscFile

    outputDir = os.path.basename(os.path.splitext(fname)[0])+"/" if not args.outputDir else args.outputDir if args.outputDir[-1] in ["\\","/"] else args.outputDir + "/"
    suffix = "" if not args.suffix else args.suffix
    extension = "txt" if not args.extension else args.extension.replace('.', '')
    acmdNames = []
    if args.mlistFile:
        with open(args.mlistFile, 'r') as f:
            acmdNames = [i.replace('\n','') for i in f.readlines()]

    charAcmdNames = not args.isArticle

    mscFile = MscFile()

    if len(suffix) > 0:
        for script in mscFile:
            script.name += suffix

    if args.assumeCharStd:
        actionCSVRealPath = os.path.join(sys.path[0], "actions.csv")
        with open(actionCSVRealPath) as actionsFile:
            actionLines = actionsFile.readlines()

    with open(fname, 'rb') as f:
        mscFile.readFromFile(f)
        mscFile.addDebugStrings()

    if not os.path.isdir(outputDir):
        os.makedirs(outputDir, exist_ok=True)

    with open(outputDir+'Scripts', 'w') as f:
        print('>globals.txt', file=f)
        with open(outputDir+'globals.txt', 'w', encoding='utf-8') as globalFile:
            for string in mscFile.strings:
                print('.string '+string, file=globalFile)

        for i,script in enumerate(mscFile):
            if not script.bounds[0] in scriptOffsets:
                scriptNames[script.bounds[0]] = script.name
                scriptOffsets.append(script.bounds[0])

        scriptCalledVars = {}
        for script in mscFile:
            clearedPaths = []
            emuScript(script, 0, [], 0)

        for script in mscFile:
            clearedPaths = []
            emuScript(script, 0, [], 1)

        renameScripts(mscFile, renames)

        headerPrinted = False
        for i,script in enumerate(mscFile):
            clearedPaths = []
            emuScript(script, 0, [], 2)
            if args.assumeCharStd:
                addCharacterComments(script, actionLines)

            scriptPrinted = False
            for j,comm in enumerate(script):
                if comm.command in [0xA, 0xD] and comm.parameters[0] in scriptOffsets and comm.parameters[0] != 0x10:
                    if not headerPrinted:
                        print(' Potential missed script offsets ')
                        print('---------------------------------')
                        headerPrinted = True
                    if not scriptPrinted:
                        print('In script %i:' % i)
                        scriptPrinted = True
                    print('\t%i | %s | may be %s' % (j,str(comm),scriptNames[comm.parameters[0]]))
            print('%s%s.%s' % (':' if mscFile.entryPoint == script.bounds[0] else '',script.name,extension),file=f)

            jumpPositions = []
            for cmd in script:
                if cmd.command in [0x4, 0x5, 0x2e, 0x34, 0x35, 0x36]:
                    if not cmd.parameters[0] in jumpPositions:
                        jumpPositions.append(cmd.parameters[0])
                    if not args.sequentialLabels:
                        cmd.parameters[0] = 'loc_%X' % (cmd.parameters[0] - script.bounds[0])

            if args.sequentialLabels:
                jumpPositions.sort()
                for cmd in script:
                    if cmd.command in [0x4, 0x5, 0x2e, 0x34, 0x35, 0x36]:
                        cmd.parameters[0] = 'loc_%X' % (jumpPositions.index(cmd.parameters[0]) + 1)            

            with open(outputDir+'%s.%s' % (script.name,extension), 'w', encoding='utf-8') as scriptFile:
                for cmd in script:
                    if cmd.commandPosition in jumpPositions:
                        print('',file=scriptFile)
                        print('loc_%X:' % (jumpPositions.index(cmd.commandPosition) + 1 if args.sequentialLabels else cmd.commandPosition - script.bounds[0]), file=scriptFile)
                    print((' ' * 8 if len(jumpPositions) > 0 else '') + COMMAND_NAMES[cmd.command] + ('.' if cmd.pushBit else '') + ' '+cmd.strParams() + (' #"%s"' % cmd.debugString if cmd.debugString != None else ''), file=scriptFile)

        if args.pathgen:
            with open(outputDir+'Paths', 'w') as pathFile:
                t = list(scriptCalls.keys())
                t.sort()
                for scriptLoc in t:
                    print("%s:"%scriptNames[scriptLoc],file=pathFile)
                    for message in scriptCalls[scriptLoc]:
                        print(message,file=pathFile)
                    print("",file=pathFile)

if __name__ == '__main__':
    start = timeit.default_timer()
    main()
    end = timeit.default_timer()
    print('Execution completed in %f seconds' % (end - start))
