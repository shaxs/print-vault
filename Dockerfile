FROM python:3.11-slim

# Install PostgreSQL client for the pg_isready command
RUN apt-get update && apt-get install -y postgresql-client

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /code/

# Copy the new entrypoint script and make it executable
COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

EXPOSE 8000

# Set the entrypoint to our script
ENTRYPOINT ["/entrypoint.sh"]