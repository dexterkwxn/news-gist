FROM python:3.9 as base

WORKDIR /code

# 
COPY ./microservices/requirements.txt /code/requirements.txt

# 
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Build Golang binary
FROM golang:latest as builder

WORKDIR /app

COPY ./microservices/newscat .

RUN go mod download

RUN go build -o /newscat
#
FROM base

WORKDIR /code

# Copy the Golang binary into main container
COPY --from=builder /newscat /code

RUN chmod +x /code/newscat

ENV PATH="/code:${PATH}"

# 
COPY ./microservices/main.py /code/main.py
COPY ./microservices/settings.py /code/settings.py

# Setup cronjob
RUN apt-get update && apt-get install -y cron

COPY ./microservices/ms_cron /etc/cron.d/ms_cron

RUN crontab /etc/cron.d/ms_cron

#
EXPOSE 80

# 
CMD ["sh", "-c", "python main.py && cron -f"]


