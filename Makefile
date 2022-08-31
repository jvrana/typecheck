PIP=pip3

.PHONY: docs export  # necessary so it doesn't look for 'docs/makefile html'

init:
	curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python
	poetry install
	poetry run pre-commit install


clean:
	rm -rf dist
	rm -rf pip-wheel-metadata
	rm -rf docs/_build
	rm -rf .pytest_cache
	find . \( -name '__pycache__' -or -name '*.pyc' \) -delete
	rm -rf .tox

build:
	poetry build

publish: build
	poetry publish
	#python -m twine upload --repository gitlab dist/* --cert ${CERT}  --verbose


docs:
	cd docs
	make