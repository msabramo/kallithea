.. _installation_win:


Installation and upgrade on Windows (7/Server 2008 R2 and newer)
================================================================

First time install
::::::::::::::::::

Target OS: Windows 7 and newer or Windows Server 2008 R2 and newer

Tested on Windows 8.1, Windows Server 2008 R2 and Windows Server 2012

To install on an older version of Windows, see `<installation_win_old.html>`_


Step 1 - Install Python
-----------------------

Install Python 2.x.y (x = 6 or 7). Latest version is recommended. If you need another version, they can run side by side.

  DO NOT USE A 3.x version.

- Download Python 2.x.y from http://www.python.org/download/
- Choose and click on the version
- Click on "Windows X86-64 Installer" for x64 or "Windows x86 MSI installer" for Win32.
- Disable UAC or run the installer with admin privileges. If you chose to disable UAC, do not forget to reboot afterwards.

While writing this Guide, the latest version was v2.7.9.
Remember the specific major and minor versions installed, because they will
be needed in the next step. In this case, it is "2.7".


Step 2 - Python BIN
-------------------

Add Python BIN folder to the path

You have to add the Python folder to the path, you can do it manually (editing "PATH" environment variable) or using Windows Support Tools that came preinstalled in Vista/7 and later.

Open a CMD and type::

  SETX PATH "%PATH%;[your-python-path]" /M

Please substitute [your-python-path] with your Python installation path. Typically: C:\\Python27


Step 3 - Install Win32py extensions
-----------------------------------

Download pywin32 from:
http://sourceforge.net/projects/pywin32/files/

- Click on "pywin32" folder
- Click on the first folder (in this case, Build 219, maybe newer when you try)
- Choose the file ending with ".amd64-py2.x.exe" (".win32-py2.x.exe" for Win32) -> x being the minor version of Python you installed (in this case, 7).
  When writing this Guide, the file was:
  http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/pywin32-219.win-amd64-py2.7.exe/download (x64)
  http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/pywin32-219.win32-py2.7.exe/download (Win32)


Step 4 - Install pip
--------------------

pip is a package management system for Python. You will need it to install Kallithea and its dependencies.

If you installed Python 2.7.9+, you already have it (as long as you ran the installer with admin privileges or disabled UAC).

If it was not installed or if you are using Python>=2.6,<2.7.9:

