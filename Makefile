.PHONY: docs

test:
	tox -- $(filter)

docs:
	cd docs && make html
