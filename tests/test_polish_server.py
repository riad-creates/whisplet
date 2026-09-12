import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location(
    "polish_server", Path(__file__).resolve().parents[1] / "sidecar/polish_server.py")
polish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(polish)


class Tokenizer:
    def encode(self, text):
        return list(text)

    def apply_chat_template(self, messages, **kwargs):
        assert kwargs["enable_thinking"] is False
        assert messages[0]["content"] == polish.SYSTEM_PROMPT
        assert messages[1]["content"].startswith(polish.CONTROL + "\n")
        return messages[1]["content"].split("\n", 1)[1]


class PolishTests(unittest.TestCase):
    def test_chunking_is_lossless_for_long_unicode_transcripts(self):
        text = "  " + "hello café 🦜.\n\n" * 400 + "THE LAST SENTENCE\n"
        chunks = polish.split_transcript(text, Tokenizer())
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunks), text)
        self.assertTrue(all(len(chunk) <= polish.INPUT_CHUNK_TOKENS for chunk in chunks))

    def test_long_output_keeps_final_sentence(self):
        text = "hello there. " * 300 + "The tail must survive."
        def generate(prompt, budget):
            yield SimpleNamespace(text=prompt, generation_tokens=len(prompt), finish_reason="stop")
        result = polish.normalize(text, Tokenizer(), generate)
        self.assertEqual(result["outputText"], text)
        self.assertGreater(result["diagnostics"]["chunkCount"], 1)
        self.assertEqual(result["diagnostics"]["fallbackChunkCount"], 0)

    def test_sentence_boundaries_are_preferred(self):
        text = "First sentence. Second sentence. Third sentence."
        chunks = polish.split_transcript(text, Tokenizer(), limit=36)
        self.assertEqual(chunks, ["First sentence. Second sentence.", " Third sentence."])

    def test_token_cap_falls_back_instead_of_truncating(self):
        text = "This is an entire sentence that must not be lost."
        def generate(prompt, budget):
            yield SimpleNamespace(text="This is", generation_tokens=budget, finish_reason="length")
        result = polish.normalize(text, Tokenizer(), generate)
        self.assertEqual(result["outputText"], text)
        self.assertEqual(result["diagnostics"]["fallbackChunkCount"], 1)

    def test_oversized_unbroken_text_never_reaches_model(self):
        text = "🦜" * 4000
        def generate(*args):
            self.fail("oversized word must be passed through")
        self.assertEqual(polish.normalize(text, Tokenizer(), generate)["outputText"], text)

    def test_blank_output_does_not_erase_speech(self):
        self.assertEqual(polish.preserve_chunk("hello there", "", False), "hello there")


if __name__ == "__main__":
    unittest.main()
