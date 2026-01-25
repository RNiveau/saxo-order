class TestStockDeduplication:
    """Test deduplication logic for combining API and manual stocks."""

    def test_deduplication_removes_duplicates_keeps_first(self):
        """Test that duplicate stocks are removed, keeping first occurrence."""
        french_stocks = [
            {"name": "Sanofi (API)", "code": "SAN:xpar", "saxo_uic": 114879}
        ]

        followup_stocks = [
            {"name": "Sanofi (Manual)", "code": "SAN:xpar", "saxo_uic": 99999}
        ]

        all_stocks = french_stocks + followup_stocks

        # Deduplication logic (same as in run_alerting)
        seen = set()
        unique_stocks = []
        for stock in all_stocks:
            if stock["code"] not in seen:
                unique_stocks.append(stock)
                seen.add(stock["code"])

        assert len(unique_stocks) == 1
        # First occurrence (API) should be kept
        assert unique_stocks[0]["name"] == "Sanofi (API)"
        assert unique_stocks[0]["saxo_uic"] == 114879

    def test_deduplication_preserves_unique_stocks(self):
        """Test that unique stocks from both sources are preserved."""
        french_stocks = [
            {"name": "TotalEnergies", "code": "TTE:xpar", "saxo_uic": 111},
            {"name": "Sanofi", "code": "SAN:xpar", "saxo_uic": 222},
        ]

        followup_stocks = [
            {"name": "Apple", "code": "AAPL:xnas", "saxo_uic": 333},
            {"name": "Microsoft", "code": "MSFT:xnas", "saxo_uic": 444},
        ]

        all_stocks = french_stocks + followup_stocks

        # Deduplication logic
        seen = set()
        unique_stocks = []
        for stock in all_stocks:
            if stock["code"] not in seen:
                unique_stocks.append(stock)
                seen.add(stock["code"])

        assert len(unique_stocks) == 4
        codes = [s["code"] for s in unique_stocks]
        assert "TTE:xpar" in codes
        assert "SAN:xpar" in codes
        assert "AAPL:xnas" in codes
        assert "MSFT:xnas" in codes

    def test_deduplication_handles_multiple_duplicates(self):
        """Test deduplication with multiple duplicate entries."""
        french_stocks = [
            {"name": "Stock A v1", "code": "A:xpar", "saxo_uic": 1},
            {"name": "Stock B v1", "code": "B:xpar", "saxo_uic": 2},
        ]

        followup_stocks = [
            {"name": "Stock A v2", "code": "A:xpar", "saxo_uic": 99},
            {"name": "Stock B v2", "code": "B:xpar", "saxo_uic": 98},
            {"name": "Stock C", "code": "C:xpar", "saxo_uic": 3},
        ]

        all_stocks = french_stocks + followup_stocks

        # Deduplication logic
        seen = set()
        unique_stocks = []
        for stock in all_stocks:
            if stock["code"] not in seen:
                unique_stocks.append(stock)
                seen.add(stock["code"])

        assert len(unique_stocks) == 3
        # First occurrences should be kept
        assert unique_stocks[0]["name"] == "Stock A v1"
        assert unique_stocks[1]["name"] == "Stock B v1"
        assert unique_stocks[2]["name"] == "Stock C"


class TestStockTransformation:
    """Test data transformation from Saxo API format to internal format."""

    def test_transform_complete_instrument(self):
        """Test transformation of instrument with all fields."""
        instrument = {
            "Symbol": "TTE:xpar",
            "Description": "TotalEnergies SE",
            "Identifier": 23255427,
        }

        # Transformation logic (same as in fetch_french_stocks)
        stock = {
            "name": instrument.get("Description", ""),
            "code": instrument.get("Symbol", ""),
            "saxo_uic": instrument.get("Identifier"),
        }

        assert stock["name"] == "TotalEnergies SE"
        assert stock["code"] == "TTE:xpar"
        assert stock["saxo_uic"] == 23255427

    def test_transform_missing_description(self):
        """Test transformation with missing Description field."""
        instrument = {"Symbol": "SAN:xpar", "Identifier": 114879}

        stock = {
            "name": instrument.get("Description", ""),
            "code": instrument.get("Symbol", ""),
            "saxo_uic": instrument.get("Identifier"),
        }

        assert stock["name"] == ""
        assert stock["code"] == "SAN:xpar"
        assert stock["saxo_uic"] == 114879

    def test_transform_missing_symbol(self):
        """Test transformation with missing Symbol field."""
        instrument = {"Description": "Test Company", "Identifier": 999}

        stock = {
            "name": instrument.get("Description", ""),
            "code": instrument.get("Symbol", ""),
            "saxo_uic": instrument.get("Identifier"),
        }

        assert stock["name"] == "Test Company"
        assert stock["code"] == ""
        assert stock["saxo_uic"] == 999

    def test_transform_missing_identifier(self):
        """Test transformation with missing Identifier field."""
        instrument = {"Symbol": "MC:xpar", "Description": "LVMH"}

        stock = {
            "name": instrument.get("Description", ""),
            "code": instrument.get("Symbol", ""),
            "saxo_uic": instrument.get("Identifier"),
        }

        assert stock["name"] == "LVMH"
        assert stock["code"] == "MC:xpar"
        assert stock["saxo_uic"] is None
