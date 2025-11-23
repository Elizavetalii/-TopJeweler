#!/usr/bin/env bash
set -euo pipefail

# Generates detailed class diagrams for the project.
# Produces PNG and DOT files under docs/uml/

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/docs/uml"
mkdir -p "$OUT_DIR"

cd "$ROOT_DIR/lumieresecrete"

echo "[uml] Generating ALL apps diagram via django-extensions (grouped by app)"
python manage.py graph_models \
  -a \
  -g \
  -o png \
  -O "$OUT_DIR/models_all" \
  -X admin -X auth -X contenttypes -X sessions -X messages -X staticfiles || true

echo "[uml] Generating CORE apps diagram (accounts, catalog, product_variants, orders, stores)"
python manage.py graph_models \
  accounts catalog product_variants orders stores \
  -g -o png -O "$OUT_DIR/models_core" \
  -X admin -X auth -X contenttypes -X sessions -X messages -X staticfiles || true

echo "[uml] Also exporting DOT versions"
python manage.py graph_models -a -g -o dot -O "$OUT_DIR/models_all" -X admin -X auth -X contenttypes -X sessions -X messages -X staticfiles || true
python manage.py graph_models accounts catalog product_variants orders stores -g -o dot -O "$OUT_DIR/models_core" -X admin -X auth -X contenttypes -X sessions -X messages -X staticfiles || true

echo "[uml] Done. See $OUT_DIR"

