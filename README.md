# Range Seeker

Agentic Liquidity Provision

**The Problem We Solve**
Uniswap liquidity provision is still too hard:
- Users must manually pick ranges, monitor price/volatility, rebalance to avoid impermanent loss or going out-of-range (zero fees).
- Existing solutions are either dumb vaults (static wide ranges = low fees) or pro tools that still require constant babysitting.

**Our Solution**
A fully autonomous, natural-language-controlled liquidity agent that:
- Runs 24/7 on a server (Coinbase CDP agent wallet)
- Holds a user-owned sovereign vault (LiquidityVault.sol) that owns the Uniswap position NFT + funds
- Rebalances, compounds fees, or emergency-exits based on user intent expressed in plain English
- Uses on-chain Pyth for tamper-proof pricing in every action
- Uses The Graph AMP for real-time volatility intelligence
- Funds via Coinbase OnchainKit Swap widget (fiat → position in one click)

**Why This Wins Everything**
- Most usable live app (works today with $10 on Base mainnet, real fees earned in demo)
- Sweeps every sponsor prize:
  - Coinbase CDP → agent wallet + OnchainKit Swap widget
  - Pyth → on-chain price update in every single rebalance tx
  - The Graph → AMP dataset for volatility + UI badges
  - Hardhat → full contract suite with factory, tests, deploy scripts
- Feels like magic: user types "farm fees aggressively but gtfo to USDC if ETH < $3000" → watches live as agent actually does it

Hardcoded for MVP: WETH/USDC 0.05% fee tier on Base (most liquid pool = best demo).

## Complete User Flow (Step-by-Step)

### Step 1: Landing & Market Context
User lands on the site → immediately sees:
- Live Pyth price chart (lightweight-charts)
- Current ETH price (Pyth)
- 24h volume & fees earned by pool (AMP)
- 24h implied volatility % calculated from every swap (The Graph AMP)
- Big badge: “Real-time chain data powered by The Graph AMP”

Action: Click “Connect Wallet” → RainbowKit modal (MetaMask, Rabby, Ledger, WalletConnect – anything works).

### Step 2: Describe Your Strategy
Two options:

**A – Presets** (Passive / Balanced / Aggressive / Capital Protector)
**B – Natural Language** (the magic)
User types:
“I want tight range fee farming but widen if volatility spikes, and exit entirely to USDC if ETH ever drops below $3000”

Frontend sends to backend → LLM (Grok API preferred, Claude fallback) with injected context:
“Current 24h implied volatility from The Graph AMP is 4.1%. Convert this user request into JSON strategy config.”

Backend returns → UI renders beautiful preview card:
- Visual range bands on the live chart
- Summary: “Aggressive fee farming (±3.2% range), auto-widen on vol spike, stop-loss at $3000”
- Edit or Confirm button

### Step 3: Deploy Vault & Agent
User clicks “Deploy My Liquidity Agent” → two transactions (both cheap on Base):

1. `factory.createVault()` → deploys personal LiquidityVault.sol (owns funds + position NFT)
2. Backend instantly creates Coinbase CDP agent wallet → UI calls `vault.setOperator(cdpAgentAddress)`

→ Total user signatures: 2
→ Vault is now live, agent has permission to act

### Step 4: Fund the Vault (Coinbase Swap Widget – Bounty Guaranteed)
Screen shows vault address + QR + big beautiful funding section:

**Option A** – Manual send (for whales)
**Option B** – “Buy/Swap directly into position (recommended)” → renders official Coinbase OnchainKit <Swap> component:
```tsx
<Swap toAddress={vaultAddress} theme="coinbase" />
```
User can:
- Buy USDC with card (fiat onramp)
- Swap any token → balanced WETH/USDC
- All funds land directly in vault

Optional checkbox: “Auto-balance my deposit” → agent will swap to ~50/50 on activation

### Step 5: Activate Agent
As soon as vault has > $50 TVL:
- “Activate” button appears
- User clicks → backend triggers CDP agent to call `vault.initializePosition(priceUpdateData)`
  → First transaction includes on-chain Pyth update + mints initial position centered on current price ± user range

Agent is now live and fully autonomous.

### Step 6: Dashboard – Watch Your Agent Work
User returns anytime to /dashboard/[vault]

Live view:
- Pyth WebSocket price feed chart
- Green band = current active range
- Faint orange historic bands = past positions
- Activity feed (realtime via Supabase or Socket.io):
  - “14:32 – Grok rebalanced to $3,620–$3,920 (price +2.8%, 24h vol spiked to 5.1% via The Graph AMP)”
  - “15:07 – Compounded 0.12% fees”
- Stats: Total fees earned, IL vs hold, performance vs passive vault
- Big red “Emergency Stop Agent” button → `setOperator(address(0))`
- “Withdraw Everything” button → `vault.withdraw()` → burns position, sends both tokens to user

User can close the tab – the agent keeps running on your server forever (or until revoked).

## Implementation Details (Oriented Around the Flow)

### Step 1–2: Market Context + Strategy Parsing
- Frontend: copy structure from yieldseeker-app
- Current price & chart: Pyth WebSocket `wss://hermes.pyth.network/ws`
- Volatility & volume: The Graph AMP SQL query (runs in backend, cached 30s)
  ```sql
  SELECT
    (sqrt_price_x96::decimal / 2^96)^2 / 1e12 AS price
  FROM "univ3@1.0.0".swap
  WHERE pool = '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640'
    AND block_timestamp > NOW() - INTERVAL '24 hours'
  ORDER BY block_timestamp DESC
  ```
  → calculate std dev of log returns → volatility %
- LLM parsing: backend endpoint → Grok API with volatility injected → returns strict JSON

### Step 3: Vault Deployment + CDP Agent Creation
- Hardhat repo with:
  - LiquidityVault.sol (~220 LOC, onlyOperator modifier, rebalance/emergencyExit with Pyth pull)
  - Factory.sol (CREATE2 for cheap deterministic addresses optional)
  - Deploy script deploys factory once, users call createVault()
- Backend (copy structure from yieldseeker-app)
  ```ts
  const agent = await coinbaseNode.wallets.create({ type: "agent" });
  // store agent private key encrypted or .env for hackathon
  ```

### Step 4: Funding
- OnchainKit <Swap> component – literally one line, sends directly to vault
- Backend polls vault balances (viem publicClient) → shows "Ready to activate" when sufficient

### Step 5–6: Autonomous Execution Loop
Backend worker (runs every 60s or Pyth WS triggered):
1. Pyth WebSocket for current price
2. For each active vault:
   - Fetch current position ticks via NonfungiblePositionManager.positions(tokenId)
   - Compare current Pyth price vs range ± buffer
   - If trigger → fetch latest Pyth VAA from Hermes → CDP Node SDK sends:
     ```ts
     agent.sendTransaction({
       to: vault,
       data: encode(rebalance(newLower, newUpper, priceUpdateData)),
       value: updateFee
     })
     ```
   - Contract rebalance():
     - pyth.updatePriceFeeds{value}(priceUpdateData)
     - decrease 100%, collect fees
     - swap to ~50/50 if needed
     - mint new range
     - emit event → backend logs for activity feed

Database: postrgresql – stores vault → agent mapping + activity log


## Challenes along the way
