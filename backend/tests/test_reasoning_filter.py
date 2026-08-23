import unittest

from utils.reasoning import ThinkingTagFilter, strip_thinking


class StripThinkingTests(unittest.TestCase):
    def test_removes_complete_thinking_block(self):
        self.assertEqual(
            strip_thinking("<thinking>internal plan</thinking>Hello Alice!"),
            "Hello Alice!",
        )

    def test_removes_multiple_thinking_blocks(self):
        self.assertEqual(
            strip_thinking(
                "Start <thinking>first secret</thinking>middle "
                "<thinking>second secret</thinking>end"
            ),
            "Start middle end",
        )

    def test_preserves_normal_text(self):
        self.assertEqual(strip_thinking("No private reasoning here."), "No private reasoning here.")

    def test_drops_unterminated_thinking_block(self):
        self.assertEqual(strip_thinking("Visible<thinking>private"), "Visible")


class ThinkingTagFilterTests(unittest.TestCase):
    def test_handles_tags_split_across_stream_chunks(self):
        stream_filter = ThinkingTagFilter()

        output = [
            stream_filter.feed("<thi"),
            stream_filter.feed("nking>private plan"),
            stream_filter.feed("</thin"),
            stream_filter.feed("king>Hello "),
            stream_filter.feed("Alice!"),
            stream_filter.finish(),
        ]

        self.assertEqual("".join(output), "Hello Alice!")

    def test_preserves_text_around_chunk_split_tags(self):
        stream_filter = ThinkingTagFilter()

        output = [
            stream_filter.feed("Before <thin"),
            stream_filter.feed("king>private</thinking> after"),
            stream_filter.finish(),
        ]

        self.assertEqual("".join(output), "Before  after")

    def test_finish_flushes_non_tag_partial_text(self):
        stream_filter = ThinkingTagFilter()

        output = stream_filter.feed("Use the literal text <thin")
        output += stream_filter.finish()

        self.assertEqual(output, "Use the literal text <thin")


if __name__ == "__main__":
    unittest.main()
