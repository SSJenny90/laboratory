import dash_html_components as html
import dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_daq as daq
from dash.dependencies import Input, Output
import components as comp
from app import app, lab 

def flow_meter(id):
    return html.Div(className="col-xl-3 col-md-6 mb-4", children=[ 
        html.Div(
            id=id,
            # className="card shadow mb-4",
            className="card border-left-warning shadow h-100 mb-4",
            children=[
            html.Div(
                className="card-header py-3 d-flex flex-row align-items-center justify-content-between",
                children = [
                    html.H6(
                        children=id.upper(),
                        className='m-0 font-weight-bold text-primary'
                    ),
            ]),
            dbc.CardBody(
                daq.LEDDisplay(id=f'{id}-mass_flow',
                    label="Flow Rate [CCM]",
                    value=f"0.00",
                    size=100,
                )),
            ]),
    ])

layout = [
    comp.header('Alicat Flow Controllers'),
    html.Div(id='flow-controllers', className='row', children=[
        flow_meter('co_a'),
        flow_meter('co_b'),
        flow_meter('co2'),
        flow_meter('h2'),
    ]),
    dcc.Interval(
        id='gas-updater',
        interval=1*1000, # in milliseconds
        n_intervals=0
    )
]

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
