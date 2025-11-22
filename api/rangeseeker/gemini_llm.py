import typing

from core import logging
from core.requester import Requester
from core.util import json_util
from core.util.typing_util import JsonObject


class LLM:
    async def get_query(self, systemPrompt: str, prompt: str) -> JsonObject:
        raise NotImplementedError('Subclasses must implement get_query')

    async def get_next_step(self, promptQuery: JsonObject) -> JsonObject:
        raise NotImplementedError('Subclasses must implement get_next_step')


class GeminiLLM(LLM):
    def __init__(self, apiKey: str, requester: Requester, modelId: str = 'gemini-2.5-flash') -> None:
        self.apiKey = apiKey
        self.requester = requester
        self.endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/{modelId}:generateContent'

    async def get_query(self, systemPrompt: str, prompt: str) -> JsonObject:
        promptQuery: JsonObject = {
            'system_instruction': {'parts': [{'text': systemPrompt}]},
            'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
            'generationConfig': {
                'response_mime_type': 'application/json',
            },
        }
        return promptQuery

    async def get_next_step(self, promptQuery: JsonObject) -> JsonObject:
        headers = {'Content-Type': 'application/json'}
        response = await self.requester.post(url=f'{self.endpoint}?key={self.apiKey}', headers=headers, dataDict=promptQuery, timeout=60)
        responseJson = response.json()
        rawText = responseJson['candidates'][0]['content']['parts'][0]['text']
        # Remove markdown code blocks if present
        jsonText = rawText.strip()
        if jsonText.startswith('```'):
            jsonText = jsonText.split('\n', 1)[1] if '\n' in jsonText else jsonText
            jsonText = jsonText.rsplit('```', 1)[0] if '```' in jsonText else jsonText
            jsonText = jsonText.strip()
        try:
            jsonDict = json_util.loads(jsonText)
        except Exception:
            logging.error(f'Error parsing JSON from Gemini response: {jsonText}')
            raise
        return typing.cast('JsonObject', jsonDict)
