.. _debugging:

===================
Debugging Kallithea
===================

If you encounter problems with Kallithea, here are some instructions
on how to debug them.

.. note:: First make sure you're using the latest version available.

Enable detailed debug
---------------------

Kallithea uses the standard Python ``logging`` module to log its output.
By default only loggers with ``INFO`` level are displayed. To enable full output
change ``level = DEBUG`` for all logging handlers in the currently used .ini file.
This change will allow you to see much more detailed output in the log file or
console. This generally helps a lot to track issues.


Enable interactive debug mode
-----------------------------

To enable interactive debug mode simply comment out ``set debug = false`` in
the .ini file. This will trigger an interactive debugger each time
there is an error in the browser, or send a http link if an error occured in the backend. This
is a great tool for fast debugging as you get a handy Python console right
in the web view.

.. warning:: NEVER ENABLE THIS ON PRODUCTION! The interactive console
             can be a serious security threat to your system.
