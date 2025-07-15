# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import logging
import requests
import os
from utils import get_connection

app = FastAPI()
logging.basicConfig(level=logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://stock-savvy-safar-app.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Holding(BaseModel):
    symbol: str
    token: str
    exchange: str

class HistoricalRequest(BaseModel):
    symboltoken: str
    interval: str  # e.g. "ONE_DAY"
    fromdate: str  # "2024-07-01 09:15"
    todate: str    # "2024-07-15 15:30"

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Angel One API is running."}

@app.post("/live-prices")
async def get_live_prices(holdings: List[Holding]):
    if not holdings:
        return {"live_prices": []}

    try:
        obj = get_connection()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Login failed")

    jwt = obj.jwt_token
    headers = {
        "X-PrivateKey": os.getenv("API_KEY"),
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00",
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json"
    }

    results = []

    for stock in holdings:
        try:
            payload = {
                "exchange": stock.exchange,
                "tradingsymbol": stock.symbol,
                "symboltoken": stock.token
            }
            response = requests.post(
                "https://apiconnect.angelone.in/rest/secure/market/v1/ltp",
                headers=headers,
                json=payload
            )
            logging.info(f"{stock.symbol} -> {response.status_code} - {response.text}")

            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    ltp_data = data["data"]
                    results.append({
                        "symbol": stock.symbol,
                        "price": ltp_data.get("ltp"),
                        "change": ltp_data.get("change"),
                        "percent_change": ltp_data.get("percentchange"),
                        "last_traded_time": ltp_data.get("last_traded_time")
                    })
                else:
                    results.append({"symbol": stock.symbol, "error": "No data in response"})
            else:
                results.append({
                    "symbol": stock.symbol,
                    "error": f"{response.status_code}: {response.text}"
                })

        except Exception as e:
            results.append({"symbol": stock.symbol, "error": str(e)})

    return {"live_prices": results}

@app.post("/historical-data")
async def get_historical_data(payload: HistoricalRequest):
    try:
        obj = get_connection()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Login failed")

    jwt = obj.jwt_token
    headers = {
        "X-PrivateKey": os.getenv("API_KEY"),
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00",
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json"
    }

    request_data = {
        "exchange": "NSE",
        "symboltoken": payload.symboltoken,
        "interval": payload.interval,
        "fromdate": payload.fromdate,
        "todate": payload.todate
    }

    try:
        response = requests.post(
            "https://apiconnect.angelone.in/rest/marketdata/v1/historical/candle-data",
            headers=headers,
            json=request_data
        )
        logging.info(f"Historical response: {response.status_code} - {response.text}")
        return response.json()
    except Exception as e:
        logging.error(f"Historical fetch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch historical data")