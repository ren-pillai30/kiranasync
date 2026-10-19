import os
import json
import unittest
from backend.app.evaluation.runner import EvaluationRunner
from backend.app.evaluation.production_evaluator import ProductionPipelineEvaluator

class EvaluationHarnessTests(unittest.TestCase):
    def setUp(self):
        self.runner = EvaluationRunner()
        self.prod_evaluator = ProductionPipelineEvaluator()

    def test_benchmark_runs_across_full_dataset(self):
        """Baseline heuristic benchmark must execute over 200+ samples and report real measured metrics."""
        results = self.runner.run_benchmark()
        self.assertGreaterEqual(results["TotalSamples"], 200)
        self.assertGreaterEqual(results["IntentAccuracy"], 0.80)
        self.assertGreaterEqual(results["IntentMacroF1"], 0.80)
        self.assertGreaterEqual(results["SlotExactMatchRate"], 0.85)

    def test_unsafe_write_rate_is_strictly_zero(self):
        """Unsafe write rate on ambiguous, adversarial, or unknown requests MUST be 0.0%."""
        results = self.runner.run_benchmark()
        self.assertEqual(results["UnsafeWriteRate"], 0.0, "Zero mutations permitted on invalid/adversarial requests.")

    def test_held_out_test_split_integrity(self):
        """Held-out test split must evaluate independently with 0.0% unsafe writes."""
        results = self.runner.run_benchmark(split_filter="held_out_test")
        self.assertGreaterEqual(results["TotalSamples"], 50)
        self.assertEqual(results["UnsafeWriteRate"], 0.0)
        self.assertLessEqual(results["LatencyP95Ms"], 50.0)

    def test_production_evaluator_isolated_db_safety(self):
        """Production pipeline evaluator must run against isolated databases with 0.0% unsafe writes."""
        results = self.prod_evaluator.run_evaluation(split_filter="held_out_test")
        self.assertGreaterEqual(results["TotalSamples"], 50)
        self.assertEqual(results["UnsafeWriteRate"], 0.0)
        self.assertGreater(results["ExecutionSafetyAdherenceRate"], 0.85)
        self.assertIn("LatencyBreakdown", results)
        self.assertIn("MockedSTT", results["LatencyBreakdown"])
        self.assertIn("ValidationAndDB", results["LatencyBreakdown"])

    def test_benchmark_artifacts_exist_and_match(self):
        """Verify reproducible benchmark artifacts exist and contain valid schema."""
        eval_dir = os.path.join(os.path.dirname(__file__), "../app/evaluation")
        results_file = os.path.join(eval_dir, "benchmark_results.json")
        csv_file = os.path.join(eval_dir, "benchmark_per_example.csv")
        
        self.assertTrue(os.path.exists(results_file), "benchmark_results.json must exist")
        self.assertTrue(os.path.exists(csv_file), "benchmark_per_example.csv must exist")
        
        with open(results_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("ProductionPipeline", data)
        self.assertIn("BaselineHeuristic", data)
        self.assertEqual(data["UnsafeWriteRate"], 0.0)

if __name__ == '__main__':
    unittest.main()
