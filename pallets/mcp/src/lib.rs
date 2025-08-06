#![cfg_attr(not(feature = "std"), no_std)]

//! # Model Context Protocol (MCP) Pallet
//!
//! This pallet provides a framework for managing and executing AI tools, prompts, and resources
//! on the blockchain through the standardized Model Context Protocol.
//!
//! ## Overview
//!
//! The MCP pallet enables decentralized AI services by facilitating communication between
//! AI clients and servers. It supports:
//!
//! - Server registration and discovery
//! - Tool registration and execution
//! - Prompt template management
//! - Resource handling via IPFS
//! - Access control and permissions
//!
//! ## Architecture
//!
//! The pallet follows the Model Context Protocol specification (2024-11-05) and provides
//! on-chain orchestration for AI services while leveraging IPFS for off-chain metadata storage.

use frame_support::{
    pallet_prelude::*,
    traits::{Get, Randomness},
};
use frame_system::pallet_prelude::*;
use scale_info::TypeInfo;
use sp_runtime::RuntimeDebug;

pub use pallet::*;

/// Type alias for server identifiers
pub type ServerId = u64;

/// Type alias for tool identifiers
pub type ToolId = u64;

/// Type alias for prompt identifiers
pub type PromptId = u64;

/// Type alias for resource identifiers
pub type ResourceId = u64;

/// Type alias for IPFS CIDs
pub type IpfsCid = BoundedVec<u8, ConstU32<64>>;

/// Protocol version following RMCP SDK conventions
#[derive(Clone, PartialEq, Eq, Encode, Decode, RuntimeDebug, TypeInfo, Default)]
pub enum ProtocolVersion {
    #[default]
    V20241105,
    V20250326,
}

#[derive(Clone, PartialEq, Eq, Encode, Decode, RuntimeDebug, TypeInfo)]
pub enum ProtocolVersionError {
    UnsupportedVersion,
}

impl ProtocolVersion {
    /// MCP Protocol version 2024-11-05
    pub const V_2024_11_05: &'static [u8] = b"2024-11-05";
    /// MCP Protocol version 2025-03-26 (latest)
    pub const V_2025_03_26: &'static [u8] = b"2025-03-26";

    /// Create a new protocol version
    pub fn new(version: &[u8]) -> Result<Self, ProtocolVersionError> {
        match version {
            b"2024-11-05" => Ok(ProtocolVersion::V20241105),
            b"2025-03-26" => Ok(ProtocolVersion::V20250326),
            _ => Err(ProtocolVersionError::UnsupportedVersion),
        }
    }

    /// Get the latest supported version
    pub fn latest() -> Self {
        ProtocolVersion::V20250326
    }

    /// Get version 2024-11-05
    pub fn v_2024_11_05() -> Self {
        ProtocolVersion::V20241105
    }
}

/// Tools capability configuration
#[derive(Encode, Decode, Clone, PartialEq, Eq, RuntimeDebug, TypeInfo, Default)]
pub struct ToolsCapability {
    /// Whether the server notifies when tool list changes
    pub list_changed: Option<bool>,
}

/// Prompts capability configuration
#[derive(Encode, Decode, Clone, PartialEq, Eq, RuntimeDebug, TypeInfo, Default)]
pub struct PromptsCapability {
    /// Whether the server notifies when prompt list changes
    pub list_changed: Option<bool>,
}

/// Resources capability configuration
#[derive(Encode, Decode, Clone, PartialEq, Eq, RuntimeDebug, TypeInfo, Default)]
pub struct ResourcesCapability {
    /// Whether the server supports resource subscriptions
    pub subscribe: Option<bool>,
    /// Whether the server notifies when resource list changes
    pub list_changed: Option<bool>,
}

/// Server capabilities configuration following RMCP SDK structure
#[derive(Encode, Decode, Clone, PartialEq, Eq, RuntimeDebug, TypeInfo, Default)]
pub struct ServerCapabilities {
    /// Logging capability
    pub logging: Option<bool>,
    /// Completions capability
    pub completions: Option<bool>,
    /// Tools capability
    pub tools: Option<ToolsCapability>,
    /// Prompts capability
    pub prompts: Option<PromptsCapability>,
    /// Resources capability
    pub resources: Option<ResourcesCapability>,
    /// Sampling capability (JSON object)
    pub sampling: Option<bool>,
}

