# Termark shell hook for zsh (the default shell on macOS).
# Add this line to ~/.zshrc:
#     source "/full/path/to/termark/shell/termark.zsh"
# Then open a new terminal.
#
# What it does: gives each terminal window its own id, and quietly records
# the commands you run so that  `termark save page`  and
# `termark save command`  (with no text) have something to save.

# A stable id for this specific terminal window.
if [ -z "$TERMARK_SESSION" ]; then
  export TERMARK_SESSION="zsh-$$-$(date +%s)"
fi

# How to call termark. Override TERMARK_BIN if it is not on your PATH.
: "${TERMARK_BIN:=termark}"

# preexec runs right before each command line is executed.
_termark_preexec() {
  # $1 is the exact command line the user typed.
  case "$1" in
    "termark log"*) ;;                       # never log our own logging call
    *) command "${TERMARK_BIN}" log "$1" >/dev/null 2>&1 ;;
  esac
}

# Register the hook without clobbering other tools' hooks.
autoload -Uz add-zsh-hook 2>/dev/null
if whence add-zsh-hook >/dev/null 2>&1; then
  add-zsh-hook preexec _termark_preexec
else
  preexec_functions+=(_termark_preexec)
fi
