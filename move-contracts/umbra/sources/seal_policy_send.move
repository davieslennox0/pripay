/// Seal access policy for send-record decryption (brief §5: "decryption
/// access controlled via Seal's identity-based access policies, scoped to
/// sender + receiver's Sui addresses only").
///
/// Seal key servers dry-run `seal_approve` before releasing a decryption
/// key share for a given identity. The identity (`id`) is whatever bytes
/// the encrypting client chose at encrypt time — here, the sender and
/// receiver addresses concatenated (32 bytes each, BCS-encoded). No
/// on-chain record object needs to exist for this check; the addresses are
/// embedded directly in the identity, and the caller's own signature
/// (ctx.sender()) proves who's asking.
module umbra::seal_policy_send {
    use sui::bcs;

    const ENoAccess: u64 = 0;

    entry fun seal_approve(id: vector<u8>, ctx: &TxContext) {
        let mut reader = bcs::new(id);
        let sender_addr = reader.peel_address();
        let receiver_addr = reader.peel_address();
        let caller = ctx.sender();
        assert!(caller == sender_addr || caller == receiver_addr, ENoAccess);
    }
}
