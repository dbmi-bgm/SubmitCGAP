clean:
	rm -rf *.egg-info

configure:  # does any pre-requisite installs
	pip install poetry

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

publish:
	scripts/publish

publish-for-ga:
	scripts/publish --noconfirm

help:
	@make info

info:
	@: $(info Here are some 'make' options:)
	   $(info - Use 'make configure' to install poetry, though 'make build' will do it automatically.)
	   $(info - Use 'make lint' to check style with flake8.)
	   $(info - Use 'make build' to install dependencies using poetry.)
	   $(info - Use 'make publish' to publish this library, but only if auto-publishing has failed.)
	   $(info - Use 'make retest' to run failing tests from the previous test run.)
	   $(info - Use 'make test' to run tests with the normal options we use for CI/CD like GA.)
	   $(info - Use 'make update' to update dependencies (and the lock file))
