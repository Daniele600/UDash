from .models import Project, Dashboard, MenuPage
from sqlalchemy import and_


class db_utils:
    TYPE_UNKNOWN = -1
    TYPE_DASHBOARD = 1
    TYPE_MENU = 2

    def get_page_type(self, prj_slug, page_slug):
        dashboard = (
            Dashboard.query.with_entities(Dashboard.id)
            .join(Project)
            .filter(and_(Project.slug == prj_slug, Dashboard.slug == page_slug))
        ).first()

        if dashboard is not None:
            return db_utils.TYPE_DASHBOARD

        menupage = (
            MenuPage.query.with_entities(MenuPage.id)
            .join(Project)
            .filter(and_(Project.slug == prj_slug, MenuPage.slug==page_slug))
        ).first()
        if menupage is not None:
            return db_utils.TYPE_MENU
        
        return db_utils.TYPE_UNKNOWN