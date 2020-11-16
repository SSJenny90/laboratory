import dash_html_components as html
import dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_daq as daq
from dash.dependencies import Input, Output

from app import app, lab 


layout = dbc.Container(id='flow-controllers',
    children= [
        daq.LEDDisplay(id='furnace-display',
                label="Flow Rate [CCM]",
                value=40,
                size=150,
            ),
        daq.Slider(id='furnace-setpoint',
            value=40,
            vertical=True
            ), 
        dcc.Interval(
            id='furnace-updater',
            interval=1*100, # in milliseconds
            n_intervals=0
        )
    ]
)

@app.callback(
        Output('furnace-display', 'value'),
    [Input('furnace-updater','n_intervals'),
    Input('furnace-setpoint','value')],)
def update_furnace(n,target):
    if lab.furnace is None:
        raise PreventUpdate
    else:
        # set the furnace target
        lab.furnace.remote_setpoint(int(target))
        return lab.furnace.indicated()
