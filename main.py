from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import logging
import os
import requests
from utils import get_connection

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize FastAPI
app = FastAPI()

# Allow frontend on Vercel to access this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://stock-savvy-safar-app.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request Models ---
class Holding(BaseModel):
    symbol: str
    token: str
    exchange: str

class HistoricalRequest(BaseModel):
    symboltoken: str
    interval: str  # "ONE_DAY", "FIVE_MINUTE", etc.
    fromdate: str  # format: "YYYY-MM-DD HH:MM"
    todate: str    # format: "YYYY-MM-DD HH:MM"

# --- Health Check ---
@app.get("/")
def health_check():
    return {"status": "ok", "message": "Angel One API is live."}

# --- Live Prices ---
@app.post("/live-prices")
async def get_live_prices(holdings: List[Holding]):
    logging.info(f"Received {len(holdings)} holdings for live price fetch.")
    if not holdings:
        return {"live_prices": []}

    try:
        obj = get_connection()
    except Exception as e:
        logging.error(f"Connection failed: {e}")
        raise HTTPException(status_code=500, detail="Angel One login failed")

    jwt = getattr(obj, "jwt_token", None)
    if not jwt:
        raise HTTPException(status_code=500, detail="Missing JWT token")

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
            logging.info(f"Fetching price for {stock.symbol}")
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
            res_json = response.json()
            if res_json.get("data"):
                data = res_json["data"]
                results.append({
                    "symbol": stock.symbol,
                    "price": data.get("ltp"),
                    "change": data.get("change"),
                    "percent_change": data.get("percentchange"),
                    "last_traded_time": data.get("last_traded_time")
                })
            else:
                logging.warning(f"No data for {stock.symbol}: {res_json}")
                results.append({
                    "symbol": stock.symbol,
                    "error": res_json.get("message", "No data received")
                })
        except Exception as e:
            logging.error(f"Error fetching price for {stock.symbol}: {str(e)}")
            results.append({"symbol": stock.symbol, "error": str(e)})

    return {"live_prices": results}

# --- Historical Data ---
@app.post("/historical-data")
async def get_historical_data(payload: HistoricalRequest):
    logging.info(f"Fetching historical data: {payload}")
    try:
        obj = get_connection()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Session creation failed")

    headers = {
        "Authorization": f"Bearer {obj.jwt_token}",
        "Content-Type": "application/json",
        "X-PrivateKey": os.getenv("API_KEY"),
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00"
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
        data = response.json()
        return data
    except Exception as e:
        logging.error(f"Historical data error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch historical data")