#!/usr/bin/env bash
# install.sh — instala agentes, comandos e skills globais do Tide Protocol para OpenCode.
set -euo pipefail

FORCE=0
DRY_RUN=0
TARGET_CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"

for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --config-dir=*) TARGET_CONFIG_DIR="${arg#*=}" ;;
    -h|--help)
      cat <<EOF
Tide Protocol installer

Uso:
  bash install.sh [opções]

Opções:
  --force                 sobrescreve arquivos Tide existentes
  --dry-run               mostra o que faria
  --config-dir=<path>     diretório de config do OpenCode

Destino default:
  ~/.config/opencode
EOF
      exit 0
      ;;
  esac
done

ROOT="$(cd "$(dirname "$0")" && pwd)"

copy_dir() {
  local src="$1" dst="$2"
  if [ ! -d "$src" ]; then
    echo "skip: $src não existe"
    return
  fi
  if [ "$DRY_RUN" = "1" ]; then
    echo "would copy: $src -> $dst"
    return
  fi
  mkdir -p "$dst"
  if [ "$FORCE" = "1" ]; then
    cp -R "$src/." "$dst/"
  else
    # Copia sem sobrescrever arquivos existentes.
    (cd "$src" && find . -type f) | while read -r file; do
      local target="$dst/${file#./}"
      if [ -e "$target" ]; then
        echo "skip existing: $target"
      else
        mkdir -p "$(dirname "$target")"
        cp "$src/${file#./}" "$target"
        echo "ok: $target"
      fi
    done
  fi
}

echo "Tide Protocol installer"
echo "  source: $ROOT"
echo "  target: $TARGET_CONFIG_DIR"
[ "$DRY_RUN" = "1" ] && echo "  mode  : dry-run"

copy_dir "$ROOT/opencode/agents" "$TARGET_CONFIG_DIR/agents"
copy_dir "$ROOT/opencode/commands" "$TARGET_CONFIG_DIR/commands"
copy_dir "$ROOT/opencode/skills" "$TARGET_CONFIG_DIR/skills"
copy_dir "$ROOT/opencode/rules" "$TARGET_CONFIG_DIR/rules"

echo
echo "Instalação concluída."
echo
echo "Notas:"
echo "  - O estado por projeto fica em .opencode/waves/ e deve ser ignorado pelo Git."
echo "  - MCP Tide ainda é contrato inicial; integração completa virá depois."
echo "  - Para usar sem mexer no config padrão, defina OPENCODE_CONFIG_DIR antes de abrir o OpenCode."
