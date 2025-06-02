FROM public.ecr.aws/sam/build-python3.10@sha256:e78695db10ca8cb129e59e30f7dc9789b0dbd0181dba195d68419c72bac51ac1 AS uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_PREFERENCE=only-system
ENV UV_FROZEN=true

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    pip install uv && \
    uv sync --frozen --no-install-project --no-dev --no-editable

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

RUN mkdir -p /root/.local

FROM public.ecr.aws/sam/build-python3.10@sha256:e78695db10ca8cb129e59e30f7dc9789b0dbd0181dba195d68419c72bac51ac1

ENV PATH="/app/.venv/bin:$PATH:/usr/sbin"

RUN yum update -y && \
    yum install -y lsof curl tar openssl && \
    yum clean all -y && \
    rm -rf /var/cache/yum && \
    groupadd --force --system app && \
    useradd app -g app -d /app && \
    chmod o+x /root

# Install kubectl (latest stable)
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl

# Install helm (latest stable)
RUN curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

COPY --from=uv --chown=app:app /root/.local /root/.local
COPY --from=uv --chown=app:app /app/.venv /app/.venv

COPY ./docker-healthcheck.sh /usr/local/bin/docker-healthcheck.sh

USER app

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD [ "docker-healthcheck.sh" ]
ENTRYPOINT ["helm-mcp-server"]
