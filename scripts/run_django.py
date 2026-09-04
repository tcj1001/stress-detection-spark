import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DJANGO_ROOT = PROJECT_ROOT / 'src' / 'django'
sys.path.insert(0, str(DJANGO_ROOT))
os.environ['DJANGO_SETTINGS_MODULE'] = 'stress_django.settings'

try:
    from django.core.management import execute_from_command_line
    args = ['manage.py'] + sys.argv[1:] if len(sys.argv) > 1 else ['manage.py', 'runserver', '8000', '--noreload']
    execute_from_command_line(args)
except Exception as e:
    print('ERROR:', e)
    import traceback; traceback.print_exc()
    raise SystemExit(1)
