import json
from collections.abc import AsyncIterable, AsyncIterator, Iterable, Iterator
from typing import cast
from uuid import uuid4

from ag_ui.core import (
    AssistantMessage,
    DeveloperMessage,
    Event,
    FunctionCall,
    Message,
    ReasoningEndEvent,
    ReasoningMessage,
    ReasoningMessageContentEvent,
    ReasoningMessageEndEvent,
    ReasoningMessageStartEvent,
    ReasoningStartEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCall,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
    ToolMessage,
    UserMessage,
)
from agents import (
    RawResponsesStreamEvent,
    RunItemStreamEvent,
    StreamEvent,
    ToolCallOutputItem,
)
from openai.types.responses import (
    EasyInputMessageParam,
    ResponseFunctionCallArgumentsDeltaEvent,
    ResponseFunctionToolCall,
    ResponseFunctionToolCallParam,
    ResponseInputItemParam,
    ResponseOutputItemAddedEvent,
    ResponseOutputItemDoneEvent,
    ResponseOutputMessage,
    ResponseOutputMessageParam,
    ResponseReasoningItem,
    ResponseReasoningItemParam,
    ResponseReasoningSummaryTextDeltaEvent,
    ResponseStreamEvent,
    ResponseTextDeltaEvent,
)
from openai.types.responses.response_input_item_param import (
    FunctionCallOutput,
)

from app.models import AgentMessages


def to_ag_ui_messages(messages: Iterable[AgentMessages]) -> list[Message]:
    return [
        ag_ui_message
        for message in messages
        if (ag_ui_message := to_ag_ui_message(message)) is not None
    ]


def to_ag_ui_message(message: AgentMessages) -> Message | None:
    input_item: ResponseInputItemParam = json.loads(message.message_data)
    if "type" in input_item:
        return _type_input_item_to_ag_ui_message(input_item, message)
    else:
        return _to_ag_ui_user_message(cast(EasyInputMessageParam, input_item), message)


def _type_input_item_to_ag_ui_message(
    input_item: ResponseInputItemParam,
    message: AgentMessages,
) -> Message | None:
    match input_item["type"]:
        case "reasoning":
            return _to_ag_ui_reasoning_message(
                cast(ResponseReasoningItemParam, input_item),  # type: ignore[redundant-cast]
                message,
            )
        case "function_call":
            return _to_ag_ui_function_call_message(
                cast(ResponseFunctionToolCallParam, input_item),  # type: ignore[redundant-cast]
                message,
            )
        case "function_call_output":
            return _to_ag_ui_function_call_output_message(
                cast(FunctionCallOutput, input_item),  # type: ignore[redundant-cast]
                message,
            )
        case "message":
            return _role_input_item_to_ag_ui_message(
                cast(EasyInputMessageParam, input_item),
                message,
            )
        case _:
            return None


def _role_input_item_to_ag_ui_message(
    input_item: EasyInputMessageParam,
    message: AgentMessages,
) -> Message | None:
    match input_item["role"]:
        case "assistant":
            return _to_ag_ui_assistant_message(
                cast(ResponseOutputMessageParam, input_item),
                message,
            )
        case "developer":
            return _to_ag_ui_developer_message(input_item, message)
        case _:
            return None


def _to_ag_ui_reasoning_message(
    item: ResponseReasoningItemParam,
    message: AgentMessages,
) -> ReasoningMessage:
    return ReasoningMessage(
        id=str(message.id),
        content="".join(summary["text"] for summary in item["summary"]),
    )


def _to_ag_ui_function_call_message(
    item: ResponseFunctionToolCallParam,
    message: AgentMessages,
) -> AssistantMessage:
    return AssistantMessage(
        id=str(message.id),
        tool_calls=[
            ToolCall(
                id=item["call_id"],
                function=FunctionCall(
                    name=item["name"],
                    arguments=item["arguments"],
                ),
            )
        ],
    )


def _to_ag_ui_function_call_output_message(
    item: FunctionCallOutput,
    message: AgentMessages,
) -> ToolMessage | None:
    if not isinstance(item["output"], str):
        return None

    return ToolMessage(
        id=str(message.id),
        content=item["output"],
        tool_call_id=item["call_id"],
    )


def _to_ag_ui_developer_message(
    item: EasyInputMessageParam,
    message: AgentMessages,
) -> DeveloperMessage | None:
    if not isinstance(item["content"], str):
        return None

    return DeveloperMessage(id=str(message.id), content=item["content"])


def _to_ag_ui_user_message(
    item: EasyInputMessageParam,
    message: AgentMessages,
) -> UserMessage | None:
    content = item["content"]
    if not isinstance(content, str):
        return None

    return UserMessage(id=str(message.id), content=content)


def _to_ag_ui_assistant_message(
    item: ResponseOutputMessageParam,
    message: AgentMessages,
) -> AssistantMessage:
    return AssistantMessage(
        id=str(message.id),
        content="".join(
            [
                content["text"]
                for content in item["content"]
                if content["type"] == "output_text"
            ]
        ),
    )


