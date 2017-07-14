# pymsc
Python library for working with MSC (Smash 4 Moveset Code)

Requires a somewhat recent version of python 3. (>3.5 should be fine)

## Using included assembler and disassembler
**Assembling:**
* Have a Scripts file (look at a disassembled mscsb for example)
* In the same folder run `python asm.py` or in whatever folder `python asm.py [pathOfScriptFile]`
* output will be to test.py

**Disassembling:**

* `python disasm.py [pathOfMscsb]` and it will output in the `output` folder
* The disassembler will set up everything needed to relink all the scripts by analyzing every script in order to locate script offsets as well as making if/else/jump/etc. use labels
* Disassembly should leave everything setup for immediate reassembly
* Any possible script offsets not found by the disassembler analysis will be printed out and may require manual renaming

**Scripts file:**

A Scripts file is a file that tells the assembler how to link the scripts. The format is rather simple:
* Use # for comments
* Each non-blank, non-comment line is a script
* Add a `>` before a script name to indicate it is a global file, global files are where you define strings and global aliases
* Add a ':' before the script you want to be the entrypoint, if none is picked it defaults to script_0
* In your scripts you can reference the offsets of other scripts using script_# where # is the script number, script number is determined by the index of the scripts in the Scripts file not including globals, blank lines or comments however most of the printed offsets do not need updating so only do this if something breaks!

**Example Script file:**

```python
#comment (this is ignored)

setupVars.txt #this is script_0
>strings.txt  #this is a globals file
wavedash.txt  #this is script_1

:start.txt    #this is script_2 and the entrypoint
```

## Library Basics
Importing library:

```python
from msc import *
```

Reading in an MSC File:

```python
with open(filename, 'rb') as f:
  mscData = MscFile()
  mscData.readFromFile(f)
```

Including debug strings in string output of commands:

```python
mscData.addDebugStrings()
```

Iterating through file: (+ getting command name from command number)

```python
for script in mscData:
  for line in script:
    print("Command Name = "+COMMAND_NAMES[line.command])
```

Looking at command parameters:

```python
test_stack = []
if line.command == 0xA: #if the command is pushInt
  test_stack.append(line.parameters[0])
```

## Credits
Thanks to Sammi Husky and Dantarion for doing a huge amount of preliminary research for this.
