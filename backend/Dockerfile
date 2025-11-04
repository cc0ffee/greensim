FROM golang:1.23-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download && go mod tidy

COPY . .

RUN go mod tidy && go build -o main .

FROM alpine:edge

COPY --from=builder /app/main /usr/local/bin/main

EXPOSE 8080
CMD ["main"]
