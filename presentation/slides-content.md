# Expense Approval Workflow Project - Presentation Slides Outline

*Copy and paste these notes into your PowerPoint slides.*

## Slide 1: Title Slide
**Title:** Dual Implementation of an Expense Approval Workflow
**Subtitle:** Serverless Orchestration: Code-First vs. Visual/Declarative
**Presenter:** [Your Name]
**Course:** CST8917 - Serverless Applications

---

## Slide 2: Introduction — The Workflow and Business Rules
**Content:**
- **Goal:** Implement an expense approval pipeline.
- **Inputs:** Employee details, amounts, categories, and descriptions.
- **Validation:** Must have required fields & valid categories (travel, meals, etc.).
- **Logic:**
  - < $100: Auto-Approved.
  - >= $100: Manager approval required.
- **Timeout:** Escalate to auto-approve if no manager response in 2 mins/hours.
- **Output:** Notification email to the employee with final status (Approved, Rejected, Escalated).

---

## Slide 3: Version A — Architecture (Durable Functions)
**Content:**
- **Model:** Azure Durable Functions (Python v2).
- **Core Components:**
  - HTTP Starter Client.
  - Orchestrator Function (`expense_orchestrator`).
  - Activity Functions (`validate_expense`, `process_expense`, `notify_employee`).
- **Human Interaction:** Implemented using `wait_for_external_event("ManagerApproval")` and a durable timer for the timeout.

---

## Slide 4: Version A — Key Design Decisions & Live Demo
**Content:**
- **Decision:** Used a dedicated HTTP endpoint (`/managerDecision/{instanceId}`) to easily fire external events to running instances.
- **Demo Focus:**
  - Show the 6 HTTP scenarios from `test-durable.http`.
  - Show parallel execution (Task.Any) between Manager Approval and Timeout.
- *(Switch to VS Code / Postman for Live Demo).*

---

## Slide 5: Version B — Architecture (Logic Apps + Service Bus)
**Content:**
- **Model:** Azure Logic Apps + Service Bus + Azure Functions (Validation).
- **Core Components:**
  - Service Bus Queue as the trigger.
  - Logic App handling condition trees and API integrations.
  - Standard Azure Function for payload validation.
  - Service Bus Topic for routing "Approved/Rejected/Escalated" messages.
  - Office 365 Connector for emailing employees.

---

## Slide 6: Version B — Key Design Decisions & Live Demo
**Content:**
- **Manager Approval Strategy:** Used Logic App "Send email with options" action. The Logic App natively pauses and waits for an action (Approve/Reject) from the email, configuring a timeout duration directly in the action's settings.
- **Demo Focus:**
  - Service Bus Explorer to drop an expense in the queue.
  - Visual run history showing the branching log.
- *(Switch to Azure Portal for Live Demo).*

---

## Slide 7: Comparison — Dimensions 1 & 2 (Experience & Testability)
**Content:**
- **Development Experience:**
  - *Durable Functions:* Fast for developers familiar with code. Version-controlled naturally. High confidence via local debugging.
  - *Logic Apps:* Drag-and-drop is fast for simple flows, but tracking down dynamic content variables was cumbersome.
- **Testability:**
  - *Durable Functions:* Excellent local testability. Python `unittest` mock frameworks work well on activities. Full offline simulation without Azure limits.
  - *Logic Apps:* Challenging to test offline. Heavy reliance on manual payload injection and checking the portal run history.

---

## Slide 8: Comparison — Dimensions 3 & 4 (Errors & Human Interaction)
**Content:**
- **Error Handling:**
  - *Durable:* Code-level try/except blocks and retry policies. Highly granular.
  - *Logic Apps:* "Configure run after" visual settings. Decent, but less flexible for complex cleanup logic.
- **Human Interaction Pattern:**
  - *Durable:* Worked well using `wait_for_external_event` and `create_timer`, but I had to build a custom API endpoint to trigger it.
  - *Logic Apps:* Very easy to set up with the "Send email with options" connector. Handled the email buttons and pausing automatically.

---

## Slide 9: Comparison — Dimensions 5 & 6 (Observability & Cost)
**Content:**
- **Observability:**
  - *Durable:* Relies heavily on Application Insights and reading text logs, which takes a bit more effort to trace.
  - *Logic Apps:* Really helpful visual run history. You can literally just look at the boxes to see what path was taken instantly.
- **Cost (Estimates):**
  - *100 expenses/day:* Both practically free (within free tier of Consumption / Logic App Standard).
  - *10,000 expenses/day:* Logic apps start costing per action executed (especially connectors), whereas Durable Functions scale effectively by execution time and memory footprint (generally cheaper at high scale).

---

## Slide 10: Recommendation
**Content:**
- **Verdict:** For complex, high-volume production systems, **Durable Functions** is recommended.
- **Reasoning:** Superior source control, unit testing patterns, and predictable cost at scale. Developers retain full control over state and error scenarios.
- **Alternative:** Choose **Logic Apps** if the workflow is built/maintained by business analysts or ops teams, or if it heavily relies on hundreds of 3rd party API connectors (where coding them manually would waste time).

---

## Slide 11: Lessons Learned
**Content:**
- Visual orchestration sounds simple but becomes a "spaghetti" of conditions when logic is complex.
- Implementing durable timers dynamically requires careful attention to UTC datetime conversions.
- The power of Service Bus topic filters significantly reduced orchestration overhead in Logic Apps.
