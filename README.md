# Range Seeker

Agentic Liquidity Provision

## The Problem We Solve

Uniswap liquidity provision is still too hard:
- Users must manually pick ranges, monitor price/volatility, rebalance to avoid impermanent loss or going out-of-range (zero fees)
- Existing solutions are either dumb vaults (static wide ranges = low fees) or pro tools that still require constant babysitting

## Our Solution

A fully autonomous, natural-language-controlled liquidity agent that:
- Runs 24/7 on a server using Coinbase CDP agent wallets
- Holds user funds in a secure smart wallet
- Rebalances automatically when positions drift out of range or approach range boundaries
- Uses natural language to define strategies (e.g., "tight range but widen if volatility spikes")
- Uses The Graph AMP for real-time pool data and volatility intelligence
- Funds via simple wallet transfers with automatic rebalancing

**Current Implementation:** WETH/USDC 0.05% fee tier on Base (most liquid pool)

## Complete User Flow

### Step 1: Connect Wallet & Create Agent
1. User connects wallet (RainbowKit - supports MetaMask, Coinbase Wallet, WalletConnect, etc.)
2. User creates an agent with:
   - Name and emoji
   - Natural language strategy description

Example strategy:
> "I want tight range fee farming but widen if volatility spikes, and exit entirely to USDC if ETH ever drops below $3000"

### Step 2: Strategy Parsing
- Backend sends strategy to LLM (Gemini) with real-time context:
  - Current 24h volatility from The Graph AMP
  - Pool statistics and historical price data
- LLM returns structured JSON strategy config with:
  - Base range percentage
  - Dynamic widening triggers
  - Price thresholds for actions
- Frontend renders visual preview on live price chart

### Step 3: Agent Wallet Creation
- Backend creates Coinbase CDP smart wallet for the agent
- Smart wallet is non-custodial and fully controlled by backend
- User gets agent wallet address for funding

### Step 4: Fund the Agent
User deposits funds to agent wallet:
- Send USDC and/or WETH directly to agent address
- Agent automatically:
  - Detects deposit via balance polling
  - Swaps to optimal 50/50 ratio using 0x API
  - Opens Uniswap V3 position with calculated tick range

### Step 5: Autonomous Operation
Background worker runs every 15 minutes:
1. Queries The Graph AMP for current pool state
2. For each active agent:
   - Gets current Uniswap positions via position manager contract
   - Checks if price is outside range or within 10% of range edge
   - If rebalance needed:
     - Withdraws existing position
     - Swaps to optimal ratio
     - Opens new position centered on current price
3. Activity is logged for dashboard display

### Step 6: Dashboard Monitoring
Users can view real-time agent status:
- Live price chart with overlays:
  - Current price (blue line)
  - Strategy ranges (orange bands)
  - Current position bounds (green lines)
  - Price thresholds (red lines)
- Asset balances (available tokens + LP position value)
- Position details with token amounts
- Manual rebalance button
- Deposit more funds functionality

## Tech Stack

### Frontend (`/app`)
- **Framework:** React + TypeScript
- **UI:** Kibalabs UI components + styled-components
- **Web3:** ethers.js, RainbowKit
- **Charts:** lightweight-charts for price visualization
- **Build:** Vite

### Backend (`/api`)
- **Framework:** Python + FastAPI (via kiba-core)
- **Database:** PostgreSQL with Alembic migrations
- **Web3:** web3.py for blockchain interactions
- **LLM:** Gemini API for strategy parsing
- **Data:** The Graph AMP for pool data and volatility
- **Swaps:** 0x API for token swaps
- **Agent Wallets:** Coinbase CDP SDK (Node.js integration)

### Worker (`/api/worker.py`)
- **Scheduler:** APScheduler for interval-based checks
- **Frequency:** Every 15 minutes
- **Tasks:**
  - Query all agents from database
  - Check position health via The Graph and on-chain calls
  - Trigger rebalances when needed

### Smart Contracts
- **Uniswap V3:** NonfungiblePositionManager for LP positions
- **Tokens:** WETH and USDC on Base
- **Pool:** 0.05% fee tier (500)

## Implementation Details

### Strategy Definition
Natural language strategies are converted to structured rules:
```typescript
{
  rules: [
    {
      type: "RANGE_WIDTH",
      priority: 1,
      parameters: {
        baseRangePercent: 10,  // ±10% from current price
        dynamicWidening: {
          volatilityThreshold: 5.0,  // Widen if vol > 5%
          widenToPercent: 20
        }
      }
    },
    {
      type: "PRICE_THRESHOLD",
      priority: 2,
      parameters: {
        priceUsd: 3000,
        operator: "LESS_THAN",
        action: "EXIT_TO_USDC"
      }
    }
  ]
}
```

### Volatility Calculation
Uses The Graph AMP to query all swaps in the last 24 hours:
```sql
SELECT
  timestamp,
  POWER(CAST(event."sqrtPriceX96" AS DOUBLE) / 79228162514264337593543950336.0, 2) as price
FROM "edgeandnode/uniswap_v3_base@0.0.1".event__swap
WHERE pool_address = X'...'
  AND timestamp > TIMESTAMP '...'
```
Calculates standard deviation of log returns and annualizes

### Position Management
- **Opening:** Encode mint parameters, sign with CDP wallet, broadcast transaction
- **Closing:** Call decreaseLiquidity(100%) then collect() to withdraw all tokens
- **Rebalancing:** Close existing position → swap if needed → open new centered position

### Tick Math
- Convert price to tick: `tick = log(price) / log(1.0001)`
- Convert tick to price: `price = 1.0001^tick`
- Tick spacing: 10 (for 0.05% fee tier)

## Database Schema

### Tables
- `users` - User accounts with wallet addresses
- `user_wallets` - User wallet addresses
- `agents` - AI agents with strategies
- `agent_wallets` - Coinbase CDP wallet addresses
- `strategies` - Strategy definitions and rules

## Running the Project

### Backend
```bash
cd api
make install
make run-local
```

### Frontend
```bash
cd app
npm install
npm run dev
```

### Worker
```bash
cd api
python worker.py
```

## Environment Variables

### Backend
- `DATABASE_URL` - PostgreSQL connection string
- `ETH_RPC_URL` - Base RPC endpoint
- `AMP_API_KEY` - The Graph AMP API key
- `COINBASE_CDP_API_KEY_NAME` - CDP API key
- `COINBASE_CDP_API_KEY_PRIVATE_KEY` - CDP private key
- `GEMINI_API_KEY` - Gemini LLM API key

### Frontend
- `VITE_API_BASE_URL` - Backend API URL

## Future Enhancements

- Multi-pool support (different token pairs and fee tiers)
- More sophisticated rebalancing triggers (MEV protection, gas optimization)
- Profit/loss tracking and performance analytics
- Social features (share strategies, leaderboards)
- Mobile app for on-the-go monitoring
- Gasless transactions via account abstraction
