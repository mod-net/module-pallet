use mod_net_runtime::WASM_BINARY;
use sc_service::ChainType;

fn load_runtime_wasm() -> Result<Vec<u8>, String> {
    if let Some(b) = WASM_BINARY {
        return Ok(b.to_vec());
    }
    // Try env override first
    if let Ok(p) = std::env::var("MODNET_WASM_PATH") {
        return std::fs::read(&p).map_err(|e| format!("Failed to read MODNET_WASM_PATH={p}: {e}"));
    }
    // Try common wbuild locations
    let candidates = [
        "target/release/wbuild/mod-net-runtime/mod_net_runtime.compact.compressed.wasm",
        "target/debug/wbuild/mod-net-runtime/mod_net_runtime.compact.compressed.wasm",
        "target/release/wbuild/solochain-template-runtime/solochain_template_runtime.compact.compressed.wasm",
        "target/debug/wbuild/solochain-template-runtime/solochain_template_runtime.compact.compressed.wasm",
    ];
    for p in candidates {
        if let Ok(bytes) = std::fs::read(p) {
            return Ok(bytes);
        }
    }
    Err("Development wasm not available".to_string())
}

/// Specialized `ChainSpec`. This is a specialization of the general Substrate ChainSpec type.
pub type ChainSpec = sc_service::GenericChainSpec;

pub fn development_chain_spec() -> Result<ChainSpec, String> {
    let wasm = load_runtime_wasm()?;
    Ok(ChainSpec::builder(&wasm, None)
        .with_name("Development")
        .with_id("dev")
        .with_chain_type(ChainType::Development)
        .with_genesis_config_preset_name(sp_genesis_builder::DEV_RUNTIME_PRESET)
        .build())
}

pub fn local_chain_spec() -> Result<ChainSpec, String> {
    let wasm = load_runtime_wasm()?;
    Ok(ChainSpec::builder(&wasm, None)
        .with_name("Local Testnet")
        .with_id("local_testnet")
        .with_chain_type(ChainType::Local)
        .with_genesis_config_preset_name(sp_genesis_builder::LOCAL_TESTNET_RUNTIME_PRESET)
        .build())
}
