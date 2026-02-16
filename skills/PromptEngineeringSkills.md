## Prompt Engineering Skills (Portable)

Use this doc when editing **system prompts** or **knowledge base** content for AI assistants (e.g. Vapi, voice agents, chatbots). Copy this file into any project or reference it so prompts stay minimal and effective.

---

## 0. Start with a structured, scalable voice prompt

Vapi’s prompting guidance recommends organizing prompts into clear sections (Identity, Style, Response Guidelines, Task), explicitly controlling turn-taking with `<wait for user response>`, and including simple error handling + tool instructions. Source: `https://docs.vapi.ai/prompting-guide`.

**Copy/paste template (voice-optimized):**

```md
[Identity]
You are <agent name>, a voice assistant for <company/product>. Your job is to <primary outcome>.

[Style]
- Keep responses under 3 sentences unless the user asks for detail.
- Use natural contractions and simple language. Avoid robotic phrases.
- Ask one question at a time.
- Keep the persona consistent. Do not mix conflicting style requirements.

[Response Guidelines]
- Confirm key details before finalizing actions (name, date, amount, address).
- Present at most 3 options at a time.
- Use clear date formatting (e.g., January 15, 2026).

[Tool Use]
- Use tools when you need up-to-date info or to take an action.
- Refer to tools by their exact names and provide required parameters.
- If the platform supports silent transfers/tool calls: when transferring/escalating, do not speak—just call the transfer/escalation tool.

[Error Handling]
- If the user’s answer is unclear, ask a single clarifying question.
- If you encounter a tool/system issue, apologize briefly and ask the user to repeat or offer an alternative path.

[Task]
0. Detect call direction:
   - If inbound: greet and ask how you can help.
   - If outbound: identify yourself/company, state purpose immediately, and confirm it's a good time.
1. Briefly greet the user and state how you can help (inbound) OR state purpose (outbound).
2. Ask for the minimum info needed for the request.
<wait for user response>
3. If required info is missing, ask for it.
<wait for user response>
4. Use the appropriate tool (if needed), then summarize the result.
5. Confirm next step or completion, then ask if there’s anything else.
```

---

## 0.5. Inbound vs. outbound calls (opening pattern)

Outbound calls need a different opening than inbound calls because **you’re interrupting them**. Keep the opener short and explicit.

- **Inbound (they called you)**:
  - Identify + offer help: “Thanks for calling <Company>. How can I help today?”
  - Ask the minimum info, then `<wait for user response>`.
- **Outbound (you called them)**:
  - Identify + purpose + permission: “Hi, this is <Name> from <Company>. I’m calling about <Reason>. Is now a bad time?”
  - If they’re busy: offer a quick reschedule option, then stop.
  - If they object: acknowledge, offer one concise alternative (or opt-out), then stop.

---

## 1. Keep the system prompt minimal (Target: ~800 tokens max)

- Put only **non-negotiable rules** and **role/tone** in the main system prompt.
- Long procedures, FAQs, and policies belong in the **Knowledge Base** (or tool descriptions), not in the prompt.
- A short prompt performs better: less dilution, less truncation risk, more capacity for tools and KB at runtime.
- **Target:** Aim for 600-800 tokens maximum for voice agents.

---

## 2. Critical rules first

- Place the most important rules at the **top** of the prompt (e.g. STOP rule, prohibited phrases, safety).
- Use **short bullets**, one idea per rule. Avoid long paragraphs.
- If the model must never do X, state it clearly and early.

---

## 3. Prefer KB for SOPs and reference content

- **System prompt:** Say *when* to use the KB (e.g. "Search the knowledge base for policies, procedures, and FAQs; follow the retrieved content").
- **Knowledge Base:** Hold full SOPs, step-by-step flows, policies, and long reference text.
- Do **not** duplicate KB content in the prompt. Reference it; don't repeat it.

---

## 4. Tool-centric behavior

- The prompt should define **when** to use which tool and **tone**; detailed "how" can live in **tool names/descriptions** and the KB.
- Keep tool-usage instructions concise. Let tool schemas and KB carry procedure detail.
- Add explicit **turn-taking** for voice flows (e.g. `<wait for user response>`) so the agent doesn’t monologue or skip steps.

---

## 4.5. Dynamic variables (LiquidJS): `{{ ... }}` and `customer.*`

Vapi supports dynamic variable substitution in prompts/messages using **LiquidJS** syntax (double curly braces). Source: `https://docs.vapi.ai/assistants/dynamic-variables` and API reference notes on `variableValues`.

### What variables are available?

- **Your custom variables**: anything you pass in `variableValues` can be referenced directly.
  - Example: if you provide `variableValues.name = "Sam"`, then `{{name}}` → `Sam`.
- **Reserved defaults**:
  - `customer` (object) is available by default, so `{{customer.number}}`, `{{customer.name}}`, etc.

### Common `customer.*` fields (from Vapi customer DTOs)

- `customer.number`
- `customer.name`
- `customer.email`
- `customer.externalId`
- `customer.extension`
- `customer.sipUri`
- (Some APIs also include number validation flags like `e164` / `numberE164CheckEnabled`.)

### Best practices (voice + safety)

- **Prefer stable, minimal variables**: use variables for facts that must be consistent (name, plan, appointment time), not long policy text.
- **Handle missing values**: many fields are optional, so guard them.

```md
{% if customer.name %}
Hello {{customer.name}}.
{% else %}
Hello there.
{% endif %}
```

- **Don’t read sensitive values by default**: avoid speaking full phone numbers/emails unless the user explicitly requests or it’s required; confirm before actions.
- **Use time/date formatting intentionally**: Vapi supports Liquid date formatting like
  `{{"now" | date: "%b %d, %Y, %I:%M %p", "America/New_York"}}`.
