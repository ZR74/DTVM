import gzip
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "tx_replay_prepare.py"

TX_HASH = "0x" + ("9" * 64)
SENDER = "0x" + ("aa" * 20)
TOP = "0x" + ("11" * 20)
CALLEE = "0x" + ("22" * 20)
BALANCE_TARGET = "0x" + ("33" * 20)
COINBASE = "0x" + ("44" * 20)

TOP_SLOT = "0x" + ("0" * 63) + "1"
CALLEE_SLOT = "0x" + ("0" * 63) + "2"
ACCESS_KEY = "0x" + ("0" * 63) + "2"

TOP_VALUE = "0x" + ("0" * 61) + "abc"
CALLEE_VALUE = "0x" + ("0" * 61) + "def"
BALANCE_VALUE = "0x" + ("0" * 62) + "99"
BLOCKHASH_VALUE = "0x" + ("fe" * 32)


def run_tool(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row))
            handle.write("\n")


def make_proof(address: str, *, balance: str, nonce: str, code_hash: str, storage: dict[str, str]) -> dict:
    return {
        "address": address,
        "balance": balance,
        "nonce": nonce,
        "codeHash": code_hash,
        "storageProof": [{"key": key, "value": value, "proof": []} for key, value in storage.items()],
    }


class RpcFixtureServer:
    def __init__(self, fixture):
        self.fixture = fixture
        self.httpd: HTTPServer | None = None
        self.thread: threading.Thread | None = None

    def __enter__(self) -> "RpcFixtureServer":
        fixture = self.fixture

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                request = json.loads(self.rfile.read(length).decode("utf-8"))
                result = fixture(request["method"], request.get("params", []))
                payload = json.dumps(
                    {"jsonrpc": "2.0", "id": request.get("id", 1), "result": result}
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        assert self.httpd is not None
        self.httpd.shutdown()
        self.httpd.server_close()
        assert self.thread is not None
        self.thread.join(timeout=5)

    @property
    def url(self) -> str:
        assert self.httpd is not None
        host, port = self.httpd.server_address
        return f"http://{host}:{port}"


def test_prepare_one_builds_state_and_replay_command(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.json.gz"
    trace_payload = {
        "trace": {
            "structLogs": [
                {"pc": 0, "op": "SLOAD", "gas": 1, "gasCost": 1, "depth": 1, "stack": [TOP_SLOT], "memory": [], "returnData": "0x"},
                {"pc": 1, "op": "POP", "gas": 1, "gasCost": 1, "depth": 1, "stack": [TOP_VALUE], "memory": [], "returnData": "0x"},
                {"pc": 2, "op": "BALANCE", "gas": 1, "gasCost": 1, "depth": 1, "stack": [BALANCE_TARGET], "memory": [], "returnData": "0x"},
                {"pc": 3, "op": "POP", "gas": 1, "gasCost": 1, "depth": 1, "stack": [BALANCE_VALUE], "memory": [], "returnData": "0x"},
                {"pc": 4, "op": "CALL", "gas": 1, "gasCost": 1, "depth": 1, "stack": ["0x0", "0x0", "0x0", "0x0", "0x0", CALLEE, "0xff"], "memory": [], "returnData": "0x"},
                {"pc": 5, "op": "SLOAD", "gas": 1, "gasCost": 1, "depth": 2, "stack": [CALLEE_SLOT], "memory": [], "returnData": "0x"},
                {"pc": 6, "op": "STOP", "gas": 1, "gasCost": 0, "depth": 2, "stack": [CALLEE_VALUE], "memory": [], "returnData": "0x"},
                {"pc": 7, "op": "BLOCKHASH", "gas": 1, "gasCost": 1, "depth": 1, "stack": ["0x10"], "memory": [], "returnData": "0x"},
                {"pc": 8, "op": "POP", "gas": 1, "gasCost": 1, "depth": 1, "stack": [BLOCKHASH_VALUE], "memory": [], "returnData": "0x"},
                {"pc": 9, "op": "STOP", "gas": 1, "gasCost": 0, "depth": 1, "stack": [], "memory": [], "returnData": "0x"},
            ]
        }
    }
    with gzip.open(trace_path, "wt", encoding="utf-8") as handle:
        json.dump(trace_payload, handle)

    rows = [
        {
            "dataset": "erc20_transfer",
            "tx_hash": TX_HASH,
            "trace_path": str(trace_path),
            "receipt_block_number": "0x64",
        }
    ]
    input_path = tmp_path / "rows.jsonl"
    write_jsonl(input_path, rows)

    proofs = {
        TOP: make_proof(
            TOP,
            balance="0x10",
            nonce="0x1",
            code_hash="0x" + ("ab" * 32),
            storage={TOP_SLOT: "0x" + ("de" * 32)},
        ),
        CALLEE: make_proof(
            CALLEE,
            balance="0x20",
            nonce="0x2",
            code_hash="0x" + ("cd" * 32),
            storage={CALLEE_SLOT: "0x" + ("ef" * 32)},
        ),
        BALANCE_TARGET: make_proof(
            BALANCE_TARGET,
            balance="0x1",
            nonce="0x0",
            code_hash="0x" + ("01" * 32),
            storage={},
        ),
        SENDER: make_proof(
            SENDER,
            balance="0x1",
            nonce="0x1",
            code_hash="0x" + ("02" * 32),
            storage={},
        ),
        COINBASE: make_proof(
            COINBASE,
            balance="0x0",
            nonce="0x0",
            code_hash="0x" + ("03" * 32),
            storage={},
        ),
    }
    codes = {
        TOP: "0x6001600055",
        CALLEE: "0x6002600055",
    }

    def fixture(method: str, params: list) -> dict:
        if method == "eth_getTransactionByHash":
            assert params == [TX_HASH]
            return {
                "hash": TX_HASH,
                "from": SENDER,
                "to": TOP,
                "input": "0xaabbccdd",
                "gas": "0x5208",
                "value": "0x0",
                "nonce": "0x7",
                "gasPrice": "0x5",
                "blockNumber": "0x64",
                "accessList": [{"address": CALLEE, "storageKeys": [ACCESS_KEY]}],
            }
        if method == "eth_getBlockByNumber":
            assert params == ["0x64", False]
            return {
                "number": "0x64",
                "timestamp": "0x1234",
                "miner": COINBASE,
                "mixHash": "0x" + ("55" * 32),
                "gasLimit": "0x1c9c380",
                "baseFeePerGas": "0x10",
            }
        if method == "eth_getProof":
            address = params[0]
            assert address in proofs
            return proofs[address]
        if method == "eth_getCode":
            address = params[0]
            return codes.get(address, "0x")
        raise AssertionError(f"unexpected RPC method: {method}")

    output_root = tmp_path / "out"
    cache_dir = tmp_path / "cache"
    with RpcFixtureServer(fixture) as server:
        payload = run_tool(
            "prepare-one",
            "--jsonl",
            str(input_path),
            "--tx-hash",
            TX_HASH,
            "--rpc-url",
            server.url,
            "--output-root",
            str(output_root),
            "--cache-dir",
            str(cache_dir),
            "--trace-search-root",
            str(tmp_path),
        )

    assert payload["ready"] is True
    state_path = Path(payload["state_path"])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["block_hash"] == BLOCKHASH_VALUE
    assert state["accounts"][TOP]["storage"][TOP_SLOT] == TOP_VALUE
    assert state["accounts"][CALLEE]["storage"][CALLEE_SLOT] == CALLEE_VALUE
    assert state["accounts"][BALANCE_TARGET]["balance"] == BALANCE_VALUE
    assert state["accounts"][SENDER]["nonce"] == 7
    assert state["access_list"] == [{"address": CALLEE, "storage_keys": [ACCESS_KEY]}]

    bytecode_path = Path(payload["bytecode_path"])
    assert bytecode_path.read_text(encoding="utf-8").strip() == "6001600055"

    command = payload["command"]
    assert "--load-state" in command
    assert str(state_path) in command
    assert "--contract-address" in command
    assert TOP in command
