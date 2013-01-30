from simpleauth2 import providers
from simpleauth2.exceptions import DeniedError, FailureError
from urllib import urlencode
import logging
import simpleauth2


class OAuth2(providers.AuthorisationProvider):
    """
    Base class for OAuth2 services
    """
    
    @staticmethod
    def credentials_to_tuple(credentials):
        return (credentials.access_token, credentials.expiration_date)
    
    @classmethod
    def credentials_from_tuple(cls, tuple_):
        short_name, access_token, expiration_date = tuple_
        return simpleauth2.Credentials(access_token, cls.get_type(), short_name, expiration_date=expiration_date)
    
    @classmethod
    def fetch_protected_resource(cls, adapter, url, credentials, content_parser, method='GET', headers={}, response_parser=None):
        # check required properties of credentials
        if not credentials.access_token:
            raise simpleauth2.exceptions.OAuth2Error('To access OAuth 2.0 resource you must provide credentials with valid access_token!')
        
        # NEW
        request_elements = cls._create_request_elements(request_type=cls.PROTECTED_RESOURCE_REQUEST_TYPE,
                                                       url=url,
                                                       state=adapter.generate_csrf(),
                                                       token=credentials.access_token)
        
        rpc = adapter.fetch_async(*request_elements,
                                    headers=headers,
                                    response_parser=response_parser,
                                    content_parser=content_parser)
        
        return rpc
    
    
    @classmethod
    def _create_request_elements(cls, request_type, url, method='GET', consumer_key='', consumer_secret='',
                                token='', redirect_uri='', scope='', state=''):
        
        # separate url base and query parameters
        url, base_params = cls._split_url(url)
        
        # add extracted params to future params
        params = dict(base_params)
        
        if request_type == cls.USER_AUTHORISATION_REQUEST_TYPE:
            # User authorisation request
            if consumer_key and redirect_uri and scope and state:
                # required
                params['client_id'] = consumer_key
                params['redirect_uri'] = redirect_uri
                params['scope'] = scope
                params['state'] = state
                params['response_type'] = 'code'
            else:
                raise simpleauth2.exceptions.OAuth2Error('Parameters consumer_key, redirect_uri, scope and state ' + \
                                                         'are required to create OAuth 2.0 user authorisation request elements!')
        
        elif request_type == cls.ACCESS_TOKEN_REQUEST_TYPE:
            # Access token request
            if token and consumer_key and consumer_secret and redirect_uri:
                params['code'] = token
                params['client_id'] = consumer_key
                params['client_secret'] = consumer_secret
                params['redirect_uri'] = redirect_uri
                params['grant_type'] = 'authorization_code'
            else:
                raise simpleauth2.exceptions.OAuth2Error('Parameters token, consumer_key, consumer_secret and redirect_uri ' + \
                                                         'are required to create OAuth 2.0 acces token request elements!')
        
        elif request_type == cls.PROTECTED_RESOURCE_REQUEST_TYPE:
            # Protected resources request
            if token:
                params['access_token'] = token
            else:
                #TODO write error message
                raise simpleauth2.exceptions.OAuth2Error('Parameter token is required to create ' + \
                                                         'OAuth 2.0 protected resources request elements!')
        
        params = urlencode(params)
        
        payload = None
        
        if method in ('POST', 'PUT'):
            payload = params
        else:
            url = url + '?' + params
        
        return url, payload, method
        
    
    
    @staticmethod
    def create_url(url_type, base, consumer_key=None, access_token=None, redirect_uri=None, scope=None, state=None):
        
        params = {}
        
        if url_type == 1:
            # Authorization Request http://tools.ietf.org/html/draft-ietf-oauth-v2-31#section-4.1.1
            if consumer_key:
                # required
                params['client_id'] = consumer_key
                params['response_type'] = 'code'
                
                # optional
                if redirect_uri: params['redirect_uri'] = redirect_uri
                if scope: params['scope'] = scope
                if state: params['state'] = state
            else:
                raise simpleauth2.exceptions.OAuth2Error('Parameter consumer_key is required to create Authorization Requestn URL!')
        
        if url_type == 2:
            # 
            if access_token:
                params['access_token'] = access_token
            else:
                raise simpleauth2.exceptions.OAuth2Error('')
            
        return base + '?' + urlencode(params)
    
    
    @providers._login_decorator
    def login(self, *args, **kwargs):
        
        authorisation_code = self.adapter.get_request_param('code')
        error = self.adapter.get_request_param('error')
        state = self.adapter.get_request_param('state')        
        
        if authorisation_code and state:
            # Phase 2 after redirect with success
            self._log(logging.INFO, 'Continuing OAuth 2.0 authorisation procedure after redirect.')
            
            # validate CSRF token
            self._log(logging.INFO, 'Validating request by comparing request state {} to stored state.'.format(state))
            stored_state = self.adapter.retrieve_provider_data(self.provider_name, 'state')
                        
            if not stored_state:
                raise FailureError('Unable to retrieve stored state!')
            elif not stored_state == state:
                raise FailureError('The returned state "{}" doesn\'t match with the stored state!'.format(state), url=self.urls[0])
            
            self._log(logging.INFO, 'Request is valid.')
            
            # exchange authorisation code for access token by the provider
            parser = self._get_parser_by_index(1)
            
            self._log(logging.INFO, 'Fetching access token from {}.'.format(self.urls[1]))
            
            request_elements = self._create_request_elements(request_type=self.ACCESS_TOKEN_REQUEST_TYPE,
                                                            url=self.urls[1],
                                                            method='POST',
                                                            token=authorisation_code,
                                                            consumer_key=self.consumer.key,
                                                            consumer_secret=self.consumer.secret,
                                                            redirect_uri=self.uri)
            
            response = self._fetch(*request_elements, content_parser=parser)
            
            access_token = response.data.get('access_token')
            
            if response.status_code != 200 or not access_token:
                raise FailureError('Failed to obtain OAuth 2.0  access token from {}! HTTP status code: {}.'\
                                  .format(self.urls[1], response.status_code),
                                  code=response.status_code,
                                  url=self.urls[1])
            
            self._log(logging.INFO, 'Got access token.')
            
            # create credentials
            self.credentials = simpleauth2.Credentials(access_token, self.get_type(), self.short_name)
            self._update_credentials(response.data)
            
            # create user
            self._update_or_create_user(response.data, self.credentials)
            
            # We're done
            
        elif error:
            # Phase 2 after redirect with error
            
            error_reason = self.adapter.get_request_param('error_reason')
            error_description = self.adapter.get_request_param('error_description')
            
            if error_reason == 'user_denied':
                raise DeniedError(error_description, url=self.urls[0])
            else:
                raise FailureError(error_description, url=self.urls[0])
        else:
            # phase 1 before redirect
            self._log(logging.INFO, 'Starting OAuth 2.0 authorisation procedure.')
            
            # generate csfr
            state = self.adapter.generate_csrf()
            self.adapter.store_provider_data(self.provider_name, 'state', state)
            
            request_elements = self._create_request_elements(request_type=self.USER_AUTHORISATION_REQUEST_TYPE,
                                                            url=self.urls[0],
                                                            consumer_key=self.consumer.key,
                                                            redirect_uri=self.uri,
                                                            scope=self._normalize_scope(self.consumer.scope),
                                                            state=state)
            
            self._log(logging.INFO, 'Redirecting to {}.'.format(request_elements[0]))
            
            self.adapter.redirect(request_elements[0])


