from starlette.requests import Request
from app.services import review
from app.web.pages import ctx, templates

req = Request({'type': 'http', 'method': 'GET', 'path': '/lots/7/capture', 'headers': [(b'cookie', b'll_lang=bn')], 'query_string': b''})
user = {'id': 4, 'role': 'inspector', 'display_name': 'Rakib Hasan', 'email': 'rakib@lotline.demo'}
lot7 = review.lot(7)
units7 = review.units_with_views(7)
prog7 = review.progress(7)

c = ctx(req, active='lots', user=user, lot=lot7, units=units7, progress=prog7, can_write=True)
html = templates.TemplateResponse(req, 'capture.html', c).body.decode('utf-8')

print('Total units rendered:', len(units7))
print('Has upload forms for views?:', 'action="/lots/7/views/' in html)
print('Has file input for upload?:', 'type="file"' in html)
print('Number of file upload inputs:', html.count('type="file"'))

