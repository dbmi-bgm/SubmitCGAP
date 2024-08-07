clean:
	make clean-python
	make clean-sphinx-build

clean-python:
	rm -rf *.egg-info

clean-sphinx-build:  # clean html output cache used for ReadTheDocs previews
	rm -rf docs/html/

clear-poetry-cache:  # clear poetry/pypi cache. for user to do explicitly, never automatic
	poetry cache clear pypi --all

configure:  # does any pre-requisite installs
	pip install poetry setuptools wheel

lint:
	flake8 submit_cgap

build:  # builds
	make configure
	poetry install

test:
	pytest -vv

retest:  # runs only failed tests from the last test run. (if no failures, it seems to run all?? -kmp 17-Dec-2020)
	pytest -vv --last-failed

update:  # updates dependencies
	poetry update

tag-and-push:  # tags the branch and pushes it
	@scripts/tag-and-push

preview-locally:  # build a ReadTheDocs preview from docs/source into docs/html
	sphinx-build -b html docs/source docs/html
	open docs/html/index.html

preview-locally-clean:  # clean build a ReadTheDocs preview from docs/source into docs/html
	make clean-sphinx-build
	make preview-locally

publish:  # publish using publish script from dcicutils.scripts
	poetry run publish-to-pypi

publish-for-ga:  # publish using publish script from dcicutils.scripts
	poetry run publish-to-pypi --noconfirm

help:
	@make info

info:
	@: $(info Here are some 'make' options:)
	   $(info - Use 'make configure' to install poetry, though 'make build' will do it automatically.)
	   $(info - Use 'make lint' to check style with flake8.)
	   $(info - Use 'make build' to install dependencies using poetry.)
	   $(info - Use 'make preview-locally' to build and a local doc tree and open it for preview.)
	   $(info - Use 'make publish' to publish this library, but only if auto-publishing has failed.)
	   $(info - Use 'make retest' to run failing tests from the previous test run.)
	   $(info - Use 'make test' to run tests with the normal options we use for CI/CD like GA.)
	   $(info - Use 'make update' to update dependencies (and the lock file))
	   $(info - Use 'make clear-poetry-cache' to clear the poetry pypi cache if in a bad state. (Safe, but later recaching can be slow.))
