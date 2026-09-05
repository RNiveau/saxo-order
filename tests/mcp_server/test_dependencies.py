from mcp_server import dependencies
from mcp_server.dependencies import (
    MARKETS,
    get_configuration,
    resolve_market,
    resolve_market_client,
)
from model import MarketName, Provenance
from model.market import EUMarket


class TestResolveMarket:
    def test_every_market_name_resolves(self):
        """A new MarketName without a class would be a KeyError at runtime."""
        assert {m: MARKETS[m]() for m in MarketName}

    def test_an_unnamed_market_stays_unnamed(self):
        """None travels down to the candle builders, where it means
        'leave the forming period out rather than guess its hours'."""
        assert resolve_market(None) is None

    def test_a_named_market_becomes_its_session_hours(self):
        assert isinstance(resolve_market(MarketName.EU), EUMarket)


class TestResolveMarketClient:
    """Provenance has to track the token, not the moment the server booted."""

    def _isolate(self, tmp_path, monkeypatch):
        get_configuration.cache_clear()
        dependencies._token_refresh_gate.clear()
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("AWS_PROFILE", raising=False)
        monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)

    def test_without_a_token_only_simulated_data_is_available(
        self, tmp_path, monkeypatch
    ):
        self._isolate(tmp_path, monkeypatch)

        assert resolve_market_client()[1] is Provenance.SIMULATED

    def test_authenticating_mid_session_is_picked_up(
        self, tmp_path, monkeypatch
    ):
        """Regression: Configuration reads the token once in __init__.

        With the configuration cached, starting the server before
        authenticating used to refuse every market tool for the rest of the
        session - while telling the caller to refresh the token.
        """
        self._isolate(tmp_path, monkeypatch)
        assert resolve_market_client()[1] is Provenance.SIMULATED

        (tmp_path / "access_token").write_text("a-token\na-refresh-token\n")
        dependencies._token_refresh_gate.clear()

        assert resolve_market_client()[1] is Provenance.LIVE

    def test_a_deleted_token_file_does_not_revoke_provenance(
        self, tmp_path, monkeypatch
    ):
        """Documents a limit rather than asserting an ideal.

        Configuration.load_tokens returns early when the file is missing and
        leaves any token it already holds in place, so deleting the file
        mid-session does not flip provenance back. Nobody deletes their
        token file while trading, and the realistic case - a token that has
        expired - is covered by the venue rejecting it on first use, which
        reaches the caller as a readable error rather than as fake data.
        Changing load_tokens would alter behaviour the CLI and API share.
        """
        self._isolate(tmp_path, monkeypatch)
        token = tmp_path / "access_token"
        token.write_text("a-token\na-refresh-token\n")
        assert resolve_market_client()[1] is Provenance.LIVE

        token.unlink()

        assert resolve_market_client()[1] is Provenance.LIVE


class TestTokenRefreshCost:
    """The token is re-read on a timer, not on every call.

    load_tokens is only a file read without AWS_PROFILE. With it set - the
    setup this server documents for DynamoDB - Configuration holds an
    S3Client and every read is a blocking boto3 get_object, which would
    otherwise land on the event loop once per tool call.
    """

    def _isolate(self, tmp_path, monkeypatch):
        get_configuration.cache_clear()
        dependencies._token_refresh_gate.clear()
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("AWS_PROFILE", raising=False)
        monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
        (tmp_path / "access_token").write_text("a-token\na-refresh-token\n")

    def test_a_burst_of_calls_reads_the_token_once(
        self, tmp_path, monkeypatch, mocker
    ):
        self._isolate(tmp_path, monkeypatch)
        config = get_configuration()
        reads = mocker.spy(config, "load_tokens")

        for _ in range(5):
            resolve_market_client()

        assert reads.call_count == 1

    def test_the_next_window_reads_again(self, tmp_path, monkeypatch, mocker):
        self._isolate(tmp_path, monkeypatch)
        config = get_configuration()
        reads = mocker.spy(config, "load_tokens")

        resolve_market_client()
        dependencies._token_refresh_gate.clear()
        resolve_market_client()

        assert reads.call_count == 2

    def test_a_storage_blip_does_not_fail_the_call(
        self, tmp_path, monkeypatch, mocker
    ):
        """A token read that fails is not a market tool that failed.

        With AWS_PROFILE set this read goes to S3, and a transient error
        there should not cost the caller an answer when the token already
        in hand is almost certainly still good.
        """
        self._isolate(tmp_path, monkeypatch)
        resolve_market_client()
        config = get_configuration()
        dependencies._token_refresh_gate.clear()
        mocker.patch.object(
            config, "load_tokens", side_effect=OSError("s3 unreachable")
        )

        assert resolve_market_client()[1] is Provenance.LIVE

    def test_a_sustained_outage_costs_one_read_per_window(
        self, tmp_path, monkeypatch, mocker
    ):
        self._isolate(tmp_path, monkeypatch)
        resolve_market_client()
        config = get_configuration()
        dependencies._token_refresh_gate.clear()
        failing = mocker.patch.object(
            config, "load_tokens", side_effect=OSError("s3 unreachable")
        )

        for _ in range(5):
            resolve_market_client()

        assert failing.call_count == 1
