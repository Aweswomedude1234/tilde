# Tilde shell hook for bash.
# Add this line to ~/.bashrc:
#     source "/full/path/to/tilde/shell/termark.bash"
# Then open a new terminal.
#
# What it does: gives each terminal window its own id, and quietly records
# the commands you run so that  `tilde save page`  and
# `tilde save command`  (with no text) have something to save.

# A stable id for this specific terminal window.
if [ -z "$TERMARK_SESSION" ]; then
  export TERMARK_SESSION="bash-$$-$(date +%s)"
fi

# How to call termark. Override TERMARK_BIN if it is not on your PATH.
: "${TERMARK_BIN:=termark}"

# The DEBUG trap fires just before each command runs. BASH_COMMAND holds it.
_termark_debug() {
  # Skip the prompt command itself, blank markers, and our own logging call.
  case "$BASH_COMMAND" in
    _termark_*|*_termark_seen*|":"|":  "*|"$PROMPT_COMMAND"|"${TERMARK_BIN} log"*|"${TERMARK_BIN}"\ log*) return ;;
  esac
  command "${TERMARK_BIN}" log "$BASH_COMMAND" >/dev/null 2>&1
}

# Only install the trap once.
case "$PROMPT_COMMAND" in
  *_termark_seen*) ;;
  *)
    trap '_termark_debug' DEBUG
    PROMPT_COMMAND=":  # _termark_seen${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
    ;;
esac
