use substrate_build_script_utils::{generate_cargo_keys, rerun_if_git_head_changed};

fn main() {
    // Always generate cargo keys
    generate_cargo_keys();

    // Skip only the git-dependent rerun logic in containerized builds to avoid
    // warnings like "fatal: not a git repository" when .git is not present.
    if std::env::var("MODNET_SKIP_GIT").is_err() {
        rerun_if_git_head_changed();
    }
}
