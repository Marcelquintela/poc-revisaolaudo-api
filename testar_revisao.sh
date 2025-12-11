#!/bin/bash

# carrega variáveis do .env no ambiente do Bash
set -o allexport
source .env
set +o allexport

curl -X POST "http://127.0.0.1:8000/neomed/api/revisaolaudo" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY_REVISAO_LAUDO" \
  -d @payload.json
