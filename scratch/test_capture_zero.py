from starlette.requests import Request
from app.web.pages import ctx, templates

req = Request({'type': 'http', 'method': 'GET', 'path': '/lots/999/capture', 'headers': [(b'cookie', b'll_lang=bn')], 'query_string': b''})
user = {'id': 4, 'role': 'inspector', 'display_name': 'Rakib Hasan', 'email': 'rakib@lotline.demo'}
dummy_lot = {'id': 999, 'lot_code': 'LT-TEST', 'lot_size': 500, 'status': 'open'}
dummy_progress = {'units': 0, 'required_units': 0, 'views': 0, 'reviewed': 0, 'pending': 0, 'pct_units': 0, 'pct_views': 0}

c = ctx(req, active='lots', user=user, lot=dummy_lot, units=[], progress=dummy_progress, can_write=True)
html = templates.TemplateResponse(req, 'capture.html', c).body.decode('utf-8')

print('Has n=0 false complete banner?:', 'n=0' in html)
print('Has G-01 button?:', 'G-01 যোগ করে ছবি আপলোড শুরু করুন' in html)
print('Has addUnitForm?:', 'id="addUnitForm"' in html)

