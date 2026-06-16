#!/usr/bin/env bash
# install.sh — instala Tide Protocol globalmente para OpenCode.
set -euo pipefail

DRY_RUN=0
FORCE=0
CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
BIN_DIR="$HOME/.local/bin"

usage() {
  cat <<EOF
Tide Protocol installer

Uso:
  bash install.sh [opções]

Opções:
  --dry-run              mostra o que faria, sem escrever
  --force                sobrescreve arquivos Tide existentes
  --config-dir=<path>    destino de config OpenCode (default: ~/.config/opencode)
  --bin-dir=<path>       destino do CLI tide (default: ~/.local/bin)
  -h, --help             mostra ajuda
EOF
}

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --force) FORCE=1 ;;
    --config-dir=*) CONFIG_DIR="${arg#*=}" ;;
    --bin-dir=*) BIN_DIR="${arg#*=}" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "erro: opção desconhecida: $arg" >&2; usage; exit 1 ;;
  esac
done

ROOT="$(cd "$(dirname "$0")" && pwd)"

say() { printf '%s\n' "$*"; }
copy_tree() {
  local src="$1" dst="$2"
  [ -d "$src" ] || return 0
  if [ "$DRY_RUN" = "1" ]; then
    say "  would sync: $dst"
    return
  fi
  mkdir -p "$dst"
  find "$src" -type f | while IFS= read -r file; do
    local rel="${file#$src/}"
    local out="$dst/$rel"
    if [ -e "$out" ] && [ "$FORCE" != "1" ]; then
      say "  skip: $out já existe (use --force para sobrescrever)"
      continue
    fi
    mkdir -p "$(dirname "$out")"
    cp "$file" "$out"
    say "  ok: $out"
  done
}

say "Tide Protocol installer"
say "  source    : $ROOT"
say "  opencode  : $CONFIG_DIR"
say "  bin       : $BIN_DIR"
[ "$DRY_RUN" = "1" ] && say "  mode      : dry-run"
[ "$FORCE" = "1" ] && say "  mode      : force"
say ""

say "Instalando agentes, comandos, skills e regras globais:"
copy_tree "$ROOT/opencode/agents" "$CONFIG_DIR/agents"
copy_tree "$ROOT/opencode/commands" "$CONFIG_DIR/commands"
copy_tree "$ROOT/opencode/skills" "$CONFIG_DIR/skills"
copy_tree "$ROOT/opencode/rules" "$CONFIG_DIR/rules/tide"
copy_tree "$ROOT/mcp" "$CONFIG_DIR/tide-mcp"

say ""
say "Instalando CLI tide:"
if [ "$DRY_RUN" = "1" ]; then
  say "  would copy: $BIN_DIR/tide"
else
  mkdir -p "$BIN_DIR"
  cp "$ROOT/bin/tide" "$BIN_DIR/tide"
  chmod +x "$BIN_DIR/tide"
  say "  ok: $BIN_DIR/tide"
fi

say ""
say "Pronto."
say "Abra qualquer projeto com:"
say "  cd <projeto> && tide init && opencode"
say ""
say "MCP seguro instalado em:"
say "  $CONFIG_DIR/tide-mcp/tide_mcp.py"
say ""
say "Se o comando tide não for encontrado, adicione ao PATH:"
say "  export PATH=\"$BIN_DIR:\$PATH\""
