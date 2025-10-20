from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import requests
import time
from datetime import datetime
import json
import logging

app = Flask(__name__, static_folder='src', static_url_path='')
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Keys from environment
BIRDEYE_API_KEY = os.getenv('BIRDEYE_API_KEY', '')
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY', '')
HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# Jupiter API endpoints (Ultra Swap)
JUPITER_QUOTE_API = "https://lite-api.jup.ag/ultra/v1/order"
JUPITER_SWAP_API = "https://lite-api.jup.ag/ultra/v1/execute"

# Trading state
bot_state = {
    'active': False,
    'positions': [],
    'trades': [],
    'capital': 50.0,
    'reserve': 0.0,
    'wallet': None
}

@app.route('/')
def index():
    return send_from_directory('src', 'index_real_trading.html')

@app.route('/api/wallet/balance', methods=['POST'])
def get_wallet_balance():
    """Proxy endpoint to get wallet balance via Helius RPC"""
    try:
        data = request.json
        wallet_address = data.get('walletAddress')
        
        if not wallet_address:
            return jsonify({'error': 'Wallet address required'}), 400
        
        logger.info(f"Fetching balance for wallet: {wallet_address}")
        
        # Call Helius RPC
        response = requests.post(
            HELIUS_RPC,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [wallet_address]
            },
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                balance_lamports = result['result']['value']
                balance_sol = balance_lamports / 1_000_000_000
                logger.info(f"Balance fetched: {balance_sol} SOL")
                return jsonify({
                    'balance': balance_sol,
                    'lamports': balance_lamports
                })
        
        logger.error(f"RPC error: {response.text}")
        return jsonify({'error': 'Failed to fetch balance'}), 500
        
    except Exception as e:
        logger.error(f"Balance fetch error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tokens/scan', methods=['GET'])
def scan_tokens():
    """Scan for new and trending tokens using DexScreener API"""
    try:
        logger.info("=" * 80)
        logger.info("STARTING TOKEN SCAN")
        logger.info("=" * 80)
        
        tokens = []
        
        # Use DexScreener API as primary source (no auth required, reliable)
        dex_tokens = scan_dexscreener_tokens()
        if dex_tokens:
            tokens.extend(dex_tokens)
            logger.info(f"✓ Found {len(dex_tokens)} tokens from DexScreener")
        
        # Fallback to established tokens if nothing found
        if len(tokens) == 0:
            logger.warning("⚠ No tokens found from DexScreener, using fallback tokens")
            tokens = get_fallback_tokens()
        
        # Apply scam detection
        safe_tokens = []
        logger.info(f"\nApplying safety checks to {len(tokens)} tokens...")
        
        for token in tokens[:20]:  # Check top 20
            safety_score = calculate_safety_score(token)
            token['safetyScore'] = safety_score
            
            if safety_score >= 85:
                safe_tokens.append(token)
                logger.info(f"✓ {token['symbol']}: Safety Score {safety_score} - PASSED")
            else:
                logger.info(f"✗ {token['symbol']}: Safety Score {safety_score} - REJECTED")
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"SCAN COMPLETE: Returning {len(safe_tokens)} safe tokens")
        logger.info(f"{'=' * 80}\n")
        
        return jsonify(safe_tokens[:10])  # Return top 10
        
    except Exception as e:
        logger.error(f"❌ Token scan error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def scan_dexscreener_tokens():
    """Scan tokens from DexScreener API - primary source for new/trending tokens"""
    tokens = []
    
    try:
        logger.info("\n📡 Scanning DexScreener for trending Solana tokens...")
        
        # Get latest boosted tokens (these are trending/promoted)
        response = requests.get(
            'https://api.dexscreener.com/token-boosts/latest/v1',
            timeout=10
        )
        
        logger.info(f"DexScreener boosted tokens response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"Found {len(data)} boosted tokens")
                
                # Get detailed pair info for each token
                for item in data[:15]:  # Get top 15 boosted tokens
                    token_address = item.get('tokenAddress')
                    chain_id = item.get('chainId', 'solana')
                    
                    if token_address and chain_id == 'solana':
                        # Get pair details
                        pair_data = get_dexscreener_token_details(token_address)
                        if pair_data:
                            tokens.append(pair_data)
                            logger.info(f"  ✓ Added {pair_data.get('symbol', 'UNKNOWN')}")
        
        # If we don't have enough tokens, get from search
        if len(tokens) < 5:
            logger.info("\n📡 Getting additional tokens from DexScreener search...")
            search_tokens = search_dexscreener_trending()
            tokens.extend(search_tokens)
        
    except Exception as e:
        logger.error(f"❌ DexScreener error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    return tokens

def get_dexscreener_token_details(token_address):
    """Get detailed token information from DexScreener"""
    try:
        response = requests.get(
            f'https://api.dexscreener.com/latest/dex/tokens/{token_address}',
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if 'pairs' in data and len(data['pairs']) > 0:
                # Get the most liquid pair
                pairs = sorted(data['pairs'], key=lambda x: float(x.get('liquidity', {}).get('usd', 0)), reverse=True)
                pair = pairs[0]
                
                return parse_dexscreener_pair(pair)
    except Exception as e:
        logger.error(f"Error getting token details for {token_address}: {str(e)}")
    
    return None

def search_dexscreener_trending():
    """Search for trending tokens on DexScreener"""
    tokens = []
    
    try:
        # Search for popular Solana tokens
        search_terms = ['SOL', 'BONK', 'WIF', 'POPCAT', 'MEW']
        
        for term in search_terms[:3]:  # Limit to avoid rate limits
            response = requests.get(
                f'https://api.dexscreener.com/latest/dex/search?q={term}',
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'pairs' in data:
                    # Filter for Solana pairs with good volume
                    solana_pairs = [p for p in data['pairs'] if p.get('chainId') == 'solana']
                    solana_pairs = sorted(solana_pairs, key=lambda x: float(x.get('volume', {}).get('h24', 0)), reverse=True)
                    
                    for pair in solana_pairs[:2]:  # Top 2 per search
                        token = parse_dexscreener_pair(pair)
                        if token and token not in tokens:
                            tokens.append(token)
                            logger.info(f"  ✓ Added {token.get('symbol', 'UNKNOWN')} from search")
            
            time.sleep(0.5)  # Rate limit protection
    
    except Exception as e:
        logger.error(f"Error searching DexScreener: {str(e)}")
    
    return tokens

def parse_dexscreener_pair(pair):
    """Parse DexScreener pair data into standard format"""
    try:
        base_token = pair.get('baseToken', {})
        price_change = pair.get('priceChange', {})
        volume = pair.get('volume', {})
        liquidity = pair.get('liquidity', {})
        
        # Calculate age (newer tokens are more interesting)
        pair_created = pair.get('pairCreatedAt', 0)
        age_hours = (time.time() * 1000 - pair_created) / (1000 * 60 * 60) if pair_created else 999999
        
        return {
            'address': base_token.get('address', ''),
            'symbol': base_token.get('symbol', 'UNKNOWN'),
            'name': base_token.get('name', 'Unknown Token'),
            'price': float(pair.get('priceUsd', 0)),
            'priceChange24h': float(price_change.get('h24', 0)),
            'volume24h': float(volume.get('h24', 0)),
            'liquidity': float(liquidity.get('usd', 0)),
            'marketCap': float(pair.get('marketCap', 0)),
            'holder': 0,  # DexScreener doesn't provide holder count
            'source': 'dexscreener',
            'dexId': pair.get('dexId', ''),
            'pairAddress': pair.get('pairAddress', ''),
            'ageHours': age_hours,
            'url': pair.get('url', '')
        }
    except Exception as e:
        logger.error(f"Error parsing DexScreener pair: {str(e)}")
        return None

def get_fallback_tokens():
    """Return established tokens as fallback"""
    logger.info("Using fallback established tokens")
    return [
        {
            'address': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
            'symbol': 'BONK',
            'name': 'Bonk',
            'price': 0.00001234,
            'priceChange24h': 5.2,
            'volume24h': 15000000,
            'liquidity': 8000000,
            'marketCap': 500000000,
            'holder': 150000,
            'source': 'fallback',
            'safetyScore': 95
        },
        {
            'address': 'orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE',
            'symbol': 'ORCA',
            'name': 'Orca',
            'price': 3.45,
            'priceChange24h': 3.1,
            'volume24h': 5000000,
            'liquidity': 12000000,
            'marketCap': 300000000,
            'holder': 50000,
            'source': 'fallback',
            'safetyScore': 98
        },
        {
            'address': 'HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3',
            'symbol': 'PYTH',
            'name': 'Pyth Network',
            'price': 0.42,
            'priceChange24h': 2.8,
            'volume24h': 8000000,
            'liquidity': 6000000,
            'marketCap': 200000000,
            'holder': 30000,
            'source': 'fallback',
            'safetyScore': 96
        }
    ]

def calculate_safety_score(token):
    """Calculate safety score for a token (0-100)"""
    score = 100
    
    # Check liquidity (very important for avoiding rug pulls)
    liquidity = token.get('liquidity', 0)
    if liquidity < 5000:
        score -= 40
        logger.debug(f"  - Low liquidity (${liquidity:.0f}): -40 points")
    elif liquidity < 20000:
        score -= 20
        logger.debug(f"  - Medium liquidity (${liquidity:.0f}): -20 points")
    elif liquidity < 50000:
        score -= 10
        logger.debug(f"  - Moderate liquidity (${liquidity:.0f}): -10 points")
    
    # Check volume (indicates real trading activity)
    volume = token.get('volume24h', 0)
    if volume < 1000:
        score -= 25
        logger.debug(f"  - Very low volume (${volume:.0f}): -25 points")
    elif volume < 10000:
        score -= 15
        logger.debug(f"  - Low volume (${volume:.0f}): -15 points")
    elif volume < 50000:
        score -= 5
        logger.debug(f"  - Moderate volume (${volume:.0f}): -5 points")
    
    # Check price change (avoid extreme pumps that might dump)
    price_change = abs(token.get('priceChange24h', 0))
    if price_change > 200:
        score -= 30
        logger.debug(f"  - Extreme price change ({price_change:.1f}%): -30 points")
    elif price_change > 100:
        score -= 15
        logger.debug(f"  - High price change ({price_change:.1f}%): -15 points")
    elif price_change > 50:
        score -= 5
        logger.debug(f"  - Moderate price change ({price_change:.1f}%): -5 points")
    
    # Bonus for newer tokens (if age data available)
    age_hours = token.get('ageHours', 999999)
    if age_hours < 24:
        score += 5
        logger.debug(f"  + Very new token ({age_hours:.1f}h): +5 points")
    elif age_hours < 168:  # 1 week
        score += 3
        logger.debug(f"  + New token ({age_hours:.1f}h): +3 points")
    
    final_score = max(0, min(100, score))
    logger.debug(f"  Final safety score: {final_score}")
    
    return final_score

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    """Start the trading bot"""
    try:
        data = request.json
        bot_state['active'] = True
        bot_state['wallet'] = data.get('walletAddress')
        bot_state['capital'] = float(data.get('capital', 50))
        
        logger.info(f"🤖 Bot started with capital: ${bot_state['capital']}, wallet: {bot_state['wallet']}")
        
        return jsonify({
            'success': True,
            'message': 'Bot started successfully',
            'state': bot_state
        })
    except Exception as e:
        logger.error(f"Bot start error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    """Stop the trading bot"""
    try:
        bot_state['active'] = False
        logger.info("🛑 Bot stopped")
        
        return jsonify({
            'success': True,
            'message': 'Bot stopped successfully',
            'state': bot_state
        })
    except Exception as e:
        logger.error(f"Bot stop error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bot/status', methods=['GET'])
def get_bot_status():
    """Get current bot status"""
    return jsonify(bot_state)

@app.route('/api/jupiter/quote', methods=['POST'])
def get_jupiter_quote():
    """Get quote from Jupiter Ultra Swap API"""
    try:
        data = request.json
        input_mint = data.get('inputMint')
        output_mint = data.get('outputMint')
        amount = data.get('amount')
        taker = data.get('taker')  # Wallet address
        
        logger.info(f"💱 Getting Jupiter quote: {input_mint[:8]}... -> {output_mint[:8]}..., amount: {amount}")
        
        # Jupiter Ultra Swap API parameters
        params = {
            'inputMint': input_mint,
            'outputMint': output_mint,
            'amount': amount,
            'taker': taker
        }
        
        logger.info(f"Request params: {params}")
        
        response = requests.get(
            JUPITER_QUOTE_API,
            params=params,
            timeout=15
        )
        
        logger.info(f"Jupiter response status: {response.status_code}")
        
        if response.status_code == 200:
            quote = response.json()
            logger.info(f"✓ Jupiter quote received: {json.dumps(quote)[:300]}...")
            return jsonify(quote)
        else:
            error_text = response.text
            logger.error(f"❌ Jupiter quote error: {response.status_code} - {error_text}")
            return jsonify({'error': f'Jupiter API error: {error_text}'}), response.status_code
            
    except Exception as e:
        logger.error(f"❌ Jupiter quote error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/jupiter/swap', methods=['POST'])
def execute_jupiter_swap():
    """Execute swap on Jupiter Ultra Swap API"""
    try:
        data = request.json
        request_id = data.get('requestId')
        signed_transaction = data.get('signedTransaction')
        
        if not request_id or not signed_transaction:
            return jsonify({'error': 'Missing requestId or signedTransaction'}), 400
        
        logger.info(f"🔄 Executing Jupiter swap with requestId: {request_id}")
        
        # Execute the swap
        response = requests.post(
            JUPITER_SWAP_API,
            json={
                'requestId': request_id,
                'signedTransaction': signed_transaction
            },
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        logger.info(f"Jupiter execute response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ Jupiter swap executed: {json.dumps(result)[:300]}...")
            return jsonify(result)
        else:
            error_text = response.text
            logger.error(f"❌ Jupiter execute error: {response.status_code} - {error_text}")
            return jsonify({'error': f'Jupiter execute error: {error_text}'}), response.status_code
            
    except Exception as e:
        logger.error(f"❌ Jupiter swap error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Starting Nova Trading Bot Backend on port {port}")
    logger.info(f"   HELIUS_API_KEY: {'✓ Set' if HELIUS_API_KEY else '✗ Missing'}")
    logger.info(f"   BIRDEYE_API_KEY: {'✓ Set' if BIRDEYE_API_KEY else '✗ Missing (optional)'}")
    app.run(host='0.0.0.0', port=port, debug=False)

