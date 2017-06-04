# pymsc
Python library for working with MSC (Smash 4 Moveset Code)

Requires a somewhat recent version of python 3. (>3.5 should be fine)

## Basics
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

## Example
Included is example.py, which is a demo showing off how to disassemble an MSCSB.

## Credits
Thanks to Sammi Husky and Dantarion for doing a huge amount of preliminary research for this.
