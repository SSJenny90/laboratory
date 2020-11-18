import dash_html_components as html
import dash_table
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_daq as daq
from dash.dependencies import Input, Output, State, MATCH, ALL
from app import app, lab, cache, get_sample
import os
import json
from dash.exceptions import PreventUpdate
from laboratory.processing import Sample
import time
from dash.dash import no_update
import copy 
import dash
import components as comp

def experiment_card(data):
    name = data.pop('name','Unknown')
    freq = data.pop('freq',[])
    return html.Div(className="col-xl-3 col-md-6 mb-4", children=[ 
        html.Div(
            className="card border-left-info shadow h-100 mb-4",
            children=[
            html.Div(
                className="card-header py-3 d-flex flex-row align-items-center justify-content-between",
                children = [
                    html.H6(
                        children=name.upper(),
                        className='m-0 font-weight-bold text-primary'
                    ),
            ]),
            dbc.CardBody(children=[
                html.P(data.pop('description','')),
                dbc.Button(
                    id={'sample-load-button': data.pop('dir')},
                    children="Load Sample", color="primary"),
                ]),
            dbc.CardFooter(
                ", ".join([f"{k.capitalize()}: {v}" for k,v in data.items()])
            ),
    ])
    ])


def layout():
    card_data = []
    for experiment in [d for d in os.listdir('data') if not d.startswith('_')]:
        with open(os.path.join('data',experiment,'sample.json')) as sample:
            card_data.append({**json.load(sample),'dir':experiment})

    return [
        comp.header('Previous Experiments'),
        html.Div(
            # id='experiment-cards', 
            className='row', 
            children=[experiment_card(card) for card in card_data]
            ),
        ]



@app.callback(
    [    Output('signal', 'data'),
        # Output({'sample-load-button': ALL},'className')
    ],
    [Input({'sample-load-button': ALL}, 'n_clicks')],
    [State({'sample-load-button': ALL}, 'id')],
    )
def get_sample_data(n_clicks, data_dir):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    else:
        directory = ctx.triggered[0]['prop_id'].split('.')[0].split(':')[-1].split('"')[1:2][0]
        get_sample(directory)
    return [directory]




