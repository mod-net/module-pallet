---
name: Fix Deployment Setup After Commune-IPFS Removal
about: Update deployment configuration and scripts after removing commune-ipfs submodule
title: 'fix(deployment): Remove commune-ipfs dependencies and update deployment setup'
labels: ['bug', 'deployment', 'breaking-change']
assignees: []
---

## Purpose

Fix deployment setup and configuration after removing the commune-ipfs submodule dependency. Multiple scripts, configurations, and documentation files still reference the removed submodule, causing deployment failures.

## Technical Details

### Impact Analysis
The commune-ipfs submodule removal affects:
- **17 files** with commune-ipfs references
- Integration test scripts
- Service management scripts
- Configuration files
- Documentation

### Affected Files Requiring Updates

#### High Priority (Deployment Critical)
- [ ] `scripts/test_real_chain_integration.py` (13 references)
- [ ] `scripts/manage-services.sh` (3 references)
- [ ] `scripts/config.py` (3 references)
- [ ] `.pre-commit-config.yaml` (3 references)
- [ ] `pyproject.toml` (3 references)

#### Medium Priority (Testing & Development)
- [ ] `modules/test_module/test_integration.py` (3 references)
- [ ] `modules/test_module/module.py` (1 reference)
- [ ] `modules/test_module/README.md` (5 references)

#### Low Priority (Documentation)
- [ ] `docs/INFRASTRUCTURE_UPDATE.md` (3 references)
- [ ] `docs/archive/mcp-development-tickets-simplified.md` (4 references)
- [ ] `docs/archive/mcp-development-tickets.md` (2 references)
- [ ] `docs/archive/mcp-pallet.md` (2 references)
- [ ] `docs/project-spec.md` (2 references)
- [ ] `CONTRIBUTING.md` (1 reference)
- [ ] `README.md` (1 reference)
- [ ] `docs/DEVELOPMENT.md` (1 reference)
- [ ] `pallets/module-registry/README.md` (1 reference)

### Required Changes

#### 1. IPFS Integration Strategy
Replace commune-ipfs with:
- [ ] Direct IPFS client integration using `ipfs-api` or `kubo-rpc-client`
- [ ] Update `mod_net_client/ipfs/handler.py` to use standard IPFS APIs
- [ ] Configure IPFS service in CI/CD (already partially done in `integration.yml`)

#### 2. Service Management Updates
- [ ] Update `scripts/manage-services.sh` to remove commune-ipfs service management
- [ ] Modify `scripts/config.py` to remove commune-ipfs configuration
- [ ] Update service startup scripts to use containerized IPFS

#### 3. Integration Test Fixes
- [ ] Refactor `scripts/test_real_chain_integration.py` to use direct IPFS connection
- [ ] Update test modules to connect to IPFS service container
- [ ] Fix integration test workflows

#### 4. Configuration Updates
- [ ] Remove commune-ipfs from `pyproject.toml` dependencies
- [ ] Update `.pre-commit-config.yaml` to remove commune-ipfs hooks
- [ ] Update environment configuration files

#### 5. Documentation Updates
- [ ] Update all documentation to reflect new IPFS integration approach
- [ ] Remove references to commune-ipfs submodule
- [ ] Add instructions for IPFS service setup

### Implementation Plan

#### Phase 1: Critical Path (Deployment Fixes)
1. **Update IPFS Client Integration**
   ```python
   # Replace commune-ipfs imports with:
   import ipfshttpclient
   # or
   from ipfs_api import IPFSApi
   ```

2. **Fix Service Scripts**
   - Remove commune-ipfs service management
   - Add IPFS container/service management
   - Update configuration loading

3. **Update CI/CD**
   - Ensure IPFS service container works properly
   - Fix integration test connections

#### Phase 2: Testing & Validation
1. **Integration Tests**
   - Verify IPFS connectivity in tests
   - Update test data and expectations
   - Validate end-to-end workflows

2. **Service Validation**
   - Test service startup/shutdown
   - Verify IPFS operations work correctly
   - Check performance impact

#### Phase 3: Documentation & Cleanup
1. **Documentation Updates**
   - Update deployment guides
   - Fix development setup instructions
   - Update architecture diagrams

2. **Code Cleanup**
   - Remove dead code references
   - Update import statements
   - Clean up configuration files

### Acceptance Criteria

- [ ] All deployment scripts run without commune-ipfs errors
- [ ] Integration tests pass with new IPFS setup
- [ ] Service management scripts work correctly
- [ ] CI/CD pipeline builds and tests successfully
- [ ] Documentation accurately reflects current setup
- [ ] No remaining commune-ipfs references in active code
- [ ] IPFS functionality works equivalently to previous setup
- [ ] Performance regression testing passes

### Dependencies

- Standard IPFS client library (ipfshttpclient or kubo-rpc-client)
- IPFS service/container configuration
- Updated test fixtures and data

### Breaking Changes

This fix addresses breaking changes introduced by commune-ipfs removal:
- Service startup procedures changed
- IPFS client API may differ
- Configuration file format updates
- Test setup modifications

### Priority: Critical
This directly blocks deployment and development workflows, preventing the team from achieving the macro-goal of maintaining a functional, deployable module pallet system.
