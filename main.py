import os
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BASE_URL = "https://api.binance.com"

price_cache = {}
price_cache["USDT"] = 0

last_sync_timestamps = {}

sync_interval = int(os.environ.get("SYNC_INTERVAL", 60))

def binance_api_request(endpoint, params=None):
    url = BASE_URL + endpoint
    response = requests.get(url, params=params)
    return response.json()

def sync_token_price_data(symbols):
    global last_sync_timestamps, price_cache

    symbols = [str(symbol)+"USDT" for symbol in symbols]

    response = binance_api_request("/api/v3/ticker/24hr", params={"symbols": str(symbols).replace("'", '"').replace(' ', '')})

    if 'code' in response:
        return

    for item in response:
        symbol = str(item["symbol"]).replace('USDT', '')
        price_change_percent = float(item["priceChangePercent"])
        price_cache[symbol] = price_change_percent
        last_sync_timestamps[symbol] = time.time()

def get_token_price_change(tokens):
    global last_sync_timestamps, price_cache

    current_timestamp = time.time()
    result = {}

    query_list=[]

    for token in tokens:
        last_sync_timestamp = last_sync_timestamps.get(token)

        if last_sync_timestamp is None:
            sync_token_price_data([token])
        elif (current_timestamp - last_sync_timestamp) > sync_interval:
            query_list.append(token)

    sync_token_price_data(query_list)

    for token in tokens:
        price_change_percent = price_cache.get(token)

        if price_change_percent is None:
            result[token] = "Token not found."
        else:
            result[token] = price_change_percent

    return result

@app.route("/", methods=["POST"])
def api():
    data = request.get_json()

    if "tokens" not in data:
        return jsonify({"error": "Tokens parameter is missing."}), 400

    print(data["tokens"])

    tokens = data["tokens"]
    result = get_token_price_change(tokens)

    return jsonify(result)

if __name__ == "__main__":
    app.run()