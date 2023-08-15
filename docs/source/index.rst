========
Overview
========

------------------------------------------
SubmitCGAP: remote file submitter for CGAP
------------------------------------------

.. image:: https://github.com/dbmi-bgm/SubmitCGAP/actions/workflows/main.yml/badge.svg
   :target: https://github.com/dbmi-bgm/SubmitCGAP/actions
   :alt: Build Status

.. image:: https://coveralls.io/repos/github/dbmi-bgm/SubmitCGAP/badge.svg
   :target: https://coveralls.io/github/dbmi-bgm/SubmitCGAP
   :alt: Coverage Percentage

.. image:: https://readthedocs.org/projects/submitcgap/badge/?version=latest
   :target: https://submitcgap.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

Description
===========

This is a tool for uploading files to CGAP.


System Requirements
===================

* Python 3.7, 3.8 or 3.9
* Pip (>=20.0.0)
* Virtualenv (>=16.0.0)


What To Do Next
===============

Advanced users who have already installed Python
can proceed to instructions for **Installing submitr**.

Less experienced users should start with instructions
for **Installing Prerequisites**,
which will introduce some basics for working with the terminal
and installing the dependencies to run this package.

Although at some point **submitr** might offer the ability to
use **rclone** invisibly, for now it uses **awscli** only.
But we do now experimentally offer some instructions for
**Using rclone instead** at the end of this documentation
in case that's an option you want to pursue.

.. toctree::
  :maxdepth: 4

  self
  installing_prerequisites
  installation
  usage
  submit_cgap
  rclone_instead
