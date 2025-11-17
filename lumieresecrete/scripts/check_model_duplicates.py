#!/usr/bin/env python3
import os, sys, collections
from pathlib import Path

# добавляем корень проекта в sys.path (гарантирует, что пакет lumieresecrete будет импортируем)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# указываем settings (можешь поменять на lumieresecrete.settings если нужно)
os.environ.setdefault('DJANGO_SETTINGS_MODULE','lumieresecrete.settings.base')

try:
    import django
    django.setup()
except Exception as e:
    print("Ошибка при инициализации Django:", e)
    sys.exit(3)

from django.apps import apps

table_to_models = collections.defaultdict(list)
for m in apps.get_models():
    table_to_models[m._meta.db_table].append(f"{m.__module__}.{m.__name__}")

duplicates = False
for table, mods in sorted(table_to_models.items()):
    if len(mods) > 1:
        duplicates = True
        print("DUPLICATE TABLE:", table)
        for mm in mods:
            print("   ", mm)

if not duplicates:
    print("No duplicate db_table names detected.")
    sys.exit(0)
else:
    sys.exit(2)
