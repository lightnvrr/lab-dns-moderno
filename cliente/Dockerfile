FROM debian:bookworm-slim

# dig/delv (bind9-dnsutils), dnssec-keygen/signzone (bind9-utils), kdig (knot-dnsutils),
# captura de pacotes, OpenSSL para o certificado e Python para a medição
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      bind9-dnsutils bind9-utils knot-dnsutils tcpdump iproute2 traceroute \
      openssl ca-certificates curl python3 python3-pip \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

WORKDIR /lab
