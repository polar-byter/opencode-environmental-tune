"""Run all completed kit code; future dashboard exercises remain explicit opt-ins.

Usage: py kit/task_metrics.py test --task <ID> --scope full -- py -m kit.test_completed
"""
import sys
import unittest


def suite():
    loader = unittest.TestLoader()
    result = unittest.TestSuite()
    for directory in ('kit/tests', 'kit/configurator/tests'):
        result.addTests(loader.discover(directory))
    names = ('test_journal.Step1ParseAndRead', 'test_journal.Step1Status', 'test_journal.Step1Tests',
             'test_learning', 'test_simple', 'test_simple_page', 'test_runtime', 'test_launcher',
             'test_tracking', 'test_observations', 'test_work_http', 'test_tokens_delivery', 'test_controls')
    result.addTests(loader.loadTestsFromNames(['kit.dashboard.tests.' + name for name in names]))
    return result


if __name__ == '__main__':
    sys.exit(not unittest.TextTestRunner(verbosity=1).run(suite()).wasSuccessful())
