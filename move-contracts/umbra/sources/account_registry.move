/// Tracks which Sui addresses have onboarded to Umbra. Deliberately stores
/// no handle data or balances here — just enough state for other modules
/// (handle_registry, escrow) to check whether an address is a known account.
module umbra::account_registry {
    use sui::clock::Clock;
    use sui::table::{Self, Table};

    const EAlreadyRegistered: u64 = 0;

    public struct AccountRegistry has key {
        id: UID,
        accounts: Table<address, AccountRecord>,
    }

    public struct AccountRecord has store, drop {
        bound_handle_count: u64,
        created_at_ms: u64,
    }

    public struct AccountCreated has copy, drop {
        account: address,
        created_at_ms: u64,
    }

    fun init(ctx: &mut TxContext) {
        transfer::share_object(AccountRegistry {
            id: object::new(ctx),
            accounts: table::new(ctx),
        });
    }

    /// Called once, the first time an address transacts with Umbra
    /// (typically right after zkLogin-derived address signs its first tx).
    public fun register(registry: &mut AccountRegistry, clock: &Clock, ctx: &mut TxContext) {
        let sender = ctx.sender();
        assert!(!registry.accounts.contains(sender), EAlreadyRegistered);
        let created_at_ms = clock.timestamp_ms();
        registry.accounts.add(sender, AccountRecord {
            bound_handle_count: 0,
            created_at_ms,
        });
        sui::event::emit(AccountCreated { account: sender, created_at_ms });
    }

    public fun is_registered(registry: &AccountRegistry, addr: address): bool {
        registry.accounts.contains(addr)
    }

    public fun handle_count(registry: &AccountRegistry, addr: address): u64 {
        registry.accounts.borrow(addr).bound_handle_count
    }

    /// Only handle_registry (same package) may adjust the bound-handle count.
    public(package) fun bump_handle_count(
        registry: &mut AccountRegistry,
        addr: address,
        increase: bool,
    ) {
        let record = registry.accounts.borrow_mut(addr);
        if (increase) {
            record.bound_handle_count = record.bound_handle_count + 1;
        } else {
            record.bound_handle_count = record.bound_handle_count - 1;
        };
    }
}
