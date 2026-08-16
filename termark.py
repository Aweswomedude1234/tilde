#!/usr/bin/env python3
"""
Termark - bookmarks for your terminal.

Save a whole terminal page (commands and their output), a single command,
a file, or a folder. Keep a bookmark global, or scoped to the folder you
were in when you saved it. Works on macOS and Windows.

This is a single file with no third party dependencies.
"""

import os
import sys
import re
import json
import time
import shutil
import platform
import subprocess
from pathlib import Path
from datetime import datetime

APP = "termark"
VERSION = "1.0.0"

# ------------------------------------------------------------------ colors
# System colors only. Plain ANSI, no custom palette, no gradients.
IS_WIN = platform.system() == "Windows"


def _enable_windows_ansi():
    if not IS_WIN:
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING on the standard output handle.
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


_enable_windows_ansi()
_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def c(text, code):
    if not _COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def dim(t):
    return c(t, "2")


def bold(t):
    return c(t, "1")


def underline(t):
    return c(t, "4")


def invert(t):
    return c(t, "7")


# ------------------------------------------------------------------ paths
def config_dir() -> Path:
    if IS_WIN:
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else (Path.home() / ".config")
    return base / APP


def store_path() -> Path:
    return config_dir() / "bookmarks.json"


def sessions_dir() -> Path:
    return config_dir() / "sessions"


def session_log_for(term_id: str) -> Path:
    return sessions_dir() / f"{term_id}.log"


def ensure_dirs():
    config_dir().mkdir(parents=True, exist_ok=True)
    sessions_dir().mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------ store
def load() -> dict:
    p = store_path()
    if not p.exists():
        return {"version": 1, "next_id": 1, "bookmarks": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        # Never lose data silently. Back up the unreadable file and start fresh.
        backup = p.with_suffix(".corrupt.json")
        shutil.copy2(p, backup)
        return {"version": 1, "next_id": 1, "bookmarks": []}


def save(db: dict):
    ensure_dirs()
    p = store_path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(db, indent=2), encoding="utf-8")
    tmp.replace(p)


# ------------------------------------------------------------------ helpers
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")


def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def rel_time(iso: str) -> str:
    try:
        t = datetime.strptime(iso, "%Y-%m-%d %H:%M")
    except Exception:
        return iso
    secs = (datetime.now() - t).total_seconds()
    if secs < 90:
        return "just now"
    mins = secs / 60
    if mins < 90:
        return f"{int(mins)}m ago"
    hours = mins / 60
    if hours < 36:
        return f"{int(hours)}h ago"
    days = hours / 24
    return f"{int(days)}d ago"


TYPE_TAG = {
    "session": "PAGE",
    "command": "CMD ",
    "file": "FILE",
    "folder": "DIR ",
}


def cwd() -> str:
    return os.getcwd()


def term_id() -> str:
    """A stable id for the current terminal session, set by the shell hook."""
    return os.environ.get("TERMARK_SESSION", "default")


def next_id(db) -> int:
    n = db.get("next_id", 1)
    db["next_id"] = n + 1
    return n


def find(db, key):
    """Look a bookmark up by numeric id or by name."""
    if key is None:
        return None
    key = str(key)
    for b in db["bookmarks"]:
        if str(b["id"]) == key:
            return b
    for b in db["bookmarks"]:
        if b.get("name", "").lower() == key.lower():
            return b
    return None


def visible(db, show_all=False):
    """Global bookmarks plus local bookmarks that belong to this folder."""
    here = cwd()
    out = []
    for b in db["bookmarks"]:
        if show_all or b["scope"] == "global" or b.get("folder") == here:
            out.append(b)
    return out


def clip_copy(text: str) -> bool:
    """Copy text to the clipboard using whatever the OS provides."""
    try:
        if IS_WIN:
            p = subprocess.Popen("clip", stdin=subprocess.PIPE, shell=True)
            p.communicate(text.encode("utf-16-le"))
            return p.returncode == 0
        if platform.system() == "Darwin":
            p = subprocess.Popen("pbcopy", stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
            return p.returncode == 0
        for tool in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "-b"]):
            if shutil.which(tool[0]):
                p = subprocess.Popen(tool, stdin=subprocess.PIPE)
                p.communicate(text.encode("utf-8"))
                return p.returncode == 0
    except Exception:
        pass
    return False


