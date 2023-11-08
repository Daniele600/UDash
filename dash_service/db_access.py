from .models import Project, Dashboard, MenuPage,User
from sqlalchemy import and_
from flask_sqlalchemy import SQLAlchemy


class db_access:
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
            return db_access.TYPE_DASHBOARD

        menupage = (
            MenuPage.query.with_entities(MenuPage.id)
            .join(Project)
            .filter(and_(Project.slug == prj_slug, MenuPage.slug==page_slug))
        ).first()
        if menupage is not None:
            return db_access.TYPE_MENU
        
        return db_access.TYPE_UNKNOWN
    
    def get_user_by_id(self, user_id):
        return User.query.filter(User.id==user_id).first()
