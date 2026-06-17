#!/usr/bin/env bash
# install.sh — instala Tide Protocol para OpenCode com modo isolado por padrão seguro.
set -euo pipefail

DRY_RUN=0
FORCE=0
GLOBAL=0
CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode-tide}"
BIN_DIR="$HOME/.local/bin"

usage() {
  cat <<EOF
Tide Protocol installer

Uso:
  bash install.sh [opções]

Opções:
  --dry-run              mostra o que faria, sem escrever
  --force                sobrescreve arquivos Tide existentes
  --global               instala na config global padrão ~/.config/opencode
  --config-dir=<path>    destino de config OpenCode (default: ~/.config/opencode-tide)
  --bin-dir=<path>       destino do CLI tide (default: ~/.local/bin)
  -h, --help             mostra ajuda

Recomendado para primeiro teste:
  bash install.sh --config-dir="$HOME/.config/opencode-tide" --bin-dir="$HOME/.local/bin" --force

Uso com config isolada:
  OPENCODE_CONFIG_DIR="$HOME/.config/opencode-tide" opencode
EOF
}

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --force) FORCE=1 ;;
    --global) GLOBAL=1; CONFIG_DIR="$HOME/.config/opencode" ;;
    --config-dir=*) CONFIG_DIR="${arg#*=}" ;;
    --bin-dir=*) BIN_DIR="${arg#*=}" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "erro: opção desconhecida: $arg" >&2; usage; exit 1 ;;
  esac
done

ROOT="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_GLOBAL="$HOME/.config/opencode"
DEFAULT_ISOLATED="$HOME/.config/opencode-tide"

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

if [ "$DRY_RUN" != "1" ] && [ "$CONFIG_DIR" = "$DEFAULT_GLOBAL" ] && [ "$GLOBAL" != "1" ]; then
  say "erro: instalação global em $DEFAULT_GLOBAL requer --global."
  say "Use a instalação isolada para não afetar projetos existentes:"
  say "  bash install.sh --config-dir=\"$DEFAULT_ISOLATED\" --bin-dir=\"$BIN_DIR\" --force"
  exit 1
fi

say "Tide Protocol installer"
say "  source    : $ROOT"
say "  opencode  : $CONFIG_DIR"
say "  bin       : $BIN_DIR"
[ "$CONFIG_DIR" = "$DEFAULT_ISOLATED" ] && say "  profile   : isolated"
[ "$CONFIG_DIR" = "$DEFAULT_GLOBAL" ] && say "  profile   : global"
[ "$DRY_RUN" = "1" ] && say "  mode      : dry-run"
[ "$FORCE" = "1" ] && say "  mode      : force"
say ""

say "Instalando agentes, comandos, skills e regras:"
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
if [ "$CONFIG_DIR" = "$DEFAULT_GLOBAL" ]; then
  say "Abra qualquer projeto com:"
  say "  cd <projeto> && tide init && opencode"
else
  say "Abra um projeto com a config isolada:"
  say "  cd <projeto> && tide init && OPENCODE_CONFIG_DIR=\"$CONFIG_DIR\" opencode"
fi
say ""
say "MCP seguro instalado em:"
say "  $CONFIG_DIR/tide-mcp/tide_mcp.py"
say ""
say "Se o comando tide não for encontrado, adicione ao PATH:"
say "  export PATH=\"$BIN_DIR:\$PATH\""
