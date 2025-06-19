from odoo import http
from odoo.http import request


class SectionController(http.Controller):
    @http.route("/sections", auth="user", website=True, type="http")
    def list_sections(self, page=1, **kw):
        PAGE_SIZE = 5
        try:
            page = int(page)  # Convert page to an integer
        except ValueError:
            page = 1  # Default to page 1 if conversion fails

        count = request.env["wrrrit.ai.prompt.section"].search_count([])
        total_pages = (count - 1) // PAGE_SIZE + 1
        sections = request.env["wrrrit.ai.prompt.section"].search(
            [], limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE
        )
        return http.request.render(
            "wrrrit_ai.template_sections_list",
            {"sections": sections, "total_pages": total_pages, "current_page": page},
        )

    @http.route(
        "/section/create", auth="user", website=True, methods=["GET", "POST"], csrf=True
    )
    def create_section(self, **post):
        if request.httprequest.method == "POST":
            request.env["wrrrit.ai.prompt.section"].create(post)
            return request.redirect("/sections")
        return request.render("wrrrit_ai.wrrrit_ai_template_section_create", {})

    @http.route(
        '/section/edit/<model("wrrrit.ai.prompt.section"):section>/',
        auth="user",
        website=True,
        methods=["GET", "POST"],
    )
    def edit_section(self, section, **post):
        if request.httprequest.method == "POST":
            section.write(post)
            return request.redirect("/sections")
        return request.render(
            "wrrrit_ai.wrrrit_ai_template_section_edit", {"section": section}
        )

    @http.route(
        '/section/delete/<model("wrrrit.ai.prompt.section"):section>/',
        auth="user",
        website=True,
    )
    def delete_section(self, section):
        section.unlink()
        return request.redirect("/sections")

    @http.route(
        '/section/details/<model("wrrrit.ai.prompt.section"):section>',
        auth="user",
        website=True,
    )
    def section_details(self, section):
        return request.render(
            "wrrrit_ai.wrrrit_ai_template_section_details", {"section": section}
        )

    @http.route("/about", auth="user", website=True)
    def about(self):
        return request.render("wrrrit_ai.wrrrit_ai_template_about")

    @http.route("/help", auth="user", website=True)
    def help(self):
        return request.render("wrrrit_ai.wrrrit_ai_template_help")