/// Transport configuration for MCP servers
#[derive(Encode, Decode, Clone, PartialEq, Eq, RuntimeDebug, TypeInfo)]
pub enum TransportConfig {
    /// Standard input/output transport
    Stdio,
    /// HTTP transport with endpoint
    Http {
        endpoint: BoundedVec<u8, ConstU32<256>>,
    },
    /// Server-Sent Events transport
    Sse {
        endpoint: BoundedVec<u8, ConstU32<256>>,
    },
    /// WebSocket transport
    WebSocket {
        endpoint: BoundedVec<u8, ConstU32<256>>,
    },
}

impl Default for TransportConfig {
    fn default() -> Self {
        Self::Stdio
    }
}

/// Server information structure
#[derive(Encode, Decode, Clone, PartialEq, Eq, RuntimeDebug, TypeInfo)]
pub struct ServerInfo<AccountId: Clone + PartialEq + Eq> {
    /// Server owner account
    pub owner: AccountId,
    /// Server name
    pub name: BoundedVec<u8, ConstU32<64>>,
    /// Server description
    pub description: Option<BoundedVec<u8, ConstU32<256>>>,
    /// Protocol version
    pub protocol_version: ProtocolVersion,
    /// Server capabilities
    pub capabilities: ServerCapabilities,
    /// Transport configuration
    pub transport: TransportConfig,
    /// IPFS CID for additional metadata
    pub metadata_cid: Option<IpfsCid>,
    /// Server status
    pub active: bool,
    /// Block number when server was registered
    pub created_at: u64,
    /// Block number when server was last updated
    pub updated_at: u64,
}

/// Tool annotations providing hints about tool behavior
#[derive(Encode, Decode, Clone, PartialEq, Eq, RuntimeDebug, TypeInfo, Default)]
pub struct ToolAnnotations {
    /// Human-readable title for the tool
    pub title: Option<BoundedVec<u8, ConstU32<128>>>,
    /// Whether the tool is read-only (doesn't modify environment)
    pub read_only_hint: Option<bool>,
    /// Whether the tool performs destructive updates
    pub destructive_hint: Option<bool>,
    /// Whether the tool is idempotent
    pub idempotent_hint: Option<bool>,
    /// Whether the tool interacts with an "open world"
    pub open_world_hint: Option<bool>,
}

/// Tool information structure following RMCP SDK structure
#[derive(Encode, Decode, Clone, PartialEq, Eq, RuntimeDebug, TypeInfo)]
pub struct ToolInfo {
    /// Associated server ID
    pub server_id: ServerId,
    /// Tool name
    pub name: BoundedVec<u8, ConstU32<64>>,
    /// Tool description
    pub description: Option<BoundedVec<u8, ConstU32<256>>>,
    /// JSON schema for input parameters (stored as JSON string)
    pub input_schema: BoundedVec<u8, ConstU32<2048>>,
    /// JSON schema for output parameters (stored as JSON string)
    pub output_schema: Option<BoundedVec<u8, ConstU32<2048>>>,
    /// Tool annotations providing behavioral hints
    pub annotations: Option<ToolAnnotations>,
    /// IPFS CID for additional metadata
    pub metadata_cid: Option<IpfsCid>,
    /// Tool status
    pub active: bool,
}

/// Prompt template structure
#[derive(Encode, Decode, Clone, PartialEq, Eq, RuntimeDebug, TypeInfo)]
pub struct PromptTemplate {
    /// Associated server ID
    pub server_id: ServerId,
    /// Prompt name
    pub name: BoundedVec<u8, ConstU32<64>>,
    /// Prompt description
    pub description: Option<BoundedVec<u8, ConstU32<256>>>,
    /// Prompt template content
    pub template: BoundedVec<u8, ConstU32<2048>>,
    /// JSON schema for template parameters
    pub parameter_schema: Option<BoundedVec<u8, ConstU32<1024>>>,
    /// Prompt category
    pub category: Option<BoundedVec<u8, ConstU32<32>>>,
    /// IPFS CID for additional metadata
    pub metadata_cid: Option<IpfsCid>,
    /// Prompt status
    pub active: bool,
}

