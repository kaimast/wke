.PHONY: cloc lint install

SRC_DIR=./wke

all: test lint install

clean:
	rm -rf ${SRC_DIR}/__pycache__

cloc:
	cloc ${SRC_DIR}

lint:
	mypy ${SRC_DIR}
	pylint ${SRC_DIR} --disable=R0917

test:
	pytest tests

package:
	python3 -m build

install:
	pip install .
