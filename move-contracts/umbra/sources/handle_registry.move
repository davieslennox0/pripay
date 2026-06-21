/// On-chain anchor for handle <-> address bindings. Stores only
/// hash(platform_id || normalized_handle) -> address, never the plaintext
/// handle, per the brief's "reveal as little as possible on the public
/// ledger" principle (§0). The real, searchable plaintext mapping lives in
/// the backend's Seal-encrypted index (§1B, §2) — this registry exists so
/// bind/unbind is a canonical, tamper-proof on-chain fact.
///
/// PIN confirmation for unbind (§6) happens off-chain/in the TEE before the
/// transaction calling `unbind_handle` is ever relayed; this module assumes
/// the caller is already authorized by the time it executes.
module umbra::handle_registry {
    use sui::clock::Clock;
    use sui::table::{Self, Table};
    use umbra::account_registry::AccountRegistry;

    const EHandleAlreadyBound: u64 = 0;
    const ENotBound: u64 = 1;
    const ENotOwner: u64 = 2;

    public struct HandleRegistry has key {
        id: UID,
        bindings: Table<vector<u8>, address>,
    }

    public struct HandleBound has copy, drop {
        owner: address,
        handle_hash: vector<u8>,
        bound_at_ms: u64,
    }

    public struct HandleUnbound has copy, drop {
        owner: address,
        handle_hash: vector<u8>,
        unbound_at_ms: u64,
    }

    fun init(ctx: &mut TxContext) {
        transfer::share_object(HandleRegistry {
            id: object::new(ctx),
            bindings: table::new(ctx),
        });
    }

    public fun bind_handle(
        registry: &mut HandleRegistry,
        account_registry: &mut AccountRegistry,
        handle_hash: vector<u8>,
        clock: &Clock,
        ctx: &mut TxContext,
    ) {
        let sender = ctx.sender();
        assert!(!registry.bindings.contains(handle_hash), EHandleAlreadyBound);
        registry.bindings.add(handle_hash, sender);
        account_registry.bump_handle_count(sender, true);
        sui::event::emit(HandleBound {
            owner: sender,
            handle_hash,
            bound_at_ms: clock.timestamp_ms(),
        });
    }

    /// Caller must be the address the handle is currently bound to.
    public fun unbind_handle(
        registry: &mut HandleRegistry,
        account_registry: &mut AccountRegistry,
        handle_hash: vector<u8>,
        clock: &Clock,
        ctx: &mut TxContext,
    ) {
        let sender = ctx.sender();
        assert!(registry.bindings.contains(handle_hash), ENotBound);
        let owner = *registry.bindings.borrow(handle_hash);
        assert!(owner == sender, ENotOwner);
        registry.bindings.remove(handle_hash);
        account_registry.bump_handle_count(sender, false);
        sui::event::emit(HandleUnbound {
            owner: sender,
            handle_hash,
            unbound_at_ms: clock.timestamp_ms(),
        });
    }

    public fun resolve(registry: &HandleRegistry, handle_hash: vector<u8>): address {
        *registry.bindings.borrow(handle_hash)
    }

    public fun is_bound(registry: &HandleRegistry, handle_hash: vector<u8>): bool {
        registry.bindings.contains(handle_hash)
    }
}
