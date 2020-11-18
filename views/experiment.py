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
import components as comp
from laboratory.processing import BUFFERS
import pandas as pd
from datetime import datetime

#=========== SETUP =================
table_columns = [{
            'id': 'target_temp',
            'name': 'Target [\u00B0C]',
            'type': 'numeric'
        }, {
            'id': 'hold_length',
            'name': 'Hold Length [hrs]',
            'type': 'numeric',
        }, {
            'id': 'heat_rate',
            'name': 'Heating Rate',
            'type': 'numeric',
        }, {
            'id': 'interval',
            'name': 'Interval [minutes]',
            'type': 'numeric',
        }, {
            'id': 'buffer',
            'name': 'fo2 buffer',
            'type': 'text',
            'presentation': 'dropdown'
        }, {
            'id': 'offset',
            'name': 'fo2 offset [log Pa]',
            'type': 'numeric',
        }, {
            'id': 'fo2_gas',
            'name': 'Gas mix type',
            'type': 'text',
            'presentation': 'dropdown'
        }, {
            'id': 'thermopower',
            'name': 'Target gradient',
            'type': 'numeric',
        }]

table = html.Div(className="col-12 mb-4", children=[ 
            html.Div(
                className="card border-left-light shadow h-100 mb-4",
                children=[
                html.Div(
                    className="card-header py-3 d-flex flex-row align-items-center justify-content-between",
                    children = [
                        html.H6(
                            children='Control File',
                            className='m-0 font-weight-bold text-primary'
                        ),
                ]),
                dbc.CardBody(children=[
                    dash_table.DataTable(
                        id='setup-table',
                        persistence=True,
                        persisted_props=['data'],
                        persistence_type='session',
                        row_deletable=True,  
                        editable=True,
                        data=[{x['id']:None for x in table_columns}],
                        columns=table_columns,
                        dropdown={
                            'buffer': {
                                    'options': [{'label': k.upper(), 'value': k} for k in BUFFERS.keys()]
                                },
                                'fo2_gas': {
                                    'options': [
                                        {'label': 'CO2/H2', 'value': 'h2'},
                                        {'label': 'CO2/CO', 'value': 'co'},
                                    ]
                                }
                            }
                    ),
                    html.Button(id='add-rows-button', className='my-3 btn-circle btn-lg btn-primary border-0', n_clicks=0, children=[
                        html.I(className='fas fa-plus')
                    ]),
                ]),
            ])
        ])

setup = [
    comp.header('Setup'),
    comp.figure('preview','col-8'),
    table,
]

@app.callback(
    Output('setup-table', 'data'),
    [Input('add-rows-button', 'n_clicks')],
    [State('setup-table', 'data'),
     State('setup-table', 'columns')])
def add_row(n_clicks, rows, columns):
    if n_clicks > 0:
        rows.append(rows[-1])
    return rows


@app.callback(
    Output('preview', 'figure'),
    [Input('setup-table', 'data'),
     Input('setup-table', 'columns'),
     State('preview','figure')])
def display_output(rows, columns, fig):
    rows.insert(0,{k:0 for k in rows[0].keys()})
    df = pd.DataFrame(rows)

    hours = df.hold_length
    ind = df.thermopower.notnull()
    hours.loc[ind] = hours.loc[ind] + 4

    hours = hours + (df.target_temp - df.target_temp.shift()) / df.heat_rate / 60
    hours[0] = 0
    hours = pd.to_timedelta(hours.cumsum(),'h')
    
    x = datetime.now() + hours
    fig['data'] = [
        {'type':'scatter', 'x':x, 'y':df.target_temp, 'name':'Temperature'},
        {'type':'scatter', 'x':x, 'y':df.offset, 'name':'Buffer offset'},
        ]

    fig['layout'] = dict(
        showlegend=False,
        yaxis=dict(
            title="Temperature",
            titlefont=dict(
                color="#1f77b4"
            ),
            tickfont=dict(
                color="#1f77b4"
            )
        ),
        yaxis2=dict(
            title="fo2 [log Pa]",
            titlefont=dict(
                color="#d62728"
            ),
            tickfont=dict(
                color="#d62728"
            ),
            anchor="x",
            overlaying="y",
            side="right"
        ),
    )

    return fig




#=========== OVERVIEW =================
overview = [
    comp.header('Overview'),
    comp.figure('temperature','col-12'),
    comp.figure('gas','col-12'),
    comp.figure('fugacity','col-12'),
    comp.figure('voltage','col-12'),
]

@app.callback(
    Output('temperature', 'figure'), 
    [Input('signal', 'data'), State('temperature','figure')])
def update_temperature(value, figure):
    if value is None:
        raise PreventUpdate
    df = get_sample(value).data

    figure['data'] = [
        {'type':'scatter', 'x':df.time, 'y':df.temp, 'name':'Temp'},
        {'type':'scatter', 'x':df.time, 'y':df.target_temp, 'name':'Target'},
        ]

    return figure

@app.callback(
    Output('gas', 'figure'), 
    [Input('signal', 'data'), State('gas','figure')])
def update_gas(value, figure):
    if value is None:
        raise PreventUpdate
    df = get_sample(value).data

    figure['data'] = [
        {'type':'scatter', 'x':df.time, 'y':df.co2, 'name':'CO2'},
        {'type':'scatter', 'x':df.time, 'y':df.h2, 'name':'H2'},
        {'type':'scatter', 'x':df.time, 'y':df.co, 'name':'CO'},
        ]

    return figure

@app.callback(
    Output('fugacity', 'figure'), 
    [Input('signal', 'data'), State('fugacity','figure')])
def update_fugacity(value, figure):
    if value is None:
        raise PreventUpdate
    df = get_sample(value).data

    figure['data'] = [
        {'type':'scatter', 'x':df.time, 'y':df.fugacity, 'name':'Target'},
        {'type':'scatter', 'x':df.time, 'y':df.log10_fugacity, 'name':'Actual'},
        ]

    return figure

@app.callback(
    Output('voltage', 'figure'), 
    [Input('signal', 'data'), State('voltage','figure')])
def update_voltage(value, figure):
    if value is None:
        raise PreventUpdate
    df = get_sample(value).data

    figure['data'] = [
        {'type':'scatter', 'x':df.time, 'y':df.voltage, 'name':'Voltage'},
        ]

    return figure
