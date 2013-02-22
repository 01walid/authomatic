"""
Google App Engine Adapters
--------------------------

Adapters and utilities to be used on |gae|_.

"""

from authomatic import adapters
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from urllib import urlencode
from webapp2_extras import sessions
import authomatic.core as core
import datetime
import logging
import os
import pickle
import urlparse

__all__ = ['ndb_config', 'Webapp2Adapter']


class Webapp2AdapterError(Exception):
    pass


class GAEError(Exception):
    pass


class NDBConfig(ndb.Model):
    """
    Datastore model for providers configuration    
    """
        
    provider_name = ndb.StringProperty( )
    class_ = ndb.StringProperty()
    
    # AuthorisationProvider
    short_name = ndb.IntegerProperty()
    consumer_key = ndb.StringProperty()
    consumer_secret = ndb.StringProperty()
    
    # OAuth2
    scope = ndb.StringProperty()
    
    # AuthenticationProvider
    identifier_param = ndb.StringProperty()
    
    # OpenID
    use_realm = ndb.BooleanProperty(default=True)
    realm_body = ndb.StringProperty()
    realm_param = ndb.StringProperty()
    xrds_param = ndb.StringProperty()
    sreg = ndb.StringProperty()
    sreg_required = ndb.StringProperty()
    ax = ndb.StringProperty()
    ax_required = ndb.StringProperty()
    pape = ndb.StringProperty()
    
    @classmethod
    def get(cls, key, default=None):
        """
        Resembles the dict.get(key[, default=None]) method
        
        Returns a provider config dictionary
        """
        
        result = cls.query(cls.provider_name == key).get()
        
        if result:
            result_dict = result.to_dict()
            
            for i in ('scope', 'sreg', 'sreg_required', 'ax', 'ax_required', 'pape', ):
                prop = result_dict.get(i)
                if prop:
                    result_dict[i] = [s.strip() for s in prop.split(',')]
                else:
                    result_dict[i] = None

            return result_dict
        else:
            return default
    
    
    @classmethod
    def values(cls):
        # get all items
        results = cls.query().fetch()
        # return list of dictionaries
        return [result.to_dict() for result in results]
    
    
    @classmethod
    def initialize(cls):
        """
        Creates an Example entity if the model is empty
        """
        
        if not len(cls.query().fetch()):
            
            example = cls.get_or_insert('Example')
            
            example.class_ = 'Provider class e.g. "authomatic.providers.oauth2.Facebook".'
            example.provider_name = 'Your custom provider name e.g. "fb".'
            
            # AuthorisationProvider
            example.consumer_key = 'Consumer key.'
            example.consumer_secret = 'Consumer secret'
            example.short_name = 1
            
            # OAuth2
            example.scope = 'coma, separated, list, of, scopes'
            
            # AuthenticationProvider
            example.identifier_param = 'User identifier to authenticate e.g. "me.yahoo.com".'
            
            # OpenID
            example.use_realm = True
            example.realm_body = 'Contents of the HTML body tag of the realm.'
            example.realm_param = 'Name of the query parameter to be used to serve the realm (leave empty for default).'
            example.xrds_param = ' The name of the query parameter to be used to serve the XRDS document (leave empty for default).'
            example.sreg = 'list, of, strings, of, optional, SREG, fields, (leave empty for defaults)'
            example.sreg_required = 'list, of, strings, of, required, SREG, fields, (leave empty for defaults)'
            example.ax = 'list, of, strings, of, optional, AX, schemas, (leave empty for defaults)'
            example.ax_required = 'list, of, strings, of, required, AX, schemas, (leave empty for defaults)'
            example.pape = 'list, of, strings, of, optional, PAPE, policies, (leave empty for defaults)'
            
            
            example.put()
            
            url = '{}://{}/_ah/admin/datastore?kind={}'.format(os.environ.get('wsgi.url_scheme'),
                                                               os.environ.get('HTTP_HOST'),
                                                               cls.__name__)
            
            raise GAEError('A NDBConfig data model was created! ' + \
                           'Go to {} and populate it with data!'.format(url))


def ndb_config():
    """
    Allows you to have a **datastore** :doc:`config` instead of a hardcoded one.
    
    This function creates an **"Example"** entity of kind **"NDBConfig"** in the datastore
    if the model is empty and raises and error to inform you that you should populate the model with data.
        
    .. note::
    
        The *Datastore Viewer* in the ``_ah/admin/`` wont let you add properties to a model
        if there is not an entity with that property already.
        Therefore it is a good idea to keep the **"Example"** entity (which has all
        possible properties set) in the datastore.
    
    :raises:
        :exc:`.GAEError`
    
    :returns:
        :class:`.NDBConfig`
    """
    
    NDBConfig.initialize()
    return NDBConfig


class _GAESessionWrapper(adapters.BaseSession):
    
    JSON_SERIALIZABLE_KEY = 'json_serializable'
    
    def __init__(self, session, response):
        self.session = session
        self.response = response
    
    
    def _from_json_serializable(self, value):
        """
        Detects if value was created by self._save_json_serializable() and
        returns its original value if so or returns unchanged value.
        
        :param value:
        """
        
        if isinstance(value, dict) and value.get(self.JSON_SERIALIZABLE_KEY):
            return pickle.loads(value.get(self.JSON_SERIALIZABLE_KEY))
        else:
            return value
    
    
    def _save_json_serializable(self, key, value):
        """
        Converts non JSON serializable objects to {JSON_SERIALIZABLE_KEY, pickle.dumps(value)} dictionary.
        
        The securecookie session backend complains that YadisServiceManager is not JSON serializable.
        We go around this by pickling the value to a dictionary,
        which we can identify by the key for unpickling when retrieved from session.
        
        :param key:
        :param value:
        """
        
        try:
            self.session.__setitem__(key, value)
            self.session.container.save_session(self.response)
        except TypeError:
            # if value is not JSON serializable pickle it to a JSON serializable dictionary
            # with identifiable key.
            json_serializable = {self.JSON_SERIALIZABLE_KEY: pickle.dumps(value)}
            self.session.__setitem__(key, json_serializable)
            self.session.container.save_session(self.response)
    
    
    def __setitem__(self, key, value):
        self._save_json_serializable(key, value)
        
    
    def __delitem__(self, key):
        self.session.__delitem__(key)
        self.session.container.save_session(self.response)
    
    
    def __getitem__(self, key):
        return self._from_json_serializable(self.session.__getitem__(key))
        
    
    def get(self, key):
        return self._from_json_serializable(self.session.get(key, None))



