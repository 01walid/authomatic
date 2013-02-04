from _pyio import __metaclass__
import abc
import datetime
import logging
import random
import simpleauth2
import urlparse


HTTP_METHODS = ('GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'TRACE', 'OPTIONS', 'CONNECT', 'PATCH')


def _login_decorator(func):
    """
    
    """
    
    def wrap(provider, *args, **kwargs):
        error = None
        try:
            func(provider, *args, **kwargs)
        except Exception as e:
            if provider.report_errors:
                error = e
                provider._log(logging.ERROR, 'Reported supressed exception: {}!'.format(repr(error)))
            else:
                raise
        finally:
            event = simpleauth2.LoginResult(provider, error)
            if provider.user or error:
                if provider.callback:
                    provider.callback(event)
                    provider._log(logging.INFO, 'Procedure finished.')
                return event
    return wrap


class BaseProvider(object):
    """
    Abstract base class for all providers
    """
    
    __metaclass__ = abc.ABCMeta
    
    def __init__(self, adapter, provider_name, consumer, callback=None,
                 short_name=None, report_errors=True, logging_level=logging.INFO,
                 csrf_generator=None):
        self.provider_name = provider_name
        self.consumer = consumer
        self.callback = callback
        self.adapter = adapter
        self.short_name = short_name
        self.report_errors = report_errors
        self._generate_csrf = csrf_generator or self._generate_csrf
        self.session_prefix = 'simpleauth'
        
        self.user = None
        
        self._user_info_request = None
        
        # setup logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging_level)
        if logging_level in (None, False):
            self.logger.disabled = False
        
        self.uri = self.adapter.url
    
    
    #=======================================================================
    # Abstract properties
    #=======================================================================
    
    @abc.abstractproperty
    def has_protected_resources(self):
        pass
    
    
    #===========================================================================
    # Abstract methods
    #===========================================================================
    
    @abc.abstractmethod
    def login(self):
        """
        
        
        Should be decorated with @_login_decorator
        """
    
    #===========================================================================
    # Exposed methods
    #===========================================================================
    
    @classmethod
    def get_type(cls):
        return cls.__module__ + '.' + cls.__bases__[0].__name__
    
    
    def update_user(self):
        return self.user
    
    
    #===========================================================================
    # Internal methods
    #===========================================================================
    
    def _session_key(self, key):
        return '{}:{}:{}'.format(self.session_prefix, self.provider_name, key)
    
    
    def _session_set(self, key, value):
        self.adapter.session[self._session_key(key)] = value
    
    
    def _session_get(self, key):
        return self.adapter.session[self._session_key(key)]
    
    
    @classmethod
    def _generate_csrf(cls):
        return str(random.randint(0, 100000000))
    
    
    def _log(self, level, msg):
        base = 'SimpleAuth:{}: '.format(self.__class__.__name__)
        self.logger.log(level, base + msg)
        
    
    def _fetch(self, *args, **kwargs):
        return self.adapter.fetch_async(*args, **kwargs).get_response()
        
    
    def _update_or_create_user(self, data, credentials=None):
        """
        Updates the properties of the self.user object.
        
        Takes into account the self.user_info_mapping property.
        """
        
        if not self.user:
            self._log(logging.INFO, 'Creating user.')
            self.user = simpleauth2.User(self, credentials=credentials)
        else:
            self._log(logging.INFO, 'Updating user.')
        
        self.user.raw_user_info = data
        
        # iterate over user properties
        for key in self.user.__dict__.keys():
            # exclude raw_user_info
            if key is not 'raw_user_info':
                # extract every data item whose key matches the user property name
                # but only if it has a value
                value = data.get(key)
                if value:
                    setattr(self.user, key, value)
                    
        # handle different structure of data by different providers
        self.user = self._user_parser(self.user, data)
        
        return self.user    
    
    
    @staticmethod
    def _user_parser(user, data):
        return user
    
    
    def _scope_parser(self, scope):
        """
        Convert scope list to csv
        """
        
        return ','.join(scope) if scope else None
    
    
    def _check_consumer(self):
        if not self.consumer.key:
            raise simpleauth2.exceptions.ConfigError('Consumer key not specified for provider {}!'.format(self.provider_name))
        
        if not self.consumer.secret:
            raise simpleauth2.exceptions.ConfigError('Consumer secret not specified for provider {}!'.format(self.provider_name))


class AuthorisationProvider(BaseProvider):
    
    has_protected_resources = True
    
    USER_AUTHORISATION_REQUEST_TYPE = 2
    ACCESS_TOKEN_REQUEST_TYPE = 3
    PROTECTED_RESOURCE_REQUEST_TYPE = 4
    
    
    #===========================================================================
    # Abstract properties
    #===========================================================================
    
    @abc.abstractproperty
    def user_authorisation_url(self):
        pass
    
    @abc.abstractproperty
    def access_token_url(self):
        pass
    
    @abc.abstractproperty
    def user_info_url(self):
        pass
    
    #===========================================================================
    # Abstract methods
    #===========================================================================
    
    @abc.abstractmethod
    def to_tuple(self, credentials):
        """
        Override must be a staticmethod
        
        :param credentials:
        """
        
        pass
    
    
    @abc.abstractmethod
    def reconstruct(self, deserialized_tuple):
        """
        Override must be a staticmethod
        
        :param deserialized_tuple:
        """
        
        pass
    
    
    @abc.abstractmethod
    def _create_request_elements(self, request_type, url, method='GET'):
        """
        
        Override must be a classmethod
        
        :param request_type:
        :param url:
        :param method:
        """
    
    
    #===========================================================================
    # Exposed methods
    #===========================================================================
    
    def create_request(self, url, method='GET', content_parser=None, response_parser=None):       
        return simpleauth2.Request(adapter=self.adapter,
                       url=url,
                       credentials=self.user.credentials,
                       method=method,
                       content_parser=content_parser,
                       response_parser=response_parser)
        
    
    def fetch_user_info(self):
        return self.user_info_request.fetch().get_response()
    
    
    def update_user(self):
        return self.fetch_user_info().user
    
    @property
    def user_info_request(self):
        if not self._user_info_request:
            
            def response_parser(response, content_parser):
                response = self.adapter.response_parser(response, content_parser)
                
                self.user = self._update_or_create_user(response.data)
                
                return simpleauth2.UserInfoResponse(response, self.user)
            
            self._user_info_request = self.create_request(self.user_info_url,
                                                          response_parser=response_parser)
        
        return self._user_info_request
    
    
    #===========================================================================
    # Internal methods
    #===========================================================================
    
    @staticmethod
    def _split_url(url):
        "Splits given url to url base and params converted to list of tuples"
        
        split = urlparse.urlsplit(url)
        
        base = urlparse.urlunsplit((split.scheme, split.netloc, split.path, 0, 0))
        
        params = urlparse.parse_qsl(split.query, True)
        
        return base, params
    
    
    @staticmethod
    def _credentials_parser(credentials, data):
        """
        Override this to handle differences in naming conventions of providers.
        
        :param credentials: Instance of Credentials class
        :param data: Response data dictionary
        """
        return credentials
    

class AuthenticationProvider(BaseProvider):
    """Base class for OpenID providers."""
    
    identifier = ''
    
    has_protected_resources = False
    
    @abc.abstractmethod
    def login(self, *args, **kwargs):
        """
        Launches the OpenID authentication procedure.
        
        Accepts oi_identifier optional parameter
        """
        
        # takes the oi_identifier argument into account only if the identifier is not hardcoded
        self.identifier = self.identifier or kwargs.get('oi_identifier', '')
        
        
        