def open_path(path: str):
    """Reveal a file or folder in the system file manager / default app."""
    try:
        if IS_WIN:
            os.startfile(path)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
        return True
    except Exception:
        return False


# ------------------------------------------------------------------ output
def line(*parts):
    print("".join(parts))


def err(msg):
    print(f"{c('termark', '31')}: {msg}", file=sys.stderr)


def ok(msg):
    print(f"{c('saved', '32')}  {msg}")


def scope_word(b):
    if b["scope"] == "global":
        return dim("global")
    folder = b.get("folder", "")
    return dim("here") if folder == cwd() else dim(os.path.basename(folder) + os.sep)


# ------------------------------------------------------------------ commands
def cmd_save(args):
    if not args:
        return help_save()

    kind = args[0]
    rest = args[1:]

    # Scope flags can appear anywhere after the kind.
    scope = "local"
    cleaned = []
    for a in rest:
        if a in ("--global", "-g"):
            scope = "global"
        elif a in ("--local", "-l"):
            scope = "local"
        else:
            cleaned.append(a)
    rest = cleaned

    db = load()

    if kind == "command":
        text, name = _split_value_name(rest)
        if not text:
            text = last_command()
        if not text:
            err("no command given and none found in this session. try: termark save command \"ls -la\"")
            return 1
        b = _new(db, "command", name, content=text)

    elif kind == "file":
        path, name = _split_value_name(rest)
        if not path:
            err("which file? try: termark save file ./notes.md")
            return 1
        ap = str(Path(path).expanduser().resolve())
        if not Path(ap).exists():
            err(f"no file at {ap}")
            return 1
        b = _new(db, "file", name or os.path.basename(ap), content=ap)

    elif kind == "folder":
        path, name = _split_value_name(rest)
        if not path:
            path = cwd()
        ap = str(Path(path).expanduser().resolve())
        if not Path(ap).is_dir():
            err(f"no folder at {ap}")
            return 1
        b = _new(db, "folder", name or os.path.basename(ap.rstrip(os.sep)) or ap, content=ap)

    elif kind in ("session", "page"):
        text, name = _split_value_name(rest)
        transcript = read_session()
        if not transcript:
            err("no terminal page recorded yet. install the shell hook, then run some commands.")
            print(dim("       see: termark welcome"))
            return 1
        b = _new(db, "session", name, content=transcript)

    else:
        err(f"unknown thing to save: {kind}")
        return help_save()

    b["scope"] = scope
    save(db)

    label = b["name"] or f"#{b['id']}"
    ok(f"{bold(TYPE_TAG[b['type']].strip())} {bold(label)}  {scope_word(b)}  {dim('#' + str(b['id']))}")
    return 0


def _split_value_name(rest):
    """Return (value, name). A trailing 'as <name>' or '--name x' sets the name."""
    name = None
    if "as" in rest:
        i = rest.index("as")
        name = " ".join(rest[i + 1:]).strip() or None
        rest = rest[:i]
    elif "--name" in rest:
        i = rest.index("--name")
        name = " ".join(rest[i + 1:]).strip() or None
        rest = rest[:i]
    value = " ".join(rest).strip()
    return value, name


def _new(db, kind, name, content):
    b = {
        "id": next_id(db),
        "type": kind,
        "name": name or "",
        "content": content,
        "scope": "local",
        "folder": cwd(),
        "created": now_iso(),
    }
    db["bookmarks"].append(b)
    return b


