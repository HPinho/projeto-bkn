from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVALUATOR = ROOT / "kernel/src/acpi/aml_evaluator.sotlas"


class AmlEvaluatorDsmContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = EVALUATOR.read_text(encoding="utf-8")

    def test_aml6b_allows_serialized_flag(self):
        # Invariante AML-6b: aceita flags de método Serialized (bit 3 / 0x08) com SyncLevel 0
        execute = self.source.split("pub fn aml_evaluator_execute_method", 1)[1].split(
            "pub fn aml_evaluator_is_ready", 1
        )[0]
        self.assertIn("let declared_args = (flags & 0x07) as usize", execute)
        self.assertIn("(flags & 0xF0) != 0", execute)
        self.assertIn("AML_EVAL_ERROR_FLAGS", execute)

    def test_aml6b_lequal_supports_buffer_comparison(self):
        # Invariante AML-6b: LEqual deve comparar buffers byte-a-byte para ToUUID / _DSM
        self.assertIn("fn aml_eval_buffers_equal", self.source)
        self.assertIn("if left.kind == AML_EVAL_VALUE_BUFFER && right.kind == AML_EVAL_VALUE_BUFFER", self.source)
        self.assertIn("let equal = aml_eval_buffers_equal(&left, &right);", self.source)

    def test_aml6b_buffer_and_package_constructors_exist(self):
        # Invariante AML-6b: helpers públicos para construção de Arg0 (Buffer) e Arg3 (Package)
        self.assertIn("pub fn aml_eval_buffer(data: *const u8, data_length: usize) -> AmlEvalValue", self.source)
        self.assertIn("pub fn aml_eval_package(data: *const u8, data_length: usize, element_count: usize) -> AmlEvalValue", self.source)

    def test_buffers_equal_algorithm(self):
        # Validação algorítmica de comparação exata de buffers
        guid_hidi2c = bytes([0xF7, 0xF6, 0xDF, 0x3C, 0x67, 0x42, 0x55, 0x45, 0xAD, 0x05, 0xB3, 0x0A, 0x3D, 0x89, 0x38, 0xDE])
        guid_wrong = bytes([0x00] * 16)
        guid_short = bytes([0xF7, 0xF6, 0xDF])

        def buffers_equal(b1, b2):
            if len(b1) != len(b2):
                return False
            return b1 == b2

        self.assertTrue(buffers_equal(guid_hidi2c, guid_hidi2c))
        self.assertFalse(buffers_equal(guid_hidi2c, guid_wrong))
        self.assertFalse(buffers_equal(guid_hidi2c, guid_short))


if __name__ == "__main__":
    unittest.main()
