.PHONY: docs

test:
	tox -- $(filter)

test-deprecations:
	cd tests && python -Wa manage.py test

docs:
	cd docs && make html
