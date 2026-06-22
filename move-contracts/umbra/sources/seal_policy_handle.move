/// Seal access policy for handle-binding decryption (brief §1B: the
/// {sui_address (encrypted) <-> handle} mapping is "store[d]... in a
/// Seal-encrypted record"). Only the owning address may decrypt — the
/// identity is just that address, BCS-encoded.
module umbra::seal_policy_handle {
    use sui::bcs;

    const ENoAccess: u64 = 0;

    entry fun seal_approve(id: vector<u8>, ctx: &TxContext) {
        let mut reader = bcs::new(id);
        let owner_addr = reader.peel_address();
        assert!(ctx.sender() == owner_addr, ENoAccess);
    }
}