/// Resource information structure
#[derive(Encode, Decode, Clone, PartialEq, Eq, RuntimeDebug, TypeInfo)]
pub struct ResourceInfo {
    /// Associated server ID
    pub server_id: ServerId,
    /// Resource name
    pub name: BoundedVec<u8, ConstU32<64>>,
    /// Resource description
    pub description: Option<BoundedVec<u8, ConstU32<256>>>,
    /// Resource URI or identifier
    pub uri: BoundedVec<u8, ConstU32<256>>,
    /// MIME type
    pub mime_type: Option<BoundedVec<u8, ConstU32<64>>>,
    /// IPFS CID for resource content
    pub content_cid: IpfsCid,
    /// IPFS CID for additional metadata
    pub metadata_cid: Option<IpfsCid>,
    /// Resource status
    pub active: bool,
}

#[frame_support::pallet]
#[allow(dead_code)]
pub mod pallet {
    use super::*;

    #[pallet::pallet]
    pub struct Pallet<T>(_);

    /// Configuration trait for the MCP pallet
    #[pallet::config]
    pub trait Config: frame_system::Config {
        /// The overarching runtime event type
        type RuntimeEvent: From<Event<Self>> + IsType<<Self as frame_system::Config>::RuntimeEvent>;

        /// Weight information for extrinsics
        type WeightInfo: WeightInfo;

        /// Randomness source for generating IDs
        type Randomness: Randomness<Self::Hash, BlockNumberFor<Self>>;

        /// Maximum number of servers per owner
        #[pallet::constant]
        type MaxServersPerOwner: Get<u32>;

        /// Maximum number of tools per server
        #[pallet::constant]
        type MaxToolsPerServer: Get<u32>;

        /// Maximum number of prompts per server
        #[pallet::constant]
        type MaxPromptsPerServer: Get<u32>;

        /// Maximum number of resources per server
        #[pallet::constant]
        type MaxResourcesPerServer: Get<u32>;

        /// Maximum length for server names
        #[pallet::constant]
        type MaxNameLength: Get<u32>;

        /// Maximum length for descriptions
        #[pallet::constant]
        type MaxDescriptionLength: Get<u32>;

        /// Maximum length for JSON schemas
        #[pallet::constant]
        type MaxSchemaLength: Get<u32>;

        /// Maximum length for prompt templates
        #[pallet::constant]
        type MaxTemplateLength: Get<u32>;

        /// Maximum length for resource URIs
        #[pallet::constant]
        type MaxUriLength: Get<u32>;

        /// Maximum length for IPFS CIDs
        #[pallet::constant]
        type MaxCidLength: Get<u32>;
    }

    /// Placeholder event - will be implemented in MCP-003
    #[pallet::event]
    #[pallet::generate_deposit(pub(super) fn deposit_event)]
    pub enum Event<T: Config> {
        /// Placeholder event for compilation
        #[codec(index = 0)]
        Placeholder,
    }

    /// Placeholder error - will be implemented in MCP-003
    #[pallet::error]
    pub enum Error<T> {
        /// Placeholder error for compilation
        Placeholder,
    }

    // Storage items will be implemented in MCP-002
    // Extrinsics will be implemented in subsequent tickets
}

/// Weight information trait for benchmarking
pub trait WeightInfo {
    // Weight functions will be implemented with extrinsics
}

/// Default weight implementation
impl WeightInfo for () {
    // Default implementations will be added
}

#[cfg(test)]
mod tests {
    use super::*;
    use frame_support::{
        parameter_types,
        traits::{ConstU32, Randomness},
    };
    use sp_core::H256;
    use sp_runtime::{
        traits::{BlakeTwo256, IdentityLookup},
        BuildStorage,
    };

    type Block = frame_system::mocking::MockBlock<Test>;

    // Mock randomness for testing
    pub struct MockRandomness;
    impl Randomness<H256, u64> for MockRandomness {
        fn random(_subject: &[u8]) -> (H256, u64) {
            (H256::zero(), 0)
        }
    }

