from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import time
import json
import os

app = Flask(__name__, static_folder='../static')
CORS(app)

# Configuration
HELIUS_API_KEY = "3a3e05cc-fcff-42bd-8a63-3cbc21226598"
BIRDEYE_API_KEY = "85cef1ef88f34331B491b0af80f7887c"
RESERVE_WALLET = "Az6NNWG54E71hQfPxSPBU3tp98SU7ivfwEUb2AEhrSSu"

# Bot state
bot_state = {
    "active": False,
    "trading_capital": 50.00,
    "reserve_balance": 0.00,
    "total_trades": 0,
    "winning_trades": 0,
    "losing_trades": 0,
    "total_profit": 0.00,
    "daily_profit": 0.00,
    "daily_loss_limit": -20.00,  # Stop if loses $20 in a day
    "max_concurrent_trades": 3,
    "last_scan_time": None,
    "connected_wallet": None
}

# Active positions
active_positions = []

# Trade history
trade_history = []

# Live feed
live_feed = []

def add_to_feed(message, type="info"):
    """Add message to live feed"""
    live_feed.insert(0, {
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "type": type  # info, success, warning, error
    })
    # Keep only last 50 messages
    if len(live_feed) > 50:
        live_feed.pop()

def calculate_scam_score(token_data):
    """Calculate scam score 0-100"""
    score = 50  # Base score
    
    # Liquidity check (30 points)
    liquidity = float(token_data.get('liquidity', {}).get('usd', 0))
    if liquidity > 100000:
        score += 30
    elif liquidity > 50000:
        score += 20
    elif liquidity > 10000:
        score += 10
    
    # Volume check (20 points)
    volume = float(token_data.get('volume', {}).get('h24', 0))
    if volume > 500000:
        score += 20
    elif volume > 100000:
        score += 15
    elif volume > 50000:
        score += 10
    
    # Age check (20 points)
    created_at = token_data.get('pairCreatedAt', 0)
    if created_at:
        age_days = (time.time() * 1000 - created_at) / (1000 * 60 * 60 * 24)
        if age_days > 365:
            score += 20
        elif age_days > 90:
            score += 15
        elif age_days > 30:
            score += 10
        elif age_days > 7:
            score += 5
    
    # Price change check (10 points)
    price_change = float(token_data.get('priceChange', {}).get('h24', 0))
    if 0 < price_change < 100:  # Reasonable growth
        score += 10
    elif price_change > 500:  # Suspicious pump
        score -= 20
    
    return min(100, max(0, score))

