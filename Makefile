# Makefile for ja2mqtt
# uses version from git with commit hash

help:
	@echo "make <target>"
	@echo "build	build ja2mqtt."
	@echo "clean	clean all temporary directories."
	@echo ""

build:
	python3 setup.py egg_info sdist

check:
	pylint ja2mqtt

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

format:
	black ja2mqtt
