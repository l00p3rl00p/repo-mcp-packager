"""
Test: Knowledge Server Template — DU-V3.3.8-03

Verifies ForgeEngine._get_knowledge_server_template() produces a fully
functional Librarian-capable MCP server:
  - add_resource: URL, file, and folder ingestion
  - search_docs: snippet extraction with stack-scoped isolation
  - list_docs: filtered listing
  - read_doc: full document retrieval
  - .index.json persistence across server restarts
  - Stack isolation (no cross-contamination)
  - MCP protocol compliance (notification guard, text content wrapper)

All tests use real subprocess execution — no fake data, no placeholders.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_template(tmpdir: Path) -> str:
    """Generate a knowledge server template rooted at tmpdir."""
    forge_dir = Path(__file__).parent.parent / "forge"
    sys.path.insert(0, str(forge_dir))
    from forge_engine import ForgeEngine  # noqa: PLC0415
    fe = ForgeEngine(Path("/tmp/test-suite"))
    return fe._get_knowledge_server_template(tmpdir / "mcp_server")


def _start_server(server_file: Path, cwd: Path) -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, str(server_file)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=str(cwd),
    )
    return proc


def _rpc(proc: subprocess.Popen, msg: dict) -> dict:
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    return json.loads(line)


def _tool_call(proc: subprocess.Popen, msg_id: int, name: str, arguments: dict) -> dict:
    resp = _rpc(proc, {
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    })
    assert "result" in resp, f"Expected result, got: {resp}"
    content = resp["result"]["content"]
    assert len(content) >= 1 and content[0]["type"] == "text", f"Bad content shape: {content}"
    return json.loads(content[0]["text"])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def server_env():
    """Spin up a fresh knowledge server in a temp directory. Yields (proc, tmpdir)."""
    with tempfile.TemporaryDirectory(prefix="ks_test_") as td:
        tmpdir = Path(td)
        server_file = tmpdir / "mcp_server.py"
        server_file.write_text(_get_template(tmpdir))
        proc = _start_server(server_file, tmpdir)
        # Handshake
        _rpc(proc, {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
        yield proc, tmpdir
        proc.stdin.close()
        proc.wait(timeout=5)


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

class TestMCPProtocolCompliance:
    def test_initialize_response(self, server_env):
        """initialize must return protocolVersion and capabilities."""
        proc, _ = server_env
        resp = _rpc(proc, {"jsonrpc": "2.0", "id": 99, "method": "initialize", "params": {}})
        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert "tools" in resp["result"]["capabilities"]

    def test_notification_guard(self, server_env):
        """Notifications (no id) must produce NO response — Rule 1."""
        proc, _ = server_env
        # Send notification then a real request; first response must be for id=42
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.flush()
        resp = _rpc(proc, {"jsonrpc": "2.0", "id": 42, "method": "tools/list", "params": {}})
        assert resp.get("id") == 42, "Notification produced a response (Rule 1 violation)"

    def test_tools_list_returns_four_tools(self, server_env):
        """tools/list must expose add_resource, search_docs, list_docs, read_doc."""
        proc, _ = server_env
        resp = _rpc(proc, {"jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {}})
        names = {t["name"] for t in resp["result"]["tools"]}
        assert names == {"add_resource", "search_docs", "list_docs", "read_doc"}

    def test_tool_result_is_content_block(self, server_env):
        """tools/call results must use content block format — Rule 2."""
        proc, tmpdir = server_env
        f = tmpdir / "probe.md"
        f.write_text("probe content")
        resp = _rpc(proc, {
            "jsonrpc": "2.0", "id": 11, "method": "tools/call",
            "params": {"name": "add_resource", "arguments": {"url": str(f)}},
        })
        content = resp["result"]["content"]
        assert content[0]["type"] == "text", "Tool result not in content block format (Rule 2 violation)"


# ---------------------------------------------------------------------------
# Resource ingestion
# ---------------------------------------------------------------------------

class TestResourceIngestion:
    def test_add_resource_local_file(self, server_env):
        """add_resource must ingest a local .md file."""
        proc, tmpdir = server_env
        f = tmpdir / "doc.md"
        f.write_text("# Test Document\nContent about Python programming.")
        result = _tool_call(proc, 20, "add_resource", {"url": str(f), "stack": "test"})
        assert result["total_indexed"] >= 1
        assert len(result["added"]) == 1
        assert result["added"][0]["title"] == "doc.md"
        assert result["errors"] == []

    def test_add_resource_local_folder(self, server_env):
        """add_resource must ingest all supported files from a folder."""
        proc, tmpdir = server_env
        folder = tmpdir / "corpus"
        folder.mkdir()
        (folder / "alpha.md").write_text("Alpha document: machine learning concepts.")
        (folder / "beta.md").write_text("Beta document: deep neural networks.")
        (folder / "ignored.xyz").write_text("This extension should be skipped.")
        result = _tool_call(proc, 21, "add_resource", {"url": str(folder), "stack": "corpus"})
        assert len(result["added"]) == 2, f"Expected 2 .md files ingested, got: {result['added']}"
        assert result["errors"] == []

    def test_add_resource_missing_path_returns_error(self, server_env):
        """add_resource on a non-existent path must return a JSON-RPC error."""
        proc, _ = server_env
        resp = _rpc(proc, {
            "jsonrpc": "2.0", "id": 22, "method": "tools/call",
            "params": {"name": "add_resource", "arguments": {"url": "/nonexistent/path/file.md"}},
        })
        assert "error" in resp, "Expected error for missing path"

    def test_add_resource_missing_url_param_returns_error(self, server_env):
        """add_resource without url param must return a JSON-RPC error."""
        proc, _ = server_env
        resp = _rpc(proc, {
            "jsonrpc": "2.0", "id": 23, "method": "tools/call",
            "params": {"name": "add_resource", "arguments": {}},
        })
        assert "error" in resp, "Expected error for missing url parameter"


# ---------------------------------------------------------------------------
# Search with snippets
# ---------------------------------------------------------------------------

class TestSearchDocs:
    def test_search_returns_snippets(self, server_env):
        """search_docs must return matches with snippet context."""
        proc, tmpdir = server_env
        f = tmpdir / "snippets_doc.md"
        f.write_text("Introduction to transformers and attention mechanisms in deep learning.")
        _tool_call(proc, 30, "add_resource", {"url": str(f), "stack": "ml"})

        result = _tool_call(proc, 31, "search_docs", {"query": "transformers", "stack": "ml"})
        assert result["count"] >= 1
        match = result["matches"][0]
        assert "snippet" in match, "Match must contain a snippet"
        assert "transformers" in match["snippet"].lower(), "Snippet must contain query term"
        assert "source" in match
        assert "title" in match

    def test_search_no_results_for_unknown_query(self, server_env):
        """search_docs for a term not in any document must return empty matches."""
        proc, tmpdir = server_env
        f = tmpdir / "known.md"
        f.write_text("This document only contains banana content.")
        _tool_call(proc, 32, "add_resource", {"url": str(f), "stack": "fruit"})

        result = _tool_call(proc, 33, "search_docs", {"query": "xyzzy_nonexistent_term_9817"})
        assert result["count"] == 0

    def test_search_missing_query_returns_error(self, server_env):
        """search_docs without query must return a JSON-RPC error."""
        proc, _ = server_env
        resp = _rpc(proc, {
            "jsonrpc": "2.0", "id": 34, "method": "tools/call",
            "params": {"name": "search_docs", "arguments": {}},
        })
        assert "error" in resp


# ---------------------------------------------------------------------------
# Stack isolation
# ---------------------------------------------------------------------------

class TestStackIsolation:
    def test_stack_a_does_not_return_stack_b_results(self, server_env):
        """Searching Stack-A must NOT return documents from Stack-B."""
        proc, tmpdir = server_env
        (tmpdir / "stack_a.md").write_text("Unique keyword: zephyroxide_alpha only in stack-a.")
        (tmpdir / "stack_b.md").write_text("Unique keyword: zephyroxide_beta only in stack-b.")
        _tool_call(proc, 40, "add_resource", {"url": str(tmpdir / "stack_a.md"), "stack": "stack-a"})
        _tool_call(proc, 41, "add_resource", {"url": str(tmpdir / "stack_b.md"), "stack": "stack-b"})

        # Search stack-a for stack-b keyword
        result = _tool_call(proc, 42, "search_docs", {"query": "zephyroxide_beta", "stack": "stack-a"})
        assert result["count"] == 0, f"Cross-contamination: stack-b content visible in stack-a ({result})"

        # Search stack-b for stack-a keyword
        result = _tool_call(proc, 43, "search_docs", {"query": "zephyroxide_alpha", "stack": "stack-b"})
        assert result["count"] == 0, f"Cross-contamination: stack-a content visible in stack-b ({result})"

    def test_unscoped_search_spans_all_stacks(self, server_env):
        """search_docs without stack filter must search across all stacks."""
        proc, tmpdir = server_env
        (tmpdir / "doc1.md").write_text("Shared term: globalterm found in stack-x.")
        (tmpdir / "doc2.md").write_text("Shared term: globalterm found in stack-y.")
        _tool_call(proc, 44, "add_resource", {"url": str(tmpdir / "doc1.md"), "stack": "stack-x"})
        _tool_call(proc, 45, "add_resource", {"url": str(tmpdir / "doc2.md"), "stack": "stack-y"})

        result = _tool_call(proc, 46, "search_docs", {"query": "globalterm"})
        assert result["count"] == 2, f"Expected 2 cross-stack matches, got {result['count']}"

    def test_list_docs_stack_filter(self, server_env):
        """list_docs(stack=x) must only return docs from that stack."""
        proc, tmpdir = server_env
        (tmpdir / "p.md").write_text("Python doc.")
        (tmpdir / "r.md").write_text("Rust doc.")
        _tool_call(proc, 47, "add_resource", {"url": str(tmpdir / "p.md"), "stack": "python"})
        _tool_call(proc, 48, "add_resource", {"url": str(tmpdir / "r.md"), "stack": "rust"})

        result = _tool_call(proc, 49, "list_docs", {"stack": "python"})
        assert result["total"] == 1
        assert result["docs"][0]["title"] == "p.md"


# ---------------------------------------------------------------------------
# Document operations
# ---------------------------------------------------------------------------

class TestDocumentOperations:
    def test_list_docs_no_filter_returns_all(self, server_env):
        """list_docs without filter returns all indexed documents."""
        proc, tmpdir = server_env
        for i in range(3):
            f = tmpdir / f"doc{i}.md"
            f.write_text(f"Document {i} content.")
            _tool_call(proc, 50 + i, "add_resource", {"url": str(f), "stack": f"s{i}"})

        result = _tool_call(proc, 53, "list_docs", {})
        assert result["total"] == 3
        for doc in result["docs"]:
            assert "id" in doc
            assert "source" in doc
            assert "title" in doc
            assert "stack" in doc
            assert "size" in doc

    def test_read_doc_by_id(self, server_env):
        """read_doc must retrieve the full content of a document by id."""
        proc, tmpdir = server_env
        f = tmpdir / "readable.md"
        f.write_text("Full content: the quick brown fox jumps over the lazy dog.")
        add_result = _tool_call(proc, 60, "add_resource", {"url": str(f), "stack": "read-test"})
        doc_id = add_result["added"][0]["id"]

        result = _tool_call(proc, 61, "read_doc", {"path": doc_id})
        assert result["id"] == doc_id
        assert "quick brown fox" in result["content"]
        assert result["stack"] == "read-test"

    def test_read_doc_by_source_path(self, server_env):
        """read_doc must also look up by source path (not just id)."""
        proc, tmpdir = server_env
        f = tmpdir / "by_path.md"
        f.write_text("Lookup by source path content.")
        _tool_call(proc, 62, "add_resource", {"url": str(f), "stack": "path-test"})

        result = _tool_call(proc, 63, "read_doc", {"path": str(f)})
        assert "Lookup by source path" in result["content"]

    def test_read_doc_not_found_returns_error(self, server_env):
        """read_doc for unknown id must return a JSON-RPC error."""
        proc, _ = server_env
        resp = _rpc(proc, {
            "jsonrpc": "2.0", "id": 64, "method": "tools/call",
            "params": {"name": "read_doc", "arguments": {"path": "nonexistent_id_abc123"}},
        })
        assert "error" in resp


# ---------------------------------------------------------------------------
# Persistence across restarts
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_index_json_written_after_add_resource(self, server_env):
        """After add_resource, .index.json must exist on disk."""
        proc, tmpdir = server_env
        f = tmpdir / "persist.md"
        f.write_text("Persistence test document.")
        _tool_call(proc, 70, "add_resource", {"url": str(f), "stack": "persist"})

        index_file = tmpdir / ".index.json"
        assert index_file.exists(), ".index.json not written after add_resource"
        data = json.loads(index_file.read_text())
        assert len(data) >= 1

    def test_index_survives_server_restart(self):
        """Index loaded by a new server process must contain previously added docs."""
        with tempfile.TemporaryDirectory(prefix="ks_restart_") as td:
            tmpdir = Path(td)
            server_file = tmpdir / "mcp_server.py"
            server_file.write_text(_get_template(tmpdir))

            # Process 1: add a document and shut down
            proc1 = _start_server(server_file, tmpdir)
            _rpc(proc1, {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
            f = tmpdir / "restart_doc.md"
            f.write_text("Restart persistence: unique content xr9q7.")
            _tool_call(proc1, 80, "add_resource", {"url": str(f), "stack": "restart"})
            proc1.stdin.close()
            proc1.wait(timeout=5)

            assert (tmpdir / ".index.json").exists()

            # Process 2: new server instance — must see prior data
            proc2 = _start_server(server_file, tmpdir)
            _rpc(proc2, {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})

            list_result = _tool_call(proc2, 81, "list_docs", {})
            assert list_result["total"] >= 1, "No docs after restart — persistence failed"

            search_result = _tool_call(proc2, 82, "search_docs", {"query": "xr9q7"})
            assert search_result["count"] >= 1, "Search failed after restart — index not loaded"

            proc2.stdin.close()
            proc2.wait(timeout=5)

    def test_index_json_is_valid_json_after_multiple_adds(self, server_env):
        """After multiple add_resource calls .index.json must be valid JSON."""
        proc, tmpdir = server_env
        for i in range(5):
            f = tmpdir / f"multi_{i}.md"
            f.write_text(f"Multi-add document {i}.")
            _tool_call(proc, 90 + i, "add_resource", {"url": str(f), "stack": "multi"})

        index_file = tmpdir / ".index.json"
        raw = index_file.read_text()
        data = json.loads(raw)  # Must not raise
        assert len(data) == 5
