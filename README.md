sdelib/ package
================
A light weight library that provides an interface to SD Elements RESTful API.

- apiclient: The base API provider for calls to SD Elements.
- interactive_plugin: This module provides the interactive experience needed for the SDE Lint tool and other similar usecases. This includes:
    - Password collection and retry
    - Application selection
    - Project selection
- conf_mgr: Configuration Manager provides support for parsing command line arguments, reading variables from config file, and allows for extended options to be defined for each usecase.

sdelint.py
================

A command line lint tool for SDElements that is capable of lightly scanning the source files and determining the contextually applicable tasks.