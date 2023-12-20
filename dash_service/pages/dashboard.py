import textwrap

import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import pandas as pd
import pandas.api.types
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from dash import callback, dcc, html, ctx
from dash.dependencies import MATCH, Input, Output, State, ALL
from dash_service.models import Page, Project, Dashboard
import json

from dash_service.pages import get_data, is_float, is_int, years, get_geojson
from dash_service.pages import (
    add_structure,
    #get_structure_id,
    get_code_from_structure_and_dq,
    get_col_name,
    merge_with_codelist,
    get_multilang_value,
    is_string_empty,
    get_label_from_structure_and_code,
)


from flask import abort
from sqlalchemy import and_

from dash_service.components_aio.card_aio import CardAIO
from dash_service.components_aio.map_aio import MapAIO
from dash_service.components_aio.chart_aio import ChartAIO
from dash_service.components_aio.downloads_aio import DownloadsAIO
from dash_service.components_aio.heading_aio import HeadingAIO
from dash_service.components_aio.pages_navigation_aio import PagesNavigationAIO
from dash_service.components_aio.years_range_selector_aio import YearsRangeSelectorAIO

import copy
import requests

# pd.set_option("display.max_columns", None)
# pd.set_option("display.max_rows", None)
# pd.set_option("display.width", 0)

# A few constant values
ID_INDICATOR = "INDICATOR"
ID_REF_AREA = "REF_AREA"
ID_OBS_VALUE = "OBS_VALUE"
ID_DATA_SOURCE = "DATA_SOURCE"
ID_TIME_PERIOD = "TIME_PERIOD"
LABEL_COL_PREFIX = "_L_"
DEFAULT_LABELS = ["OBS_VALUE", "TIME_PERIOD", "REF_AREA"]

ELEM_ID_PAGE_NAV = "PAGE_NAV"
ELEM_ID_YEARS_RANGE_SEL = "YEARS_RANGE_SEL"
ELEM_ID_CARDS = "CARDS"
ELEM_ID_MAIN = "MAIN"
ELEM_ID_CHARTS = "CHARTS"
ELEM_ID_HEADING = "HEADING"

#CFG_N_THEMES = "THEMES"

DBELEM = "DBELEM_"


# set defaults
pio.templates.default = "plotly_white"
# px.defaults.color_continuous_scale = px.colors.sequential.BuGn
UNICEF_color_continuous_scale = [
    "#002759",
    "#00377D",
    "#0058AB",
    "#0083CF",
    "#1CABE2",
    "#69DBFF",
    "#A3EAFF",
    "#CFF4FF",
]
UNICEF_color_qualitative = [
    "#0058AB",
    "#1CABE2",
    "#00833D",
    "#80BD41",
    "#6A1E74",
    "#961A49",
    "#E2231A",
    "#F26A21",
    "#FFC20E",
    "#FFF09C",
]
# px.defaults.color_discrete_sequence = px.colors.qualitative.Dark24
px.defaults.color_discrete_sequence = UNICEF_color_qualitative
px.defaults.color_continuous_scale = UNICEF_color_continuous_scale

default_font_family = "Roboto"
default_font_size = 12


# move this elsewhere
translations = {
    "sources": {"en": "Sources", "pt": "Fontes"},
    "years": {"en": "Years", "pt": "Anos"},
    "show_historical": {"en": "Show historical data", "pt": "Mostrar série histórica"},
    "bar": {"en": "Bar", "pt": "Gráfico em colunas"},
    "line": {"en": "Line", "pt": "Gráfico em linhas"},
    "scatter": {"en": "Scatter", "pt": "Scatter PT"},
    "download_excel": {"en": "Download Excel", "pt": "Download Excel"},
    "download_csv": {"en": "Download CSV", "pt": "Download CSV"},
    "OBS_VALUE": {"en": "Value", "pt": "Valores"},
    "TIME_PERIOD": {"en": "Time period", "pt": "Ano"},
    "REF_AREA": {"en": "Geographic area", "pt": "Estado"},
}

# the configuration of the "Download plot" button in the charts
cfg_plot = {
    "toImageButtonOptions": {
        "format": "png",  # one of png, svg, jpeg, webp
        "filename": "plot",
        "width": 1200,
        "height": 800,
        "scale": 1,  # Multiply title/legend/axis/canvas sizes by this factor
    },
    "displayModeBar": True,
    "displaylogo": False,
}

