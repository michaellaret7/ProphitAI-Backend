from contextlib import contextmanager
from types import SimpleNamespace

from prophitai_atlas.execution import ExecutionLoop, ToolHandler
from prophitai_atlas.logging import AgentPrinter
from prophitai_atlas.models import PrintMode
from prophitai_shared import NormalizedLLMResponse
from prophitai_shared.llm_backends.models import UsageStats


class RecordingSpan:
    def __init__(self) -> None:
        self.updates = []

    def update(self, **kwargs):
        self.updates.append(kwargs)


class RecordingObserver:
    def __init__(self) -> None:
        self.calls = []
        self.spans = []

    @contextmanager
    def execution_loop(self, *, input):
        span = RecordingSpan()
        self.calls.append(("execution_loop", input))
        self.spans.append(span)
        yield span

    @contextmanager
    def iteration(self, *, number, input):
        span = RecordingSpan()
        self.calls.append(("iteration", number, input))
        self.spans.append(span)
        yield span

    @contextmanager
    def tool(self, *, name, args):
        span = RecordingSpan()
        self.calls.append(("tool", name, args))
        self.spans.append(span)
        yield span

    def current_context(self):
        self.calls.append(("current_context",))
        return "ctx"

    @contextmanager
    def attach_context(self, context):
        self.calls.append(("attach_context", context))
        yield


class DummyCallback:
    def on_run_started(self, **kwargs):
        pass

    def on_iteration_start(self, **kwargs):
        pass

    def on_iteration_end(self, **kwargs):
        pass

    def on_run_finished(self, **kwargs):
        pass

    def on_run_error(self, **kwargs):
        pass


class DummyBackend:
    def call_llm(self, **kwargs):
        return NormalizedLLMResponse(
            assistant_text="done",
            usage=UsageStats(input_tokens=1, output_tokens=1, total_tokens=2),
        )


class DummyAgent:
    def __init__(self) -> None:
        self.printer = AgentPrinter(PrintMode.PRODUCTION)
        self.messages = [{"role": "user", "content": "hello"}]
        self.model = "dummy-model"
        self.max_iterations = 3
        self.session_id = "dummy-session"
        self.chat_callback = DummyCallback()
        self.backend = DummyBackend()
        self.tools = []
        self.temperature = None
        self.total_tokens = 0
        self.cache_creation_input_tokens = 0
        self.cache_read_input_tokens = 0
        self.tool_functions = {"echo": lambda text: {"success": True, "text": text}}
        self.user_id = None

    def get_tool_names(self):
        return list(self.tool_functions)


def test_execution_loop_uses_observer_for_loop_and_iteration_spans():
    agent = DummyAgent()
    observer = RecordingObserver()
    agent.tool_handler = SimpleNamespace(current_iteration=0)

    result = ExecutionLoop(agent, observer=observer).execute(message_id="msg-1")

    assert result["answer"] == "done"
    assert observer.calls[0][0] == "execution_loop"
    assert observer.calls[0][1]["agent"] == "DummyAgent"
    assert observer.calls[1][0] == "iteration"
    assert observer.calls[1][1] == 1


def test_tool_handler_uses_observer_for_tool_execution_and_context():
    agent = DummyAgent()
    observer = RecordingObserver()
    handler = ToolHandler(agent, agent.printer, observer=observer)

    result = handler._execute_tool("echo", {"text": "hello"})
    contextual_result = handler._execute_tool_with_context("ctx", "echo", {"text": "world"})

    assert result == {"success": True, "text": "hello"}
    assert contextual_result == {"success": True, "text": "world"}
    assert ("tool", "echo", {"text": "hello"}) in observer.calls
    assert ("attach_context", "ctx") in observer.calls
