import os
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BASE_URL = "https://api.binance.com"

price_cache = {}
price_cache["USDT"] = {"price": 1, "priceChangePercent": 0, "success": True}

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
        return response

    for item in response:
        symbol = str(item["symbol"]).replace('USDT', '')
        price = float(item["lastPrice"])
        price_change_percent = float(item["priceChangePercent"])
        price_cache[symbol] = {"price": price, "priceChangePercent": price_change_percent, "success": True}
        last_sync_timestamps[symbol] = time.time()

    return None

def get_token_price_change(tokens):
    global last_sync_timestamps, price_cache

    current_timestamp = time.time()
    result = []
    error = None

    query_list=[]

    for token in tokens:
        last_sync_timestamp = last_sync_timestamps.get(token)

        if last_sync_timestamp is None:
            error = sync_token_price_data([token])
        elif (current_timestamp - last_sync_timestamp) > sync_interval:
            query_list.append(token)

    if query_list:
        error = sync_token_price_data(query_list)

    if error:
        return [], error

    for token in tokens:
        price_data = price_cache.get(token, {"success": False})

        result.append({token: price_data})

    return result, None

@app.route("/", methods=["POST"])
def api():
    data = request.get_json()

    if "tokens" not in data:
        return jsonify({"code": 400, "message": "Tokens parameter is missing.", "data": [], "success": False}), 400

    print(data["tokens"])

    tokens = data["tokens"]
    result_data, error = get_token_price_change(tokens)

    if error:
        return jsonify({"code": error["code"], "message": error["msg"], "data": [], "success": False}), 400

    return jsonify({"code": 0, "message": "ok", "data": result_data, "success": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=12002)
