from dataclasses import dataclass
from typing import List, Optional
from src.database.models.common import Order, TradingSession

@dataclass
class OrderBookEntry:
    order: Order
    rank: int
    group_name: str

    @property
    def display_price(self) -> str:
        return f"{self.order.price:,.2f}"

    @property
    def display_volume(self) -> str:
        return f"{self.order.volume:,.0f}"

@dataclass
class OrderBook:
    session_id: int
    orders: List[OrderBookEntry]

    @property
    def total_volume(self) -> float:
        return sum(entry.order.volume for entry in self.orders)

    @property
    def weighted_average_price(self) -> float:
        if not self.orders:
            return 0.0
        total_value = sum(entry.order.price * entry.order.volume for entry in self.orders)
        total_vol = self.total_volume
        return total_value / total_vol if total_vol > 0 else 0.0

    def get_top_orders(self, limit: int = 10) -> List[OrderBookEntry]:
        return self.orders[:limit]
