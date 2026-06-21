# BUILD BRIEF — "Umbra" (working name, rename freely)
### Privacy-First, Social-Handle Crypto Payments on Sui

Paste this into Claude Code as the project brief. Work through the phases in order — each phase should be a working, testable increment before moving to the next. Ask me before making architecture decisions not covered here.

---

## 0. Core Principles (non-negotiable)

- **Non-custodial.** Umbra never holds user keys. zkLogin + Sui's native account abstraction handle custody.
- **Privacy by default.** Transaction amounts, sender/receiver linkage, and handle bindings are encrypted at rest (Seal) and in transit. Public Sui ledger should reveal as little as possible — favor encrypted payloads + ZK proofs over plaintext on-chain data.
- **No fiat.** Everything is crypto-to-crypto. Users send stablecoins (USDC primary) via a social handle; receivers get crypto, full stop. No bank rails, no KYC flows in v1.
- **Stack:** React/Vite frontend, FastAPI backend (Python, matches existing infra patterns), Sui Move for on-chain logic, Seal for encryption, Walrus for encrypted blob storage, deployed on Vultr via Caddy + pm2 (consistent with existing project infra).

---

## 1. Identity Layer — zkLogin (two separate systems, do not conflate)

**A. Login (auth into the platform):** Sui's native zkLogin only supports OpenID Connect providers — Google, Facebook, Apple, Twitch (Sui's official supported set; verify current list before building, Mysten Labs updates it). Build login with these only.

**B. Handle binding (for receiving payments):** Twitter/X, Discord, Telegram, email are NOT zkLogin OIDC providers. These are bound post-login as verified linked identities:
- User logs in via zkLogin (Google/Facebook/Apple/Twitch).
- User then "binds" a handle: OAuth-verify ownership (Twitter OAuth2, Discord OAuth2, Telegram Login Widget, email magic link) and store a signed mapping `{sui_address (encrypted) <-> handle}` in a Seal-encrypted record, indexed for lookup.
- Build unbind flow: removes the mapping, requires PIN confirmation (see §6).
- A user can bind multiple handles across platforms to one Sui address. Store as an array.

**Build order:** zkLogin auth first (Google as the single provider for MVP), then build the handle-binding service as a separate module once auth is solid.

---

## 2. Handle Resolution Service (the "type a handle, see results" search)

This is a backend microservice, not a frontend trick. Build per-platform:
- **Twitter/X:** Requires paid API tier for live username search/typeahead. Flag cost to me before building — MVP fallback: search only among handles already bound on Umbra (internal index), not live Twitter-wide search.
- **Discord:** Use Discord OAuth2 + bot to resolve username#discriminator or new unique usernames. No public search API for arbitrary users — same constraint as Twitter: search the internal bound-handle index.
- **Telegram:** Telegram Bot API can resolve `@username` to a chat if the bot has interacted with that user, or via Telegram Login Widget for binding. Live search of arbitrary unbound users isn't really possible — same internal-index pattern applies.
- **Email:** Trivial — just an input field with format validation, no external API.
- **Facebook:** Graph API does not support public handle search. Bind-only, no search.
- **Twitch:** Helix API supports username lookup directly (`/users?login=`) — this one CAN do live external search.

**Reality check for the build:** Across all six platforms, the only one with reliable live public search is Twitch (and possibly Twitter at a paid tier). Build the send flow around an **internal index of bound handles** as primary search (instant, free, works across all platforms), with Twitch external lookup as a bonus. Make the search UI typeahead-style regardless — same UX, different data source underneath.

---

## 3. Send Flow

1. Sender clicks "Send."
2. Platform selector chips: Twitter / Facebook / Email / Discord / Telegram / Twitch.
3. Typeahead search box queries the Handle Resolution Service (§2) for that platform, debounced, shows matching bound users with avatar if available.
4. Sender picks recipient, enters amount + selects token/chain.
5. Sender enters transaction PIN (§6).
6. Backend computes fee (§7), assembles the transfer payload.
7. Payload is encrypted via **Seal** before any on-chain write.
8. Transaction execution happens inside a **TEE** (see §4 — this needs an external compute layer, Sui itself has no native TEE execution).
9. Encrypted transaction record (metadata, not raw amounts in plaintext) is stored to **Walrus**.
10. Sui transaction settles; receiver is notified (if they have an account) or gets a claim link (if unbound recipient — escrow until they sign up and bind that handle).

---

## 4. TEE Execution Layer

