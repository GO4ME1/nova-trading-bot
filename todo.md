# Nova Trading Bot TODO

## Completed
- [x] Switch from Birdeye to DexScreener API
- [x] Update to Jupiter Ultra Swap API
- [x] Fix CORS issues with backend proxy
- [x] Fix browser Buffer compatibility
- [x] Add configurable trading amount input
- [x] Execute first successful trade

## In Progress
- [x] Remove +50% take profit cap (let winners run)
- [x] Update closePosition to use Ultra Swap API
- [x] Implement real-time price updates from DexScreener
- [x] Add auto-sell logic: -15% stop loss + 15% trailing stop (10% drop from peak)
- [x] Add debug logging for position tracking
- [ ] Test position tracking with next trade
- [ ] Verify auto-sell trigg- [x] Prevent multiple buy attempts when out of funds


- [x] Fix trading amount input field not updating trade size
- [x] Fix "connection is not defined" error preventing position tracking
- [x] Make transaction confirmation non-blocking to allow position tracking
- [x] Fix Live Feed to show sell transaction details and P&L
- [x] Implement Recent Trades display with completed trades history
- [x] Fix P&L calculation to show correct SOL amounts
- [x] Add localStorage persistence for positions (survive page refresh)