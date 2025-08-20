fn main() {
    // Build scripts do not receive crate features via `cfg(feature = ...)`.
    // Cargo exposes enabled features as `CARGO_FEATURE_*` env vars.
    let std_enabled = std::env::var("CARGO_FEATURE_STD").is_ok();
    if !std_enabled {
        // No native build; skip generating the embedded wasm.
        return;
    }

    let builder = substrate_wasm_builder::WasmBuilder::init_with_defaults();
    builder.build();
}
