FROM alpine:latest

ENV LANG en_US.utf8

# Install system packages
RUN apk update \
    && apk upgrade \
    && apk --no-cache add python3 \
    && apk --no-cache add etcd etcd-ctl --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing \
    && rm -rf /var/cache/apk/*

# Install Python dependencies for docker entrypoint
RUN pip3 install docker-cluster-controller requests

# Copy docker entrypoint
COPY docker-entrypoint.py /usr/local/bin/docker-entrypoint.py
RUN chmod 544 /usr/local/bin/docker-entrypoint.py

VOLUME /data
EXPOSE 2379 2380 4001

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.py"]
CMD ["--start"]