async def to_ag_ui_stream(
    thread_id: str,
    stream_event: AsyncIterable[StreamEvent],
) -> AsyncIterator[Event]:

    run_id = f"run_{uuid4().hex}"
    tool_call_ids: dict[int, str] = {}

    yield RunStartedEvent(thread_id=thread_id, run_id=run_id)

    async for event in stream_event:
        match event:
            case RawResponsesStreamEvent(data=data):
                for ag_ui_event in _response_to_ag_ui_events(data, tool_call_ids):
                    yield ag_ui_event
            case RunItemStreamEvent():
                for ag_ui_event in _run_item_to_ag_ui_events(event):
                    yield ag_ui_event

    yield RunFinishedEvent(thread_id=thread_id, run_id=run_id)


def _response_to_ag_ui_events(
    event: ResponseStreamEvent,
    tool_call_ids: dict[int, str],
) -> Iterator[Event]:
    match event:
        case ResponseOutputItemAddedEvent(item=ResponseReasoningItem() as item):
            yield _to_ag_ui_reasoning_start_event(item)
            yield _to_ag_ui_reasoning_message_start_event(item)

        case ResponseReasoningSummaryTextDeltaEvent() as event:
            yield _to_ag_ui_reasoning_message_content_event(event)

        case ResponseOutputItemDoneEvent(item=ResponseReasoningItem() as item):
            yield _to_ag_ui_reasoning_message_end_event(item)
            yield _to_ag_ui_reasoning_end_event(item)

        case ResponseOutputItemAddedEvent(
            output_index=output_index,
            item=ResponseFunctionToolCall() as item,
        ):
            tool_call_ids[output_index] = item.call_id
            yield _to_ag_ui_tool_call_start_event(item)

        case ResponseFunctionCallArgumentsDeltaEvent(output_index=output_index):
            tool_call_id = tool_call_ids.get(output_index)
            if tool_call_id is not None:
                yield _to_ag_ui_tool_args_event(event, tool_call_id)

        case ResponseOutputItemAddedEvent(item=ResponseOutputMessage() as item):
            yield _to_ag_ui_text_message_start_event(item)

        case ResponseTextDeltaEvent() as event:
            yield _to_ag_ui_text_message_content_event(event)

        case ResponseOutputItemDoneEvent(item=ResponseOutputMessage() as item):
            yield _to_ag_ui_text_message_end_event(item)


def _run_item_to_ag_ui_events(run_item: RunItemStreamEvent) -> Iterator[Event]:
    match run_item:
        case RunItemStreamEvent(
            item=ToolCallOutputItem(
                raw_item={
                    "type": "function_call_output",
                    "call_id": str(call_id),
                    "output": str(output),
                }
            )
        ):
            yield _to_ag_ui_tool_call_end_event(call_id)
            yield _to_ag_ui_tool_result_event(call_id, output)


def _to_ag_ui_reasoning_start_event(item: ResponseReasoningItem) -> ReasoningStartEvent:
    return ReasoningStartEvent(message_id=item.id)


def _to_ag_ui_reasoning_message_start_event(
    item: ResponseReasoningItem,
) -> ReasoningMessageStartEvent:
    return ReasoningMessageStartEvent(message_id=item.id, role="reasoning")


def _to_ag_ui_reasoning_message_content_event(
    event: ResponseReasoningSummaryTextDeltaEvent,
) -> ReasoningMessageContentEvent:
    return ReasoningMessageContentEvent(message_id=event.item_id, delta=event.delta)


def _to_ag_ui_reasoning_message_end_event(
    item: ResponseReasoningItem,
) -> ReasoningMessageEndEvent:
    return ReasoningMessageEndEvent(message_id=item.id)


def _to_ag_ui_reasoning_end_event(item: ResponseReasoningItem) -> ReasoningEndEvent:
    return ReasoningEndEvent(message_id=item.id)


def _to_ag_ui_tool_call_start_event(
    item: ResponseFunctionToolCall,
) -> ToolCallStartEvent:
    return ToolCallStartEvent(
        tool_call_id=item.call_id,
        tool_call_name=item.name,
    )


def _to_ag_ui_tool_args_event(
    event: ResponseFunctionCallArgumentsDeltaEvent,
    tool_call_id: str,
) -> ToolCallArgsEvent:
    return ToolCallArgsEvent(tool_call_id=tool_call_id, delta=event.delta)


def _to_ag_ui_tool_call_end_event(tool_call_id: str) -> ToolCallEndEvent:
    return ToolCallEndEvent(tool_call_id=tool_call_id)


def _to_ag_ui_tool_result_event(
    tool_call_id: str,
    content: str,
) -> ToolCallResultEvent:
    return ToolCallResultEvent(
        message_id=f"msg_{uuid4().hex}",
        tool_call_id=tool_call_id,
        content=content,
    )


def _to_ag_ui_text_message_start_event(
    item: ResponseOutputMessage,
) -> TextMessageStartEvent:
    return TextMessageStartEvent(message_id=item.id)


def _to_ag_ui_text_message_content_event(
    event: ResponseTextDeltaEvent,
) -> TextMessageContentEvent:
    return TextMessageContentEvent(message_id=event.item_id, delta=event.delta)


def _to_ag_ui_text_message_end_event(
    item: ResponseOutputMessage,
) -> TextMessageEndEvent:
    return TextMessageEndEvent(message_id=item.id)
