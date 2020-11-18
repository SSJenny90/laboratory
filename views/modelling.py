import dash_html_components as html
import dash_table
import dash_bootstrap_components as dbc
import dash_daq as daq
from dash.dependencies import Input, Output, State, MATCH, ALL
from app import app, lab, get_sample
import os
import json
from dash.exceptions import PreventUpdate
import time
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash_core_components as dcc

fig = make_subplots(rows=4, cols=1, 
    shared_xaxes=True,
    specs = [[{}], [{}], [{}], [{}]],
    vertical_spacing=0.01)

modelling = [
    html.Div(
        id='home',
        className="d-sm-flex align-items-center justify-content-between mb-4",
        children=[
            html.H1('Overview', className='page-header display-5 text-center'),
        ]),
    dcc.Graph('experiment-1',figure=fig),

]



# @app.callback(
#     Output('experiment-1', 'figure'), 
#     [Input('signal', 'data'),
#     State('experiment-1','figure'),
#     ])
# def update_experiment(value, figure):
#     if value is None:
#         raise PreventUpdate
        
#     df = get_sample(value).data


#     for i, data in enumerate(['temp','target_temp','voltage','actual_fugacity','h2']):
#         figure['data'][i]['x'] = df['time']
#         figure['data'][i]['y'] = df[data]


#     return figure



