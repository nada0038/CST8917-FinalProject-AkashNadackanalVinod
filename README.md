# CST8917 Final Project: Dual Implementation of an Expense Approval Workflow

### Name: Akash Nadackanal Vinod
### Student Number: 041156265
### Course Code: CST8917 - Serverless Applications | Winter 2026
### Project Title: Dual Implementation of an Expense Approval Workflow
### Date: 21 April 2026
### Demo Video
[YouTube](https://youtu.be/gRzD4zib_NM)
----

## 1. Version A Summary (Durable Functions)

**Brief Description:** 
Version A implements the code-first expense approval workflow using Azure Durable Functions (Python V2). The architecture relies on an HTTP-triggered client function which launches an Orchestrator. The orchestration relies heavily on activity chaining. 

**Design Decisions:**
- Handled validation via a separate activity function (`validate_expense`). If the payload fails validation, the workflow halts cleanly and returns an error payload without further state hydration.
- I implemented the Human Interaction pattern by making the code wait for either an external event (`ManagerApproval`) or a timeout timer (`context.create_timer`).
- I added an HTTP webhook `POST /api/managerDecision/{instanceId}` so I could easily pass the "approve" or "reject" decision into the paused function.

**Challenges:**
Understanding synchronous versus asynchronous Python generation patterns within the Orchestrator was tricky. Ensuring that I yielded all tasks and didn't attempt asynchronous I/O within the orchestrator itself (violating code constraints) caused early runtime errors. Mocking time out behaviors for local testing reliably using UTC times required strict debugging.

---

## 2. Version B Summary (Logic Apps + Service Bus)

**Brief Description:**
Version B tackles the exact same business logic but pivots to an event-driven, visual workflow utilizing cloud-native connectors. A Service Bus queue triggers the flow. Validation is heavily outsourced to a standard Azure Function HTTP endpoint, which prevents duplicating large Python conditional logic into discrete Logic App visual elements.

**Manager Approval Approach:**
For Manager Approval, the workflow utilizes the Office 365 Outlook connector's **"Send email with options"** action. This approach was highly optimal because the Logic App natively treats it as a webhook/callback loop. The Logic App visually "pauses" the run, sending HTML buttons directly to the manager's inbox. If the button click arrives, it processes the choice. I wrapped this step in a timeout setting (configurable on the connector's settings) so that if no response was captured within the bounds, the Logic App progresses to the "Escalated" branch. Finally, a Service Bus topic handles pub-sub routing for the resulting notification flags.

**Challenges:**
Testing the integration of Service Bus trigger bindings offline was exceedingly frustrating compared to purely HTTP-based functions. Constructing strict Service Bus Topic properties to trigger the Correct Subscriptions needed quite a bit of manual UI configuration on the Azure Portal, removing the ease of Infrastructure-as-code deployments.

---

## 3. Comparison Analysis

### 1. Development Experience
The development experience drastically differed depending on my comfort with IDEs versus GUI environments. Building the code-first Durable Functions implementation in Visual Studio Code was remarkably fluid. Because logic resided entirely in Python, I enjoyed the benefits of precise autocomplete, static linting, and rapid string manipulations. It felt like writing standard synchronous code. 

Logic Apps provided a lot of instant gratification. Getting the initial trigger and HTTP call working took way less time than configuring the local Azure storage emulators for the Python version. However, once the logic started getting complex with nested timeouts and passing variables around, the Logic App Canvas just turned into a mess of intersecting lines. Durable Functions gave me way more confidence in the code itself, whereas Logic Apps was much faster for simple setups.

### 2. Testability
Durable Functions clearly dominated testability. The capability to use the local Azure Functions Core Tools alongside a locally emulated Azurite storage instance meant I could execute end-to-end tests cleanly offline. Writing automated unit tests for Activity Functions using standard Python mock testing frameworks was remarkably straightforward because they are pure in-and-out mapping functions.

Logic Apps presented significant friction for automated testing. You cannot seamlessly unit-test a visually scoped designer block. Most testing effectively required live integration—dropping messages into a Live Azure Service Bus and checking the web portal to trace the outputs visually. It was highly dependent on live infrastructure and lacked easy local assertions.

### 3. Error Handling
Durable Functions offers granular, code-centric exception management. If my validation HTTP call failed, a traditional `try/except` block allowed me to cleanly isolate the failure, log deeply, or execute custom compensating transactions (Saga patterns) without cluttering the workflow. Furthermore, `CallActivityWithRetry` provided programmatic control over exponential backoff configurations.

Logic Apps rely heavily on "Configure Run After" behaviors. If an action fails, you can attach alternative actions to execute. While it visibly models flow control, wrapping large subsets of actions in "Scope" limits to catch aggregated faults gets incredibly messy visually. It lacks the surgical precision of customized exception handling you acquire natively through Python scripts.

### 4. Human Interaction Pattern
To implement a "Wait For Manager Approval" step, Durable Functions demanded abstract thinking. Firing an external event against an orchestrator ID required setting up a distinct incoming webhook API point, tracking the `instance_id`, resolving parallel tasks via `yield context.task_any`, and strictly resolving UTC time-checks for the timeout variable. It was conceptually powerful, but practically required writing overhead scaffolding.

On the other hand, Logic Apps made this part super easy using its built-in connectors. I used the "Send Email With Options" Office 365 tool, which automatically handles the webhook responses and correlation IDs in the background. It just drops clickable HTML buttons right into the manager's email. Setting up the human interaction part took barely any time compared to doing it in Python.

### 5. Observability
Observability provides interesting stark contrasts. Durable Functions outputs a heavy stream of technical logs into Application Insights. While powerful for tracking latency or analyzing cold starts via KQL queries, tracing the explicit "state" of one individual business workflow often requires matching obscure orchestrator IDs through tables to understand which step succeeded.

Logic Apps offers unparalleled visual observability. The "Run History" tool highlights success and failures on the exact graphical canvas where the app was built. Clicking an individual visual node immediately reveals exact raw inputs, outputs, and header responses associated with that distinct moment. For diagnosing high-level API failures visually to non-technical users, Logic Apps was infinitely superior.

### 6. Cost Evaluation
For a low-volume scenario approximating roughly 100 expenses processed a day, both platforms reside firmly inside the Azure Free Grants and operate for mere pennies. 

However, evaluating costs at a heavier scale (e.g., 10,000 requests per day equating to 300,000 runs a month) highlighted different cost anchors. Logic App Standard environments trigger minute costs per *action* metric. A workflow computing validation, database lookups, branching, and mailing could generate 10+ billed actions per run, sharply driving up connector costs via the consumption plan. In contrast, Durable Functions scale purely on Compute Time / Memory executions. Executing simple Python validation scripts is remarkably fast. Thus, while Durable orchestrators require background storage transactions that cost minor fractions, executing high throughput computation generally remains far cheaper and highly scalable strictly mathematically on pure code execution engines.

---

## 4. Recommendation

If entrusted by a team to select the architecture for a large-scale enterprise production pipeline, **I would decisively recommend building upon Azure Durable Functions (Version A).**

Enterprise environments prioritize version control, deployment pipelines (CI/CD), and rigorous automated testing. Code-first orchestration via Durable Functions maps seamlessly to mature Git branching logic and unit testing constraints. An engineering team can assert logic states aggressively offline inside CI pipelines before code ever hits production environments, reducing catastrophic regressions. Furthermore, as the application expands incrementally—say integrating complex integrations, specialized cryptography, or custom machine learning validations—writing Python extensions remains infinitely extensible compared to waiting for a vendor to support a specific third-party module logic connector.

However, I would alternatively choose **Logic Apps** purely in scenarios heavily dependent on third-party SaaS platforms involving "Citizen Developers". If the overarching goal is loosely coupling 20 different cloud SaaS APis (SalesForce, Service Now, Office 365, Slack) to sync data with no major data transformations involved, writing API wrappers manually is wasted developer effort. In environments where business analysts—not developers—maintain the flows visually, Logic Apps accelerates delivery with remarkable efficiency.

---

## 5. References
- Azure Functions Documentation, *Durable Functions Overview*: https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-overview
- Microsoft Learn, *Human interaction in Durable Functions*: https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-phone-verification
- Microsoft Learn, *Create automated workflows with Azure Logic Apps*: https://learn.microsoft.com/en-us/azure/logic-apps/

---
