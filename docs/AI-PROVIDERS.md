# AI provayderlar — kalit olish

## OpenAI

1. [platform.openai.com](https://platform.openai.com) → API keys → Create secret key  
2. Tizimda: Provider **openai**, token `sk-...`, model masalan `gpt-4o-mini`

## Anthropic (Claude)

1. [console.anthropic.com](https://console.anthropic.com) → API Keys  
2. Provider **anthropic**, kalitni xavfsiz saqlang

## Google Gemini

1. [Google AI Studio](https://aistudio.google.com) → API key  
2. Provider **google** (test va router kengayishi bilan)

## Mistral / Groq / DeepSeek / xAI

Har biri uchun rasmiy konsoldan API key oling va `POST /api/ai-tokens` orqali `provider` maydoniga mos nom yozing (`mistral`, `groq`, `deepseek`, `xai`).

## Custom (Ollama, LocalAI)

- **Base URL:** masalan `http://host:11434/v1`  
- **Model:** `llama3.2`  
- **Token:** bo‘sh yoki ixtiyoriy

## Narx (taxminiy)

| Provider | Model        | ~1K token |
|----------|--------------|-----------|
| OpenAI   | gpt-4o-mini  | arzon     |
| OpenAI   | gpt-4o       | yuqori    |

Aniq narxlar provayder narxlar sahifasidan.
