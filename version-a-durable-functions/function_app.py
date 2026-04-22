import azure.functions as func
import azure.durable_functions as df
import json
import logging
from datetime import timedelta

app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# ----------------- ACTIVITIES ----------------- #

@app.activity_trigger(input_name="expense")
def validate_expense(expense: dict) -> dict:
    required_fields = ["employeeName", "employeeEmail", "amount", "category", "description", "managerEmail"]
    valid_categories = ["travel", "meals", "supplies", "equipment", "software", "other"]

    # Check for missing fields
    for field in required_fields:
        if field not in expense or expense[field] is None:
            return {"isValid": False, "error": f"Missing required field: {field}"}

    # Check validity of category
    if str(expense.get("category")).lower() not in valid_categories:
        return {"isValid": False, "error": f"Invalid category. Must be one of: {', '.join(valid_categories)}"}
    
    # Check amount as a number
    try:
        amount = float(expense.get("amount"))
        if amount <= 0:
            return {"isValid": False, "error": "Amount must be strictly positive."}
    except ValueError:
        return {"isValid": False, "error": "Amount must be a valid number."}

    return {"isValid": True}

@app.activity_trigger(input_name="processingData")
def process_expense(processingData: dict) -> str:
    # Simulates saving the expense state to a database
    expense = processingData.get("expense")
    outcome = processingData.get("outcome")
    logging.info(f"Processing expense {expense.get('description')} with outcome: {outcome}")
    return outcome

@app.activity_trigger(input_name="notificationData")
def notify_employee(notificationData: dict) -> str:
    # Simulates sending an email to the employee
    employeeEmail = notificationData.get("employeeEmail")
    outcome = notificationData.get("outcome")
    logging.info(f"Sending email to {employeeEmail}: Your expense was {outcome}.")
    return f"Notified {employeeEmail} of outcome: {outcome}"

# ----------------- ORCHESTRATOR ----------------- #

@app.orchestration_trigger(context_name="context")
def expense_orchestrator(context: df.DurableOrchestrationContext):
    expense = context.get_input()
    
    # Step 1: Validation
    validation_result = yield context.call_activity("validate_expense", expense)
    if not validation_result.get("isValid"):
        return {"status": "Error", "message": validation_result.get("error")}

    amount = float(expense.get("amount"))
    outcome = ""

    # Step 2: Auto-approve or Manager Approval
    if amount < 100:
        outcome = "approved"
    else:
        # Wait for manager approval or timeout (e.g., 2 minutes for testing)
        # In literal production this would be Days or Hours. Here we use 2 mins for demo purposes.
        due_time = context.current_utc_datetime + timedelta(minutes=2)
        approval_event = context.wait_for_external_event("ManagerApproval")
        timeout_task = context.create_timer(due_time)

        # Wait for either the approval or the timeout
        winner = yield context.task_any([approval_event, timeout_task])

        if winner == approval_event:
            # We got a response from the manager
            manager_decision = approval_event.result
            if manager_decision.lower() == "approve" or manager_decision.lower() == "approved":
                outcome = "approved"
            else:
                outcome = "rejected"
            timeout_task.cancel() # Cancel the timer
        else:
            # Timeout happened first
            outcome = "escalated"

    # Step 3: Processing
    yield context.call_activity("process_expense", {"expense": expense, "outcome": outcome})

    # Step 4: Notification
    notification_result = yield context.call_activity("notify_employee", {
        "employeeEmail": expense.get("employeeEmail"),
        "outcome": outcome
    })

    return {
        "status": "Completed",
        "outcome": outcome,
        "notification": notification_result
    }

# ----------------- HTTP CLIENTS ----------------- #

@app.route(route="submitExpense")
@app.durable_client_input(client_name="client")
async def submit_expense_http(req: func.HttpRequest, client: df.DurableOrchestrationClient) -> func.HttpResponse:
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON payload.", status_code=400)

    instance_id = await client.start_new("expense_orchestrator", None, req_body)
    logging.info(f"Started orchestration with ID = '{instance_id}'.")
    return client.create_check_status_response(req, instance_id)

@app.route(route="managerDecision/{instanceId}")
@app.durable_client_input(client_name="client")
async def manager_decision_http(req: func.HttpRequest, client: df.DurableOrchestrationClient) -> func.HttpResponse:
    instance_id = req.route_params.get("instanceId")
    try:
        req_body = req.get_json()
        decision = req_body.get("decision")
    except ValueError:
        return func.HttpResponse("Invalid JSON paylod. Expecting { 'decision': 'approve' | 'reject' }", status_code=400)
    
    if not decision:
         return func.HttpResponse("Missing 'decision' in body.", status_code=400)

    # Raise the external event to the orchestrator execution
    await client.raise_event(instance_id, "ManagerApproval", decision)
    
    return func.HttpResponse(f"Sent {decision} to instance {instance_id}.", status_code=202)
