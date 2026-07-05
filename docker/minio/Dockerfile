# Railway deploys Docker-image services with no way to override the start
# command via the CLI (only the dashboard/GraphQL API can set a "custom
# start command" on a bare-image service). The official minio/minio image's
# default entrypoint needs `server /data --console-address ":9001"` as
# arguments or it just prints usage and exits — this wrapper bakes that
# command into the image itself so no per-service dashboard setting is
# needed, the same way docker/docker-compose.yml already runs it locally.
FROM minio/minio:latest

CMD ["server", "/data", "--console-address", ":9001"]
