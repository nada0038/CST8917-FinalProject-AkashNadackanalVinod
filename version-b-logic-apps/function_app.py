import azure.functions as func
import logging
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="validate_expense")
def validate_expense(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function validate_expense processed a request.')

    try:
        expense = req.get_json()
    except ValueError:
        return func.HttpResponse(
             json.dumps({"isValid": False, "error": "Invalid JSON format"}),
             mimetype="application/json",
             status_code=400
        )

    required_fields = ["employeeName", "employeeEmail", "amount", "category", "description", "managerEmail"]
    valid_categories = ["travel", "meals", "supplies", "equipment", "software", "other"]

    # Check for missing fields
    for field in required_fields:
        if field not in expense or expense[field] is None:
            return func.HttpResponse(
                json.dumps({"isValid": False, "error": f"Missing required field: {field}"}),
                mimetype="application/json",
                status_code=400
            )

    # Check validity of category
    if str(expense.get("category")).lower() not in valid_categories:
        return func.HttpResponse(
            json.dumps({"isValid": False, "error": f"Invalid category. Must be one of: {', '.join(valid_categories)}"}),
            mimetype="application/json",
            status_code=400
        )

    # Check amount as a number
    try:
        amount = float(expense.get("amount"))
        if amount <= 0:
            return func.HttpResponse(
                json.dumps({"isValid": False, "error": "Amount must be strictly positive."}),
                mimetype="application/json",
                status_code=400
            )
    except ValueError:
        return func.HttpResponse(
            json.dumps({"isValid": False, "error": "Amount must be a valid number."}),
            mimetype="application/json",
            status_code=400
        )

    return func.HttpResponse(
        json.dumps({"isValid": True, "amount": amount}),
        mimetype="application/json",
        status_code=200
    )
