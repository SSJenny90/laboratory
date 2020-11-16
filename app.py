import dash
from laboratory import Laboratory
import dash_bootstrap_components as dbc

lab = Laboratory()

stylesheets = [
    dbc.themes.CERULEAN,
]

app = dash.Dash(__name__, 
    external_stylesheets=stylesheets,
    suppress_callback_exceptions=True
    )

server = app.server