from dash import callback, dcc, html
from dash_service.models import Page, MenuPage
import unicodedata
import dash_bootstrap_components as dbc


def layout(project_slug=None, page_slug=None, lang="en", **query_params):
    # Function to strip accents before sorting
    def strip_accents(s):
        return "".join(
            c
            for c in unicodedata.normalize("NFD", s)
            if unicodedata.category(c) != "Mn"
        )
    
    menu_pages = "There are no menu pages defined yet" 
    dashboards_pages = "There are no dashboard pages defined yet" 

    all_menupages = MenuPage.query.all()
    all_dashboards = Page.query.all()
    
    print(all_menupages)
    print(all_dashboards)
    

    all_dashboards.sort(key=lambda x: (x.project.name, strip_accents(x.title)))
    all_menupages.sort(key=lambda x: (x.project.name, strip_accents(x.title)))

    #if all_menupages is not None:


    

    ret = html.Div(
        #className="container",
        children=[
            html.Div(className="row col", children=[menu_pages]),
            html.Div(className="row col", children=[dashboards_pages]),
        ],
    )

    return ret
