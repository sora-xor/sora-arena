"""A successful state alone is insufficient package qualification evidence."""
from copy import deepcopy
from pathlib import Path
import unittest
from verify_packaged_report import NATIVE, problems

BRIDGE = Path('/fixture/SoraArena.app/Contents/UE/SoraArena/Binaries/Mac/libconnect_norito_bridge.dylib')


def report():
    return {'failed': 0, 'notRun': 0, 'inProcess': 0, 'tests': [{
        'fullTestPath': NATIVE, 'state': 'Success', 'errors': 0, 'entries': [
            {'event': {'type': 'Info', 'message': f'NativeLoader context=client staged_library={BRIDGE}'}},
            {'event': {'type': 'Info', 'message': 'NativeLoader ABI=30 research_builder=1 join_inspector=1 join_signing_blocked=1 buy_signing_blocked=1'}}]}]}


class PackagedReportTests(unittest.TestCase):
    def check(self, value=None, log=None, selected='SoraArena', status=0):
        if log is None: log = f"Found 1 automation tests based on '{selected}'"
        return problems(report() if value is None else value, log, selected, status, BRIDGE)

    def test_real_client_evidence_passes(self): self.assertEqual([], self.check())

    def test_missing_discovery_rejects(self): self.assertTrue(self.check(log=''))

    def test_wrong_discovery_selection_rejects(self):
        self.assertTrue(self.check(log="Found 1 automation tests based on 'SoraArena.Campaign'"))

    def test_success_with_error_counter_or_event_rejects(self):
        for counter in (True, False):
            value = report()
            if counter: value['tests'][0]['errors'] = 1
            else: value['tests'][0]['entries'].append({'event': {'type': 'Error', 'message': 'actual failure'}})
            self.assertTrue(self.check(value))

    def test_aggregate_failure_incomplete_and_nonzero_exit_reject(self):
        for key in ('failed', 'notRun', 'inProcess'):
            value = report(); value[key] = 1
            self.assertTrue(self.check(value))
        self.assertTrue(self.check(status=142))

    def test_native_cannot_silently_disappear_from_full_or_connect_suite(self):
        value = report(); value['tests'][0]['fullTestPath'] = 'SoraArena.Connect.SomeOlderTest'
        for selection in ('SoraArena', 'SoraArena.Connect', NATIVE):
            self.assertTrue(self.check(value, selected=selection))

    def test_unselected_native_is_not_required(self):
        value = report(); value['tests'][0]['fullTestPath'] = 'SoraArena.Campaign.Example'; value['tests'][0]['entries'] = []
        self.assertEqual([], self.check(value, selected='SoraArena.Campaign'))

    def test_wrong_library_or_editor_context_reject(self):
        for message in ('NativeLoader context=client staged_library=/another/bridge.dylib',
                        f'NativeLoader context=editor staged_library={BRIDGE}'):
            value = report(); value['tests'][0]['entries'][0]['event']['message'] = message
            self.assertTrue(self.check(value))

    def test_missing_abi_or_signing_restriction_execution_rejects(self):
        value = report(); value['tests'][0]['entries'].pop()
        self.assertTrue(self.check(value))

    def test_duplicate_native_or_bad_discovery_count_rejects(self):
        value = report(); value['tests'].append(deepcopy(value['tests'][0]))
        self.assertTrue(self.check(value, log="Found 2 automation tests based on 'SoraArena'"))
        self.assertTrue(self.check(log="Found 2 automation tests based on 'SoraArena'"))

    def test_material_fallback_and_fatal_reject(self):
        for failure in ('LogMaterial: Warning: Material /Game/Test missing usage flag bUsedWithNanite! Default Material will be used in game',
                        'LogOutputDevice: Error: Ensure condition failed: broken'):
            self.assertTrue(self.check(log="Found 1 automation tests based on 'SoraArena'\n" + failure))


if __name__ == '__main__': unittest.main()