- Go to https://bootstrap.pypa.io
- Right-click on get-pip.py and choose Saves as...
- Run "python get-pip.py" in the folder where you downloaded get-pip.py (may require admin access).
(See http://stackoverflow.com/questions/4750806/how-to-install-pip-on-windows for explanations or alternatives)

Note that pip.exe will be placed inside your Python installation's Scripts folder, which is likely not on your path.

Open a CMD and type::

  SETX PATH "%PATH%;[your-python-path]\Scripts" /M


Step 5 - Kallithea Folder Structure
-----------------------------------

Create a Kallithea folder structure.

This is only an example to install Kallithea. Of course, you can change it. However, this Guide will follow the proposed structure, so please later adapt the paths if you change them. Folders with NO SPACES are recommended. But you can try it if you are brave...

Create the following folder structure::

  C:\Kallithea
  C:\Kallithea\Bin
  C:\Kallithea\Env
  C:\Kallithea\Repos


Step 6 - Install virtualenv
---------------------------

.. note::
   A python virtual environment will allow for isolation between the Python packages of your system and those used for Kallithea.
   It is strongly recommended to use it to ensure that Kallithea does not change a dependency that another software uses or vice versa.
   If you are using your server (or VM) only for Kallithea, you can skip this step, at your own risk.

Install Virtual Env for Python

In a command prompt type::

  pip install virtualenv

Virtualenv will now be inside your Python Scripts path (C:\\Python27\\Scripts or similar).

To create a virtual environment, run::

  virtualenv C:\Kallithea\Env


Step 7 - Install Kallithea
--------------------------

In order to install Kallithea, you need to be able to run "pip install kallithea". It will use Python pip to install the Kallithea Python package and its dependencies.
Some Python packages use managed code and need to be compiled.
This can be done on Linux without any special steps. On Windows, you will need to install Microsoft Visual C++ compiler for Python 2.7.

Download and install "Microsoft Visual C++ Compiler for Python 2.7" from http://aka.ms/vcpython27

.. note::
  You can also install the dependencies using already compiled Windows binaries packages. A good source of compiled Python packages is http://www.lfd.uci.edu/~gohlke/pythonlibs/. However, not all of the necessary packages for Kallithea are on this site and some are hard to find, so we will stick with using the compiler.

In a command prompt type (adapting paths if necessary)::

  cd C:\Kallithea\Env\Scripts
  activate

The prompt will change into "(Env) C:\\Kallithea\\Env\\Scripts" or similar
(depending of your folder structure). Then type::

  pip install kallithea

(Long step, please wait until fully complete)

Some warnings will appear. Don't worry, they are normal.


Step 8 - (Optional) Install git
-------------------------------
Mercurial being a python package, it was installed automatically when doing "pip install kallithea".

You need to install git manually if you want Kallithea to be able to host git repositories.

See http://git-scm.com/book/en/v2/Getting-Started-Installing-Git#Installing-on-Windows for instructions.


Step 9 - Configuring Kallithea
------------------------------

Steps taken from `<setup.html>`_

You have to use the same command prompt as in Step 7, so if you closed it, reopen it following the same commands (including the "activate" one).

When ready, type::

  cd C:\Kallithea\Bin
  paster make-config Kallithea production.ini

Then, you must edit production.ini to fit your needs (IP address, IP port, mail settings, database, etc.) NotePad++ (free) or similar text editors are recommended, as they handle well the EndOfLine character differences between Unix and Windows (http://notepad-plus-plus.org/).

For the sake of simplicity, run it with the default settings. After your edits (if any), in the previous Command Prompt, type::

  paster setup-db production.ini

(This time a NEW database will be installed. You must follow a different step to later UPGRADE to a newer Kallithea version)

The script will ask you for confirmation about creating a NEW database, answer yes (y)

The script will ask you for repository path, answer C:\\Kallithea\\Repos (or similar).

The script will ask you for admin username and password, answer "admin" + "123456" (or whatever you want)

The script will ask you for admin mail, answer "admin@xxxx.com" (or whatever you want)

If you make a mistake and the script doesn't end, don't worry: start it again.

If you decided not to install git, you will get errors about it that you can ignore.


Step 10 - Running Kallithea
---------------------------

In the previous command prompt, being in the C:\\Kallithea\\Bin folder, type::

  paster serve production.ini

Open your web server, and go to http://127.0.0.1:5000

It works!! :-)

Remark:
If it does not work the first time, Ctrl-C the CMD process and start it again. Don't forget the "http://" in Internet Explorer.


What this Guide does not cover:

- Installing Celery
- Running Kallithea as a Windows Service. You can investigate here:

  - http://pypi.python.org/pypi/wsgisvc
  - http://ryrobes.com/python/running-python-scripts-as-a-windows-service/
  - http://wiki.pylonshq.com/display/pylonscookbook/How+to+run+Pylons+as+a+Windows+service

- Using Apache. You can investigate here:

  - https://groups.google.com/group/rhodecode/msg/c433074e813ffdc4


Upgrading
:::::::::

Stop running Kallithea
Open a CommandPrompt like in Step 7 (cd to C:\Kallithea\Env\Scripts and activate) and type::

  pip install kallithea --upgrade
  cd \Kallithea\Bin

Backup your production.ini file now.

Then, run::

  paster make-config Kallithea production.ini

Look for changes and update your production.ini accordingly.

Then, update the database::

  paster upgrade-db production.ini

Full steps in `<upgrade.html>`_
