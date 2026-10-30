FROM alpine:3.22
RUN apk add --no-cache openssh-client netcat-openbsd
COPY entrypoint.sh /usr/local/bin/tunnel
ENTRYPOINT ["sh", "/usr/local/bin/tunnel"]
