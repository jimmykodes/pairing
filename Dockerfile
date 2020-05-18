FROM python:3.7

RUN apt-get update && apt-get install -yy gcc build-essential python-setuptools

ENV PYTHONUNBUFFERED 1

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

WORKDIR /app