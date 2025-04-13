# `mnlscript.py`
Compiler and decompiler for the Mario & Luigi scripting language from and to Python.


## Installation
```bash
pip3 install mnlscript
```


## Usage
### *Bowser's Inside Story*
First, you'll need [`mnltools.py`](https://github.com/MnL-Modding/mnltools.py) in order to unpack and repack the ROM:
```bash
pip3 install mnltools
```
Then you can unpack and decompile the game:
```bash
mnl-nds-unpack bis.rom
mnlscript-bis-decompile
```
Afterwards, to compile and repack:
```bash
mnlscript-bis-compile [SCRIPTS TO COMPILE]
mnl-nds-pack -o bis.rom
```
`[SCRIPTS TO COMPILE]` should be a space-separated list of the scripts to compile (e.g. `scripts/fevent/009c.py scripts/fevent/021d.py`, or `scripts/fevent/{009c,021d}.py` if your shell supports it).
Although you can leave this blank to recompile all scripts, this is not recommended as it is slow and unnecessary.


### *Dream Team (Bros.)*
First, you'll need to extract the RomFS, for example through Azahar (or any Citra fork).
Unfortunately, Azahar doesn't support extracting the ExeFS, so you'll have to extract it separately, e.g. with [CTRTool](https://github.com/3DSGuy/Project_CTR/releases):
```bash
ctrtool --exefsdir=exefs dt.cci
```
You'll want to put these `exefs` and `romfs` folders side by side inside the Mods directory for your game (to locate this directory in Azahar, right-click on the game and press “Open > Mods Location”).
Take note of the name of the directory (the title ID), as you'll need to substitute it in the following commands.

Now, open the directory where you would like to work on your mod in a terminal.
If your system supports it, you should create a symbolic link to the game's Mods directory named `data`:
* **Windows (PowerShell, *may need to run as Administrator*):** `New-Item -ItemType SymbolicLink -Path .\data -Target $env:APPDATA\Azahar\load\mods\<TitleID>`
* **Linux:** `ln -s ~/.local/share/azahar-emu/load/mods/<TitleID> data`
* **macOS:** `ln -s "$HOME/Library/Application Support/Azahar/load/mods/<TitleID>" data`

And then you can decompile and compile the game:
```bash
mnlscript-dt-decompile
mnlscript-dt-compile [SCRIPTS TO COMPILE]
```
If you can't use symlinks, add the `-d /path/to/mods/<TitleID>` argument to both of the above commands.
`[SCRIPTS TO COMPILE]` should be a space-separated list of the scripts to compile (e.g. `scripts/fevent/0082.py scripts/fevent/00a0.py`, or `scripts/fevent/{0082,00a0}.py` if your shell supports it).
Although you can leave this blank to recompile all scripts, this is not recommended as it is very slow and unnecessary.
There is no need to repack the ROM, as it is loaded as a mod.
