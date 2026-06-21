/// Holds funds sent to a handle that has no bound Sui address yet (§3 step
/// 10: "claim link... escrow until they sign up and bind that handle").
/// Keyed by the same handle_hash scheme as handle_registry so a claim can be
/// resolved purely from the hash, without ever putting the plaintext handle
/// on-chain.
module umbra::escrow {
    use sui::balance::{Self, Balance};
    use sui::clock::Clock;
    use sui::coin::{Self, Coin};
    use sui::table::{Self, Table};

    const ENotClaimable: u64 = 0;

    public struct EscrowVault<phantom T> has key {
        id: UID,
        deposits: Table<vector<u8>, Balance<T>>,
    }

    public struct Deposited has copy, drop {
        handle_hash: vector<u8>,
        sender: address,
        amount: u64,
        deposited_at_ms: u64,
    }

    public struct Claimed has copy, drop {
        handle_hash: vector<u8>,
        claimer: address,
        amount: u64,
        claimed_at_ms: u64,
    }

    /// No package init: EscrowVault is generic, so the concrete coin type
    /// (and one vault per type) is chosen at deploy time via this call.
    public fun create<T>(ctx: &mut TxContext) {
        transfer::share_object(EscrowVault<T> {
            id: object::new(ctx),
            deposits: table::new(ctx),
        });
    }

    /// Deposits accumulate if multiple sends land on the same unbound handle
    /// before the recipient claims.
    public fun deposit<T>(
        vault: &mut EscrowVault<T>,
        handle_hash: vector<u8>,
        payment: Coin<T>,
        clock: &Clock,
        ctx: &mut TxContext,
    ) {
        let amount = payment.value();
        let added = payment.into_balance();
        if (vault.deposits.contains(handle_hash)) {
            vault.deposits.borrow_mut(handle_hash).join(added);
        } else {
            vault.deposits.add(handle_hash, added);
        };
        sui::event::emit(Deposited {
            handle_hash,
            sender: ctx.sender(),
            amount,
            deposited_at_ms: clock.timestamp_ms(),
        });
    }

    /// Caller (backend/TEE) should call handle_registry::bind_handle for
    /// this handle_hash in the same transaction before claiming, so the
    /// funds land on an address that's now canonically bound to the handle.
    public fun claim<T>(
        vault: &mut EscrowVault<T>,
        handle_hash: vector<u8>,
        clock: &Clock,
        ctx: &mut TxContext,
    ): Coin<T> {
        assert!(vault.deposits.contains(handle_hash), ENotClaimable);
        let balance = vault.deposits.remove(handle_hash);
        let amount = balance.value();
        sui::event::emit(Claimed {
            handle_hash,
            claimer: ctx.sender(),
            amount,
            claimed_at_ms: clock.timestamp_ms(),
        });
        coin::from_balance(balance, ctx)
    }

    public fun has_deposit<T>(vault: &EscrowVault<T>, handle_hash: vector<u8>): bool {
        vault.deposits.contains(handle_hash)
    }

    public fun pending_amount<T>(vault: &EscrowVault<T>, handle_hash: vector<u8>): u64 {
        vault.deposits.borrow(handle_hash).value()
    }
}
