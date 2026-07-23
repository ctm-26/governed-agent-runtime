#!/usr/bin/env python3
"""State-machine tests for scripts/bootstrap-github.sh."""

from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = Path("scripts/bootstrap-github.sh")
REAL_GIT = shutil.which("git")

MOCK_GH = """\
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

args = sys.argv[1:]
log_path = Path(os.environ["MOCK_GH_LOG"])
with log_path.open("a", encoding="utf-8") as stream:
    stream.write(" ".join(args) + "\\n")

if args[:2] == ["auth", "status"]:
    if os.environ.get("MOCK_GH_AUTH", "ok") != "ok":
        print("not logged in", file=sys.stderr)
        raise SystemExit(1)
    host = os.environ.get("GITHUB_HOST", "github.test")
    scopes = os.environ.get("MOCK_GH_SCOPES", "repo,workflow")
    rendered = ", ".join(f"'{scope}'" for scope in scopes.split(",") if scope)
    print(host)
    print("  logged in")
    if rendered:
        print(f"  - Token scopes: {rendered}")
    raise SystemExit(0)

if args == ["api", "--hostname", os.environ["GITHUB_HOST"], "--include", "user"]:
    if os.environ.get("MOCK_GH_API_AUTH", "ok") != "ok":
        print("gh: authentication failed (HTTP 401)", file=sys.stderr)
        raise SystemExit(1)
    scopes = os.environ.get("MOCK_GH_SCOPES", "repo,workflow")
    sys.stdout.write("HTTP/2.0 200 OK\\r\\n")
    if scopes:
        sys.stdout.write(f"X-OAuth-Scopes: {scopes}\\r\\n")
    sys.stdout.write('\\r\\n{"login":"example"}\\n')
    raise SystemExit(0)

if args and args[0] == "api":
    expected_endpoint = f"repos/{os.environ['GITHUB_OWNER']}/{os.environ['GITHUB_REPO']}"
    expected_args = [
        "api",
        "--hostname",
        os.environ["GITHUB_HOST"],
        expected_endpoint,
        "--jq",
        "[.full_name, .clone_url, .visibility, (.permissions.push // false)] | @tsv",
    ]
    if args != expected_args:
        print(f"unexpected repository API invocation: {' '.join(args)}", file=sys.stderr)
        raise SystemExit(2)
    state = Path(os.environ["MOCK_GH_STATE"]).read_text(encoding="utf-8").strip()
    if state != "existing":
        print("gh: Not Found (HTTP 404)", file=sys.stderr)
        raise SystemExit(1)
    remote = os.environ["MOCK_GH_REMOTE_URL"]
    full_name = os.environ.get(
        "MOCK_GH_FULL_NAME",
        f"{os.environ['GITHUB_OWNER']}/{os.environ['GITHUB_REPO']}",
    )
    visibility = os.environ.get("MOCK_GH_VISIBILITY", "public")
    can_push = os.environ.get("MOCK_GH_CAN_PUSH", "true")
    print(f"{full_name}\\t{remote}\\t{visibility}\\t{can_push}")
    raise SystemExit(0)

if args[:2] == ["repo", "create"]:
    expected_target = f"{os.environ['GITHUB_OWNER']}/{os.environ['GITHUB_REPO']}"
    expected_visibility = "--" + os.environ.get(
        "MOCK_GH_CREATE_VISIBILITY",
        os.environ.get("GITHUB_VISIBILITY", "public"),
    )
    if (
        len(args) != 6
        or args[2] != expected_target
        or args[3] != expected_visibility
        or args[4] != "--description"
        or not args[5]
    ):
        print(f"unexpected create invocation: {' '.join(args)}", file=sys.stderr)
        raise SystemExit(2)
    create_mode = os.environ.get("MOCK_GH_CREATE", "ok")
    if create_mode == "fail":
        print("simulated creation failure", file=sys.stderr)
        raise SystemExit(1)
    Path(os.environ["MOCK_GH_STATE"]).write_text("existing\\n", encoding="utf-8")
    if create_mode == "lost-response":
        print("simulated lost creation response", file=sys.stderr)
        raise SystemExit(1)
    print(f"https://github.test/{os.environ['GITHUB_OWNER']}/{os.environ['GITHUB_REPO']}")
    raise SystemExit(0)

print(f"unsupported mock gh invocation: {' '.join(args)}", file=sys.stderr)
raise SystemExit(2)
"""


class BootstrapGitHubTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        if REAL_GIT is None:
            self.skipTest("git is required")

        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp = Path(self.temp_dir.name)
        self.repo = self.temp / "repo with spaces"
        self.remote = self.temp / "target.git"
        self.mock_bin = self.temp / "bin"
        self.mock_bin.mkdir()
        self.home = self.temp / "home"
        self.home.mkdir()
        self.state = self.temp / "github-state"
        self.state.write_text("missing\n", encoding="utf-8")
        self.gh_log = self.temp / "gh.log"
        self.gh_log.write_text("", encoding="utf-8")

        shutil.copytree(
            ROOT,
            self.repo,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".DS_Store"),
        )

        mock_gh = self.mock_bin / "gh"
        mock_gh.write_text(MOCK_GH, encoding="utf-8")
        mock_gh.chmod(0o755)

        self.env = os.environ.copy()
        self.env.update(
            {
                "PATH": f"{self.mock_bin}{os.pathsep}{self.env['PATH']}",
                "HOME": str(self.home),
                "GITHUB_OWNER": "example",
                "GITHUB_REPO": "runtime",
                "GITHUB_HOST": "github.test",
                "GITHUB_VISIBILITY": "public",
                "MOCK_GH_AUTH": "ok",
                "MOCK_GH_SCOPES": "repo,workflow",
                "MOCK_GH_STATE": str(self.state),
                "MOCK_GH_LOG": str(self.gh_log),
                "MOCK_GH_REMOTE_URL": str(self.remote),
                "MOCK_GH_VISIBILITY": "public",
                "MOCK_GH_CAN_PUSH": "true",
                "GIT_AUTHOR_NAME": "Bootstrap Test",
                "GIT_AUTHOR_EMAIL": "bootstrap@example.invalid",
                "GIT_COMMITTER_NAME": "Bootstrap Test",
                "GIT_COMMITTER_EMAIL": "bootstrap@example.invalid",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
            }
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_command(
        self,
        *args: str,
        cwd: Path | None = None,
        check: bool = True,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            args,
            cwd=cwd or self.repo,
            env=env or self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(
                f"command failed ({result.returncode}): {' '.join(args)}\n{result.stdout}"
            )
        return result

    def git(self, *args: str, cwd: Path | None = None, check: bool = True):
        return self.run_command(REAL_GIT, *args, cwd=cwd, check=check)

    def init_local_commit(self) -> str:
        self.git("init", "-b", "main")
        self.git("add", "--all")
        self.git("commit", "-s", "-m", "initial")
        return self.git("rev-parse", "HEAD").stdout.strip()

    def init_bare_remote(self) -> None:
        self.git("init", "--bare", str(self.remote), cwd=self.temp)

    def set_existing_repository(self) -> None:
        self.state.write_text("existing\n", encoding="utf-8")

    def run_bootstrap(
        self, *arguments: str, env_updates: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        env = self.env.copy()
        if env_updates:
            env.update(env_updates)
        return self.run_command(
            "/bin/bash",
            str(BOOTSTRAP),
            *arguments,
            check=False,
            env=env,
        )

    def gh_calls(self) -> list[str]:
        return self.gh_log.read_text(encoding="utf-8").splitlines()

    def remote_main_exists(self) -> bool:
        result = self.git(
            "--git-dir",
            str(self.remote),
            "show-ref",
            "--verify",
            "--quiet",
            "refs/heads/main",
            cwd=self.temp,
            check=False,
        )
        return result.returncode == 0

    def remote_ref_exists(self, ref: str) -> bool:
        result = self.git(
            "--git-dir",
            str(self.remote),
            "show-ref",
            "--verify",
            "--quiet",
            ref,
            cwd=self.temp,
            check=False,
        )
        return result.returncode == 0

    def worktree_snapshot(self) -> tuple[tuple[str, int, str], ...]:
        snapshot: list[tuple[str, int, str]] = []
        for path in sorted(self.repo.rglob("*")):
            relative = path.relative_to(self.repo)
            if relative.parts and relative.parts[0] == ".git":
                continue
            if path.is_symlink():
                digest = f"symlink:{os.readlink(path)}"
            elif path.is_file():
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                continue
            snapshot.append((relative.as_posix(), path.stat().st_mode & 0o777, digest))
        return tuple(snapshot)

    def test_unauthenticated_fails_before_repository_lookup_or_creation(self) -> None:
        result = self.run_bootstrap(
            env_updates={"MOCK_GH_AUTH": "missing"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not authenticated", result.stdout)
        self.assertEqual(
            self.gh_calls(),
            ["auth status --hostname github.test"],
        )
        self.assertFalse((self.repo / ".git").exists())
        self.assertEqual(self.state.read_text(encoding="utf-8"), "missing\n")

    def test_missing_workflow_scope_fails_before_repository_creation(self) -> None:
        result = self.run_bootstrap(
            env_updates={"MOCK_GH_SCOPES": "repo"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required workflow permission", result.stdout)
        self.assertFalse(
            any("repos/example/runtime" in call for call in self.gh_calls())
        )
        self.assertFalse(any(call.startswith("repo create") for call in self.gh_calls()))
        self.assertFalse((self.repo / ".git").exists())

    def test_committed_workflow_still_requires_scope_when_worktree_copy_is_deleted(
        self,
    ) -> None:
        self.init_local_commit()
        workflow = self.repo / ".github" / "workflows" / "validate.yml"
        workflow.unlink()

        result = self.run_bootstrap(
            "--dry-run",
            env_updates={"MOCK_GH_SCOPES": "repo"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required workflow permission", result.stdout)
        self.assertFalse(
            any("repos/example/runtime" in call for call in self.gh_calls())
        )
        self.assertFalse(any(call.startswith("repo create") for call in self.gh_calls()))

    def test_api_auth_failure_stops_before_git_or_repository_creation(self) -> None:
        result = self.run_bootstrap(
            "--dry-run",
            env_updates={"MOCK_GH_API_AUTH": "fail"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("could not call the GitHub API", result.stdout)
        self.assertIn("Recovery:", result.stdout)
        self.assertFalse((self.repo / ".git").exists())
        self.assertFalse(any(call.startswith("repo create") for call in self.gh_calls()))
        self.assertFalse(
            any("repos/example/runtime" in call for call in self.gh_calls())
        )

    def test_missing_repository_creation_scope_fails_closed(self) -> None:
        result = self.run_bootstrap(
            "--dry-run",
            env_updates={"MOCK_GH_SCOPES": "workflow"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot be confirmed for public repository creation", result.stdout)
        self.assertFalse(any(call.startswith("repo create") for call in self.gh_calls()))
        self.assertFalse((self.repo / ".git").exists())

    def test_fresh_dry_run_plans_all_actions_without_mutation(self) -> None:
        before_snapshot = self.worktree_snapshot()

        result = self.run_bootstrap("--dry-run")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("would initialize", result.stdout)
        self.assertIn("would create public repository example/runtime", result.stdout)
        self.assertIn("would add remote origin", result.stdout)
        self.assertIn("would push the new local commit", result.stdout)
        self.assertFalse((self.repo / ".git").exists())
        self.assertEqual(self.worktree_snapshot(), before_snapshot)
        self.assertEqual(self.state.read_text(encoding="utf-8"), "missing\n")
        self.assertFalse(any(call.startswith("repo create") for call in self.gh_calls()))

    def test_partial_git_metadata_is_not_reinitialized(self) -> None:
        git_metadata = self.repo / ".git"
        git_metadata.write_text("not valid git metadata\n", encoding="utf-8")

        result = self.run_bootstrap("--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Git metadata exists", result.stdout)
        self.assertEqual(
            git_metadata.read_text(encoding="utf-8"),
            "not valid git metadata\n",
        )
        self.assertFalse(
            any("repos/example/runtime" in call for call in self.gh_calls())
        )

    def test_dry_run_reuses_equal_remote_and_commit_without_mutation(self) -> None:
        local_sha = self.init_local_commit()
        self.init_bare_remote()
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "-u", "origin", "main")
        self.set_existing_repository()
        before_status = self.git("status", "--porcelain=v1", "--untracked-files=all").stdout
        before_config = self.git("config", "--local", "--list").stdout
        before_head = self.git("rev-parse", "HEAD").stdout
        before_refs = self.git("for-each-ref", "--format=%(refname) %(objectname)").stdout
        before_remote_refs = self.git(
            "--git-dir",
            str(self.remote),
            "for-each-ref",
            "--format=%(refname) %(objectname)",
            cwd=self.temp,
        ).stdout
        before_snapshot = self.worktree_snapshot()

        result = self.run_bootstrap("--dry-run")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(f"Reusing local commit {local_sha}", result.stdout)
        self.assertIn("Reusing existing GitHub repository", result.stdout)
        self.assertIn("no push is needed", result.stdout)
        self.assertEqual(
            self.git("status", "--porcelain=v1", "--untracked-files=all").stdout,
            before_status,
        )
        self.assertEqual(self.git("config", "--local", "--list").stdout, before_config)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, before_head)
        self.assertEqual(
            self.git("for-each-ref", "--format=%(refname) %(objectname)").stdout,
            before_refs,
        )
        self.assertEqual(
            self.git(
                "--git-dir",
                str(self.remote),
                "for-each-ref",
                "--format=%(refname) %(objectname)",
                cwd=self.temp,
            ).stdout,
            before_remote_refs,
        )
        self.assertEqual(self.worktree_snapshot(), before_snapshot)
        self.assertFalse(any(call.startswith("repo create") for call in self.gh_calls()))

    def test_dry_run_plans_push_when_remote_branch_is_missing(self) -> None:
        local_sha = self.init_local_commit()
        self.init_bare_remote()
        self.git("remote", "add", "origin", str(self.remote))
        self.set_existing_repository()
        before_status = self.git("status", "--porcelain=v1", "--untracked-files=all").stdout
        before_config = self.git("config", "--local", "--list").stdout
        before_head = self.git("rev-parse", "HEAD").stdout
        before_refs = self.git("for-each-ref", "--format=%(refname) %(objectname)").stdout
        before_snapshot = self.worktree_snapshot()
        before_remote_refs = self.git(
            "--git-dir",
            str(self.remote),
            "for-each-ref",
            "--format=%(refname) %(objectname)",
            cwd=self.temp,
        ).stdout

        result = self.run_bootstrap("--dry-run")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(f"would push {local_sha} as new branch", result.stdout)
        self.assertFalse(self.remote_main_exists())
        self.assertEqual(
            self.git("status", "--porcelain=v1", "--untracked-files=all").stdout,
            before_status,
        )
        self.assertEqual(self.git("config", "--local", "--list").stdout, before_config)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, before_head)
        self.assertEqual(
            self.git("for-each-ref", "--format=%(refname) %(objectname)").stdout,
            before_refs,
        )
        self.assertEqual(self.worktree_snapshot(), before_snapshot)
        self.assertEqual(
            self.git(
                "--git-dir",
                str(self.remote),
                "for-each-ref",
                "--format=%(refname) %(objectname)",
                cwd=self.temp,
            ).stdout,
            before_remote_refs,
        )
        self.assertFalse(any(call.startswith("repo create") for call in self.gh_calls()))

    def test_dry_run_plans_remote_addition_without_adding_it(self) -> None:
        self.init_local_commit()
        self.init_bare_remote()
        self.set_existing_repository()

        result = self.run_bootstrap("--dry-run")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(f"would add remote origin as {self.remote}", result.stdout)
        self.assertEqual(self.git("remote").stdout, "")
        self.assertFalse(self.remote_main_exists())

    def test_existing_repository_without_push_permission_is_refused(self) -> None:
        self.init_local_commit()
        self.init_bare_remote()
        self.set_existing_repository()

        result = self.run_bootstrap(
            "--dry-run",
            env_updates={"MOCK_GH_CAN_PUSH": "false"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not report push permission", result.stdout)
        self.assertEqual(self.git("remote").stdout, "")
        self.assertFalse(self.remote_main_exists())

    def test_repository_rename_redirect_is_not_followed_implicitly(self) -> None:
        self.init_local_commit()
        self.init_bare_remote()
        self.set_existing_repository()

        result = self.run_bootstrap(
            "--dry-run",
            env_updates={"MOCK_GH_FULL_NAME": "different-owner/renamed-runtime"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("canonical repository different-owner/renamed-runtime", result.stdout)
        self.assertEqual(self.git("remote").stdout, "")
        self.assertFalse(self.remote_main_exists())

    def test_local_push_url_rewrite_is_refused_before_remote_add(self) -> None:
        self.init_local_commit()
        self.init_bare_remote()
        wrong_remote = self.temp / "rewrite-target.git"
        self.git("init", "--bare", str(wrong_remote), cwd=self.temp)
        self.git(
            "config",
            "--local",
            f"url.{wrong_remote}.pushInsteadOf",
            str(self.remote),
        )
        self.set_existing_repository()

        result = self.run_bootstrap("--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pushInsteadOf configuration requires review", result.stdout)
        self.assertEqual(self.git("remote").stdout, "")
        self.assertFalse(self.remote_main_exists())

    def test_mismatched_origin_is_refused_without_overwrite(self) -> None:
        self.init_local_commit()
        self.init_bare_remote()
        wrong_remote = self.temp / "wrong.git"
        self.git("init", "--bare", str(wrong_remote), cwd=self.temp)
        self.git("remote", "add", "origin", str(wrong_remote))
        self.set_existing_repository()

        result = self.run_bootstrap("--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite it or push elsewhere", result.stdout)
        self.assertEqual(self.git("remote", "get-url", "origin").stdout.strip(), str(wrong_remote))
        self.assertFalse(self.remote_main_exists())

    def test_mismatched_pushurl_is_refused(self) -> None:
        self.init_local_commit()
        self.init_bare_remote()
        wrong_remote = self.temp / "wrong-push.git"
        self.git("init", "--bare", str(wrong_remote), cwd=self.temp)
        self.git("remote", "add", "origin", str(self.remote))
        self.git("remote", "set-url", "--add", "--push", "origin", str(wrong_remote))
        self.set_existing_repository()

        result = self.run_bootstrap("--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(wrong_remote), result.stdout)
        self.assertFalse(self.remote_main_exists())

    def test_plaintext_http_origin_is_refused(self) -> None:
        self.init_local_commit()
        insecure = "http://github.test/example/runtime.git"
        expected = "https://github.test/example/runtime.git"
        self.git("remote", "add", "origin", insecure)
        self.set_existing_repository()

        result = self.run_bootstrap(
            "--dry-run",
            env_updates={"MOCK_GH_REMOTE_URL": expected},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(insecure, result.stdout)
        self.assertIn("refusing to overwrite it or push elsewhere", result.stdout)
        self.assertEqual(self.git("remote", "get-url", "origin").stdout.strip(), insecure)

    def test_dirty_existing_worktree_is_refused_and_preserved(self) -> None:
        local_sha = self.init_local_commit()
        self.init_bare_remote()
        self.git("remote", "add", "origin", str(self.remote))
        self.set_existing_repository()
        readme = self.repo / "README.md"
        changed_readme = readme.read_text(encoding="utf-8") + "\nlocal work\n"
        readme.write_text(changed_readme, encoding="utf-8")
        untracked = self.repo / "local-notes.txt"
        untracked.write_text("preserve me\n", encoding="utf-8")
        status_before = self.git("status", "--porcelain=v1", "--untracked-files=all").stdout

        result = self.run_bootstrap()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("uncommitted changes", result.stdout)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), local_sha)
        self.assertEqual(readme.read_text(encoding="utf-8"), changed_readme)
        self.assertEqual(untracked.read_text(encoding="utf-8"), "preserve me\n")
        self.assertEqual(
            self.git("status", "--porcelain=v1", "--untracked-files=all").stdout,
            status_before,
        )
        self.assertFalse(self.remote_main_exists())

    def test_corrupt_index_is_not_treated_as_a_clean_worktree(self) -> None:
        self.init_local_commit()
        self.init_bare_remote()
        self.set_existing_repository()
        index = self.repo / ".git" / "index"
        index.write_bytes(b"broken index\n")

        result = self.run_bootstrap()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Could not inspect the local worktree and index", result.stdout)
        self.assertEqual(index.read_bytes(), b"broken index\n")
        self.assertFalse(
            any("repos/example/runtime" in call for call in self.gh_calls())
        )
        self.assertFalse(self.remote_main_exists())

    def test_intent_to_add_index_entry_is_refused_and_preserved(self) -> None:
        self.git("init", "-b", "main")
        self.git("add", "-N", "README.md")
        index_before = self.git("ls-files", "--stage").stdout

        result = self.run_bootstrap("--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("index already contains entries", result.stdout)
        self.assertEqual(self.git("ls-files", "--stage").stdout, index_before)
        self.assertFalse(
            any("repos/example/runtime" in call for call in self.gh_calls())
        )

    def test_dirty_validator_is_never_executed_before_refusal(self) -> None:
        self.init_local_commit()
        readme = self.repo / "README.md"
        readme_before = readme.read_bytes()
        validator = self.repo / "scripts" / "check-repo.py"
        validator.write_text(
            "from pathlib import Path\nPath('README.md').unlink()\n",
            encoding="utf-8",
        )

        result = self.run_bootstrap()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("uncommitted changes", result.stdout)
        self.assertTrue(readme.exists())
        self.assertEqual(readme.read_bytes(), readme_before)
        self.assertFalse(
            any("repos/example/runtime" in call for call in self.gh_calls())
        )

    def test_active_commit_hook_is_neither_bypassed_nor_executed(
        self,
    ) -> None:
        self.git("init", "-b", "main")
        self.init_bare_remote()
        readme = self.repo / "README.md"
        readme_before = readme.read_bytes()
        hook_marker = self.temp / "commit-hook-ran"
        hook = self.repo / ".git" / "hooks" / "pre-commit"
        hook.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                printf '\\nhook mutation\\n' >> README.md
                git add README.md
                touch {shlex.quote(str(hook_marker))}
                """
            ),
            encoding="utf-8",
        )
        hook.chmod(0o755)

        result = self.run_bootstrap()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Active Git hook", result.stdout)
        self.assertIn("will not bypass it", result.stdout)
        self.assertFalse(hook_marker.exists())
        self.assertEqual(readme.read_bytes(), readme_before)
        self.assertNotEqual(
            self.git("rev-parse", "--verify", "HEAD", check=False).returncode,
            0,
        )
        self.assertFalse(
            any("repos/example/runtime" in call for call in self.gh_calls())
        )
        self.assertFalse(self.remote_main_exists())

    def test_remote_ahead_is_rejected_without_force_or_ref_changes(self) -> None:
        local_sha = self.init_local_commit()
        self.init_bare_remote()
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "-u", "origin", "main")
        self.set_existing_repository()

        other = self.temp / "other checkout"
        self.git("clone", "--branch", "main", str(self.remote), str(other), cwd=self.temp)
        (other / "remote-only.txt").write_text("remote advance\n", encoding="utf-8")
        self.git("add", "remote-only.txt", cwd=other)
        self.git("commit", "-s", "-m", "remote advance", cwd=other)
        self.git("push", "origin", "main", cwd=other)
        remote_sha = self.git(
            "--git-dir",
            str(self.remote),
            "rev-parse",
            "refs/heads/main",
            cwd=self.temp,
        ).stdout.strip()

        result = self.run_bootstrap("--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non-destructive push preflight was rejected", result.stdout)
        self.assertIn("reconcile without force-pushing", result.stdout)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), local_sha)
        self.assertEqual(
            self.git(
                "--git-dir",
                str(self.remote),
                "rev-parse",
                "refs/heads/main",
                cwd=self.temp,
            ).stdout.strip(),
            remote_sha,
        )

    def test_existing_upstream_is_not_overwritten(self) -> None:
        self.init_local_commit()
        self.init_bare_remote()
        other = self.temp / "other-upstream.git"
        self.git("init", "--bare", str(other), cwd=self.temp)
        self.git("remote", "add", "origin", str(self.remote))
        self.git("remote", "add", "other", str(other))
        self.git("config", "branch.main.remote", "other")
        self.git("config", "branch.main.merge", "refs/heads/different")
        self.set_existing_repository()
        config_before = self.git("config", "--local", "--list").stdout

        result = self.run_bootstrap("--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite it", result.stdout)
        self.assertEqual(self.git("config", "--local", "--list").stdout, config_before)
        self.assertFalse(self.remote_main_exists())

    def test_push_follow_tags_configuration_cannot_expand_scope(self) -> None:
        local_sha = self.init_local_commit()
        self.git("tag", "-a", "v1-test", "-m", "must remain local")
        self.git("config", "push.followTags", "true")
        self.init_bare_remote()
        self.git("remote", "add", "origin", str(self.remote))
        self.set_existing_repository()

        result = self.run_bootstrap()

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(self.remote_main_exists())
        self.assertFalse(self.remote_ref_exists("refs/tags/v1-test"))
        self.assertEqual(
            self.git(
                "--git-dir",
                str(self.remote),
                "rev-parse",
                "refs/heads/main",
                cwd=self.temp,
            ).stdout.strip(),
            local_sha,
        )

    def test_active_pre_push_hook_requires_manual_push_without_running(self) -> None:
        self.init_local_commit()
        self.init_bare_remote()
        self.git("remote", "add", "origin", str(self.remote))
        self.set_existing_repository()
        marker = self.temp / "pre-push-hook-ran"
        hook = self.repo / ".git" / "hooks" / "pre-push"
        hook.write_text(
            f"#!/bin/sh\ntouch {shlex.quote(str(marker))}\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)
        config_before = self.git("config", "--local", "--list").stdout

        result = self.run_bootstrap()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Active Git hook", result.stdout)
        self.assertIn("Run the push manually", result.stdout)
        self.assertFalse(marker.exists())
        self.assertFalse(self.remote_main_exists())
        self.assertEqual(self.git("config", "--local", "--list").stdout, config_before)

    def test_lost_create_response_requeries_and_continues(self) -> None:
        self.init_bare_remote()

        result = self.run_bootstrap(
            env_updates={
                "MOCK_GH_CREATE": "lost-response",
                "TMPDIR": str(self.repo),
            },
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("creation returned an error", result.stdout)
        self.assertIn("reusing it", result.stdout)
        self.assertTrue(self.remote_main_exists())
        self.assertEqual(
            sum(call.startswith("repo create") for call in self.gh_calls()),
            1,
        )
        self.assertFalse(
            any(
                "governed-agent-bootstrap." in path
                for path in self.git("ls-files").stdout.splitlines()
            )
        )
        self.assertEqual(
            list(self.repo.glob("governed-agent-bootstrap.*")),
            [],
        )

    def test_lost_create_response_with_wrong_visibility_refuses_push(self) -> None:
        self.init_bare_remote()

        result = self.run_bootstrap(
            env_updates={
                "MOCK_GH_CREATE": "lost-response",
                "MOCK_GH_VISIBILITY": "private",
            },
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private after creation/readback", result.stdout)
        self.assertEqual(self.git("remote").stdout, "")
        self.assertFalse(self.remote_main_exists())

    def test_definitive_create_failure_preserves_local_commit_for_rerun(self) -> None:
        self.init_bare_remote()

        result = self.run_bootstrap(
            env_updates={"MOCK_GH_CREATE": "fail"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("GitHub repository creation failed", result.stdout)
        self.assertIn("Recovery:", result.stdout)
        self.assertEqual(self.state.read_text(encoding="utf-8"), "missing\n")
        self.assertTrue((self.repo / ".git").exists())
        self.assertEqual(self.git("rev-list", "--count", "HEAD").stdout.strip(), "1")
        self.assertEqual(self.git("remote").stdout, "")
        self.assertFalse(self.remote_main_exists())

    def test_failed_push_resumes_without_recreating_repository_or_commit(self) -> None:
        self.init_bare_remote()
        hooks = self.remote / "hooks"
        reject_marker = self.remote / "reject-next-push"
        reject_marker.write_text("reject\n", encoding="utf-8")
        hook = hooks / "pre-receive"
        hook.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                if [ -f {str(reject_marker)!r} ]; then
                  rm -f {str(reject_marker)!r}
                  echo "simulated one-time push rejection" >&2
                  exit 1
                fi
                exit 0
                """
            ),
            encoding="utf-8",
        )
        hook.chmod(0o755)

        first = self.run_bootstrap()

        self.assertNotEqual(first.returncode, 0)
        self.assertIn("Push failed after preflight", first.stdout)
        self.assertIn("will reuse", first.stdout)
        first_sha = self.git("rev-parse", "HEAD").stdout.strip()
        first_commit_count = self.git("rev-list", "--count", "HEAD").stdout.strip()
        self.assertEqual(self.state.read_text(encoding="utf-8"), "existing\n")
        self.assertEqual(self.git("remote", "get-url", "origin").stdout.strip(), str(self.remote))
        self.assertFalse(self.remote_main_exists())
        self.assertEqual(
            sum(call.startswith("repo create") for call in self.gh_calls()),
            1,
        )

        second = self.run_bootstrap()

        self.assertEqual(second.returncode, 0, second.stdout)
        self.assertIn("Reusing existing GitHub repository", second.stdout)
        self.assertIn("Reusing remote origin", second.stdout)
        self.assertIn(f"Reusing local commit {first_sha}", second.stdout)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), first_sha)
        self.assertEqual(
            self.git("rev-list", "--count", "HEAD").stdout.strip(),
            first_commit_count,
        )
        self.assertTrue(self.remote_main_exists())
        self.assertEqual(
            self.git("--git-dir", str(self.remote), "rev-parse", "refs/heads/main", cwd=self.temp).stdout.strip(),
            first_sha,
        )
        self.assertEqual(
            sum(call.startswith("repo create") for call in self.gh_calls()),
            1,
        )


if __name__ == "__main__":
    unittest.main()
