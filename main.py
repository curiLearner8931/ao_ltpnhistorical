from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import logging
import requests
from utils import get_connection

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://stock-savvy-safar-app.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class Holding(BaseModel):
    symbol: str
    token: str
    exchange: str

class HistoricalRequest(BaseModel):
    symboltoken: str
    interval: str  # e.g., "ONE_DAY", "FIVE_MINUTE"
    fromdate: str  # format: "YYYY-MM-DD HH:MM"
    todate: str    # format: "YYYY-MM-DD HH:MM"

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Angel One API is live."}

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

    results = []
    for stock in holdings:
        try:
            logging.info(f"Fetching price for {stock.symbol}")
            response = obj.ltpData(
                exchange=stock.exchange,
                tradingsymbol=stock.symbol,
                symboltoken=stock.token
            )
            if response.get("data"):
                data = response["data"]
                results.append({
                    "symbol": stock.symbol,
                    "price": data.get("ltp"),
                    "change": data.get("change"),
                    "percent_change": data.get("percentchange"),
                    "last_traded_time": data.get("last_traded_time")
                })
            else:
                results.append({"symbol": stock.symbol, "error": "No data received"})
        except Exception as e:
            results.append({"symbol": stock.symbol, "error": str(e)})
    return {"live_prices": results}

@app.post("/historical-data")
async def get_historical_data(payload: HistoricalRequest):
    logging.info(f"Fetching historical data: {payload}")
    try:
        obj = get_connection()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Session creation failed")

    headers = {
        "Authorization": f"Bearer {obj.jwt_token}",
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
        data = response.json()
        return data
    except Exception as e:
        logging.error(f"Historical data error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch historical data")
