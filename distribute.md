# Notes on distribution

This file is a short summary of the [packaging projects documentation](https://packaging.python.org/tutorials/packaging-projects/).

To distribute this python package first make sure that ```tox``` is not raising any errors.
By running ```tox``` in the root of this repository.

Then run the following to create distribution artefacts inside the ```dist``` folder.

```bash
python3 setup.py sdist bdist_wheel
```

Now upload the generated artefacts with

```bash
twine upload dist/*
```
