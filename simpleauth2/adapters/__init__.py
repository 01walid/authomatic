from urllib import urlencode
import binascii
import hashlib
import hmac
import random
import simpleauth2
import time
import urllib
from _pyio import __metaclass__
import abc


class BaseSession(object):
    
    @abc.abstractmethod
    def __setitem__(self, key, value):
        pass
    
    
    @abc.abstractmethod
    def __getitem__(self, key):
        pass
    
    
    @abc.abstractmethod
    def __delitem__(self, key):
        pass
    
    
    @abc.abstractmethod
    def get(self, key):
        pass


class BaseAdapter(object):
    """
    Base class for platform adapters
    
    Defines common interface for platform specific (non standard library) functionality.
    """    
    
    __metaclass__ = abc.ABCMeta
    
    def login(self, *args, **kwargs):
        return simpleauth2.login(self,  *args, **kwargs)
    
    
    @abc.abstractproperty
    def url(self):
        """Must return the url of the actual request including path but without query and fragment"""
    
    
    @abc.abstractproperty
    def params(self):
        """Must return a dictionary of all request parameters of any HTTP method."""
    
    
    @abc.abstractmethod
    def write(self, value):
        """
        Must write specified value to response.
        
        :param value: string
        """
    
    
    @abc.abstractmethod
    def set_header(self, key, value):
        """
        Must set response headers to key = value.
        
        :param key:
        :param value:
        """
    
    
    @abc.abstractmethod
    def redirect(self, url):
        """
        Must issue a http 302 redirect to the url
        
        :param url: string
        """
    
    
    @abc.abstractproperty
    def session(self):
        """
        A session abstraction with BaseSession or dict interface
        """
    
    
    @abc.abstractmethod
    def response_parser(self, response, content_parser):
        """
        A classproperty to convert platform specific fetch response to simpleauth2.Response.
        
        :param response: result of platform specific fetch call
        :param content_parser: should be passed to simpleauth2.Response constructor.
        
        :returns: simpleauth2.Response
        """
    
    
    @abc.abstractproperty
    def openid_store(self):
        """
        A permanent storage abstraction as described by the openid.store.interface.OpenIDStore interface
        of the python-openid library http://pypi.python.org/pypi/python-openid/.
        
        Required only by the OpenID provider
        """
    

class WebObBaseAdapter(BaseAdapter):
    """
    Abstract base class for adapters for WebOb based frameworks.
    
    See http://webob.org/
    """
    
    @abc.abstractproperty
    def request(self):
        pass
    
    
    @abc.abstractproperty
    def response(self):
        pass
    
    
    #===========================================================================
    # Request
    #===========================================================================
    
    @property
    def url(self):
        return self.request.path_url
    
    
    @property
    def params(self):
        return dict(self.request.params)
    
    
    #===========================================================================
    # Response
    #===========================================================================
            
    def write(self, value):
        self.response.write(value)
    
    
    def set_header(self, key, value):
        self.response.headers[key] = value
    
    
    def redirect(self, url):
        self.response.location = url
        self.response.status = 302
    
    
    
    
    

























