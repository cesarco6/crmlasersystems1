import os
import sys
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from docxtpl import DocxTemplate

try:
    doc = DocxTemplate('templates/docs/plantilla_pedido.docx')
    doc.render({'rfc': ''})
    print("SUCCESS")
except Exception as e:
    print("FAILED")
    traceback.print_exc()
