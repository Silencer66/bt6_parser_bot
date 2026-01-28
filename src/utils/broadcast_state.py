from datetime import datetime, timedelta
from typing import Optional, Set

class BroadcastState:
    def __init__(self):
        self.is_active: bool = False
        self.end_time: Optional[datetime] = None
        self.admin_id: Optional[int] = None
        self.target_chat_ids: Set[int] = set()
        self.report_message_id: Optional[int] = None
        self.responses: list = [] # Список словарей {time, user, group, text}
        self.session_direction: str = 'buy'
        self.currency_from: str = ''
        self.currency_to: str = ''

    def start(self, admin_id: int, duration_minutes: int, target_chat_ids: list[int], direction: str = 'buy', currency_from: str = '', currency_to: str = ''):
        self.admin_id = admin_id
        self.end_time = datetime.now() + timedelta(minutes=duration_minutes)
        self.target_chat_ids = set(target_chat_ids)
        self.is_active = True
        self.responses = []
        self.report_message_id = None
        self.session_direction = direction # 'buy' or 'sell' (наше намерение)
        self.currency_from = currency_from
        self.currency_to = currency_to

    def stop(self):
        self.is_active = False
        self.end_time = None
        self.admin_id = None
        self.target_chat_ids.clear()
        self.report_message_id = None

    def set_report_message_id(self, msg_id: int):
        self.report_message_id = msg_id

    def add_response(self, user: str, group: str, text: str, price: float = None, volume: str = None, side: str = None, raw_text: str = ""):
        self.responses.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "user": user,
            "group": group,
            "text": text,
            "price": price,
            "volume": volume,
            "side": side,
            "raw_text": raw_text
        })

    def get_dashboard_text(self) -> str:
        """Генерирует текст Табло с ТОПом предложений"""
        if not self.responses:
            return "⏳ Ожидаю первые сообщения..."
        
        # Фильтрация: нам нужны только встречные заявки и те, где есть цена
        # Если мы BUY, ищем SELL. Если мы SELL, ищем BUY.
        target_side = 'sell' if self.session_direction == 'buy' else 'buy'
        
        valid_responses = [r for r in self.responses if r['price'] is not None and (r.get('side') == target_side or r.get('side') is None)]
        other_responses = [r for r in self.responses if r not in valid_responses]
        
        # Сортировка
        # Если мы BUY (хотим купить), нам важна НИЗКАЯ цена -> Ascending
        # Если мы SELL (хотим продать), нам важна ВЫСОКАЯ цена -> Descending
        reverse_sort = True if self.session_direction == 'sell' else False
        
        valid_responses.sort(key=lambda x: x['price'], reverse=reverse_sort)
        
        # Формирование текста
        lines = []
        
        if valid_responses:
            lines.append(f"📊 <b>ТОП ПРЕДЛОЖЕНИЙ ({'Сортировка по выгодности' if self.session_direction else 'Список'}):</b>")
            for i, r in enumerate(valid_responses[:10], 1): # Топ 10
                price_str = f"{r['price']}"
                vol_str = f" | {r['volume']}" if r['volume'] else ""
                lines.append(f"{i}. <b>{price_str}</b>{vol_str} | {r['user']} ({r['group']})")
            
            # Средневзвешенный курс (просто среднее, т.к. объем строка)
            avg_price = sum(r['price'] for r in valid_responses) / len(valid_responses)
            lines.append(f"\n📈 <b>Средний курс: {avg_price:.2f}</b>")
        
        if other_responses:
            lines.append("\n📋 <b>Прочие сообщения:</b>")
            for r in other_responses[-5:]: # Последние 5 прочих
                lines.append(f"• {r['user']}: {r.get('raw_text', '')[:30]}...")
                
        return "\n".join(lines)

    def is_monitoring(self, chat_id: int = None) -> bool:
        if not self.is_active:
            return False
        
        if datetime.now() > self.end_time:
            self.stop()
            return False
            
        # Если передан chat_id, проверяем, нужно ли его слушать
        if chat_id is not None and chat_id not in self.target_chat_ids:
            return False
            
        return True

# Глобальный инстанс
broadcast_manager = BroadcastState()
