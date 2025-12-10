"""
Módulo principal da API de Revisão de Laudo.

Este serviço expõe um endpoint HTTP para receber solicitações de revisão
de laudos já emitidos, conforme contrato acordado com o cliente.
"""

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, field_validator, model_validator

# Instância principal da aplicação FastAPI
app = FastAPI(
    title="API de Revisão de Laudo - poc",
    description=(
        "Serviço responsável por registrar solicitações de revisão de laudos "
        "já emitidos, informando médico solicitante, profissional atribuído, "
        "justificativa textual e motivos estruturados da revisão."
    ),
    version="1.0.0",
)


class RequestingPhysician(BaseModel):
    """
    Modelo de dados para o médico solicitante da revisão.
    """

    name: str  # Nome completo do médico solicitante
    councilCode: str  # Sigla do conselho profissional (ex.: "CRM")
    professionalRegistrationNumber: str  # Número de registro no conselho
    councilStateCode: str  # UF do conselho (ex.: "CE", "SP")
    phone: str  # Telefone de contato
    email: EmailStr  # E-mail do médico solicitante (validação de formato)
    cpf: str  # CPF do médico solicitante (somente dígitos)

    @field_validator(
        "name",
        "councilCode",
        "professionalRegistrationNumber",
        "councilStateCode",
        "phone",
        "cpf",
        mode="before",
    )
    @classmethod
    def not_empty(cls, value: str) -> str:
        """
        Valida que campos textuais obrigatórios não sejam vazios ou apenas espaços.
        """
        if value is None:
            raise ValueError("Campo obrigatório não pode ser nulo.")
        value_str = str(value).strip()
        if not value_str:
            raise ValueError("Campo obrigatório não pode ser vazio.")
        return value_str

    @field_validator("cpf")
    @classmethod
    def validate_cpf_digits(cls, value: str) -> str:
        """
        Validação simples para garantir que o CPF contenha somente dígitos
        e tenha tamanho 11. (Não faz validação de dígitos verificadores.)
        """
        if not value.isdigit():
            raise ValueError("CPF deve conter apenas dígitos.")
        if len(value) != 11:
            raise ValueError("CPF deve ter exatamente 11 dígitos.")
        return value


class AssignedProfessional(BaseModel):
    """
    Modelo de dados para o profissional atribuído à revisão do laudo.
    """

    professionalCode: str  # Código interno do profissional
    professionalName: str  # Nome completo do profissional

    @field_validator("professionalCode", "professionalName", mode="before")
    @classmethod
    def not_empty(cls, value: str) -> str:
        """
        Valida que campos textuais obrigatórios não sejam vazios ou apenas espaços.
        """
        if value is None:
            raise ValueError("Campo obrigatório não pode ser nulo.")
        value_str = str(value).strip()
        if not value_str:
            raise ValueError("Campo obrigatório não pode ser vazio.")
        return value_str


class ReviewReasons(BaseModel):
    """
    Modelo de dados para os motivos estruturados da revisão do laudo.
    """

    lateralityError: bool  # Motivo: erro de lateralidade
    orthographicError: bool  # Motivo: erro ortográfico
    diagnosticDivergence: bool  # Motivo: divergência diagnóstica
    wrongExamTopography: bool  # Motivo: exame de outra topografia
    measurementDivergence: bool  # Motivo: divergência de mensuração/medida
    other: bool  # Motivo: outro
    otherDescription: Optional[str] = None  # Descrição quando other = true

    @model_validator(mode="after")
    def validate_reasons(self) -> "ReviewReasons":
        """
        Regras de negócio:
        - Pelo menos um campo booleano deve ser True.
        - Quando 'other' for True, 'otherDescription' torna-se obrigatório.
        """
        # Verifica se ao menos um motivo foi marcado como True
        has_any_true = any(
            [
                self.lateralityError,
                self.orthographicError,
                self.diagnosticDivergence,
                self.wrongExamTopography,
                self.measurementDivergence,
                self.other,
            ]
        )
        if not has_any_true:
            raise ValueError(
                "Pelo menos um motivo em 'reviewReasons' deve ser verdadeiro."
            )

        # Se other = True, então otherDescription é obrigatório e não pode ser vazio
        if self.other:
            if self.otherDescription is None or not str(self.otherDescription).strip():
                raise ValueError(
                    "Quando 'other' = true, 'otherDescription' é obrigatório."
                )

        return self


