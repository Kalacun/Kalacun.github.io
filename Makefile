PYTHON ?= python3

.PHONY: build check publish preview

build:
	$(PYTHON) tools/build.py

check:
	$(PYTHON) tools/build.py --check
	$(PYTHON) -m unittest discover -s tools -p 'test_*.py' -v

publish: check
	$(PYTHON) tools/build.py --publish

preview: build
	$(PYTHON) -m http.server 8000 --bind 127.0.0.1
