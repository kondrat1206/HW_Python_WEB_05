import aiohttp
import asyncio
import websockets
import json
from datetime import datetime, timedelta
import sys
import logging

log_file = 'commands.log'
file_handler = logging.FileHandler(log_file)
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(format=log_format, level=logging.INFO, handlers=[file_handler])
class ExchangeRateService:
    API_URL = "https://api.privatbank.ua/p24api/exchange_rates?json&date={}"

    async def get_exchange_rates(self, days_back, currencies):
        dates = [datetime.now() - timedelta(days=i) for i in range(0, days_back)]
        tasks = [self._fetch_data(date, currencies) for date in dates]
        return await asyncio.gather(*tasks)

    async def _fetch_data(self, date, currencies):
        try:
            formatted_date = date.strftime("%d.%m.%Y")
            url = self.API_URL.format(formatted_date)

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()  
                    data = await response.json()
                    return self._process_data(data, currencies, formatted_date)

        except aiohttp.ClientError as e:
            print(f"Error during request: {e}")
            return None

    def _process_data(self, data, currencies, formatted_date):
        result = {formatted_date: {}}
        for currency in currencies:
            rates = self._find_rate(data, currency)
            if rates:
                result[formatted_date][currency] = {
                    "sale": rates.get("saleRate"),
                    "purchase": rates.get("purchaseRate"),
                }
        #print(result)        
        return json.dumps(result)

    def _find_rate(self, data, currency):
        for rate in data["exchangeRate"]:
            if rate["currency"] == currency:
                return {
                    "saleRate": rate.get("saleRate"),
                    "purchaseRate": rate.get("purchaseRate"),
                }
        return None

async def handle_exchange_command(message):
    command, currencies, days_back = message.split()
    if command == "exchange":
        await log_command(message)
        currencies = currencies.split(',')
        days_back = int(days_back)
        if days_back <= 10:
            exchange_rate_service = ExchangeRateService()
            results = await exchange_rate_service.get_exchange_rates(days_back, currencies)
            formatted_results = [result for result in results if result]
            return json.dumps(formatted_results)
        else:
            return "Days_back must be equal or greater than 10"
    else:
        return "Invalid command. Please use: exchange <currencies> <days_back>"
    

async def handler(websocket, path):
    greeting = "Hello! Set currencies and days_back parameters to get exchange rates. Or send message: \"exchange USD,EUR 2\""
    await websocket.send(greeting)
    async for message in websocket:
        response = await handle_exchange_command(message)
        await websocket.send(response)

async def log_command(message, success=True):
    
    log_message = f"Received command: {message}"
    if not success:
        log_message = f"Error processing command {message}"
    logging.info(log_message)

async def main():
    server = await websockets.serve(handler, "localhost", 8765)
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
