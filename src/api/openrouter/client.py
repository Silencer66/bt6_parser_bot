import json
import httpx
from typing import Optional, Dict, Any
from src.config import Config, logger

class OpenRouterClient:
    def __init__(self):
        self.api_key = Config.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/Antigravity/bt6_parser_bot", # Required by OpenRouter for stats
            "X-Title": "BT6 Parser Bot",
            "Content-Type": "application/json"
        }
        # Используем надежную платную модель (быстрая и точная для JSON)
        self.model = "openai/gpt-4o-mini"

    async def analyze_message(self, message_text: str, context_prompt: str = "") -> Optional[Dict[str, Any]]:
        """
        Отправляет сообщение на анализ в LLM.
        """
        if not self.api_key:
            return None

        system_instruction = (
            "Ты профессиональный p2p трейдер. Анализируй сообщения из чатов и извлекай торговые предложения.\n\n"
            "**ПРАВИЛА:**\n"
            "1. Если сообщение НЕ содержит торгового предложения (спам, вопросы, новости) — верни: {\"is_offer\": false}\n"
            "2. Если сообщение содержит предложение купить/продать валюту — извлеки данные в JSON:\n"
            "   {\n"
            "     \"is_offer\": true,\n"
            "     \"side\": \"buy\" | \"sell\",  // buy = автор ПОКУПАЕТ, sell = автор ПРОДАЕТ\n"
            "     \"price\": number | null,    // Цена (курс обмена). Если не указана — null\n"
            "     \"volume\": string | null,   // Объем ('10000', '50k', 'от 100'). Если не указан — null\n"
            "     \"currency\": string          // Валюта (USDT, RUB, USD, CNY и т.д.)\n"
            "   }\n\n"
            "**ПРИМЕРЫ:**\n"
            "Сообщение: 'Покупаем по 78' → {\"is_offer\": true, \"side\": \"buy\", \"price\": 78, \"volume\": null, \"currency\": \"RUB\"}\n"
            "Сообщение: 'Продаем USD по курсу 78' → {\"is_offer\": true, \"side\": \"sell\", \"price\": 78, \"volume\": null, \"currency\": \"USD\"}\n"
            "Сообщение: 'Всем привет!' → {\"is_offer\": false}\n\n"
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
                    # response.raise_for_status() # Не роняем бота, просто вернем None
                    return None
                    
                data = response.json()
                content = data['choices'][0]['message']['content']
                
                # Очистка от markdown
                if "```" in content:
                    content = content.split("```")[1].strip()
                    if content.startswith("json"):
                        content = content[4:].strip()
                        
                result = json.loads(content)
                return result

        except Exception as e:
            logger.error(f"AI Analysis failed: {e}")
            return None

# Глобальный инстанс
ai_client = OpenRouterClient()
