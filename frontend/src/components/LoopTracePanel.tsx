import { buildLoopStory, type StoryPhase, type ToolSchema } from "../lib/loopStory";
import { formatMessageContent, type DebugMessage } from "../lib/formatMessage";
import type { AgentEvent } from "../types/protocol";

interface Props {
  events: AgentEvent[];
}

const PHASE_LABELS: Record<StoryPhase["kind"], string> = {
  prompt: "call_model — 请求拼装",
  think: "模型输出 · 思考",
  tool_call: "模型输出 · 工具调用",
  tool_result: "工具观察结果 (tool_result)",
  final: "本轮最终答复",
};

function ToolSchemasView({ schemas }: { schemas: ToolSchema[] }) {
  if (schemas.length === 0) {
    return <p className="muted">（本轮无 tools 参数，如 plan 阶段）</p>;
  }
  return (
    <ol className="story-tool-schemas">
      {schemas.map((schema) => (
        <li key={schema.name} className="story-tool-schema">
          <div className="story-tool-schema-head">
            <code>{schema.name}</code>
            <span className="story-hint">{schema.description}</span>
          </div>
          <pre className="story-pre">{JSON.stringify(schema.input_schema, null, 2)}</pre>
        </li>
      ))}
    </ol>
  );
}

function CallModelRequestView({
  messages,
  toolSchemas,
}: {
  messages: DebugMessage[];
  toolSchemas: ToolSchema[];
}) {
  const system = messages.find((message) => message.role === "system");
  const userContext = messages.filter((message) => message.role !== "system");

  return (
    <div className="call-model-request">
      <p className="story-call-desc">
        每次 <code>call_model</code> 向 LLM 发送两部分：<strong>messages[]</strong>（含 system +
        对话）与 <strong>tools[]</strong>（tool schema，独立 API 字段，不拼进 system 字符串）。
        会话在首次 <code>get_or_create_session</code> 时注入 system prompt；之后每轮 user
        turn 追加 user 消息，历史保留在 session 里作为 user context。
      </p>

      <div className="call-model-parts">
        <section className="call-model-part">
          <h4>① System prompt</h4>
          <p className="story-hint">session[0]，首次创建会话时写入，之后每轮复用</p>
          {system ? (
            <pre className="story-pre">{formatMessageContent(system, 2000)}</pre>
          ) : (
            <p className="muted">（无 system 消息）</p>
          )}
        </section>

        <section className="call-model-part">
          <h4>② User context（对话历史）</h4>
          <p className="story-hint">messages[1…]：user / assistant / tool_result 多轮上下文</p>
          {userContext.length === 0 ? (
            <p className="muted">（尚无对话，仅 system）</p>
          ) : (
            <ol className="story-message-list">
              {userContext.map((message, index) => (
                <li key={`${message.role}-${index}`} className={`story-msg story-msg-${message.role}`}>
                  <span className="story-msg-role">{message.role}</span>
                  <pre>{formatMessageContent(message)}</pre>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="call-model-part">
          <h4>③ Tool schemas（tools API 参数）</h4>
          <p className="story-hint">
            <code>build_tool_schemas(tools)</code> → 与 messages 并列传入，model 据此决定是否 tool_use
          </p>
          <ToolSchemasView schemas={toolSchemas} />
        </section>
      </div>
    </div>
  );
}

function PhaseBody({ phase }: { phase: StoryPhase }) {
  switch (phase.kind) {
    case "prompt":
      return <CallModelRequestView messages={phase.messages} toolSchemas={phase.toolSchemas} />;
    case "think":
      return <pre className="story-pre">{phase.content}</pre>;
    case "tool_call":
      return (
        <div className="story-tool-call">
          <p>
            工具 <code>{phase.toolName}</code>
            {phase.decision && <span className={`decision decision-${phase.decision}`}> · {phase.decision}</span>}
            {phase.permissionDecision && (
              <span className="story-hint"> · 用户权限: {phase.permissionDecision}</span>
            )}
          </p>
          <pre className="story-pre">{JSON.stringify(phase.toolInput, null, 2)}</pre>
        </div>
      );
    case "tool_result":
      return (
        <div className={`story-tool-result${phase.isError ? " is-error" : ""}`}>
          <p className="story-hint">
            {phase.toolName} → 写回 session 作为 user 侧的 tool_result，下一轮 call_model 会进入 user context
          </p>
          <pre className="story-pre">{phase.content}</pre>
        </div>
      );
    case "final":
      return <pre className="story-pre story-final">{phase.content}</pre>;
    default:
      return null;
  }
}

export function LoopTracePanel({ events }: Props) {
  if (events.length === 0) {
    return (
      <p className="muted">
        发送一条消息后，这里会按 agent loop 流程展示：用户输入 → 每轮 call_model → 工具 → 最终输出。
      </p>
    );
  }

  const story = buildLoopStory(events);

  return (
    <div className="loop-story">
      <div className="flow-diagram" aria-hidden>
        <span>用户输入</span>
        <span className="flow-arrow">→</span>
        <span>session += user</span>
        <span className="flow-arrow">→</span>
        <span>call_model</span>
        <span className="flow-arrow">→</span>
        <span>system + context + tools</span>
        <span className="flow-arrow">→</span>
        <span>工具/作答</span>
        <span className="flow-arrow">→</span>
        <span>最终输出</span>
      </div>

      <section className="story-section story-user">
        <h3>① 用户输入（本 turn 写入 session）</h3>
        <pre className="story-pre">{story.userMessage ?? "（未知）"}</pre>
      </section>

      {story.turns.map((turn) => (
        <section key={turn.turnIndex} className="story-section story-turn">
          <h3>
            ② Loop 第 {turn.turnIndex + 1} 轮
            <span className="story-hint">for turn_index in range(max_steps)</span>
          </h3>
          {turn.phases.length === 0 ? (
            <p className="muted">（本轮暂无步骤）</p>
          ) : (
            <ol className="story-phases">
              {turn.phases.map((phase, index) => (
                <li key={`${phase.kind}-${index}`} className={`story-phase story-phase-${phase.kind}`}>
                  <div className="story-phase-title">{PHASE_LABELS[phase.kind]}</div>
                  <PhaseBody phase={phase} />
                </li>
              ))}
            </ol>
          )}
        </section>
      ))}

      <section className="story-section story-output">
        <h3>③ 最终输出（run_finished）</h3>
        {story.error && <pre className="story-pre story-error">{story.error}</pre>}
        {story.finalAnswer ? (
          <pre className="story-pre story-final">{story.finalAnswer}</pre>
        ) : (
          !story.error && <p className="muted">等待 run 结束…</p>
        )}
        {story.sessionMessageCount != null && (
          <p className="story-hint">session 当前共 {story.sessionMessageCount} 条 messages</p>
        )}
      </section>

      <details className="story-raw">
        <summary>原始 WS 事件（高级调试）</summary>
        <pre>{JSON.stringify(events, null, 2)}</pre>
      </details>
    </div>
  );
}
