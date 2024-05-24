FROM python:3.12-bullseye as buildstage

WORKDIR /app
COPY . .

RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --only main \
    && pip uninstall -y poetry

FROM python:3.12-slim-bullseye

WORKDIR /app
COPY . .

COPY --from=buildstage /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=buildstage /usr/local/bin  /usr/local/bin

RUN pip install awslambdaric

RUN useradd --no-create-home --home-dir /app appuser && chown -R appuser /app
USER appuser

# Set runtime interface client as default command for the container runtime
ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
# Pass the name of the function handler as an argument to the runtime
CMD [ "lambda_function.handler" ]