# RustChain Security Quest #398 - Step 1 and Step 2 Assessment

Claimant wallet: `JNCjmuxhJgAUg1WL9rq7tZCRSVT2f1yRhhWdFj9UpsU`

Scope reviewed:

- `docs/attestation-flow.md`
- `docs/hardware-fingerprinting.md`
- `docs/epoch-settlement.md`
- `rip201_bucket_fix.py`

## Step 1 - Security Assessment

### `/attest/submit` Trust Boundary

RustChain's attestation flow is the enrollment path that decides whether a miner is allowed into an epoch and what reward multiplier that miner receives. The documented sequence is: the miner starts a mining session, the client collects system information, runs hardware checks, builds a fingerprint JSON object, signs it with an Ed25519 key, and sends it to `POST /attest/submit`.

The node-side trust boundary starts at this endpoint. Everything before the request is client-controlled and therefore untrusted. The server must verify the signature, validate the fingerprint, reject VM or emulator indicators, check whether the same hardware is already enrolled, and only then record epoch enrollment and multiplier information.

The strongest part of the design is that it does not treat a wallet string or a claimed CPU family as sufficient evidence. The attestation payload is expected to include device information and fingerprint evidence, and the server is expected to perform duplicate-hardware checks before enrollment. The weak point is that any field collected by the client can be spoofed unless the server derives reward-critical classification from independently cross-checked evidence. That makes server-side validation the core security control.

### Hardware Fingerprinting and VM-Farm Resistance

RustChain's anti-farm design is based on multiple independent signals rather than one hardware identifier. The hardware fingerprinting documentation lists six primary checks plus behavioral heuristics:

- Clock skew and oscillator drift
- Cache timing fingerprint
- SIMD unit identity
- Thermal drift entropy
- Instruction path jitter
- Anti-emulation checks
- Behavioral hypervisor heuristics

This is a stronger model than simply checking `platform.machine()` or a CPU brand string. VM farms can spoof obvious fields, but they struggle to reproduce a consistent physical profile across timing, thermal, instruction, and cache behavior. A VM can report "PowerPC G4", but matching G4-like cache timing, AltiVec evidence, aging oscillator drift, and non-hypervisor behavior is much harder.

The main security requirement is that these checks must be enforced server-side for any reward multiplier decision. If the node accepts raw client labels such as `device_arch` or `family`, a miner can bypass the economic model by claiming a more valuable antiquity class while running on modern commodity hardware.

### Epoch Rewards

The epoch settlement documentation describes a 24-hour epoch with 144 ten-minute slots. Miners submit attestations during the epoch. At settlement, active enrolled miners are selected, total weight is calculated from their antiquity multipliers, and the epoch pot is distributed proportionally.

The important security property is that settlement depends on previously accepted enrollment state. If fake or duplicated hardware is admitted before settlement, the epoch calculation can be economically correct while still paying the wrong participants. This means attestation correctness is upstream of reward correctness.

There are two settlement-related attack surfaces:

1. Enrollment poisoning: attacker gets invalid hardware accepted into an epoch with an inflated multiplier.
2. Liveness manipulation: attacker appears active near settlement time without doing honest periodic attestation.

The documented `last_attest` filter helps with liveness by requiring recent activity. It does not by itself protect multiplier integrity. Multiplier integrity must come from the attestation and hardware validation path.

### Potential Attack Vector

The clearest attack vector is reward-bucket spoofing. An attacker running a modern x86 system claims a vintage PowerPC family in the attestation payload. If the node uses the claimed `device_arch` or family string directly to assign a vintage bucket, the attacker receives a higher multiplier than honest modern hardware. At scale, this can drain a disproportionate share of the epoch pot and dilute real vintage miners.

The attack is economically attractive because it does not require breaking signatures or consensus. It only requires a client to lie about hardware classification if the server trusts that field. It also scales well across a farm unless duplicate-hardware checks and fingerprint correlation are strong enough to detect repeated profiles.

## Step 2 - Known Fix Reproduction: Antiquity / Bucket Spoofing

I selected the known fix represented by `rip201_bucket_fix.py`, which addresses modern CPU claims being routed into a vintage reward bucket.

### Attack Before the Fix

Before the fix, the vulnerable pattern is:

1. Miner submits an attestation payload.
2. Payload includes a claimed architecture or family, for example `device_arch=G4`.
3. Server routes the miner into a reward bucket based on that client-controlled claim.
4. Modern x86 hardware receives a vintage PowerPC multiplier.

The issue is not that the client sends architecture data. The issue is using client-reported architecture as the authority for reward classification.

### Fix in the Code

`rip201_bucket_fix.py` adds server-side defenses around bucket classification. The module summary identifies four key controls:

- CPU brand-string cross-validation against the claimed `device_arch`
- SIMD evidence requirements for vintage PowerPC claims, especially AltiVec / `vec_perm`
- Cache-timing profile validation against expected PowerPC characteristics
- Server-side bucket classification derived from verified hardware features rather than raw client-reported strings

The first concrete layer is the modern x86 brand-pattern list. It detects Intel and AMD product families such as Core, Xeon, Ryzen, EPYC, Athlon, Threadripper, and vendor strings such as `GenuineIntel` or `AuthenticAMD`. If a payload claims a PowerPC class while exposing one of these modern x86 identifiers, the server has a direct inconsistency signal.

That alone is not sufficient, because brand strings can also be spoofed. The stronger part is the combined-evidence model: a vintage PowerPC claim needs supporting SIMD and cache-timing evidence. The server should classify the bucket from verified properties instead of accepting the client's requested bucket.

### Why the Fix Is Sufficient for This Class

The fix addresses the root cause: reward-critical bucket assignment moves from "client says it is G4" to "server verifies whether the evidence is consistent with G4-like hardware."

It is sufficient against the basic attack because a modern x86 machine claiming PowerPC has to pass multiple independent checks:

- It must avoid modern x86 brand detection.
- It must provide PowerPC-specific SIMD evidence.
- It must match cache timing characteristics.
- It must survive server-side reclassification from verified features.

The attack cost increases from changing a JSON field to simulating a coherent hardware profile. That is the right direction for RustChain's Proof-of-Antiquity model.

### Remaining Limitations

This fix is strong for obvious x86-to-vintage spoofing, but the broader system still depends on:

- How robustly timing evidence is collected.
- Whether the server rejects missing or low-confidence evidence.
- Whether fingerprint profiles are normalized consistently across operating systems.
- Whether duplicate or near-duplicate fingerprints are detected across wallets.

The safest policy is fail-closed for high-value antiquity buckets: if a miner claims a vintage family but cannot provide enough corroborating evidence, it should fall back to a conservative modern/unknown bucket instead of receiving the vintage multiplier.

## Suggested Additional Hardening

1. Record a validation confidence score with every enrollment.
2. Store the derived bucket and the evidence used to derive it, not only the raw payload.
3. Add regression tests for mismatched claims such as `device_arch=G4` plus `Intel Xeon` brand strings.
4. Treat missing SIMD/cache evidence as ineligible for vintage multipliers.
5. Rate-limit repeated failed attestation attempts from the same network and wallet.

## Conclusion

RustChain's design has the right high-level shape: signed attestations, multi-signal hardware fingerprints, duplicate hardware checks, and epoch settlement based on enrolled miners. The main security lesson is that the node must never let client-controlled labels decide reward multipliers. `rip201_bucket_fix.py` implements the correct server-side pattern by cross-validating claims and deriving reward buckets from verified hardware evidence.
