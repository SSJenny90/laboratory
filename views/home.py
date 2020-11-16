import dash_html_components as html
import dash_table
import dash_bootstrap_components as dbc
import dash_daq as daq
from dash.dependencies import Input, Output
from app import app, lab

layout = html.Div(id='home',children=[
    html.H1('Welcome to the Conductive Earth Laboratory!', className='display-5 text-center'),
    daq.PowerButton(id='my-power-button',
        on=False,
        size=150,
        label='Connect Instruments'
    ),
    html.Div(id='power-button-output',className='d-none')
],
)

@app.callback(
    Output('power-button-output', 'children'),
    [Input('my-power-button', 'on')],
    prevent_initial_call=True
    )
def update_output(on):
    if on:
        lab.load_instruments()
        return '/instruments'
    else:
        return lab.shutdown()
