import dash
from dash import Dash, html, dcc, callback, Output, Input, State
import plotly.express as px
import dash_bootstrap_components as dbc
import logging
import datetime
import json
import uuid

log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)

def save_user_data(data):
    with open('user_data.json', 'w') as f:
        json.dump(data, f)

def load_user_data():
    try:
        with open('user_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'loans': {}}

user_data = load_user_data()

class Loan:
    def __init__(self, remaining_amount, annual_rate, monthly_payment):
        self.remaining_amount = remaining_amount
        self.annual_rate = annual_rate
        self.monthly_payment = monthly_payment

    def amortization_schedule(self, additional_payment):
        schedule = []
        remaining_amount = self.remaining_amount
        i = 0
        while remaining_amount > 0 and i < 1000:
            interest_payment = remaining_amount * self.annual_rate / 12
            principal_payment = self.monthly_payment - interest_payment + additional_payment
            remaining_amount -= principal_payment
            # detect overpayment
            if remaining_amount < 0:
                principal_payment += remaining_amount
                additional_payment = max(0, additional_payment + remaining_amount)
                remaining_amount = 0
            schedule.append((i + 1, principal_payment + interest_payment, interest_payment, principal_payment, additional_payment, remaining_amount))
            i += 1
        return schedule

    def total_payment(self, additional_payment):
        return sum(payment for _, payment, _, _, _, _, in self.amortization_schedule(additional_payment))

    def total_interest(self, additional_payment):
        return sum(interest for _, _, interest, _, _, _, in self.amortization_schedule(additional_payment))

    def payoff_date(self, additional_payment):
        for month, _, _, _, _, remaining in self.amortization_schedule(additional_payment):
            if remaining <= 0.01:
                return ((datetime.date.today() + datetime.timedelta(days=30 * month)).strftime('%Y-%m'), month)
        return (None, None)

def create_loan_card(loan_id, loan_name=None, loan_amount=10000, annual_rate=7.5, monthly_payment=1000, additional_payment=0):
    return dbc.Col([
        dbc.Card([
            dbc.CardBody([
                dbc.Form([
                    dbc.Input(type="hidden", value=loan_id, id={"type": "loan_id", "index": loan_id}),
                    dbc.Row([
                        dbc.Col([
                            dbc.FormFloating([
                                dbc.Input(type="text", placeholder="Loan name", size="lg", value=loan_name, id={"type": "loan_name", "index": loan_id}),
                                dbc.Label("Loan name"),
                                ],
                                className="mb-3",
                            ),
                        ], width=11),
                        dbc.Col([
                            dbc.Button([html.I(className="fas fa-trash-alt fs-2")], color="link", id={"type": "delete_loan", "index": loan_id}),
                        ], width="1")
                    ]),
                    dbc.Row([
                        dbc.Col(
                            dbc.InputGroup(
                                [
                                    dbc.InputGroupText("Loan amount"),
                                    dbc.Input(type="number", value=loan_amount, min=0, id={"type": "loan_amount", "index": loan_id}),
                                    dbc.InputGroupText("$"),
                                    ],
                                className="mb-3",
                                ),
                            ),
                    ]),
                    dbc.Row([
                        dbc.Col(
                            dbc.InputGroup(
                                [
                                    dbc.InputGroupText("APR"),
                                    dbc.Input(type="number", value=annual_rate, min=0, id={"type": "annual_rate", "index": loan_id}),
                                    dbc.InputGroupText("%"),
                                    ],
                                className="mb-3",
                                ),
                            ),
                        dbc.Col(
                            dbc.InputGroup(
                                [
                                    dbc.InputGroupText("Monthly payment"),
                                    dbc.Input(type="number", value=monthly_payment, min=0, id={"type": "monthly_payment", "index": loan_id}),
                                    dbc.InputGroupText("$"),
                                    ],
                                className="mb-3",
                                ),
                            ),
                    ]),
                    dbc.Row([
                        dbc.Col(
                            dbc.InputGroup(
                                [
                                    dbc.InputGroupText("Additional payment"),
                                    dbc.Input(type="number", value=additional_payment, min=0, id={"type": "additional_payment", "index": loan_id}),
                                    dbc.InputGroupText("$"),
                                    ],
                                className="mb-3",
                                ),
                            ),
                    ]),
                ]),
                dbc.Row([dbc.Col(html.Div(id={"type": "output", "index": loan_id}))]),
            ]),
        ]),
    ], width=6, className="mb-3")

app = Dash(
        "Badger",
        external_stylesheets=[dbc.themes.CERULEAN, dbc.icons.FONT_AWESOME],
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"},
            ],
        #suppress_callback_exceptions=True
        )