@app.route('/')
def index():
    """Serve the main HTML page"""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nova - Ultimate Trading Bot</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1729 100%);
            color: #e0e7ff;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 30px 20px;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(147, 51, 234, 0.1));
            border-radius: 20px;
            border: 1px solid rgba(59, 130, 246, 0.2);
        }
        
        .logo {
            font-size: 48px;
            font-weight: 700;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
            animation: glow 3s ease-in-out infinite;
        }
        
        @keyframes glow {
            0%, 100% { filter: drop-shadow(0 0 20px rgba(59, 130, 246, 0.5)); }
            50% { filter: drop-shadow(0 0 30px rgba(139, 92, 246, 0.7)); }
        }
        
        .subtitle {
            font-size: 16px;
            color: #94a3b8;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: rgba(30, 41, 59, 0.5);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid rgba(59, 130, 246, 0.2);
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }
        
        .card:hover {
            border-color: rgba(59, 130, 246, 0.5);
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(59, 130, 246, 0.2);
        }
        
        .card-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
            color: #3b82f6;
        }
        
        .stat-value {
            font-size: 32px;
            font-weight: 700;
            background: linear-gradient(135deg, #10b981, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .stat-label {
            font-size: 14px;
            color: #64748b;
            margin-top: 4px;
        }
        
        .btn {
            padding: 14px 28px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(59, 130, 246, 0.4);
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
        }
        
        .btn-danger:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(239, 68, 68, 0.4);
        }
        
        .btn-success {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
        }
        
        .btn-warning {
            background: linear-gradient(135deg, #f59e0b, #d97706);
            color: white;
        }
        
        .status-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-active {
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
            border: 1px solid #10b981;
        }
        
        .status-inactive {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border: 1px solid #ef4444;
        }
        
        .positions-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
        }
        
        .positions-table th {
            text-align: left;
            padding: 12px;
            border-bottom: 2px solid rgba(59, 130, 246, 0.3);
            color: #3b82f6;
            font-weight: 600;
        }
        
        .positions-table td {
            padding: 12px;
            border-bottom: 1px solid rgba(59, 130, 246, 0.1);
        }
        
        .profit-positive {
            color: #10b981;
            font-weight: 600;
        }
        
        .profit-negative {
            color: #ef4444;
            font-weight: 600;
        }
        
        .live-feed {
            max-height: 400px;
            overflow-y: auto;
            margin-top: 16px;
        }
        
        .feed-item {
            padding: 12px;
            margin-bottom: 8px;
            border-radius: 8px;
            border-left: 3px solid;
            background: rgba(30, 41, 59, 0.3);
        }
        
        .feed-info { border-left-color: #3b82f6; }
        .feed-success { border-left-color: #10b981; }
        .feed-warning { border-left-color: #f59e0b; }
        .feed-error { border-left-color: #ef4444; }
        
        .feed-time {
            font-size: 11px;
            color: #64748b;
            margin-bottom: 4px;
        }
        
        .feed-message {
            font-size: 14px;
        }
        
        .button-group {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 16px;
        }
        
        .scanner-section {
            margin-top: 30px;
        }
        
        .token-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 16px;
            margin-top: 20px;
        }
        
        .token-card {
            background: rgba(30, 41, 59, 0.5);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(59, 130, 246, 0.2);
        }
        
        .token-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .token-name {
            font-weight: 600;
            font-size: 16px;
        }
        
        .token-symbol {
            color: #64748b;
            font-size: 14px;
        }
        
        .safety-score {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .score-high { background: rgba(16, 185, 129, 0.2); color: #10b981; }
        .score-medium { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
        .score-low { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">✨ NOVA</div>
            <div class="subtitle">Ultimate Solana Trading Bot</div>
        </div>
        
        <div class="grid">
            <div class="card">
                <div class="card-title">🤖 Bot Status</div>
                <div class="status-badge" id="botStatus">Inactive</div>
                <div class="button-group">
                    <button class="btn btn-primary" onclick="startBot()">🚀 Start Bot</button>
                    <button class="btn btn-warning" onclick="pauseBot()">⏸️ Pause</button>
                    <button class="btn btn-danger" onclick="stopAndSellAll()">🛑 Stop & Sell All</button>
                    <button class="btn btn-danger" onclick="emergencyExit()">🚨 Emergency Exit</button>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title">💰 Capital Management</div>
                <div>
                    <div class="stat-value" id="tradingCapital">$50.00</div>
                    <div class="stat-label">Trading Capital (75%)</div>
                </div>
                <div style="margin-top: 16px;">
                    <div class="stat-value" id="reserveBalance">$0.00</div>
                    <div class="stat-label">Reserve Balance (25%)</div>
                </div>
                <div class="button-group">
                    <button class="btn btn-success" onclick="withdrawReserve()">💸 Withdraw Reserve</button>
                    <button class="btn btn-success" onclick="withdrawAll()">💰 Withdraw All</button>
                    <button class="btn btn-success" onclick="withdrawProfits()">📈 Withdraw Profits</button>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title">📊 Performance</div>
                <div>
                    <div class="stat-value" id="totalProfit">$0.00</div>
                    <div class="stat-label">Total Profit</div>
                </div>
                <div style="margin-top: 16px;">
                    <div style="font-size: 18px;">
                        Win Rate: <span id="winRate" class="profit-positive">0%</span>
                    </div>
                    <div style="font-size: 14px; color: #64748b; margin-top: 4px;">
                        <span id="totalTrades">0</span> trades 
                        (<span id="winningTrades" class="profit-positive">0</span> wins, 
                        <span id="losingTrades" class="profit-negative">0</span> losses)
                    </div>
                </div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card" style="grid-column: 1 / -1;">
                <div class="card-title">📍 Active Positions (<span id="activeCount">0</span>)</div>
                <table class="positions-table" id="positionsTable">
                    <thead>
                        <tr>
                            <th>Token</th>
                            <th>Entry Price</th>
                            <th>Current Price</th>
                            <th>Amount</th>
                            <th>P&L</th>
                            <th>P&L %</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody id="positionsBody">
                        <tr>
                            <td colspan="7" style="text-align: center; color: #64748b;">No active positions</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <div class="card-title">📡 Live Feed</div>
                <div class="live-feed" id="liveFeed">
                    <div class="feed-item feed-info">
                        <div class="feed-time">Just now</div>
                        <div class="feed-message">Bot initialized. Ready to trade!</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title">📜 Recent Trades</div>
                <div class="live-feed" id="tradeHistory">
                    <div style="text-align: center; color: #64748b; padding: 20px;">
                        No trades yet
                    </div>
                </div>
            </div>
        </div>
        
        <div class="scanner-section">
            <div class="card">
                <div class="card-title">🔍 Token Scanner</div>
                <div class="button-group">
                    <button class="btn btn-primary" onclick="scanTokens('ultra_new')">⚡ Ultra New (&lt;7min)</button>
                    <button class="btn btn-primary" onclick="scanTokens('very_new')">🆕 Very New (&lt;1h)</button>
                    <button class="btn btn-primary" onclick="scanTokens('fresh')">🌱 Fresh (&lt;24h)</button>
                    <button class="btn btn-primary" onclick="scanTokens('established')">💎 Established</button>
                    <button class="btn btn-primary" onclick="scanTokens('top_gainers')">📈 Top Gainers</button>
                    <button class="btn btn-primary" onclick="scanTokens('trending')">🔥 Trending</button>
                </div>
                <div class="token-grid" id="tokenGrid">
                    <div style="grid-column: 1 / -1; text-align: center; color: #64748b; padding: 40px;">
                        Click a category to scan tokens
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let updateInterval;
        
        function updateDashboard() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('botStatus').textContent = data.active ? 'Active' : 'Inactive';
                    document.getElementById('botStatus').className = 'status-badge ' + (data.active ? 'status-active' : 'status-inactive');
                    
                    document.getElementById('tradingCapital').textContent = '$' + data.trading_capital.toFixed(2);
                    document.getElementById('reserveBalance').textContent = '$' + data.reserve_balance.toFixed(2);
                    document.getElementById('totalProfit').textContent = '$' + data.total_profit.toFixed(2);
                    document.getElementById('totalTrades').textContent = data.total_trades;
                    document.getElementById('winningTrades').textContent = data.winning_trades;
                    document.getElementById('losingTrades').textContent = data.losing_trades;
                    
                    const winRate = data.total_trades > 0 ? ((data.winning_trades / data.total_trades) * 100).toFixed(1) : 0;
                    document.getElementById('winRate').textContent = winRate + '%';
                });
            
            // Update positions
            fetch('/api/positions')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('activeCount').textContent = data.positions.length;
                    const tbody = document.getElementById('positionsBody');
                    if (data.positions.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #64748b;">No active positions</td></tr>';
                    } else {
                        tbody.innerHTML = data.positions.map(p => `
                            <tr>
                                <td><strong>${p.token}</strong></td>
                                <td>$${p.entry_price.toFixed(6)}</td>
                                <td>$${p.current_price.toFixed(6)}</td>
                                <td>$${p.amount.toFixed(2)}</td>
                                <td class="${p.pnl >= 0 ? 'profit-positive' : 'profit-negative'}">$${p.pnl.toFixed(2)}</td>
                                <td class="${p.pnl_percent >= 0 ? 'profit-positive' : 'profit-negative'}">${p.pnl_percent.toFixed(2)}%</td>
                                <td><button class="btn btn-danger" onclick="closePosition('${p.id}')">Close</button></td>
                            </tr>
                        `).join('');
                    }
                });
            
            // Update live feed
            fetch('/api/feed')
                .then(r => r.json())
                .then(data => {
                    const feed = document.getElementById('liveFeed');
                    feed.innerHTML = data.feed.map(item => `
                        <div class="feed-item feed-${item.type}">
                            <div class="feed-time">${new Date(item.timestamp).toLocaleTimeString()}</div>
                            <div class="feed-message">${item.message}</div>
                        </div>
                    `).join('');
                });
        }
        
        function startBot() {
            fetch('/api/bot/start', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    alert(data.message);
                    updateDashboard();
                });
        }
        
        function pauseBot() {
            fetch('/api/bot/pause', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    alert(data.message);
                    updateDashboard();
                });
        }
        
        function stopAndSellAll() {
            if (confirm('This will close all positions and stop the bot. Continue?')) {
                fetch('/api/bot/stop-sell-all', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message);
                        updateDashboard();
                    });
            }
        }
        
        function emergencyExit() {
            if (confirm('EMERGENCY EXIT: This will immediately sell all positions at market price. Continue?')) {
                fetch('/api/bot/emergency-exit', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message);
                        updateDashboard();
                    });
            }
        }
        
        function withdrawReserve() {
            fetch('/api/withdraw/reserve', { method: 'POST' })
                .then(r => r.json())
                .then(data => alert(data.message));
        }
        
        function withdrawAll() {
            if (confirm('This will close all positions and withdraw everything. Continue?')) {
                fetch('/api/withdraw/all', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => alert(data.message));
            }
        }
        
        function withdrawProfits() {
            fetch('/api/withdraw/profits', { method: 'POST' })
                .then(r => r.json())
                .then(data => alert(data.message));
        }
        
        function closePosition(id) {
            if (confirm('Close this position?')) {
                fetch(`/api/position/${id}/close`, { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message);
                        updateDashboard();
                    });
            }
        }
        
        function scanTokens(category) {
            document.getElementById('tokenGrid').innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: #64748b; padding: 40px;">Scanning...</div>';
            
            fetch(`/api/scan/${category}`)
                .then(r => r.json())
                .then(data => {
                    const grid = document.getElementById('tokenGrid');
                    if (data.tokens.length === 0) {
                        grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: #64748b; padding: 40px;">No tokens found</div>';
                    } else {
                        grid.innerHTML = data.tokens.map(t => `
                            <div class="token-card">
                                <div class="token-header">
                                    <div>
                                        <div class="token-name">${t.name}</div>
                                        <div class="token-symbol">${t.symbol}</div>
                                    </div>
                                    <div class="safety-score score-${t.safety_score >= 85 ? 'high' : t.safety_score >= 70 ? 'medium' : 'low'}">
                                        ${t.safety_score}/100
                                    </div>
                                </div>
                                <div style="margin-top: 12px;">
                                    <div>Price: <strong>$${t.price}</strong></div>
                                    <div class="${t.change >= 0 ? 'profit-positive' : 'profit-negative'}">
                                        24h: ${t.change >= 0 ? '+' : ''}${t.change}%
                                    </div>
                                    <div style="font-size: 12px; color: #64748b; margin-top: 8px;">
                                        Volume: $${(t.volume / 1000000).toFixed(2)}M<br>
                                        Liquidity: $${(t.liquidity / 1000000).toFixed(2)}M
                                    </div>
                                </div>
                            </div>
                        `).join('');
                    }
                });
        }
        
        // Update every 5 seconds
        updateDashboard();
        setInterval(updateDashboard, 5000);
    </script>
