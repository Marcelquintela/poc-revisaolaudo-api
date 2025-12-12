# carrega variáveis do .env no ambiente do Bash
set -o allexport
source .env
set +o allexport


curl -X POST "http://poc-revisaolaudo-api.onrender.com/neomed/api/revisaolaudo" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY_REVISAO_LAUDO" \
  -d @payload.json