def cmd_list(args):
    show_all = "--all" in args or "-a" in args
    only = None
    for k in ("session", "command", "file", "folder", "page"):
        if k in args:
            only = "session" if k == "page" else k
    db = load()
    items = visible(db, show_all)
    if only:
        items = [b for b in items if b["type"] == only]

    if not items:
        print(dim("no bookmarks here yet."))
        print(dim("try:   termark save folder   or   termark welcome"))
        return 0

    items.sort(key=lambda b: b["id"], reverse=True)
    width = max((len(f"#{b['id']}") for b in items), default=2)

    header = "  bookmarks here and global" if not show_all else "  every bookmark"
    print(dim(header))
    print(dim("  " + "-" * 40))
    for b in items:
        idc = c(f"#{b['id']}".rjust(width), "2")
        tag = invert(f" {TYPE_TAG[b['type']]} ")
        name = bold(b["name"]) if b["name"] else dim("(unnamed)")
        preview = _preview(b)
        meta = f"{scope_word(b)} {dim('.')} {dim(rel_time(b['created']))}"
        print(f"  {idc} {tag} {name}")
        if preview:
            print(f"      {dim(preview)}")
        print(f"      {meta}")
    print(dim("  " + "-" * 40))
    print(dim(f"  {len(items)} shown . open one with:  termark open <id or name>"))
    return 0


def _preview(b):
    if b["type"] == "session":
        n = len([ln for ln in b["content"].splitlines() if ln.strip()])
        first = next((ln.strip() for ln in b["content"].splitlines() if ln.strip()), "")
        return f"{n} lines . starts: {first[:48]}"
    if b["type"] == "command":
        return b["content"][:64]
    return b["content"]


def cmd_show(args):
    if not args:
        err("show what? try: termark show 3")
        return 1
    db = load()
    b = find(db, args[0])
    if not b:
        err(f"no bookmark called {args[0]}")
        return 1

    title = b["name"] or f"#{b['id']}"
    print(bold(f"{TYPE_TAG[b['type']].strip()}  {title}") + f"   {scope_word(b)}  {dim(b['created'])}")
    print(dim("-" * 48))
    if b["type"] in ("file", "folder"):
        print(b["content"])
        exists = Path(b["content"]).exists()
        print(dim("exists" if exists else "missing (path no longer there)"))
    elif b["type"] == "command":
        print(b["content"])
    else:
        print(b["content"].rstrip("\n"))
    return 0


def cmd_open(args):
    if not args:
        err("open what? try: termark open 3")
        return 1
    db = load()
    b = find(db, args[0])
    if not b:
        err(f"no bookmark called {args[0]}")
        return 1

    if b["type"] == "command":
        if clip_copy(b["content"]):
            print(f"{c('copied', '32')}  command on your clipboard, ready to paste")
        else:
            print(dim("clipboard not available, here it is:"))
        print(bold(b["content"]))
        return 0

    if b["type"] in ("file", "folder"):
        if not Path(b["content"]).exists():
            err(f"path is gone: {b['content']}")
            return 1
        if open_path(b["content"]):
            print(f"{c('opened', '32')}  {b['content']}")
        else:
            print(b["content"])
        return 0

    if b["type"] == "session":
        # A saved terminal page is text. Print it back exactly as captured.
        print(dim(f"replaying page {('#' + str(b['id'])) if not b['name'] else b['name']}"))
        print(dim("-" * 48))
        print(b["content"].rstrip("\n"))
        return 0
    return 0


def cmd_rm(args):
    if not args:
        err("remove what? try: termark rm 3")
        return 1
    db = load()
    removed = []
    for key in args:
        b = find(db, key)
        if b:
            db["bookmarks"].remove(b)
            removed.append(b)
    if not removed:
        err("nothing matched")
        return 1
    save(db)
    for b in removed:
        print(f"{c('removed', '31')} {b['name'] or ('#' + str(b['id']))}")
    return 0


def cmd_search(args):
    if not args:
        err("search for what? try: termark search deploy")
        return 1
    q = " ".join(args).lower()
    db = load()
    hits = []
    for b in visible(db, show_all=True):
        hay = f"{b.get('name','')} {b['content']}".lower()
        if q in hay:
            hits.append(b)
    if not hits:
        print(dim(f"no bookmark matches '{q}'"))
        return 0
    print(dim(f"  matches for '{q}'"))
    for b in hits:
        tag = invert(f" {TYPE_TAG[b['type']]} ")
        name = bold(b["name"]) if b["name"] else dim(f"#{b['id']}")
        print(f"  {c('#'+str(b['id']), '2')} {tag} {name}  {dim(_preview(b))}")
    return 0


