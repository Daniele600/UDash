from dash import callback, dcc, html
from dash_service.models import Page, Splashpage
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
    
    splashpages = "There are no splash pages defined yet" 
    dashboards_pages = "There are no dashboard pages defined yet" 

    all_splashpages = Splashpage.query.all()
    all_dashboards = Page.query.all()
    
    all_splashpages.sort(key=lambda x: (x.project.name, strip_accents(x.title)))
    all_dashboards.sort(key=lambda x: (x.project.name, strip_accents(x.title)))
    
    if all_splashpages is not None and len(all_splashpages)>0:
        tbl_header_menu = [html.Thead(html.Tr([html.Th("Project"),html.Th("Page"), html.Th("Link")]))]
        for spl in all_splashpages:
            tbl_rows = []
            lnk = html.A(children=(spl.title),href=f"?prj={spl.project.slug}&page={spl.slug}")
            tbl_rows.append(html.Tr([html.Td(spl.project.name),html.Td(spl.title),html.Td(lnk)]))
        tbl_body_menu = [html.Tbody(tbl_rows)]
    
        splashpages=dbc.Table(tbl_header_menu + tbl_body_menu, bordered=True)

    if all_dashboards is not None and len(all_dashboards)>0:
        tbl_header = [html.Thead(html.Tr([html.Th("Project"),html.Th("Page"), html.Th("Link")]))]
        for dashb in all_dashboards:
            tbl_rows = []
            lnk = html.A(children=(dashb.title),href=f"?prj={dashb.project.slug}&page={dashb.slug}")
            tbl_rows.append(html.Tr([html.Td(dashb.project.name),html.Td(dashb.title),html.Td(lnk)]))
        tbl_body = [html.Tbody(tbl_rows)]
    
        dashboards_pages=dbc.Table(tbl_header + tbl_body, bordered=True)

    header_menupages = html.Div(className = "row", children=[html.H2("Splash pages")])
    splashpages_div=html.Div(className = "row col", children=[splashpages])

    header_dashboards = html.Div(className = "row", children=[html.H2("Dashboards")])
    dashboard_div=html.Div(className = "row col", children=[dashboards_pages])



    

    ret = html.Div(
        #className="container",
        children=[
            html.Div(children=[header_menupages,splashpages_div]),
            html.Div(children=[header_dashboards,dashboard_div]),
        ],
    )

    return ret
