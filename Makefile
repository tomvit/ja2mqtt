# Makefile for ja2mqtt

help:
	@echo "make <target>"
	@echo "build	build ja2mqtt package in dist directory."
	@echo "image    build local dev Docker image"
	@echo "clean	clean all temporary directories."
	@echo "format	format the code using black."
	@echo "require	create requirements.txt from setup.py"
	@echo ""

build:
	python3 setup.py egg_info sdist

check:
	pylint --python-version=3.6 ja2mqtt

image:
	rm dist/*
	python3 setup.py egg_info sdist
	rm -fr docker/files && mkdir -p docker/files
	cp dist/ja2mqtt-*.tar.gz docker/files
	cp config/sample-config.yaml docker/files
	cp config/ja2mqtt.yaml docker/files
	cd docker && docker build . --platform linux/arm64 -t tomvit/ja2mqtt-dev:latest

clean:
	rm -fr build
	rm -fr dist
	rm -fr ja2mqtt/*.egg-info
	rm -fr docs/_build

html:
	cd docs && make clean && make html

format:
	black ja2mqtt

require:
	bin/requirements-setup-py.sh
