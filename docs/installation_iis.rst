.. _installation_iis:

Installing Kallithea on Microsoft Internet Information Services (IIS)
=====================================================================

The following is documented using IIS 7/8 terminology. There should be nothing
preventing you from applying this on IIS 6 well.

.. note::

    For the best security, it is strongly recommended to only host the site over
    a secure connection, e.g. using TLS.

Prerequisites
-------------

Apart from the normal requirements for Kallithea, it is also necessary to get an
ISAPI-WSGI bridge module, e.g. isapi-wsgi.

Installation
------------

The following will assume that your Kallithea is at ``c:\inetpub\kallithea`` and
will be served from the root of its own website. The changes to serve it in its
own virtual folder will be noted where appropriate.

Application Pool
................

Make sure that there is a unique application pool for the Kallithea application
with an identity that has read access to the Kallithea distribution.

The application pool does not need to be able to run any managed code. If you
are using a 32-bit Python installation, then you must enable 32 bit program in
the advanced settings for the application pool otherwise Python will not be able
to run on the website and consequently, Kallithea will not be able to run.

.. note::

    The application pool can be the same as an existing application pool as long
    as the requirements to Kallithea are enabled by the existing application
    pool.

ISAPI Handler
.............

The ISAPI handler needs to be generated from a custom file. Imagining that the
Kallithea installation is in ``c:\inetpub\kallithea``, we would have a file in
the same directory called, e.g. ``dispatch.py`` with the following contents::

    import sys

    if hasattr(sys, "isapidllhandle"):
        import win32traceutil

    import isapi_wsgi

    def __ExtensionFactory__():
        from paste.deploy import loadapp
        from paste.script.util.logging_config import fileConfig
        fileConfig('c:\\inetpub\\kallithea\\production.ini')
        application = loadapp('config:c:\\inetpub\\kallithea\\production.ini')

        def app(environ, start_response):
            user = environ.get('REMOTE_USER', None)
            if user is not None:
                os.environ['REMOTE_USER'] = user
            return application(environ, start_response)

        return isapi_wsgi.ISAPIThreadPoolHandler(app)

    if __name__=='__main__':
        from isapi.install import *
        params = ISAPIParameters()
        sm = [ScriptMapParams(Extension="*", Flags=0)]
        vd = VirtualDirParameters(Name="/",
                                  Description = "ISAPI-WSGI Echo Test",
                                  ScriptMaps = sm,
                                  ScriptMapUpdate = "replace")
        params.VirtualDirs = [vd]
        HandleCommandLine(params)

This script has two parts: First, when run directly using Python, it will
install a script map ISAPI handler into the root application of the default
website, and secondly it will be called from the ISAPI handler when invoked
from the website.

The ISAPI handler is registered to all file extensions, so it will automatically
be the one handling all requests to the website. When the website starts the
ISAPI handler, it will start a thread pool managed wrapper around the paster
middleware WSGI handler that Kallithea runs within and each HTTP request to the
site will be processed through this logic henceforth.

Authentication with Kallithea using IIS authentication modules
..............................................................

The recommended way to handle authentication with Kallithea using IIS is to let
IIS handle all the authentication and just pass it to Kallithea.

To move responsibility into IIS from Kallithea, we need to configure Kallithea
to let external systems handle authentication and then let Kallithea create the
user automatically. To do this, access the administration's authentication page
and enable the ``kallithea.lib.auth_modules.auth_container`` plugin. Once it is
added, enable it with the ``REMOTE_USER`` header and check *Clean username*.
Finally, save the changes on this page.

Switch to the administration's permissions page and disable anonymous access,
otherwise Kallithea will not attempt to use the authenticated user name. By
default, Kallithea will populate the list of users lazily as they log in. Either
disable external auth account activation and ensure that you pre-populate the
user database with an external tool, or set it to *Automatic activation of
external account*. Finally, save the changes.

The last necessary step is to enable the relevant authentication in IIS, e.g.
Windows authentication.

Troubleshooting
---------------

Typically, any issues in this setup will either be entirely in IIS or entirely
in Kallithea (or Kallithea's WSGI/paster middleware). Consequently, two
different options for finding issues exist: IIS' failed request tracking which
is great at finding issues until they exist inside Kallithea, at which point the
ISAPI-WSGI wrapper above uses ``win32traceutil``, which is part of ``pywin32``.

In order to dump output from WSGI using ``win32traceutil`` it is sufficient to
type the following in a console window::

    python -m win32traceutil

and any exceptions occurring in the WSGI layer and below (i.e. in the Kallithea
application itself) that are uncaught, will be printed here complete with stack
traces, making it a lot easier to identify issues.
