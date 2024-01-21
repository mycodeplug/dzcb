FROM python:3

ENV UID=1000
ENV GID=1000

RUN groupadd --gid ${GID} app && \
    useradd --uid ${UID} --gid ${GID} -m --home /app app

COPY . /app/dzcb
RUN chown -R ${UID}:${GID} /app/dzcb

WORKDIR /app
USER app

RUN pip install --user /app/dzcb && \
    rm -rf /app/dzcb

ENTRYPOINT [ "python", "-m", "dzcb" ]
CMD []
