"""Contains layouts suitable for being the value of the 'layout' attribute of
Dash app instances.
"""

import dash
from dash import dcc, html

def base_layout():
    return html.Div(
        id="mainContainer",
        className="has-bootstrap",
        children=[
            dcc.Store(id="store"),
            html.Div(
                className="container-fluid",
                children=[
                    html.Div(id="dash_main_container"),
                    dcc.Location(id="dash-location", refresh=False),
                ],
            ),
        ],
    )