"""Remove model-internal reasoning tags from user-visible text."""

THINKING_OPEN = "<thinking>"
THINKING_CLOSE = "</thinking>"


def _partial_marker_length(value: str, marker: str) -> int:
    """Return the longest suffix of ``value`` that could start ``marker``."""
    max_length = min(len(value), len(marker) - 1)
    for length in range(max_length, 0, -1):
        if value.endswith(marker[:length]):
            return length
    return 0


class ThinkingTagFilter:
    """Streaming-safe filter for Nova ``<thinking>`` content."""

    def __init__(self) -> None:
        self._buffer = ""
        self._in_thinking = False

    def feed(self, text: str) -> str:
        """Consume one stream chunk and return only user-visible text."""
        if not text:
            return ""

        self._buffer += text
        visible: list[str] = []

        while self._buffer:
            marker = THINKING_CLOSE if self._in_thinking else THINKING_OPEN
            marker_index = self._buffer.find(marker)

            if marker_index >= 0:
                if not self._in_thinking:
                    visible.append(self._buffer[:marker_index])
                self._buffer = self._buffer[marker_index + len(marker):]
                self._in_thinking = not self._in_thinking
                continue

            partial_length = _partial_marker_length(self._buffer, marker)
            complete_length = len(self._buffer) - partial_length
            complete_text = self._buffer[:complete_length]

            if not self._in_thinking:
                visible.append(complete_text)

            self._buffer = self._buffer[complete_length:]
            break

        return "".join(visible)

    def finish(self) -> str:
        """Finish one model call, dropping any unterminated reasoning block."""
        visible = "" if self._in_thinking else self._buffer
        self._buffer = ""
        self._in_thinking = False
        return visible


def strip_thinking(text: str) -> str:
    """Remove reasoning blocks from a complete string."""
    stream_filter = ThinkingTagFilter()
    return stream_filter.feed(text) + stream_filter.finish()