Sui has no native TEE for transaction execution — this needs an external trusted compute layer. Options to evaluate (pick one, don't build custom TEE infra from scratch):
- **AWS Nitro Enclaves** — simplest to stand up on existing Vultr-adjacent infra patterns, well-documented.
- **Oasis ROFL** / **Phala Network** — purpose-built for confidential compute tied to chain state, more native fit if cost/complexity is acceptable.

Use this layer specifically for: decrypting the sender's PIN-protected request, validating the transfer, and signing/relaying to Sui — so the plaintext amount + handle mapping never touches a regular server process.

---

## 5. Storage — Walrus + Seal

- Every transaction record written to Walrus is Seal-encrypted client-side or TEE-side before upload — Walrus should only ever store ciphertext.
- Decryption access controlled via Seal's identity-based access policies, scoped to sender + receiver's Sui addresses only.
- Store: encrypted amount, encrypted token type, encrypted memo (if any), timestamp, and a hash for audit/dispute purposes — not the plaintext handle mapping (that lives in the handle-binding store, also Seal-encrypted).

---

## 6. Transaction PIN

- Separate from zkLogin auth. 4-6 digit PIN, required for: sending, receiving claims, binding/unbinding handles, and swaps.
- Store PIN hash (Argon2id) — never plaintext, never recoverable, only resettable via zkLogin re-auth + cooldown period.
- Rate-limit PIN attempts (lock after 5 fails, escalating cooldown).

---

## 7. Fee Logic (exact spec)

```
PLATFORM_FEE_USDC = 0.10   # flat, per send, regardless of amount
MIN_SEND_USDC     = 0.15   # enforced floor: amount - fee must be >= 0.05
MAX_SEND_USDC     = None   # no cap

def validate_send(amount):
    if amount < MIN_SEND_USDC:
        raise Error("Minimum send is 0.15 USDC")
    receiver_gets = amount - PLATFORM_FEE_USDC
    return receiver_gets  # platform keeps PLATFORM_FEE_USDC

# Swaps: gas fees deducted from the sending amount, not charged separately.
# Platform fee (0.10) accrues to a dedicated revenue Sui address, already in USDC — no conversion step needed since the platform only deals in crypto.
```

Build a `revenue_vault` Sui Move module that auto-routes the 0.10 fee on every transaction to a platform-controlled address. Track cumulative volume + fee revenue for the dashboard (§11).

---

## 8. Multi-Chain Receiving

Don't build a custom bridge — integrate an existing aggregator:
- **LI.FI** or **deBridge** as the cross-chain routing layer (both have solid SDKs, handle EVM + Solana + others).
- **Wormhole** as a fallback/native option for Sui-specific routes.

Flow: incoming token from any supported chain → aggregator quotes route → settles as USDC (or user's chosen token) on Sui → credited to user's Umbra balance. Scope MVP to Sui + Ethereum/Base/Arbitrum (EVM) + Solana; expand later.

---

## 9. AI Agent Support

- Build a separate API key-based auth path (distinct from zkLogin) so AI agents can hold a scoped, revocable credential instead of a human OAuth session.
- Agent accounts still require a bound Sui address and still pay the same fee structure — no special-casing on fees.
- Rate-limit and scope agent API keys (e.g., max per-tx amount, daily volume cap) — configurable per key.
- Document this as a small SDK (Python + JS) so agents (including your own WARDEN/ManagerX-style agents) can call `umbra.send(handle, platform, amount, token)` directly.

---

## 10. Swap Module

UI: pick chain → pick swap venue → execute.

| Chain | Swap venue |
|---|---|
| EVM (Ethereum, Base, Arbitrum, X Layer, etc.) | Uniswap (v3/v4 router) |
| Solana | Jupiter aggregator API |
| Sui | Aftermath Finance SDK |
| Cross-chain native (BTC, etc.) | THORChain |
| Anything not covered above | LI.FI or 1inch as a meta-aggregator fallback |

Gas fees for swaps are deducted from the sending amount per the spec in §7 — don't charge a separate platform fee on top of swap gas unless explicitly told to.

---

## 11. Dashboard

- Balance overview (per chain/token, aggregated USD-equivalent value using live price feeds — CoinGecko is fine).
- Transaction history (decrypt-on-view via Seal, paginated, filterable by platform/handle/date).
- Total transaction volume (personal + show platform-wide aggregate if you want a "growth" stat publicly).
- Bound handles management (bind/unbind UI per §1B).
- PIN reset / security settings.

---

## 12. Suggested Build Order for Claude Code

1. Sui Move contracts: account registry, handle-binding registry, revenue vault, escrow-for-unbound-recipients.
2. zkLogin auth (Google provider only for MVP).
3. Handle binding + internal search index (skip live external search initially).
4. Send flow UI + backend, without Seal/TEE/Walrus first — get the happy path working with plaintext on testnet.
5. Layer in Seal encryption for stored records.
6. Layer in TEE execution (start with a stub/mock TEE interface so the rest of the system doesn't block on infra decisions).
7. Walrus storage integration.
8. Multi-chain receive via LI.FI/deBridge.
9. Swap module (start with Aftermath since you're already deep in Sui).
10. Dashboard.
11. AI agent SDK + API key auth last — it reuses everything built above.

---

## Open flags for you to resolve before/while building

- Twitter/X API tier cost for live search — decide budget before promising full live search.
- Pick TEE provider (Nitro Enclaves vs Oasis ROFL vs Phala) — affects infra cost and complexity meaningfully.
- Confirm current zkLogin supported provider list with Mysten Labs docs before locking auth scope.
