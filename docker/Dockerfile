FROM alpine:latest

# install python3 and pip
ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools

# copy ja2mqtt installation package
RUN mkdir -p /opt/ja2mqtt/install
COPY files/ja2mqtt-*.tar.gz /opt/ja2mqtt/install

# install ja2mqtt
RUN cd /opt/ja2mqtt && \
  mkdir config && \
  mkdir logs && \
  pip install install/ja2mqtt-*.tar.gz && \
  rm -fr /opt/ja2mqtt/install

# copy default ja2mqtt configuration
COPY files/sample-config.yaml /opt/ja2mqtt/config/config.yaml
COPY files/ja2mqtt.yaml /opt/ja2mqtt/config

# create helper scripts
RUN echo -e "#!/bin/sh\n/usr/bin/ja2mqtt pub \$*">/usr/bin/pub && \
  chmod +x /usr/bin/pub

ENV JA2MQTT_CONFIG=config/config.yaml
ENV JA2MQTT_NO_ANSI=True
ENV JA2MQTT_DEBUG=False

# start the command on running the container
WORKDIR /opt/ja2mqtt
CMD [ "/usr/bin/ja2mqtt", "run", "-c", "config/config.yaml" ]