app.title = "Badger"

@app.callback(
    Output({"type": "output", "index": dash.dependencies.MATCH}, "children"),
    Input({"type": "loan_id", "index": dash.dependencies.MATCH}, "value"),
    Input({"type": "loan_name", "index": dash.dependencies.MATCH}, "value"),
    Input({"type": "loan_amount", "index": dash.dependencies.MATCH}, "value"),
    Input({"type": "annual_rate", "index": dash.dependencies.MATCH}, "value"),
    Input({"type": "monthly_payment", "index": dash.dependencies.MATCH}, "value"),
    Input({"type": "additional_payment", "index": dash.dependencies.MATCH}, "value"),
)
def update_loan(loan_id, loan_name, loan_amount, annual_rate, monthly_payment, additional_payment):
    if loan_id is None or loan_name is None or loan_name == '' or loan_amount is None or annual_rate is None or monthly_payment is None or additional_payment is None:
        return None
    try:
        user_data['loans'][loan_id] = {
                'loan_name': loan_name,
                'loan_amount': loan_amount,
                'annual_rate': annual_rate,
                'monthly_payment': monthly_payment,
                'additional_payment': additional_payment
                }
        save_user_data(user_data)
        loan = Loan(loan_amount, annual_rate/100.0, monthly_payment)
        total_payment = loan.total_payment(additional_payment)
        total_interest = loan.total_interest(additional_payment)
        (payoff_date, months) = loan.payoff_date(additional_payment)
        amortization_schedule = loan.amortization_schedule(additional_payment)
        return html.Div([
            dbc.Table([
                html.Thead(html.Tr([html.Th('Total payment'), html.Th('Total interest'), html.Th('Payoff date')])),
                html.Tbody([html.Tr([html.Td(f'${total_payment:,.2f}'), html.Td(f'${total_interest:,.2f}'), html.Td(payoff_date)])]),
            ]),
            html.Div([
                dbc.Accordion([
                    dbc.AccordionItem([
                        dbc.Table([
                            html.Thead(html.Tr([html.Th('Month'), html.Th('Payment'), html.Th('Interest'), html.Th('Principal'), html.Th('Additional'), html.Th('Remaining')])),
                            html.Tbody(
                                [html.Tr([html.Td(month), html.Td(f'${payment:,.2f}'), html.Td(f'${interest:,.2f}'), html.Td(f'${principal:,.2f}'), html.Td(f'${additional:,.2f}'), html.Td(f'${remaining:,.2f}')]) for \
                                        month, payment, interest, principal, additional, remaining in amortization_schedule],
                            ),
                        ]),
                    ], title='Amortization schedule'),
                ], start_collapsed=True),
            ]),
        ])
    except Exception as e:
        logging.exception(e)
        return html.Div(f'Error: {e}')

@callback(
    Output("loan_cards", "children"),
    Input("add_loan", "n_clicks"),
    State("loan_cards", "children"),
)
def add_loan(n_clicks, children):
    if n_clicks is None or n_clicks == 0:
        return dash.no_update
    loan_id = str(uuid.uuid4())
    user_data['loans'][loan_id] = {
            'loan_name': '',
            'loan_amount': 0,
            'annual_rate': 0,
            'monthly_payment': 0,
            'additional_payment': 0
            }
    children.insert(0, create_loan_card(loan_id))
    return children

@callback(
    Output("loan_cards", "children", allow_duplicate=True),
    Input({"type": "delete_loan", "index": dash.dependencies.ALL}, "n_clicks"),
    prevent_initial_call=True
)
def delete_loan(n_clicks):
    ctx = dash.callback_context
    if ctx.triggered[0]['value'] is None:
        return dash.no_update
    loan_id = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])['index']
    if loan_id not in user_data['loans']:
        return dash.no_update
    del user_data['loans'][loan_id]
    save_user_data(user_data)
    return [create_loan_card(loan_id, **loan) for loan_id, loan in user_data['loans'].items()]

def get_layout():
    user_data = load_user_data()
    return dbc.Container([
        html.H1("Badger"),
        dbc.Button("Add loan", id="add_loan", n_clicks=0, className="mb-3"),
        dbc.Row(id="loan_cards", children=[create_loan_card(loan_id, **loan) for loan_id, loan in user_data['loans'].items()]),
    ])

app.layout = get_layout

if __name__ == "__main__":
    app.run_server(debug=True, dev_tools_silence_routes_logging=False)

