import json
import httpx
from typing import Optional, Dict, Any, List
from config import Config, logger

class OpenRouterClient:
    def __init__(self):
        self.api_key = Config.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/Antigravity/bt6_parser_bot",
            "X-Title": "BT6 Parser Bot",
            "Content-Type": "application/json"
        }
        self.model = "anthropic/claude-3.5-sonnet"

    async def analyze_message(self, message_text: str, context_prompt: str = "") -> Optional[List[Dict[str, Any]]]:
        """
        Отправляет сообщение на анализ в LLM.
        Возвращает список офферов или None если спам.
        """
        if not self.api_key:
            return None

        system_instruction = (
            "Ты профессиональный p2p трейдер. Анализируй сообщения из чатов и извлекай торговые предложения.\n\n"
            "**ПРАВИЛА:**\n"
            "1. Если сообщение НЕ содержит торговых предложений (спам, вопросы, новости) — верни: {\"offers\": []}\n"
            "2. Если сообщение содержит предложения купить/продать валюту — извлеки ВСЕ предложения в массив:\n"
            "   {\n"
            "     \"offers\": [\n"
            "       {\n"
            "         \"side\": \"buy\" | \"sell\",  // buy = автор ПОКУПАЕТ, sell = автор ПРОДАЕТ\n"
            "         \"price\": number | null,    // Цена (курс обмена). Если не указана — null. ВАЖНО: конвертируй запятые в точки (88,90 → 88.90)\n"
            "         \"volume\": string | null,   // Объем ('10000', '50k', 'от 100'). Если не указан — null\n"
            "         \"currency\": string          // Валюта (USDT, RUB, USD, CNY и т.д.)\n"
            "       }\n"
            "     ]\n"
            "   }\n\n"
            "**ВАЖНО:**\n"
            "- Если в сообщении НЕСКОЛЬКО предложений (например, 'Покупаем по 88,50, продаем по 88,90') — извлеки ОБА в массив\n"
            "- Цены с ЗАПЯТОЙ (88,90) конвертируй в число с ТОЧКОЙ (88.90)\n"
            "- Если цена не указана явно — ставь null\n\n"
            "**ПРИМЕРЫ:**\n"
            "Сообщение: 'Покупаем по 78' → {\"offers\": [{\"side\": \"buy\", \"price\": 78, \"volume\": null, \"currency\": \"RUB\"}]}\n"
            "Сообщение: 'Продаем USD по курсу 78,50' → {\"offers\": [{\"side\": \"sell\", \"price\": 78.5, \"volume\": null, \"currency\": \"USD\"}]}\n"
            "Сообщение: 'Покупка 89,55, Продажа 89,95' → {\"offers\": [{\"side\": \"buy\", \"price\": 89.55, \"volume\": null, \"currency\": \"RUB\"}, {\"side\": \"sell\", \"price\": 89.95, \"volume\": null, \"currency\": \"RUB\"}]}\n"
            "Сообщение: 'Всем привет!' → {\"offers\": []}\n\n"
            "**ВАЖНО:** Отвечай ТОЛЬКО валидным JSON, без комментариев."
        )
        
        if context_prompt:
             system_instruction += f"\n\n**КОНТЕКСТ ПОИСКА:** {context_prompt}"

        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": message_text}
            ]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.error(f"OpenRouter Error ({self.model}): {response.text}")
                    return None
                    
                data = response.json()
                content = data['choices'][0]['message']['content']
                
                # Очистка от markdown
                if "```" in content:
                    content = content.split("```")[1].strip()
                    if content.startswith("json"):
                        content = content[4:].strip()
                        
                result = json.loads(content)
                
                # Новый формат: возвращаем список офферов
                offers = result.get('offers', [])
                
                # Если пустой список — это спам
                if not offers:
                    return None
                
                return offers

        except Exception as e:
            logger.error(f"AI Analysis failed: {e}")
            return None

# Глобальный инстанс
ai_client = OpenRouterClient()
