#!/bin/bash

curl -X POST "https://poc-revisaolaudo-api.onrender.com/neomed/api/revisaolaudo" \
  -H "Content-Type: application/json" \
  -H "x-api-key: 4fa574a9dc0d621b" \
  -d @payload.json