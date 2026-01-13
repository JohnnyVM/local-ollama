# ---- build stage (needs nvcc) ----
FROM nvidia/cuda:12.2.2-devel-ubuntu22.04 AS build

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git cmake build-essential \
    libcurl4-openssl-dev ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/ggerganov/llama.cpp.git
WORKDIR /app/llama.cpp

# Make CUDA driver stub visible to the linker during build
RUN ln -sf /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1
ENV LIBRARY_PATH=/usr/local/cuda/lib64/stubs:${LIBRARY_PATH}
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64/stubs:${LD_LIBRARY_PATH}

RUN cmake -B build \
    -DGGML_CUDA=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_LIBRARY_PATH=/usr/local/cuda/lib64/stubs \
 && cmake --build build --config Release -j

# ---- runtime stage (smaller) ----
FROM nvidia/cuda:12.2.2-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    libcurl4 ca-certificates libgomp1 libcuda \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy server binary
COPY --from=build /app/llama.cpp/build/bin/llama-server /app/llama-server

# Copy shared libs that llama-server needs (mtmd, ggml, etc.)
COPY --from=build /app/llama.cpp/build/bin/*.so* /app/

# Ensure the loader can find libs in /app
ENV LD_LIBRARY_PATH=/app

EXPOSE 8080
ENTRYPOINT ["/app/llama-server"]
