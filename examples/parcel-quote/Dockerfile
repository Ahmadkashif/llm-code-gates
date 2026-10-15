FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
WORKDIR /app
COPY quotesvc/ quotesvc/
RUN useradd --uid 10001 --create-home app
USER 10001
ENV HOST=0.0.0.0 PORT=8080
EXPOSE 8080
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/up', timeout=2)"
CMD ["python", "-m", "quotesvc.app"]
