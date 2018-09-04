FROM frolvlad/alpine-oraclejdk8:cleaned

RUN apk add --update --no-cache bash python3 maven sudo git docker openrc zip
RUN pip3 install docker pyyaml docker-compose