class Facebook(OAuth2):
    """
    Facebook Oauth 2.0 service
    """
    
    # class properties
    urls = ('https://www.facebook.com/dialog/oauth',
            'https://graph.facebook.com/oauth/access_token',
            'https://graph.facebook.com/me')
    
    parsers = (None, providers.QUERY_STRING_PARSER)
    
    user_info_mapping = dict(user_id='id',
                            picture=(lambda data: 'http://graph.facebook.com/{}/picture?type=large'.format(data.get('username'))))
    
    def _update_credentials(self, data):
        """
        We need to override this method to fix Facebooks naming deviation
        """
        credentials = super(Facebook, self)._update_credentials(data)
        
        # Facebook returns "expires" instead of "expires_in"
        credentials.expires_in = data.get('expires')
        return credentials


class Google(OAuth2):
    """
    Google Oauth 2.0 service
    """
    
    # class properties
    urls = ('https://accounts.google.com/o/oauth2/auth',
            'https://accounts.google.com/o/oauth2/token',
            'https://www.googleapis.com/oauth2/v1/userinfo')
    
    parsers = (None, providers.JSON_PARSER)
    
    user_info_mapping = dict(name='name',
                            first_name='given_name',
                            last_name='family_name',
                            user_id='id')
    
    def _normalize_scope(self, scope):
        """
        Google has space-separated scopes
        """
        return ' '.join(scope)
    
    
class WindowsLive(OAuth2):
    """
    Windlows Live Oauth 2.0 service
    """
    
    # class properties
    urls = ('https://oauth.live.com/authorize',
            'https://oauth.live.com/token',
            'https://apis.live.net/v5.0/me')
    
    parsers = (None, providers.JSON_PARSER)
    
    user_info_mapping=dict(user_id='id',
                           email=(lambda data: data.get('emails', {}).get('preferred')))


