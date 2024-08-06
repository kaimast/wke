.PHONY: cloc lint install

SRC_DIR=./wke

all: test lint install

clean:
	rm -rf ${SRC_DIR}/__pycache__

cloc:
	cloc ${SRC_DIR}

lint:
	pylint ${SRC_DIR}
	mypy ${SRC_DIR}

test:
	pytest tests

package:
	python3 -m build

install:
	pip install .
