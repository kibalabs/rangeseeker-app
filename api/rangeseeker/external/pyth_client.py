import urllib.parse

from core.requester import Requester


class PythClient:
    def __init__(self, requester: Requester) -> None:
        self.requester = requester
        self.baseUrl = 'https://hermes.pyth.network'

    async def get_prices(self, priceIds: list[str]) -> dict[str, float]:
        if not priceIds:
            return {}
        # https://hermes.pyth.network/v2/updates/price/latest?ids[]=...
        queryParams = [('ids[]', priceId) for priceId in priceIds]
        queryString = urllib.parse.urlencode(queryParams)
        url = f'{self.baseUrl}/v2/updates/price/latest?{queryString}'
        response = await self.requester.get(url)
        data = response.json()
        prices = {}
        # The API returns a JSON object with 'parsed' field containing the list of updates
        # if the 'parsed' query param is set to true, or by default on this endpoint it might return parsed data
        # Let's check the response structure. Usually v2/updates/price/latest returns a JSON object.
        # If we look at standard usage, it returns { binary: ..., parsed: [...] }
        parsedData = data.get('parsed', [])
        for item in parsedData:
            priceId = '0x' + item['id']
            # price object contains price, conf, expo, publish_time
            priceData = item['price']
            price = float(priceData['price'])
            expo = int(priceData['expo'])
            # price * 10^expo
            finalPrice = price * (10**expo)
            prices[priceId] = finalPrice
        return prices
