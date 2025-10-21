FROM golang:1.25-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod tidy

COPY . .

RUN go build -o main .

FROM alpine:edge

COPY --from=builder /app/main /usr/local/bin/main

EXPOSE 8080
CMD ["main"]