    frame_support::construct_runtime!(
        pub enum Test
        {
            System: frame_system,
            McpPallet: crate,
        }
    );

    parameter_types! {
        pub const BlockHashCount: u64 = 250;
        pub const SS58Prefix: u8 = 42;
    }

    impl frame_system::Config for Test {
        type BaseCallFilter = frame_support::traits::Everything;
        type BlockWeights = ();
        type BlockLength = ();
        type DbWeight = ();
        type RuntimeOrigin = RuntimeOrigin;
        type RuntimeCall = RuntimeCall;
        type Nonce = u64;
        type Hash = H256;
        type Hashing = BlakeTwo256;
        type AccountId = u64;
        type Lookup = IdentityLookup<Self::AccountId>;
        type Block = Block;
        type RuntimeEvent = RuntimeEvent;
        type BlockHashCount = BlockHashCount;
        type Version = ();
        type PalletInfo = PalletInfo;
        type AccountData = ();
        type OnNewAccount = ();
        type OnKilledAccount = ();
        type SystemWeightInfo = ();
        type SS58Prefix = SS58Prefix;
        type OnSetCode = ();
        type MaxConsumers = ConstU32<16>;
        type RuntimeTask = ();
        type ExtensionsWeightInfo = ();
        type SingleBlockMigrations = ();
        type MultiBlockMigrator = ();
        type PreInherents = ();
        type PostInherents = ();
        type PostTransactions = ();
    }

    parameter_types! {
        pub const MaxServersPerOwner: u32 = 10;
        pub const MaxToolsPerServer: u32 = 50;
        pub const MaxPromptsPerServer: u32 = 20;
        pub const MaxResourcesPerServer: u32 = 100;
        pub const MaxNameLength: u32 = 64;
        pub const MaxDescriptionLength: u32 = 256;
        pub const MaxSchemaLength: u32 = 1024;
        pub const MaxTemplateLength: u32 = 2048;
        pub const MaxUriLength: u32 = 256;
        pub const MaxCidLength: u32 = 64;
    }

    impl Config for Test {
        type RuntimeEvent = RuntimeEvent;
        type WeightInfo = ();
        type Randomness = MockRandomness;
        type MaxServersPerOwner = MaxServersPerOwner;
        type MaxToolsPerServer = MaxToolsPerServer;
        type MaxPromptsPerServer = MaxPromptsPerServer;
        type MaxResourcesPerServer = MaxResourcesPerServer;
        type MaxNameLength = MaxNameLength;
        type MaxDescriptionLength = MaxDescriptionLength;
        type MaxSchemaLength = MaxSchemaLength;
        type MaxTemplateLength = MaxTemplateLength;
        type MaxUriLength = MaxUriLength;
        type MaxCidLength = MaxCidLength;
    }

    fn new_test_ext() -> sp_io::TestExternalities {
        frame_system::GenesisConfig::<Test>::default()
            .build_storage()
            .unwrap()
            .into()
    }

    #[test]
    fn test_protocol_version_default() {
        let default_version = ProtocolVersion::default();
        assert_eq!(default_version, ProtocolVersion::V20241105);
    }

    #[test]
    fn test_protocol_version_creation() {
        let v1 = ProtocolVersion::V20241105;
        let v2 = ProtocolVersion::V20250326;

        assert_eq!(v1, ProtocolVersion::V20241105);
        assert_eq!(v2, ProtocolVersion::V20250326);
    }

    #[test]
    fn test_server_capabilities_default() {
        let capabilities = ServerCapabilities::default();
        assert!(capabilities.logging.is_none());
        assert!(capabilities.completions.is_none());
        assert!(capabilities.tools.is_none());
        assert!(capabilities.prompts.is_none());
        assert!(capabilities.resources.is_none());
        assert!(capabilities.sampling.is_none());
    }

    #[test]
    fn test_server_capabilities_with_tools() {
        let capabilities = ServerCapabilities {
            tools: Some(ToolsCapability {
                list_changed: Some(true),
            }),
            ..Default::default()
        };

        assert!(capabilities.tools.is_some());
        assert_eq!(capabilities.tools.unwrap().list_changed, Some(true));
    }

