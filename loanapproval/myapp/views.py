import os

from django.shortcuts import render
import requests

# ===========================
# IBM Cloud Credentials
# ===========================
# Keep these secrets out of source control. Set them in your environment
# or in a local .env file that is ignored by Git.

API_KEY = os.getenv("IBM_API_KEY")
DEPLOYMENT_URL = os.getenv("IBM_DEPLOYMENT_URL")


def home(request):

    result = ""
    probability = None

    def parse_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def parse_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    if request.method == "POST":

        # Get form data
        loan_id = request.POST.get("loan_id", "LP000000")
        gender = request.POST.get("gender")
        married = request.POST.get("married")
        dependents = parse_int(request.POST.get("dependents"))
        education = request.POST.get("education")
        self_employed = request.POST.get("self")
        applicant_income = parse_int(request.POST.get("income"))
        coapplicant_income = parse_float(request.POST.get("coincome"))
        loan_amount = parse_float(request.POST.get("loanamount"))
        loan_term = parse_float(request.POST.get("term"))
        credit_history = parse_float(request.POST.get("credit"))
        property_area = request.POST.get("property")

        if coapplicant_income is None:
            coapplicant_income = 0.0

        probability = None

        def local_predict(
            gender,
            married,
            dependents,
            education,
            self_employed,
            applicant_income,
            coapplicant_income,
            loan_amount,
            loan_term,
            credit_history,
            property_area,
        ):
            score = 0
            if credit_history == 1.0:
                score += 2
            if applicant_income >= 5000:
                score += 1
            if loan_amount <= 200:
                score += 1
            if married == "Yes":
                score += 1
            if education == "Graduate":
                score += 1
            if self_employed == "No":
                score += 1
            if property_area == "Urban":
                score += 1
            if dependents == 0:
                score += 1
            if loan_term >= 360:
                score += 1
            if applicant_income == 0:
                score -= 2
            return "Y" if score >= 3 else "N"

        if None in (dependents, applicant_income, loan_amount, loan_term, credit_history):
            result = "Please fill in all required numeric fields."
        else:
            # Fail fast when IBM credentials are not configured to avoid obscure KeyErrors
            if not API_KEY or not DEPLOYMENT_URL:
                result = "Server misconfigured: missing IBM_API_KEY or IBM_DEPLOYMENT_URL"
                return render(request, "index.html", {"result": result, "probability": probability})

            try:

                # ===========================
                # Generate IBM IAM Token
                # ===========================

                token_response = requests.post(
                    "https://iam.cloud.ibm.com/identity/token",
                    data={
                        "apikey": API_KEY,
                        "grant_type": "urn:ibm:params:oauth:grant-type:apikey"
                    }
                )

                token_json = token_response.json()

                print("TOKEN RESPONSE:")
                print(token_json)

                mltoken = token_json["access_token"]

                headers = {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + mltoken
                }

                # ===========================
                # Payload
                # ===========================

                payload = {
                    "input_data": [
                        {
                            "fields": [
                                "Loan_ID",
                                "Gender",
                                "Married",
                                "Dependents",
                                "Education",
                                "Self_Employed",
                                "ApplicantIncome",
                                "CoapplicantIncome",
                                "LoanAmount",
                                "Loan_Amount_Term",
                                "Credit_History",
                                "Property_Area"
                            ],
                            "values": [[
                                loan_id,
                                gender,
                                married,
                                dependents,
                                education,
                                self_employed,
                                applicant_income,
                                coapplicant_income,
                                loan_amount,
                                loan_term,
                                credit_history,
                                property_area
                            ]]
                        }
                    ]
                }

                print("\nPayload:")
                print(payload)

                # ===========================
                # Call Deployment
                # ===========================

                response = requests.post(
                    DEPLOYMENT_URL,
                    headers=headers,
                    json=payload
                )

                print("\nStatus Code:")
                print(response.status_code)

                print("\nResponse Text:")
                print(response.text)

                prediction = response.json()

                print("\nPrediction JSON:")
                print(prediction)

                # ===========================
                # Read Prediction
                # ===========================

                output = None
                probability = None
                if response.ok and "predictions" in prediction:
                    values = prediction["predictions"][0]["values"][0]
                    if isinstance(values, list) and len(values) >= 1:
                        output = values[0]
                        if len(values) > 1:
                            probability = values[1]
                    else:
                        output = values

                if output == "Y":
                    result = "Loan Approved"
                elif output == "N":
                    result = "Loan Rejected"
                else:
                    raise ValueError("Invalid prediction response")

            except Exception as e:

                print("\nERROR:")
                print(e)
                print("Falling back to local prediction")

                probability = None
                fallback_output = local_predict(
                    gender,
                    married,
                    dependents,
                    education,
                    self_employed,
                    applicant_income,
                    coapplicant_income,
                    loan_amount,
                    loan_term,
                    credit_history,
                    property_area,
                )
                if fallback_output == "Y":
                    result = "Loan Approved (local prediction)"
                else:
                    result = "Loan Rejected (local prediction)"

    return render(request, "index.html", {"result": result, "probability": probability})