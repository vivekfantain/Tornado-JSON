import sys
import pytest
from jsonschema import ValidationError
from tornado.testing import AsyncHTTPTestCase

try:
    sys.path.append('.')
    from tornado_json import routes
    from tornado_json import utils
    from tornado_json import jsend
    sys.path.append('demos/helloworld')
    import helloworld
except ImportError as e:
    print("Please run `py.test` from the root project directory")
    exit(1)


class SuccessException(Exception):

    """Great success!"""


class MockRequestHandler(object):

    class Request(object):
        body = "{\"I am a\": \"JSON object\"}"

    request = Request()

    def fail(message):
        raise utils.APIError(message)

    def success(self, message):
        raise SuccessException


class TestTornadoJSONBase(object):

    """Base class for all tornado_json test classes"""


class TestRoutes(TestTornadoJSONBase):

    """Tests the routes module"""

    def test_get_routes(self):
        """Tests routes.get_routes"""
        assert sorted(routes.get_routes(
            helloworld)) == sorted([
            ("/api/helloworld", helloworld.api.HelloWorldHandler),
            ("/api/asynchelloworld", helloworld.api.AsyncHelloWorld),
            ("/api/postit", helloworld.api.PostIt),
            ("/api/greeting/(?P<name>[a-zA-Z0-9_]+)/?$",
             helloworld.api.Greeting),
            ("/api/freewilled", helloworld.api.FreeWilledHandler)
        ])

    def test_gen_submodule_names(self):
        """Tests routes.gen_submodule_names"""
        assert list(routes.gen_submodule_names(helloworld)
                    ) == ['helloworld.api']

    def test_get_module_routes(self):
        """Tests routes.get_module_routes"""
        assert sorted(routes.get_module_routes(
            'helloworld.api')) == sorted([
            ("/api/helloworld", helloworld.api.HelloWorldHandler),
            ("/api/asynchelloworld", helloworld.api.AsyncHelloWorld),
            ("/api/postit", helloworld.api.PostIt),
            ("/api/greeting/(?P<name>[a-zA-Z0-9_]+)/?$",
             helloworld.api.Greeting),
            ("/api/freewilled", helloworld.api.FreeWilledHandler)
        ])


class TestUtils(TestTornadoJSONBase):

    """Tests the utils module"""

    def test_api_assert(self):
        """Test utils.api_assert"""
        with pytest.raises(utils.APIError):
            utils.api_assert(False, 400)

        utils.api_assert(True, 400)

    class TerribleHandler(MockRequestHandler):

        """This 'handler' is used in test_io_schema"""

        apid = {
            "get": {
                "input_schema": "This doesn't matter because GET request",
                "output_schema": {
                    "type": "number",
                },
            },
            "post": {
                "input_schema": {
                    "type": "number",
                },
                "output_schema": {
                    "type": "number",
                },
            },
        }

        @utils.io_schema
        def get(self):
            return "I am not the handler you are looking for."

        @utils.io_schema
        def post(self):
            return "Fission mailed."

    class ReasonableHandler(MockRequestHandler):

        """This 'handler' is used in test_io_schema"""

        apid = {
            "get": {
                "input_schema": None,
                "output_schema": {
                    "type": "string",
                },
            },
            "post": {
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "I am a": {"type": "string"},
                    },
                    "required": ["I am a"],
                },
                "output_schema": {
                    "type": "string",
                },
            },
        }

        @utils.io_schema
        def get(self, fname, lname):
            return "I am the handler you are looking for, {} {}".format(
                fname, lname)

        @utils.io_schema
        def post(self):
            # Test that self.body is available as expected
            assert self.body == {"I am a": "JSON object"}
            return "Mail received."

    # TODO: Test io_schema functionally instead; pytest.raises does
    #   not seem to be catching errors being thrown after change
    #   to async compatible code.
    # def test_io_schema(self):
    #     """Tests the utils.io_schema decorator"""
    #     th = self.TerribleHandler()
    #     rh = self.ReasonableHandler()

    #     # Expect a TypeError to be raised because of invalid output
    #     with pytest.raises(TypeError):
    #         th.get("Duke", "Flywalker")

    #     # Expect a validation error because of invalid input
    #     with pytest.raises(ValidationError):
    #         th.post()

    #     # Both of these should succeed as the body matches the schema
    #     with pytest.raises(SuccessException):
    #         rh.get("J", "S")
    #     with pytest.raises(SuccessException):
    #         rh.post()


class TestJSendMixin(TestTornadoJSONBase):

    """Tests the JSendMixin module"""

    class MockJSendMixinRH(jsend.JSendMixin):

        """Mock handler for testing JSendMixin"""
        _buffer = None

        def write(self, data):
            self._buffer = data

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def setup(cls):
        """Create mock handler instance"""
        cls.jsend_rh = cls.MockJSendMixinRH()

    def test_success(self):
        """Tests JSendMixin.success"""
        data = "Huzzah!"
        self.jsend_rh.success(data)
        assert self.jsend_rh._buffer == {'status': 'success', 'data': data}

    def test_fail(self):
        """Tests JSendMixin.fail"""
        data = "Aww!"
        self.jsend_rh.fail(data)
        assert self.jsend_rh._buffer == {'status': 'fail', 'data': data}

    def test_error(self):
        """Tests JSendMixin.error"""
        message = "Drats!"
        data = "I am the plural form of datum."
        code = 9001
        self.jsend_rh.error(message=message, data=data, code=code)
        assert self.jsend_rh._buffer == {
            'status': 'error', 'message': message, 'data': data, 'code': code}
