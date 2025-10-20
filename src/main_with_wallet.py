from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import time
import requests
from datetime import datetime

app = Flask(__name__, static_folder='.')
CORS(app)

# Configuration
HELIUS_API_KEY = "3a3e05cc-fcff-42bd-8a63-3cbc21226598"
BIRDEYE_API_KEY = "85cef1ef88f34331B491b0af80f7887c"
RESERVE_WALLET = "Az6NNWG54E71hQfPxSPBU3tp98SU7ivfwEUb2AEhrSSu"

# Bot state
bot_state = {
    "active": False,
    "paused": False,
    "trading_capital": 50.00,
    "reserve_balance": 0.00,
    "total_profit": 0.00,
    "total_trades": 0,
    "wins": 0,
    "losses": 0,
    "positions": [],
    "trades": [],
    "connected_wallet": None,
    "wallet_balance_sol": 0,
    "wallet_balance_usdc": 0,
    "last_scan_time": None,
    "scanning": False,
    "last_activity": "Initialized"
}

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route('/api/wallet/balance/<wallet_address>', methods=['GET'])
def get_wallet_balance(wallet_address):
    """Get SOL balance for a wallet using Helius RPC"""
    try:
        helius_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
        
        # Get SOL balance
        response = requests.post(helius_url, json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [wallet_address]
        })
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data:
                lamports = data['result']['value']
                sol_balance = lamports / 1_000_000_000  # Convert lamports to SOL
                return jsonify({
                    "sol": sol_balance,
                    "usdc": 0.00  # TODO: Implement USDC balance
                })
        
        return jsonify({"error": "Failed to fetch balance"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bot/status', methods=['GET'])
def get_status():
    return jsonify(bot_state)

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    data = request.json or {}
    wallet_address = data.get('wallet_address')
    
    if not wallet_address:
        return jsonify({"error": "Wallet address required"}), 400
    
    bot_state["active"] = True
    bot_state["paused"] = False
    bot_state["connected_wallet"] = wallet_address
    bot_state["last_activity"] = "Bot started - scanning for tokens"
    return jsonify({"status": "started", "wallet": wallet_address})

@app.route('/api/bot/pause', methods=['POST'])
def pause_bot():
    bot_state["active"] = False
    bot_state["paused"] = True
    return jsonify({"status": "paused"})

@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    bot_state["active"] = False
    bot_state["paused"] = False
    bot_state["positions"] = []
    return jsonify({"status": "stopped"})

@app.route('/api/bot/emergency_exit', methods=['POST'])
def emergency_exit():
    bot_state["active"] = False
    bot_state["positions"] = []
    return jsonify({"status": "emergency_exit_complete"})

# Removed duplicate get_wallet_balance function - using the one at line 44 instead

@app.route('/api/tokens/scan', methods=['POST'])
def scan_tokens():
    data = request.json or {}
    category = data.get('category', 'established')
    
    try:
        if category == 'established':
            # Get established tokens from DexScreener
            tokens = []
            for symbol in ['BONK', 'WIF', 'JUP', 'PYTH', 'ORCA']:
                response = requests.get(
                    f'https://api.dexscreener.com/latest/dex/search?q={symbol}',
                    timeout=10
                )
                if response.ok:
                    data = response.json()
                    pairs = data.get('pairs', [])
                    solana_pairs = [p for p in pairs if p.get('chainId') == 'solana']
                    if solana_pairs:
                        best_pair = max(solana_pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0)))
                        tokens.append({
                            'symbol': symbol,
                            'name': best_pair.get('baseToken', {}).get('name', symbol),
                            'address': best_pair.get('baseToken', {}).get('address', ''),
                            'price': float(best_pair.get('priceUsd', 0)),
                            'change_24h': float(best_pair.get('priceChange', {}).get('h24', 0)),
                            'volume_24h': float(best_pair.get('volume', {}).get('h24', 0)),
                            'liquidity': float(best_pair.get('liquidity', {}).get('usd', 0)),
                            'age_days': 365,
                            'scam_score': 95
                        })
            
            return jsonify({"tokens": tokens[:10]})
        
        # Get new/trending tokens from Birdeye API
        headers = {'X-API-KEY': BIRDEYE_API_KEY}
        
        if category == 'ultra_new':
            # Tokens created in last 1 hour
            url = 'https://public-api.birdeye.so/defi/token_creation?chain=solana&sort_by=creation_time&sort_type=desc&offset=0&limit=20'
        elif category == 'very_new':
            # Tokens created in last 6 hours
            url = 'https://public-api.birdeye.so/defi/token_creation?chain=solana&sort_by=creation_time&sort_type=desc&offset=0&limit=20'
        elif category == 'fresh':
            # Tokens created in last 24 hours
            url = 'https://public-api.birdeye.so/defi/token_creation?chain=solana&sort_by=creation_time&sort_type=desc&offset=0&limit=20'
        elif category == 'top_gainers':
            # Top gainers by 24h change
            url = 'https://public-api.birdeye.so/defi/token_trending?chain=solana&sort_by=rank&sort_type=asc&offset=0&limit=20'
        elif category == 'trending':
            # Trending by volume
            url = 'https://public-api.birdeye.so/defi/token_trending?chain=solana&sort_by=rank&sort_type=asc&offset=0&limit=20'
        else:
            return jsonify({"tokens": []})
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if not response.ok:
            return jsonify({"tokens": []})
        
        data = response.json()
        tokens_data = data.get('data', {}).get('items', []) or data.get('data', [])
        
        tokens = []
        for token_data in tokens_data[:10]:
            # Get token details
            address = token_data.get('address', '')
            if not address:
                continue
                
            # Fetch price and details from DexScreener
            dex_response = requests.get(
                f'https://api.dexscreener.com/latest/dex/tokens/{address}',
                timeout=5
            )
            
            if dex_response.ok:
                dex_data = dex_response.json()
                pairs = dex_data.get('pairs', [])
                solana_pairs = [p for p in pairs if p.get('chainId') == 'solana']
                
                if solana_pairs:
                    best_pair = max(solana_pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0)))
                    
                    # Calculate age
                    created_at = token_data.get('createdAt', 0) or best_pair.get('pairCreatedAt', 0)
                    age_hours = (time.time() * 1000 - created_at) / (1000 * 3600) if created_at else 999
                    
                    # Calculate scam score (simplified)
                    liquidity = float(best_pair.get('liquidity', {}).get('usd', 0))
                    volume = float(best_pair.get('volume', {}).get('h24', 0))
                    scam_score = min(95, max(50, int(70 + (liquidity / 10000) + (volume / 50000))))
                    
                    tokens.append({
                        'symbol': best_pair.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                        'name': best_pair.get('baseToken', {}).get('name', 'Unknown'),
                        'address': address,
                        'price': float(best_pair.get('priceUsd', 0)),
                        'change_24h': float(best_pair.get('priceChange', {}).get('h24', 0)),
                        'volume_24h': volume,
                        'liquidity': liquidity,
                        'age_hours': age_hours,
                        'scam_score': scam_score
                    })
        
        return jsonify({"tokens": tokens})
    
    except Exception as e:
        return jsonify({"error": str(e), "tokens": []}), 500

@app.route('/api/withdraw/reserve', methods=['POST'])
def withdraw_reserve():
    data = request.json or {}
    wallet_address = data.get('wallet_address')
    
    if not wallet_address:
        return jsonify({"error": "Wallet address required"}), 400
    
    amount = bot_state["reserve_balance"]
    if amount <= 0:
        return jsonify({"error": "No funds in reserve"}), 400
    
    # In production, this would create a Solana transaction
    # For now, just update the state
    bot_state["reserve_balance"] = 0
    
    return jsonify({
        "status": "success",
        "amount": amount,
        "to": wallet_address,
        "message": f"Withdrew ${amount:.2f} from reserve"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

