from odoo import models, fields, api

class CourseReview(models.Model):
    _name = 'elearning.course.review'
    _description = 'Course Review'
    _order = 'create_date desc'

    course_id = fields.Many2one('elearning.course', string='Course', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user)
    rating = fields.Selection([
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars'),
    ], string='Rating', required=True)
    comment = fields.Text(string='Comment')

    _sql_constraints = [
        ('unique_user_course_review', 'unique(user_id, course_id)', 'You can only review a course once.')
    ]
