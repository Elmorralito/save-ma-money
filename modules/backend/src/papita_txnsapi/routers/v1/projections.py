"""Owner-scoped Financial Projections & Amortization API router (/api/v1/projections)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.rate_limit import enforce_tenant_api_rate_limit
from papita_txnsapi.dependencies.services import get_accounts_service, get_users_service
from papita_txnsapi.schemas.accounts import (
    accounts_from_dataframe,
    balances_by_account_id,
    effective_account_balance,
)
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.projections import (
    CreditCardProjectionRequest,
    CreditCardProjectionResponse,
    InvestmentProjectionRequest,
    InvestmentProjectionResponse,
    LoanAmortizationRequest,
    LoanAmortizationResponse,
    RealEstateProjectionRequest,
    RealEstateProjectionResponse,
    build_credit_card_projection,
    build_investment_projection,
    build_loan_amortization,
    build_real_estate_projection,
)
from papita_txnsmodel.services.users import UsersService

router = APIRouter(
    prefix="/projections",
    tags=["Projections"],
    dependencies=[Depends(enforce_tenant_api_rate_limit)],
)


class PortfolioAccountProjectionItem(BaseModel):
    """Account snapshot merged with any user-saved projection rate/term overrides."""

    id: uuid.UUID
    name: str
    account_kind: str
    currency: str
    balance: float
    group: str  # debt | credit_card | real_estate | investment
    config: dict[str, Any] = Field(default_factory=dict)


class PortfolioProjectionsResponse(BaseModel):
    debts: list[PortfolioAccountProjectionItem] = Field(default_factory=list)
    credit_cards: list[PortfolioAccountProjectionItem] = Field(default_factory=list)
    real_estate: list[PortfolioAccountProjectionItem] = Field(default_factory=list)
    investments: list[PortfolioAccountProjectionItem] = Field(default_factory=list)


class AccountProjectionConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")

    rate_convention: str | None = None
    annual_rate_pct: float | None = Field(default=None, ge=-50, le=200)
    remaining_months: int | None = Field(default=None, ge=0, le=480)
    monthly_insurance: float | None = Field(default=None, ge=0)
    extra_monthly_payment: float | None = Field(default=None, ge=0)
    monthly_payment: float | None = Field(default=None, ge=0)
    investment_type: str | None = None
    monthly_contribution: float | None = Field(default=None, ge=0)
    horizon_years: int | None = Field(default=None, ge=1, le=40)
    annual_fee_pct: float | None = Field(default=None, ge=0, le=10)
    annual_inflation_pct: float | None = Field(default=None, ge=0, le=30)
    tax_on_gains_pct: float | None = Field(default=None, ge=0, le=50)
    annual_fx_drift_pct: float | None = Field(default=None, ge=-30, le=30)
    annual_appreciation_pct: float | None = Field(default=None, ge=-30, le=50)
    monthly_rent_income: float | None = Field(default=None, ge=0)
    occupancy_pct: float | None = Field(default=None, ge=0, le=100)
    monthly_hoa_and_maintenance: float | None = Field(default=None, ge=0)
    annual_property_tax_pct: float | None = Field(default=None, ge=0, le=10)
    pay_in_one_installment: bool | None = None
    linked_mortgage_id: str | None = None


def _classify_account_group(account_kind: str, name: str) -> str | None:
    kind = account_kind.lower()
    lower_name = name.lower()
    if "credit_card" in kind or "credit card" in lower_name or "visa" in lower_name or "mc nu" in lower_name:
        return "credit_card"
    if (
        "loan" in kind
        or "mortgage" in kind
        or "liability" in kind
        or "leverage" in lower_name
        or "cartera" in lower_name
    ):
        return "debt"
    if "real_estate" in kind or "aluna beach resort" in lower_name:
        return "real_estate"
    if any(
        k in kind
        for k in (
            "investment",
            "trading",
            "crypto",
            "retirement",
            "pension",
            "fiduciary",
            "savings",
            "lending",
            "asset",
        )
    ):
        if "savings account bancolombia" in lower_name or "cuenta nu" in lower_name:
            return None
        return "investment"
    return None


@router.get("/portfolio", response_model=PortfolioProjectionsResponse)
def get_projection_portfolio(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
) -> PortfolioProjectionsResponse:
    """Return the owner's debts, credit cards, real estate, and investments with saved configs."""
    df, _total = accounts_service.list_accounts(owner=owner, skip=0, limit=200)
    accounts = accounts_from_dataframe(df)
    account_ids = [acc.id for acc in accounts if acc.id is not None]
    if accounts_service.balances_service is None or not account_ids:
        balance_map: dict[uuid.UUID, float] = {}
    else:
        balances_df = accounts_service.balances_service.get_balances(owner=owner, account_ids=account_ids)
        balance_map = balances_by_account_id(balances_df)
    saved_configs: dict[str, dict[str, Any]] = dict((owner.preferences or {}).get("projection_configs") or {})

    debts: list[PortfolioAccountProjectionItem] = []
    credit_cards: list[PortfolioAccountProjectionItem] = []
    real_estate: list[PortfolioAccountProjectionItem] = []
    investments: list[PortfolioAccountProjectionItem] = []

    for acc in accounts:
        if not acc.active or acc.id is None:
            continue
        kind_str = acc.account_kind.value if hasattr(acc.account_kind, "value") else str(acc.account_kind)
        group = _classify_account_group(kind_str, acc.name)
        if group is None:
            continue
        raw_bal = effective_account_balance(acc, balance_map=balance_map)
        bal = abs(float(raw_bal if raw_bal else (acc.current_value or acc.initial_value or 0.0)))
        cfg = dict(saved_configs.get(str(acc.id)) or {})
        item = PortfolioAccountProjectionItem(
            id=acc.id,
            name=acc.name,
            account_kind=kind_str,
            currency=acc.currency or "COP",
            balance=round(bal, 2),
            group=group,
            config=cfg,
        )
        if group == "debt":
            debts.append(item)
        elif group == "credit_card":
            credit_cards.append(item)
        elif group == "real_estate":
            real_estate.append(item)
        else:
            investments.append(item)

    return PortfolioProjectionsResponse(
        debts=debts,
        credit_cards=credit_cards,
        real_estate=real_estate,
        investments=investments,
    )


@router.put("/config/{account_id}")
def save_account_projection_config(
    account_id: uuid.UUID,
    payload: AccountProjectionConfigUpdate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> dict[str, Any]:
    """Persist user-configured interest rates, conventions, and assumptions for an account."""
    existing_configs = dict((owner.preferences or {}).get("projection_configs") or {})
    cleaned = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    existing_configs[str(account_id)] = cleaned
    try:
        users_service.update_user_settings(
            owner=owner,
            preferences={"projection_configs": existing_configs},
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return {"account_id": str(account_id), "config": cleaned}


@router.post("/loan", response_model=LoanAmortizationResponse)
def project_loan(
    payload: LoanAmortizationRequest,
    _owner: Annotated[UsersDTO, Depends(get_current_owner)],
) -> LoanAmortizationResponse:
    """Calculate a full Colombian EA or US APR loan amortization schedule."""
    return build_loan_amortization(payload)


@router.post("/credit-card", response_model=CreditCardProjectionResponse)
def project_credit_card(
    payload: CreditCardProjectionRequest,
    _owner: Annotated[UsersDTO, Depends(get_current_owner)],
) -> CreditCardProjectionResponse:
    """Calculate a credit card payoff schedule (Colombian EA cuotas/revolving or US APR)."""
    return build_credit_card_projection(payload)


@router.post("/real-estate", response_model=RealEstateProjectionResponse)
def project_real_estate(
    payload: RealEstateProjectionRequest,
    _owner: Annotated[UsersDTO, Depends(get_current_owner)],
) -> RealEstateProjectionResponse:
    """Calculate property appreciation, linked mortgage paydown, net equity, and rental cashflow."""
    return build_real_estate_projection(payload)


@router.post("/investment", response_model=InvestmentProjectionResponse)
def project_investment(
    payload: InvestmentProjectionRequest,
    _owner: Annotated[UsersDTO, Depends(get_current_owner)],
) -> InvestmentProjectionResponse:
    """Calculate compound investment projection net of fees, inflation, FX drift, and taxes."""
    return build_investment_projection(payload)