- **Keep it one-turn safe**: use variables to personalize the *current* step, then ask and wait.

---

## 4.8. Transfers & escalation (cold vs. warm vs. silent)

Transfers happen in every real project. Define the pattern in the prompt so the agent doesn’t ramble or confuse the user.

Vapi specifically supports **blind/cold** and **warm** transfer modes (plus variants) in its transfer configuration, and recommends **silent transfers** in the prompting guide. Sources: `https://docs.vapi.ai/api-reference/phone-numbers/list` (transfer modes) and `https://docs.vapi.ai/prompting-guide` (silent transfers).

- **Cold / blind transfer** (fast handoff):
  - Tell the user what will happen in one sentence, then transfer.
  - Example prompt rule: “If the user requests a human, say one short sentence (‘Okay, I’ll connect you now.’) then transfer.”
- **Warm transfer** (context given to the operator):
  - Collect the minimum context + generate a short summary for the operator (issue + account + urgency + desired outcome), then transfer.
  - If supported, wait for the operator to speak first before delivering the summary (prevents speaking over voicemail/IVR).
- **Silent transfer** (seamless UX):
  - If the platform supports it: **do not speak at all**; just call the transfer/escalation tool.

---

## 5. Avoid bloat when adding behavior

When adding new behavior (e.g. a new question, flow, or rule):

1. **First:** Can it live in the KB? If yes, add it there and add one short line in the prompt (e.g. "Before closing, ask how they heard about us and tag in CRM").
2. **Second:** Can it live in a tool description? If yes, update the tool schema; prompt only says when to call the tool.
3. **Last:** Only if it's a critical, non-negotiable rule that must never be forgotten, add a short bullet to the system prompt.

---

## 6. Few-shot examples

- Use 1–2 examples only where they materially change behavior.
- Keep examples short. In voice, long examples consume tokens and can hurt consistency.

---

### 6.1. Voice few-shot example (interruption + objection)

Keep this short; it’s here to *teach turn-taking and tone under pressure*.

```text
User (interrupts): Actually—hold on. I’m in a meeting. What is this about?
Assistant: Sorry—my bad. I’ll be quick. This is <Name> from <Company> about <Reason>. Is there a better time today, or should I call tomorrow?
<wait for user response>

User: I’m not interested.
Assistant: Got it. Before I go—should I mark you as “do not call,” or would you prefer an email instead?
<wait for user response>
```

---

## 7. Voice-specific guidance

- **Keep responses brief:** Under 3 sentences unless customer asks for detail. Voice loses attention faster than text.
- **Speak naturally:** Use contractions ("I'll" not "I will"), casual tone, avoid robotic phrases.
- **Handle interruptions gracefully:** If customer interrupts, acknowledge and adjust to their new topic.
- **Confirm before finalizing:** Repeat key details back (name, phone, date) before completing actions.
- **Voice formatting:** Prefer speaking numbers naturally (and spell out numbers when it improves TTS), and avoid long lists.
- **Turn-taking:** Use `<wait for user response>` markers for multi-step flows so you don’t continue without the user.
- **Persona consistency:** Don’t combine conflicting requirements (e.g. “formal and professional” + “use slang and be casual”). Pick one persona and enforce it everywhere (system prompt, KB, and examples).

---

## 8. Iterate with a success-rate mindset (design → test → refine)

- **Design:** Write the smallest prompt that can reliably do the job.
- **Test:** Run realistic calls across all branches (happy path + edge cases).
- **Refine:** Tighten wording, add missing constraints, remove bloat.
- **Repeat:** Track improvements over time.

**Metrics to track:**

- **Success rate:** % of requests completed end-to-end without human intervention.
- **Conversation quality:** correctness, relevance, and whether it waits/asks at the right times.
- **UX:** naturalness, brevity, and whether confirmations prevent mistakes.

---

## 9. Checklist before shipping prompt changes

- [ ] No long procedures pasted into the prompt; they're in KB or tool descriptions.
- [ ] Critical rules (safety, prohibited phrases, STOP rule) are at the top and concise.
- [ ] One idea per bullet; no dense paragraphs.
- [ ] New behavior added via KB or tool first; prompt only references or gives a single short instruction.
- [ ] Prompt is under 800 tokens (check with token counter).
- [ ] No duplicate content between prompt and KB.
- [ ] Voice-specific guidance applied (brevity, natural language).
- [ ] Call direction is handled (inbound vs outbound opener is correct for the scenario).
- [ ] Turn-taking is explicit in multi-step flows (`<wait for user response>`).
- [ ] Error-handling is present (unclear input → clarify; tool failure → retry/alternate/escalate).
- [ ] Tool usage is unambiguous (exact tool names + required parameters).
- [ ] Transfer/escalation behavior is defined (cold vs warm vs silent; what to say, what to send, what tool to call).
- [ ] Persona requirements are internally consistent (no conflicting tone/style instructions).

---

## 10. Red flags (prompt is too long)

- More than 1,000 tokens total
- Duplicate content from KB
- Step-by-step procedures in prompt
- Lists of data (pricing, hours, service areas)
- Long examples (>5 lines each)
- "Instructions" for every possible scenario

---

## Reuse across projects

- Copy this file into `skills/` or `doc/` in any repo, or keep it in a shared folder (e.g. `~/Developer/skills/`).
- In Cursor, reference it when working on prompts (e.g. open the file or @-mention it), or add a per-project rule that says: "When editing system prompts or KB, follow the guidelines in `skills/PromptEngineeringSkills.md`."