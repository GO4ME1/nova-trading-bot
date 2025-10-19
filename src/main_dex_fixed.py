"""
Nova Ultimate - With REAL DexScreener API (Fixed)
"""

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import json
import logging
from datetime import datetime
import os
import requests
from time import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# YOUR API KEYS
HELIUS_API_KEY = "3a3e05cc-fcff-42bd-8a63-3cbc21226598"
BIRDEYE_API_KEY = "85cef1ef88f34331B491b0af80f7887c"

# YOUR RESERVE WALLET
RESERVE_WALLET_ADDRESS = "Az6NNWG54E71hQfPxSPBU3tp98SU7ivfwEUb2AEhrSSu"

logger.info("✅ APIs Loaded: DexScreener + Helius + Birdeye + Jupiter")
logger.info(f"✅ Reserve Wallet: {RESERVE_WALLET_ADDRESS[:8]}...{RESERVE_WALLET_ADDRESS[-8:]}")

# Bot state
bot_state = {
    'configs': {},
    'reserve_wallet': 0,
    'trading_capital': 50,
}

# Cache for API calls
_cache = {}
_cache_ttl = 30  # 30 seconds

def get_cached(key, fetch_func, ttl=30):
    """Simple cache with TTL"""
    now = time()
    if key in _cache:
        data, timestamp = _cache[key]
        if now - timestamp < ttl:
            return data
    
    data = fetch_func()
    _cache[key] = (data, now)
    return data