colours = ["success", "warning", "danger", "info"]

EMPTY_CHART = {
    "layout": {
        "xaxis": {"visible": False},
        "yaxis": {"visible": False},
        "annotations": [
            {
                "text": "No data is available for the selected filters",
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 28},
            }
        ],
    }
}


# The entry point, retrieves the page from the storage and renderes the page
def layout(lang="en", **query_params):
    """
    Returns the page layout
    """

    project_slug = query_params.get("prj", None)
    page_slug = query_params.get("page", None)

    db_config = (
        Dashboard.query.join(Project)
        .filter(and_(Page.slug == page_slug, Project.slug == project_slug))
        .first()
    )

    page_config = db_config.content
    geography = db_config.geography

    print("page_config")
    print("page_config")
    print("page_config")
    print("page_config")
    print(page_config)

    return render_page_template(
        page_config, geography, lang, query_params, project_slug
    )


# Gets the element that will be rendered on the navigation bar
def get_page_nav_items(page_config, project_slug, lang):
    nav_type = None
    ret = None
    if "page_nav" in page_config and "type" in page_config["page_nav"]:
        nav_type = page_config["page_nav"]["type"]
    if nav_type is None:
        nav_type = "all"
    if nav_type == "all":
        nav_items = (
            Dashboard.query.with_entities(
                Dashboard.slug, Dashboard.title, Project.slug.label("prj_slug")
            )
            .join(Project)
            .filter(Project.slug == project_slug)
            .all()
        )

        ret = [
            {"name": ni.title, "prj_slug": ni.prj_slug, "slug": ni.slug, "lang": lang}
            for ni in nav_items
        ]
    return ret


def render_page_template(
    page_config: dict, geojson: str, lang: str, query_params, project_slug: str
) -> html.Div:

    elem_page_nav = None
    elem_main_title = None
    #elem_years_selector = None

    nav_links = get_page_nav_items(page_config, project_slug, lang)

    if nav_links is not None and len(nav_links) > 0:
        elem_page_nav = PagesNavigationAIO(
            nav_links, query_params, aio_id=ELEM_ID_PAGE_NAV
        )

    if "main_title" in page_config:
        elem_main_title = HeadingAIO(page_config["main_title"], aio_id=ELEM_ID_HEADING)

    # elem_years_selector = YearsRangeSelectorAIO(
    #     aio_id=ELEM_ID_YEARS_RANGE_SEL, additional_classes="pb-2"
    # )

    home_icon = None
    
    if "home_button" in page_config and "params" in page_config["home_button"]:
        #"home_button":{"params":"prj=rosa&page=home_page"},
        home_link = "?"+page_config["home_button"]["params"]
        home_icon = html.A(
            className="text-primary",
            children=html.I(className="fa-solid fa-house fa-2xl"),
            href=home_link
        )

    ret = html.Div(
        [
            dcc.Store(id="lang", data=lang),  # stores the language
            dcc.Store(id="sel_state", data=None),  # stores the selection state
            dcc.Store(id="page_config", data=page_config),  # stores the page config
            dcc.Store(id="geoj", data=geojson),  # stores the geoJson
            dcc.Store(
                id="data_structures", data={}, storage_type="session"
            ),  # stores the data structure for caching
            dcc.Location(
                id="theme"
            ),  # controls the location hash (e.g. education#theme)
            elem_page_nav,
            elem_main_title,
            html.Div(
                className="bg-light mt-2",
                children=[
                    html.Div(
                        className="d-flex justify-content-center py-2",
                        children=[dbc.ButtonGroup(id="theme_buttons")],
                    ),
                    html.Div(className="float-start align-middle ms-3", children=[home_icon]),
                    # html.Div(
                    #     className="d-flex justify-content-center",
                    #     children=elem_years_selector,
                    # ),
                ],
            ),
            html.Div(id="dashboard_contents", className="mt-2", children=[]),
        ]
    )

    return ret

