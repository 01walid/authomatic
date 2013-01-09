from . import BaseAdapter
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from simpleauth2 import Response
from webapp2_extras import sessions
import urlparse

# taken from anyjson.py
try:
    import simplejson as json
except ImportError: # pragma: no cover
    try:
        # Try to import from django, should work on App Engine
        from django.utils import simplejson as json
    except ImportError:
        # Should work for Python2.6 and higher.
        import json

class ProvidersConfigModel(ndb.Model):
    """
    Datastore model for providers configuration
    """
    
    name = ndb.StringProperty()
    class_name = ndb.StringProperty()
    consumer_key = ndb.StringProperty()
    consumer_secret = ndb.StringProperty()
    scope = ndb.StringProperty()
    
    @classmethod
    def get(cls, key, default=None):
        """
        Resembles the dict.get(key[, default=None]) method
        
        Returns the 
        """
        result = cls.query(cls.name == key).get()
        if result:
            result_dict = result.to_dict()
            # convert scope to list
            scope = result_dict.get('scope')
            if scope:
                result_dict['scope'] = [s.strip() for s in scope.split(',')]
            return result_dict
        else:
            return default 
        
    @classmethod
    def initialize(cls):
        """
        Creates an Example entity if the model is empty
        """
        
        if not len(cls.query().fetch()):
            example = cls.get_or_insert('Example')
            example.name = 'string-identifier-of-provider.'
            example.class_name = 'Name of provider class.'
            example.consumer_key = 'Consumer key.'
            example.consumer_secret = 'Consumer secret'
            example.scope = 'coma, separated, list, of, scopes'
            example.put()


class GAEWebapp2Adapter(BaseAdapter):
    
    def __init__(self, handler, providers_config=None, session=None, session_secret=None, session_key='simpleauth2'):
        self._handler = handler
        self._providers_config = providers_config
        self._session = session
        self._session_secret = session_secret
        self._session_key = session_key
        
        # create session
        if not (session or session_secret):
            raise Exception('Either session or session_secret must be specified')
        
        if not session:
            # create default session
            session_store = sessions.SessionStore(handler.request, dict(secret_key=session_secret))
            self._session = session_store.get_session(session_key, max_age=60)
        
        # session structure:
        #
        # {'facebook': {'phase': 0},
        #  'twitter': {'phase': 1,
        #              'oauth_token': None,
        #              'oauth_token_secret': None}}
    
    def get_current_uri(self):
        """Returns the uri of the actual request"""
        
        route_name = self._handler.request.route.name
        args = self._handler.request.route_args
        return self._handler.uri_for(route_name, *args, _full=True)
    
    
    def get_request_param(self, key):
        """Returns a GET or POST variable by key"""
        
        return self._handler.request.params.get(key)
    
    
    def set_phase(self, provider_name, phase):
        self.store_provider_data(provider_name, 'phase', phase)
    
    
    def get_phase(self, provider_name):
        return self.retrieve_provider_data(provider_name, 'phase', 0)
    
    
    def store_provider_data(self, provider_name, key, value):
        self._session.setdefault(self._session_key, {}).setdefault(provider_name, {})[key] = value
        self._save_session()
        
        
    def retrieve_provider_data(self, provider_name, key, default=None):
        return self._session.setdefault(self._session_key, {}).setdefault(provider_name, {}).get(key, default)
    
    
    def get_providers_config(self):
        
        if self._providers_config:
            return self._providers_config
        else:
            # use Providers model if no providers config specified
            providers_config = ProvidersConfigModel
            providers_config.initialize()
            return providers_config
    
    
    def redirect(self, url):
        self._handler.redirect(url)
    
    
    def fetch(self, url, payload=None, method='GET', headers={}):
        #TODO: Check whether the method is valid
        #TODO: Return Request instance
        return self.fetch_async(url, payload, method, headers).get_result()
    
    
    def fetch_async(self, url, payload=None, method='GET', headers={}):
        """
        Makes an asynchronous object
        
        Must return an object which has a get_result() method
        """
        
        rpc = urlfetch.create_rpc()
        urlfetch.make_fetch_call(rpc, url, payload, method, headers)
        
        #TODO: Return rpc wrapper which returns Request instance on get_result()
        return rpc
    
    
    @staticmethod
    def json_parser(body):
        return json.loads(body)
    
    
    @staticmethod
    def query_string_parser(body):
        res = dict(urlparse.parse_qsl(body))
        if not res:
            res = json.loads(body)
        return res
    
    
    @staticmethod
    def parse_response(response, parser=None):
        resp = Response()
        
        resp.content = response.content
        resp.status_code = response.status_code
        resp.headers = response.headers
        resp.final_url = response.final_url
        resp.data = parser(response.content) if parser else None
        
        return resp
    
    
    def _save_session(self):
        self._session.container.session_store.save_sessions(self._handler.response)

