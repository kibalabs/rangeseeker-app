FROM python:3.12.11-slim

# NOTE(krishan711): gcc, libc6-dev for ed25519-blake2b lib
RUN apt-get update && apt-get install --yes --no-install-recommends make git gcc libc6-dev

WORKDIR /app
COPY makefile .

COPY pyproject.toml .
# COPY uv.lock .
RUN make install

COPY . .

EXPOSE 5000
CMD ["make", "start-prod"]