    #[test]
    fn test_transport_config_default() {
        assert_eq!(TransportConfig::default(), TransportConfig::Stdio);
    }

    #[test]
    fn test_server_info_creation() {
        new_test_ext().execute_with(|| {
            let server_info = ServerInfo {
                owner: 1u64,
                name: b"test-server".to_vec().try_into().unwrap(),
                description: Some(b"Test server description".to_vec().try_into().unwrap()),
                protocol_version: ProtocolVersion::v_2024_11_05(),
                capabilities: ServerCapabilities {
                    logging: None,
                    completions: None,
                    tools: Some(ToolsCapability {
                        list_changed: Some(true),
                    }),
                    prompts: Some(PromptsCapability {
                        list_changed: Some(true),
                    }),
                    resources: None,
                    sampling: None,
                },
                transport: TransportConfig::Stdio,
                metadata_cid: None,
                active: true,
                created_at: 1u64,
                updated_at: 1u64,
            };

            assert_eq!(server_info.owner, 1u64);
            assert_eq!(server_info.name.to_vec(), b"test-server".to_vec());
            assert!(server_info.capabilities.tools.is_some());
            assert!(server_info.capabilities.prompts.is_some());
            assert!(server_info.capabilities.resources.is_none());
            assert!(server_info.capabilities.sampling.is_none());
        });
    }

    #[test]
    fn test_tool_info_creation() {
        let tool_info = ToolInfo {
            server_id: 1,
            name: b"test-tool".to_vec().try_into().unwrap(),
            description: Some(b"Test tool description".to_vec().try_into().unwrap()),
            input_schema: b"{\"type\": \"object\"}".to_vec().try_into().unwrap(),
            output_schema: None,
            annotations: None,
            metadata_cid: None,
            active: true,
        };

        assert_eq!(tool_info.server_id, 1);
        assert_eq!(tool_info.name.to_vec(), b"test-tool".to_vec());
        assert!(tool_info.active);
    }

    #[test]
    fn test_prompt_template_creation() {
        let prompt = PromptTemplate {
            server_id: 1,
            name: b"test-prompt".to_vec().try_into().unwrap(),
            description: Some(b"Test prompt description".to_vec().try_into().unwrap()),
            template: b"Hello {{name}}!".to_vec().try_into().unwrap(),
            parameter_schema: Some(b"{\"type\": \"object\"}".to_vec().try_into().unwrap()),
            category: Some(b"greeting".to_vec().try_into().unwrap()),
            metadata_cid: None,
            active: true,
        };

        assert_eq!(prompt.server_id, 1);
        assert_eq!(prompt.name.to_vec(), b"test-prompt".to_vec());
        assert_eq!(prompt.template.to_vec(), b"Hello {{name}}!".to_vec());
        assert!(prompt.active);
    }

    #[test]
    fn test_resource_info_creation() {
        let resource = ResourceInfo {
            server_id: 1,
            name: b"test-resource".to_vec().try_into().unwrap(),
            description: Some(b"Test resource description".to_vec().try_into().unwrap()),
            uri: b"file://test.txt".to_vec().try_into().unwrap(),
            mime_type: Some(b"text/plain".to_vec().try_into().unwrap()),
            content_cid: b"QmTest123".to_vec().try_into().unwrap(),
            metadata_cid: None,
            active: true,
        };

        assert_eq!(resource.server_id, 1);
        assert_eq!(resource.name.to_vec(), b"test-resource".to_vec());
        assert_eq!(resource.uri.to_vec(), b"file://test.txt".to_vec());
        assert_eq!(resource.content_cid.to_vec(), b"QmTest123".to_vec());
        assert!(resource.active);
    }

    #[test]
    fn test_types_implement_required_traits() {
        // Test that all types implement required traits for Substrate
        let _: ProtocolVersion = ProtocolVersion::v_2024_11_05();
        let _: ServerCapabilities = ServerCapabilities::default();
        let _: TransportConfig = TransportConfig::default();

        // These should compile without errors, proving the traits are implemented
        // Test passes if no panic occurs
    }
}
