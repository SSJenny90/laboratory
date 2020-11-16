import dash_html_components as html
import dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_daq as daq
from dash.dependencies import Input, Output

from app import app, lab 

def flow_meter(id):
    return dbc.CardBody(id=id,
        children=[
            dbc.Card([
            dbc.CardHeader(daq.LEDDisplay(id=f'{id}-mass_flow',
                label="Flow Rate [CCM]",
                value=0.00,
                size=100,
            )),
            dbc.CardBody([
                html.H3(id.upper(),className='card-title text-center'),

            ])

            ]),
        ],
        className="my-3 w-50",
        )

# layout = html.Div(id='flow-controllers',
#     children= [
#         dbc.Row([
#             dbc.Col([
#                 html.H1('Flow Controllers'),
#             ],width=4, className='bg-secondary'),
#             dbc.Col([
#                 dbc.CardDeck([
#                     flow_meter('co_a'),
#                     flow_meter('co2'),
#                     flow_meter('co_b'),
#                     flow_meter('h2'),
#                 ])
#             ],width=8),
#         ],style={'min-height':'calc(100vh - 56px)'}),
#         dcc.Interval(
#             id='gas-updater',
#             interval=1*1000, # in milliseconds
#             n_intervals=0
#         )
#     ]
# )
layout = dbc.Container(id='flow-controllers',
    children= [
        dbc.Row([
            dbc.CardDeck([
                flow_meter('co_a'),
                flow_meter('co2'),
                flow_meter('co_b'),
                flow_meter('h2'),
            ],className='w-100')
        ],style={'min-height':'calc(100vh - 56px)'}),
        dcc.Interval(
            id='gas-updater',
            interval=1*1000, # in milliseconds
            n_intervals=0
        )
    ]
)

@app.callback([
        Output('co_a-mass_flow', 'value'),
        Output('co_b-mass_flow', 'value'),
        Output('co2-mass_flow', 'value'),
        Output('h2-mass_flow', 'value'),],
    [Input('gas-updater','n_intervals')],
    prevent_initial_call=True)
def update_output(n):
    if lab.gas is None:
        raise PreventUpdate
    else:
        gas = {key: val if val > 0 else 0 for key, val in lab.gas.get_all().items()}
        if not gas:
           raise PreventUpdate 
        return f"{gas['co_a']:.2f}", f"{gas['co_b']:.3f}", f"{gas['co2']:.2f}", f"{gas['h2']:.2f}"