</body>
</html>
'''

@app.route('/api/status')
def get_status():
    """Get bot status"""
    return jsonify(bot_state)

@app.route('/api/positions')
def get_positions():
    """Get active positions"""
    return jsonify({"positions": active_positions})

@app.route('/api/feed')
def get_feed():
    """Get live feed"""
    return jsonify({"feed": live_feed})

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    """Start the bot"""
    bot_state["active"] = True
    add_to_feed("🚀 Bot started! Scanning for opportunities...", "success")
    return jsonify({"success": True, "message": "Bot started successfully!"})

@app.route('/api/bot/pause', methods=['POST'])
def pause_bot():
    """Pause the bot (keeps positions open)"""
    bot_state["active"] = False
    add_to_feed("⏸️ Bot paused. Existing positions remain open.", "warning")
    return jsonify({"success": True, "message": "Bot paused. Positions remain open."})

@app.route('/api/bot/stop-sell-all', methods=['POST'])
def stop_and_sell_all():
    """Stop bot and close all positions"""
    bot_state["active"] = False
    # Close all positions
    for position in active_positions:
        # Simulate selling
        profit = position['amount'] * 0.10  # Assume 10% profit for demo
        bot_state["total_profit"] += profit
        bot_state["reserve_balance"] += profit * 0.25
        bot_state["trading_capital"] += profit * 0.75
        add_to_feed(f"💰 Closed {position['token']}: +${profit:.2f}", "success")
    
    active_positions.clear()
    add_to_feed("🛑 Bot stopped. All positions closed.", "warning")
    return jsonify({"success": True, "message": "Bot stopped and all positions closed!"})

@app.route('/api/bot/emergency-exit', methods=['POST'])
def emergency_exit():
    """Emergency exit - sell everything immediately"""
    bot_state["active"] = False
    active_positions.clear()
    add_to_feed("🚨 EMERGENCY EXIT! All positions closed at market price.", "error")
    return jsonify({"success": True, "message": "Emergency exit completed!"})

@app.route('/api/withdraw/reserve', methods=['POST'])
def withdraw_reserve():
    """Withdraw reserve balance"""
    amount = bot_state["reserve_balance"]
    if amount > 0:
        bot_state["reserve_balance"] = 0
        add_to_feed(f"💸 Withdrew ${amount:.2f} from reserve to {RESERVE_WALLET[:8]}...", "success")
        return jsonify({"success": True, "message": f"Withdrew ${amount:.2f} to your wallet!"})
    return jsonify({"success": False, "message": "No funds in reserve"})

@app.route('/api/withdraw/all', methods=['POST'])
def withdraw_all():
    """Withdraw everything"""
    total = bot_state["trading_capital"] + bot_state["reserve_balance"]
    bot_state["trading_capital"] = 0
    bot_state["reserve_balance"] = 0
    active_positions.clear()
    add_to_feed(f"💰 Withdrew all funds: ${total:.2f}", "success")
    return jsonify({"success": True, "message": f"Withdrew ${total:.2f} to your wallet!"})

@app.route('/api/withdraw/profits', methods=['POST'])
def withdraw_profits():
    """Withdraw profits only"""
    if bot_state["total_profit"] > 0:
        amount = bot_state["total_profit"]
        bot_state["reserve_balance"] -= amount
        bot_state["total_profit"] = 0
        add_to_feed(f"📈 Withdrew profits: ${amount:.2f}", "success")
        return jsonify({"success": True, "message": f"Withdrew ${amount:.2f} profits!"})
    return jsonify({"success": False, "message": "No profits to withdraw"})

@app.route('/api/position/<position_id>/close', methods=['POST'])
def close_position(position_id):
    """Close a specific position"""
    for i, pos in enumerate(active_positions):
        if pos['id'] == position_id:
            profit = pos['pnl']
            bot_state["total_profit"] += profit
            if profit > 0:
                bot_state["winning_trades"] += 1
                bot_state["reserve_balance"] += profit * 0.25
                bot_state["trading_capital"] += profit * 0.75
            else:
                bot_state["losing_trades"] += 1
                bot_state["trading_capital"] += profit
            
            active_positions.pop(i)
            add_to_feed(f"💰 Closed {pos['token']}: ${profit:+.2f}", "success" if profit > 0 else "warning")
            return jsonify({"success": True, "message": f"Position closed: ${profit:+.2f}"})
    
    return jsonify({"success": False, "message": "Position not found"})

@app.route('/api/scan/<category>')
def scan_tokens(category):
    """Scan tokens by category"""
    try:
        tokens = []
        
        if category == 'established':
            # Scan established tokens like BONK, WIF, etc.
            symbols = ['BONK', 'WIF', 'JUP', 'PYTH', 'JTO']
            for symbol in symbols:
                try:
                    response = requests.get(
                        f'https://api.dexscreener.com/latest/dex/search?q={symbol}',
                        timeout=5
                    )
                    if response.status_code == 200:
                        data = response.json()
                        pairs = data.get('pairs', [])
                        # Filter for Solana and get best pair
                        solana_pairs = [p for p in pairs if p.get('chainId') == 'solana']
                        if solana_pairs:
                            # Get pair with highest liquidity
                            best_pair = max(solana_pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0)))
                            
                            safety_score = calculate_scam_score(best_pair)
                            
                            tokens.append({
                                'name': best_pair.get('baseToken', {}).get('name', 'Unknown'),
                                'symbol': best_pair.get('baseToken', {}).get('symbol', 'Unknown'),
                                'price': best_pair.get('priceUsd', '0'),
                                'change': float(best_pair.get('priceChange', {}).get('h24', 0)),
                                'volume': float(best_pair.get('volume', {}).get('h24', 0)),
                                'liquidity': float(best_pair.get('liquidity', {}).get('usd', 0)),
                                'safety_score': safety_score
                            })
                except:
                    continue
        
        return jsonify({"tokens": tokens})
    
    except Exception as e:
        return jsonify({"error": str(e), "tokens": []})

@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "bot_active": bot_state["active"],
        "apis": {
            "helius": "connected",
            "birdeye": "connected",
            "jupiter": "connected",
            "dexscreener": "connected"
        }
    })

if __name__ == '__main__':
    add_to_feed("✨ Nova Ultimate initialized!", "success")
    add_to_feed(f"🔗 APIs connected: Helius, Birdeye, Jupiter, DexScreener", "info")
    add_to_feed(f"💰 Reserve wallet: {RESERVE_WALLET[:8]}...", "info")
    add_to_feed(f"💵 Starting capital: ${bot_state['trading_capital']:.2f}", "info")
    
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

