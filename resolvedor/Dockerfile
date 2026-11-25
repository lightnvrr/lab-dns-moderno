FROM debian:bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends unbound tcpdump ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /var/lib/unbound

# Âncora da raiz com as duas KSKs (20326 = KSK-2017 e 38696 = KSK-2024).
# Copiada do pacote dns-root-data; o Unbound mantém o arquivo atualizado (RFC 5011).
COPY root.key /var/lib/unbound/root.key
RUN chown -R unbound:unbound /var/lib/unbound

# -d: fica em primeiro plano (necessário em contêiner)
CMD ["unbound", "-d", "-c", "/etc/unbound/lab/unbound.conf"]
