from simpleauth2 import providers
from urllib import urlencode
import binascii
import hashlib
import hmac
import logging
import simpleauth2
import time
import urllib


class OAuth1(providers.ProtectedResorcesProvider):
    
    def __init__(self, *args, **kwargs):
        super(OAuth1, self).__init__(*args, **kwargs)
        
        # create keys under which oauth token and secret will be stored in session
        self._oauth_token_key = self.provider_name + '_oauth_token'
        self._oauth_token_secret_key = self.provider_name + '_oauth_token_secret'
    
    def _update_credentials(self, response):
        
        credentials = super(OAuth1, self)._update_credentials(response)
        
        credentials.access_token = response.get('oauth_token')
        credentials.access_token_secret = response.get('oauth_token_secret')
        
        credentials.consumer_key = self.consumer.key
        credentials.consumer_secret = self.consumer.secret
        credentials.provider_type = self.get_type()
        
        return credentials    
    
    @classmethod
    def fetch_protected_resource(cls, adapter, url, credentials, content_parser, method='GET', response_parser=None):
        # check required properties of credentials
        if not credentials.access_token:
            raise simpleauth2.exceptions.OAuth2Error('To access OAuth 2.0 resource you must provide credentials with valid access_token!')
        
        url2 = cls.create_url(url_type=4,
                              base=url,
                              consumer_key=credentials.consumer_key,
                              consumer_secret=credentials.consumer_secret,
                              token=credentials.access_token,
                              token_secret=credentials.access_token_secret,
                              nonce=adapter.generate_csrf())
        
        rpc = adapter.fetch_async(content_parser,
                                  url=url2,
                                  response_parser=response_parser)
        
        return rpc
        
    
    @staticmethod
    def credentials_to_tuple(credentials):
        return (credentials.access_token, credentials.access_token_secret)
    
    
    @classmethod
    def credentials_from_tuple(cls, tuple_):
        short_name, access_token, access_token_secret = tuple_
        return simpleauth2.Credentials(access_token, cls.get_type(), short_name, access_token_secret=access_token_secret)
    
    
    @staticmethod
    def create_url(url_type, base, consumer_key=None, consumer_secret=None, token=None, token_secret=None, verifier=None, method='GET', callback=None, nonce=None):
        """ Creates a HMAC-SHA1 signed url to access OAuth 1.0 endpoint"""
        
        params = {}
        
        if url_type == 1:
            # Request Token URL
            if consumer_key and consumer_secret and callback:
                params['oauth_consumer_key'] = consumer_key
                params['oauth_callback'] = callback
            else:
                raise simpleauth2.exceptions.OAuth1Error('Parameters consumer_key, consumer_secret and callback are required to create Request Token URL!')
            
        elif url_type == 2:
            # User Authorization URL
            if token:
                params['oauth_token'] = token
                return base + '?' + urlencode(params)
            else:
                raise simpleauth2.exceptions.OAuth1Error('Parameter token is required to create User Authorization URL!')
            
        elif url_type == 3:
            # Access Token URL
            if consumer_key and consumer_secret and token and verifier:
                params['oauth_token'] = token
                params['oauth_consumer_key'] = consumer_key
                params['oauth_verifier'] = verifier
            else:
                raise simpleauth2.exceptions.OAuth1Error('Parameters consumer_key, consumer_secret, token and verifier are required to create Access Token URL!')
            
        elif url_type == 4:
            # Protected Resources URL
            if consumer_key and consumer_secret and token and token_secret:
                params['oauth_token'] = token
                params['oauth_consumer_key'] = consumer_key
            else:
                raise simpleauth2.exceptions.OAuth1Error('Parameters consumer_key, consumer_secret, token and token_secret are required to create Protected Resources URL!')
        
        
        
        # Sign request.
        # http://oauth.net/core/1.0a/#anchor13
        
        # Prepare parameters for signature base string
        # http://oauth.net/core/1.0a/#rfc.section.9.1
        params['oauth_signature_method'] = 'HMAC-SHA1' #TODO: Add other signature methods
        params['oauth_timestamp'] = str(int(time.time()))
        params['oauth_nonce'] = nonce
        params['oauth_version'] = '1.0'
        
        # Normalize request parameters
        # http://oauth.net/core/1.0a/#rfc.section.9.1.1
        
        # the oauth_signature MUST NOT be there
        params_to_sign = [(k, v) for k, v in params.items() if k != 'oauth_signature']
        
        # parameters must be sorted first by key, then by value
        params_to_sign.sort()
        
        # parameters must be separated by the & sign like this: a=1&c=hi%20there&f=25&f=50&f=a&z=p&z=t 
        params_to_sign = urllib.urlencode(params_to_sign)
        params_to_sign = params_to_sign.replace('+', '%20').replace('%7E', '~')
        
        # Concatenate http method, base URL and request parameters by &
        # http://oauth.net/core/1.0a/#rfc.section.9.1.3
        base_string = '&'.join((simpleauth2.escape(method),
                        simpleauth2.escape(base),
                        simpleauth2.escape(params_to_sign)))
        
        
        
        # Prepare the signature key
        # http://oauth.net/core/1.0a/#rfc.section.9.2
        key = '{}&'.format(simpleauth2.escape(consumer_secret))
        if token_secret:
            key += simpleauth2.escape(token_secret)
        
        
        
        # Generate signature
        
        # Generate HMAC-SHA1 signature
        # http://oauth.net/core/1.0a/#rfc.section.9.2
        hashed = hmac.new(key, base_string, hashlib.sha1)
        signature = binascii.b2a_base64(hashed.digest())[:-1]
        
        
        #TODO: Generate RSA-SHA1 signature if there is need for it
        # http://oauth.net/core/1.0a/#rfc.section.9.3
        
        # add signature to params
        params['oauth_signature'] = signature
        
        # return signed url
        return base + '?' + urlencode(params)
    
    
    def login(self, **kwargs):
        
        self._check_consumer()
        
        if self.phase == 0:
            
            
            parser = self._get_parser_by_index(0)
            
            # Create Request Token URL
            url1 = self.create_url(url_type=1,
                                     base=self.urls[0],
                                     consumer_key=self.consumer.key,
                                     consumer_secret=self.consumer.secret,
                                     callback=self.uri,
                                     nonce=self.adapter.generate_csrf())
            
            response = self._fetch(parser, url1)
            
            logging.info('RESPONSE = {}'.format(response.status_code))
            
            # check if response status is OK
            if response.status_code != 200:
                self._finish(simpleauth2.AuthError.FAILURE, \
                             'Failed to obtain request token from {}! HTTP status code: {}.'\
                             .format(self.urls[0], response.status_code),
                             code=response.status_code,
                             url=self.urls[0])
                return
            
            # extract OAuth token and save it to storage
            #oauth_token = parser(response).get('oauth_token')
            oauth_token = response.data.get('oauth_token')
            if not oauth_token:
                self._finish(simpleauth2.AuthError.FAILURE, \
                             'Response from {} doesn\'t contain OAuth 1.0a oauth_token!'.format(self.urls[0]),
                             response.data,
                             url=self.urls[0])
                return
            
            self.adapter.store_provider_data(self.provider_name, 'oauth_token', oauth_token)
            
            # extract OAuth token secret and save it to storage
            #oauth_token_secret = parser(response.setdefault('content'), {}).get('oauth_token_secret')
            oauth_token_secret = response.data.get('oauth_token_secret')
            if not oauth_token_secret:
                self.adapter.reset_phase(self.provider_name)
                raise Exception('Could not get a valid OAuth token secret from provider {}!'.format(self.provider_name))
            
            self.adapter.store_provider_data(self.provider_name, 'oauth_token_secret', oauth_token_secret)
            
            # Create User Authorization URL
            url2 = self.create_url(url_type=2,
                                     base=self.urls[1],
                                     token=oauth_token)
            
            self.adapter.redirect(url2)
            
            self._increase_phase()
            
        if self.phase == 1:
            
            self._reset_phase()
                        
            # retrieve the OAuth token from session
            oauth_token = self.adapter.retrieve_provider_data(self.provider_name, 'oauth_token')
            if not oauth_token:
                self._finish(simpleauth2.AuthError.FAILURE,
                             'Unable to retrieve OAuth 1.0a oauth_token from storage!')
                return
            
            # if the user denied the request token
            #TODO: Not sure that all providers return it as denied=token since there is no mention in the OAuth 1.0a spec
            if self.adapter.get_request_param('denied') == oauth_token:
                self._finish(simpleauth2.AuthError.DENIED,
                             'User denied the OAuth 1.0a request token {} during a redirect to {}!'.format(oauth_token, self.urls[1]),
                             error_original_msg=self.adapter.get_request_param('denied'),
                             url=self.urls[1])
                return
            
            oauth_token_secret = self.adapter.retrieve_provider_data(self.provider_name, 'oauth_token_secret')
            if not oauth_token_secret:
                self._finish(simpleauth2.AuthError.FAILURE,
                             'Unable to retrieve OAuth 1.0a oauth_token_secret from storage!')
                return
            
            # extract the verifier
            verifier = self.adapter.get_request_param('oauth_verifier')
            if not verifier:
                self._finish(simpleauth2.AuthError.FAILURE,
                             'Unable to retrieve OAuth 1.0a oauth_verifier from storage!')
                return
                        
            parser = self._get_parser_by_index(1)
            
            # Create Access Token URL
            url3 = self.create_url(url_type=3,
                                     base=self.urls[2],
                                     token=oauth_token,
                                     consumer_key=self.consumer.key,
                                     consumer_secret=self.consumer.secret,
                                     token_secret=oauth_token_secret,
                                     verifier=verifier,
                                     nonce=self.adapter.generate_csrf())
            
            response = self._fetch(parser, url3, method='POST')
            
            if response.status_code != 200:
                self._finish(simpleauth2.AuthError.FAILURE, \
                             'Failed to obtain OAuth 1.0a  oauth_token from {}! HTTP status code: {}.'\
                             .format(self.urls[2], response.status_code),
                             code=response.status_code,
                             url=self.urls[2])
                return
            
            logging.info('RESPONSE DATA = {}'.format(response.data))
            
            self._update_or_create_user(response.data)
            
            self.credentials = simpleauth2.Credentials(self.consumer.access_token, self.get_type(), self.short_name)
            self._update_credentials(response.data)
                        
            self._finish()


class Twitter(OAuth1):
    urls = ('https://api.twitter.com/oauth/request_token',
            'https://api.twitter.com/oauth/authorize',
            'https://api.twitter.com/oauth/access_token',
            'https://api.twitter.com/1/account/verify_credentials.json')
    
    parsers = (providers.QUERY_STRING_PARSER, providers.QUERY_STRING_PARSER)
    
    user_info_mapping = dict(user_id='short_name',
                            username='screen_name',
                            picture='profile_image_url',
                            locale='lang',
                            link='url')

