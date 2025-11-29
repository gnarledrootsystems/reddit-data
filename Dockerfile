FROM python:latest

RUN useradd -ms /bin/sh -u 1001 app
USER app

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY --chown=app:app . /app

CMD ["python", "-u", "./scripts/main.py"]