def get_themes(page_config:dict):
    theme_isactive_k = [ k for k, v in page_config.items() if k.startswith('is_theme_active_')] # get all the is_theme_active_# keys
    theme_numbers = [int(n.split("_")[-1]) for n in theme_isactive_k] # get all the numbers n in is_theme_active_n
    theme_numbers = [n for n in theme_numbers if page_config["is_theme_active_"+str(n)]] # filter out the inactive themes

    ret = []
    for t in theme_numbers:
        ret.append({"id":"TH_"+str(t), "name":page_config["theme_name_"+str(t)], "components":page_config["theme_components_"+str(t)]})
    
    return ret

def get_theme_node(page_config:dict, theme_id:str):
    themes = get_themes(page_config)
    if theme_id is None:
        return themes[0]
    for t in themes:
        if t["id"]==theme_id:
            return t
    return None



# Triggered when the theme changes
# It only updates the state of the theme selection
@callback(
    Output("sel_state", "data"),
    [
        Input("theme", "hash")
    ],
    [State("page_config", "data"), State("lang", "data")],
)
def new_selection_state(theme, page_config, lang):

    themes = get_themes(page_config)
    # removes the leading # if a theme has been selected, the first theme available otherwise
    if theme:
        theme = theme[1:].upper()
    else:
        theme = str(themes[0]["id"])


    #theme = theme[1:].upper() if theme else next(iter(page_config[CFG_N_THEMES].keys()))
    # The selected years range

    selections = dict(theme=theme)

    return selections
    


def _get_elem_id(row, col):
    return f"{DBELEM}{row}_{col}"


def _get_elem_cfg_pos(elem_id):
    return {
        "row": int(elem_id.split("_")[1]),
        "col": int(elem_id.split("_")[2]),
    }


# Triggered when the selection state changes
@callback(
    Output(HeadingAIO.ids.subtitle(ELEM_ID_HEADING), "children"),
    Output("theme_buttons", "children"),
    # Output("dashboard_contents", "children"),
    [
        Input("sel_state", "data"),
    ],
    State("page_config", "data"),
)
def show_themes(selections, page_config):
    
    themes = get_themes(page_config)
    # Gets the theme's name to fill the Subtitle
    #No theme selected, get the first one
    if (selections is None or selections["theme"] is None or selections["theme"].strip() == ""):
        theme_node=themes[0]
    else:
        theme_node=get_theme_node(page_config,selections["theme"])

    print("theme_node")
    print(theme_node)

    subtitle = theme_node.get("name", "")

    # Creates the Themes' buttons; hide the buttons when only one option is available
    if len(themes) == 1:
        theme_buttons = None
    else:
        theme_buttons = []
        for idx, t in enumerate(themes):
            is_active = selections["theme"] == t["id"]
            theme_buttons.append(dbc.Button(t["name"], id="btn_theme_" + t["id"], color=colours[idx%len(colours)], class_name="theme mx-1", href=f"#{t['id'].lower()}", active=is_active))

    return subtitle, theme_buttons


@callback(
    Output("data_structures", "data"),
    [Input("sel_state", "data")],
    [State("page_config", "data"), State("lang", "data")],
)
# Downloads all the DSD for the data.
# Typically 1 dataflow per page but can handle data from multiple Dataflows in 1 page
def download_structures(selections, page_config, lang):
    data_structures = {}
    #TODO Move it back to config
    enpoint_url = "https://sdmx.data.unicef.org/ws/public/sdmxapi/rest"
    #enpoint_url = page_config["global_data_endpoint"]

    #theme_node = page_config[CFG_N_THEMES][selections["theme"]]
    theme_node = get_theme_node(page_config, selections["theme"])

    if "components" in theme_node:
        for comp in theme_node["components"]:
            if "dataquery" in comp:
                for dq in comp["dataquery"]:
                    if "dataflow" in dq and dq["dataflow"].strip()!="":
                        add_structure(enpoint_url, data_structures, dq["dataflow"], lang)


    return data_structures


def _round_pandas_col(df, col_name, round_to):
    if len(df) == 0:
        return df
    df[col_name] = pd.to_numeric(df[col_name], errors="ignore")
    if pandas.api.types.is_numeric_dtype(df[col_name]):
        df = df.round({col_name: round_to})
    return df


def format_num(n):
    if is_int(n):
        ret = "{0:{grp}d}".format(int(n), grp="_")
    elif is_float(n):
        ret = "{0:{grp}g}".format(float(n), grp="_")
    else:
        return n
    return ret.replace("_", " ")


