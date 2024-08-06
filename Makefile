.PHONY: cloc lint install

all: test lint install

cloc:
	cloc ./wke

lint:
	pylint ./wke
	mypy ./wke

test:
	pytest ./wke

install:
	pip install .
