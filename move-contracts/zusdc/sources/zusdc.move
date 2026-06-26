/// zUSDC — testnet mock USDC for Umbra development.
/// 6 decimals, same as Circle USDC, so amounts are a drop-in replacement.
/// TreasuryCap is transferred to the deployer; anyone with it can mint.
module zusdc::zusdc {
    use sui::coin;
    use sui::url;

    public struct ZUSDC has drop {}

    fun init(witness: ZUSDC, ctx: &mut TxContext) {
        let (treasury, metadata) = coin::create_currency(
            witness,
            6,
            b"zUSDC",
            b"zUSDC",
            b"Umbra testnet mock USDC (6 decimals, mirrors Circle USDC)",
            option::some(url::new_unsafe_from_bytes(b"https://umbra.finance/zusdc.png")),
            ctx,
        );
        transfer::public_freeze_object(metadata);
        transfer::public_transfer(treasury, ctx.sender());
    }

    /// Mint `amount` zUSDC to `recipient`. Caller must hold the TreasuryCap.
    public fun mint(
        treasury: &mut coin::TreasuryCap<ZUSDC>,
        amount: u64,
        recipient: address,
        ctx: &mut TxContext,
    ) {
        coin::mint_and_transfer(treasury, amount, recipient, ctx);
    }
}
