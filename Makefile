.PHONY: cloc lint install

SRC_DIR=./wke
TEST_DIR=./tests

all: test lint install

clean:
	rm -rf ${SRC_DIR}/__pycache__

cloc:
	cloc ${SRC_DIR}

lint:
	mypy ${SRC_DIR} ${TEST_DIR}
	flake8 ${SRC_DIR} ${TEST_DIR}

test:
	pytest tests

package:
	python3 -m build

install:
	pip install .

container: docker-test/Dockerfile
	cd docker-test && docker buildx build --platform linux/amd64 -t wke-test-container . 
    
