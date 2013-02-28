.. Authomatic documentation master file, created by
   sphinx-quickstart on Thu Feb  7 16:09:00 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Authomatic is a ...

Table Of Contents
=================

.. toctree::
   
   reference/index
   examples/index

Usage
=====

Bla

Credentials
-----------

If the **user** has logged in with an :class:`.AuthorisationProvider` i.e. |oauth1|_ or |oauth2|_,
the :attr:`.User.credentials` attribute will contain a :class:`.Credentials` object.
It will be empty in other cases.

::
   
   if result.user.credentials:
      # User logged in with Oauth 2.0 or Oauth 1.0a
      credentials = result.user.credentials

Credentials can be serialized to a lightweight url-safe string.

::
   
   serialized = credentials.serialize()

It would be useles if they could not be deserialized back to original.

.. note::
   
   The deserialization is dependent on the :doc:`reference/config` used when they have been serialized.
   You can deserialize them in a different application as long as you wrapp it in the
   :func:`authomatic.middleware` with the same :doc:`reference/config`.

::
   
   credentials = authomatic.credentials(serialized)

They know the provider name which you specified in the :doc:`reference/config`.

::
   
   provider_name = credentials.provider_name

|oauth2| credentials have limited lifetime. You can check whether they are still valid,
in how many seconds they expire, get the date and time or UNIX timestamp of their expiration
and find out whether they expire soon.

::
   
   valid = credentials.valid # True / False
   seconds_remaining = credentials.expire_in
   expire_on = credentials.expiration_date # datetime.datetime()
   expire_on = credentials.expiration_time # 1362080855
   should_refresh = credentials.expire_soon(60 * 60 * 24) # True if expire in less than one day

You can refresh the credentials if they will expire soon.
If they are not valid anymore you must call the :func:`authomatic.login` function to get new credentials.

::
   
   if credentials.expire_soon():
      response = credentials.refresh():
      if response and response.status == 200:
         print 'Credentials have been refreshed succesfully.'

Finally use the credentials (serialized or deserialized) to access **protected resourcess** of the **user**
by passing it to the :func:`authomatic.access` function along with the **resource** URL.

::
   
   response = authomatic.access(credentials, 'https://graph.facebook.com/#####?fields=birthday')

Asynchronous Requests
---------------------

Bla

Session
-------




..
   The Authomatic_ library uses a default
   **secure cookie** based session to store state during the *login procedure*.
   If you want to use another session implementation you can pass it
   together wit **its save method** to the :func:`authomatic.login` function.
   
   .. literalinclude:: advanced-credentials.py
      :language: python
      :lines: 14-27
   
   But wait, haven't I told you that the library is simple to use?
   There must be a better way to make a |webapp2| session!
   
   You guessed it didn't you? There is one from the :mod:`authomatic.extras.gae` module:
   
   .. literalinclude:: ../../examples/gae/advanced-credentials/main.py
      :language: python
      :lines: 17
   
   If you are allready using a |webapp2| session you can do it like this:
   
   .. literalinclude:: advanced-credentials.py
      :language: python
      :lines: 38


   
   
   
   