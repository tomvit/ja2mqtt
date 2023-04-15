# Makefile for ja2mqtt
# uses version from git with commit hash

help:
	@echo "make <target>"
	@echo "build	build ja2mqtt."
	@echo "clean	clean all temporary directories."
	@echo ""

build:
	python setup.py egg_info sdist

check:
	pylint ja2mqtt

clean:
	rm -fr build
	rm -fr dist
	rm -fr ja2mqtt/*.egg-info

format:
	black ja2mqtt
