import authomatic
from authomatic.adapters import gae
import config
import jinja2
import json
import logging
import os
import webapp2

class BaseHandler(webapp2.RequestHandler):
    """
    Base handler which adds jinja2 templating and session.
    """
    
    @webapp2.cached_property
    def jinja2_environment(self):
        path = os.path.join(os.path.dirname(__file__), 'templates')
        return jinja2.Environment(loader=jinja2.FileSystemLoader(path))
    
    def rr(self, template, **context):
        template = self.jinja2_environment.get_template(template)
        self.response.write(template.render(context))


class Home(BaseHandler):
    def get(self):
        self.rr('home.html',
                title='Authomatic example',
                oauth1=sorted(config.OAUTH1.items()),
                oauth2=sorted(config.OAUTH2.items()))


class Login(BaseHandler):
    def any(self, provider_name):
        result = authomatic.login(gae.Webapp2Adapter(self), provider_name)
        if result:
            apis = []
            if result.user:
                result.user.update()
                if result.user.credentials:
                    apis = config.CONFIG.get(provider_name, {}).get('_apis', {})
                
            self.response.write(result.js_callback('loginCallback',
                                                   custom=dict(apis=apis)))

class Action(BaseHandler):
    def get(self):
        provider_name = self.request.params.get('provider', '')
        api = self.request.params.get('api', '')
        credentials = self.request.params.get('credentials', '')
        user_id = self.request.params.get('user_id', '')
        
        method, url = config.CONFIG.get(provider_name, {}).get('_apis', {}).get(api, (None, None))
        
        if method and url:
            url = url.format(id=user_id)
            response = authomatic.access(credentials, url, method=method)
            self.response.write(response.content)


class JSON(BaseHandler):
    def get(self):
        authomatic.json_endpoint(gae.Webapp2Adapter(self))


class Test(BaseHandler):
    def get(self):
        self.rr('test.html')


ROUTES = [webapp2.Route(r'/login/<:.*>', Login, handler_method='any'),
          webapp2.Route(r'/action', Action),
          webapp2.Route(r'/json', JSON),
          webapp2.Route(r'/test', Test),
          webapp2.Route(r'/', Home)]

authomatic.setup(config=config.CONFIG,
                 secret='dsgdfgdgj5fd5g4fmjnfggf6gnkfgn5fngh4n564d3vr54er5',
                 report_errors=True,
                 logging_level=logging.DEBUG)

app = webapp2.WSGIApplication(ROUTES, debug=True)
