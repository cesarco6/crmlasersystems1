import os, sys, django, traceback
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from docxtpl import DocxTemplate
doc = DocxTemplate('templates/docs/plantilla_pedido.docx')
try:
    doc.render({'rfc': ''})
except Exception as e:
    print('LINENO:', e.lineno)
    xml = doc.get_xml().decode('utf-8')
    # xml is usually 1 line. We need to parse Jinja trace
    print(xml[max(0, 1000):1500])