class ReviewRequest(BaseModel):
    """
    Modelo de dados para a solicitação de revisão de laudo.
    """

    accessionNumber: str  # Identificador único do exame
    requestingPhysician: RequestingPhysician  # Médico que solicita a revisão
    freeAssignmentFlag: bool  # Se a atribuição do revisor é livre
    assignedProfessional: Optional[AssignedProfessional] = None  # Profissional atribuído
    reviewJustification: str  # Justificativa textual da revisão
    reviewReasons: ReviewReasons  # Motivos estruturados da revisão

    @field_validator("accessionNumber", "reviewJustification", mode="before")
    @classmethod
    def not_empty(cls, value: str) -> str:
        """
        Valida que campos textuais obrigatórios não sejam vazios ou apenas espaços.
        """
        if value is None:
            raise ValueError("Campo obrigatório não pode ser nulo.")
        value_str = str(value).strip()
        if not value_str:
            raise ValueError("Campo obrigatório não pode ser vazio.")
        return value_str

    @model_validator(mode="after")
    def validate_business_rules(self) -> "ReviewRequest":
        """
        Regras de negócio específicas da solicitação de revisão:

        - accessionNumber é obrigatório (integração para verificar existência
          na Worklist/Laudo deve ser implementada em outra camada).
        - reviewJustification é obrigatória e deve ter texto.
        - Quando freeAssignmentFlag = false, assignedProfessional é obrigatório.
        - Quando freeAssignmentFlag = true, assignedProfessional pode ser ignorado.
        """
        if not self.accessionNumber or not self.accessionNumber.strip():
            raise ValueError("accessionNumber é obrigatório.")

        if not self.reviewJustification or not self.reviewJustification.strip():
            raise ValueError("reviewJustification é obrigatória.")

        if self.freeAssignmentFlag is False and self.assignedProfessional is None:
            raise ValueError(
                "Quando 'freeAssignmentFlag' = false, 'assignedProfessional' é obrigatório."
            )

        return self


class ReviewResponse(BaseModel):
    """
    Modelo de resposta (ACK) para solicitação de revisão de laudo.
    """

    status: str  # Ex.: "ACK" ou "ERROR"
    message: str  # Mensagem de descrição do resultado
    receivedItems: int  # Quantidade de itens processados na requisição


@app.post(
    "/poc/api/revisaolaudo",
    response_model=ReviewResponse,
    summary="Registrar solicitação de revisão de laudo",
    tags=["Revisão de Laudo"],
)
async def create_review_request(payload: List[ReviewRequest]):
    """
    Endpoint responsável por receber solicitações de revisão de laudos.

    Parâmetros:
    - payload: lista de objetos ReviewRequest enviada pelo cliente.

    Retorno:
    - Objeto ReviewResponse com ACK de recebimento ou erro de validação.
    """

    # Verificação simples para garantir que a lista não esteja vazia.
    if not payload:
        raise HTTPException(
            status_code=400,
            detail="A requisição deve conter pelo menos um item na lista.",
        )

    # Aqui poderia ser feita a persistência em banco de dados ou envio para uma fila.
    # Exemplo:
    # for item in payload:
    #     salvar_solicitacao_no_banco(item)
    #     publicar_evento_para_fila(item)

    # Retorna um ACK simples informando a quantidade de itens recebidos
    return ReviewResponse(
        status="ACK",
        message="Solicitação(ões) de revisão recebida(s) com sucesso.",
        receivedItems=len(payload),
    )
