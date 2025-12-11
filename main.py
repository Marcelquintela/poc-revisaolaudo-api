"""
API de Revisão de Laudo – Neomed
- FastAPI + Pydantic v2
- Proteção via API Key (header x-api-key)
- Endpoint: POST /neomed/api/revisaolaudo
- Health: GET /health
"""

import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Security, Depends, status
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from dotenv import load_dotenv

# Carrega .env quando executar localmente (no Render as envs são definidas no painel)
load_dotenv()

# -------------------------------------------------------------------
# CONFIGURAÇÃO DA API KEY
# -------------------------------------------------------------------
API_KEY_HEADER_NAME = "x-api-key"
API_KEY_EXPECTED = os.getenv("API_KEY_REVISAO_LAUDO")  # definir no .env (local) ou nas env vars do Render

api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Valida chave recebida no header x-api-key.
    - Se a chave esperada não estiver configurada no servidor -> 500
    - Se a chave enviada for inválida/ausente -> 403
    """
    if API_KEY_EXPECTED is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chave de API não configurada no servidor."
        )

    if api_key is None or api_key != API_KEY_EXPECTED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chave de API inválida ou ausente."
        )

    return api_key


# -------------------------------------------------------------------
# MODELOS (Pydantic v2)
# -------------------------------------------------------------------
class RequestingPhysician(BaseModel):
    name: str
    councilCode: str
    professionalRegistrationNumber: str
    councilStateCode: str
    phone: str
    email: EmailStr
    cpf: str

    @field_validator(
        "name", "councilCode", "professionalRegistrationNumber",
        "councilStateCode", "phone", "cpf",
        mode="before"
    )
    @classmethod
    def not_empty(cls, v):
        """Valida campos obrigatórios não nulos/vazios."""
        if v is None:
            raise ValueError("Campo obrigatório não pode ser nulo.")
        s = str(v).strip()
        if not s:
            raise ValueError("Campo obrigatório não pode ser vazio.")
        return s

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v):
        """Validação simples: somente dígitos e 11 caracteres."""
        if not str(v).isdigit():
            raise ValueError("CPF deve conter apenas dígitos.")
        if len(str(v)) != 11:
            raise ValueError("CPF deve ter 11 dígitos.")
        return v


class AssignedProfessional(BaseModel):
    professionalCode: str
    professionalName: str

    @field_validator("professionalCode", "professionalName", mode="before")
    @classmethod
    def not_empty(cls, v):
        if v is None:
            raise ValueError("Campo obrigatório não pode ser nulo.")
        s = str(v).strip()
        if not s:
            raise ValueError("Campo obrigatório não pode ser vazio.")
        return s


class ReviewReasons(BaseModel):
    lateralityError: bool
    orthographicError: bool
    diagnosticDivergence: bool
    wrongExamTopography: bool
    measurementDivergence: bool
    other: bool
    otherDescription: Optional[str] = None

    @model_validator(mode="after")
    def validate_reasons(self):
        """Regras:
         - pelo menos um booleano deve ser true
         - se other = true, otherDescription é obrigatório
        """
        if not any([
            self.lateralityError,
            self.orthographicError,
            self.diagnosticDivergence,
            self.wrongExamTopography,
            self.measurementDivergence,
            self.other,
        ]):
            raise ValueError("Pelo menos um motivo em 'reviewReasons' deve ser verdadeiro.")

        if self.other:
            if self.otherDescription is None or not str(self.otherDescription).strip():
                raise ValueError("Quando 'other' = true, 'otherDescription' é obrigatório.")
        return self


class ReviewRequest(BaseModel):
    accessionNumber: str
    requestingPhysician: RequestingPhysician
    freeAssignmentFlag: bool
    assignedProfessional: Optional[AssignedProfessional] = None
    reviewJustification: str
    reviewReasons: ReviewReasons

    @field_validator("accessionNumber", "reviewJustification", mode="before")
    @classmethod
    def not_empty(cls, v):
        if v is None:
            raise ValueError("Campo obrigatório não pode ser nulo.")
        s = str(v).strip()
        if not s:
            raise ValueError("Campo obrigatório não pode ser vazio.")
        return s

    @model_validator(mode="after")
    def validate_rules(self):
        """Regras de negócio adicionais."""
        if not self.accessionNumber.strip():
            raise ValueError("accessionNumber é obrigatório.")

        if not self.reviewJustification.strip():
            raise ValueError("reviewJustification é obrigatória.")

        if self.freeAssignmentFlag is False and self.assignedProfessional is None:
            raise ValueError("Quando freeAssignmentFlag=false, assignedProfessional é obrigatório.")

        return self


class ReviewResponse(BaseModel):
    status: str
    message: str
    receivedItems: int


# -------------------------------------------------------------------
# FASTAPI APP
# -------------------------------------------------------------------
app = FastAPI(
    title="API Revisão de Laudos – Neomed",
    version="1.0.0",
    description="Serviço para registro de solicitações de revisão de laudos."
)


@app.get("/health")
async def health_check():
    """Endpoint de health para monitoramento."""
    return {"status": "UP", "service": "revisaolaudo"}


@app.post(
    "/neomed/api/revisaolaudo",
    response_model=ReviewResponse,
    summary="Registrar solicitação de revisão de laudo"
)
async def create_review_request(
    # payload: List[ReviewRequest], # era lista passou a ser unico objeto
    payload: ReviewRequest,
    api_key: str = Depends(get_api_key)
):
    """
    Recebe uma lista de solicitações de revisão de laudos.
    - Validação de api_key via header x-api-key (Dependência get_api_key).
    """
    if not payload:
        raise HTTPException(status_code=400, detail="A lista de solicitações não pode estar vazia.")

    # Aqui a lógica de persistência ou envio para fila seria aplicada.
    return ReviewResponse(
        status="ACK",
        message="Solicitação(ões) recebida(s) com sucesso.",
        receivedItems=len(payload)
    )
