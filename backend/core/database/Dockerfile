ARG TAG=16

FROM postgres:${TAG}

RUN mkdir /docker-entrypoint-init.d/ /opt/postgresql.conf.d \
    && chmod 777 /docker-entrypoint-init.d/ \
    && chmod 755 /opt/postgresql.conf.d \
    && chown postgres:postgres /opt/postgresql.conf.d

COPY ./config/configuration-ssl.sh /docker-entrypoint-initdb.d/
RUN chmod +x /docker-entrypoint-initdb.d/configuration-ssl.sh

COPY ./config/docker-before-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-before-entrypoint.sh

COPY ./config/extends-conf.sh /docker-entrypoint-initdb.d/
RUN chmod +x /docker-entrypoint-initdb.d/extends-conf.sh

# ssl.conf baked dans l'image — plus besoin de monter conf.d sur le VPS
COPY ./conf.d/ssl.conf /opt/postgresql.conf.d/ssl.conf

ENTRYPOINT [ "docker-before-entrypoint.sh" ]
CMD [ "postgres" ]