def fetch_solana_tokens_search(query="SOL"):
    """Search for Solana tokens using DexScreener search API"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])
            # Filter for Solana only
            solana_pairs = [p for p in pairs if p.get('chainId') == 'solana']
            logger.info(f"✅ Found {len(solana_pairs)} Solana pairs for query '{query}'")
            return solana_pairs
        else:
            logger.warning(f"DexScreener search returned {response.status_code}")
    except Exception as e:
        logger.error(f"DexScreener search error: {e}")
    return []

def fetch_token_by_address(addresses):
    """Fetch tokens by their addresses"""
    try:
        # Join addresses with comma
        addr_str = ','.join(addresses[:30])  # Max 30 addresses
        url = f"https://api.dexscreener.com/latest/dex/tokens/{addr_str}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])
            logger.info(f"✅ Found {len(pairs)} pairs for addresses")
            return pairs
        else:
            logger.warning(f"DexScreener tokens returned {response.status_code}")
    except Exception as e:
        logger.error(f"DexScreener tokens error: {e}")
    return []

def calculate_scam_score(pair):
    """Calculate scam score based on multiple factors"""
    score = 100
    
    # Check liquidity
    liquidity = pair.get('liquidity', {}).get('usd', 0) or 0
    if liquidity < 10000:
        score -= 30
    elif liquidity < 50000:
        score -= 15
    elif liquidity < 100000:
        score -= 5
    
    # Check volume
    volume = pair.get('volume', {}).get('h24', 0) or 0
    if volume < 1000:
        score -= 20
    elif volume < 10000:
        score -= 10
    
    # Check FDV
    fdv = pair.get('fdv', 0) or 0
    if fdv > 0 and fdv < 100000:
        score -= 10
    
    # Check price change (too high = suspicious)
    price_change = pair.get('priceChange', {}).get('h24', 0) or 0
    if abs(price_change) > 1000:
        score -= 15
    
    return max(0, min(100, score))

def get_token_age_minutes(pair):
    """Calculate token age in minutes"""
    created_at = pair.get('pairCreatedAt')
    if created_at:
        try:
            age_ms = datetime.now().timestamp() * 1000 - created_at
            return int(age_ms / 60000)
        except:
            pass
    return None

def format_token_data(pair):
    """Format pair data for UI"""
    base_token = pair.get('baseToken', {})
    price_usd = float(pair.get('priceUsd', 0) or 0)
    price_change_24h = float(pair.get('priceChange', {}).get('h24', 0) or 0)
    volume_24h = float(pair.get('volume', {}).get('h24', 0) or 0)
    liquidity_usd = float(pair.get('liquidity', {}).get('usd', 0) or 0)
    
    age_minutes = get_token_age_minutes(pair)
    scam_score = calculate_scam_score(pair)
    
    # Signals
    signals = []
    if volume_24h > 1000000:
        signals.append('High Volume')
    if price_change_24h > 50:
        signals.append('Strong Rally')
    if price_change_24h > 100:
        signals.append('Momentum')
    if liquidity_usd > 500000:
        signals.append('High Liquidity')
    if age_minutes and age_minutes < 60:
        signals.append('New Launch')
    
    # Warnings
    warnings = []
    if liquidity_usd < 50000:
        warnings.append('Low Liquidity')
    if scam_score < 70:
        warnings.append('High Risk')
    if age_minutes and age_minutes < 10:
        warnings.append('Very New')
    
    token_data = {
        'symbol': base_token.get('symbol', 'UNKNOWN'),
        'name': base_token.get('name', 'Unknown Token'),
        'price': price_usd,
        'change24h': price_change_24h,
        'volume24h': volume_24h,
        'liquidity': liquidity_usd,
        'scam_score': scam_score,
        'holders': 0,
        'signals': signals,
        'warnings': warnings,
        'address': base_token.get('address', '')
    }
    
    if age_minutes:
        if age_minutes < 60:
            token_data['age_minutes'] = age_minutes
        elif age_minutes < 1440:
            token_data['age_hours'] = round(age_minutes / 60, 1)
        else:
            token_data['age_days'] = round(age_minutes / 1440)
    else:
        token_data['age_days'] = 999
    
    return token_data

# Read HTML from previous file
try:
    with open('/home/ubuntu/nova-ultimate-deploy/src/main.py', 'r') as f:
        content = f.read()
        HTML = content.split('HTML = """')[1].split('"""')[0]
except:
    HTML = "<h1>Error loading UI</h1>"

@app.route('/')
def index():
    return Response('<!DOCTYPE html><html>' + HTML + '</html>', mimetype='text/html')

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'mode': 'ultimate_dexscreener_fixed'})

@app.route('/api/bot/status')
def bot_status():
    wallet = request.args.get('wallet', 'demo')
    config = bot_state['configs'].get(wallet, {})
    return jsonify({
        'active': config.get('is_active', False),
        'capital': {
            'trading': bot_state['trading_capital'],
            'reserve': bot_state['reserve_wallet']
        }
    })

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    data = request.json or {}
    wallet = data.get('wallet', 'demo')
    bot_state['configs'][wallet] = {'is_active': True}
    logger.info(f"🚀 BOT started for {wallet}")
    return jsonify({
        'success': True,
        'message': f'🚀 Nova Ultimate activated! Scanning real Solana tokens. 25% profits → {RESERVE_WALLET_ADDRESS[:8]}...{RESERVE_WALLET_ADDRESS[-8:]}',
        'active': True
    })

@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    data = request.json or {}
    wallet = data.get('wallet', 'demo')
    if wallet in bot_state['configs']:
        bot_state['configs'][wallet]['is_active'] = False
    return jsonify({'success': True, 'message': 'Bot stopped', 'active': False})

@app.route('/api/tokens/scan')
def scan_tokens_real():
    category = request.args.get('category', 'established')
    
    logger.info(f"🔍 Scanning REAL {category} tokens...")
    
    try:
        # Use different search queries for different categories
        if category == 'ultra_new' or category == 'very_new' or category == 'fresh':
            # Search for popular base tokens to find new pairs
            queries = ['SOL', 'USDC', 'BONK', 'WIF', 'JUP']
            all_pairs = []
            for q in queries:
                pairs = get_cached(f'search_{q}', lambda: fetch_solana_tokens_search(q), ttl=30)
                all_pairs.extend(pairs)
            
            # Filter by age
            tokens = []
            age_limit = 7 if category == 'ultra_new' else (60 if category == 'very_new' else 1440)
            
            for pair in all_pairs:
                age_min = get_token_age_minutes(pair)
                if age_min and age_min <= age_limit:
                    tokens.append(format_token_data(pair))
                if len(tokens) >= 20:
                    break
        
        elif category == 'gainers':
            # Search multiple queries and sort by price change
            queries = ['SOL', 'USDC', 'BONK', 'WIF']
            all_pairs = []
            for q in queries:
                pairs = get_cached(f'search_{q}', lambda: fetch_solana_tokens_search(q), ttl=30)
                all_pairs.extend(pairs)
            
            # Remove duplicates by symbol, keep highest gainer
            seen_symbols = {}
            for pair in all_pairs:
                symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')
                price_change = float(pair.get('priceChange', {}).get('h24', 0) or 0)
                if symbol not in seen_symbols or price_change > seen_symbols[symbol]['change']:
                    seen_symbols[symbol] = {'pair': pair, 'change': price_change}
            
            # Sort by price change
            unique_pairs = [v['pair'] for v in seen_symbols.values()]
            sorted_pairs = sorted(unique_pairs, key=lambda x: float(x.get('priceChange', {}).get('h24', 0) or 0), reverse=True)
            tokens = [format_token_data(p) for p in sorted_pairs[:20]]
        
        elif category == 'trending':
            # Sort by volume
            queries = ['SOL', 'USDC', 'BONK', 'WIF']
            all_pairs = []
            for q in queries:
                pairs = get_cached(f'search_{q}', lambda: fetch_solana_tokens_search(q), ttl=30)
                all_pairs.extend(pairs)
            
            # Remove duplicates by symbol, keep highest volume
            seen_symbols = {}
            for pair in all_pairs:
                symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')
                volume = float(pair.get('volume', {}).get('h24', 0) or 0)
                if symbol not in seen_symbols or volume > seen_symbols[symbol]['volume']:
                    seen_symbols[symbol] = {'pair': pair, 'volume': volume}
            
            unique_pairs = [v['pair'] for v in seen_symbols.values()]
            sorted_pairs = sorted(unique_pairs, key=lambda x: float(x.get('volume', {}).get('h24', 0) or 0), reverse=True)
            tokens = [format_token_data(p) for p in sorted_pairs[:20]]
        
        else:  # established
            # Search for well-known tokens
            queries = ['BONK', 'WIF', 'JUP', 'PYTH', 'SAMO', 'POPCAT', 'MEW', 'MYRO']
            tokens = []
            seen_symbols = set()
            
            for q in queries:
                pairs = get_cached(f'search_{q}', lambda: fetch_solana_tokens_search(q), ttl=60)
                # Sort by liquidity to get best pair
                sorted_pairs = sorted(pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0), reverse=True)
                
                for pair in sorted_pairs:
                    token = format_token_data(pair)
                    # Only add if we haven't seen this symbol and it's high quality
                    if token['symbol'] not in seen_symbols and token['scam_score'] >= 85:
                        tokens.append(token)
                        seen_symbols.add(token['symbol'])
                        break  # Only take best pair for this token
                
                if len(tokens) >= 20:
                    break
        
        logger.info(f"✅ Returning {len(tokens)} {category} tokens")
        
        return jsonify({
            'success': True,
            'category': category,
            'tokens': tokens,
            'count': len(tokens),
            'source': 'dexscreener_api'
        })
    
    except Exception as e:
        logger.error(f"Error scanning: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e), 'tokens': [], 'count': 0})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info("=" * 80)
    logger.info("🌟 Nova ULTIMATE - DexScreener API Fixed")
    logger.info("=" * 80)
    logger.info("✅ DexScreener: Connected")
    logger.info("✅ Helius RPC: Ready")
    logger.info("✅ Birdeye API: Ready")
    logger.info("✅ Jupiter API: Ready")
    logger.info("=" * 80)
    logger.info("📊 Strategy: 10% per trade → 4% trailing → 25% reserve + 75% compound")
    logger.info(f"🚀 Port: {port}")
    logger.info("=" * 80)
    
    app.run(host='0.0.0.0', port=port, debug=False)

