.. Data Growth documentation master file, created by
   sphinx-quickstart on Wed Dec 17 18:26:35 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Data Growth's documentation
===========================

Data Growth is a lightweight Extract, Transform and Load (ETL) library,
that helps to connect your software to external data sources.

These data sources can be API's, terminal commands or LLM's.
Datagrowth is the bridge between all that data and your application logic.
Because data sources and their outputs can be described uniformly in Python,
using Datagrowth prevents vendor lock-in to specific data sources.
It can also save costs, because it will re-use data sources like LLM responses whenever possible.

Datagrowth is mainly used within Django projects, where the data can be stored inside Django models.
Use the different processors to extract and transform data,
before loading it into your models exactly how your project needs.
When using Django Restframework you can also share the loaded data easily over a REST API to other devices or services.
Datagrowth also provides classes to set this up quickly.

Contents
--------

.. toctree::
   :maxdepth: 2

   resources/index
   configuration/index
   processors/index
   utils/index
   reference
