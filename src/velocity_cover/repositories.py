"""Repository-facing contracts for Track 2."""
from typing import Protocol

from src.domain.repositories import (
    IItemRepository,
    IRulesRepository,
    ISalesRepository,
    IStockRepository,
    IStoreRepository,
)


class VelocityCoverRepository(Protocol):
    stores: IStoreRepository
    items: IItemRepository
    stock: IStockRepository
    sales: ISalesRepository
    rules: IRulesRepository
