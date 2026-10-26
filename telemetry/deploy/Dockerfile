FROM rust:1.93-bookworm AS build
WORKDIR /source
COPY Cargo.toml Cargo.lock ./
COPY pow-kernel ./pow-kernel
COPY pow-spec ./pow-spec
COPY telemetry ./telemetry
# Cargo resolves the root package even when building only the collector.
RUN mkdir src && printf 'fn main() {}\n' > src/main.rs
RUN cargo build --locked --release -p seine-telemetry --features server

FROM debian:bookworm-slim
COPY --from=build /source/target/release/seine-telemetry /usr/local/bin/seine-telemetry
USER 65534:65534
EXPOSE 9080
ENTRYPOINT ["/usr/local/bin/seine-telemetry"]
