"""FASE 10 integracion Meta Business: FileTokenStorage."""
import json
import os

from mcp_client.storage import FileTokenStorage


def test_has_credentials_false_when_empty(tmp_path):
    st = FileTokenStorage("meta_ads", base_dir=str(tmp_path))
    assert st.has_credentials() is False


def test_has_credentials_true_with_refresh_token(tmp_path):
    (tmp_path / "meta_ads_tokens.json").write_text(json.dumps({"refresh_token": "rt-abc"}))
    st = FileTokenStorage("meta_ads", base_dir=str(tmp_path))
    assert st.has_credentials() is True


def test_write_is_atomic_and_0600(tmp_path):
    st = FileTokenStorage("meta_ads", base_dir=str(tmp_path))
    st._write(st._tokens_path, {"access_token": "at"})
    assert st._read(st._tokens_path) == {"access_token": "at"}
    # sin .tmp huerfano
    assert not any(p.suffix == ".tmp" for p in tmp_path.iterdir())
    if os.name == "posix":
        assert (os.stat(st._tokens_path).st_mode & 0o777) == 0o600


def test_corrupt_file_is_ignored(tmp_path):
    (tmp_path / "meta_ads_tokens.json").write_text("{not json")
    st = FileTokenStorage("meta_ads", base_dir=str(tmp_path))
    assert st.has_credentials() is False


def test_missing_dir_is_created_on_write(tmp_path):
    nested = tmp_path / "does" / "not" / "exist"
    st = FileTokenStorage("meta_ads", base_dir=str(nested))
    st._write(st._client_path, {"client_id": "x"})
    assert st._client_path.exists()


def test_seed_client_info_writes_prereg_client(tmp_path):
    st = FileTokenStorage("meta_ads", base_dir=str(tmp_path))
    st.seed_client_info(client_id="APP123", redirect_uris=["http://localhost:8766/callback"],
                        scope="ads_read")
    data = st._read(st._client_path)
    assert data["client_id"] == "APP123"
    assert data["token_endpoint_auth_method"] == "none"
    assert data["scope"] == "ads_read"


def test_seed_client_info_is_idempotent(tmp_path):
    st = FileTokenStorage("meta_ads", base_dir=str(tmp_path))
    st.seed_client_info(client_id="APP123", redirect_uris=["u"], scope="ads_read")
    mtime1 = st._client_path.stat().st_mtime_ns
    st.seed_client_info(client_id="APP123", redirect_uris=["u"], scope="ads_read")
    assert st._client_path.stat().st_mtime_ns == mtime1  # no reescritura
