# pull official base image
FROM python:3.11.4-slim-buster

# create directory for the app user
RUN mkdir -p /home/app

# install system dependencies
RUN apt-get update
RUN apt-get install -y netcat
RUN apt-get -y install libpq-dev gcc

RUN apt-get update \
  # dependencies for building Python packages
  && apt-get install -y build-essential \
  # psycopg2 dependencies
  && apt-get install -y libpq-dev \
  # Translations dependencies
  && apt-get install -y gettext \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# create the app user
RUN addgroup --system app && adduser --system --group app

# create the appropriate directories
ENV HOME=/home/app
ENV APP_HOME=/home/app/web
RUN mkdir $APP_HOME
WORKDIR $APP_HOME

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# copy entrypoint.prod.sh
COPY ./entrypoint.sh /usr/local/bin/
RUN sed -i 's/\r$//g' /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

COPY ./start.sh /usr/local/bin/
RUN sed -i 's/\r$//g' /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

COPY ./start-celeryworker.sh /usr/local/bin/
RUN sed -i 's/\r$//g' /usr/local/bin/start-celeryworker.sh
RUN chmod +x /usr/local/bin/start-celeryworker.sh

# copy project
COPY . $APP_HOME

# chown all the files to the app user
RUN chown -R app:app $APP_HOME

# change to the app user
USER app

# run entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]