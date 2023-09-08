FROM node:12.13-alpine AS static-build
RUN apk --no-cache add \
    g++ make python
WORKDIR /opt/scaife-viewer/src/
COPY package.json package-lock.json ./
RUN npm ci
COPY webpack.config.js babel.config.js .eslintrc.json ./
COPY ./static static
COPY ./test test

ARG FORCE_SCRIPT_NAME
RUN npm run lint
RUN npm run unit
RUN npm run build

FROM python:3.9-alpine AS python-build
WORKDIR /opt/scaife-viewer/src/
RUN pip --no-cache-dir --disable-pip-version-check install virtualenv
ENV PATH="/opt/scaife-viewer/bin:${PATH}" VIRTUAL_ENV="/opt/scaife-viewer"
COPY requirements.txt /opt/scaife-viewer/src/
RUN pip install pip wheel --upgrade
RUN set -x \
    && virtualenv /opt/scaife-viewer \
    && apk --no-cache add \
        build-base curl git libffi-dev libxml2-dev libxslt-dev postgresql-dev linux-headers \
    && pip install -r requirements.txt
# TODO: Move PyGithub dependency as an extra installable
# for scaife-viewer-core
RUN pip install flake8 flake8-quotes isort PyGithub

FROM python:3.9-alpine AS python-source
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /opt/scaife-viewer/src/
ENV PATH="/opt/scaife-viewer/bin:${PATH}" VIRTUAL_ENV="/opt/scaife-viewer"
ENV SECRET_KEY="foo"
WORKDIR /opt/scaife-viewer/src/
COPY --from=static-build /opt/scaife-viewer/src/static/dist /opt/scaife-viewer/src/static/dist
COPY --from=static-build /opt/scaife-viewer/src/static/stats /opt/scaife-viewer/src/static/stats
COPY --from=python-build /opt/scaife-viewer/ /opt/scaife-viewer/
RUN apk --no-cache add so:libc.musl-x86_64.so.1 libgcc so:libpq.so.5 curl bash
COPY . .
RUN flake8 sv_pdl
RUN isort -c **/*.py
RUN python manage.py collectstatic --noinput
CMD gunicorn --log-file=- --preload sv_pdl.wsgi
