.PHONY: cloc lint install

SRC_DIR=./wke

all: test lint install

clean:
	rm -rf ${SRC_DIR}/__pycache__

cloc:
	cloc ${SRC_DIR}

lint:
	mypy ${SRC_DIR}
	flake8 ${SRC_DIR}

test:
	pytest tests

package:
	python3 -m build

install:
	pip install .
