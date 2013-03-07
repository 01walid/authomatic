Providers
---------

Providers are abstractions of the **provider** party of the
**provider**/**consumer**/**user** triangle and they are the very core of this library.
There is no reason for you to instantiate them manualy.
You only should specify them in the :doc:`config` and access members of their instances
available in the :class:`.LoginResult` returned by the :func:`authomatic.login` function.

Some provider types accept additional keyword arguments in their constructor which you can pass to them
through the :func:`authomatic.login` function's keyword arguments or through the :doc:`config` like this:

.. note::

   Keyword arguments passed through :func:`authomatic.login` will override
   the values set in :doc:`config`.

::

    CONFIG = {
        'facebook': {
            'class_': oauth2.Facebook, # Subclass of AuthorisationProvider

            # AuthorisationProvider specific keyword arguments:
            'short_name': 1,
            'consumer_key': '###################',
            'consumer_secret': '###################',

            # oauth2.OAuth2 specific keyword arguments:
            'scope': ['user_about_me', 'email']
         },
         'openid': {
             'class_': openid.OpenID, # Subclass of AuthenticationProvider

             # AuthenticationProvider specific keyword arguments:
             'identifier_param': 'claimed_id',

             # openid.OpenID specific keyword arguments:
             'use_realm': True,
             'realm_body': 'OpenID Realm.',
             'realm_param': 'r',
             'xrds_param': 'x',
             'sreg': ['nickname', 'email'],
             'sreg_required': ['email'],
             'ax': ['http://axschema.org/contact/email', 'http://axschema.org/namePerson'],
             'ax_required': ['http://axschema.org/contact/email'],
             'pape': ['http://schemas.openid.net/pape/policies/2007/06/multi-factor']
        },  
    }


Additional keyword arguments by provider type:

+----------------------------------+------------------+-----------+-+
| Provider Type                    | Argument Name    | Required  | |
+==================================+==================+===========+=+
| :class:`.OAuth2`                 | consumer_key     | yes       | |
+                                  +------------------+-----------+-+
|                                  | consumer_secret  | yes       | |
+                                  +------------------+-----------+-+
|                                  | short_name       | yes       | |
+                                  +------------------+-----------+-+
|                                  | scope            |           | |
+----------------------------------+------------------+-----------+-+
| :class:`.OAuth1`                 | consumer_key     | yes       | |
+                                  +------------------+-----------+-+
|                                  | consumer_secret  | yes       | |
+                                  +------------------+-----------+-+
|                                  | short_name       | yes       | |
+----------------------------------+------------------+-----------+-+
| :class:`.OpenID`                 | identifier_param |           | |
+                                  +------------------+-----------+-+
|                                  | use_realm        |           | |
+                                  +------------------+-----------+-+
|                                  | realm_body       |           | |
+                                  +------------------+-----------+-+
|                                  | realm_param      |           | |
+                                  +------------------+-----------+-+
|                                  | xrds_param       |           | |
+                                  +------------------+-----------+-+
|                                  | sreg             |           | |
+                                  +------------------+-----------+-+
|                                  | sreg_required    |           | |
+                                  +------------------+-----------+-+
|                                  | ax               |           | |
+                                  +------------------+-----------+-+
|                                  | ax_required      |           | |
+                                  +------------------+-----------+-+
|                                  | pape             |           | |
+----------------------------------+------------------+-----------+-+
| :class:`.GAEOpenID`              | identifier_param |           | |
+----------------------------------+------------------+-----------+-+



Available provider classes:

+------------------------------+--------------------------+-------------------------------+-+
| |oauth2|                     | |oauth1|                 | |openid|                      | |
+==============================+==========================+===============================+=+
| :class:`.oauth2.Facebook`    | :class:`.oauth1.Twitter` | :class:`.openid.OpenID`       | |
+------------------------------+--------------------------+-------------------------------+-+
| :class:`.oauth2.Google`      |                          | :class:`.openid.Yahoo`        | |
+------------------------------+--------------------------+-------------------------------+-+
| :class:`.oauth2.WindowsLive` |                          | :class:`.openid.Google`       | |
+------------------------------+--------------------------+-------------------------------+-+
| :class:`.oauth2.Viadeo`      |                          | :class:`.gaeopenid.GAEOpenID` | |
+------------------------------+--------------------------+-------------------------------+-+
|                              |                          | :class:`.gaeopenid.Yahoo`     | |
+------------------------------+--------------------------+-------------------------------+-+
|                              |                          | :class:`.gaeopenid.Google`    | |
+------------------------------+--------------------------+-------------------------------+-+


.. automodule:: authomatic.providers.oauth2
   :members:

.. automodule:: authomatic.providers.oauth1
   :members:

.. automodule:: authomatic.providers.openid
   :members:

.. automodule:: authomatic.providers.gaeopenid
   :members:

.. automodule:: authomatic.providers
   :members: