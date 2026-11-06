"""Unit of Work sobre una sesión SQLAlchemy: una transacción por solicitud (ADR-02)."""
from sqlalchemy.orm import Session

from sazon_urbano.domain.repositorios import UnitOfWork


class UnitOfWorkSql(UnitOfWork):
    def __init__(self, session: Session):
        self._session = session

    def iniciar(self) -> None:
        pass  # SQLAlchemy abre la transacción al primer uso de la sesión

    def confirmar(self) -> None:
        self._session.commit()

    def deshacer(self) -> None:
        self._session.rollback()
