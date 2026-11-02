from django.conf import settings
from base.admin import site as admin_site
from django.http import FileResponse, Http404
from django.urls import include, path, re_path
from django.views.decorators.http import require_GET


@require_GET
def frontend(request, route=''):
    index = settings.FRONTEND_DIST / 'index.html'
    if not index.exists():
        raise Http404('Build the React frontend before deployment.')
    response = FileResponse(index.open('rb'), content_type='text/html')
    response['Cache-Control'] = 'no-cache'
    return response


urlpatterns = [path('admin/', admin_site.urls), path('api/', include('base.urls')),
    re_path(r'^(?!api(?:/|$)|admin(?:/|$)|static(?:/|$)|images(?:/|$))(?P<route>.*)$', frontend)]
