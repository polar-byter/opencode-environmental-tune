"""Run all kit tests: the kit itself, the configurator and the dashboard.

Usage: py kit/task_metrics.py test --task <ID> --scope full -- py -m kit.test_completed
"""
import sys
import unittest


def suite():
    loader = unittest.TestLoader()
    result = unittest.TestSuite()
    for directory in ('kit/tests', 'kit/configurator/tests'):
        result.addTests(loader.discover(directory))
    # The dashboard tests import kit.dashboard as a package, so the project root is the top level.
    result.addTests(loader.discover('kit/dashboard/tests', top_level_dir='.'))
    return result


if __name__ == '__main__':
    sys.exit(not unittest.TextTestRunner(verbosity=1).run(suite()).wasSuccessful())
