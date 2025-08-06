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
//! ## Usage
//!
//! TODO: Implementation will be added in subsequent commits

pub use pallet::*;

#[frame_support::pallet]
pub mod pallet {
    use frame_support::pallet_prelude::*;

    #[pallet::pallet]
    pub struct Pallet<T>(_);

    #[pallet::config]
    pub trait Config: frame_system::Config {
        type RuntimeEvent: From<Event<Self>> + IsType<<Self as frame_system::Config>::RuntimeEvent>;
    }

    #[pallet::event]
    pub enum Event<T: Config> {
        /// This is a placeholder event - actual events will be implemented later
        #[allow(dead_code)]
        Placeholder,
    }

    // Note: Errors and calls will be implemented in subsequent commits
}
