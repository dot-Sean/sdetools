Requirements
================
- Python 2.4+

This project is intended to be ultra lightweight, and portable.
The only requirement is to have Python 2.4+ installed.

The console usage
================

__sde.py__

The command line tool to run SD Elements integration modules. Use 'python sde.py help' to see usage and 'python sde.py help <cmd>' to see usage for specific module.

The package usage
================
import sdetools

sdetools.call('api_proxy', {'api_func': 'get_applications'})

SDE Library (sdelib/)
================
A light weight library that provides an interface to SD Elements RESTful API.

- __apiclient__: The base API provider for calls to SD Elements.
- __interactive_plugin__: This module provides the interactive experience needed for the SDE Lint tool and other similar usecases. This includes:
    - Password collection and retry
    - Application selection
    - Project selection
- __conf_mgr__: Configuration Manager provides support for parsing command line arguments, reading variables from config file, and allows for extended options to be defined for each usecase.

