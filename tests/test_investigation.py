"""Checks the investigation contract and coordinated timing transformation."""
import unittest

from src.investigation.app import app, cases, time_experiment


class InvestigationTests(unittest.TestCase):
    def test_timing_changes_preserve_counts_and_adjust_rates(self):
        flow = cases()[0]['flow']
        original_copy = dict(flow)
        slower, changes = time_experiment(flow, 2)
        self.assertEqual(flow, original_copy)
        self.assertEqual(slower['Flow Duration'], flow['Flow Duration'] * 2)
        self.assertEqual(slower['Flow IAT Mean'], flow['Flow IAT Mean'] * 2)
        self.assertEqual(slower['Active Std'], flow['Active Std'] * 2)
        self.assertEqual(slower['Flow Packets/s'], flow['Flow Packets/s'] / 2)
        self.assertEqual(slower['Total Fwd Packets'], flow['Total Fwd Packets'])
        self.assertEqual(slower['Packet Length Variance'], flow['Packet Length Variance'])
        self.assertEqual(slower['Flow Duration'] * slower['Flow Packets/s'], flow['Flow Duration'] * flow['Flow Packets/s'])
        self.assertTrue(changes)
        unchanged, no_changes = time_experiment(flow, 1)
        self.assertEqual(unchanged, flow)
        self.assertEqual(no_changes, [])

    def test_case_prediction_experiment_and_reveal(self):
        client = app.test_client()
        self.assertEqual(client.get('/').status_code, 200)
        response = client.get('/api/case')
        self.assertEqual(response.status_code, 200)
        case = response.get_json()
        self.assertNotIn('label', case)
        self.assertNotIn('Label', case['flow'])
        self.assertEqual(len(case['flow']), 65)
        base_response = client.post('/api/analyse', json={'id': case['id']})
        self.assertEqual(base_response.status_code, 200)
        base = base_response.get_json()
        self.assertFalse(base['simulated'])
        self.assertEqual(base['changes'], [])
        self.assertEqual(len(base['result']['shap']), 10)
        self.assertTrue(all(item['meaning'] for item in base['result']['shap']))
        experiment = client.post('/api/analyse', json={'id': case['id'], 'factor': 0.5})
        self.assertEqual(experiment.status_code, 200)
        self.assertTrue(experiment.get_json()['simulated'])
        self.assertNotIn('label', experiment.get_json())
        truth = client.post('/api/reveal', json={'id': case['id']}).get_json()
        self.assertIn(truth['binary_label'], ['BENIGN', 'ATTACK'])
        self.assertEqual(truth['label'], cases()[case['id']]['label'])
        invalid = client.post('/api/analyse', json={'id': case['id'], 'factor': 0})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(client.post('/api/reveal', json={'id': -1}).status_code, 400)


if __name__ == '__main__':
    unittest.main()
