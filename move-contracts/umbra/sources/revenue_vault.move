/// Auto-routes the flat platform fee (§7 of the build brief) on every send
/// to a platform-controlled vault, and tracks cumulative volume/fees for the
/// dashboard (§11). Generic over coin type T so it isn't hard-locked to one
/// USDC issuer, though USDC is the primary token (§0).
module umbra::revenue_vault {
    use sui::balance::{Self, Balance};
    use sui::clock::Clock;
    use sui::coin::{Self, Coin};

    const ENotAdmin: u64 = 0;
    const EBelowMinSend: u64 = 1;

    /// 0.10 USDC, in USDC's 6-decimal base units. Matches PLATFORM_FEE_USDC
    /// in the brief's fee spec exactly — keep these in sync if it ever changes.
    const PLATFORM_FEE_BASE_UNITS: u64 = 100_000;
    /// 0.15 USDC floor: enforces "amount - fee must be >= 0.05" from the spec.
    const MIN_SEND_BASE_UNITS: u64 = 150_000;

    public struct RevenueVault<phantom T> has key {
        id: UID,
        balance: Balance<T>,
        admin: address,
        cumulative_volume: u64,
        cumulative_fees: u64,
    }

    public struct FeeCollected has copy, drop {
        payer: address,
        amount_sent: u64,
        fee: u64,
        collected_at_ms: u64,
    }

    public fun create<T>(admin: address, ctx: &mut TxContext) {
        transfer::share_object(RevenueVault<T> {
            id: object::new(ctx),
            balance: balance::zero<T>(),
            admin,
            cumulative_volume: 0,
            cumulative_fees: 0,
        });
    }

    /// Splits the flat platform fee off `payment` and routes it into the
    /// vault. Returns the remainder for the caller to forward to the
    /// receiver — receiver_gets = amount - PLATFORM_FEE_USDC, per §7.
    public fun collect_fee<T>(
        vault: &mut RevenueVault<T>,
        payment: Coin<T>,
        clock: &Clock,
        ctx: &mut TxContext,
    ): Coin<T> {
        let amount_sent = payment.value();
        assert!(amount_sent >= MIN_SEND_BASE_UNITS, EBelowMinSend);
        let mut remaining = payment;
        let fee_coin = remaining.split(PLATFORM_FEE_BASE_UNITS, ctx);
        vault.balance.join(fee_coin.into_balance());
        vault.cumulative_volume = vault.cumulative_volume + amount_sent;
        vault.cumulative_fees = vault.cumulative_fees + PLATFORM_FEE_BASE_UNITS;
        sui::event::emit(FeeCollected {
            payer: ctx.sender(),
            amount_sent,
            fee: PLATFORM_FEE_BASE_UNITS,
            collected_at_ms: clock.timestamp_ms(),
        });
        remaining
    }

    public fun withdraw<T>(vault: &mut RevenueVault<T>, amount: u64, ctx: &mut TxContext): Coin<T> {
        assert!(ctx.sender() == vault.admin, ENotAdmin);
        coin::from_balance(vault.balance.split(amount), ctx)
    }

    public fun cumulative_volume<T>(vault: &RevenueVault<T>): u64 { vault.cumulative_volume }
    public fun cumulative_fees<T>(vault: &RevenueVault<T>): u64 { vault.cumulative_fees }
}
