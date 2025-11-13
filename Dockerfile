FROM python:3.11-slim

# Install PostgreSQL client and git for the build process
RUN apt-get update && apt-get install -y postgresql-client git && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /code/

# Capture git information at build time if .git directory exists
# This runs during image build, not at runtime, so git info is baked into the image
RUN if [ -d .git ]; then \
      git rev-parse --short HEAD > /code/.git_commit && \
      git rev-parse --abbrev-ref HEAD > /code/.git_branch; \
    else \
      echo "unknown" > /code/.git_commit && \
      echo "unknown" > /code/.git_branch; \
    fi

# Copy the new entrypoint script and make it executable
COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

EXPOSE 8000

# Set the entrypoint to our script
ENTRYPOINT ["/entrypoint.sh"]