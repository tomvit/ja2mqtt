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

image:
	python setup.py egg_info sdist
	mkdir -p docker/files
	cp dist/ja2mqtt-2.0.0.tar.gz docker/files
	cp config/sample-config.yaml docker/files
	cp config/ja2mqtt.yaml docker/files
	cd docker && docker build . -t tomvit/ja2mqtt:2.0.0

clean:
	rm -fr build
	rm -fr dist
	rm -fr ja2mqtt/*.egg-info

format:
	black ja2mqtt
