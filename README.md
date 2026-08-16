# Termark

Bookmarks for your terminal. Save a whole terminal page (commands and their
output), a single command, a file, or a folder. Keep a bookmark global, or
scoped to the folder you were in when you saved it.

Works on macOS and Windows. One Python file, no third party packages.

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

The installer puts a `termark` launcher on your PATH and tells you the one
line to add to your shell so full pages can be captured. Open a new terminal
and run `termark welcome` for the tour.

You can also run it without installing:

```bash
python3 termark.py welcome
```

## The four things you can save

| Thing    | Command                                       |
| -------- | --------------------------------------------- |
| A command| `termark save command "kubectl get pods -A"`  |
| A file   | `termark save file ./deploy.yaml`             |
| A folder | `termark save folder ~/work/api`              |
| A page   | `termark save page`                           |

Name any of them with `as`:

```bash
termark save folder ~/work/api as api
termark save page as "friday deploy"
```

## Global or folder only

Every bookmark is tied to the folder you saved it in. Running `termark list`
shows the bookmarks for the folder you are in, plus every global one. Add
`--global` (or `-g`) to make a bookmark show up everywhere.

```bash
termark save file ./notes.md            # only shows in this folder
termark save file ~/.zshrc --global     # shows everywhere
```

## Find and use

```bash
termark list                 # bookmarks here, plus global ones
termark list --all           # every bookmark in every folder
termark search deploy        # search names and contents

termark show 3               # print a bookmark
termark open 3               # act on it
termark rm 3                 # remove it
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
   termark install
   ```

2. Record a session with output. This wraps your shell in the system
   recorder so both commands and their output are captured:

   ```bash
   termark record
   # run your commands
   termark save page as "the thing that broke"
   exit
   ```

## Where things live

Bookmarks are stored as plain JSON so you can read, sync, or back them up.

- macOS and Linux: `~/.config/termark/bookmarks.json`
- Windows: `%APPDATA%\termark\bookmarks.json`

## Command reference

```
termark save command "<text>"   save a command (or the last one you ran)
termark save file <path>        save a file
termark save folder <path>      save a folder (defaults to here)
termark save page               save the whole terminal page
    flags:  --global | -g   --local | -l   as <name>

termark list [--all]            list bookmarks
termark search <text>           search names and contents
termark show  <id|name>         print a bookmark
termark open  <id|name>         copy a command, reveal a file, replay a page
termark rm    <id|name> ...     remove one or more

termark welcome                 the four step tour
termark install                 print the shell hook line
termark record                  record a full page with its output
termark version
```

## Platform notes

The tool itself is a single cross platform Python file. The only per platform
part is the shell hook, since each shell registers hooks differently:

- `shell/termark.zsh`  for zsh (the default shell on macOS)
- `shell/termark.bash` for bash
- `shell/termark.ps1`  for PowerShell on Windows

Pick the one for your shell. `termark install` picks it for you.
