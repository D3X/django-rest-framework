from django.conf.urls import url
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import override_settings

from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework.utils import json
from rest_framework.views import APIView


class PostView(APIView):
    def post(self, request):
        return Response(data=request.data, status=200)


def regular_view(request):
    return HttpResponse()


urlpatterns = [
    url(r'^auth$', APIView.as_view(authentication_classes=(TokenAuthentication,))),
    url(r'^post$', PostView.as_view()),
    url(r'^regular$', regular_view),
]


class RequestUserMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        assert hasattr(request, 'user'), '`user` is not set on request'
        assert request.user.is_authenticated, '`user` is not authenticated'

        return response


class RequestPOSTMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.body
        response = self.get_response(request)
        assert request.POST['foo'] == 'bar'

        return response


class RequestJSONMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        assert list(request.POST.keys()) == []

        return response


@override_settings(ROOT_URLCONF='tests.test_middleware')
class TestMiddleware(APITestCase):

    @override_settings(MIDDLEWARE=('tests.test_middleware.RequestUserMiddleware',))
    def test_middleware_can_access_user_when_processing_response(self):
        user = User.objects.create_user('john', 'john@example.com', 'password')
        key = 'abcd1234'
        Token.objects.create(key=key, user=user)

        self.client.get('/auth', HTTP_AUTHORIZATION='Token %s' % key)

    @override_settings(MIDDLEWARE=('tests.test_middleware.RequestPOSTMiddleware',))
    def test_middleware_can_access_request_post_when_processing_response(self):
        response = self.client.post('/post', {'foo': 'bar'})
        assert response.status_code == 200

    @override_settings(MIDDLEWARE=('tests.test_middleware.RequestJSONMiddleware',))
    def test_original_request_post_is_not_populated_on_json_requests(self):
        # regular view
        response = self.client.post('/regular', json.dumps({'foo': 'bar'}), content_type='application/json')
        assert response.status_code == 200

        # drf
        with self.assertRaises(AssertionError):
            response = self.client.post('/post', json.dumps({'foo': 'bar'}), content_type='application/json')