# ------------------------------------------------------------- session read
def read_session() -> str:
    """
    Return the current terminal page.

    Prefers a full transcript captured by `termark record`. Falls back to the
    command log written by the shell hook so a page is never empty when the
    hook is installed.
    """
    tid = term_id()
    log = session_log_for(tid)
    if log.exists():
        raw = log.read_text(encoding="utf-8", errors="replace")
        return strip_ansi(raw).strip("\n")
    # Fall back to a plain command log if present.
    hist = sessions_dir() / f"{tid}.cmds"
    if hist.exists():
        return hist.read_text(encoding="utf-8", errors="replace").strip("\n")
    return ""


def last_command() -> str:
    tid = term_id()
    hist = sessions_dir() / f"{tid}.cmds"
    if hist.exists():
        lines = [ln for ln in hist.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
        # The very last line is this termark call itself, so take the one before.
        for ln in reversed(lines):
            if not ln.strip().startswith("termark"):
                return ln.strip()
    return ""


def cmd_record(args):
    """Start a fully recorded terminal page using the OS transcript tool."""
    ensure_dirs()
    tid = term_id()
    log = session_log_for(tid)
    print(dim("recording this terminal page. everything you type and see is captured."))
    print(dim("run  termark save page  when you want to keep it, then type  exit  to stop."))
    if IS_WIN:
        # PowerShell transcript.
        ps = f'Start-Transcript -Path "{log}" -Force | Out-Null; ' \
             f'$Host.UI.RawUI.WindowTitle = "termark recording"'
        subprocess.run(["powershell", "-NoExit", "-Command", ps], check=False)
    else:
        shell = os.environ.get("SHELL", "/bin/bash")
        if platform.system() == "Darwin":
            subprocess.run(["script", "-q", str(log), shell], check=False)
        else:
            subprocess.run(["script", "-q", "-c", shell, str(log)], check=False)
    return 0


# ------------------------------------------------------------------ onboard
def cmd_welcome(args):
    ensure_dirs()
    b = bold
    print()
    print(b("  Termark") + dim("  bookmarks for your terminal"))
    print(dim("  " + "-" * 46))
    print("""  Save the things you keep hunting for: a whole
  terminal page, one command, a file, or a folder.
""")
    print(b("  1. Save something"))
    print(dim("     a command   ") + "termark save command \"kubectl get pods\"")
    print(dim("     a file      ") + "termark save file ./deploy.yaml")
    print(dim("     a folder    ") + "termark save folder ~/work/api")
    print(dim("     this page   ") + "termark save page as \"friday deploy\"")
    print()
    print(b("  2. Choose where it lives"))
    print("     Bookmarks are tied to the folder you saved them in.")
    print("     Add " + b("--global") + " to see one from anywhere.")
    print(dim("     example    ") + "termark save file ~/.zshrc --global")
    print()
    print(b("  3. Find it later"))
    print(dim("     list       ") + "termark list")
    print(dim("     search     ") + "termark search deploy")
    print(dim("     open       ") + "termark open \"friday deploy\"")
    print(dim("     (open copies a command, reveals a file, replays a page)"))
    print()
    print(b("  4. Capture full pages"))
    print("     To bookmark a page with its output, install the")
    print("     shell hook once, or wrap a session in a recorder:")
    print(dim("     hook       ") + "termark install")
    print(dim("     recorder   ") + "termark record")
    print()
    print(dim("  " + "-" * 46))
    print(dim("  that is everything. run  termark list  to begin."))
    print()
    return 0


def cmd_install(args):
    """Print, or write, the shell hook for the user's shell."""
    ensure_dirs()
    plat = platform.system()
    here = Path(__file__).resolve().parent
    if IS_WIN:
        target = here / "shell" / "termark.ps1"
        print(b := bold("PowerShell"))
        print("Add this line to your profile (" + dim("$PROFILE") + "):")
        print(bold(f'  . "{target}"'))
        print(dim("Then open a new terminal. Command history is captured per window."))
        return 0

    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        target = here / "shell" / "termark.zsh"
        rc = "~/.zshrc"
    elif "bash" in shell:
        target = here / "shell" / "termark.bash"
        rc = "~/.bashrc"
    else:
        target = here / "shell" / "termark.bash"
        rc = "your shell rc file"
    print(bold(f"Add this line to {rc}:"))
    print(bold(f'  source "{target}"'))
    print(dim("Then open a new terminal. Command history is captured per window,"))
    print(dim("so  termark save page  and  termark save command  just work."))
    return 0


# ------------------------------------------------------------------ hooks-io
def cmd_log(args):
    """
    Internal. Called by the shell hook to append a command to the session log.
    Not meant to be typed by hand.
    """
    if not args:
        return 0
    ensure_dirs()
    tid = term_id()
    text = " ".join(args).strip()
    if not text:
        return 0
    hist = sessions_dir() / f"{tid}.cmds"
    with hist.open("a", encoding="utf-8") as f:
        f.write(text + "\n")
    return 0


# ------------------------------------------------------------------ help
def help_save():
    print(bold("termark save <thing>"))
    print("  command  \"<text>\"      save a command (or the last one you ran)")
    print("  file     <path>         save a file")
    print("  folder   <path>         save a folder (defaults to here)")
    print("  page                    save the whole terminal page")
    print(dim("  add --global to keep it visible everywhere, or  as <name>  to name it"))
    return 0


def cmd_help(args):
    print()
    print(bold(f"  termark {VERSION}") + dim("  bookmarks for your terminal"))
    print()
    print(bold("  save"))
    print("    termark save command \"git rebase -i HEAD~3\"")
    print("    termark save file ./notes.md")
    print("    termark save folder ~/work/api as api")
    print("    termark save page as \"friday deploy\"")
    print(dim("    flags:  --global | -g    --local | -l    as <name>"))
    print()
    print(bold("  find"))
    print("    termark list            bookmarks here plus global ones")
    print("    termark list --all      every bookmark, every folder")
    print("    termark search <text>   search names and contents")
    print()
    print(bold("  use"))
    print("    termark show  <id|name> print a bookmark")
    print("    termark open  <id|name> copy a command, reveal a file, replay a page")
    print("    termark rm    <id|name> remove one or more")
    print()
    print(bold("  set up"))
    print("    termark welcome         the 4 step tour")
    print("    termark install         print the shell hook line")
    print("    termark record          record a full page with its output")
    print()
    print(dim(f"  bookmarks live in  {store_path()}"))
    print()
    return 0


# ------------------------------------------------------------------ main
COMMANDS = {
    "save": cmd_save,
    "add": cmd_save,
    "list": cmd_list,
    "ls": cmd_list,
    "show": cmd_show,
    "cat": cmd_show,
    "open": cmd_open,
    "go": cmd_open,
    "rm": cmd_rm,
    "remove": cmd_rm,
    "del": cmd_rm,
    "search": cmd_search,
    "find": cmd_search,
    "welcome": cmd_welcome,
    "install": cmd_install,
    "record": cmd_record,
    "log": cmd_log,
    "help": cmd_help,
}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        # First run with no store shows the tour, otherwise the help card.
        if not store_path().exists() and (not argv):
            return cmd_welcome([])
        return cmd_help([])
    if argv[0] in ("-v", "--version", "version"):
        print(f"termark {VERSION} on {platform.system()}")
        return 0
    cmd = argv[0]
    fn = COMMANDS.get(cmd)
    if not fn:
        err(f"no command '{cmd}'. run  termark help")
        return 1
    try:
        return fn(argv[1:]) or 0
    except KeyboardInterrupt:
        print()
        return 130
    except BrokenPipeError:
        # Output was piped into something that stopped reading, like `head`.
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0


if __name__ == "__main__":
    sys.exit(main())
