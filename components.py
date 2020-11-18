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


def header(header):
    return html.Div(
        className='d-sm-flex align-items-center justify-content-between mb-4',
        children=html.H1(
            className="h3 mb-0 text-gray-800",
            children=header)
        )

def figure(name, col_dims=''):
    fig = go.Figure(go.Scatter())
    # fig.update_layout(
    #     margin=dict(l=50, r=50, t=5, b=5),
    # )
    return html.Div(className=f"{col_dims} mb-4", children=[ 
            html.Div(
                className="card border-left-light shadow h-100 mb-4",
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
                    dcc.Graph(
                    id=name,
                    figure=fig,
                    config=dict(
                        displaylogo=True,
                        frameMargins=0,
                        toImageButtonOptions=dict(
                            format='svg',
                        ),
                        )
                    )
                ]),
            ])
        ])