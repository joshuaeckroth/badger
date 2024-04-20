from dash import Dash, html, dcc, callback, Output, Input
import plotly.express as px
import dash_bootstrap_components as dbc
import logging
import datetime

log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)

class Loan:
    def __init__(self, loan_name, remaining_amount, annual_rate, term_months):
        self.loan_name = loan_name
        self.remaining_amount = remaining_amount
        self.annual_rate = annual_rate
        self.remaining_term_months = term_months

    def baseline_monthly_payment(self):
        monthly_rate = self.annual_rate / 12
        return self.remaining_amount * monthly_rate / (1 - (1 + monthly_rate) ** -self.remaining_term_months)

    def amortization_schedule(self, additional_payment):
        schedule = []
        remaining_amount = self.remaining_amount
        for i in range(self.remaining_term_months):
            interest_payment = remaining_amount * self.annual_rate / 12
            principal_payment = self.baseline_monthly_payment() - interest_payment + additional_payment
            remaining_amount -= principal_payment
            # detect overpayment
            if remaining_amount < 0:
                principal_payment += remaining_amount
                additional_payment = max(0, additional_payment + remaining_amount)
                remaining_amount = 0
            schedule.append((i + 1, principal_payment + interest_payment, interest_payment, principal_payment, additional_payment, remaining_amount))
            # stop if loan is paid off
            if remaining_amount == 0:
                break
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


app = Dash(
        "Badger",
        external_stylesheets=[dbc.themes.CERULEAN],
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"},
            ],
        )
app.title = "Badger"

app.layout = dbc.Container([
    html.H1("Badger"),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Car Loan"),
                    dbc.Form([
                        dbc.Row([
                            dbc.Col(
                                dbc.InputGroup(
                                    [
                                        dbc.InputGroupText("Loan amount"),
                                        dbc.Input(type="number", id="loan_amount", value=100000, min=0),
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
                                        dbc.Input(type="number", id="annual_rate", value=3.5, min=0),
                                        dbc.InputGroupText("%"),
                                        ],
                                    className="mb-3",
                                    ),
                                ),
                            dbc.Col(
                                dbc.InputGroup(
                                    [
                                        dbc.InputGroupText("Term"),
                                        dbc.Input(type="number", id="term", value=36, min=1),
                                        dbc.InputGroupText("months"),
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
                                        dbc.Input(type="number", id="additional_payment", value=0, min=0),
                                        dbc.InputGroupText("$"),
                                        ],
                                    className="mb-3",
                                    ),
                                ),
                        ]),
                    ]),
                    dbc.Row([dbc.Col(html.Div(id="output"))]),
                ]),
            ]),
        ], width=6),
    ]),
])


@app.callback(
    Output("output", "children"),
    Input("loan_amount", "value"),
    Input("annual_rate", "value"),
    Input("term", "value"),
    Input("additional_payment", "value"),
)
def calculate(loan_amount, annual_rate, term, additional_payment):
    if loan_amount is None or annual_rate is None or term is None or additional_payment is None:
        return None
    try:
        loan = Loan('Loan 1', loan_amount, annual_rate/100.0, term)
        monthly_payment = loan.baseline_monthly_payment()
        total_payment = loan.total_payment(additional_payment)
        total_interest = loan.total_interest(additional_payment)
        (payoff_date, months) = loan.payoff_date(additional_payment)
        amortization_schedule = loan.amortization_schedule(additional_payment)
        return html.Div([
            dbc.Table([
                html.Thead(html.Tr([html.Th('Monthly payment'), html.Th('Total payment'), html.Th('Total interest'), html.Th('Payoff date')])),
                html.Tbody([html.Tr([html.Td(f'${monthly_payment:,.2f}'), html.Td(f'${total_payment:,.2f}'), html.Td(f'${total_interest:,.2f}'), html.Td(payoff_date)])]),
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

if __name__ == "__main__":
    app.run_server(debug=True, dev_tools_silence_routes_logging=False)

