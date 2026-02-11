from datetime import datetime, timedelta
from typing import Optional, Set, Any

class BroadcastState:
    def __init__(self):
        self.is_active: bool = False
        self.end_time: Optional[datetime] = None
        self.admin_id: Optional[int] = None
        self.target_chat_ids: Set[int] = set()
        self.report_message_id: Optional[int] = None
        self.report_chat_id: Optional[int] = None  # чат, куда отправлено табло (для редактирования через бота)
        self._bot: Optional[Any] = None  # aiogram Bot для редактирования табло (без entity userbot)
        self.responses: list = [] # Список словарей {time, user, group, text}
        self.session_direction: str = 'buy'
        self.currency_from: str = ''
        self.currency_to: str = ''
        self.is_custom_mode: bool = False
        self.target_rate: Optional[float] = None

    def start(self, admin_id: int, duration_minutes: int, target_chat_ids: list[int], direction: str = 'buy', currency_from: str = '', currency_to: str = '', is_custom: bool = False, target_rate: Optional[float] = None):
        self.admin_id = admin_id
        self.end_time = datetime.now() + timedelta(minutes=duration_minutes)
        self.target_chat_ids = set(target_chat_ids)
        self.is_active = True
        self.responses = []
        self.report_message_id = None
        self.report_chat_id = None
        self.session_direction = direction # 'buy' or 'sell' (наше намерение)
        self.currency_from = currency_from
        self.currency_to = currency_to
        self.is_custom_mode = is_custom
        self.target_rate = target_rate

    def stop(self):
        self.is_active = False
        self.end_time = None
        self.admin_id = None
        self.target_chat_ids.clear()
        self.report_message_id = None
        self.report_chat_id = None
        self._bot = None

    def set_report_message_id(self, msg_id: int):
        self.report_message_id = msg_id

    def set_report_message(self, chat_id: int, message_id: int, bot: Any = None):
        """Сохранить сообщение табло и бота для последующего редактирования."""
        self.report_chat_id = chat_id
        self.report_message_id = message_id
        if bot is not None:
            self._bot = bot

    def set_bot(self, bot: Any):
        """Установить экземпляр aiogram Bot для редактирования табло."""
        self._bot = bot

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
        """Route to appropriate dashboard formatter"""
        if self.is_custom_mode:
            return self._format_custom_dashboard()
        else:
            return self._format_structured_dashboard()
    
    def _format_structured_dashboard(self) -> str:
        """Генерирует текст Табло для структурированных торговых сессий"""
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

        # Фильтрация по целевому курсу
        # Если мы BUY (хотим купить), нам нужны все которые меньше либо равны target_rate
        # Если мы SELL (хотим продать), нам нужны все которые больше либо равны target_rate
        if self.target_rate is not None and self.target_rate > 0:
            if self.session_direction == 'buy':
                valid_responses = [r for r in valid_responses if r['price'] <= self.target_rate]
            else:
                valid_responses = [r for r in valid_responses if r['price'] >= self.target_rate]

        # Формирование текста
        lines = []
        
        if valid_responses:
            #
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
    
    def _format_custom_dashboard(self) -> str:
        """Генерирует текст Табло для кастомных рассылок (показывает buy и sell)"""
        if not self.responses:
            return "⏳ Ожидаю первые сообщения..."
        
        buy_offers = [r for r in self.responses if r.get('side') == 'buy' and r.get('price')]
        sell_offers = [r for r in self.responses if r.get('side') == 'sell' and r.get('price')]
        other_msgs = [r for r in self.responses if not r.get('price')]
        
        buy_offers.sort(key=lambda x: x['price'], reverse=True)
        sell_offers.sort(key=lambda x: x['price'])
        
        lines = []
        
        if sell_offers:
            lines.append("💰 <b>ПРОДАЖА (лучшие предложения):</b>")
            for i, r in enumerate(sell_offers[:5], 1):
                vol_str = f" | {r.get('volume', '?')}" if r.get('volume') else ""
                lines.append(f"{i}. {r['price']}{vol_str} | {r['user']} ({r['group']})")
            avg_sell = sum(r['price'] for r in sell_offers) / len(sell_offers)
            lines.append(f"Средний: {avg_sell:.2f}\n")
        
        if buy_offers:
            lines.append("🛒 <b>ПОКУПКА (лучшие предложения):</b>")
            for i, r in enumerate(buy_offers[:5], 1):
                vol_str = f" | {r.get('volume', '?')}" if r.get('volume') else ""
                lines.append(f"{i}. {r['price']}{vol_str} | {r['user']} ({r['group']})")
            avg_buy = sum(r['price'] for r in buy_offers) / len(buy_offers)
            lines.append(f"Средний: {avg_buy:.2f}\n")
        
        if buy_offers and sell_offers:
            spread = avg_sell - avg_buy
            lines.append(f"💡 <b>Спред: {spread:.2f}</b>\n")
        
        if other_msgs:
            lines.append("📋 <b>Прочие сообщения:</b>")
            for r in other_msgs[-3:]:
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

    async def edit_report_message_text(self, text: str) -> bool:
        """Обновить текст сообщения табло через бота (без использования entity в userbot)."""
        if self._bot is None or self.report_chat_id is None or self.report_message_id is None:
            return False
        try:
            await self._bot.edit_message_text(
                chat_id=self.report_chat_id,
                message_id=self.report_message_id,
                text=text,
                parse_mode="HTML",
            )
            return True
        except Exception:
            return False

# Глобальный инстанс
broadcast_manager = BroadcastState()
