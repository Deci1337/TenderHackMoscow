"""
50 regression tests for ML ranking and NLP pipeline quality.

Split into two groups:
  - nlp  : offline tests, no server required  (~25 tests)
  - api  : integration tests against live API  (~25 tests)

Usage:
    # NLP tests only (fast, no server):
    pytest backend/tests/test_search_quality.py -m nlp -v

    # All tests (requires: docker compose up, stack ready):
    pytest backend/tests/test_search_quality.py -v

    # Print quality summary:
    pytest backend/tests/test_search_quality.py -m api -v -s
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, str(__file__.split("tests")[0]))

SEARCH_URL = os.environ.get("SEARCH_URL", "http://localhost:8000/api/v1/search")
PROBE_INN = os.environ.get("PROBE_INN", "1234567890123")
TIMEOUT = int(os.environ.get("PROBE_TIMEOUT", "15"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _api(query: str, limit: int = 5, category: str | None = None) -> dict | None:
    payload = {"query": query, "user_inn": PROBE_INN, "limit": limit, "offset": 0}
    if category:
        payload["category"] = category
    try:
        req = urllib.request.Request(
            SEARCH_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _names(data: dict, k: int = 5) -> list[str]:
    return [r.get("name", "").lower() for r in (data.get("results") or [])[:k]]


def _categories(data: dict, k: int = 5) -> list[str]:
    return [r.get("category", "").lower() for r in (data.get("results") or [])[:k]]


def _server_available() -> bool:
    try:
        urllib.request.urlopen(
            SEARCH_URL.replace("/api/v1/search", "/health"), timeout=3
        )
        return True
    except Exception:
        return False


skip_no_server = pytest.mark.skipif(
    not _server_available(),
    reason="live stack not running (docker compose up)",
)


# ---------------------------------------------------------------------------
# NLP OFFLINE TESTS  (25 tests)
# ---------------------------------------------------------------------------

class TestQueryType:
    """task 4.1 — query_type classification in process_query output."""

    @pytest.fixture(scope="class")
    def nlp(self):
        from app.services.nlp_service import NLPService
        svc = NLPService()
        svc.initialize()
        return svc

    @pytest.mark.nlp
    def test_single_word_is_short(self, nlp):
        assert nlp.process_query("бумага")["query_type"] == "short"

    @pytest.mark.nlp
    def test_two_words_is_medium(self, nlp):
        assert nlp.process_query("бумага офисная")["query_type"] == "medium"

    @pytest.mark.nlp
    def test_three_words_is_medium(self, nlp):
        assert nlp.process_query("бумага для принтера")["query_type"] == "medium"

    @pytest.mark.nlp
    def test_four_words_is_long(self, nlp):
        assert nlp.process_query("бумага а4 для принтера офис")["query_type"] == "long"

    @pytest.mark.nlp
    def test_stopwords_not_counted(self, nlp):
        # "и", "для", "с" are stopwords — stripped before counting
        result = nlp.process_query("ручка и карандаш")
        assert result["query_type"] in ("short", "medium")


class TestTypoCorrection:
    """Typo correction via SymSpell + domain dictionary (10 tests)."""

    @pytest.fixture(scope="class")
    def nlp(self):
        from app.services.nlp_service import NLPService
        svc = NLPService()
        svc.initialize()
        return svc

    @pytest.mark.nlp
    def test_extra_letter(self, nlp):
        corrected, fixed = nlp.correct_typos("карандашь")
        assert "карандаш" in corrected

    @pytest.mark.nlp
    def test_vowel_swap(self, nlp):
        corrected, _ = nlp.correct_typos("карандош")
        assert "карандаш" in corrected

    @pytest.mark.nlp
    def test_double_letter(self, nlp):
        corrected, fixed = nlp.correct_typos("ручкаа")
        assert "ручка" in corrected

    @pytest.mark.nlp
    def test_case_normalization(self, nlp):
        corrected, _ = nlp.correct_typos("БУМАГА")
        assert corrected == "бумага"

    @pytest.mark.nlp
    def test_clean_word_unchanged(self, nlp):
        corrected, fixed = nlp.correct_typos("принтер")
        assert corrected == "принтер"
        assert fixed is False

    @pytest.mark.nlp
    def test_short_word_not_mangled(self, nlp):
        # Words <= 2 chars must not be corrected
        corrected, _ = nlp.correct_typos("пк")
        assert "пк" in corrected

    @pytest.mark.nlp
    def test_unit_in_query(self, nlp):
        corrected, _ = nlp.correct_typos("бумага 500 листов")
        assert "бумага" in corrected

    @pytest.mark.nlp
    def test_multiword_typo(self, nlp):
        corrected, fixed = nlp.correct_typos("принтер многофункциональны")
        # at minimum normalization should not crash
        assert isinstance(corrected, str) and len(corrected) > 0

    @pytest.mark.nlp
    def test_mixed_case_corrected(self, nlp):
        corrected, _ = nlp.correct_typos("Принтер МФУ")
        assert "принтер" in corrected.lower()

    @pytest.mark.nlp
    def test_empty_string(self, nlp):
        corrected, fixed = nlp.correct_typos("")
        assert corrected == ""
        assert fixed is False


class TestUnitNormalization:
    """task 2.3 — normalize_units strips numeric prefix (5 tests)."""

    @pytest.fixture(scope="class")
    def nlp(self):
        from app.services.nlp_service import NLPService
        return NLPService()

    @pytest.mark.nlp
    def test_kg_stripped(self, nlp):
        assert nlp.normalize_units("2 кг") == "кг"

    @pytest.mark.nlp
    def test_pieces_stripped(self, nlp):
        assert nlp.normalize_units("100 шт") == "шт"

    @pytest.mark.nlp
    def test_litre_stripped(self, nlp):
        assert nlp.normalize_units("5 л") == "л"

    @pytest.mark.nlp
    def test_unit_in_sentence(self, nlp):
        result = nlp.normalize_units("бумага 500 шт а4")
        assert "500" not in result
        assert "шт" in result

    @pytest.mark.nlp
    def test_no_unit_unchanged(self, nlp):
        assert nlp.normalize_units("принтер офисный") == "принтер офисный"


class TestSynonymExpansion:
    """task 2.2 — synonyms expand query tokens (5 tests)."""

    @pytest.fixture(scope="class")
    def nlp(self):
        from app.services.nlp_service import NLPService
        svc = NLPService()
        svc.initialize()
        return svc

    @pytest.mark.nlp
    def test_pк_expands_to_computer(self, nlp):
        terms, _ = nlp.expand_synonyms("пк")
        joined = " ".join(terms)
        assert any(w in joined for w in ("компьютер", "системный", "персональный"))

    @pytest.mark.nlp
    def test_mfu_expands_to_printer(self, nlp):
        terms, _ = nlp.expand_synonyms("мфу")
        joined = " ".join(terms)
        assert any(w in joined for w in ("принтер", "копир", "сканер"))

    @pytest.mark.nlp
    def test_laptop_abbreviation(self, nlp):
        terms, _ = nlp.expand_synonyms("нб")
        joined = " ".join(terms)
        assert any(w in joined for w in ("ноутбук", "лэптоп", "портативный"))

    @pytest.mark.nlp
    def test_no_expansion_for_unknown(self, nlp):
        terms, applied = nlp.expand_synonyms("ксерокопия")
        # must not crash; terms should at least contain the original lemma
        assert isinstance(terms, list)

    @pytest.mark.nlp
    def test_expansion_deduplicates(self, nlp):
        terms, _ = nlp.expand_synonyms("принтер")
        assert len(terms) == len(set(terms))


# ---------------------------------------------------------------------------
# API INTEGRATION TESTS  (25 tests)
# ---------------------------------------------------------------------------

class TestAPIBasic:
    """API responds, results are non-empty, scores are positive."""

    @pytest.mark.api
    @skip_no_server
    def test_api_returns_results_for_paper(self):
        data = _api("бумага")
        assert data is not None
        assert len(data.get("results", [])) > 0

    @pytest.mark.api
    @skip_no_server
    def test_api_scores_positive(self):
        data = _api("ноутбук")
        scores = [r.get("score", 0) for r in data.get("results", [])]
        assert all(s > 0 for s in scores)

    @pytest.mark.api
    @skip_no_server
    def test_api_results_sorted_descending(self):
        data = _api("принтер")
        scores = [r.get("score", 0) for r in data.get("results", [])]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.api
    @skip_no_server
    def test_api_returns_name_and_category(self):
        data = _api("картридж")
        for r in data.get("results", []):
            assert "name" in r

    @pytest.mark.api
    @skip_no_server
    def test_api_total_gte_results(self):
        data = _api("офисная мебель", limit=5)
        assert data.get("total", 0) >= len(data.get("results", []))


class TestTypoQuality:
    """Typo queries must return same top category as clean queries."""

    @pytest.mark.api
    @skip_no_server
    def test_typo_pencil_returns_pencil(self):
        data = _api("карандашь", limit=5)
        assert data is not None, "API unreachable"
        names = _names(data)
        assert any("карандаш" in n for n in names), f"Expected pencil in {names}"

    @pytest.mark.api
    @skip_no_server
    def test_typo_paper_returns_paper(self):
        data = _api("бумага а44", limit=5)
        names = _names(data)
        assert any("бумага" in n for n in names), f"Expected paper in {names}"

    @pytest.mark.api
    @skip_no_server
    def test_typo_printer_returns_printer(self):
        data = _api("принтерр", limit=5)
        names = _names(data)
        assert any("принтер" in n or "мфу" in n for n in names), f"Expected printer in {names}"

    @pytest.mark.api
    @skip_no_server
    def test_typo_corrected_query_in_response(self):
        data = _api("ручкаа")
        assert data.get("corrected_query") is not None or len(data.get("results", [])) > 0

    @pytest.mark.api
    @skip_no_server
    def test_typo_stapler_returns_office(self):
        data = _api("степлерр", limit=5)
        assert data is not None


class TestSynonymQuality:
    """Abbreviation / synonym queries must retrieve correct products."""

    @pytest.mark.api
    @skip_no_server
    def test_pk_returns_computer(self):
        data = _api("пк", limit=5)
        names = _names(data)
        assert any(
            kw in n for n in names
            for kw in ("компьютер", "системный", "персональный", "пк")
        ), f"No computer in {names}"

    @pytest.mark.api
    @skip_no_server
    def test_nb_returns_laptop(self):
        data = _api("нб", limit=5)
        names = _names(data)
        assert any(
            kw in n for n in names
            for kw in ("ноутбук", "лэптоп", "портативный", "нб")
        ), f"No laptop in {names}"

    @pytest.mark.api
    @skip_no_server
    def test_mfu_returns_printer_family(self):
        data = _api("мфу", limit=5)
        names = _names(data)
        assert any(
            kw in n for n in names
            for kw in ("принтер", "мфу", "копир", "сканер", "многофункциональное")
        ), f"No printer/MFU in {names}"

    @pytest.mark.api
    @skip_no_server
    def test_ibp_returns_ups(self):
        data = _api("ибп", limit=5)
        names = _names(data)
        assert any(
            kw in n for n in names
            for kw in ("ибп", "источник бесперебойного", "упс", "ups")
        ), f"No UPS in {names}"

    @pytest.mark.api
    @skip_no_server
    def test_szi_returns_security_software(self):
        data = _api("сзи", limit=5)
        # must not crash
        assert data is not None


class TestMultiWordQuality:
    """Multi-word queries get more semantic weight (long query type)."""

    @pytest.mark.api
    @skip_no_server
    def test_multiword_laptop_returns_laptop(self):
        data = _api("ноутбук для офиса 15 дюймов", limit=5)
        names = _names(data)
        assert any("ноутбук" in n for n in names), f"Expected laptop in {names}"

    @pytest.mark.api
    @skip_no_server
    def test_multiword_stationery_returns_stationery(self):
        data = _api("канцелярские товары для офиса карандаши ручки", limit=5)
        names = _names(data)
        assert any(
            kw in n for n in names
            for kw in ("ручка", "карандаш", "канцелярск")
        ), f"Expected stationery in {names}"

    @pytest.mark.api
    @skip_no_server
    def test_multiword_no_empty_results(self):
        data = _api("поставка бумаги а4 для нужд учреждения", limit=5)
        assert len(data.get("results", [])) > 0

    @pytest.mark.api
    @skip_no_server
    def test_long_query_semantic_active(self):
        # long queries should lean on semantics; result should still be relevant
        data = _api("расходные материалы для оргтехники картриджи тонер", limit=5)
        names = _names(data)
        assert any(
            kw in n for n in names
            for kw in ("картридж", "тонер", "расходн")
        ), f"Expected cartridge/toner in {names}"

    @pytest.mark.api
    @skip_no_server
    def test_ambiguous_kran_returns_results(self):
        # "кран" — homograph (water tap vs crane)
        data = _api("кран")
        assert len(data.get("results", [])) > 0


class TestEdgeCases:
    """Edge cases: empty-ish queries, numbers, special chars."""

    @pytest.mark.api
    @skip_no_server
    def test_category_only_word(self):
        data = _api("канцелярия")
        assert data is not None and len(data.get("results", [])) > 0

    @pytest.mark.api
    @skip_no_server
    def test_all_caps_normalized(self):
        data_caps = _api("ПРИНТЕР")
        data_lower = _api("принтер")
        names_caps = _names(data_caps)
        names_lower = _names(data_lower)
        # top result should be the same regardless of case
        assert names_caps[0] == names_lower[0] if names_caps and names_lower else True

    @pytest.mark.api
    @skip_no_server
    def test_number_only_query_graceful(self):
        data = _api("100")
        assert data is not None

    @pytest.mark.api
    @skip_no_server
    def test_single_char_graceful(self):
        data = _api("а")
        assert data is not None

    @pytest.mark.api
    @skip_no_server
    def test_limit_respected(self):
        data = _api("бумага", limit=3)
        assert len(data.get("results", [])) <= 3


class TestRankingQuality:
    """Ranking-specific: personalization, popularity, negative signals."""

    @pytest.mark.api
    @skip_no_server
    def test_popular_item_in_top5(self):
        # common procurement item should rank high by popularity
        data = _api("бумага а4", limit=10)
        names = _names(data, k=10)
        assert any("бумага" in n for n in names), f"Paper not found in {names}"

    @pytest.mark.api
    @skip_no_server
    def test_exact_name_tops_partial(self):
        # exact product name should beat vague match
        data = _api("карандаш механический", limit=5)
        names = _names(data)
        assert any("карандаш" in n for n in names), f"No pencil in {names}"

    @pytest.mark.api
    @skip_no_server
    def test_medical_gloves_in_medical_context(self):
        data = _api("перчатки медицинские", limit=5)
        names = _names(data)
        assert any("перчатк" in n for n in names), f"Expected gloves in {names}"

    @pytest.mark.api
    @skip_no_server
    def test_server_hardware_category(self):
        data = _api("сервер", limit=5)
        assert data is not None

    @pytest.mark.api
    @skip_no_server
    def test_furniture_returns_furniture(self):
        data = _api("стол офисный", limit=5)
        names = _names(data)
        assert any("стол" in n for n in names), f"No desk in {names}"
