=====================
Installing SubmitCGAP
=====================

SubmitCGAP with Docker
======================

Previously, using SubmitCGAP required doing a manual installation on the machine
of the submitter. Now, we provide a Docker image for more convenient ease of use,
eliminating the need for setting up a lot of system level dependencies that are
beyond the scope of need for this application.

The only system level requirement is ``Docker`` or ``podman``. Note that
podman_ is docker compatible via command line. Note that you may need to install ``make``
as well if your system does not come with it.

.. _podman: https://podman.io/whatis.html

Step 1: Installation
====================

Option 1: Build the image locally
---------------------------------

Use ``make build-docker-local`` to build the SubmitCGAP Docker image. Once complete,
``make exec-docker-local`` will open a bash session into a container that is pre-configured
to run SubmitCGAP.

Option 2: Pull Image from Dockerhub
---------------------------------

TODO: put a version of the image on Dockerhub once this is released. Provide make targets for pulling
and exec'ing into it.

Step 2: Add submission files to submission_files/ directory
===========================================================

Create a directory in the repository top level called ``submission_files`` and copy all submission
files into this directory. This directory will be mounted to the SubmitCGAP container so you can
run commands that interact with the submission files within the container.

Step 3: Configure Credentials
=============================

TODO: provide this.

==================================
Previous Installation Instructions
==================================

Manual installation instructions (previously the only instructions) are below.
Note that the Dockerfile in effect provides precise installation instructions on a Debian-based system.

System Requirements
===================

* Python 3.6 or 3.7
* ``pip`` (version 20 or higher)
* ``virtualenv`` (version 16 or higher)


Setting Up a Virtual Environment (OPTIONAL)
===========================================

This action is optional.
If you do not create a virtual environment, Poetry will make one for you.
But there are still good reasons you might want to make your own, so here
are three ways to do it:

* If you have virtualenvwrapper that knows to use Python 3.6::

   mkvirtualenv myenv

* If you have virtualenv but not virtualenvwrapper,
  and you have python3.6 in your ``PATH``::

   virtualenv myenv -p python3.6

* If you are using ``pyenv`` to control what environment you use::

   pyenv exec python -m venv myenv


Activating a Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You should execute all actions related to this repository
from within a virtual environment.

To activate a virtual environment::

   source myenv/bin/activate


Deactivating a Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It's rarely necessary to deactivate a virtual environment.
One is automatically deactivated if you enter another,
and normally they have very little effect on other actions you might
take. So it's normally safe to just leave them activated.

However, if you want to deactivate an active environment, just do::

   deactivate


Installing in a Virtual Environment
==========================================

Installation for Developers
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are a developer, you'll be installing with Poetry.
Once you have created a virtual environment, or have decided to just let Poetry handle that,
go ahead with the installation. To do that, make sure your current directory is the source repository and do::

   make build


.. tip::

   Poetry is the substrate that our build scripts rely on.
   You won't be calling it directly, but ``make build`` will call it.


Installation for End Users (non-Developers)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you're an end user,
once you have created and activated the virtual environment,
just do::

   pip install submit_cgap


Setting Up Credentials
======================

Credentials can be placed in the file ``~/.cgap-keys.json``. The file format is::

   {"envname1": {"key": ..., "secret": ..., "server": ...}, "envname2": ..., ...}

   The envname to use for production is "fourfront-cgap".
   The envname to use for local debugging is "fourfront-cgaplocal".
   So a typical file might look like:

   {
       "fourfront-cgap": {
           "key": "some_key",
           "secret": "some_secret",
           "server": "https://cgap.hms.harvard.edu"
       },
       "fourfront-local": {
           "key": "some_other_key",
           "secret": "some_other_secret",
           "server": "http://localhost:8000"
       },
       "fourfront-cgapdev": {
           "key": "some_third_key",
           "secret": "some_third_secret",
           "server": "http://fourfront-cgapdev.9wzadzju3p.us-east-1.elasticbeanstalk.com/"
       }
   }

This file should _not_ be readable by others than yourself.
Set its permissions accordingly by using ``chmod 600``,
which sets the file to be readable and writable only by yourself,
and to give no one else (but the system superuser) any permissions at all::

   $ ls -dal ~/.cgap-keys.json
   -rw-r--r--  1 jqcgapuser  staff  297 Sep  4 13:14 /Users/jqcgapuser/.cgap-keys.json

   $ chmod 600 ~/.cgap-keys.json

   $ ls -dal ~/.cgap-keys.json
   -rw-------  1 jqcgapuser  staff  297 Sep  4 13:14 /Users/jqcgapuser/.cgap-keys.json


