# The base image. Authors build FROM this and add one Python file.
#
# It carries the contract, a raster reader, a STAC client, and the entrypoint that speaks the platform's protocol,
# so an author never writes JSON handling, argument parsing or exit codes, and a conformant image is the default rather than an achievement
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

COPY pyproject.toml ./
COPY geotriage/ ./geotriage/
RUN pip install --no-cache-dir '.[dev]'

# Where an author's code goes. Exactly one of GEOTRIAGE_MODEL or GEOTRIAGE_PROVIDER names the class to load, and thereby what this image is
ENV PYTHONPATH=/src
ENV GEOTRIAGE_MODEL=""
ENV GEOTRIAGE_PROVIDER=""

# Models do their own I/O through mounted files; they need no network and no credentials, and the platform runs them with both taken away
ENTRYPOINT ["python", "-m", "geotriage.runtime"]
CMD ["describe"]
