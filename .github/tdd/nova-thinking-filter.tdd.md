# Nova thinking-filter TDD evidence

## Source and user journey

No plan file was supplied. The journey was derived from the reported UI defect:
as an employee using chat, I see only the assistant's final answer, never the
model's internal `<thinking>` content, in either live streaming or history.

## RED and GREEN evidence

- RED: `.venv/Scripts/python.exe -m unittest tests.test_reasoning_filter -v`
  failed with `ModuleNotFoundError: No module named 'utils.reasoning'` before
  production code was added.
- GREEN: `.venv/Scripts/python.exe -m unittest discover -s tests -v` ran 10
  tests successfully.
- Compilation: `.venv/Scripts/python.exe -m compileall -q agent utils tests`
  completed successfully.

## Test specification

| Guarantee | Test type | Result |
|---|---|---|
| Complete and multiple thinking blocks are removed | Unit | PASS |
| Tags split across arbitrary stream chunks are removed | Unit | PASS |
| Normal text and text surrounding thinking blocks is preserved | Unit | PASS |
| Unterminated reasoning is dropped without hiding the next model call | Unit/integration | PASS |
| SSE text events never contain thinking content | Integration | PASS |
| History excludes thinking-only messages and sanitizes final answers | Integration | PASS |

## Coverage and known gaps

Python's standard-library `trace` runner reported 97% line coverage for
`utils.reasoning`. The environment does not include the third-party `coverage`
package. Tests use simulated LangGraph stream events; final verification still
requires deploying the Lambda image and sending a real Nova-backed chat turn.
