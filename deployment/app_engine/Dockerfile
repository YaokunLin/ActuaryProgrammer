FROM python3

ENV PYTHONUNBUFFERED 1

ADD requirements/requirements.txt /app/requirements.txt
RUN pip3 install --upgrade pip && pip3 install -r /app/requirements.txt

RUN python3 -c 'from django.core.management import utils; print(utils.get_random_secret_key())