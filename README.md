[![Build Status](https://travis-ci.com/fako/datagrowth.svg?branch=master)](https://travis-ci.com/fako/datagrowth)

DATAGROWTH
==========

Data Growth is a Django application that helps to gather data in an organized way. With it you can declare pipelines
for the data gathering and preprocessing as well as pipelines for filtering and redistribution.


Installation
------------

You can install Datagrowth with your Django application by running

```bash
pip install datagrowth
```


Getting started
---------------

Currently there are two major use cases.
The **Resources** provide a way to uniformly gather data from very different sources.
**Configurations** are a way to store and transfer key-value pairs,
which your code can use to act on different contexts.

Follow these guides to get an idea how you can use Datagrowth:

* [Resources](https://data-scope.com/datagrowth/resources/)
* [Configurations](https://data-scope.com/datagrowth/configuration/)


Running the tests
-----------------

There is a Django mock project inside the tests directory of the repository.
You can run these tests by running this inside that directory:

```bash
python manage.py test
```  

Alternatively you can execute the tests against multiple Django versions by running:

```bash
tox
```
