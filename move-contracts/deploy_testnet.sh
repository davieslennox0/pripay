#!/usr/bin/env bash
# Deploy Umbra Move package to Sui testnet and wire up shared objects.
# Run after funding the deployer address via https://faucet.sui.io
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "$0")/umbra" && pwd)"
REVENUE_ADMIN="${1:-$(sui client active-address)}"
ZUSDC_PACKAGE="0x228245f74e01948d43ef584c0e94e160874e7936434e2e390eec7228db2b61ba"
COIN_TYPE="${ZUSDC_PACKAGE}::zusdc::ZUSDC"

echo "=== Umbra Testnet Deployment ==="
echo "Package dir : $PACKAGE_DIR"
echo "Active addr : $(sui client active-address)"
echo "Revenue admin: $REVENUE_ADMIN"
echo ""

# 1. Check balance
BALANCE=$(sui client balance 2>&1 | grep -o '[0-9,]* MIST' | head -1 || echo "0 MIST")
echo "Balance: $BALANCE"

# 2. Publish the package
echo ""
echo "--- Publishing package ---"
PUBLISH_OUT=$(sui client publish "$PACKAGE_DIR" \
  --gas-budget 200000000 \
  --json 2>&1)

# Extract package ID
PACKAGE_ID=$(echo "$PUBLISH_OUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for change in data.get('objectChanges', []):
    if change.get('type') == 'published':
        print(change['packageId'])
        break
" 2>/dev/null)

if [ -z "$PACKAGE_ID" ]; then
  echo "ERROR: could not extract package ID. Full output:"
  echo "$PUBLISH_OUT"
  exit 1
fi
echo "Package ID: $PACKAGE_ID"

# Extract shared object IDs created by init functions (AccountRegistry, HandleRegistry)
ACCOUNT_REGISTRY_ID=$(echo "$PUBLISH_OUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for change in data.get('objectChanges', []):
    if change.get('type') == 'created' and 'account_registry::AccountRegistry' in change.get('objectType',''):
        print(change['objectId'])
        break
" 2>/dev/null)

HANDLE_REGISTRY_ID=$(echo "$PUBLISH_OUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for change in data.get('objectChanges', []):
    if change.get('type') == 'created' and 'handle_registry::HandleRegistry' in change.get('objectType',''):
        print(change['objectId'])
        break
" 2>/dev/null)

echo "AccountRegistry : $ACCOUNT_REGISTRY_ID"
echo "HandleRegistry  : $HANDLE_REGISTRY_ID"

# 3. Create EscrowVault<ZUSDC>
echo ""
echo "--- Creating EscrowVault<$COIN_TYPE> ---"
ESCROW_OUT=$(sui client call \
  --package "$PACKAGE_ID" \
  --module escrow \
  --function create \
  --type-args "$COIN_TYPE" \
  --gas-budget 50000000 \
  --json 2>&1)

ESCROW_VAULT_ID=$(echo "$ESCROW_OUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for change in data.get('objectChanges', []):
    if change.get('type') == 'created' and 'escrow::EscrowVault' in change.get('objectType',''):
        print(change['objectId'])
        break
" 2>/dev/null)
echo "EscrowVault<ZUSDC>: $ESCROW_VAULT_ID"

# 4. Create RevenueVault<ZUSDC>
echo ""
echo "--- Creating RevenueVault<$COIN_TYPE> (admin=$REVENUE_ADMIN) ---"
REVENUE_OUT=$(sui client call \
  --package "$PACKAGE_ID" \
  --module revenue_vault \
  --function create \
  --type-args "$COIN_TYPE" \
  --args "$REVENUE_ADMIN" \
  --gas-budget 50000000 \
  --json 2>&1)

REVENUE_VAULT_ID=$(echo "$REVENUE_OUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for change in data.get('objectChanges', []):
    if change.get('type') == 'created' and 'revenue_vault::RevenueVault' in change.get('objectType',''):
        print(change['objectId'])
        break
" 2>/dev/null)
echo "RevenueVault<ZUSDC>: $REVENUE_VAULT_ID"

# 5. Write deployment record
DEPLOY_OUT="/root/umbra/move-contracts/deployed_testnet.json"
python3 - <<PYEOF
import json
record = {
    "network": "testnet",
    "deployer": "$(sui client active-address)",
    "package_id": "$PACKAGE_ID",
    "account_registry": "$ACCOUNT_REGISTRY_ID",
    "handle_registry": "$HANDLE_REGISTRY_ID",
    "escrow_vault_sui": "$ESCROW_VAULT_ID",
    "revenue_vault_sui": "$REVENUE_VAULT_ID",
    "revenue_admin": "$REVENUE_ADMIN",
    "zusdc_package": "$ZUSDC_PACKAGE",
    "coin_type": "$COIN_TYPE",
    "zusdc_treasury_cap": "0x6e4e4afd8c5388d2810fc72e263b77de4efcece57a243888fa8634c86dc4c6e3",
    "note": "testnet uses zUSDC (6 dec mock); redeploy with Circle USDC type for mainnet"
}
with open("$DEPLOY_OUT", "w") as f:
    json.dump(record, f, indent=2)
print("Wrote $DEPLOY_OUT")
PYEOF

echo ""
echo "=== Deployment complete ==="
echo "Add to backend/.env:"
echo "  SUI_PACKAGE_ID=$PACKAGE_ID"
echo "  SUI_ACCOUNT_REGISTRY=$ACCOUNT_REGISTRY_ID"
echo "  SUI_HANDLE_REGISTRY=$HANDLE_REGISTRY_ID"
echo "  SUI_ESCROW_VAULT=$ESCROW_VAULT_ID"
echo "  SUI_REVENUE_VAULT=$REVENUE_VAULT_ID"
