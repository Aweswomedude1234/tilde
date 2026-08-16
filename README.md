# Tilde

Bookmarks for your terminal. Save a whole terminal page (commands and their
output), a single command, a file, or a folder. Keep a bookmark global, or
scoped to the folder you were in when you saved it.

Works on macOS and Windows. One Python file, no third party packages.

Tilde is free and open to use.

```
saved  PAGE friday deploy  here  #4
saved  FILE deploy.yaml     global #2
saved  CMD  pods            here   #1
```

## Install

macOS or Linux:

```bash
bash install.sh
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

The installer puts a `tilde` launcher on your PATH and tells you the one
line to add to your shell so full pages can be captured. Open a new terminal
and run `tilde welcome` for the tour.

You can also run it without installing:

```bash
python3 termark.py welcome
```

## The four things you can save

| Thing    | Command                                       |
| -------- | --------------------------------------------- |
| A command| `tilde save command "kubectl get pods -A"`  |
| A file   | `tilde save file ./deploy.yaml`             |
| A folder | `tilde save folder ~/work/api`              |
| A page   | `tilde save page`                           |

Name any of them with `as`:

```bash
tilde save folder ~/work/api as api
tilde save page as "friday deploy"
```

## Global or folder only

Every bookmark is tied to the folder you saved it in. Running `tilde list`
shows the bookmarks for the folder you are in, plus every global one. Add
`--global` (or `-g`) to make a bookmark show up everywhere.

```bash
tilde save file ./notes.md            # only shows in this folder
tilde save file ~/.zshrc --global     # shows everywhere
```

## Find and use

```bash
tilde list                 # bookmarks here, plus global ones
tilde list --all           # every bookmark in every folder
tilde search deploy        # search names and contents

tilde show 3               # print a bookmark
tilde open 3               # act on it
tilde rm 3                 # remove it
```

`open` does the right thing for each type:

- A command is copied to your clipboard, ready to paste.
- A file or folder is revealed in Finder or Explorer.
- A page is replayed back into your terminal exactly as it was captured.

You can pass an id (`3`) or a name (`"friday deploy"`) anywhere.

## Capturing a full page

A saved page keeps the commands and their output. There are two ways to
capture one.

1. Install the shell hook (recommended). It quietly records the commands you
   run in each terminal window, so `termark save page` just works. The
   installer prints the exact line to add. To see it again:

   ```bash
   tilde install
   ```

2. Record a session with output. This wraps your shell in the system
   recorder so both commands and their output are captured:

   ```bash
   tilde record
   # run your commands
   termark save page as "the thing that broke"
   exit
   ```

## Where things live

Bookmarks are stored as plain JSON so you can read, sync, or back them up.

- macOS and Linux: `~/.config/tilde/bookmarks.json`
- Windows: `%APPDATA%\tilde\bookmarks.json`

## Command reference

```
tilde save command "<text>"   save a command (or the last one you ran)
tilde save file <path>        save a file
tilde save folder <path>      save a folder (defaults to here)
tilde save page               save the whole terminal page
    flags:  --global | -g   --local | -l   as <name>

tilde list [--all]            list bookmarks
tilde search <text>           search names and contents
tilde show  <id|name>         print a bookmark
tilde open  <id|name>         copy a command, reveal a file, replay a page
tilde rm    <id|name> ...     remove one or more

tilde welcome                 the four step tour
tilde install                 print the shell hook line
tilde record                  record a full page with its output
tilde version
```

## Platform notes

The tool itself is a single cross platform Python file. The only per platform
part is the shell hook, since each shell registers hooks differently:

- `shell/termark.zsh`  for zsh (the default shell on macOS)
- `shell/termark.bash` for bash
- `shell/termark.ps1`  for PowerShell on Windows

Pick the one for your shell. `tilde install` picks it for you.
