from odoo import models, fields


class CourseCategory(models.Model):
    _name = 'elearning.category'
    _description = 'Course Category'

    name = fields.Char(string='Category Name', required=True)
    description = fields.Text(string='Description')
    courses = fields.One2many('elearning.course', 'category_id', string='Courses')
