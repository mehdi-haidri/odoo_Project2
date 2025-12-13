from odoo import models, fields, api


class CourseCategory(models.Model):
    _name = 'elearning.category'
    _description = 'Course Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    image = fields.Image(string='Image')
    
    courses = fields.One2many('elearning.course', 'category_id', string='Courses')
    course_count = fields.Integer(string='Course Count', compute='_compute_course_count')

    @api.depends('courses')
    def _compute_course_count(self):
        for category in self:
            category.course_count = len(category.courses)
