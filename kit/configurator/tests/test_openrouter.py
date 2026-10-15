"""Live-catalog contract: units, unknown prices, coding scope, safe public fetch and cache."""
from decimal import Decimal
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kit.configurator import openrouter


def row(model_id='author/coder', **changes):
    value = {'id': model_id, 'name': 'Test Coder', 'description': 'A model for coding.',
             'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']},
             'pricing': {'prompt': '0.0000003', 'completion': '0.0000012'},
             'context_length': 128000, 'supported_parameters': ['tools']}
    value.update(changes)
    return value


def snapshot(*rows, programming_ids=()):
    return {'version': 1, 'fetched_at': 1792048374, 'payload': {'data': list(rows)},
            'programming_ids': list(programming_ids), 'warning': ''}


class CatalogDataTests(unittest.TestCase):
    def test_prices_are_exact_usd_per_million(self):
        model = openrouter.parse_models({'data': [row()]})[0]
        self.assertEqual(openrouter.money(model.input_price), '$0.3')
        self.assertEqual(openrouter.money(model.output_price), '$1.2')
        self.assertEqual(openrouter.money(Decimal('0.0000000001')), '$0.0001')
        self.assertEqual(openrouter.money(Decimal('0')), '$0')

    def test_unknown_or_dynamic_prices_never_become_free(self):
        for value in (None, '', 'NaN', 'Infinity', '-1', 'wrong', True, {}):
            with self.subTest(value=value):
                model = openrouter.parse_models({'data': [row(pricing={'prompt': value, 'completion': '0'})]})[0]
                self.assertEqual(model.tariff, 'Unknown')
                self.assertEqual(openrouter.money(model.input_price), '—')

    def test_free_variant_id_is_preserved_and_request_fee_is_not_free(self):
        models = openrouter.parse_models({'data': [row('author/coder:free', pricing={'prompt': '0', 'completion': '0'}),
                    row('author/request-fee', pricing={'prompt': '0', 'completion': '0', 'request': '0.01'})]})
        self.assertEqual(models[0].id, 'author/coder:free')
        self.assertEqual(models[0].tariff, 'Free')
        self.assertEqual(models[1].tariff, 'Paid')
        self.assertEqual(openrouter.money(models[1].request_price, False), '$0.01')

    def test_conditional_tariff_is_visible_even_if_current_rates_zero(self):
        model = openrouter.parse_models({'data': [row(pricing={'prompt': '0', 'completion': '0',
                     'overrides': [{'min_prompt_tokens': 100, 'prompt': '0.001'}]})]})[0]
        self.assertEqual(model.tariff, 'Conditional')

    def test_coding_category_and_description_both_contribute(self):
        models = openrouter.parse_models({'data': [row('a/special', name='General', description='General reasoning.'),
                      row('a/coder:free'), row('a/story', name='Story', description='Fiction writing.')]}, {'a/special'})
        self.assertEqual({m.id for m in openrouter.select_models(models)}, {'a/special', 'a/coder:free'})
        self.assertEqual(len(openrouter.select_models(models, scope='all')), 3)

    def test_filters_and_sorting_include_free_to_paid_and_unknown_last(self):
        models = openrouter.parse_models({'data': [row('a/paid'), row('a/unknown', pricing={}),
                    row('a/free:free', pricing={'prompt': '0', 'completion': '0'}),
                    row('a/no-tools', supported_parameters=[], context_length=256000)]})
        ordered = openrouter.select_models(models)
        self.assertEqual(ordered[0].id, 'a/free:free')
        self.assertEqual(ordered[-1].id, 'a/unknown')
        self.assertEqual([m.id for m in openrouter.select_models(models, tariff='free')], ['a/free:free'])
        self.assertNotIn('a/no-tools', [m.id for m in openrouter.select_models(models, tools_only=True)])
        self.assertEqual(openrouter.select_models(models, query='paid')[0].id, 'a/paid')
        self.assertEqual(openrouter.select_models(models, sort='context')[0].id, 'a/no-tools')

    def test_non_text_models_duplicates_and_bad_rows_do_not_pollute_catalog(self):
        valid = row()
        models = openrouter.parse_models({'data': [None, {'id': 7}, valid, valid,
                 row('a/image', architecture={'input_modalities': ['text'], 'output_modalities': ['image']}),
                 row('a/bad', architecture={'input_modalities': None, 'output_modalities': None})]})
        self.assertEqual([model.id for model in models], ['author/coder'])

    def test_missing_tools_and_context_stay_unknown(self):
        model = openrouter.parse_models({'data': [row(context_length=True, supported_parameters=None)]})[0]
        self.assertIsNone(model.context)
        self.assertIsNone(model.tools)

    def test_invalid_catalog_is_an_error_instead_of_empty_success(self):
        for value in ([], {}, {'data': None}, {'data': [{'id': 'bad'}]}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                openrouter.parse_models(value)

    def test_only_exact_secure_openrouter_base_reuses_role_key(self):
        self.assertTrue(openrouter.is_openrouter('https://openrouter.ai/api/v1/'))
        for url in ('https://openrouter.ai.evil.test/api/v1', 'http://openrouter.ai/api/v1',
                    'https://user:secret@openrouter.ai/api/v1', 'https://openrouter.ai/api/v1?key=a',
                    'https://different.test/v1', ''):
            self.assertFalse(openrouter.is_openrouter(url))


class CatalogFetchTests(unittest.TestCase):
    def test_public_request_uses_no_key_and_no_arbitrary_host(self):
        body = io.BytesIO(b'{"data":[]}')
        with patch.object(openrouter, 'urlopen', return_value=body) as call:
            self.assertEqual(openrouter.request_catalog(openrouter.CATALOG_URL), {'data': []})
        request = call.call_args.args[0]
        self.assertIsNone(request.get_header('Authorization'))
        self.assertEqual(request.full_url, 'https://openrouter.ai/api/v1/models')
        self.assertEqual(call.call_args.kwargs['timeout'], 20)

    def test_fetch_combines_complete_catalog_with_optional_category_and_caches(self):
        payload = {'data': [row('a/general', description='General reasoning.', name='General')],
                   'total_count': 1, 'links': {'next': None}}
        with tempfile.TemporaryDirectory() as folder, patch.object(openrouter, 'request_catalog',
                    side_effect=[payload, {'data': [{'id': 'a/general'}]}]) as fetch:
            result = openrouter.fetch(Path(folder))
            self.assertEqual(fetch.call_args_list[0].args, (openrouter.CATALOG_URL,))
            self.assertEqual(result['programming_ids'], ['a/general'])
            self.assertEqual(openrouter.cached(Path(folder))['payload'], payload)
            self.assertEqual(openrouter.parse_models(payload, result['programming_ids'])[0].coding, 'OpenRouter picks')

    def test_category_failure_keeps_full_catalog_with_honest_scope_warning(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(openrouter, 'request_catalog',
                    side_effect=[{'data': [row()]}, TimeoutError('offline')]):
            result = openrouter.fetch(Path(folder))
        self.assertEqual(len(result['payload']['data']), 1)
        self.assertIn('unavailable', result['warning'])

    def test_partial_catalog_is_not_silently_saved_as_complete(self):
        for extra in ({'total_count': 2}, {'links': {'next': 'https://wrong.example/page2'}}):
            with tempfile.TemporaryDirectory() as folder, patch.object(openrouter, 'request_catalog',
                         return_value=dict({'data': [row()]}, **extra)):
                with self.assertRaisesRegex(ValueError, 'Incomplete'):
                    openrouter.fetch(Path(folder))
                self.assertFalse((Path(folder) / openrouter.CACHE_PATH).exists())

    def test_cache_damage_and_future_timestamp_are_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / openrouter.CACHE_PATH
            path.parent.mkdir()
            for text in ('broken', json.dumps(dict(snapshot(row()), fetched_at=float('inf'))),
                         json.dumps(dict(snapshot(row()), programming_ids=[{}]))):
                path.write_text(text)
                self.assertIsNone(openrouter.cached(Path(folder)))
