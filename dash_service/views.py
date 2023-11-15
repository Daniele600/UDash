import os
#import pathlib

from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.fileadmin import FileAdmin
from sqlalchemy.sql import func
from .models import Page, Splashpage,User
from wtforms.fields import PasswordField
from wtforms import validators
from .app_settings import FILES_UPLOAD_PATH,FILES_UPLOAD_ALLOWED_EXT
import flask_login


def get_current_user()->User:
    return flask_login.current_user

def is_admin()->bool:
    if flask_login.current_user.is_authenticated:
        if flask_login.current_user.is_admin:
            return True
    return False



class ProjectView(ModelView):
    column_list = ("name", "slug", "description", "created_at", "updated_at")
    column_searchable_list = ("name", "slug", "description")
    column_filters = ("name", "slug", "description")
    form_excluded_columns = ("created_at", "updated_at", "pages")
    form_readonly_columns = ("slug",)

    def is_accessible(self):
        return is_admin()
    
class DashboardView(ModelView):
    column_display_all_relations = True
    # column_formatters = {
    #     "content": json_formatter,
    # }
    column_list = (
        "project",
        "title",
        "slug",
        # "content",
        "geography",
        "created_at",
        "updated_at",
    )

    fields_order = (
        "project",
        "title",
        "slug",
        "content",
        "geography",
        "created_at",
        "updated_at",
    )

    form_create_rules = fields_order
    form_edit_rules = fields_order

    form_widget_args = {
        "created_at": {"disabled": True},
        "updated_at": {"disabled": True},
    }

    form_excluded_columns = ["page"]

    items = []
    upload_files_path = (
        #f"{pathlib.Path(__file__).parent.parent.absolute()}/dash_service/static"

    )
    #up = upload_files_path
    upload_files_path = os.path.join(os.path.dirname(__file__), FILES_UPLOAD_PATH)

    if os.path.isdir(upload_files_path):
        for f in os.listdir(upload_files_path):
            if os.path.isfile(os.path.join(upload_files_path, f)):
                items.append((f, f))

    form_choices = {"geography": items}

    def is_accessible(self):
        return get_current_user().is_authenticated

    def get_query(self):
        if is_admin():
            return self.session.query(self.model)
        return self.session.query(self.model).filter(
            Page.project_id == get_current_user().project_id
        )

    def get_count_query(self):
        if is_admin():
            return self.session.query(func.count("*"))
        return self.session.query(func.count("*")).filter(
            Page.project_id == get_current_user().project_id
        )
    

class SplashView(ModelView):
    column_display_all_relations = True
    column_list = (
        "project",
        "title",
        "slug",
        "created_at",
        "updated_at",
    )

    fields_order = (
        "project",
        "title",
        "slug",
        "content",
        "created_at",
        "updated_at",
    )
    form_create_rules = fields_order
    form_edit_rules = fields_order

    form_widget_args = {
        "created_at": {"disabled": True},
        "updated_at": {"disabled": True},
    }

    form_excluded_columns = ["page"]

    def is_accessible(self):
        return get_current_user().is_authenticated

    def get_query(self):
        if is_admin():
            return self.session.query(self.model)
        return self.session.query(self.model).filter(
            Splashpage.project_id == get_current_user().project_id
        )

    def get_count_query(self):
        if is_admin():
            return self.session.query(func.count("*"))
        return self.session.query(func.count("*")).filter(
            Splashpage.project_id == get_current_user().project_id
        )


class UserView(ModelView):
    #On create form add the DataRequired validator
    def create_form(self, obj=None):
        form = super().create_form(obj)
        form.password2.validators = [validators.DataRequired()]
        # , [validators.DataRequired()]

        return form
    #On edit form add the leave blank to keep old password message
    def edit_form(self, obj=None):
        form = super().edit_form(obj)

        form.password2.description = (
            "Type a new passoword to change it, leave blank otherwise"
        )

        return form

    column_display_all_relations = True
    column_list = (
        "id",
        "name",
        "email",
        # "password",
        "project",
        "is_admin",
        "is_user_active",
        "created_at",
        "updated_at",
    )

    # The order of the fileds
    form_columns = (
        "project",
        "name",
        "email",
        # "password",
        "password2",
        "is_admin",
        "is_user_active",
        "created_at",
        "updated_at",
    )

    form_widget_args = {
        "created_at": {"disabled": True},
        "updated_at": {"disabled": True},
    }


    #Create a password2 field to prevent the form overwriting the old password
    form_excluded_columns = "password"
    form_extra_fields = {"password2": PasswordField("Password")}

    def on_model_change(self, form, instance, is_created):

        # if is_created:
        #     instance.set_password(form.password.data)
        # else:
        #     old_pwd = form.password.object_data
        #     if old_pwd != instance.password:
        #         instance.set_password(form.password.data)

        #User created? add the pwd
        if is_created:
            instance.set_password(form.password2.data)
        #User edited? If password2 filed is empty kepp old pwd, replace otherwise
        else:
            old_hashed_pwd = instance.password
            if form.password2.data.strip()!="":
                instance.set_password(form.password2.data)
            else:
                instance.password=old_hashed_pwd

        

        #raise Exception("prevent update")

    def is_accessible(self):
        return is_admin()


class ExtFileAdmin(FileAdmin):
    # def __init__(self, base_path, *args, **kwargs):
    #     super().__init__(base_path, *args, **kwargs)

    allowed_extensions = FILES_UPLOAD_ALLOWED_EXT

    #upload_template = 'templates/admin/extFileForml.html'
    upload_template = 'admin/file/extFileForml.html'

    def is_accessible(self):
        return is_admin()



# # production storage will be an Azure blob storage
# path = os.path.join(os.path.dirname(__file__), "static")

# admin.add_view(FileAdmin(path, "/static/", name="Static Files"))
#admin.add_view(ExtFileAdmin(path, "/static/", name="Static Files"))