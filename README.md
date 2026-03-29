[![datagrowth workflow](https://github.com/fako/datagrowth/actions/workflows/postgres.yml/badge.svg)](https://github.com/fako/datagrowth/actions) [![PyPI pyversions](https://img.shields.io/pypi/pyversions/datagrowth.svg)](https://pypi.python.org/pypi/datagrowth/) [![GPLv3 license](https://img.shields.io/badge/License-LGPLv3-blue.svg)](https://github.com/fako/datagrowth/blob/master/LICENSE)

DATAGROWTH
==========

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


Installation
------------

You can install Datagrowth by running

```bash
pip install datagrowth
```

And then add ``datagrowth.django.apps.DatagrowthConfig`` to ``INSTALLED_APPS``.


Getting started
---------------

Currently there are two major use cases.
The **Resources** provide a way to uniformly gather data from very different sources.
**Configurations** are a way to store and transfer key-value pairs,
which your code can use to act on different contexts.

Follow these guides to get an idea how you can use Datagrowth:

* [Resources](https://fako.github.io/datagrowth/latest/resources/index.html)
* [Configurations](https://fako.github.io/datagrowth/latest/configuration/index.html)


Running the tests
-----------------

There is a Django mock project inside the tests directory of the repository.
In it are a lot of tests to demonstrate how Datagrowth and Django can work together,
as well as to assure that everything functions as designed.

Apart from the Django tests there is also a pytest suite, which checks lower level Datagrowth functionality.
In the future it will be feasible to use Datagrowth without Django in smaller prototype projects.

You can run all tests by running this inside the repo root:

```bash
invoke test.run
```

Alternatively you can execute the tests against multiple Python/Django/database versions by running:

```bash
tox
```
