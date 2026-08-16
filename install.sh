#!/usr/bin/env bash
# Termark installer for macOS and Linux.
# Run:  bash install.sh
set -e

HERE="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/termark"

# 1. Python check.
if ! command -v python3 >/dev/null 2>&1; then
  echo "Termark needs python3. Install it, then run this again."
  exit 1
fi

# 2. Put a launcher on PATH.
mkdir -p "$BIN_DIR"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec python3 "$HERE/termark.py" "\$@"
EOF
chmod +x "$LAUNCHER"
echo "Installed launcher at $LAUNCHER"

# 3. Make sure that folder is on PATH.
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    echo
    echo "Add this to your shell rc file so 'termark' is found:"
    echo "    export PATH=\"$BIN_DIR:\$PATH\""
    ;;
esac

# 4. Point the user at the right shell hook.
SHELL_NAME="$(basename "${SHELL:-bash}")"
echo
echo "To capture full pages, add the shell hook to your rc file:"
case "$SHELL_NAME" in
  zsh)  echo "    echo 'source \"$HERE/shell/termark.zsh\"'  >> ~/.zshrc" ;;
  bash) echo "    echo 'source \"$HERE/shell/termark.bash\"' >> ~/.bashrc" ;;
  *)    echo "    source \"$HERE/shell/termark.bash\"   (from your shell rc)" ;;
esac

echo
echo "Then open a new terminal and run:  termark welcome"
